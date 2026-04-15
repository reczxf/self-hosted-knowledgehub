"""PostgreSQL vector column support without requiring the pgvector Python package."""

from __future__ import annotations

from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    """Minimal pgvector-compatible SQLAlchemy type."""

    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_: object) -> str:
        return f"VECTOR({self.dimensions})"

    def bind_processor(self, _: object):
        def process(value: list[float] | tuple[float, ...] | None) -> str | None:
            if value is None:
                return None
            return "[" + ",".join(f"{float(item):.8f}" for item in value) + "]"

        return process

    def result_processor(self, _: object, __: object):
        def process(value: str | list[float] | None) -> list[float] | None:
            if value is None or isinstance(value, list):
                return value
            stripped = value.strip()[1:-1]
            if not stripped:
                return []
            return [float(item) for item in stripped.split(",")]

        return process

    class comparator_factory(UserDefinedType.Comparator):
        """Custom pgvector distance operators."""

        def cosine_distance(self, other: object):
            return self.expr.op("<=>")(other)
