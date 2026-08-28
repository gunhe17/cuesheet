from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from cuesheet.api.core.usecase import In
from cuesheet.api.core.usecase import Out
from cuesheet.api.core.validate import typecheck

from cuesheet.api.domain.cuesheet.cuesheet import Cuesheet
from cuesheet.api.domain.cuesheet.cuesheet_repository import CuesheetRepository
from cuesheet.api.domain.cuesheet.cuesheet_event import CuesheetEvent

from cuesheet.api.domain.cue.cue_repository import CueRepository
from cuesheet.api.domain.role.role_repository import RoleRepository
from cuesheet.api.domain.task.task_repository import TaskRepository
from cuesheet.api.domain.participant.participant_repository import ParticipantRepository
from cuesheet.api.domain.user.user_repository import UserRepository

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
async def get(*, session, event_group_id, input: Input, cuesheet_id: UUID, user_id: UUID | None = None) -> Output:
    # find
    event, cuesheet = CuesheetEvent.read(
        cuesheet=(
            await CuesheetRepository.get_by_id(
                session=session,
                id=cuesheet_id,
            )
        )
    )
    cues = await CueRepository.filter_by_cuesheet_id(
        session=session,
        cuesheet_id=cuesheet_id,
    )
    roles = await RoleRepository.filter_by_cuesheet_id(
        session=session,
        cuesheet_id=cuesheet_id,
    )
    tasks = await TaskRepository.filter_by_cuesheet_id(
        session=session,
        cuesheet_id=cuesheet_id,
    )
    participants = await ParticipantRepository.filter_by_cuesheet_id(
        session=session,
        cuesheet_id=cuesheet_id,
    )
    users = await UserRepository.find_by_ids(
        session=session,
        ids=[participant.user_id for participant in participants],
    )

    # schedule
    scheduled = _schedule(
        cuesheet=cuesheet,
        cues=cues,
        now=datetime.now(timezone.utc),
    )

    # return
    return Output(
        data={
            "cuesheet": {**cuesheet.to_dict(), "delay_sec": scheduled["delay_sec"]},
            "cues": [
                {
                    **cue.to_dict(),
                    "eta": scheduled["eta"][str(cue.id)],
                    "tasks": [
                        task.to_dict() for task in tasks if task.cue_id == cue.id
                    ],
                }
                for cue in cues
            ],
            "roles": [
                role.to_dict() for role in roles
            ],
            "participants": _participants(participants=participants, users=users),
            "me": _me(participants=participants, user_id=user_id),
        },
        event=[
            emitted.to_dict()
            for emitted in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="cuesheet_get",
                    atomics=[event],
                    actor_user_id=user_id,
                    actor_cuesheet_id=cuesheet_id,
                )
            )
        ],
    )


# #
# schedule

def _schedule(*, cuesheet: Cuesheet, cues: list, now: datetime) -> dict:
    # 진행중이면 현재 큐 시작 시각이, 준비중/종료면 예정 시각이 기준
    running = (
        cuesheet.current_cue_id is not None and cuesheet.ended_at is None
    )
    current_index = next(
        (index for index, cue in enumerate(cues) if cue.id == cuesheet.current_cue_id),
        None,
    )

    # delay
    delay_sec = 0
    if running and current_index is not None and cuesheet.cue_started_at is not None:
        elapsed = (now - cuesheet.cue_started_at.to_datetime()).total_seconds()
        delay_sec = max(0, int(elapsed - cues[current_index].planned_sec.to_int()))

    # eta
    if running and current_index is not None and cuesheet.cue_started_at is not None:
        cursor = cuesheet.cue_started_at.to_datetime() + timedelta(seconds=delay_sec)
        start_index = current_index
    else:
        cursor = cuesheet.scheduled_at.to_datetime()
        start_index = 0

    eta = {}
    for index, cue in enumerate(cues):
        if index < start_index:
            eta[str(cue.id)] = None
            continue
        eta[str(cue.id)] = cursor.isoformat()
        cursor = cursor + timedelta(seconds=cue.planned_sec.to_int())

    return {
        "delay_sec": delay_sec,
        "eta": eta,
    }


# #
# participant

def _participants(*, participants: list, users: list) -> list:
    names = {user.id: user.name.to_str() for user in users}
    return [
        {
            "id": str(participant.id),
            "user_id": str(participant.user_id),
            "name": names.get(participant.user_id),
            "can_advance": participant.can_advance.to_bool(),
            "role_ids": participant.role_ids.to_json(),
        }
        for participant in participants
    ]


def _me(*, participants: list, user_id: UUID | None) -> dict | None:
    mine = next(
        (participant for participant in participants if participant.user_id == user_id),
        None,
    )
    if mine is None:
        return None

    return {
        "participant_id": str(mine.id),
        "can_advance": mine.can_advance.to_bool(),
        "role_ids": mine.role_ids.to_json(),
    }


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
            await get(
                session=session,
                event_group_id=uuid4(),
                input=Input(),
                cuesheet_id=UUID(args.cuesheet_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
