from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.common.exception import UnauthorizedError

from cuesheet.api.domain.cuesheet.cuesheet_repository import CuesheetRepository

from cuesheet.api.domain.participant.participant import Participant
from cuesheet.api.domain.participant.can_advance import CanAdvance
from cuesheet.api.domain.participant.role_ids import RoleIds
from cuesheet.api.domain.participant.participant_repository import ParticipantRepository
from cuesheet.api.domain.participant.participant_event import ParticipantEvent

from cuesheet.api.domain.event.event.event_repository import EventRepository

from cuesheet.api.infrastructure.database.postgresql.client import db_client
from cuesheet.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    invite_token: str
    role_ids: list[str] = []


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def join(*, session, event_group_id, input: Input, cuesheet_id: UUID, user_id: UUID) -> Output:
    # find
    cuesheet = await CuesheetRepository.get_by_id(
        session=session,
        id=cuesheet_id,
    )

    # verify
    # 어느 링크로 들어왔는지가 권한을 정한다
    if input.invite_token == cuesheet.manager_token.to_str():
        can_advance = True
    elif input.invite_token == cuesheet.viewer_token.to_str():
        can_advance = False
    else:
        raise UnauthorizedError()

    # join
    # 재합류는 새로 만들지 않고 역할·권한만 갱신한다
    existing = await ParticipantRepository.find_by_user_and_cuesheet(
        session=session,
        user_id=user_id,
        cuesheet_id=cuesheet_id,
    )
    if existing is None:
        event, participant = ParticipantEvent.created(
            participant=(
                await ParticipantRepository.add_unique_by_cuesheet_and_user(
                    session=session,
                    entity=Participant.new(
                        cuesheet_id=cuesheet_id,
                        user_id=user_id,
                        can_advance=CanAdvance.from_bool(can_advance),
                        role_ids=RoleIds.from_json(input.role_ids),
                    ),
                )
            )
        )
    else:
        event, participant = ParticipantEvent.updated(
            participant=(
                await ParticipantRepository.update(
                    session=session,
                    entity=(
                        existing
                        .with_can_advance(CanAdvance.from_bool(can_advance))
                        .with_role_ids(RoleIds.from_json(input.role_ids))
                    ),
                )
            )
        )

    # return
    return Output(
        data=participant.to_dict(),
        event=[
            emitted.to_dict()
            for emitted in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="participant_join",
                    atomics=[event],
                    actor_user_id=user_id,
                )
            )
        ],
    )


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuesheet-id", required=True)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--invite-token", required=True)
    parser.add_argument("--role-id", action="append", default=[])
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await join(
                session=session,
                event_group_id=uuid4(),
                input=Input(invite_token=args.invite_token, role_ids=args.role_id),
                cuesheet_id=UUID(args.cuesheet_id),
                user_id=UUID(args.user_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
