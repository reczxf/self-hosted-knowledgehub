"""Pydantic schemas for ingestion APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

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


class WebPageIngestRequest(BaseModel):
    """Request body for ingesting a webpage capture."""

    model_config = ConfigDict(str_strip_whitespace=True)

    source_type: Literal["web_page"] = "web_page"
    event_type: str = "capture.web_page"
    capture_method: str
    url: str
    canonical_url: str | None = None
    referrer_url: str | None = None
    title: str | None = None
    author: str | None = None
    language: str | None = None
    mime_type: str | None = "text/html"
    occurred_at: datetime
    captured_at: datetime | None = None
    original_created_at: datetime | None = None
    original_updated_at: datetime | None = None
    browser_profile: str | None = None
    user_agent: str | None = None
    extractor_version: str | None = None
    schema_version: str = "1"
    actor_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    assets: list[InlineAssetCreate] = Field(default_factory=list)


class IngestResponse(BaseModel):
    """API response after a successful ingest."""

    source_item_id: str
    source_version_id: str
    event_id: str
    asset_count: int

