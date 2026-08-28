from __future__ import annotations

import os
from pathlib import Path


# #
# env

# usecase 모듈이 CLI 섹션 때문에 import 시점에 db_client 를 만든다 — 환경변수가 먼저 있어야 한다
def _load_env() -> None:
    path = Path(__file__).resolve().parent.parent / ".env" / ".env.develop"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key, value)


_load_env()

# 전용 test DB — dev DB 를 쓰면 앞선 실행이 남긴 행이 다음 실행을 오염시킨다
os.environ["APP_ENV"] = "test"
os.environ["TEST_POSTGRES_HOST"] = os.environ.get("PYTEST_POSTGRES_HOST", "127.0.0.1")
os.environ["TEST_POSTGRES_CONTAINER_PORT"] = os.environ["TEST_POSTGRES_PORT"]

OWNER_USER = os.environ["TEST_POSTGRES_USER"]
OWNER_PASSWORD = os.environ["TEST_POSTGRES_PASSWORD"]

# 앱은 BYPASSRLS 없는 롤로 붙는다 — 소유자로 붙으면 RLS 가 통째로 무시돼 격리 회귀를 못 잡는다
APP_ROLE = "app_test"
APP_PASSWORD = "app_test_pw"
os.environ["TEST_POSTGRES_USER"] = APP_ROLE
os.environ["TEST_POSTGRES_PASSWORD"] = APP_PASSWORD


import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from cuesheet.api.config import TestPostgresConfig  # noqa: E402
from cuesheet.api.infrastructure.database.postgresql.client import Postgres, db_client  # noqa: E402


# #
# role

_DROP_ROLE = f"""
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
        EXECUTE 'DROP OWNED BY {APP_ROLE}';
        EXECUTE 'DROP ROLE {APP_ROLE}';
    END IF;
END $$;
"""

# asyncpg 는 한 execute 에 여러 문장을 못 넣는다 — 문장마다 나눈다
_CREATE_ROLE = [
    f"CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{APP_PASSWORD}'",
    f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}",
    f"GRANT ALL ON ALL TABLES IN SCHEMA public TO {APP_ROLE}",
    f"GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}",
]


def _owner() -> Postgres:
    config = TestPostgresConfig()
    return Postgres(
        f"postgresql+asyncpg://{OWNER_USER}:{OWNER_PASSWORD}"
        f"@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
    )


# #
# schema

@pytest.fixture(scope="session", autouse=True)
async def schema():
    owner = _owner()

    # DDL 은 소유자로 — 앱 롤은 테이블을 만들 권한이 없다
    async with owner.engine.begin() as connection:
        await connection.execute(text(_DROP_ROLE))
    await owner.delete_tables()
    Postgres._tables_created = False
    await owner.create_tables_once_in_process()
    async with owner.engine.begin() as connection:
        for statement in _CREATE_ROLE:
            await connection.execute(text(statement))

    yield

    await db_client.close()
    async with owner.engine.begin() as connection:
        await connection.execute(text(_DROP_ROLE))
    await owner.delete_tables()
    await owner.close()
