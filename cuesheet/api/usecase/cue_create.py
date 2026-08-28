from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.cue.cue import Cue
from cuesheet.api.domain.cue.seq import Seq
from cuesheet.api.domain.cue.cue_title import CueTitle
from cuesheet.api.domain.cue.planned_sec import PlannedSec
from cuesheet.api.domain.cue.color import Color
from cuesheet.api.domain.cue.cue_repository import CueRepository
from cuesheet.api.domain.cue.cue_event import CueEvent

from cuesheet.api.domain.event.event.event_repository import EventRepository

from cuesheet.api.infrastructure.database.postgresql.client import db_client
from cuesheet.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    seq: int
    title: str
    planned_sec: int
    color: str | None = None


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def create(*, session, event_group_id, input: Input, cuesheet_id: UUID, user_id: UUID | None = None) -> Output:
    # persist
    event, cue = CueEvent.created(
        cue=(
            await CueRepository.add_unique_by_seq(
                session=session,
                entity=Cue.new(
                    cuesheet_id=cuesheet_id,
                    seq=Seq.from_int(input.seq),
                    title=CueTitle.from_str(input.title),
                    planned_sec=PlannedSec.from_int(input.planned_sec),
                    color=(
                        Color.from_str(input.color) if input.color else Color.default()
                    ),
                ),
            )
        )
    )

    # return
    return Output(
        data=cue.to_dict(),
        event=[
            emitted.to_dict()
            for emitted in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="cue_create",
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
    parser.add_argument("--seq", required=True, type=int)
    parser.add_argument("--title", required=True)
    parser.add_argument("--planned-sec", required=True, type=int)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await create(
                session=session,
                event_group_id=uuid4(),
                input=Input(
                    seq=args.seq,
                    title=args.title,
                    planned_sec=args.planned_sec,
                ),
                cuesheet_id=UUID(args.cuesheet_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
