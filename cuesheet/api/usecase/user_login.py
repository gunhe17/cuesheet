from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.config import get_auth_config

from cuesheet.api.domain.common.exception import InvalidCredentialError, TooManyAttemptsError

from cuesheet.api.domain.user.login_id import LoginId
from cuesheet.api.domain.user.pin import Pin
from cuesheet.api.domain.user.session_token import SessionToken
from cuesheet.api.domain.user.user_repository import UserRepository
from cuesheet.api.domain.user.user_event import UserEvent

from cuesheet.api.domain.event.event.event_repository import EventRepository

from cuesheet.api.infrastructure.hash.argon2.client import argon2
from cuesheet.api.infrastructure.hash.sha256.client import sha256
from cuesheet.api.infrastructure.token.secrets.client import token
from cuesheet.api.infrastructure.database.postgresql.client import db_client
from cuesheet.api.infrastructure.database.postgresql.session import postgresql_transactional_session
from cuesheet.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    login_id: str
    pin: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def login(*, session, event_group_id, input: Input) -> Output:
    # find
    now = datetime.now(timezone.utc)
    config = get_auth_config()

    found = await UserRepository.verify_login_id(
        session=session,
        login_id=LoginId.from_str(input.login_id),
    )

    # guard
    if found.is_locked(at=now):
        raise TooManyAttemptsError(
            retry_after_sec=int((found.locked_until.to_datetime() - now).total_seconds()),
        )

    # verify
    if not (
        argon2.verify(
            hash=found.pin_hash.to_str(),
            value=Pin.from_str(input.pin).to_str(),
        )
    ):
        await _record_failure(entity=found, at=now, config=config)
        raise InvalidCredentialError()

    # issue
    raw_token = token.generate()

    # persist
    # 이전 세션 토큰을 덮어쓴다. 한 기기만 로그인되는 임시 구현이다
    event, user = UserEvent.updated(
        user=(
            await UserRepository.update(
                session=session,
                entity=found.succeed_login(
                    session_token=SessionToken.from_str(sha256.hash(value=raw_token)),
                ),
            )
        )
    )

    # return
    return Output(
        data={
            **user.to_dict(),
            "token": raw_token,
        },
        event=[
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="user_login",
                    atomics=[event],
                    actor_user_id=user.id,
                )
            )
        ],
    )


# #
# record

# 거부하면서 상태를 남겨야 하는 유일한 지점이다. 요청 트랜잭션은 raise 로 롤백되므로
# 실패 누적을 같은 session 에 쓰면 사라진다 — 별도 트랜잭션으로 확정한다 ([INV-5] 예외)
async def _record_failure(*, entity, at, config) -> None:
    async with postgresql_transactional_session() as isolated:
        await UserRepository.update(
            session=isolated,
            entity=entity.fail_login(
                at=at,
                max_attempts=config.LOGIN_MAX_ATTEMPTS,
                lock_sec=config.LOGIN_LOCK_SEC,
            ),
        )


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--login-id", required=True)
    parser.add_argument("--pin", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await login(
                session=session,
                event_group_id=uuid4(),
                input=Input(login_id=args.login_id, pin=args.pin),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
