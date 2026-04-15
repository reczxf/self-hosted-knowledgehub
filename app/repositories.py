"""Persistence, indexing and query logic for PKOS."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.indexing import (
    build_indexable_text,
    compute_text_embedding,
    estimate_token_count,
    extract_text_content,
)
from app.llm import LlmAnswer, deepseek_client
from app.models import (
    BinaryAsset,
    ConversationSession,
    ConversationTurn,
    DerivedDocument,
    Event,
    KnowledgeItem,
    ProcessingJob,
    SourceItem,
    SourceVersion,
)
from app.schemas import (
    AssetRecordResponse,
    BookmarkIngestRequest,
    ChatIngestRequest,
    ConversationAnswerResponse,
    ConversationEvidenceItem,
    ConversationTurnItem,
    DerivedDocumentSummary,
    DocumentIngestRequest,
    EventDetail,
    EventSummary,
    IngestResponse,
    InlineAssetCreate,
    JobRunResponse,
    KnowledgeItemDetail,
    KnowledgeItemSummary,
    ProcessingJobSummary,
    SearchIngestRequest,
    SearchResultItem,
    SourceItemDetail,
    SourceItemSummary,
    SourceVersionDetail,
    SourceVersionSummary,
    WebPageIngestRequest,
)
from app.storage import LocalAssetStore

INDEX_SOURCE_VERSION_JOB = "index_source_version"
COMPILE_KNOWLEDGE_JOB = "compile_knowledge_item"
PREVIEW_LENGTH = 240
SUMMARY_LENGTH = 320
CONVERSATION_HISTORY_TURNS = 6


@dataclass(slots=True)
class PreparedInlineAsset:
    """Decoded inline asset before persistence."""

    asset_role: str
    file_name: str | None
    mime_type: str | None
    metadata: dict[str, object]
    raw_bytes: bytes
    sha256: str
    size_bytes: int


async def ingest_webpage(
    *,
    session: AsyncSession,
    payload: WebPageIngestRequest,
    asset_store: LocalAssetStore,
) -> IngestResponse:
    """Persist a webpage capture into database and local storage."""
    return await _persist_capture(
        session=session,
        asset_store=asset_store,
        source_type=payload.source_type,
        event_type=payload.event_type,
        canonical_uri=payload.canonical_url or payload.url,
        source_uri=payload.url,
        referrer_uri=payload.referrer_url,
        title=payload.title,
        author=payload.author,
        language=payload.language,
        mime_type=payload.mime_type,
        occurred_at=payload.occurred_at,
        captured_at=payload.captured_at,
        original_created_at=payload.original_created_at,
        original_updated_at=payload.original_updated_at,
        browser_profile=payload.browser_profile,
        user_agent=payload.user_agent,
        device_context=payload.device_context,
        extractor_version=payload.extractor_version,
        schema_version=payload.schema_version,
        actor_id=payload.actor_id,
        session_id=payload.session_id,
        metadata=payload.metadata,
        assets=payload.assets,
        envelope_payload=payload.model_dump(mode="json"),
        content_fingerprint_payload=_fingerprint_payload(payload),
        event_metadata={
            "capture_method": payload.capture_method,
            "url": payload.url,
            "canonical_url": payload.canonical_url or payload.url,
        },
        capture_method=payload.capture_method,
    )


async def ingest_bookmark(
    *,
    session: AsyncSession,
    payload: BookmarkIngestRequest,
    asset_store: LocalAssetStore,
) -> IngestResponse:
    """Persist a bookmark capture into database and local storage."""
    return await _persist_capture(
        session=session,
        asset_store=asset_store,
        source_type=payload.source_type,
        event_type=payload.event_type,
        canonical_uri=payload.canonical_url or payload.url,
        source_uri=payload.url,
        referrer_uri=payload.referrer_url,
        title=payload.title,
        author=payload.author,
        language=payload.language,
        mime_type=payload.mime_type,
        occurred_at=payload.occurred_at,
        captured_at=payload.captured_at,
        original_created_at=payload.original_created_at,
        original_updated_at=payload.original_updated_at,
        browser_profile=payload.browser_profile,
        user_agent=payload.user_agent,
        device_context=payload.device_context,
        extractor_version=payload.extractor_version,
        schema_version=payload.schema_version,
        actor_id=payload.actor_id,
        session_id=payload.session_id,
        metadata=payload.metadata,
        assets=payload.assets,
        envelope_payload=payload.model_dump(mode="json"),
        content_fingerprint_payload=_fingerprint_payload(payload),
        event_metadata={
            "capture_method": payload.capture_method,
            "url": payload.url,
            "canonical_url": payload.canonical_url or payload.url,
        },
        capture_method=payload.capture_method,
    )


async def ingest_search(
    *,
    session: AsyncSession,
    payload: SearchIngestRequest,
    asset_store: LocalAssetStore,
) -> IngestResponse:
    """Persist a search result page capture into database and local storage."""
    canonical_uri = payload.canonical_url or payload.url
    metadata = {
        **payload.metadata,
        "query": payload.query,
        "search_engine": payload.search_engine,
    }
    return await _persist_capture(
        session=session,
        asset_store=asset_store,
        source_type=payload.source_type,
        event_type=payload.event_type,
        canonical_uri=canonical_uri,
        source_uri=payload.url,
        referrer_uri=payload.referrer_url,
        title=payload.title or payload.query,
        author=payload.author,
        language=payload.language,
        mime_type=payload.mime_type,
        occurred_at=payload.occurred_at,
        captured_at=payload.captured_at,
        original_created_at=payload.original_created_at,
        original_updated_at=payload.original_updated_at,
        browser_profile=payload.browser_profile,
        user_agent=payload.user_agent,
        device_context=payload.device_context,
        extractor_version=payload.extractor_version,
        schema_version=payload.schema_version,
        actor_id=payload.actor_id,
        session_id=payload.session_id,
        metadata=metadata,
        assets=payload.assets,
        envelope_payload=payload.model_dump(mode="json"),
        content_fingerprint_payload=_fingerprint_payload(payload),
        event_metadata={
            "capture_method": payload.capture_method,
            "url": payload.url,
            "canonical_url": canonical_uri,
            "query": payload.query,
            "search_engine": payload.search_engine,
        },
        capture_method=payload.capture_method,
    )


async def ingest_chat(
    *,
    session: AsyncSession,
    payload: ChatIngestRequest,
    asset_store: LocalAssetStore,
) -> IngestResponse:
    """Persist a chat thread into database and local storage."""
    chat_assets = list(payload.assets)
    if payload.messages:
        chat_assets.append(
            InlineAssetCreate(
                asset_role="chat_messages",
                file_name="messages.json",
                mime_type="application/json",
                text_content=json.dumps(
                    [message.model_dump(mode="json") for message in payload.messages],
                    ensure_ascii=False,
                    indent=2,
                ),
                metadata={"generated_by": "pkos-collector", "message_count": len(payload.messages)},
            )
        )

    canonical_uri = payload.thread_url or f"chat://{payload.provider}/{payload.thread_id}"
    metadata = {
        **payload.metadata,
        "provider": payload.provider,
        "thread_id": payload.thread_id,
        "thread_url": payload.thread_url,
        "message_count": len(payload.messages),
    }
    return await _persist_capture(
        session=session,
        asset_store=asset_store,
        source_type=payload.source_type,
        event_type=payload.event_type,
        canonical_uri=canonical_uri,
        source_uri=payload.thread_url,
        referrer_uri=None,
        title=payload.title or payload.thread_id,
        author=payload.author,
        language=payload.language,
        mime_type=payload.mime_type,
        occurred_at=payload.occurred_at,
        captured_at=payload.captured_at,
        original_created_at=payload.original_created_at,
        original_updated_at=payload.original_updated_at,
        browser_profile=None,
        user_agent=None,
        device_context=payload.device_context,
        extractor_version=payload.extractor_version,
        schema_version=payload.schema_version,
        actor_id=payload.actor_id,
        session_id=payload.session_id,
        metadata=metadata,
        assets=chat_assets,
        envelope_payload=payload.model_dump(mode="json"),
        content_fingerprint_payload=_fingerprint_payload(payload),
        event_metadata={
            "capture_method": payload.capture_method,
            "provider": payload.provider,
            "thread_id": payload.thread_id,
            "thread_url": payload.thread_url,
            "message_count": len(payload.messages),
        },
        capture_method=payload.capture_method,
    )


async def ingest_document(
    *,
    session: AsyncSession,
    payload: DocumentIngestRequest,
    asset_store: LocalAssetStore,
) -> IngestResponse:
    """Persist an uploaded document into database and local storage."""
    document_assets = list(payload.assets)
    return await _persist_capture(
        session=session,
        asset_store=asset_store,
        source_type=payload.source_type,
        event_type=payload.event_type,
        canonical_uri=payload.original_path or f"file://{payload.file_name}",
        source_uri=payload.original_path,
        referrer_uri=None,
        title=payload.title or payload.file_name,
        author=None,
        language=None,
        mime_type=payload.mime_type,
        occurred_at=payload.occurred_at,
        captured_at=payload.captured_at,
        original_created_at=payload.original_created_at,
        original_updated_at=payload.original_updated_at,
        browser_profile=None,
        user_agent=None,
        device_context=payload.device_context,
        extractor_version=payload.extractor_version,
        schema_version=payload.schema_version,
        actor_id=payload.actor_id,
        session_id=payload.session_id,
        metadata={
            **payload.metadata,
            "file_name": payload.file_name,
            "original_path": payload.original_path,
        },
        assets=document_assets,
        envelope_payload=payload.model_dump(mode="json"),
        content_fingerprint_payload=_fingerprint_payload(payload),
        event_metadata={
            "capture_method": payload.capture_method,
            "file_name": payload.file_name,
            "original_path": payload.original_path,
        },
        capture_method=payload.capture_method,
    )


async def _persist_capture(
    *,
    session: AsyncSession,
    asset_store: LocalAssetStore,
    source_type: str,
    event_type: str,
    canonical_uri: str,
    source_uri: str | None,
    referrer_uri: str | None,
    title: str | None,
    author: str | None,
    language: str | None,
    mime_type: str | None,
    occurred_at: datetime,
    captured_at: datetime | None,
    original_created_at: datetime | None,
    original_updated_at: datetime | None,
    browser_profile: str | None,
    user_agent: str | None,
    device_context: str | None,
    extractor_version: str | None,
    schema_version: str,
    actor_id: str | None,
    session_id: str | None,
    metadata: dict[str, object],
    assets: Sequence[InlineAssetCreate],
    envelope_payload: dict[str, object],
    content_fingerprint_payload: dict[str, object],
    event_metadata: dict[str, object],
    capture_method: str,
) -> IngestResponse:
    """Persist a generic capture into database and local storage."""
    now = captured_at or datetime.now(UTC)
    prepared_assets = _prepare_inline_assets(asset_store=asset_store, assets=assets)
    content_sha256 = _calculate_content_sha256(
        prepared_assets=prepared_assets,
        fingerprint_payload=content_fingerprint_payload,
    )

    source_item = await _get_or_create_source_item(
        session=session,
        source_type=source_type,
        source_uri=source_uri,
        title=title,
        author=author,
        language=language,
        mime_type=mime_type,
        metadata=metadata,
        canonical_uri=canonical_uri,
        captured_at=now,
    )

    existing_version = await _get_existing_version_by_content_sha(
        session=session,
        source_item_id=source_item.id,
        content_sha256=content_sha256,
    )
    if existing_version is not None:
        event = Event(
            event_type=event_type,
            source_item_id=source_item.id,
            source_version_id=existing_version.id,
            occurred_at=occurred_at,
            captured_at=now,
            actor_id=actor_id,
            session_id=session_id,
            metadata_json={**event_metadata, "deduplicated": True},
        )
        session.add(event)
        source_item.latest_captured_at = now
        await session.commit()
        return IngestResponse(
            source_item_id=str(source_item.id),
            source_version_id=str(existing_version.id),
            event_id=str(event.id),
            asset_count=0,
            version_created=False,
            deduplicated=True,
        )

    version_no = await _next_version_no(session=session, source_item_id=source_item.id)
    envelope_asset = asset_store.store_json(
        category="captures",
        suggested_name="envelope.json",
        payload=envelope_payload,
    )

    source_version = SourceVersion(
        source_item_id=source_item.id,
        version_no=version_no,
        capture_method=capture_method,
        content_sha256=content_sha256,
        size_bytes=envelope_asset.size_bytes,
        occurred_at=occurred_at,
        captured_at=now,
        original_created_at=original_created_at,
        original_updated_at=original_updated_at,
        extractor_version=extractor_version,
        schema_version=schema_version,
        referrer_uri=referrer_uri,
        user_agent=user_agent,
        browser_profile=browser_profile,
        device_context=device_context,
        metadata_json=metadata,
    )
    session.add(source_version)
    await session.flush()

    asset_records: list[BinaryAsset] = [
        BinaryAsset(
            source_version_id=source_version.id,
            asset_role="request_envelope",
            relative_path=envelope_asset.relative_path,
            file_name="envelope.json",
            mime_type="application/json",
            size_bytes=envelope_asset.size_bytes,
            sha256=envelope_asset.sha256,
            metadata_json={"generated_by": "pkos-collector"},
        )
    ]
    total_asset_bytes = envelope_asset.size_bytes

    for asset in prepared_assets:
        stored = asset_store.store_bytes(
            category="captures",
            suggested_name=asset.file_name or f"{asset.asset_role}.bin",
            content=asset.raw_bytes,
        )
        total_asset_bytes += stored.size_bytes
        asset_records.append(
            BinaryAsset(
                source_version_id=source_version.id,
                asset_role=asset.asset_role,
                relative_path=stored.relative_path,
                file_name=asset.file_name,
                mime_type=asset.mime_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                metadata_json=asset.metadata,
            )
        )

    source_version.size_bytes = total_asset_bytes
    for asset_record in asset_records:
        session.add(asset_record)

    event = Event(
        event_type=event_type,
        source_item_id=source_item.id,
        source_version_id=source_version.id,
        occurred_at=occurred_at,
        captured_at=now,
        actor_id=actor_id,
        session_id=session_id,
        metadata_json=event_metadata,
    )
    session.add(event)
    source_item.latest_captured_at = now

    await _enqueue_processing_job(
        session=session,
        source_version_id=source_version.id,
        job_type=INDEX_SOURCE_VERSION_JOB,
        payload={"source_item_id": str(source_item.id), "content_sha256": content_sha256},
    )
    await session.commit()

    return IngestResponse(
        source_item_id=str(source_item.id),
        source_version_id=str(source_version.id),
        event_id=str(event.id),
        asset_count=len(asset_records),
        version_created=True,
        deduplicated=False,
    )


def _prepare_inline_assets(
    *,
    asset_store: LocalAssetStore,
    assets: Sequence[InlineAssetCreate],
) -> list[PreparedInlineAsset]:
    prepared_assets: list[PreparedInlineAsset] = []
    for asset in assets:
        raw_bytes = asset_store.decode_asset_content(
            content_base64=asset.content_base64,
            text_content=asset.text_content,
        )
        prepared_assets.append(
            PreparedInlineAsset(
                asset_role=asset.asset_role,
                file_name=asset.file_name,
                mime_type=asset.mime_type,
                metadata=asset.metadata,
                raw_bytes=raw_bytes,
                sha256=hashlib.sha256(raw_bytes).hexdigest(),
                size_bytes=len(raw_bytes),
            )
        )
    return prepared_assets


def _calculate_content_sha256(
    *,
    prepared_assets: Sequence[PreparedInlineAsset],
    fingerprint_payload: dict[str, object],
) -> str:
    hasher = hashlib.sha256()
    if prepared_assets:
        for asset in prepared_assets:
            hasher.update(asset.asset_role.encode("utf-8"))
            hasher.update((asset.mime_type or "").encode("utf-8"))
            hasher.update(asset.raw_bytes)
        return hasher.hexdigest()
    normalized = json.dumps(
        fingerprint_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    hasher.update(normalized)
    return hasher.hexdigest()


def _fingerprint_payload(payload: object) -> dict[str, object]:
    if not hasattr(payload, "model_dump"):
        raise TypeError("payload must support model_dump")
    return payload.model_dump(
        mode="json",
        exclude={"captured_at", "occurred_at", "actor_id", "session_id"},
    )


async def _get_or_create_source_item(
    *,
    session: AsyncSession,
    source_type: str,
    source_uri: str | None,
    title: str | None,
    author: str | None,
    language: str | None,
    mime_type: str | None,
    metadata: dict[str, object],
    canonical_uri: str,
    captured_at: datetime,
) -> SourceItem:
    result = await session.execute(
        select(SourceItem).where(
            SourceItem.source_type == source_type,
            SourceItem.canonical_uri == canonical_uri,
        )
    )
    source_item = result.scalar_one_or_none()
    if source_item is not None:
        if title is not None:
            source_item.title = title
        if author is not None:
            source_item.author = author
        if language is not None:
            source_item.language_code = language
        if mime_type is not None:
            source_item.mime_type = mime_type
        if metadata:
            source_item.metadata_json = {**source_item.metadata_json, **metadata}
        source_item.latest_captured_at = captured_at
        return source_item

    source_item = SourceItem(
        source_type=source_type,
        canonical_uri=canonical_uri,
        title=title,
        author=author,
        language_code=language,
        mime_type=mime_type,
        first_captured_at=captured_at,
        latest_captured_at=captured_at,
        metadata_json={**({"url": source_uri} if source_uri else {}), **metadata},
    )
    session.add(source_item)
    await session.flush()
    return source_item


async def _next_version_no(*, session: AsyncSession, source_item_id: object) -> int:
    result = await session.execute(
        select(func.coalesce(func.max(SourceVersion.version_no), 0) + 1).where(
            SourceVersion.source_item_id == source_item_id
        )
    )
    return int(result.scalar_one())


async def _get_existing_version_by_content_sha(
    *,
    session: AsyncSession,
    source_item_id: object,
    content_sha256: str,
) -> SourceVersion | None:
    result = await session.execute(
        select(SourceVersion).where(
            SourceVersion.source_item_id == source_item_id,
            SourceVersion.content_sha256 == content_sha256,
        )
    )
    return result.scalar_one_or_none()


async def _enqueue_processing_job(
    *,
    session: AsyncSession,
    source_version_id: object,
    job_type: str,
    payload: dict[str, object],
) -> ProcessingJob:
    existing_result = await session.execute(
        select(ProcessingJob).where(
            ProcessingJob.job_type == job_type,
            ProcessingJob.source_version_id == source_version_id,
        )
    )
    existing_job = existing_result.scalar_one_or_none()
    if existing_job is not None:
        return existing_job

    job = ProcessingJob(
        job_type=job_type,
        status="pending",
        source_version_id=source_version_id,
        payload_json=payload,
    )
    session.add(job)
    await session.flush()
    return job


async def _list_knowledge_items_by_source_versions(
    *,
    session: AsyncSession,
    source_version_ids: Sequence[object],
    limit: int,
) -> list[KnowledgeItemSummary]:
    if not source_version_ids:
        return []
    result = await session.execute(
        select(KnowledgeItem)
        .where(KnowledgeItem.source_version_id.in_(source_version_ids))
        .order_by(KnowledgeItem.updated_at.desc())
        .limit(limit)
    )
    return [_to_knowledge_item_summary(item) for item in result.scalars().all()]


async def list_source_items(
    *,
    session: AsyncSession,
    source_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SourceItemSummary]:
    """List source items."""
    query = (
        select(SourceItem)
        .order_by(SourceItem.latest_captured_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if source_type is not None:
        query = query.where(SourceItem.source_type == source_type)
    result = await session.execute(query)
    return [_to_source_item_summary(item) for item in result.scalars().all()]


async def get_source_item(*, session: AsyncSession, source_item_id: str) -> SourceItemDetail | None:
    """Get a source item by id."""
    result = await session.execute(
        select(SourceItem)
        .options(selectinload(SourceItem.versions), selectinload(SourceItem.events))
        .where(SourceItem.id == uuid.UUID(source_item_id))
    )
    item = result.scalar_one_or_none()
    if item is None:
        return None
    return _to_source_item_detail(item)


async def list_source_versions(
    *,
    session: AsyncSession,
    source_item_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[SourceVersionSummary]:
    """List versions for a source item."""
    result = await session.execute(
        select(SourceVersion)
        .where(SourceVersion.source_item_id == uuid.UUID(source_item_id))
        .order_by(SourceVersion.version_no.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_to_source_version_summary(version) for version in result.scalars().all()]


async def get_source_version(
    *,
    session: AsyncSession,
    source_version_id: str,
) -> SourceVersionDetail | None:
    """Get a source version by id."""
    result = await session.execute(
        select(SourceVersion)
        .options(selectinload(SourceVersion.binary_assets))
        .where(SourceVersion.id == uuid.UUID(source_version_id))
    )
    version = result.scalar_one_or_none()
    if version is None:
        return None
    return _to_source_version_detail(version)


async def list_events(
    *,
    session: AsyncSession,
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[EventSummary]:
    """List events."""
    query = select(Event).order_by(Event.occurred_at.desc()).limit(limit).offset(offset)
    if event_type is not None:
        query = query.where(Event.event_type == event_type)
    result = await session.execute(query)
    return [_to_event_summary(event) for event in result.scalars().all()]


async def get_event(*, session: AsyncSession, event_id: str) -> EventDetail | None:
    """Get an event by id."""
    result = await session.execute(select(Event).where(Event.id == uuid.UUID(event_id)))
    event = result.scalar_one_or_none()
    if event is None:
        return None
    return _to_event_detail(event)


async def list_processing_jobs(
    *,
    session: AsyncSession,
    status: str | None = None,
    job_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ProcessingJobSummary]:
    """List processing jobs."""
    query = (
        select(ProcessingJob)
        .order_by(ProcessingJob.queued_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status is not None:
        query = query.where(ProcessingJob.status == status)
    if job_type is not None:
        query = query.where(ProcessingJob.job_type == job_type)
    result = await session.execute(query)
    return [_to_processing_job_summary(job) for job in result.scalars().all()]


async def list_knowledge_items(
    *,
    session: AsyncSession,
    knowledge_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[KnowledgeItemSummary]:
    """List compiled knowledge items."""
    query = (
        select(KnowledgeItem)
        .order_by(KnowledgeItem.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if knowledge_type is not None:
        query = query.where(KnowledgeItem.knowledge_type == knowledge_type)
    result = await session.execute(query)
    return [_to_knowledge_item_summary(item) for item in result.scalars().all()]


async def get_knowledge_item(
    *,
    session: AsyncSession,
    knowledge_item_id: str,
) -> KnowledgeItemDetail | None:
    """Get a knowledge item by id."""
    result = await session.execute(
        select(KnowledgeItem).where(KnowledgeItem.id == uuid.UUID(knowledge_item_id))
    )
    item = result.scalar_one_or_none()
    if item is None:
        return None
    return _to_knowledge_item_detail(item)


async def answer_conversation_question(
    *,
    session: AsyncSession,
    question: str,
    session_id: str | None = None,
    limit: int = 5,
    search_mode: str = "hybrid",
) -> ConversationAnswerResponse:
    """Answer a question using knowledge items plus indexed source evidence."""
    conversation_session = await _get_or_create_conversation_session(
        session=session,
        session_id=session_id,
        question=question,
    )
    prior_turns = await _list_conversation_turns(
        session=session,
        session_id=conversation_session.id,
        limit=CONVERSATION_HISTORY_TURNS,
    )
    user_turn = await _create_conversation_turn(
        session=session,
        session_id=conversation_session.id,
        role="user",
        content=question,
        metadata={"search_mode": search_mode},
    )

    evidence_map: dict[str, ConversationEvidenceItem] = {}

    if search_mode in {"text", "hybrid"}:
        for item in await search_derived_documents_text(
            session=session,
            query=question,
            limit=limit,
        ):
            evidence_map[str(item.document.source_version_id)] = ConversationEvidenceItem(
                source_version_id=item.document.source_version_id,
                title=item.document.title,
                preview=item.document.plain_text_preview,
                score=item.score,
                match_type="text",
            )

    if search_mode in {"semantic", "hybrid"}:
        for item in await search_derived_documents_semantic(
            session=session,
            query=question,
            limit=limit,
        ):
            existing = evidence_map.get(str(item.document.source_version_id))
            if existing is None or item.score > existing.score:
                evidence_map[str(item.document.source_version_id)] = ConversationEvidenceItem(
                    source_version_id=item.document.source_version_id,
                    title=item.document.title,
                    preview=item.document.plain_text_preview,
                    score=item.score,
                    match_type="semantic",
                )

    ordered_evidence = sorted(
        evidence_map.values(),
        key=lambda item: item.score,
        reverse=True,
    )[:limit]

    source_version_ids = [item.source_version_id for item in ordered_evidence]
    knowledge_items = await _list_knowledge_items_by_source_versions(
        session=session,
        source_version_ids=source_version_ids,
        limit=limit,
    )
    fallback_answer = _compose_conversation_answer(
        question=question,
        knowledge_items=knowledge_items,
        evidence_items=ordered_evidence,
    )
    llm_answer = await _generate_conversation_answer_with_deepseek(
        question=question,
        history_turns=prior_turns,
        knowledge_items=knowledge_items,
        evidence_items=ordered_evidence,
        fallback_answer=fallback_answer,
    )
    assistant_turn = await _create_conversation_turn(
        session=session,
        session_id=conversation_session.id,
        role="assistant",
        content=llm_answer.answer,
        provider=llm_answer.provider,
        model=llm_answer.model,
        used_fallback=llm_answer.used_fallback,
        metadata={
            "knowledge_item_ids": [str(item.id) for item in knowledge_items],
            "evidence_source_version_ids": [
                str(item.source_version_id) for item in ordered_evidence
            ],
        },
    )
    conversation_session.last_question = question
    conversation_session.last_answer = llm_answer.answer
    await session.commit()
    conversation_turns = _select_latest_turn_window(
        [*prior_turns, user_turn, assistant_turn],
        limit=CONVERSATION_HISTORY_TURNS,
    )

    return ConversationAnswerResponse(
        session_id=conversation_session.id,
        question=question,
        answer=llm_answer.answer,
        provider=llm_answer.provider,
        model=llm_answer.model,
        used_fallback=llm_answer.used_fallback,
        knowledge_items=knowledge_items,
        evidence_items=ordered_evidence,
        conversation_turns=[_to_conversation_turn_item(turn) for turn in conversation_turns],
    )


async def _get_or_create_conversation_session(
    *,
    session: AsyncSession,
    session_id: str | None,
    question: str,
) -> ConversationSession:
    if session_id is not None:
        existing = await session.get(ConversationSession, uuid.UUID(session_id))
        if existing is None:
            raise ValueError(f"conversation session not found: {session_id}")
        return existing

    conversation_session = ConversationSession(
        title=_build_conversation_session_title(question),
        status="active",
        last_question=question,
    )
    session.add(conversation_session)
    await session.flush()
    return conversation_session


async def _list_conversation_turns(
    *,
    session: AsyncSession,
    session_id: object,
    limit: int,
) -> list[ConversationTurn]:
    result = await session.execute(
        select(ConversationTurn)
        .where(ConversationTurn.session_id == session_id)
        .order_by(ConversationTurn.turn_no.asc())
    )
    return _select_latest_turn_window(result.scalars().all(), limit=limit)


async def _create_conversation_turn(
    *,
    session: AsyncSession,
    session_id: object,
    role: str,
    content: str,
    provider: str | None = None,
    model: str | None = None,
    used_fallback: bool = False,
    metadata: dict[str, object] | None = None,
) -> ConversationTurn:
    turn_no = await _next_conversation_turn_no(session=session, session_id=session_id)
    turn = ConversationTurn(
        session_id=session_id,
        turn_no=turn_no,
        role=role,
        content=content,
        provider=provider,
        model=model,
        used_fallback=used_fallback,
        metadata_json=metadata or {},
    )
    session.add(turn)
    await session.flush()
    return turn


async def _next_conversation_turn_no(*, session: AsyncSession, session_id: object) -> int:
    result = await session.execute(
        select(func.max(ConversationTurn.turn_no)).where(ConversationTurn.session_id == session_id)
    )
    return int(result.scalar_one_or_none() or 0) + 1


async def process_pending_jobs(
    *,
    session: AsyncSession,
    asset_store: LocalAssetStore,
    limit: int = 10,
) -> JobRunResponse:
    """Process pending jobs inside the API process."""
    completed = 0
    failed = 0
    jobs: list[ProcessingJobSummary] = []
    processed = 0

    while processed < limit:
        result = await session.execute(
            select(ProcessingJob.id)
            .where(ProcessingJob.status == "pending")
            .order_by(ProcessingJob.queued_at.asc())
            .limit(1)
        )
        job_id = result.scalar_one_or_none()
        if job_id is None:
            break
        try:
            job = await _run_single_job(session=session, asset_store=asset_store, job_id=job_id)
        except Exception:
            failed += 1
            jobs.append(await _get_processing_job_summary(session=session, job_id=job_id))
        else:
            if job.status == "completed":
                completed += 1
            elif job.status == "failed":
                failed += 1
            jobs.append(job)
        processed += 1

    return JobRunResponse(
        requested_limit=limit,
        processed=processed,
        completed=completed,
        failed=failed,
        jobs=jobs,
    )


async def _run_single_job(
    *,
    session: AsyncSession,
    asset_store: LocalAssetStore,
    job_id: object,
) -> ProcessingJobSummary:
    now = datetime.now(UTC)
    result = await session.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    job = result.scalar_one()
    job.status = "running"
    job.started_at = now
    job.attempts += 1
    await session.commit()

    try:
        if job.job_type == INDEX_SOURCE_VERSION_JOB:
            document = await _index_source_version(
                session=session,
                asset_store=asset_store,
                source_version_id=job.source_version_id,
            )
            await _enqueue_processing_job(
                session=session,
                source_version_id=job.source_version_id,
                job_type=COMPILE_KNOWLEDGE_JOB,
                payload={"derived_document_id": str(document.id)},
            )
            result_payload = {
                "derived_document_id": str(document.id),
                "token_count": document.token_count,
            }
        elif job.job_type == COMPILE_KNOWLEDGE_JOB:
            knowledge_item = await _compile_knowledge_item(
                session=session,
                source_version_id=job.source_version_id,
            )
            result_payload = {
                "knowledge_item_id": str(knowledge_item.id),
                "knowledge_type": knowledge_item.knowledge_type,
            }
        else:
            raise ValueError(f"unsupported job type: {job.job_type}")
    except Exception as exc:
        await session.rollback()
        result = await session.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
        failed_job = result.scalar_one()
        failed_job.status = "failed"
        failed_job.failed_at = datetime.now(UTC)
        failed_job.error_message = str(exc)
        await session.commit()
        return _to_processing_job_summary(failed_job)

    result = await session.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    completed_job = result.scalar_one()
    completed_job.status = "completed"
    completed_job.completed_at = datetime.now(UTC)
    completed_job.failed_at = None
    completed_job.error_message = None
    completed_job.result_json = result_payload
    await session.commit()
    return _to_processing_job_summary(completed_job)


async def _get_processing_job_summary(
    *,
    session: AsyncSession,
    job_id: object,
) -> ProcessingJobSummary:
    result = await session.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    return _to_processing_job_summary(result.scalar_one())


async def _index_source_version(
    *,
    session: AsyncSession,
    asset_store: LocalAssetStore,
    source_version_id: object,
) -> DerivedDocument:
    result = await session.execute(
        select(SourceVersion)
        .options(selectinload(SourceVersion.binary_assets), selectinload(SourceVersion.source_item))
        .where(SourceVersion.id == source_version_id)
    )
    source_version = result.scalar_one()
    source_item = source_version.source_item

    index_assets = [
        asset
        for asset in source_version.binary_assets
        if asset.asset_role != "request_envelope"
    ]
    if not index_assets:
        index_assets = list(source_version.binary_assets)

    snippets: list[str] = []
    for asset in index_assets:
        content = asset_store.read_bytes(relative_path=asset.relative_path)
        text = extract_text_content(
            content=content,
            mime_type=asset.mime_type,
            file_name=asset.file_name,
        )
        if text:
            snippets.append(text)

    combined_metadata = {
        **source_item.metadata_json,
        **source_version.metadata_json,
        "capture_method": source_version.capture_method,
        "device_context": source_version.device_context,
    }
    plain_text = build_indexable_text(
        title=source_item.title,
        snippets=snippets,
        metadata=combined_metadata,
    )
    embedding = compute_text_embedding(plain_text, dimensions=settings.embedding_dimensions)
    token_count = estimate_token_count(plain_text)

    derived_result = await session.execute(
        select(DerivedDocument).where(DerivedDocument.source_version_id == source_version.id)
    )
    derived_document = derived_result.scalar_one_or_none()
    if derived_document is None:
        derived_document = DerivedDocument(
            source_item_id=source_item.id,
            source_version_id=source_version.id,
            content_sha256=source_version.content_sha256,
            title=source_item.title,
            plain_text=plain_text,
            embedding=embedding,
            token_count=token_count,
            metadata_json={
                "source_type": source_item.source_type,
                "asset_roles": [asset.asset_role for asset in index_assets],
            },
        )
        session.add(derived_document)
    else:
        derived_document.content_sha256 = source_version.content_sha256
        derived_document.title = source_item.title
        derived_document.plain_text = plain_text
        derived_document.embedding = embedding
        derived_document.token_count = token_count
        derived_document.metadata_json = {
            "source_type": source_item.source_type,
            "asset_roles": [asset.asset_role for asset in index_assets],
        }
    await session.commit()
    return derived_document


async def _compile_knowledge_item(
    *,
    session: AsyncSession,
    source_version_id: object,
) -> KnowledgeItem:
    result = await session.execute(
        select(DerivedDocument)
        .options(
            selectinload(DerivedDocument.source_version).selectinload(SourceVersion.source_item)
        )
        .where(DerivedDocument.source_version_id == source_version_id)
    )
    derived_document = result.scalar_one()
    source_version = derived_document.source_version
    source_item = source_version.source_item

    title = derived_document.title or source_item.title or f"Insight {source_version.version_no}"
    summary = derived_document.plain_text[:SUMMARY_LENGTH] or None
    body_text = derived_document.plain_text
    slug = _build_knowledge_slug(
        knowledge_type="insight_card",
        title=title,
        source_version_id=source_version.id,
    )
    evidence = [
        f"source_item:{source_item.id}",
        f"source_version:{source_version.id}",
        f"derived_document:{derived_document.id}",
    ]

    knowledge_result = await session.execute(
        select(KnowledgeItem).where(KnowledgeItem.source_version_id == source_version.id)
    )
    knowledge_item = knowledge_result.scalar_one_or_none()
    if knowledge_item is None:
        knowledge_item = KnowledgeItem(
            knowledge_type="insight_card",
            status="active",
            slug=slug,
            title=title,
            summary=summary,
            body_text=body_text,
            source_item_id=source_item.id,
            source_version_id=source_version.id,
            derived_document_id=derived_document.id,
            evidence_json=evidence,
            metadata_json={
                "source_type": source_item.source_type,
                "generated_from": "derived_document",
            },
        )
        session.add(knowledge_item)
    else:
        knowledge_item.knowledge_type = "insight_card"
        knowledge_item.status = "active"
        knowledge_item.slug = slug
        knowledge_item.title = title
        knowledge_item.summary = summary
        knowledge_item.body_text = body_text
        knowledge_item.source_item_id = source_item.id
        knowledge_item.source_version_id = source_version.id
        knowledge_item.derived_document_id = derived_document.id
        knowledge_item.evidence_json = evidence
        knowledge_item.metadata_json = {
            "source_type": source_item.source_type,
            "generated_from": "derived_document",
        }
    await session.commit()
    return knowledge_item


async def search_derived_documents_text(
    *,
    session: AsyncSession,
    query: str,
    limit: int = 10,
) -> list[SearchResultItem]:
    """Search derived documents using PostgreSQL full text search."""
    tsquery = func.plainto_tsquery("simple", query)
    rank = func.ts_rank_cd(DerivedDocument.search_vector, tsquery).label("score")
    result = await session.execute(
        select(DerivedDocument, rank)
        .where(DerivedDocument.search_vector.op("@@")(tsquery))
        .order_by(rank.desc(), DerivedDocument.updated_at.desc())
        .limit(limit)
    )
    return [
        SearchResultItem(
            document=_to_derived_document_summary(document),
            score=float(score or 0.0),
            match_type="text",
        )
        for document, score in result.all()
    ]


async def search_derived_documents_semantic(
    *,
    session: AsyncSession,
    query: str,
    limit: int = 10,
) -> list[SearchResultItem]:
    """Search derived documents using in-process cosine similarity over stored embeddings."""
    query_embedding = compute_text_embedding(query, dimensions=settings.embedding_dimensions)
    result = await session.execute(
        select(DerivedDocument)
        .where(DerivedDocument.embedding.is_not(None))
        .order_by(DerivedDocument.updated_at.desc())
        .limit(max(limit * 20, 100))
    )
    candidates = result.scalars().all()

    scored = [
        (
            document,
            _cosine_similarity(query_embedding, document.embedding or []),
        )
        for document in candidates
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [
        SearchResultItem(
            document=_to_derived_document_summary(document),
            score=round(score, 6),
            match_type="semantic",
        )
        for document, score in scored[:limit]
    ]


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _build_knowledge_slug(
    *,
    knowledge_type: str,
    title: str,
    source_version_id: object,
) -> str:
    normalized_title = "".join(
        character.lower() if character.isalnum() else "-"
        for character in title.strip()
    )
    compact_title = "-".join(part for part in normalized_title.split("-") if part)
    suffix = str(source_version_id).split("-")[0]
    return f"{knowledge_type}-{compact_title or 'item'}-{suffix}"


def _compose_conversation_answer(
    *,
    question: str,
    knowledge_items: Sequence[KnowledgeItemSummary],
    evidence_items: Sequence[ConversationEvidenceItem],
) -> str:
    if knowledge_items:
        titles = "；".join(item.title for item in knowledge_items[:3])
        summary_parts = [item.summary for item in knowledge_items[:2] if item.summary]
        summary_text = " ".join(summary_parts).strip()
        if summary_text:
            return f"围绕“{question}”，当前最相关的知识对象包括：{titles}。{summary_text}"
        return f"围绕“{question}”，当前最相关的知识对象包括：{titles}。"

    if evidence_items:
        previews = " ".join(item.preview for item in evidence_items[:2]).strip()
        return f"围绕“{question}”，当前还没有沉淀出的知识对象，但原始证据显示：{previews}"

    return f"围绕“{question}”，当前还没有检索到足够的知识对象或原始证据。"


def _build_conversation_session_title(question: str) -> str:
    compact = " ".join(question.split())
    return compact[:80] or "Conversation Session"


def _select_latest_turn_window(
    turns: Sequence[ConversationTurn],
    *,
    limit: int,
) -> list[ConversationTurn]:
    if len(turns) <= limit:
        return list(turns)
    return list(turns[-limit:])


def _build_conversation_history_context(turns: Sequence[ConversationTurn]) -> str:
    if not turns:
        return ""
    return "\n".join(
        f"{'用户' if turn.role == 'user' else '助手'}: {turn.content}"
        for turn in turns
    )


async def _generate_conversation_answer_with_deepseek(
    *,
    question: str,
    history_turns: Sequence[ConversationTurn],
    knowledge_items: Sequence[KnowledgeItemSummary],
    evidence_items: Sequence[ConversationEvidenceItem],
    fallback_answer: str,
) -> LlmAnswer:
    history_context = _build_conversation_history_context(history_turns)
    knowledge_context = "\n".join(
        f"- {item.title}: {item.summary or ''}".strip()
        for item in knowledge_items
    )
    evidence_context = "\n".join(
        f"- {item.title or item.source_version_id}: {item.preview}".strip()
        for item in evidence_items
    )

    if not deepseek_client.enabled:
        return LlmAnswer(
            answer=fallback_answer,
            provider="local",
            model="fallback-template",
            used_fallback=True,
        )

    try:
        return await deepseek_client.answer(
            question=question,
            history_context=history_context,
            knowledge_context=knowledge_context,
            evidence_context=evidence_context,
        )
    except Exception:
        return LlmAnswer(
            answer=fallback_answer,
            provider="local",
            model="fallback-template",
            used_fallback=True,
        )


def _to_source_item_summary(item: SourceItem) -> SourceItemSummary:
    return SourceItemSummary(
        id=item.id,
        source_type=item.source_type,
        canonical_uri=item.canonical_uri,
        title=item.title,
        author=item.author,
        language_code=item.language_code,
        mime_type=item.mime_type,
        first_captured_at=item.first_captured_at,
        latest_captured_at=item.latest_captured_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        metadata=item.metadata_json,
    )


def _to_source_item_detail(item: SourceItem) -> SourceItemDetail:
    summary = _to_source_item_summary(item)
    return SourceItemDetail(
        **summary.model_dump(),
        version_count=len(item.versions),
        event_count=len(item.events),
    )


def _to_asset_response(asset: BinaryAsset) -> AssetRecordResponse:
    return AssetRecordResponse(
        id=asset.id,
        asset_role=asset.asset_role,
        storage_backend=asset.storage_backend,
        relative_path=asset.relative_path,
        file_name=asset.file_name,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        sha256=asset.sha256,
        created_at=asset.created_at,
        metadata=asset.metadata_json,
    )


def _to_source_version_summary(version: SourceVersion) -> SourceVersionSummary:
    return SourceVersionSummary(
        id=version.id,
        source_item_id=version.source_item_id,
        version_no=version.version_no,
        capture_method=version.capture_method,
        content_sha256=version.content_sha256,
        size_bytes=version.size_bytes,
        occurred_at=version.occurred_at,
        captured_at=version.captured_at,
        extractor_version=version.extractor_version,
        schema_version=version.schema_version,
        referrer_uri=version.referrer_uri,
        user_agent=version.user_agent,
        browser_profile=version.browser_profile,
        device_context=version.device_context,
        metadata=version.metadata_json,
    )


def _to_source_version_detail(version: SourceVersion) -> SourceVersionDetail:
    summary = _to_source_version_summary(version)
    return SourceVersionDetail(
        **summary.model_dump(),
        original_created_at=version.original_created_at,
        original_updated_at=version.original_updated_at,
        assets=[_to_asset_response(asset) for asset in version.binary_assets],
    )


def _to_event_summary(event: Event) -> EventSummary:
    return EventSummary(
        id=event.id,
        event_type=event.event_type,
        source_item_id=event.source_item_id,
        source_version_id=event.source_version_id,
        occurred_at=event.occurred_at,
        captured_at=event.captured_at,
        actor_id=event.actor_id,
        session_id=event.session_id,
        metadata=event.metadata_json,
    )


def _to_event_detail(event: Event) -> EventDetail:
    return EventDetail(**_to_event_summary(event).model_dump())


def _to_conversation_turn_item(turn: ConversationTurn) -> ConversationTurnItem:
    return ConversationTurnItem(
        id=turn.id,
        session_id=turn.session_id,
        turn_no=turn.turn_no,
        role=turn.role,
        content=turn.content,
        provider=turn.provider,
        model=turn.model,
        used_fallback=turn.used_fallback,
        created_at=turn.created_at,
        metadata=turn.metadata_json,
    )


def _to_derived_document_summary(document: DerivedDocument) -> DerivedDocumentSummary:
    return DerivedDocumentSummary(
        id=document.id,
        source_item_id=document.source_item_id,
        source_version_id=document.source_version_id,
        content_sha256=document.content_sha256,
        title=document.title,
        plain_text_preview=document.plain_text[:PREVIEW_LENGTH],
        token_count=document.token_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
        metadata=document.metadata_json,
    )


def _to_processing_job_summary(job: ProcessingJob) -> ProcessingJobSummary:
    return ProcessingJobSummary(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        source_version_id=job.source_version_id,
        attempts=job.attempts,
        queued_at=job.queued_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        failed_at=job.failed_at,
        error_message=job.error_message,
        payload=job.payload_json,
        result=job.result_json,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _to_knowledge_item_summary(item: KnowledgeItem) -> KnowledgeItemSummary:
    return KnowledgeItemSummary(
        id=item.id,
        knowledge_type=item.knowledge_type,
        status=item.status,
        slug=item.slug,
        title=item.title,
        summary=item.summary,
        source_item_id=item.source_item_id,
        source_version_id=item.source_version_id,
        derived_document_id=item.derived_document_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        metadata=item.metadata_json,
    )


def _to_knowledge_item_detail(item: KnowledgeItem) -> KnowledgeItemDetail:
    summary = _to_knowledge_item_summary(item)
    return KnowledgeItemDetail(
        **summary.model_dump(),
        body_text=item.body_text,
        evidence=item.evidence_json,
    )
