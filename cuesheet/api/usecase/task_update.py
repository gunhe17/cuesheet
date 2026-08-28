from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.task.instruction import Instruction
from cuesheet.api.domain.task.note import Note
from cuesheet.api.domain.task.task_repository import TaskRepository
from cuesheet.api.domain.task.task_event import TaskEvent

from cuesheet.api.domain.event.event.event_repository import EventRepository

from cuesheet.api.infrastructure.database.postgresql.client import db_client
from cuesheet.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    id: str
    instruction: str | None = None
    note: str | None = None


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def update(*, session, event_group_id, input: Input, cuesheet_id: UUID, user_id: UUID | None = None) -> Output:
    # find
    found = await TaskRepository.get_by_id(
        session=session,
        id=UUID(input.id),
        cuesheet_id=cuesheet_id,
    )
    updated = found

    # update
    if input.instruction is not None:
        updated = updated.with_instruction(Instruction.from_str(input.instruction))
    if input.note is not None:
        updated = updated.with_note(Note.from_str(input.note))

    # persist
    event, task = TaskEvent.updated(
        task=(
            await TaskRepository.update(
                session=session,
                entity=updated,
            )
        )
    )

    # return
    return Output(
        data=task.to_dict(),
        event=[
            emitted.to_dict()
            for emitted in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="task_update",
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
    parser.add_argument("--instruction")
    parser.add_argument("--note")
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await update(
                session=session,
                event_group_id=uuid4(),
                input=Input(id=args.id, instruction=args.instruction, note=args.note),
                cuesheet_id=UUID(args.cuesheet_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
