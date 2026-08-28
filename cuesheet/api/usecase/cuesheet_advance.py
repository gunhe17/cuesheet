from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.cuesheet.cue_started_at import CueStartedAt
from cuesheet.api.domain.cuesheet.ended_at import EndedAt
from cuesheet.api.domain.cuesheet.cuesheet_repository import CuesheetRepository
from cuesheet.api.domain.cuesheet.cuesheet_event import CuesheetEvent

from cuesheet.api.domain.cue.cue_repository import CueRepository

from cuesheet.api.domain.event.event.event_repository import EventRepository

from cuesheet.api.infrastructure.database.postgresql.client import db_client
from cuesheet.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    expected_cue_id: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def advance(*, session, event_group_id, input: Input, cuesheet_id: UUID, user_id: UUID | None = None) -> Output:
    # find
    found = await CuesheetRepository.get_by_id(
        session=session,
        id=cuesheet_id,
    )

    # guard
    # manager 둘이 동시에 눌러도 큐가 두 칸 뛰지 않게 한다
    if str(found.current_cue_id) != input.expected_cue_id or found.ended_at is not None:
        return Output(data=found.to_dict(), event=[])

    current = await CueRepository.get_by_id(
        session=session,
        id=found.current_cue_id,
        cuesheet_id=cuesheet_id,
    )
    next_cue = await CueRepository.find_next(
        session=session,
        cuesheet_id=cuesheet_id,
        seq=current.seq,
    )

    # advance
    now = datetime.now(timezone.utc)
    advanced = (
        found.advance(next_cue_id=next_cue.id, at=CueStartedAt.from_datetime(now))
        if next_cue is not None
        else found.end(at=EndedAt.from_datetime(now))
    )

    event, cuesheet = CuesheetEvent.updated(
        cuesheet=(
            await CuesheetRepository.update(
                session=session,
                entity=advanced,
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
                    name="cuesheet_advance",
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
    parser.add_argument("--expected-cue-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await advance(
                session=session,
                event_group_id=uuid4(),
                input=Input(expected_cue_id=args.expected_cue_id),
                cuesheet_id=UUID(args.cuesheet_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
