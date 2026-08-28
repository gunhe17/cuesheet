from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

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
    id: str
    seq: int | None = None
    title: str | None = None
    planned_sec: int | None = None
    color: str | None = None


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def update(*, session, event_group_id, input: Input, cuesheet_id: UUID, user_id: UUID | None = None) -> Output:
    # find
    found = await CueRepository.get_by_id(
        session=session,
        id=UUID(input.id),
        cuesheet_id=cuesheet_id,
    )
    updated = found

    # update
    if input.seq is not None:
        updated = updated.with_seq(Seq.from_int(input.seq))
    if input.title is not None:
        updated = updated.with_title(CueTitle.from_str(input.title))
    if input.planned_sec is not None:
        updated = updated.with_planned_sec(PlannedSec.from_int(input.planned_sec))
    if input.color is not None:
        updated = updated.with_color(Color.from_str(input.color))

    # persist
    event, cue = CueEvent.updated(
        cue=(
            await CueRepository.update_unique_by_seq(
                session=session,
                entity=updated,
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
                    name="cue_update",
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
    parser.add_argument("--seq", type=int)
    parser.add_argument("--title")
    parser.add_argument("--planned-sec", type=int)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await update(
                session=session,
                event_group_id=uuid4(),
                input=Input(
                    id=args.id,
                    seq=args.seq,
                    title=args.title,
                    planned_sec=args.planned_sec,
                ),
                cuesheet_id=UUID(args.cuesheet_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
