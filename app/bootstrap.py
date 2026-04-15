"""Lightweight schema bootstrap helpers for runtime compatibility."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

COMPATIBILITY_DDL: Sequence[str] = (
    """
    ALTER TABLE source_versions
    ADD COLUMN IF NOT EXISTS device_context VARCHAR(255)
    """,
    """
    ALTER TABLE processing_jobs
    ADD COLUMN IF NOT EXISTS error_message TEXT
    """,
)


async def ensure_runtime_schema(connection: AsyncConnection) -> None:
    """Apply small backward-compatible schema fixes for existing databases."""
    await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    for statement in COMPATIBILITY_DDL:
        await connection.execute(text(_normalize_sql(statement)))


def _normalize_sql(statement: str) -> str:
    return " ".join(statement.split())
