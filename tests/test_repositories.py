from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.llm import LlmAnswer
from app.models import ConversationTurn
from app.repositories import (
    _build_conversation_history_context,
    _build_knowledge_slug,
    _calculate_content_sha256,
    _cosine_similarity,
    _fingerprint_payload,
    _generate_conversation_answer_with_deepseek,
)
from app.schemas import ConversationEvidenceItem, KnowledgeItemSummary, WebPageIngestRequest


def test_fingerprint_payload_excludes_runtime_fields() -> None:
    payload = WebPageIngestRequest(
        capture_method="browser_extension",
        url="https://example.com",
        occurred_at=datetime(2026, 4, 15, tzinfo=UTC),
        captured_at=datetime(2026, 4, 15, 1, tzinfo=UTC),
        actor_id="user-1",
        session_id="session-1",
    )

    fingerprint = _fingerprint_payload(payload)

    assert "captured_at" not in fingerprint
    assert "occurred_at" not in fingerprint
    assert "actor_id" not in fingerprint
    assert "session_id" not in fingerprint


def test_calculate_content_sha256_falls_back_to_fingerprint_payload() -> None:
    first = _calculate_content_sha256(
        prepared_assets=[],
        fingerprint_payload={"url": "https://example.com", "title": "PKOS"},
    )
    second = _calculate_content_sha256(
        prepared_assets=[],
        fingerprint_payload={"title": "PKOS", "url": "https://example.com"},
    )

    assert first == second


def test_cosine_similarity_returns_expected_bounds() -> None:
    same = _cosine_similarity([1.0, 0.0], [1.0, 0.0])
    opposite = _cosine_similarity([1.0, 0.0], [-1.0, 0.0])

    assert same == 1.0
    assert opposite == -1.0


def test_build_knowledge_slug_generates_stable_slug() -> None:
    slug = _build_knowledge_slug(
        knowledge_type="insight_card",
        title="PKOS Memory Layer",
        source_version_id="12345678-aaaa-bbbb-cccc-1234567890ab",
    )

    assert slug == "insight_card-pkos-memory-layer-12345678"


def test_build_conversation_history_context_formats_turns() -> None:
    turns = [
        ConversationTurn(
            session_id=uuid4(),
            turn_no=1,
            role="user",
            content="什么是 PKOS？",
        ),
        ConversationTurn(
            session_id=uuid4(),
            turn_no=2,
            role="assistant",
            content="PKOS 是个人知识操作系统。",
        ),
    ]

    context = _build_conversation_history_context(turns)

    assert "用户: 什么是 PKOS？" in context
    assert "助手: PKOS 是个人知识操作系统。" in context


@pytest.mark.asyncio
async def test_generate_conversation_answer_uses_fallback_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        enabled = False

    monkeypatch.setattr("app.repositories.deepseek_client", FakeClient())
    answer = await _generate_conversation_answer_with_deepseek(
        question="PKOS 现在能做什么？",
        history_turns=[],
        knowledge_items=[],
        evidence_items=[],
        fallback_answer="fallback answer",
    )

    assert answer.used_fallback is True
    assert answer.provider == "local"
    assert answer.answer == "fallback answer"


@pytest.mark.asyncio
async def test_generate_conversation_answer_uses_deepseek_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        enabled = True

        async def answer(self, **_: object) -> LlmAnswer:
            return LlmAnswer(
                answer="deepseek answer",
                provider="deepseek",
                model="deepseek-chat",
            )

    monkeypatch.setattr("app.repositories.deepseek_client", FakeClient())

    answer = await _generate_conversation_answer_with_deepseek(
        question="PKOS 现在能做什么？",
        history_turns=[],
        knowledge_items=[
            KnowledgeItemSummary(
                id=uuid4(),
                knowledge_type="insight_card",
                status="active",
                slug="pkos-insight",
                title="PKOS Insight",
                summary="PKOS 已有知识层",
                source_item_id=None,
                source_version_id=None,
                derived_document_id=None,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                metadata={},
            )
        ],
        evidence_items=[
            ConversationEvidenceItem(
                source_version_id=uuid4(),
                title="PKOS Memory",
                preview="PKOS memory layer supports retrieval",
                score=0.8,
                match_type="text",
            )
        ],
        fallback_answer="fallback answer",
    )

    assert answer.used_fallback is False
    assert answer.provider == "deepseek"
    assert answer.answer == "deepseek answer"
