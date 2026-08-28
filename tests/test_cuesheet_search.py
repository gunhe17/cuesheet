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


async def _cuesheet(client, headers: dict, title: str, minutes: int) -> dict:
    at = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
    response = await client.post("/cuesheets", headers=headers, json={"title": title, "scheduled_at": at})
    return response.json()["data"]


# #
# search

@pytest.mark.asyncio
async def test_lists_only_my_cuesheets(client):
    mine = await _user(client, "search_mine")
    other = await _user(client, "search_other")

    await _cuesheet(client, mine, "내 행사 A", 10)
    await _cuesheet(client, mine, "내 행사 B", 20)
    await _cuesheet(client, other, "남의 행사", 30)

    listed = (await client.get("/cuesheets", headers=mine)).json()["data"]

    assert [row["title"] for row in listed] == ["내 행사 B", "내 행사 A"]


@pytest.mark.asyncio
async def test_joined_cuesheet_appears(client):
    owner = await _user(client, "search_owner")
    guest = await _user(client, "search_guest")

    cuesheet = await _cuesheet(client, owner, "초대받은 행사", 40)

    assert (await client.get("/cuesheets", headers=guest)).json()["data"] == []

    await client.post(
        f"/cuesheets/{cuesheet['id']}/participants",
        headers=guest,
        json={"invite_token": cuesheet["viewer_token"], "role_ids": []},
    )

    listed = (await client.get("/cuesheets", headers=guest)).json()["data"]
    assert [row["title"] for row in listed] == ["초대받은 행사"]
    assert listed[0]["can_advance"] is False


@pytest.mark.asyncio
async def test_creator_is_manager_in_the_list(client):
    owner = await _user(client, "search_creator")
    await _cuesheet(client, owner, "내가 만든 행사", 50)

    listed = (await client.get("/cuesheets", headers=owner)).json()["data"]

    assert listed[0]["can_advance"] is True
    assert listed[0]["participant_id"]


@pytest.mark.asyncio
async def test_invite_tokens_are_not_listed(client):
    owner = await _user(client, "search_token")
    await _cuesheet(client, owner, "토큰 노출 확인", 60)

    listed = (await client.get("/cuesheets", headers=owner)).json()["data"]

    assert "manager_token" not in listed[0]
    assert "viewer_token" not in listed[0]


@pytest.mark.asyncio
async def test_records_the_creator_as_owner(client):
    owner = await _user(client, "search_owner_col")
    guest = await _user(client, "search_guest_col")

    cuesheet = await _cuesheet(client, owner, "소유자 기록", 70)
    await client.post(
        f"/cuesheets/{cuesheet['id']}/participants",
        headers=guest,
        json={"invite_token": cuesheet["viewer_token"], "role_ids": []},
    )

    mine = (await client.get("/cuesheets", headers=owner)).json()["data"][0]
    theirs = (await client.get("/cuesheets", headers=guest)).json()["data"][0]

    # 합류자에게도 같은 owner 가 보인다 — 소유는 참여와 별개다
    assert mine["owner_user_id"] == theirs["owner_user_id"]
    assert mine["owner_user_id"] == cuesheet["owner_user_id"]


@pytest.mark.asyncio
async def test_requires_authentication(client):
    assert (await client.get("/cuesheets")).status_code == 401
