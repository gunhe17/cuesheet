from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from cuesheet.api.bin.server import app
from cuesheet.api.config import get_auth_config


# #
# fixture

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        yield client


async def _register(client, login_id: str, pin: str = "1234") -> None:
    await client.post("/users", json={"login_id": login_id, "name": login_id, "pin": pin})


async def _login(client, login_id: str, pin: str):
    return await client.post("/users/session", json={"login_id": login_id, "pin": pin})


# #
# lockout

@pytest.mark.asyncio
async def test_wrong_pin_locks_after_five_attempts(client):
    await _register(client, "lock_target")
    limit = get_auth_config().LOGIN_MAX_ATTEMPTS

    # 1..4 회는 자격증명 오류
    for _ in range(limit - 1):
        response = await _login(client, "lock_target", "0000")
        assert response.status_code == 401

    # 5회째에도 401 이지만 여기서 잠긴다
    assert (await _login(client, "lock_target", "0000")).status_code == 401

    # 이후는 올바른 PIN 이어도 429
    locked = await _login(client, "lock_target", "1234")
    assert locked.status_code == 429


@pytest.mark.asyncio
async def test_failure_count_survives_the_rejection(client):
    # 실패 누적이 요청 롤백을 타면 카운터가 0 으로 돌아가 영원히 안 잠긴다
    await _register(client, "lock_persist")
    limit = get_auth_config().LOGIN_MAX_ATTEMPTS

    for _ in range(limit):
        await _login(client, "lock_persist", "9999")

    assert (await _login(client, "lock_persist", "1234")).status_code == 429


@pytest.mark.asyncio
async def test_success_resets_the_counter(client):
    await _register(client, "lock_reset")
    limit = get_auth_config().LOGIN_MAX_ATTEMPTS

    for _ in range(limit - 1):
        await _login(client, "lock_reset", "0000")

    assert (await _login(client, "lock_reset", "1234")).status_code == 200

    # 카운터가 살아 있었다면 다음 실패 한 번에 잠긴다
    for _ in range(limit - 1):
        assert (await _login(client, "lock_reset", "0000")).status_code == 401
    assert (await _login(client, "lock_reset", "1234")).status_code == 200
