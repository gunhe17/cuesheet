from __future__ import annotations

import argparse
import asyncio
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.common.exception import InvalidError

from cuesheet.api.domain.cuesheet.cuesheet_repository import CuesheetRepository

from cuesheet.api.domain.cue.cue_repository import CueRepository
from cuesheet.api.domain.cue.cue_event import CueEvent

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
async def delete(*, session, event_group_id, input: Input, cuesheet_id: UUID, user_id: UUID | None = None) -> Output:
    # find
    cuesheet = await CuesheetRepository.get_by_id(
        session=session,
        id=cuesheet_id,
    )

    # guard
    # 권한 문제가 아니라 잘못된 요청이라 ForbiddenError 가 아니다
    if str(cuesheet.current_cue_id) == input.id:
        raise InvalidError("Cue")

    # persist
    event, cue = CueEvent.deleted(
        cue=(
            await CueRepository.remove_by_id(
                session=session,
                id=(
                    await CueRepository.get_by_id(
                        session=session,
                        id=UUID(input.id),
                        cuesheet_id=cuesheet_id,
                    )
                ).id,
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
                    name="cue_delete",
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
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await delete(
                session=session,
                event_group_id=uuid4(),
                input=Input(id=args.id),
                cuesheet_id=UUID(args.cuesheet_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
