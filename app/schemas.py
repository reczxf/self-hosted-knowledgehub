"""Pydantic schemas for ingestion and query APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InlineAssetCreate(BaseModel):
    """Asset payload embedded in the ingest request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    asset_role: str
    file_name: str | None = None
    mime_type: str | None = None
    content_base64: str | None = None
    text_content: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("content_base64", "text_content")
    @classmethod
    def empty_strings_to_none(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value


class ChatMessageCreate(BaseModel):
    """A single chat message embedded in a chat ingest request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    role: str
    content: str
    author: str | None = None
    occurred_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class BaseIngestRequest(BaseModel):
    """Shared fields for source ingest requests."""

    model_config = ConfigDict(str_strip_whitespace=True)

    capture_method: str
    occurred_at: datetime
    captured_at: datetime | None = None
    original_created_at: datetime | None = None
    original_updated_at: datetime | None = None
    extractor_version: str | None = None
    schema_version: str = "1"
    actor_id: str | None = None
    session_id: str | None = None
    device_context: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    assets: list[InlineAssetCreate] = Field(default_factory=list)


class WebCaptureIngestRequest(BaseIngestRequest):
    """Shared fields for URL-based captures."""

    url: str
    canonical_url: str | None = None
    referrer_url: str | None = None
    title: str | None = None
    author: str | None = None
    language: str | None = None
    mime_type: str | None = "text/html"
    browser_profile: str | None = None
    user_agent: str | None = None


class WebPageIngestRequest(WebCaptureIngestRequest):
    """Request body for ingesting a webpage capture."""

    source_type: Literal["web_page"] = "web_page"
    event_type: str = "capture.web_page"


class BookmarkIngestRequest(WebCaptureIngestRequest):
    """Request body for ingesting a bookmark."""

    source_type: Literal["bookmark"] = "bookmark"
    event_type: str = "capture.bookmark"


class SearchIngestRequest(WebCaptureIngestRequest):
    """Request body for ingesting a search result page."""

    source_type: Literal["search_result"] = "search_result"
    event_type: str = "capture.search"
    query: str
    search_engine: str | None = None


class ChatIngestRequest(BaseIngestRequest):
    """Request body for ingesting a chat thread."""

    source_type: Literal["chat_thread"] = "chat_thread"
    event_type: str = "capture.chat"
    provider: str
    thread_id: str
    thread_url: str | None = None
    title: str | None = None
    author: str | None = None
    language: str | None = None
    mime_type: str | None = "application/json"
    messages: list[ChatMessageCreate] = Field(default_factory=list)


class DocumentIngestRequest(BaseIngestRequest):
    """Request body for ingesting an uploaded document."""

    source_type: Literal["document"] = "document"
    event_type: str = "capture.document"
    file_name: str
    title: str | None = None
    mime_type: str | None = None
    original_path: str | None = None


class IngestResponse(BaseModel):
    """API response after a successful ingest."""

    source_item_id: str
    source_version_id: str
    event_id: str
    asset_count: int
    version_created: bool = True
    deduplicated: bool = False


class AssetRecordResponse(BaseModel):
    """Serialized binary asset metadata."""

    id: UUID
    asset_role: str
    storage_backend: str
    relative_path: str
    file_name: str | None
    mime_type: str | None
    size_bytes: int | None
    sha256: str | None
    created_at: datetime
    metadata: dict[str, object]


class SourceItemSummary(BaseModel):
    """Summary view of a source item."""

    id: UUID
    source_type: str
    canonical_uri: str | None
    title: str | None
    author: str | None
    language_code: str | None
    mime_type: str | None
    first_captured_at: datetime
    latest_captured_at: datetime
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, object]


class SourceItemDetail(SourceItemSummary):
    """Detailed view of a source item."""

    version_count: int
    event_count: int


class SourceItemListResponse(BaseModel):
    """Paginated list response for source items."""

    items: list[SourceItemSummary]
    limit: int
    offset: int


class SourceVersionSummary(BaseModel):
    """Summary view of a source version."""

    id: UUID
    source_item_id: UUID
    version_no: int
    capture_method: str
    content_sha256: str | None
    size_bytes: int | None
    occurred_at: datetime | None
    captured_at: datetime
    extractor_version: str | None
    schema_version: str
    referrer_uri: str | None
    user_agent: str | None
    browser_profile: str | None
    device_context: str | None = None
    metadata: dict[str, object]


class SourceVersionDetail(SourceVersionSummary):
    """Detailed view of a source version."""

    original_created_at: datetime | None
    original_updated_at: datetime | None
    assets: list[AssetRecordResponse]


class SourceVersionListResponse(BaseModel):
    """Paginated list response for source versions."""

    items: list[SourceVersionSummary]
    limit: int
    offset: int


class EventSummary(BaseModel):
    """Summary view of an event."""

    id: UUID
    event_type: str
    source_item_id: UUID | None
    source_version_id: UUID | None
    occurred_at: datetime
    captured_at: datetime
    actor_id: str | None
    session_id: str | None
    metadata: dict[str, object]


class EventDetail(EventSummary):
    """Detailed view of an event."""


class EventListResponse(BaseModel):
    """Paginated list response for events."""

    items: list[EventSummary]
    limit: int
    offset: int


class DerivedDocumentSummary(BaseModel):
    """Searchable derived document summary."""

    id: UUID
    source_item_id: UUID
    source_version_id: UUID
    content_sha256: str | None
    title: str | None
    plain_text_preview: str
    token_count: int
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, object]


class SearchResultItem(BaseModel):
    """Search result item for text or semantic retrieval."""

    document: DerivedDocumentSummary
    score: float
    match_type: Literal["text", "semantic"]


class SearchResultsResponse(BaseModel):
    """Search response payload."""

    query: str
    items: list[SearchResultItem]
    limit: int


class ProcessingJobSummary(BaseModel):
    """Background job summary."""

    id: UUID
    job_type: str
    status: str
    source_version_id: UUID
    attempts: int
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    error_message: str | None
    payload: dict[str, object]
    result: dict[str, object]
    created_at: datetime
    updated_at: datetime


class ProcessingJobListResponse(BaseModel):
    """Paginated job list response."""

    items: list[ProcessingJobSummary]
    limit: int
    offset: int


class JobRunResponse(BaseModel):
    """Response after processing pending jobs."""

    requested_limit: int
    processed: int
    completed: int
    failed: int
    jobs: list[ProcessingJobSummary]


class KnowledgeItemSummary(BaseModel):
    """Compiled knowledge object summary."""

    id: UUID
    knowledge_type: str
    status: str
    slug: str
    title: str
    summary: str | None
    source_item_id: UUID | None
    source_version_id: UUID | None
    derived_document_id: UUID | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, object]


class KnowledgeItemDetail(KnowledgeItemSummary):
    """Compiled knowledge object detail."""

    body_text: str
    evidence: list[str]


class KnowledgeItemListResponse(BaseModel):
    """Paginated knowledge item list response."""

    items: list[KnowledgeItemSummary]
    limit: int
    offset: int


class ConversationAskRequest(BaseModel):
    """Single-turn conversation request."""

    question: str
    session_id: UUID | None = None
    limit: int = Field(default=5, ge=1, le=20)
    search_mode: Literal["text", "semantic", "hybrid"] = "hybrid"


class ConversationEvidenceItem(BaseModel):
    """Evidence item used in a conversation answer."""

    source_version_id: UUID
    title: str | None
    preview: str
    score: float
    match_type: Literal["text", "semantic"]


class ConversationTurnItem(BaseModel):
    """Conversation turn returned to clients."""

    id: UUID
    session_id: UUID
    turn_no: int
    role: Literal["user", "assistant"]
    content: str
    provider: str | None = None
    model: str | None = None
    used_fallback: bool = False
    created_at: datetime
    metadata: dict[str, object]


class ConversationAnswerResponse(BaseModel):
    """Structured answer payload for the conversation layer."""

    session_id: UUID
    question: str
    answer: str
    provider: str
    model: str
    used_fallback: bool = False
    knowledge_items: list[KnowledgeItemSummary]
    evidence_items: list[ConversationEvidenceItem]
    conversation_turns: list[ConversationTurnItem]
