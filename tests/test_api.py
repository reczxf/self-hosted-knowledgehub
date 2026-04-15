from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from app import main
from app.database import get_db_session
from app.schemas import (
    ConversationAnswerResponse,
    ConversationTurnItem,
    DerivedDocumentSummary,
    EventDetail,
    EventSummary,
    IngestResponse,
    JobRunResponse,
    KnowledgeItemDetail,
    KnowledgeItemSummary,
    ProcessingJobSummary,
    SearchResultItem,
    SourceItemSummary,
    SourceVersionDetail,
    SourceVersionSummary,
)


@pytest_asyncio.fixture
async def client() -> httpx.AsyncClient:
    main.settings.init_db_on_startup = False

    async def override_session():
        yield object()

    main.app.dependency_overrides[get_db_session] = override_session
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    main.app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("path", "target_name", "payload"),
    [
        (
            "/ingest/bookmark",
            "ingest_bookmark",
            {
                "capture_method": "browser_extension",
                "url": "https://example.com/bookmark",
                "occurred_at": "2026-04-15T10:00:00Z",
            },
        ),
        (
            "/ingest/search",
            "ingest_search",
            {
                "capture_method": "browser_extension",
                "url": "https://example.com/search?q=pkos",
                "query": "pkos",
                "occurred_at": "2026-04-15T10:00:00Z",
            },
        ),
        (
            "/ingest/chat",
            "ingest_chat",
            {
                "capture_method": "api_push",
                "provider": "openai",
                "thread_id": "thread-123",
                "occurred_at": "2026-04-15T10:00:00Z",
                "messages": [{"role": "user", "content": "hello"}],
            },
        ),
    ],
)
async def test_new_ingest_endpoints(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    target_name: str,
    payload: dict[str, object],
) -> None:
    async def fake_ingest(**_: object) -> IngestResponse:
        return IngestResponse(
            source_item_id=str(uuid4()),
            source_version_id=str(uuid4()),
            event_id=str(uuid4()),
            asset_count=2,
        )

    monkeypatch.setattr(main, target_name, fake_ingest)

    response = await client.post(path, json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["asset_count"] == 2
    assert body["version_created"] is True
    assert body["deduplicated"] is False
    assert body["source_item_id"]
    assert body["source_version_id"]
    assert body["event_id"]


async def test_upload_ingest_endpoint(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_ingest_document(**_: object) -> IngestResponse:
        return IngestResponse(
            source_item_id=str(uuid4()),
            source_version_id=str(uuid4()),
            event_id=str(uuid4()),
            asset_count=2,
        )

    monkeypatch.setattr(main, "ingest_document", fake_ingest_document)

    response = await client.post(
        "/ingest/upload",
        files={"file": ("notes.txt", b"pkos notes", "text/plain")},
        data={"title": "Local Notes"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["asset_count"] == 2
    assert body["version_created"] is True


async def test_root_redirects_to_ui(client: httpx.AsyncClient) -> None:
    response = await client.get("/", follow_redirects=False)

    assert response.status_code in (307, 308)
    assert response.headers["location"] == "/ui"


async def test_ui_page_is_served(client: httpx.AsyncClient) -> None:
    response = await client.get("/ui")

    assert response.status_code in (200, 503)
    assert "PKOS Studio" in response.text or "frontend build not found" in response.text


async def test_list_sources_endpoint(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)

    async def fake_list_sources(**_: object) -> list[SourceItemSummary]:
        return [
            SourceItemSummary(
                id=uuid4(),
                source_type="web_page",
                canonical_uri="https://example.com/a",
                title="A",
                author=None,
                language_code="zh",
                mime_type="text/html",
                first_captured_at=now,
                latest_captured_at=now,
                created_at=now,
                updated_at=now,
                metadata={},
            )
        ]

    monkeypatch.setattr(main, "list_source_items", fake_list_sources)

    response = await client.get("/sources?source_type=web_page&limit=10&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["source_type"] == "web_page"


async def test_get_source_endpoint_not_found(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_source(**_: object) -> None:
        return None

    monkeypatch.setattr(main, "get_source_item", fake_get_source)

    response = await client.get(f"/sources/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "source item not found"


async def test_list_source_versions_endpoint(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    source_item_id = uuid4()

    async def fake_list_versions(**_: object) -> list[SourceVersionSummary]:
        return [
            SourceVersionSummary(
                id=uuid4(),
                source_item_id=source_item_id,
                version_no=1,
                capture_method="browser_extension",
                content_sha256="abc",
                size_bytes=123,
                occurred_at=now,
                captured_at=now,
                extractor_version="1.0.0",
                schema_version="1",
                referrer_uri=None,
                user_agent=None,
                browser_profile=None,
                metadata={},
            )
        ]

    monkeypatch.setattr(main, "list_source_versions", fake_list_versions)

    response = await client.get(f"/sources/{source_item_id}/versions")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["version_no"] == 1


async def test_get_source_version_endpoint(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    source_version_id = uuid4()
    source_item_id = uuid4()

    async def fake_get_version(**_: object) -> SourceVersionDetail:
        return SourceVersionDetail(
            id=source_version_id,
            source_item_id=source_item_id,
            version_no=2,
            capture_method="browser_extension",
            content_sha256="def",
            size_bytes=456,
            occurred_at=now,
            captured_at=now,
            extractor_version="1.0.0",
            schema_version="1",
            referrer_uri=None,
            user_agent=None,
            browser_profile=None,
            metadata={},
            original_created_at=None,
            original_updated_at=None,
            assets=[],
        )

    monkeypatch.setattr(main, "get_source_version", fake_get_version)

    response = await client.get(f"/versions/{source_version_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(source_version_id)


async def test_list_events_and_get_event_endpoints(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    event_id = uuid4()

    async def fake_list_events(**_: object) -> list[EventSummary]:
        return [
            EventSummary(
                id=event_id,
                event_type="capture.web_page",
                source_item_id=None,
                source_version_id=None,
                occurred_at=now,
                captured_at=now,
                actor_id=None,
                session_id=None,
                metadata={"url": "https://example.com"},
            )
        ]

    async def fake_get_event(**_: object) -> EventDetail:
        return EventDetail(
            id=event_id,
            event_type="capture.web_page",
            source_item_id=None,
            source_version_id=None,
            occurred_at=now,
            captured_at=now,
            actor_id=None,
            session_id=None,
            metadata={"url": "https://example.com"},
        )

    monkeypatch.setattr(main, "list_events", fake_list_events)
    monkeypatch.setattr(main, "get_event", fake_get_event)

    list_response = await client.get("/events")
    detail_response = await client.get(f"/events/{event_id}")

    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == str(event_id)


async def test_jobs_endpoints(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    source_version_id = uuid4()
    job_id = uuid4()

    async def fake_list_jobs(**_: object) -> list[ProcessingJobSummary]:
        return [
            ProcessingJobSummary(
                id=job_id,
                job_type="index_source_version",
                status="pending",
                source_version_id=source_version_id,
                attempts=0,
                queued_at=now,
                started_at=None,
                completed_at=None,
                failed_at=None,
                error_message=None,
                payload={"source_version_id": str(source_version_id)},
                result={},
                created_at=now,
                updated_at=now,
            )
        ]

    async def fake_run_jobs(**_: object) -> JobRunResponse:
        return JobRunResponse(
            requested_limit=5,
            processed=1,
            completed=1,
            failed=0,
            jobs=await fake_list_jobs(),
        )

    monkeypatch.setattr(main, "list_processing_jobs", fake_list_jobs)
    monkeypatch.setattr(main, "process_pending_jobs", fake_run_jobs)

    list_response = await client.get("/jobs")
    run_response = await client.post("/jobs/run?limit=5")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["job_type"] == "index_source_version"
    assert run_response.status_code == 200
    assert run_response.json()["completed"] == 1


async def test_search_endpoints(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    document = DerivedDocumentSummary(
        id=uuid4(),
        source_item_id=uuid4(),
        source_version_id=uuid4(),
        content_sha256="abc",
        title="PKOS",
        plain_text_preview="PKOS memory layer",
        token_count=12,
        created_at=now,
        updated_at=now,
        metadata={"source_type": "web_page"},
    )

    async def fake_text_search(**_: object) -> list[SearchResultItem]:
        return [SearchResultItem(document=document, score=0.9, match_type="text")]

    async def fake_semantic_search(**_: object) -> list[SearchResultItem]:
        return [SearchResultItem(document=document, score=0.8, match_type="semantic")]

    monkeypatch.setattr(main, "search_derived_documents_text", fake_text_search)
    monkeypatch.setattr(main, "search_derived_documents_semantic", fake_semantic_search)

    text_response = await client.get("/search/text?q=pkos")
    semantic_response = await client.get("/search/semantic?q=knowledge")

    assert text_response.status_code == 200
    assert text_response.json()["items"][0]["match_type"] == "text"
    assert semantic_response.status_code == 200
    assert semantic_response.json()["items"][0]["match_type"] == "semantic"


async def test_knowledge_endpoints(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    knowledge_id = uuid4()

    async def fake_list_knowledge(**_: object) -> list[KnowledgeItemSummary]:
        return [
            KnowledgeItemSummary(
                id=knowledge_id,
                knowledge_type="insight_card",
                status="active",
                slug="insight-card-pkos-1234",
                title="PKOS Insight",
                summary="PKOS memory layer summary",
                source_item_id=None,
                source_version_id=None,
                derived_document_id=None,
                created_at=now,
                updated_at=now,
                metadata={"source_type": "web_page"},
            )
        ]

    async def fake_get_knowledge(**_: object) -> KnowledgeItemDetail:
        return KnowledgeItemDetail(
            id=knowledge_id,
            knowledge_type="insight_card",
            status="active",
            slug="insight-card-pkos-1234",
            title="PKOS Insight",
            summary="PKOS memory layer summary",
            source_item_id=None,
            source_version_id=None,
            derived_document_id=None,
            created_at=now,
            updated_at=now,
            metadata={"source_type": "web_page"},
            body_text="PKOS memory layer summary body",
            evidence=["source_item:1", "source_version:2"],
        )

    monkeypatch.setattr(main, "list_knowledge_items", fake_list_knowledge)
    monkeypatch.setattr(main, "get_knowledge_item", fake_get_knowledge)

    list_response = await client.get("/knowledge")
    detail_response = await client.get(f"/knowledge/{knowledge_id}")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["knowledge_type"] == "insight_card"
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == str(knowledge_id)


async def test_conversation_answer_endpoint(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    conversation_session_id = uuid4()

    async def fake_answer_question(**_: object) -> ConversationAnswerResponse:
        return ConversationAnswerResponse(
            session_id=conversation_session_id,
            question="PKOS 现在能做什么？",
            answer="当前可以基于知识对象和原始证据返回结构化回答。",
            provider="deepseek",
            model="deepseek-chat",
            used_fallback=False,
            conversation_turns=[
                ConversationTurnItem(
                    id=uuid4(),
                    session_id=conversation_session_id,
                    turn_no=1,
                    role="user",
                    content="PKOS 现在能做什么？",
                    created_at=now,
                    metadata={},
                ),
                ConversationTurnItem(
                    id=uuid4(),
                    session_id=conversation_session_id,
                    turn_no=2,
                    role="assistant",
                    content="当前可以基于知识对象和原始证据返回结构化回答。",
                    provider="deepseek",
                    model="deepseek-chat",
                    used_fallback=False,
                    created_at=now,
                    metadata={},
                ),
            ],
            knowledge_items=[
                KnowledgeItemSummary(
                    id=uuid4(),
                    knowledge_type="insight_card",
                    status="active",
                    slug="insight-card-pkos",
                    title="PKOS Insight",
                    summary="PKOS 已有最小知识层",
                    source_item_id=None,
                    source_version_id=None,
                    derived_document_id=None,
                    created_at=now,
                    updated_at=now,
                    metadata={},
                )
            ],
            evidence_items=[],
        )

    monkeypatch.setattr(main, "answer_conversation_question", fake_answer_question)

    response = await client.post(
        "/conversation/answer",
        json={"question": "PKOS 现在能做什么？", "search_mode": "hybrid", "limit": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert "结构化回答" in body["answer"]
    assert body["provider"] == "deepseek"
    assert body["session_id"] == str(conversation_session_id)
    assert len(body["conversation_turns"]) == 2


async def test_conversation_answer_endpoint_returns_404_for_unknown_session(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_answer_question(**_: object) -> ConversationAnswerResponse:
        raise ValueError("conversation session not found: missing-session")

    monkeypatch.setattr(main, "answer_conversation_question", fake_answer_question)

    response = await client.post(
        "/conversation/answer",
        json={
            "question": "继续刚才的话题",
            "session_id": str(uuid4()),
            "search_mode": "hybrid",
            "limit": 5,
        },
    )

    assert response.status_code == 404
    assert "conversation session not found" in response.json()["detail"]
