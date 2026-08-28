from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.cuesheet.cuesheet_repository import CuesheetRepository
from cuesheet.api.domain.cuesheet.cuesheet_event import CuesheetEvent

from cuesheet.api.domain.participant.participant_repository import ParticipantRepository

from cuesheet.api.domain.event.event.event_repository import EventRepository

from cuesheet.api.infrastructure.database.postgresql.client import db_client
from cuesheet.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    pass


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def search(*, session, event_group_id, input: Input, user_id: UUID) -> Output:
    # find
    participants = await ParticipantRepository.filter_by_user_id(
        session=session,
        user_id=user_id,
    )
    founds = CuesheetEvent.read_many(
        cuesheets=(
            await CuesheetRepository.filter_by_ids(
                session=session,
                ids=[participant.cuesheet_id for participant in participants],
            )
        )
    )

    # return
    return Output(
        data=_listed(founds=founds, participants=participants),
        event=[
            emitted.to_dict()
            for emitted in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="cuesheet_search",
                    atomics=[event for event, _ in founds],
                    actor_user_id=user_id,
                )
            )
        ],
    )


# #
# listed

def _listed(*, founds: list, participants: list) -> list:
    mine = {participant.cuesheet_id: participant for participant in participants}
    return [
        {
            **cuesheet.to_dict(),
            "participant_id": str(mine[cuesheet.id].id),
            "can_advance": mine[cuesheet.id].can_advance.to_bool(),
            "role_ids": mine[cuesheet.id].role_ids.to_json(),
        }
        for _, cuesheet in founds
    ]


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await search(
                session=session,
                event_group_id=uuid4(),
                input=Input(),
                user_id=UUID(args.user_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
