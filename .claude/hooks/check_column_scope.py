#!/usr/bin/env python3
"""column-scope.md 이름 대 info 일관성 검사. Base.metadata 를 introspect 한다."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cuesheet.api.domain  # noqa: F401
from cuesheet.api.core.model import Base


AXES = {"team", "account", "org"}


def check() -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    tables = Base.metadata.tables

    for name, table in sorted(tables.items()):
        scope_cols = [
            (c.name, c.info["scope"], c.primary_key)
            for c in table.columns
            if c.info.get("scope")
        ]

        # completeness
        if not scope_cols and table.info.get("scope") != "global":
            errors.append(f"{name}: 격리 안 됨. scope 컬럼 / root id-scope / 명시적 global 중 하나 필요")

        scoped = {n for n, _, _ in scope_cols}

        # scope 컬럼명은 축 referent 를 담아야. root id 는 예외
        for col, axis, is_pk in scope_cols:
            if not is_pk and not col.endswith(f"{axis}_id"):
                errors.append(f"{name}.{col}: scope={axis} 인데 이름이 *{axis}_id 아님")

        for column in table.columns:
            col = column.name
            if col == "id" or not col.endswith("_id"):
                continue
            referent = col[:-3].rsplit("_", 1)[-1]

            # 축 이름인데 scope 없음 -> 격리냐 참조냐 확인
            if referent in AXES and col not in scoped:
                warnings.append(f"{name}.{col}: 축 이름인데 scope 없음. 격리냐 참조냐 확인")

            # FK referent 가 테이블도 ref/ref_by 도 없음 -> actor_id 류
            if referent + "s" not in tables and not (column.info.get("ref") or column.info.get("ref_by")):
                errors.append(f"{name}.{col}: FK referent '{referent}' 테이블 없음 + ref/ref_by 없음")

    return errors, warnings


def main() -> int:
    errors, warnings = check()
    for w in warnings:
        print(f"[column-scope 경고] {w}")
    for e in errors:
        print(f"[column-scope 에러] {e}")
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
