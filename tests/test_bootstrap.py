from __future__ import annotations

from app.bootstrap import COMPATIBILITY_DDL, _normalize_sql


def test_compatibility_ddl_contains_device_context_patch() -> None:
    normalized = [_normalize_sql(statement) for statement in COMPATIBILITY_DDL]

    assert any(
        "ALTER TABLE source_versions ADD COLUMN IF NOT EXISTS device_context" in statement
        for statement in normalized
    )


def test_normalize_sql_collapses_whitespace() -> None:
    assert _normalize_sql("ALTER   TABLE\nsource_versions") == "ALTER TABLE source_versions"
