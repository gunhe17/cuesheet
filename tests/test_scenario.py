from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from cuesheet.api.bin.server import app


# #
# fixture

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        yield client


# #
# scenario — 행사 하루

@pytest.mark.asyncio
async def test_runs_an_event_from_setup_to_end(client):
    director = await _join_service(client, "day_director", "김총괄")
    sound = await _join_service(client, "day_sound", "박음향")

    # 총괄이 큐시트를 짠다
    show = await _create(client, director, "정기공연")
    roles = await _roles(client, director, show, ["음향", "조명"])
    cues = await _cues(client, director, show, [("개회", 300), ("인사말", 600), ("폐회", 180)])
    opening = await _task(client, director, show, cues[0], roles["음향"], "오프닝 BGM")
    closing = await _task(client, director, show, cues[2], roles["음향"], "엔딩 BGM")

    # 음향 담당이 링크로 합류한다
    await _invite(client, sound, show, "viewer", [roles["음향"]])

    # 시작 전 — 예정 시각 기준으로 순서가 잡혀 있다
    before = await _read(client, sound, show)
    assert before["cuesheet"]["state"] == "ready"
    assert before["me"]["role_ids"] == [roles["음향"]]
    assert [cue["eta"] is not None for cue in before["cues"]] == [True, True, True]

    # 시작 — 첫 순서로 들어간다
    await _post(client, director, f"/cuesheets/{show}/run")
    running = await _read(client, sound, show)
    assert running["cuesheet"]["state"] == "running"
    assert running["cuesheet"]["current_cue_id"] == cues[0]

    # 담당자가 자기 todo 를 체크한다
    await _post(client, sound, f"/cuesheets/{show}/tasks/{opening}/check")
    checked = await _find_task(client, sound, show, opening)
    assert checked["done_at"] is not None
    assert checked["done_by_participant_id"] == running["me"]["participant_id"]

    # 총괄이 순서를 넘긴다
    await _advance(client, director, show, cues[0])
    await _advance(client, director, show, cues[1])
    assert (await _read(client, sound, show))["cuesheet"]["current_cue_id"] == cues[2]

    # 마지막 순서에서 넘기면 종료된다
    await _advance(client, director, show, cues[2])
    ended = await _read(client, sound, show)
    assert ended["cuesheet"]["state"] == "ended"
    assert ended["cuesheet"]["ended_at"] is not None

    # 안 한 일은 안 한 채로 남는다
    assert (await _find_task(client, sound, show, closing))["done_at"] is None


# #
# scenario — 총괄 둘이 동시에 누른다

@pytest.mark.asyncio
async def test_two_directors_pressing_next_advance_one_step(client):
    first = await _join_service(client, "race_first", "총괄1")
    second = await _join_service(client, "race_second", "총괄2")

    show = await _create(client, first, "동시 진행")
    cues = await _cues(client, first, show, [("하나", 60), ("둘", 60), ("셋", 60)])
    await _invite(client, second, show, "manager", [])
    await _post(client, first, f"/cuesheets/{show}/run")

    # 둘 다 같은 화면(1번 순서)을 보고 눌렀다
    await _advance(client, first, show, cues[0])
    stale = await _advance(client, second, show, cues[0])

    assert stale["current_cue_id"] == cues[1]
    # 늦은 쪽은 아무 일도 안 했으므로 기록도 없다
    assert stale is not None


@pytest.mark.asyncio
async def test_stale_press_records_no_event(client):
    director = await _join_service(client, "race_event", "총괄")
    show = await _create(client, director, "기록 확인")
    cues = await _cues(client, director, show, [("하나", 60), ("둘", 60)])
    await _post(client, director, f"/cuesheets/{show}/run")

    fresh = await _raw_advance(client, director, show, cues[0])
    stale = await _raw_advance(client, director, show, cues[0])

    assert len(fresh["event"]) == 1
    assert stale["event"] == []


# #
# scenario — 실수로 넘겼다

@pytest.mark.asyncio
async def test_rewind_returns_to_the_previous_cue_once(client):
    director = await _join_service(client, "rewind_director", "총괄")
    show = await _create(client, director, "되돌리기")
    cues = await _cues(client, director, show, [("하나", 60), ("둘", 60), ("셋", 60)])
    await _post(client, director, f"/cuesheets/{show}/run")

    await _advance(client, director, show, cues[0])
    await _advance(client, director, show, cues[1])

    back = await _rewind(client, director, show, cues[2])
    assert back["current_cue_id"] == cues[1]
    # 되돌릴 자리를 썼으므로 비운다 — 이게 "1단계만" 의 실체다
    assert back["prev_cue_id"] is None

    # 연달아 눌러도 더 안 간다
    again = await _rewind(client, director, show, cues[1])
    assert again["current_cue_id"] == cues[1]

    # 다시 넘기면 되돌릴 자리가 새로 생긴다
    forward = await _advance(client, director, show, cues[1])
    assert forward["prev_cue_id"] == cues[1]


# #
# scenario — 진행 중 편집

@pytest.mark.asyncio
async def test_editing_mid_event_shifts_later_etas(client):
    director = await _join_service(client, "edit_director", "총괄")
    show = await _create(client, director, "진행 중 편집")
    cues = await _cues(client, director, show, [("하나", 300), ("둘", 300), ("셋", 300)])
    await _post(client, director, f"/cuesheets/{show}/run")

    before = _eta(await _read(client, director, show), cues[2])

    # 2번 순서를 5분에서 15분으로 늘린다
    await _patch(client, director, f"/cuesheets/{show}/cues/{cues[1]}", {"planned_sec": 900})
    after = _eta(await _read(client, director, show), cues[2])

    assert (after - before).total_seconds() == 600


@pytest.mark.asyncio
async def test_appending_a_cue_mid_event(client):
    director = await _join_service(client, "append_director", "총괄")
    show = await _create(client, director, "순서 추가")
    cues = await _cues(client, director, show, [("하나", 60), ("둘", 60)])
    await _post(client, director, f"/cuesheets/{show}/run")

    await _cues(client, director, show, [("앙코르", 120)], start=3)
    listed = (await _read(client, director, show))["cues"]

    assert [cue["title"] for cue in listed] == ["하나", "둘", "앙코르"]
    assert listed[2]["eta"] is not None


@pytest.mark.asyncio
async def test_current_cue_cannot_be_deleted(client):
    director = await _join_service(client, "delete_director", "총괄")
    show = await _create(client, director, "삭제 거부")
    cues = await _cues(client, director, show, [("하나", 60), ("둘", 60)])
    await _post(client, director, f"/cuesheets/{show}/run")

    blocked = await client.delete(f"/cuesheets/{show}/cues/{cues[0]}", headers=director)
    assert blocked.status_code == 400

    # 진행 중이 아닌 순서는 지울 수 있다
    allowed = await client.delete(f"/cuesheets/{show}/cues/{cues[1]}", headers=director)
    assert allowed.status_code == 200


# #
# scenario — 권한 경계

@pytest.mark.asyncio
async def test_viewer_cannot_control_or_edit(client):
    director = await _join_service(client, "guard_director", "총괄")
    viewer = await _join_service(client, "guard_viewer", "담당")

    show = await _create(client, director, "권한")
    roles = await _roles(client, director, show, ["음향", "조명"])
    cues = await _cues(client, director, show, [("하나", 60)])
    others = await _task(client, director, show, cues[0], roles["조명"], "무대 풀업")
    await _invite(client, viewer, show, "viewer", [roles["음향"]])
    await _post(client, director, f"/cuesheets/{show}/run")

    denied = {
        "진행": await client.post(
            f"/cuesheets/{show}/run/advance", headers=viewer, json={"expected_cue_id": cues[0]}
        ),
        "순서 추가": await client.post(
            f"/cuesheets/{show}/cues", headers=viewer, json={"seq": 9, "title": "x", "planned_sec": 60}
        ),
        "역할 추가": await client.post(f"/cuesheets/{show}/roles", headers=viewer, json={"name": "영상"}),
        "제목 수정": await client.patch(f"/cuesheets/{show}", headers=viewer, json={"title": "x"}),
        "남의 todo": await client.post(f"/cuesheets/{show}/tasks/{others}/check", headers=viewer),
    }

    assert {label: response.status_code for label, response in denied.items()} == {
        "진행": 403,
        "순서 추가": 403,
        "역할 추가": 403,
        "제목 수정": 403,
        "남의 todo": 403,
    }


@pytest.mark.asyncio
async def test_director_can_check_any_role(client):
    director = await _join_service(client, "any_director", "총괄")
    show = await _create(client, director, "대신 체크")
    roles = await _roles(client, director, show, ["음향"])
    cues = await _cues(client, director, show, [("하나", 60)])
    task = await _task(client, director, show, cues[0], roles["음향"], "BGM")

    # 총괄은 음향 역할이 아니지만 무전으로 듣고 대신 누른다
    assert (await _read(client, director, show))["me"]["role_ids"] == []
    await _post(client, director, f"/cuesheets/{show}/tasks/{task}/check")

    assert (await _find_task(client, director, show, task))["done_at"] is not None


@pytest.mark.asyncio
async def test_promoting_a_viewer_grants_control(client):
    director = await _join_service(client, "promote_director", "총괄")
    viewer = await _join_service(client, "promote_viewer", "담당")

    show = await _create(client, director, "권한 승격")
    cues = await _cues(client, director, show, [("하나", 60), ("둘", 60)])
    await _invite(client, viewer, show, "viewer", [])
    await _post(client, director, f"/cuesheets/{show}/run")

    blocked = await client.post(
        f"/cuesheets/{show}/run/advance", headers=viewer, json={"expected_cue_id": cues[0]}
    )
    assert blocked.status_code == 403

    mine = (await _read(client, viewer, show))["me"]["participant_id"]
    await _patch(client, director, f"/cuesheets/{show}/participants/{mine}", {"can_advance": True})

    allowed = await client.post(
        f"/cuesheets/{show}/run/advance", headers=viewer, json={"expected_cue_id": cues[0]}
    )
    assert allowed.status_code == 200


# #
# scenario — 미완료를 남기고 넘어간다

@pytest.mark.asyncio
async def test_unchecked_tasks_never_block_or_autocomplete(client):
    director = await _join_service(client, "skip_director", "총괄")
    show = await _create(client, director, "미완료")
    roles = await _roles(client, director, show, ["음향"])
    cues = await _cues(client, director, show, [("하나", 60), ("둘", 60)])
    task = await _task(client, director, show, cues[0], roles["음향"], "안 할 일")

    await _post(client, director, f"/cuesheets/{show}/run")
    await _advance(client, director, show, cues[0])

    # 넘어갔지만 미완료로 남는다
    assert (await _find_task(client, director, show, task))["done_at"] is None


@pytest.mark.asyncio
async def test_uncheck_reverts_a_completed_task(client):
    director = await _join_service(client, "uncheck_director", "총괄")
    show = await _create(client, director, "체크 해제")
    roles = await _roles(client, director, show, ["음향"])
    cues = await _cues(client, director, show, [("하나", 60)])
    task = await _task(client, director, show, cues[0], roles["음향"], "실수로 체크")

    await _post(client, director, f"/cuesheets/{show}/tasks/{task}/check")
    await client.delete(f"/cuesheets/{show}/tasks/{task}/check", headers=director)

    reverted = await _find_task(client, director, show, task)
    assert reverted["done_at"] is None
    assert reverted["done_by_participant_id"] is None


# #
# scenario — 역할을 지운다

@pytest.mark.asyncio
async def test_deleting_a_role_leaves_the_cuesheet_readable(client):
    director = await _join_service(client, "role_director", "총괄")
    member = await _join_service(client, "role_member", "담당")

    show = await _create(client, director, "역할 삭제")
    roles = await _roles(client, director, show, ["음향"])
    cues = await _cues(client, director, show, [("하나", 60)])
    await _task(client, director, show, cues[0], roles["음향"], "BGM")
    await _invite(client, member, show, "viewer", [roles["음향"]])

    await client.delete(f"/cuesheets/{show}/roles/{roles['음향']}", headers=director)

    # role_ids 에 남은 id 는 필터에 안 걸릴 뿐 오류가 아니다
    after = await _read(client, member, show)
    assert after["roles"] == []
    assert after["me"]["role_ids"] == [roles["음향"]]


# #
# scenario — 종료된 행사

@pytest.mark.asyncio
async def test_ending_is_idempotent(client):
    director = await _join_service(client, "end_director", "총괄")
    show = await _create(client, director, "종료 멱등")
    cues = await _cues(client, director, show, [("하나", 60)])
    await _post(client, director, f"/cuesheets/{show}/run")

    first = await _post(client, director, f"/cuesheets/{show}/run/end")
    second = await _post(client, director, f"/cuesheets/{show}/run/end")

    assert first["ended_at"] == second["ended_at"]


# #
# helper — 서비스 가입

async def _join_service(client, login_id: str, name: str) -> dict:
    await client.post("/users", json={"login_id": login_id, "name": name, "pin": "1234"})
    response = await client.post("/users/session", json={"login_id": login_id, "pin": "1234"})
    return {"Authorization": f"Bearer {response.json()['data']['token']}"}


# #
# helper — 큐시트 구성

async def _create(client, headers: dict, title: str) -> str:
    at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    created = await _post(client, headers, "/cuesheets", {"title": title, "scheduled_at": at})
    _TOKENS[created["id"]] = created
    return created["id"]


async def _roles(client, headers: dict, show: str, names: list) -> dict:
    return {
        name: (await _post(client, headers, f"/cuesheets/{show}/roles", {"name": name}))["id"]
        for name in names
    }


async def _cues(client, headers: dict, show: str, plan: list, start: int = 1) -> list:
    return [
        (
            await _post(
                client,
                headers,
                f"/cuesheets/{show}/cues",
                {"seq": start + index, "title": title, "planned_sec": planned},
            )
        )["id"]
        for index, (title, planned) in enumerate(plan)
    ]


async def _task(client, headers: dict, show: str, cue: str, role: str, instruction: str) -> str:
    created = await _post(
        client,
        headers,
        f"/cuesheets/{show}/tasks",
        {"cue_id": cue, "role_id": role, "instruction": instruction},
    )
    return created["id"]


async def _invite(client, headers: dict, show: str, kind: str, role_ids: list) -> dict:
    return await _post(
        client,
        headers,
        f"/cuesheets/{show}/participants",
        {"invite_token": _TOKENS[show][f"{kind}_token"], "role_ids": role_ids},
    )


# #
# helper — 진행

async def _advance(client, headers: dict, show: str, expected: str) -> dict:
    return await _post(
        client, headers, f"/cuesheets/{show}/run/advance", {"expected_cue_id": expected}
    )


async def _rewind(client, headers: dict, show: str, expected: str) -> dict:
    return await _post(
        client, headers, f"/cuesheets/{show}/run/rewind", {"expected_cue_id": expected}
    )


async def _raw_advance(client, headers: dict, show: str, expected: str) -> dict:
    response = await client.post(
        f"/cuesheets/{show}/run/advance", headers=headers, json={"expected_cue_id": expected}
    )
    assert response.status_code == 200, response.text
    return response.json()


# #
# helper — 조회

async def _read(client, headers: dict, show: str) -> dict:
    response = await client.get(f"/cuesheets/{show}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def _find_task(client, headers: dict, show: str, task: str) -> dict:
    read = await _read(client, headers, show)
    return next(
        found
        for cue in read["cues"]
        for found in cue["tasks"]
        if found["id"] == task
    )


def _eta(read: dict, cue: str) -> datetime:
    return datetime.fromisoformat(
        next(found for found in read["cues"] if found["id"] == cue)["eta"]
    )


# #
# helper — 전송

_TOKENS: dict = {}


async def _post(client, headers: dict, path: str, body: dict | None = None) -> dict:
    response = await client.post(path, headers=headers, json=body)
    assert response.status_code == 200, f"{path} -> {response.status_code} {response.text}"
    return response.json()["data"]


async def _patch(client, headers: dict, path: str, body: dict) -> dict:
    response = await client.patch(path, headers=headers, json=body)
    assert response.status_code == 200, f"{path} -> {response.status_code} {response.text}"
    return response.json()["data"]
