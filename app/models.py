"""ORM models for ingestion entities."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TimestampMixin:
    """Shared timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SourceItem(TimestampMixin, Base):
    """A logical source object, such as a page or chat thread."""

    __tablename__ = "source_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_uri: Mapped[str | None] = mapped_column(Text())
    title: Mapped[str | None] = mapped_column(Text())
    author: Mapped[str | None] = mapped_column(Text())
    language_code: Mapped[str | None] = mapped_column(String(16))
    mime_type: Mapped[str | None] = mapped_column(String(255))
    first_captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    latest_captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    versions: Mapped[list["SourceVersion"]] = relationship(back_populates="source_item")
    events: Mapped[list["Event"]] = relationship(back_populates="source_item")

    __table_args__ = (
        Index("idx_source_items_source_type", "source_type"),
        Index("idx_source_items_canonical_uri", "canonical_uri"),
        Index("idx_source_items_metadata_gin", metadata_json, postgresql_using="gin"),
    )


class SourceVersion(Base):
    """A captured snapshot of a source item."""

    __tablename__ = "source_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_items.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(nullable=False)
    capture_method: Mapped[str] = mapped_column(String(64), nullable=False)
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    original_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    original_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extractor_version: Mapped[str | None] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    referrer_uri: Mapped[str | None] = mapped_column(Text())
    user_agent: Mapped[str | None] = mapped_column(Text())
    browser_profile: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    source_item: Mapped[SourceItem] = relationship(back_populates="versions")
    binary_assets: Mapped[list["BinaryAsset"]] = relationship(back_populates="source_version")
    events: Mapped[list["Event"]] = relationship(back_populates="source_version")

    __table_args__ = (
        UniqueConstraint("source_item_id", "version_no", name="uq_source_versions_source_item_version"),
        Index("idx_source_versions_source_item_id", "source_item_id"),
        Index("idx_source_versions_captured_at", "captured_at"),
        Index("idx_source_versions_occurred_at", "occurred_at"),
        Index("idx_source_versions_metadata_gin", metadata_json, postgresql_using="gin"),
    )


class BinaryAsset(Base):
    """An asset stored in local file storage."""

    __tablename__ = "binary_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False
    )
    asset_role: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(32), nullable=False, default="local_fs")
    relative_path: Mapped[str] = mapped_column(Text(), nullable=False)
    file_name: Mapped[str | None] = mapped_column(Text())
    mime_type: Mapped[str | None] = mapped_column(String(255))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    source_version: Mapped[SourceVersion] = relationship(back_populates="binary_assets")

    __table_args__ = (
        Index("idx_binary_assets_source_version_id", "source_version_id"),
        Index("idx_binary_assets_asset_role", "asset_role"),
        Index("idx_binary_assets_sha256", "sha256"),
    )


class Event(Base):
    """User or system event tied to captured source material."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_items.id", ondelete="SET NULL")
    )
    source_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_versions.id", ondelete="SET NULL")
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor_id: Mapped[str | None] = mapped_column(String(255))
    session_id: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    source_item: Mapped[SourceItem | None] = relationship(back_populates="events")
    source_version: Mapped[SourceVersion | None] = relationship(back_populates="events")

    __table_args__ = (
        Index("idx_events_event_type", "event_type"),
        Index("idx_events_occurred_at", "occurred_at"),
        Index("idx_events_source_item_id", "source_item_id"),
        Index("idx_events_metadata_gin", metadata_json, postgresql_using="gin"),
    )
