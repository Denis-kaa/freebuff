"""Клиент для локальной LLM (ollama/llama.cpp)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

***REMOVED***quests

from realtor_os.logger import setup_logger

_LOGGER = setup_logger("realtor_os.llm")


class LLMError(Exception):
    """Ошибка LLM."""


@dataclass
class LLMResponse:
    content: str
    done: bool = True


class LocalLLM:
    """Обёртка над локальной LLM через HTTP API."""

    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: int = 60) -> None:
        self.base_url = base_url or os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434")
        self.model = model or os.environ.get("LLM_MODEL", "qwen2.5:7b")
        self.timeout = timeout

    def ask(self, prompt: str, context: str = "") -> LLMResponse:
        """Задать вопрос локальной LLM.

        Args:
            prompt: Вопрос пользователя.
            context: Контекст из RAG.

        Returns:
            Ответ LLM.
        """
        full_prompt = self._build_prompt(prompt, context)
        payload: dict[str, Any***REMOVED*** = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
        ***REMOVED***
        try:
            response = requests.post(
                f"{self.base_url***REMOVED***/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise LLMError(f"LLM request failed: {exc***REMOVED***") from exc

        data = response.json()
        return LLMResponse(content=data.get("response", "").strip())

    def _build_prompt(self, prompt: str, context: str) -> str:
        return (
            "Ты — ассистент риелтора. Отвечай на основе контекста.\n\n"
            f"Контекст:\n{context***REMOVED***\n\n"
            f"Вопрос:\n{prompt***REMOVED***\n"
        )
