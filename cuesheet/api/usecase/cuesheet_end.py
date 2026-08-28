from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.cuesheet.ended_at import EndedAt
from cuesheet.api.domain.cuesheet.cuesheet_repository import CuesheetRepository
from cuesheet.api.domain.cuesheet.cuesheet_event import CuesheetEvent

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
async def end(*, session, event_group_id, input: Input, cuesheet_id: UUID, user_id: UUID | None = None) -> Output:
    # find
    found = await CuesheetRepository.get_by_id(
        session=session,
        id=cuesheet_id,
    )

    # guard
    if found.ended_at is not None:
        return Output(data=found.to_dict(), event=[])

    # end
    event, cuesheet = CuesheetEvent.updated(
        cuesheet=(
            await CuesheetRepository.update(
                session=session,
                entity=found.end(
                    at=EndedAt.from_datetime(datetime.now(timezone.utc)),
                ),
            )
        )
    )

    # return
    return Output(
        data=cuesheet.to_dict(),
        event=[
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="cuesheet_end",
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
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await end(
                session=session,
                event_group_id=uuid4(),
                input=Input(),
                cuesheet_id=UUID(args.cuesheet_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
