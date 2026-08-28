from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from cuesheet.api.usecase import user_register
from cuesheet.api.usecase import user_login
from cuesheet.api.usecase import cuesheet_create
from cuesheet.api.usecase import role_create
from cuesheet.api.usecase import cue_create
from cuesheet.api.usecase import task_create
from cuesheet.api.usecase import participant_join

from cuesheet.api.infrastructure.database.postgresql.client import db_client
from cuesheet.api.infrastructure.database.common.session import transactional_session


# #
# fixture

PIN = "1234"

USERS = [
    {"login_id": "choi", "name": "최유진", "role": "manager"},
    {"login_id": "kim", "name": "김하늘", "role": "camera"},
    {"login_id": "park", "name": "박도윤", "role": "light"},
]

ROLES = ["카메라", "조명", "음향", "자막"]

CUES = [
    {"color": "amber", "title": "오프닝 타이틀 VCR", "planned_sec": 35,
     "tasks": [("자막", "타이틀 CG 송출", "페이드인 15프레임")]},
    {"color": "rose", "title": "MC 오프닝", "planned_sec": 130,
     "tasks": [("카메라", "1번 스탠바이", "스탠딩"), ("음향", "MC 핀마이크 오픈", None)]},
    {"color": "teal", "title": "1위 후보 소개 CG", "planned_sec": 50,
     "tasks": [("자막", "CG-04 송출", None)]},
    {"color": "blue", "title": "무대 ① 아티스트 A", "planned_sec": 200,
     "tasks": [("카메라", "4번 지미집 · 6번 크레인", "인트로 8초 후 전환"),
               ("조명", "무대 프리셋 A", None),
               ("음향", "MR 큐", None)]},
    {"color": "rose", "title": "MC 브릿지", "planned_sec": 65,
     "tasks": [("카메라", "1번 고정", None)]},
    {"color": "blue", "title": "무대 ② 아티스트 B", "planned_sec": 225,
     "tasks": [("카메라", "3번 · 5번", None), ("조명", "무대 프리셋 B", None)]},
    {"color": "violet", "title": "광고", "planned_sec": 90, "tasks": []},
    {"color": "amber", "title": "주간 차트 코너", "planned_sec": 240,
     "tasks": [("자막", "차트 CG 순차 송출", "10위부터"), ("음향", "BGM 페이드", None)]},
    {"color": "blue", "title": "무대 ③ 아티스트 C", "planned_sec": 210,
     "tasks": [("카메라", "4번 · 6번", None), ("조명", "무대 프리셋 C", None)]},
    {"color": "rose", "title": "1위 발표", "planned_sec": 135,
     "tasks": [("카메라", "1번 · 3번", "꽃가루 타이밍"), ("조명", "풀업", None)]},
    {"color": "rose", "title": "엔딩", "planned_sec": 60,
     "tasks": [("음향", "엔딩 BGM", None)]},
]

JOINS = [
    {"login_id": "kim", "roles": ["카메라"]},
    {"login_id": "park", "roles": ["조명", "음향"]},
]


# #
# seed

async def seed(*, session, minutes: int) -> dict:
    # user
    users = {}
    for fixture in USERS:
        users[fixture["login_id"]] = await _register_or_login(
            session=session,
            login_id=fixture["login_id"],
            name=fixture["name"],
        )

    owner_id = UUID(users["choi"]["id"])

    # cuesheet
    created = await cuesheet_create.create(
        session=session,
        event_group_id=uuid4(),
        input=cuesheet_create.Input(
            title="뮤직 스테이지",
            scheduled_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
        ),
        user_id=owner_id,
    )
    cuesheet = created.data
    cuesheet_id = UUID(cuesheet["id"])

    # role
    roles = {}
    for name in ROLES:
        role = await role_create.create(
            session=session,
            event_group_id=uuid4(),
            input=role_create.Input(name=name),
            cuesheet_id=cuesheet_id,
            user_id=owner_id,
        )
        roles[name] = role.data["id"]

    # cue + task
    for index, fixture in enumerate(CUES, start=1):
        cue = await cue_create.create(
            session=session,
            event_group_id=uuid4(),
            input=cue_create.Input(
                seq=index,
                title=fixture["title"],
                planned_sec=fixture["planned_sec"],
                color=fixture["color"],
            ),
            cuesheet_id=cuesheet_id,
            user_id=owner_id,
        )
        for role_name, instruction, note in fixture["tasks"]:
            await task_create.create(
                session=session,
                event_group_id=uuid4(),
                input=task_create.Input(
                    cue_id=cue.data["id"],
                    role_id=roles[role_name],
                    instruction=instruction,
                    note=note,
                ),
                cuesheet_id=cuesheet_id,
                user_id=owner_id,
            )

    # participant
    for fixture in JOINS:
        await participant_join.join(
            session=session,
            event_group_id=uuid4(),
            input=participant_join.Input(
                invite_token=cuesheet["viewer_token"],
                role_ids=[roles[name] for name in fixture["roles"]],
            ),
            cuesheet_id=cuesheet_id,
            user_id=UUID(users[fixture["login_id"]]["id"]),
        )

    return {
        "cuesheet_id": str(cuesheet_id),
        "manager_token": cuesheet["manager_token"],
        "viewer_token": cuesheet["viewer_token"],
    }


# 여러 번 돌려도 되게 — 이미 있는 계정이면 로그인으로 대체한다
async def _register_or_login(*, session, login_id: str, name: str) -> dict:
    try:
        registered = await user_register.register(
            session=session,
            event_group_id=uuid4(),
            input=user_register.Input(login_id=login_id, name=name, pin=PIN),
        )
        return registered.data
    except Exception:
        logged_in = await user_login.login(
            session=session,
            event_group_id=uuid4(),
            input=user_login.Input(login_id=login_id, pin=PIN),
        )
        return logged_in.data


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=1)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    await db_client.create_tables_once_in_process()
    async with transactional_session(db_client.SessionLocal) as session:
        result = await seed(session=session, minutes=args.minutes)

    print()
    print(f"  cuesheet   {result['cuesheet_id']}")
    print(f"  manager    {result['manager_token']}")
    print(f"  viewer     {result['viewer_token']}")
    print()
    for fixture in USERS:
        print(f"  {fixture['login_id']:6} / {PIN}   {fixture['name']}")
    print()

if __name__ == "__main__":
    asyncio.run(_main())
