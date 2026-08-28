from __future__ import annotations

from sqlalchemy import text


# #
# row-level security

TENANT_SETTING = "app.current_cuesheet"

# cuesheets·users·participants 는 제외한다. AuthorizeParticipant 가 스코프를 걸기 전에
# participants 를 읽어 멤버십을 확인해야 해서, RLS 를 걸면 자기 자신을 못 읽는다
_TENANT_COLUMNS = {
    "roles": "cuesheet_id",
    "cues": "cuesheet_id",
    "tasks": "cuesheet_id",
    "atomic_events": "actor_cuesheet_id",
}


def _predicate(column: str) -> str:
    # NULL setting ↔ NULL row 만 통과 — 미설정 시 전체 노출(fail-open) 차단.
    # nullif 필수 — set_config 를 한 번 쓴 커넥션은 스코프가 풀린 뒤 NULL 이 아니라 '' 를 돌려주고,
    # ''::uuid 는 캐스팅 오류다. 풀링된 커넥션이 재사용될 때 터진다
    return (
        f"{column} IS NOT DISTINCT FROM "
        f"nullif(current_setting('{TENANT_SETTING}', true), '')::uuid"
    )


def apply_rls(conn) -> None:
    for table, column in _TENANT_COLUMNS.items():
        predicate = _predicate(column)
        conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
        conn.execute(text(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({predicate}) WITH CHECK ({predicate})"
        ))
