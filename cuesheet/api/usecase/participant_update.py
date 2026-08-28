from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

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
    id: str
    can_advance: bool | None = None
    role_ids: list[str] | None = None


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def update(*, session, event_group_id, input: Input, cuesheet_id: UUID, user_id: UUID | None = None) -> Output:
    # find
    found = await ParticipantRepository.get_by_id(
        session=session,
        id=UUID(input.id),
        cuesheet_id=cuesheet_id,
    )
    updated = found

    # update
    if input.can_advance is not None:
        updated = updated.with_can_advance(CanAdvance.from_bool(input.can_advance))
    if input.role_ids is not None:
        updated = updated.with_role_ids(RoleIds.from_json(input.role_ids))

    # persist
    event, participant = ParticipantEvent.updated(
        participant=(
            await ParticipantRepository.update(
                session=session,
                entity=updated,
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
                    name="participant_update",
                    atomics=[event],
                    actor_user_id=user_id,
                    actor_cuesheet_id=cuesheet_id,
                )
            )
        ],
    )


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuesheet-id", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--can-advance", type=lambda v: v.lower() == "true")
    parser.add_argument("--role-id", action="append")
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await update(
                session=session,
                event_group_id=uuid4(),
                input=Input(id=args.id, can_advance=args.can_advance, role_ids=args.role_id),
                cuesheet_id=UUID(args.cuesheet_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
