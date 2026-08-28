from __future__ import annotations

import argparse
import asyncio
from uuid import uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.user.user import User
from cuesheet.api.domain.user.login_id import LoginId
from cuesheet.api.domain.user.user_name import UserName
from cuesheet.api.domain.user.pin import Pin
from cuesheet.api.domain.user.pin_hash import PinHash
from cuesheet.api.domain.user.user_repository import UserRepository
from cuesheet.api.domain.user.user_event import UserEvent

from cuesheet.api.domain.event.event.event_repository import EventRepository

from cuesheet.api.infrastructure.hash.argon2.client import argon2
from cuesheet.api.infrastructure.database.postgresql.client import db_client
from cuesheet.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    login_id: str
    name: str
    pin: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def register(*, session, event_group_id, input: Input) -> Output:
    # persist
    event, user = UserEvent.created(
        user=(
            await UserRepository.add_unique_by_login_id(
                session=session,
                entity=User.new(
                    login_id=LoginId.from_str(input.login_id),
                    name=UserName.from_str(input.name),
                    pin_hash=PinHash.from_str(
                        argon2.hash(value=Pin.from_str(input.pin).to_str()),
                    ),
                ),
            )
        )
    )

    # return
    return Output(
        data=user.to_dict(),
        event=[
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="user_register",
                    atomics=[event],
                )
            )
        ],
    )


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--login-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--pin", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await register(
                session=session,
                event_group_id=uuid4(),
                input=Input(
                    login_id=args.login_id,
                    name=args.name,
                    pin=args.pin,
                ),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
