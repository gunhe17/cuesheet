from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.common.exception import ForbiddenError

from cuesheet.api.domain.task.done_at import DoneAt
from cuesheet.api.domain.task.task_repository import TaskRepository
from cuesheet.api.domain.task.task_event import TaskEvent

from cuesheet.api.domain.event.event.event_repository import EventRepository

from cuesheet.api.infrastructure.database.postgresql.client import db_client
from cuesheet.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    id: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def check(
    *,
    session,
    event_group_id,
    input: Input,
    cuesheet_id: UUID,
    participant_id: UUID,
    can_advance: bool = False,
    role_ids: list | None = None,
    user_id: UUID | None = None,
) -> Output:
    # find
    found = await TaskRepository.get_by_id(
        session=session,
        id=UUID(input.id),
        cuesheet_id=cuesheet_id,
    )

    # guard
    if not can_advance and str(found.role_id) not in (role_ids or []):
        raise ForbiddenError("Task")

    # persist
    event, task = TaskEvent.updated(
        task=(
            await TaskRepository.update(
                session=session,
                entity=found.check(
                    at=DoneAt.from_datetime(datetime.now(timezone.utc)),
                    participant_id=participant_id,
                ),
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
                    name="task_check",
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
    parser.add_argument("--participant-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await check(
                session=session,
                event_group_id=uuid4(),
                input=Input(id=args.id),
                cuesheet_id=UUID(args.cuesheet_id),
                participant_id=UUID(args.participant_id),
                can_advance=True,
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
