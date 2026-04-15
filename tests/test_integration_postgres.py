from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import main
from app.bootstrap import ensure_runtime_schema
from app.database import Base, get_db_session
from app.models import (
    ConversationSession,
    ConversationTurn,
    DerivedDocument,
    Event,
    KnowledgeItem,
    ProcessingJob,
    SourceVersion,
)
from app.repositories import (
    ingest_webpage,
    process_pending_jobs,
    search_derived_documents_semantic,
    search_derived_documents_text,
)
from app.schemas import InlineAssetCreate, WebPageIngestRequest
from app.storage import LocalAssetStore

TEST_DATABASE_URL = os.getenv("PKOS_TEST_DATABASE_URL")


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def postgres_session(tmp_path: Path) -> AsyncIterator[tuple[AsyncSession, LocalAssetStore]]:
    if not TEST_DATABASE_URL:
        pytest.skip("PKOS_TEST_DATABASE_URL is not set")

    asset_store = LocalAssetStore(tmp_path)
    asset_store.ensure_directories()
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        connect_args={"timeout": 3},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
    except Exception as exc:  # pragma: no cover - depends on local environment
        await engine.dispose()
        pytest.skip(f"test database is unavailable: {exc}")

    async with session_factory() as session:
        yield session, asset_store

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def postgres_api_client(
    tmp_path: Path,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], LocalAssetStore]]:
    if not TEST_DATABASE_URL:
        pytest.skip("PKOS_TEST_DATABASE_URL is not set")

    asset_store = LocalAssetStore(tmp_path)
    asset_store.ensure_directories()
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        connect_args={"timeout": 3},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
            await ensure_runtime_schema(connection)
    except Exception as exc:  # pragma: no cover - depends on local environment
        await engine.dispose()
        pytest.skip(f"test database is unavailable: {exc}")

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    original_asset_store = main.asset_store
    main.app.dependency_overrides[get_db_session] = override_session
    main.asset_store = asset_store
    main.settings.init_db_on_startup = False

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_factory, asset_store

    main.app.dependency_overrides.clear()
    main.asset_store = original_asset_store
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def test_ingest_webpage_deduplicates_same_content(
    postgres_session: tuple[AsyncSession, LocalAssetStore],
) -> None:
    session, asset_store = postgres_session
    payload = WebPageIngestRequest(
        capture_method="browser_extension",
        url="https://example.com/articles/pkos",
        canonical_url="https://example.com/articles/pkos",
        title="PKOS",
        occurred_at=datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
        device_context="desktop.chrome",
        assets=[
            InlineAssetCreate(
                asset_role="page_html",
                file_name="page.html",
                mime_type="text/html",
                text_content="<html><body><h1>PKOS</h1><p>Memory layer notes</p></body></html>",
            )
        ],
    )

    first = await ingest_webpage(session=session, payload=payload, asset_store=asset_store)
    second = await ingest_webpage(session=session, payload=payload, asset_store=asset_store)

    version_count = await session.scalar(select(func.count()).select_from(SourceVersion))
    event_count = await session.scalar(select(func.count()).select_from(Event))
    job_count = await session.scalar(select(func.count()).select_from(ProcessingJob))

    assert first.version_created is True
    assert first.deduplicated is False
    assert second.version_created is False
    assert second.deduplicated is True
    assert first.source_version_id == second.source_version_id
    assert version_count == 1
    assert event_count == 2
    assert job_count == 1


async def test_process_jobs_builds_indexes_and_enables_search(
    postgres_session: tuple[AsyncSession, LocalAssetStore],
) -> None:
    session, asset_store = postgres_session
    payload = WebPageIngestRequest(
        capture_method="browser_extension",
        url="https://example.com/articles/memory-layer",
        canonical_url="https://example.com/articles/memory-layer",
        title="Memory Layer",
        occurred_at=datetime(2026, 4, 15, 11, 0, tzinfo=UTC),
        metadata={"topic": "pkos", "tags": ["memory", "search"]},
        assets=[
            InlineAssetCreate(
                asset_role="page_html",
                file_name="page.html",
                mime_type="text/html",
                text_content=(
                    "<html><body><h1>PKOS Memory Layer</h1>"
                    "<p>Semantic search and full text retrieval.</p></body></html>"
                ),
            )
        ],
    )

    ingest_result = await ingest_webpage(session=session, payload=payload, asset_store=asset_store)
    job_result = await process_pending_jobs(session=session, asset_store=asset_store, limit=10)

    derived_count = await session.scalar(select(func.count()).select_from(DerivedDocument))
    knowledge_count = await session.scalar(select(func.count()).select_from(KnowledgeItem))
    stored_document = await session.scalar(select(DerivedDocument))
    stored_knowledge = await session.scalar(select(KnowledgeItem))
    text_results = await search_derived_documents_text(
        session=session,
        query="semantic retrieval",
        limit=5,
    )
    semantic_results = await search_derived_documents_semantic(
        session=session,
        query="memory search",
        limit=5,
    )

    assert ingest_result.version_created is True
    assert job_result.processed == 2
    assert job_result.completed == 2
    assert derived_count == 1
    assert knowledge_count == 1
    assert stored_document is not None
    assert stored_knowledge is not None
    assert "PKOS Memory Layer" in stored_document.plain_text
    assert stored_knowledge.knowledge_type == "insight_card"
    assert stored_knowledge.source_version_id == stored_document.source_version_id
    assert stored_document.embedding is not None
    assert len(stored_document.embedding) == 64
    assert text_results
    assert text_results[0].document.source_version_id == stored_document.source_version_id
    assert semantic_results
    assert semantic_results[0].document.source_version_id == stored_document.source_version_id


async def test_api_ingest_run_jobs_and_search_roundtrip(
    postgres_api_client: tuple[
        httpx.AsyncClient,
        async_sessionmaker[AsyncSession],
        LocalAssetStore,
    ],
) -> None:
    client, session_factory, _asset_store = postgres_api_client

    ingest_response = await client.post(
        "/ingest/webpage",
        json={
            "capture_method": "browser_extension",
            "url": "https://example.com/articles/conversation-layer",
            "canonical_url": "https://example.com/articles/conversation-layer",
            "title": "Conversation Layer",
            "occurred_at": "2026-04-15T12:00:00Z",
            "metadata": {"topic": "conversation", "tags": ["deepseek", "answering"]},
            "assets": [
                {
                    "asset_role": "page_html",
                    "file_name": "conversation.html",
                    "mime_type": "text/html",
                    "text_content": (
                        "<html><body><h1>PKOS Conversation Layer</h1>"
                        "<p>DeepSeek answers are grounded by knowledge items and raw evidence.</p>"
                        "</body></html>"
                    ),
                }
            ],
        },
    )

    assert ingest_response.status_code == 201
    ingest_body = ingest_response.json()
    assert ingest_body["version_created"] is True
    assert ingest_body["deduplicated"] is False

    jobs_response = await client.post("/jobs/run?limit=10")

    assert jobs_response.status_code == 200
    jobs_body = jobs_response.json()
    assert jobs_body["processed"] == 2
    assert jobs_body["completed"] == 2
    assert jobs_body["failed"] == 0

    text_response = await client.get("/search/text?q=grounded%20evidence&limit=5")
    semantic_response = await client.get("/search/semantic?q=conversation%20knowledge&limit=5")

    assert text_response.status_code == 200
    assert semantic_response.status_code == 200
    assert text_response.json()["items"]
    assert semantic_response.json()["items"]
    assert text_response.json()["items"][0]["document"]["title"] == "Conversation Layer"
    assert semantic_response.json()["items"][0]["document"]["title"] == "Conversation Layer"

    async with session_factory() as session:
        derived_count = await session.scalar(select(func.count()).select_from(DerivedDocument))
        knowledge_count = await session.scalar(select(func.count()).select_from(KnowledgeItem))

    assert derived_count == 1
    assert knowledge_count == 1


async def test_conversation_answer_persists_session_and_turns(
    postgres_api_client: tuple[
        httpx.AsyncClient,
        async_sessionmaker[AsyncSession],
        LocalAssetStore,
    ],
) -> None:
    client, session_factory, _asset_store = postgres_api_client

    await client.post(
        "/ingest/webpage",
        json={
            "capture_method": "browser_extension",
            "url": "https://example.com/articles/pkos-overview",
            "canonical_url": "https://example.com/articles/pkos-overview",
            "title": "PKOS Overview",
            "occurred_at": "2026-04-15T13:00:00Z",
            "assets": [
                {
                    "asset_role": "page_html",
                    "file_name": "overview.html",
                    "mime_type": "text/html",
                    "text_content": (
                        "<html><body><h1>PKOS Overview</h1>"
                        "<p>PKOS stores sources, builds knowledge, and answers questions.</p>"
                        "</body></html>"
                    ),
                }
            ],
        },
    )
    await client.post("/jobs/run?limit=10")

    first_response = await client.post(
        "/conversation/answer",
        json={"question": "PKOS 是什么？", "search_mode": "hybrid", "limit": 5},
    )

    assert first_response.status_code == 200
    first_body = first_response.json()
    assert first_body["session_id"]
    assert len(first_body["conversation_turns"]) == 2

    second_response = await client.post(
        "/conversation/answer",
        json={
            "question": "它现在能做什么？",
            "session_id": first_body["session_id"],
            "search_mode": "hybrid",
            "limit": 5,
        },
    )

    assert second_response.status_code == 200
    second_body = second_response.json()
    assert second_body["session_id"] == first_body["session_id"]
    assert len(second_body["conversation_turns"]) == 4

    async with session_factory() as session:
        session_count = await session.scalar(select(func.count()).select_from(ConversationSession))
        turn_count = await session.scalar(select(func.count()).select_from(ConversationTurn))

    assert session_count == 1
    assert turn_count == 4
