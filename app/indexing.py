"""Text extraction and embedding helpers for the Memory Layer."""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
from collections.abc import Iterable

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def extract_text_content(*, content: bytes, mime_type: str | None, file_name: str | None) -> str:
    """Extract plain text from a stored asset."""
    normalized_mime = (mime_type or "").lower()
    normalized_name = (file_name or "").lower()

    if "json" in normalized_mime or normalized_name.endswith(".json"):
        return _extract_json_text(content)
    if "html" in normalized_mime or normalized_name.endswith((".html", ".htm")):
        decoded = _decode_bytes(content)
        without_tags = HTML_TAG_RE.sub(" ", decoded)
        return _normalize_text(html.unescape(without_tags))
    if normalized_mime.startswith("text/") or normalized_name.endswith(
        (".md", ".txt", ".log", ".csv", ".jsonl")
    ):
        return _normalize_text(_decode_bytes(content))
    return _normalize_text(_decode_bytes(content))


def compute_text_embedding(text: str, *, dimensions: int) -> list[float]:
    """Generate a deterministic lightweight embedding without external services."""
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")

    vector = [0.0] * dimensions
    tokens = TOKEN_RE.findall(text.lower())
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], byteorder="big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + (digest[5] / 255.0)
        vector[bucket] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def build_indexable_text(
    *,
    title: str | None,
    snippets: Iterable[str],
    metadata: dict[str, object],
) -> str:
    """Combine title, extracted snippets and useful metadata into a search document."""
    parts: list[str] = []
    if title:
        parts.append(title)

    for snippet in snippets:
        if snippet:
            parts.append(snippet)

    metadata_text = _flatten_json_strings(metadata)
    if metadata_text:
        parts.append(metadata_text)

    return _normalize_text("\n".join(parts))


def estimate_token_count(text: str) -> int:
    """Estimate token count cheaply for search diagnostics."""
    return len(TOKEN_RE.findall(text))


def _extract_json_text(content: bytes) -> str:
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _normalize_text(_decode_bytes(content))
    return _normalize_text(_flatten_json_strings(payload))


def _flatten_json_strings(value: object) -> str:
    collected: list[str] = []
    _collect_strings(value, collected)
    return "\n".join(collected)


def _collect_strings(value: object, collected: list[str]) -> None:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            collected.append(normalized)
        return
    if isinstance(value, dict):
        for nested in value.values():
            _collect_strings(nested, collected)
        return
    if isinstance(value, list | tuple | set):
        for nested in value:
            _collect_strings(nested, collected)


def _decode_bytes(content: bytes) -> str:
    return content.decode("utf-8", errors="ignore")


def _normalize_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()
