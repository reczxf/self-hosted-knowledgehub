"""FastAPI entrypoint for the PKOS collector."""

from __future__ import annotations

import base64
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap import ensure_runtime_schema
from app.config import settings
from app.database import Base, engine, get_db_session
from app.repositories import (
    answer_conversation_question,
    get_event,
    get_knowledge_item,
    get_source_item,
    get_source_version,
    ingest_bookmark,
    ingest_chat,
    ingest_document,
    ingest_search,
    ingest_webpage,
    list_events,
    list_knowledge_items,
    list_processing_jobs,
    list_source_items,
    list_source_versions,
    process_pending_jobs,
    search_derived_documents_semantic,
    search_derived_documents_text,
)
from app.schemas import (
    BookmarkIngestRequest,
    ChatIngestRequest,
    ConversationAnswerResponse,
    ConversationAskRequest,
    DocumentIngestRequest,
    EventDetail,
    EventListResponse,
    IngestResponse,
    JobRunResponse,
    KnowledgeItemDetail,
    KnowledgeItemListResponse,
    ProcessingJobListResponse,
    SearchIngestRequest,
    SearchResultsResponse,
    SourceItemDetail,
    SourceItemListResponse,
    SourceVersionDetail,
    SourceVersionListResponse,
    WebPageIngestRequest,
)
from app.storage import LocalAssetStore

asset_store = LocalAssetStore(settings.data_dir)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
frontend_dist_dir = frontend_dir / "dist"
ui_assets_dir = frontend_dist_dir / "assets"
ui_index_path = frontend_dist_dir / "index.html"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize storage directories and database schema."""
    if settings.init_db_on_startup:
        asset_store.ensure_directories()
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await ensure_runtime_schema(connection)
    yield


app = FastAPI(title="PKOS Collector", version="0.1.0", lifespan=lifespan)
app.mount(
    "/ui/assets",
    StaticFiles(directory=ui_assets_dir, check_dir=False),
    name="ui-assets",
)
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    """Redirect the root URL to the built-in dashboard."""
    return RedirectResponse(url="/ui")


@app.get("/ui", include_in_schema=False)
async def ui_dashboard() -> HTMLResponse:
    """Serve the built-in web dashboard."""
    if not ui_index_path.exists():
        return HTMLResponse(
            (
                "<html><body style='font-family: sans-serif; padding: 40px;'>"
                "<h1>PKOS Studio frontend build not found</h1>"
                "<p>请先在仓库根目录执行：</p>"
                "<pre>cd frontend\nnpm install\nnpm run build</pre>"
                "<p>然后刷新 <code>/ui</code>。</p>"
                "</body></html>"
            ),
            status_code=503,
        )
    return HTMLResponse(ui_index_path.read_text(encoding="utf-8"))


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    """Liveness endpoint."""
    return {"status": "ok"}


@app.post("/ingest/webpage", response_model=IngestResponse, status_code=201)
async def ingest_webpage_endpoint(
    payload: WebPageIngestRequest,
    session: DbSession,
) -> IngestResponse:
    """Ingest a webpage capture and persist assets locally."""
    return await ingest_webpage(session=session, payload=payload, asset_store=asset_store)


@app.post("/ingest/bookmark", response_model=IngestResponse, status_code=201)
async def ingest_bookmark_endpoint(
    payload: BookmarkIngestRequest,
    session: DbSession,
) -> IngestResponse:
    """Ingest a bookmark capture and persist assets locally."""
    return await ingest_bookmark(session=session, payload=payload, asset_store=asset_store)


@app.post("/ingest/search", response_model=IngestResponse, status_code=201)
async def ingest_search_endpoint(
    payload: SearchIngestRequest,
    session: DbSession,
) -> IngestResponse:
    """Ingest a search result capture and persist assets locally."""
    return await ingest_search(session=session, payload=payload, asset_store=asset_store)


@app.post("/ingest/chat", response_model=IngestResponse, status_code=201)
async def ingest_chat_endpoint(
    payload: ChatIngestRequest,
    session: DbSession,
) -> IngestResponse:
    """Ingest a chat thread and persist assets locally."""
    return await ingest_chat(session=session, payload=payload, asset_store=asset_store)


@app.post("/ingest/upload", response_model=IngestResponse, status_code=201)
async def ingest_upload_endpoint(
    session: DbSession,
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str | None, Form()] = None,
    occurred_at: Annotated[str | None, Form()] = None,
    capture_method: Annotated[str, Form()] = "manual_upload",
    device_context: Annotated[str | None, Form()] = None,
) -> IngestResponse:
    """Ingest a local uploaded file as a document source."""
    file_bytes = await file.read()
    payload = DocumentIngestRequest(
        capture_method=capture_method,
        occurred_at=datetime.fromisoformat(occurred_at) if occurred_at else datetime.now(UTC),
        device_context=device_context,
        file_name=file.filename or "upload.bin",
        title=title or file.filename or "Uploaded Document",
        mime_type=file.content_type,
        assets=[
            {
                "asset_role": "uploaded_file",
                "file_name": file.filename or "upload.bin",
                "mime_type": file.content_type,
                "content_base64": None,
                "text_content": file_bytes.decode("utf-8", errors="ignore")
                if (file.content_type or "").startswith("text/")
                or (file.filename or "").lower().endswith((".txt", ".md", ".html", ".htm", ".json"))
                else None,
            }
        ],
        metadata={"upload_size_bytes": len(file_bytes)},
    )
    if payload.assets[0].text_content is None:
        payload.assets[0].content_base64 = base64.b64encode(file_bytes).decode("ascii")

    return await ingest_document(session=session, payload=payload, asset_store=asset_store)


@app.get("/sources", response_model=SourceItemListResponse)
async def list_sources_endpoint(
    session: DbSession,
    source_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SourceItemListResponse:
    """List source items."""
    items = await list_source_items(
        session=session,
        source_type=source_type,
        limit=limit,
        offset=offset,
    )
    return SourceItemListResponse(items=items, limit=limit, offset=offset)


@app.get("/sources/{source_item_id}", response_model=SourceItemDetail)
async def get_source_endpoint(source_item_id: str, session: DbSession) -> SourceItemDetail:
    """Get a source item by id."""
    item = await get_source_item(session=session, source_item_id=source_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="source item not found")
    return item


@app.get("/sources/{source_item_id}/versions", response_model=SourceVersionListResponse)
async def list_source_versions_endpoint(
    source_item_id: str,
    session: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SourceVersionListResponse:
    """List versions for a source item."""
    items = await list_source_versions(
        session=session,
        source_item_id=source_item_id,
        limit=limit,
        offset=offset,
    )
    return SourceVersionListResponse(items=items, limit=limit, offset=offset)


@app.get("/versions/{source_version_id}", response_model=SourceVersionDetail)
async def get_source_version_endpoint(
    source_version_id: str,
    session: DbSession,
) -> SourceVersionDetail:
    """Get a source version by id."""
    version = await get_source_version(session=session, source_version_id=source_version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="source version not found")
    return version


@app.get("/events", response_model=EventListResponse)
async def list_events_endpoint(
    session: DbSession,
    event_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> EventListResponse:
    """List events."""
    items = await list_events(
        session=session,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    return EventListResponse(items=items, limit=limit, offset=offset)


@app.get("/events/{event_id}", response_model=EventDetail)
async def get_event_endpoint(event_id: str, session: DbSession) -> EventDetail:
    """Get an event by id."""
    event = await get_event(session=session, event_id=event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    return event


@app.get("/jobs", response_model=ProcessingJobListResponse)
async def list_jobs_endpoint(
    session: DbSession,
    status: str | None = None,
    job_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ProcessingJobListResponse:
    """List processing jobs."""
    items = await list_processing_jobs(
        session=session,
        status=status,
        job_type=job_type,
        limit=limit,
        offset=offset,
    )
    return ProcessingJobListResponse(items=items, limit=limit, offset=offset)


@app.post("/jobs/run", response_model=JobRunResponse)
async def run_jobs_endpoint(
    session: DbSession,
    limit: int = Query(default=10, ge=1, le=100),
) -> JobRunResponse:
    """Run pending background jobs in-process."""
    return await process_pending_jobs(session=session, asset_store=asset_store, limit=limit)


@app.get("/search/text", response_model=SearchResultsResponse)
async def search_text_endpoint(
    session: DbSession,
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> SearchResultsResponse:
    """Search derived documents with full text query."""
    items = await search_derived_documents_text(session=session, query=q, limit=limit)
    return SearchResultsResponse(query=q, items=items, limit=limit)


@app.get("/search/semantic", response_model=SearchResultsResponse)
async def search_semantic_endpoint(
    session: DbSession,
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> SearchResultsResponse:
    """Search derived documents with semantic retrieval."""
    items = await search_derived_documents_semantic(session=session, query=q, limit=limit)
    return SearchResultsResponse(query=q, items=items, limit=limit)


@app.get("/knowledge", response_model=KnowledgeItemListResponse)
async def list_knowledge_endpoint(
    session: DbSession,
    knowledge_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> KnowledgeItemListResponse:
    """List compiled knowledge items."""
    items = await list_knowledge_items(
        session=session,
        knowledge_type=knowledge_type,
        limit=limit,
        offset=offset,
    )
    return KnowledgeItemListResponse(items=items, limit=limit, offset=offset)


@app.get("/knowledge/{knowledge_item_id}", response_model=KnowledgeItemDetail)
async def get_knowledge_endpoint(
    knowledge_item_id: str,
    session: DbSession,
) -> KnowledgeItemDetail:
    """Get a compiled knowledge item by id."""
    item = await get_knowledge_item(session=session, knowledge_item_id=knowledge_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="knowledge item not found")
    return item


@app.post("/conversation/answer", response_model=ConversationAnswerResponse)
async def conversation_answer_endpoint(
    payload: ConversationAskRequest,
    session: DbSession,
) -> ConversationAnswerResponse:
    """Return a structured answer based on knowledge and evidence."""
    try:
        return await answer_conversation_question(
            session=session,
            question=payload.question,
            session_id=str(payload.session_id) if payload.session_id is not None else None,
            limit=payload.limit,
            search_mode=payload.search_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
