#!/usr/bin/env python3
"""
model_gateway.py — Model Gateway для Buffy Project.

Единый API для вызова всех моделей (OpenAI-совместимый):
  - DeepSeek (облачная)
  - Gemini (облачная)
  - Ollama (локальная)
  - OpenRouter (агрегатор)
  - SambaNova (облачная)

Принципы:
  1. Один вызов → любой провайдер
  2. Graceful fallback: primary → fallback → error
  3. Capability-based routing через SmartRouter
  4. Key rotation через KeyPool
  5. Streaming support
  6. Token counting (эвристика)

Использование:
    from scripts_01.model_gateway import ModelGateway

    gw = ModelGateway()
    result = gw.generate("deepseek-v4-flash", [
        {"role": "user", "content": "Hello"}
    ])
    print(result["content"])

    # С fallback
    result = gw.generate("deepseek-v4-flash", messages, fallback="gemini-2.5-flash")

    # По capabilities
    result = gw.generate_by_capabilities(["code", "fast"], messages)

    # Streaming
    for chunk in gw.generate_stream("deepseek-v4-flash", messages):
        print(chunk, end="")
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import re
from typing import Any, Dict, Iterator, List, Optional, Tuple

from pathlib import Path

import httpx
import importlib.util

# Путь к корню проекта
WORKSPACE = Path(__file__).resolve().parent.parent

# Добавляем пути для импорта core.router и .keys/keypool
sys.path.insert(0, str(WORKSPACE))


def _import_keypool() -> Any:
    """Ленивый импорт KeyPool из .keys/keypool.py."""
    kp_path = WORKSPACE / ".keys" / "keypool.py"
    spec = importlib.util.spec_from_file_location("keypool", str(kp_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load KeyPool from {kp_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.KeyPool()


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class ModelResponse:
    """Стандартный ответ модели."""
    content: str
    model: str
    provider: str
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
    })
    latency_ms: int = 0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    cached: bool = False
    fallback_used: bool = False


@dataclass
class StreamChunk:
    """Чанк стриминга."""
    content: str = ""
    finish_reason: str | None = None
    model: str = ""
    usage: Dict[str, int] | None = None


# ── Провайдеры и модели ──────────────────────────────────────

PROVIDER_ENDPOINTS: Dict[str, Dict[str, Any]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": {
            "deepseek-v4-flash": {"max_tokens": 128000},
            "deepseek-v3-pro": {"max_tokens": 128000},
            "deepseek-chat": {"max_tokens": 32000},
        },
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": {
            "gemini-2.5-flash": {"max_tokens": 1048576},
            "gemini-2.0-flash": {"max_tokens": 1048576},
            "gemini-1.5-pro": {"max_tokens": 1048576},
        },
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "models": {
            "deepseek/deepseek-chat": {"max_tokens": 128000},
            "openai/gpt-4o": {"max_tokens": 128000},
            "anthropic/claude-3.5-sonnet": {"max_tokens": 200000},
            "google/gemini-2.0-flash-001": {"max_tokens": 1048576},
        },
    },
    "sambanova": {
        "base_url": "https://api.sambanova.ai/v1",
        "models": {
            "Meta-Llama-3.3-70B-Instruct": {"max_tokens": 128000},
            "Meta-Llama-3.1-405B-Instruct": {"max_tokens": 128000},
            "Qwen2.5-72B-Instruct": {"max_tokens": 128000},
            "DeepSeek-R1-Distill-Llama-70B": {"max_tokens": 32000},
        },
    },
    "ollama": {
        "base_url": "http://localhost:11434",
        "models": {
            "qwen2.5:1.5b": {"max_tokens": 4096},
            "qwen2.5:0.5b": {"max_tokens": 2048},
        },
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": {
            "qwen-max": {"max_tokens": 32000},
            "qwen-plus": {"max_tokens": 32000},
            "qwen-turbo": {"max_tokens": 8000},
        },
    },
}

# Маппинг: Runtime (агент) → модель Model Gateway (правило 11 User-Choice Override).
# Когда policy resolve возвращает Runtime, этот маппинг даёт конкретную модель для вызова.
# Рантайм без маппинга (напр. openclaw) → graceful fallback на SmartRouter.
RUNTIME_MODELS: Dict[str, str] = {
    "freebuff": "deepseek-v4-flash",
    "claude-code": "anthropic/claude-3.5-sonnet",
}


# Cross-provider cloud fallback chain (v5.189.49+).
# Когда hard error {'402/billing', '401/auth', '5xx/server'} приходит на текущем
# провайдере, _call_with_fallback проходит по этой цепочке и выбирает
# следующего облачного провайдера С КЛЮЧОМ в KeyPool (см. .keys/keypool.py).
# П р и о р и т е т  cloud-first: deepseek (primary) → gemini → dashscope.
# Локальный Ollama — НЕ ПЕРЕБИРАЕТСЯ автоматически (opt-in only, через
# SmartRouter.preference=LOCAL). ANTI-6b defense: повтор одной и той же ошибки
# одного и того же провайдера — трата одного attempt'а на заведомо failable
# payload (402 на deepseek → retry deepseek → снова 402).
_CLOUD_FALLBACK_CHAIN: Tuple[str, ...] = ("deepseek", "gemini", "dashscope")
# Default cloud model per chain-step (override через fallback='<model>' arg).
_CLOUD_FALLBACK_MODELS: Dict[str, str] = {
    "deepseek":  "deepseek-v4-flash",
    "gemini":    "gemini-2.5-flash",
    "dashscope": "qwen-max",
}
# Pattern для парсинга HTTP status code из RuntimeError провайдеров (OpenAI-
# совместимые + Gemini провайдеры бросают `f"API error {status_code}: ...)"`).
_HARD_ERROR_STATUS_RE = re.compile(r"\berror (\d{3})\b")


def _is_hard_error(exc: Exception) -> bool:
    """True если ошибка — failover-worthy error class.

    Hard errors {'402/billing', '401/auth', '5xx/server'} — same provider
    повторит ту же ошибку; cross-provider fallback — правильное response.

    Soft errors (timeout, network, ConnectError) — possibly transient;
    допустим same-provider key-rotation retry (attempt < 1).
    """
    m = _HARD_ERROR_STATUS_RE.search(str(exc))
    if not m:
        return False
    code = int(m.group(1))
    return code in (401, 402) or 500 <= code < 600


# Маппинг: имя модели → провайдер
def _model_to_provider(model_name: str) -> str | None:
    """Определяет провайдера по имени модели."""
    for provider, cfg in PROVIDER_ENDPOINTS.items():
        if model_name in cfg["models"]:
            return provider
    # Fallback: проверяем префиксы
    model_lower = model_name.lower()
    # OpenRouter: модели вида deepseek/deepseek-chat — contain / and provider/ prefix
    if "/" in model_name:
        return "openrouter"
    if any(p in model_lower for p in ["deepseek"]):
        return "deepseek"
    if any(p in model_lower for p in ["gemini"]):
        return "gemini"
    if any(p in model_lower for p in ["qwen", "dashscope"]):
        return "dashscope"
    if any(p in model_lower for p in ["llama", "meta-llama"]):
        return "sambanova"
    if any(p in model_lower for p in ["ollama", "qwen2.5"]):
        return "ollama"
    if any(p in model_lower for p in ["openrouter"]):
        return "openrouter"
    return None


# ═══════════════════════════════════════════════════════════════
# Token Counter (эвристика)
# ═══════════════════════════════════════════════════════════════


def count_tokens(text: str) -> int:
    """Приблизительный подсчёт токенов.
    
    Использует эвристику: ~1.3 токена на 4 символа для русского/кода.
    """
    if not text:
        return 0
    try:
        return max(1, int(len(text) / 4 * 1.3))
    except Exception:
        return len(text)


def count_messages_tokens(messages: List[Dict[str, Any]]) -> int:
    """Подсчёт токенов в списке сообщений."""
    total = 0
    for msg in messages:
        total += count_tokens(msg.get("content", ""))
        total += count_tokens(msg.get("role", ""))
    # Overhead форматирования
    total += len(messages) * 4
    return total


# ═══════════════════════════════════════════════════════════════
# Provider implementations
# ═══════════════════════════════════════════════════════════════


class BaseProvider(ABC):
    """Абстрактный провайдер модели."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or ""

    @abstractmethod
    def generate(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> ModelResponse:
        ...

    def generate_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> Iterator[StreamChunk]:
        """Стриминг (по умолчанию — без стриминга)."""
        result = self.generate(model, messages, temperature, max_tokens, timeout)
        yield StreamChunk(content=result.content, finish_reason=result.finish_reason, model=model)
        yield StreamChunk(finish_reason="stop", model=model)


class OpenAICompatibleProvider(BaseProvider):
    """Провайдер с OpenAI-совместимым API (DeepSeek, OpenRouter, SambaNova, DashScope)."""

    def __init__(self, base_url: str, api_key: str, provider_name: str = "openai"):
        super().__init__(api_key)
        self.base_url = base_url.rstrip("/")
        self._provider_name = provider_name

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_body(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int | None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        if stream:
            body["stream"] = True
        return body

    def generate(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> ModelResponse:
        start = time.monotonic()
        body = self._build_body(model, messages, temperature, max_tokens)

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"API error {e.response.status_code}: {e.response.text[:200]}") from e
        except httpx.TimeoutException:
            raise RuntimeError(f"Timeout after {timeout}s for {model}") from None
        except Exception as e:
            raise RuntimeError(f"Request failed: {e}") from e

        elapsed = int((time.monotonic() - start) * 1000)
        choice = data.get("choices", [{}])[0]
        usage = data.get("usage", {})

        return ModelResponse(
            content=choice.get("message", {}).get("content", ""),
            model=data.get("model", model),
            provider=self._provider_name,
            finish_reason=choice.get("finish_reason", "stop"),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            latency_ms=elapsed,
        )

    def generate_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> Iterator[StreamChunk]:
        """Streaming via SSE (Server-Sent Events).

        Format: `data: {json_chunk}` lines, terminated by `data: [DONE]`.
        Each chunk has `choices[0].delta.content` with partial text.
        """
        body = self._build_body(model, messages, temperature, max_tokens, stream=True)

        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=body,
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        # SSE format: lines start with "data: "
                        if line.startswith("data: "):
                            data_str = line[len("data: "):]
                            if data_str.strip() == "[DONE]":
                                yield StreamChunk(finish_reason="stop", model=model)
                                return
                            try:
                                chunk_data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue
                            choices = chunk_data.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            finish = choices[0].get("finish_reason")
                            usage = chunk_data.get("usage")
                            if content or finish:
                                yield StreamChunk(
                                    content=content,
                                    finish_reason=finish,
                                    model=chunk_data.get("model", model),
                                    usage=usage if usage else None,
                                )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Stream API error {e.response.status_code}: {e.response.text[:200]}") from e
        except httpx.TimeoutException:
            raise RuntimeError(f"Stream timeout after {timeout}s for {model}") from None
        except Exception as e:
            raise RuntimeError(f"Stream request failed: {e}") from e


class GeminiProvider(BaseProvider):
    """Провайдер Google Gemini (отдельный API формат)."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Конвертирует OpenAI-формат сообщений в Gemini format.

        Returns:
            (contents, system_instruction)
        """
        contents = []
        system_instruction = None
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = content
                continue
            gemini_role = "model" if role in ("assistant", "model") else "user"
            contents.append({"role": gemini_role, "parts": [{"text": content}]})
        return contents, system_instruction

    def _build_body(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int | None,
    ) -> Dict[str, Any]:
        contents, system_instruction = self._convert_messages(messages)
        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if max_tokens:
            body["generationConfig"]["maxOutputTokens"] = max_tokens
        return body

    def generate(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> ModelResponse:
        start = time.monotonic()
        body = self._build_body(messages, temperature, max_tokens)
        url = f"{self.BASE_URL}/models/{model}:generateContent?key={self.api_key}"

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Gemini error {e.response.status_code}: {e.response.text[:200]}") from e
        except Exception as e:
            raise RuntimeError(f"Gemini request failed: {e}") from e

        elapsed = int((time.monotonic() - start) * 1000)
        candidates = data.get("candidates", [])
        if not candidates:
            return ModelResponse(content="", model=model, provider="gemini", latency_ms=elapsed)

        content_parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in content_parts)
        finish = candidates[0].get("finishReason", "STOP").lower()

        usage = data.get("usageMetadata", {})
        return ModelResponse(
            content=text,
            model=model,
            provider="gemini",
            finish_reason=finish,
            usage={
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            },
            latency_ms=elapsed,
        )

    def generate_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> Iterator[StreamChunk]:
        """Streaming via Gemini streamGenerateContent endpoint.

        Gemini returns a JSON array of chunk objects (not SSE format).
        Each chunk has `candidates[0].content.parts[0].text`.
        """
        body = self._build_body(messages, temperature, max_tokens)
        # streamGenerateContent returns chunked JSON array
        url = f"{self.BASE_URL}/models/{model}:streamGenerateContent?alt=sse&key={self.api_key}"

        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream("POST", url, json=body) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        # Gemini with alt=sse returns SSE format: data: {json}
                        if line.startswith("data: "):
                            data_str = line[len("data: "):]
                            # Gemini doesn't send [DONE], stream just ends
                            try:
                                chunk_data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue
                            candidates = chunk_data.get("candidates", [])
                            if not candidates:
                                continue
                            parts = candidates[0].get("content", {}).get("parts", [])
                            text = "".join(p.get("text", "") for p in parts)
                            finish = candidates[0].get("finishReason")
                            usage = chunk_data.get("usageMetadata")
                            if text or finish:
                                yield StreamChunk(
                                    content=text,
                                    finish_reason=finish.lower() if finish else None,
                                    model=model,
                                    usage={
                                        "prompt_tokens": usage.get("promptTokenCount", 0),
                                        "completion_tokens": usage.get("candidatesTokenCount", 0),
                                        "total_tokens": usage.get("totalTokenCount", 0),
                                    } if usage else None,
                                )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Gemini stream error {e.response.status_code}: {e.response.text[:200]}") from e
        except httpx.TimeoutException:
            raise RuntimeError(f"Gemini stream timeout after {timeout}s") from None
        except Exception as e:
            raise RuntimeError(f"Gemini stream failed: {e}") from e


class OllamaProvider(BaseProvider):
    """Провайдер Ollama (локальный)."""

    BASE_URL = "http://localhost:11434"

    def _build_body(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int | None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        ollama_messages = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            for msg in messages
        ]
        body: Dict[str, Any] = {
            "model": model,
            "messages": ollama_messages,
            "options": {"temperature": temperature},
            "stream": stream,
        }
        if max_tokens:
            body["options"]["num_predict"] = max_tokens
        return body

    def generate(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 120,
    ) -> ModelResponse:
        start = time.monotonic()
        body = self._build_body(model, messages, temperature, max_tokens, stream=False)

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{self.BASE_URL}/api/chat", json=body)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RuntimeError(f"Ollama model '{model}' not found. Run: ollama pull {model}") from e
            raise RuntimeError(f"Ollama error {e.response.status_code}: {e.response.text[:200]}") from e
        except httpx.TimeoutException:
            raise RuntimeError(f"Ollama timeout after {timeout}s (model may still be loading)") from None
        except httpx.ConnectError:
            raise RuntimeError("Ollama not running. Start with: ollama serve") from None
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e

        elapsed = int((time.monotonic() - start) * 1000)
        content = data.get("message", {}).get("content", "")
        done = data.get("done", True)

        return ModelResponse(
            content=content,
            model=data.get("model", model),
            provider="ollama",
            finish_reason="stop" if done else "unknown",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": (data.get("prompt_eval_count", 0) + data.get("eval_count", 0)),
            },
            latency_ms=elapsed,
        )

    def generate_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 120,
    ) -> Iterator[StreamChunk]:
        """Streaming via Ollama newline-delimited JSON.

        Ollama returns individual JSON objects separated by newlines.
        Each object has `message.content` with partial text and `done` flag.
        """
        body = self._build_body(model, messages, temperature, max_tokens, stream=True)

        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream("POST", f"{self.BASE_URL}/api/chat", json=body) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        content = chunk_data.get("message", {}).get("content", "")
                        done = chunk_data.get("done", False)
                        if content:
                            yield StreamChunk(
                                content=content,
                                finish_reason="stop" if done else None,
                                model=chunk_data.get("model", model),
                            )
                        if done:
                            # Final chunk with usage stats
                            yield StreamChunk(
                                finish_reason="stop",
                                model=model,
                                usage={
                                    "prompt_tokens": chunk_data.get("prompt_eval_count", 0),
                                    "completion_tokens": chunk_data.get("eval_count", 0),
                                    "total_tokens": (
                                        chunk_data.get("prompt_eval_count", 0)
                                        + chunk_data.get("eval_count", 0)
                                    ),
                                },
                            )
                            return
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RuntimeError(f"Ollama model '{model}' not found. Run: ollama pull {model}") from e
            raise RuntimeError(f"Ollama stream error {e.response.status_code}") from e
        except httpx.TimeoutException:
            raise RuntimeError(f"Ollama stream timeout after {timeout}s") from None
        except httpx.ConnectError:
            raise RuntimeError("Ollama not running. Start with: ollama serve") from None
        except Exception as e:
            raise RuntimeError(f"Ollama stream failed: {e}") from e


# ═══════════════════════════════════════════════════════════════
# Model Gateway
# ═══════════════════════════════════════════════════════════════


class ModelGateway:
    """Единый шлюз для вызова всех моделей.

    Особенности:
    - OpenAI-совместимый интерфейс
    - Graceful fallback между провайдерами
    - Capability-based routing через SmartRouter
    - Key rotation через KeyPool
    - Подсчёт токенов
    - EventBus интеграция
    """

    def __init__(self, event_bus: Any = None, policy_engine: Any = None):
        self._event_bus = event_bus
        self._policy_engine = policy_engine  # PolicyEngine (правило 11) — опционально
        self._keypool: Any = None  # Lazy init to avoid import issues
        self._providers: Dict[str, BaseProvider] = {}
        self._router: Any = None   # SmartRouter — lazy init
        self._cache: Dict[str, ModelResponse] = {}
        # Кэш health-check Ollama (cloud-first роутинг, ANTI-6b defense):
        # чтобы не бить localhost при каждом route(), проверяем с TTL.
        self._ollama_ok: Optional[bool] = None
        self._ollama_checked_at: float = 0.0
        # TTL кэша health-check локального провайдера (секунды).
        self._OLLAMA_HEALTH_TTL: float = 5.0
        # Таймаут health-check (секунды) — быстрый отказ, если сервер не поднят.
        self._OLLAMA_HEALTH_TIMEOUT: float = 0.5

    @property
    def keypool(self):
        if self._keypool is None:
            self._keypool = _import_keypool()
        return self._keypool

    @property
    def router(self):
        if self._router is None:
            from core_02.router import SmartRouter, ModelCatalog
            self._router = SmartRouter(
                ModelCatalog.default(),
                provider_available=self._provider_available,
            )
        return self._router

    # ── availability (cloud-first роутинг, ANTI-6b defense) ────────────────

    def _provider_available(self, provider: Any) -> bool:
        """Доступен ли провайдер: облачный = есть ключ; локальный (ollama) = отвечает.

        Используется SmartRouter.provider_available для cloud-first выбора:
        если локальная qwen2.5:1.5b не запущена, а у DeepSeek/Gemini есть
        ключи — роутер выбирает облачную модель, а не падает в gen_failed.
        """
        name = getattr(provider, "value", None) or str(provider)
        if name == "ollama":
            return self._ollama_reachable()
        # Облачный провайдер доступен, если в KeyPool есть ключ. Fail-safe:
        # если keypool недоступен (ошибка импорта) — считаем провайдера
        # доступным (роутер не ломаем, падение поймает _call_with_fallback).
        try:
            return bool(self.keypool.has_key(name))
        except Exception:
            return True

    def _ollama_reachable(self) -> bool:
        """Кэшированный health-check Ollama (localhost:11434).

        Проверяем один раз за TTL, чтобы route() не делал HTTP на каждый вызов.
        Fail-safe: любая ошибка (не запущен / нет httpx) → False (недоступен).
        """
        now = time.monotonic()
        if (
            self._ollama_ok is not None
            and (now - self._ollama_checked_at) < self._OLLAMA_HEALTH_TTL
        ):
            return self._ollama_ok
        ok = False
        try:
            with httpx.Client(timeout=self._OLLAMA_HEALTH_TIMEOUT) as client:
                client.get("http://localhost:11434/api/tags")
            ok = True
        except Exception:
            ok = False
        self._ollama_ok = ok
        self._ollama_checked_at = now
        return ok

    def _get_provider(self, provider_name: str) -> BaseProvider:
        """Возвращает провайдера (создаёт при первом вызове)."""
        if provider_name not in self._providers:
            cfg = PROVIDER_ENDPOINTS.get(provider_name)
            if not cfg:
                raise ValueError(f"Unknown provider: {provider_name}")

            api_key = self.keypool.rotate(provider_name) or ""

            if provider_name == "gemini":
                self._providers[provider_name] = GeminiProvider(api_key)
            elif provider_name == "ollama":
                self._providers[provider_name] = OllamaProvider(api_key)
            elif provider_name in ("deepseek", "openrouter", "sambanova", "dashscope"):
                self._providers[provider_name] = OpenAICompatibleProvider(
                    base_url=cfg["base_url"], api_key=api_key,
                    provider_name=provider_name,
                )
            else:
                raise ValueError(f"Unsupported provider: {provider_name}")

        return self._providers[provider_name]

    def _rotate_key(self, provider_name: str):
        """Ротирует ключ для провайдера (принудительно создаёт нового)."""
        if provider_name in self._providers:
            del self._providers[provider_name]

    def generate(
        self,
        model: str | None = None,
        messages: List[Dict[str, Any]] | None = None,
        fallback: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
        capabilities: List[str] | None = None,
    ) -> ModelResponse:
        """Генерирует ответ модели.

        Args:
            model: имя модели (deepseek-v4-flash, gemini-2.5-flash, ...)
            messages: список сообщений [{"role": "user", "content": "..."}]
            fallback: модель для fallback при ошибке
            temperature: температура (0.0-1.0)
            max_tokens: максимальное количество токенов в ответе
            timeout: таймаут запроса в секундах
            capabilities: если указан — маршрутизировать по capabilities

        Returns:
            ModelResponse
        """
        messages = messages or []
        start = time.monotonic()

        # 1. Определяем модель
        if capabilities and not model:
            # Маршрутизация по capabilities: User-Choice Override (правило 11) → SmartRouter
            model, route_fallback, _ = self.resolve_model(capabilities)
            fallback = fallback or route_fallback

        if not model:
            raise ValueError("Either model or capabilities must be specified")

        provider_name = _model_to_provider(model)
        if not provider_name:
            raise ValueError(f"Cannot determine provider for model: {model}")

        # 2. Вызываем модель
        result = self._call_with_fallback(
            provider_name=provider_name,
            model=model,
            messages=messages,
            fallback=fallback,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

        # 3. Публикуем событие
        self._publish_event(result, messages)

        return result

    def resolve_model(
        self,
        capabilities: List[str],
    ) -> Tuple[Optional[str], Optional[str], str]:
        """Выбирает модель для capabilities: User-Choice Override → SmartRouter.

        Правило 11 (User-Choice Override): если пользователь назначил Runtime на
        capability (policy resolve), его модель имеет приоритет; иначе —
        автоматическая маршрутизация SmartRouter.

        Args:
            capabilities: список capability (coding, research, ...)

        Returns:
            (model, fallback_model, source), где source =
              "policy:<runtime>" — override пользователя применён
              "router"          — авто-выбор SmartRouter
              "none"            — модель не найдена
        """
        # 1. User-Choice Override: policy resolve по capabilities
        if self._policy_engine is not None and capabilities:
            try:
                from freebuff_plugin_03.policy import is_policy_override
                for cap in capabilities:
                    result = self._policy_engine.resolve(cap)
                    runtime = result.get("runtime") if isinstance(result, dict) else None
                    # Только явный пользовательский override (source == "policy") имеет
                    # приоритет; авто-выбор через fallback_chain/cap_registry (source
                    # "auto") остаётся за SmartRouter (правило 11).
                    is_override = is_policy_override(result)
                    if not runtime or not is_override:
                        continue
                    model = RUNTIME_MODELS.get(runtime)
                    if model:
                        return model, None, f"policy:{runtime}"
            except Exception:
                pass  # Graceful degradation → SmartRouter

        # 2. Авто-выбор SmartRouter
        try:
            decision = self.router.route(required_capabilities=capabilities or None)
            fallback = decision.model if not decision.fallback_used else None
            return decision.model, fallback, "router"
        except Exception:
            return None, None, "none"

    def _has_key_for(self, provider_name: str) -> bool:
        """True если KeyPool имеет key для provider (cloud-first фильтр).

        Soft fail: если keypool не может ответить (ImportError / AttributeError / TypeError) —
        считаем провайдера доступным (роутер не ломаем, повторная попытка
        поймает ошибку в _call_with_fallback).
        """
        try:
            return bool(self.keypool.has_key(provider_name))
        except Exception:
            return True

    def _default_model_for_provider(self, provider_name: str) -> str:
        """Default cloud model per provider (uses _CLOUD_FALLBACK_MODELS)."""
        return _CLOUD_FALLBACK_MODELS.get(provider_name, "deepseek-v4-flash")

    def _call_with_fallback(
        self,
        provider_name: str,
        model: str,
        messages: List[Dict[str, Any]],
        fallback: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
        attempt: int = 0,
        provider_chain: Optional[List[str]] = None,
        trial_trail: Optional[List[str]] = None,
    ) -> ModelResponse:
        """Cross-provider cloud fallback (v5.189.49+).

        Логика:
          1. Пробуем primary provider/model как есть.
          2. Soft error + attempt < 1 → rotate key + retry same provider
             (transient error — вероятно починится ключом/повтором).
          3. Hard error {'402/401/5xx'} OR после key rotation → walk
             _CLOUD_FALLBACK_CHAIN (skip current provider), pick next
             provider WITH a key (см. .keys/keypool.py), retry.
          4. После provider chain exhaust → fallback model из user arg
             (last try, single).
          5. Все exhaust → RuntimeError с trial trail (list of tried providers).
        """
        if provider_chain is None:
            provider_chain = list(_CLOUD_FALLBACK_CHAIN)
        if trial_trail is None:
            trial_trail = [provider_name]

        try:
            provider = self._get_provider(provider_name)
            return provider.generate(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        except Exception as e:
            error_msg = str(e)
            is_hard = _is_hard_error(e)

            # 1. Soft error: rotate key + retry same provider (attempt < 1).
            if not is_hard and attempt < 1:
                self._rotate_key(provider_name)
                return self._call_with_fallback(
                    provider_name, model, messages, fallback,
                    temperature, max_tokens, timeout,
                    attempt + 1, provider_chain, trial_trail,
                )

            # 2. Walk _CLOUD_FALLBACK_CHAIN (skip current), pick next WITH a key.
            # НЕ повторяем тот же provider on hard error (CHISTO ANTI-6b defense).
            if provider_name in provider_chain:
                start_idx = provider_chain.index(provider_name) + 1
            else:
                start_idx = 0
            next_idx = start_idx
            # Wrap-around если chain exceeded: ещё одна попытка через fallback param
            while next_idx < len(provider_chain):
                next_provider = provider_chain[next_idx]
                if next_provider != provider_name and self._has_key_for(next_provider):
                    trial_trail.append(next_provider)
                    next_model = self._default_model_for_provider(next_provider)
                    try:
                        result = self._call_with_fallback(
                            next_provider, next_model, messages, None,
                            temperature, max_tokens, timeout,
                            0, provider_chain, trial_trail,
                        )
                        result.fallback_used = True
                        # Cross-provider switch metadata для audit trail.
                        result.provider = next_provider
                        return result
                    except Exception:
                        next_idx += 1
                        continue
                next_idx += 1

            # 3. Fallback param (user explicit, single model) — last try.
            if fallback and attempt < 2:
                fb_provider = _model_to_provider(fallback)
                if fb_provider and fb_provider not in trial_trail:
                    trial_trail.append(fb_provider)
                    try:
                        result = self._call_with_fallback(
                            fb_provider, fallback, messages, None,
                            temperature, max_tokens, timeout,
                            attempt + 1, provider_chain, trial_trail,
                        )
                        result.fallback_used = True
                        result.model = fallback
                        return result
                    except Exception:
                        pass

            # 4. Exhaust: raise с информативным trail.
            raise RuntimeError(
                f"All fallback providers exhausted for {model}: "
                f"tried {trial_trail}; last error: {error_msg}"
            ) from e

    def generate_stream(
        self,
        model: str | None = None,
        messages: List[Dict[str, Any]] | None = None,
        fallback: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> Iterator[StreamChunk]:
        """Генерирует ответ в streaming-режиме.

        Args:
            model: имя модели (deepseek-v4-flash, gemini-2.5-flash, ...)
            messages: список сообщений [{"role": "user", "content": "..."}]
            fallback: модель для fallback при ошибке инициализации стрима
            temperature: температура (0.0-1.0)
            max_tokens: максимальное количество токенов в ответе
            timeout: таймаут запроса в секундах

        Yields:
            StreamChunk с частичным контентом и/или finish_reason
        """
        messages = messages or []

        if not model:
            raise ValueError("model is required for streaming")

        provider_name = _model_to_provider(model)
        if not provider_name:
            raise ValueError(f"Cannot determine provider for model: {model}")

        try:
            provider = self._get_provider(provider_name)
            self._publish_stream_event(model, provider_name, fallback_used=False)
            for chunk in provider.generate_stream(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            ):
                yield chunk
        except Exception as e:
            if fallback:
                fb_provider_name = _model_to_provider(fallback)
                if fb_provider_name and fb_provider_name != provider_name:
                    # Fallback: переключаемся на другую модель
                    self._publish_stream_event(fallback, fb_provider_name, True)
                    fb_provider = self._get_provider(fb_provider_name)
                    for chunk in fb_provider.generate_stream(
                        model=fallback,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout,
                    ):
                        yield chunk
                    return
            raise

    def generate_by_capabilities(
        self,
        capabilities: List[str],
        messages: List[Dict[str, Any]],
        **kwargs,
    ) -> ModelResponse:
        """Генерирует ответ, выбирая модель по capabilities."""
        return self.generate(messages=messages, capabilities=capabilities, **kwargs)

    def _publish_stream_event(
        self,
        model: str,
        provider: str,
        fallback_used: bool = False,
    ):
        """Публикует событие streaming вызова модели."""
        if self._event_bus is None:
            return
        try:
            from scripts_01.event_bus import Event
            event_type = "model.fallback" if fallback_used else "model.called"
            self._event_bus.publish(Event(
                type=event_type,
                source="model_gateway",
                data={
                    "model": model,
                    "provider": provider,
                    "streaming": True,
                    "fallback_used": fallback_used,
                },
            ))
        except Exception:
            pass

    def _publish_event(self, result: ModelResponse, messages: List[Dict[str, Any]]):
        """Публикует событие вызова модели."""
        if self._event_bus is None:
            return
        try:
            from scripts_01.event_bus import Event
            event_type = "model.called"
            if result.fallback_used:
                event_type = "model.fallback"
            elif result.cached:
                event_type = "model.cached"

            self._event_bus.publish(Event(
                type=event_type,
                source="model_gateway",
                data={
                    "model": result.model,
                    "provider": result.provider,
                    "latency_ms": result.latency_ms,
                    "total_tokens": result.usage.get("total_tokens", 0),
                    "finish_reason": result.finish_reason,
                    "fallback_used": result.fallback_used,
                    "cached": result.cached,
                    "prompt_tokens": count_messages_tokens(messages),
                },
            ))
        except Exception:
            pass

    def status(self) -> Dict[str, Any]:
        """Статус Gateway: доступные провайдеры и модели."""
        providers = {}
        for pname, cfg in PROVIDER_ENDPOINTS.items():
            models = list(cfg["models"].keys())
            api_key = self.keypool.rotate(pname)
            providers[pname] = {
                "models": models,
                "has_key": api_key is not None,
                "base_url": cfg["base_url"],
            }
        return {
            "providers": providers,
            "total_providers": len(providers),
            "total_models": sum(len(p["models"]) for p in providers.values()),
        }


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Model Gateway — единый API для вызова моделей",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # generate
    p_gen = sub.add_parser("generate", help="Вызвать модель")
    p_gen.add_argument("model", help="Имя модели")
    p_gen.add_argument("prompt", help="Текст запроса")
    p_gen.add_argument("--system", help="System prompt")
    p_gen.add_argument("--temp", type=float, default=0.7)
    p_gen.add_argument("--max-tokens", type=int)
    p_gen.add_argument("--fallback", help="Модель для fallback")

    # generate-stream
    p_stream = sub.add_parser("generate-stream", help="Streaming вызов модели")
    p_stream.add_argument("model", help="Имя модели")
    p_stream.add_argument("prompt", help="Текст запроса")
    p_stream.add_argument("--system", help="System prompt")
    p_stream.add_argument("--temp", type=float, default=0.7)
    p_stream.add_argument("--max-tokens", type=int)
    p_stream.add_argument("--timeout", type=int, default=120)

    # status
    sub.add_parser("status", help="Статус Gateway")

    # models
    sub.add_parser("models", help="Список доступных моделей")

    args = parser.parse_args()
    gw = ModelGateway()

    if args.command == "generate":
        messages = []
        if args.system:
            messages.append({"role": "system", "content": args.system})
        messages.append({"role": "user", "content": args.prompt})

        kwargs = {
            "model": args.model,
            "messages": messages,
            "temperature": args.temp,
            "max_tokens": args.max_tokens,
            "fallback": args.fallback,
        }

        try:
            result = gw.generate(**{k: v for k, v in kwargs.items() if v is not None})
            print(f"\n{'─' * 60}")
            print(result.content)
            print(f"{'─' * 60}")
            print(f"  Model: {result.model} ({result.provider})")
            print(f"  Tokens: {result.usage['total_tokens']} "
                  f"(prompt {result.usage['prompt_tokens']} + "
                  f"completion {result.usage['completion_tokens']})")
            print(f"  Latency: {result.latency_ms}ms"
                  f"{' (fallback)' if result.fallback_used else ''}")
        except Exception as e:
            print(f"❌ Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "generate-stream":
        messages = []
        if args.system:
            messages.append({"role": "system", "content": args.system})
        messages.append({"role": "user", "content": args.prompt})

        kwargs = {
            "model": args.model,
            "messages": messages,
            "temperature": args.temp,
            "timeout": args.timeout,
        }
        if args.max_tokens:
            kwargs["max_tokens"] = args.max_tokens

        try:
            print(f"\n{'─' * 60}", flush=True)
            for chunk in gw.generate_stream(**kwargs):
                if chunk.content:
                    print(chunk.content, end="", flush=True)
                if chunk.finish_reason == "stop" and chunk.usage:
                    print(f"\n{'─' * 60}")
                    print(f"  Model: {chunk.model}")
                    print(f"  Tokens: {chunk.usage.get('total_tokens', 0)}")
            print(flush=True)
        except Exception as e:
            print(f"\n❌ Stream error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "status":
        s = gw.status()
        print("📊 MODEL GATEWAY STATUS")
        print(f"   Total providers: {s['total_providers']}")
        print(f"   Total models:    {s['total_models']}")
        for pname, info in s["providers"].items():
            key_status = "🔑" if info["has_key"] else "❌"
            print(f"\n   {key_status} {pname}:")
            print(f"      URL:    {info['base_url']}")
            for m in info["models"]:
                print(f"      • {m}")

    elif args.command == "models":
        print("📋 AVAILABLE MODELS")
        for pname, cfg in PROVIDER_ENDPOINTS.items():
            print(f"\n  {pname}:")
            for mname, minfo in cfg["models"].items():
                print(f"    • {mname} ({minfo['max_tokens']} tok)")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
