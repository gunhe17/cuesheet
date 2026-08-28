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


async def _user(client, login_id: str) -> dict:
    await client.post("/users", json={"login_id": login_id, "name": login_id, "pin": "1111"})
    response = await client.post("/users/session", json={"login_id": login_id, "pin": "1111"})
    return {"Authorization": f"Bearer {response.json()['data']['token']}"}


async def _cuesheet(client, headers: dict, title: str) -> dict:
    at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    response = await client.post("/cuesheets", headers=headers, json={"title": title, "scheduled_at": at})
    return response.json()["data"]


# #
# isolation

@pytest.mark.asyncio
async def test_cue_of_other_cuesheet_is_invisible(client):
    # 같은 사용자가 큐시트 둘을 만들고 각각에 큐를 넣는다
    headers = await _user(client, "isolation_owner")

    first = await _cuesheet(client, headers, "행사 A")
    second = await _cuesheet(client, headers, "행사 B")

    created = await client.post(
        f"/cuesheets/{first['id']}/cues",
        headers=headers,
        json={"seq": 1, "title": "A의 순서", "planned_sec": 60},
    )
    cue_id = created.json()["data"]["id"]

    # B 의 스코프로는 A 의 큐가 보이지 않는다
    leaked = await client.get(f"/cuesheets/{second['id']}", headers=headers)
    assert [cue["id"] for cue in leaked.json()["data"]["cues"]] == []

    # B 의 스코프로 A 의 큐를 직접 지목해도 404
    denied = await client.delete(f"/cuesheets/{second['id']}/cues/{cue_id}", headers=headers)
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_non_participant_is_forbidden(client):
    owner = await _user(client, "isolation_owner2")
    stranger = await _user(client, "isolation_stranger")

    cuesheet = await _cuesheet(client, owner, "남의 행사")

    response = await client.get(f"/cuesheets/{cuesheet['id']}", headers=stranger)
    assert response.status_code == 403
