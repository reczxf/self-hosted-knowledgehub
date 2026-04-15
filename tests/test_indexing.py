from __future__ import annotations

from app.indexing import build_indexable_text, compute_text_embedding, extract_text_content


def test_extract_text_content_from_html() -> None:
    text = extract_text_content(
        content=b"<html><body><h1>PKOS</h1><p>Hello Memory Layer</p></body></html>",
        mime_type="text/html",
        file_name="page.html",
    )

    assert "PKOS" in text
    assert "Hello Memory Layer" in text


def test_compute_text_embedding_is_deterministic() -> None:
    first = compute_text_embedding("pkos memory layer", dimensions=16)
    second = compute_text_embedding("pkos memory layer", dimensions=16)

    assert first == second
    assert len(first) == 16


def test_build_indexable_text_merges_title_snippets_and_metadata() -> None:
    text = build_indexable_text(
        title="PKOS",
        snippets=["Memory layer", "semantic search"],
        metadata={"source_type": "web_page", "tags": ["knowledge", "search"]},
    )

    assert "PKOS" in text
    assert "semantic search" in text
    assert "knowledge" in text
