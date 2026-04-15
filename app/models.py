"""ORM models for ingestion entities."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.vector import Vector


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

    versions: Mapped[list[SourceVersion]] = relationship(back_populates="source_item")
    events: Mapped[list[Event]] = relationship(back_populates="source_item")
    knowledge_items: Mapped[list[KnowledgeItem]] = relationship(back_populates="source_item")

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
    device_context: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    source_item: Mapped[SourceItem] = relationship(back_populates="versions")
    binary_assets: Mapped[list[BinaryAsset]] = relationship(back_populates="source_version")
    events: Mapped[list[Event]] = relationship(back_populates="source_version")
    derived_documents: Mapped[list[DerivedDocument]] = relationship(back_populates="source_version")
    processing_jobs: Mapped[list[ProcessingJob]] = relationship(back_populates="source_version")
    knowledge_items: Mapped[list[KnowledgeItem]] = relationship(back_populates="source_version")

    __table_args__ = (
        UniqueConstraint(
            "source_item_id",
            "version_no",
            name="uq_source_versions_source_item_version",
        ),
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


class ConversationSession(TimestampMixin, Base):
    """A persisted multi-turn conversation session."""

    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str | None] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    last_question: Mapped[str | None] = mapped_column(Text())
    last_answer: Mapped[str | None] = mapped_column(Text())
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    turns: Mapped[list[ConversationTurn]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_conversation_sessions_status", "status"),
        Index("idx_conversation_sessions_updated_at", "updated_at"),
    )


class ConversationTurn(Base):
    """A single user or assistant message within a conversation session."""

    __tablename__ = "conversation_turns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_no: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(128))
    used_fallback: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    session: Mapped[ConversationSession] = relationship(back_populates="turns")

    __table_args__ = (
        UniqueConstraint("session_id", "turn_no", name="uq_conversation_turns_session_turn"),
        Index("idx_conversation_turns_session_id", "session_id"),
        Index("idx_conversation_turns_role", "role"),
    )


class DerivedDocument(TimestampMixin, Base):
    """Derived text and vector record for a captured source version."""

    __tablename__ = "derived_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_items.id", ondelete="CASCADE"), nullable=False
    )
    source_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False
    )
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(Text())
    plain_text: Mapped[str] = mapped_column(Text(), nullable=False)
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(plain_text, ''))",
            persisted=True,
        ),
        nullable=False,
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(64))
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    source_version: Mapped[SourceVersion] = relationship(back_populates="derived_documents")
    knowledge_items: Mapped[list[KnowledgeItem]] = relationship(back_populates="derived_document")

    __table_args__ = (
        UniqueConstraint("source_version_id", name="uq_derived_documents_source_version"),
        Index("idx_derived_documents_source_item_id", "source_item_id"),
        Index("idx_derived_documents_search_vector", "search_vector", postgresql_using="gin"),
    )


class ProcessingJob(TimestampMixin, Base):
    """Asynchronous processing task metadata."""

    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    source_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload_json: Mapped[dict[str, object]] = mapped_column(
        "payload", JSONB, nullable=False, default=dict, server_default="{}"
    )
    result_json: Mapped[dict[str, object]] = mapped_column(
        "result", JSONB, nullable=False, default=dict, server_default="{}"
    )
    error_message: Mapped[str | None] = mapped_column(Text())

    source_version: Mapped[SourceVersion] = relationship(back_populates="processing_jobs")

    __table_args__ = (
        UniqueConstraint("job_type", "source_version_id", name="uq_processing_jobs_type_version"),
        Index("idx_processing_jobs_status", "status"),
        Index("idx_processing_jobs_job_type", "job_type"),
        Index("idx_processing_jobs_source_version_id", "source_version_id"),
    )


class KnowledgeItem(TimestampMixin, Base):
    """Compiled knowledge object derived from indexed source material."""

    __tablename__ = "knowledge_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text())
    body_text: Mapped[str] = mapped_column(Text(), nullable=False)
    source_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_items.id", ondelete="SET NULL")
    )
    source_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_versions.id", ondelete="SET NULL")
    )
    derived_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("derived_documents.id", ondelete="SET NULL")
    )
    evidence_json: Mapped[list[str]] = mapped_column(
        "evidence", JSONB, nullable=False, default=list, server_default="[]"
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    source_item: Mapped[SourceItem | None] = relationship(back_populates="knowledge_items")
    source_version: Mapped[SourceVersion | None] = relationship(back_populates="knowledge_items")
    derived_document: Mapped[DerivedDocument | None] = relationship(
        back_populates="knowledge_items"
    )

    __table_args__ = (
        Index("idx_knowledge_items_type", "knowledge_type"),
        Index("idx_knowledge_items_status", "status"),
        Index("idx_knowledge_items_source_item_id", "source_item_id"),
    )
