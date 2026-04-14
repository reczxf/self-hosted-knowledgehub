"""FastAPI entrypoint for the PKOS collector."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import Base, engine, get_db_session
from app.repositories import ingest_webpage
from app.schemas import IngestResponse, WebPageIngestRequest
from app.storage import LocalAssetStore

asset_store = LocalAssetStore(settings.data_dir)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize storage directories and database schema."""
    asset_store.ensure_directories()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="PKOS Collector", version="0.1.0", lifespan=lifespan)
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


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

