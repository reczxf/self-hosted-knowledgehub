"""DeepSeek API client for the conversation layer."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass(slots=True)
class LlmAnswer:
    """Normalized LLM answer payload."""

    answer: str
    provider: str
    model: str
    used_fallback: bool = False


class DeepSeekClient:
    """Minimal async DeepSeek chat completions client."""

    def __init__(self) -> None:
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.api_key = settings.deepseek_api_key
        self.model = settings.deepseek_model
        self.timeout = settings.deepseek_timeout_seconds
        self.max_tokens = settings.deepseek_max_tokens

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def answer(
        self,
        *,
        question: str,
        history_context: str,
        knowledge_context: str,
        evidence_context: str,
    ) -> LlmAnswer:
        """Generate an answer from DeepSeek or raise if unavailable."""
        if not self.enabled:
            raise RuntimeError("DeepSeek API key is not configured")

        system_prompt = (
            "你是 PKOS 的知识问答助手。"
            "请优先依据已沉淀知识对象回答，再用原始证据补强。"
            "回答必须简洁、直接、中文输出。"
            "如果证据不足，要明确指出不足，不要编造。"
        )
        user_prompt = (
            f"问题：{question}\n\n"
            f"历史对话：\n{history_context or '无'}\n\n"
            f"知识对象：\n{knowledge_context or '无'}\n\n"
            f"原始证据：\n{evidence_context or '无'}\n\n"
            "请输出一段直接回答。"
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            payload = response.json()

        return LlmAnswer(
            answer=payload["choices"][0]["message"]["content"].strip(),
            provider="deepseek",
            model=self.model,
            used_fallback=False,
        )


deepseek_client = DeepSeekClient()
