from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.cuesheet.cuesheet import Cuesheet
from cuesheet.api.domain.cuesheet.cuesheet_title import CuesheetTitle
from cuesheet.api.domain.cuesheet.scheduled_at import ScheduledAt
from cuesheet.api.domain.cuesheet.invite_token import InviteToken
from cuesheet.api.domain.cuesheet.cuesheet_repository import CuesheetRepository
from cuesheet.api.domain.cuesheet.cuesheet_event import CuesheetEvent

from cuesheet.api.domain.participant.participant import Participant
from cuesheet.api.domain.participant.can_advance import CanAdvance
from cuesheet.api.domain.participant.role_ids import RoleIds
from cuesheet.api.domain.participant.participant_repository import ParticipantRepository
from cuesheet.api.domain.participant.participant_event import ParticipantEvent

from cuesheet.api.domain.event.event.event_repository import EventRepository

from cuesheet.api.infrastructure.token.secrets.client import token
from cuesheet.api.infrastructure.database.postgresql.client import db_client
from cuesheet.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    title: str
    scheduled_at: datetime


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def create(*, session, event_group_id, input: Input, user_id: UUID) -> Output:
    # create
    # 초대 토큰은 링크로 다시 꺼내 써야 해서 단방향 해싱하지 않는다
    manager_token = token.generate()
    viewer_token = token.generate()

    cuesheet_event, cuesheet = CuesheetEvent.created(
        cuesheet=(
            await CuesheetRepository.add(
                session=session,
                entity=Cuesheet.new(
                    owner_user_id=user_id,
                    title=CuesheetTitle.from_str(input.title),
                    scheduled_at=ScheduledAt.from_datetime(input.scheduled_at),
                    manager_token=InviteToken.from_str(manager_token),
                    viewer_token=InviteToken.from_str(viewer_token),
                ),
            )
        )
    )

    # join
    participant_event, _ = ParticipantEvent.created(
        participant=(
            await ParticipantRepository.add_unique_by_cuesheet_and_user(
                session=session,
                entity=Participant.new(
                    cuesheet_id=cuesheet.id,
                    user_id=user_id,
                    can_advance=CanAdvance.from_bool(True),
                    role_ids=RoleIds.from_json([]),
                ),
            )
        )
    )

    # return
    return Output(
        data={
            **cuesheet.to_dict(),
            "manager_token": manager_token,
            "viewer_token": viewer_token,
        },
        event=[
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="cuesheet_create",
                    atomics=[cuesheet_event, participant_event],
                    actor_user_id=user_id,
                )
            )
        ],
    )


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--scheduled-at", required=True)
    parser.add_argument("--user-id", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await create(
                session=session,
                event_group_id=uuid4(),
                input=Input(
                    title=args.title,
                    scheduled_at=datetime.fromisoformat(args.scheduled_at),
                ),
                user_id=UUID(args.user_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
