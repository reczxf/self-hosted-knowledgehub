"""Persistence logic for ingest operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BinaryAsset, Event, SourceItem, SourceVersion
from app.schemas import IngestResponse, WebPageIngestRequest
from app.storage import LocalAssetStore


async def ingest_webpage(
    *,
    session: AsyncSession,
    payload: WebPageIngestRequest,
    asset_store: LocalAssetStore,
) -> IngestResponse:
    """Persist a webpage capture into database and local storage."""
    canonical_uri = payload.canonical_url or payload.url
    now = payload.captured_at or datetime.now(UTC)

    source_item = await _get_or_create_source_item(
        session=session,
        payload=payload,
        canonical_uri=canonical_uri,
        captured_at=now,
    )

    version_no = await _next_version_no(session=session, source_item_id=source_item.id)

    envelope_asset = asset_store.store_json(
        category="captures",
        suggested_name="envelope.json",
        payload=payload.model_dump(mode="json"),
    )

    asset_records: list[BinaryAsset] = [
        BinaryAsset(
            source_version_id=None,  # set after source version is created
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
    content_sha256 = envelope_asset.sha256

    source_version = SourceVersion(
        source_item_id=source_item.id,
        version_no=version_no,
        capture_method=payload.capture_method,
        content_sha256=content_sha256,
        size_bytes=total_asset_bytes,
        occurred_at=payload.occurred_at,
        captured_at=now,
        original_created_at=payload.original_created_at,
        original_updated_at=payload.original_updated_at,
        extractor_version=payload.extractor_version,
        schema_version=payload.schema_version,
        referrer_uri=payload.referrer_url,
        user_agent=payload.user_agent,
        browser_profile=payload.browser_profile,
        metadata_json=payload.metadata,
    )
    session.add(source_version)
    await session.flush()

    for asset in payload.assets:
        raw_bytes = asset_store.decode_asset_content(
            content_base64=asset.content_base64,
            text_content=asset.text_content,
        )
        stored = asset_store.store_bytes(
            category="captures",
            suggested_name=asset.file_name or f"{asset.asset_role}.bin",
            content=raw_bytes,
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
    if payload.assets:
        source_version.content_sha256 = asset_records[1].sha256

    for asset_record in asset_records:
        asset_record.source_version_id = source_version.id
        session.add(asset_record)

    event = Event(
        event_type=payload.event_type,
        source_item_id=source_item.id,
        source_version_id=source_version.id,
        occurred_at=payload.occurred_at,
        captured_at=now,
        actor_id=payload.actor_id,
        session_id=payload.session_id,
        metadata_json={
            "capture_method": payload.capture_method,
            "url": payload.url,
            "canonical_url": canonical_uri,
        },
    )
    session.add(event)

    source_item.latest_captured_at = now
    await session.commit()

    return IngestResponse(
        source_item_id=str(source_item.id),
        source_version_id=str(source_version.id),
        event_id=str(event.id),
        asset_count=len(asset_records),
    )


async def _get_or_create_source_item(
    *,
    session: AsyncSession,
    payload: WebPageIngestRequest,
    canonical_uri: str,
    captured_at: datetime,
) -> SourceItem:
    result = await session.execute(
        select(SourceItem).where(
            SourceItem.source_type == payload.source_type,
            SourceItem.canonical_uri == canonical_uri,
        )
    )
    source_item = result.scalar_one_or_none()
    if source_item is not None:
        if payload.title is not None:
            source_item.title = payload.title
        if payload.author is not None:
            source_item.author = payload.author
        if payload.language is not None:
            source_item.language_code = payload.language
        if payload.mime_type is not None:
            source_item.mime_type = payload.mime_type
        source_item.latest_captured_at = captured_at
        return source_item

    source_item = SourceItem(
        source_type=payload.source_type,
        canonical_uri=canonical_uri,
        title=payload.title,
        author=payload.author,
        language_code=payload.language,
        mime_type=payload.mime_type,
        first_captured_at=captured_at,
        latest_captured_at=captured_at,
        metadata_json={"url": payload.url, **payload.metadata},
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

