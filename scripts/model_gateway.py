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
    from scripts.model_gateway import ModelGateway

    gw = ModelGateway()
    result = gw.generate("deepseek-v4-flash", [
        {"role": "user", "content": "Hello"***REMOVED***
    ***REMOVED***)
    print(result["content"***REMOVED***)

    # С fallback
    result = gw.generate("deepseek-v4-flash", messages, fallback="gemini-2.5-flash")

    # По capabilities
    result = gw.generate_by_capabilities(["code", "fast"***REMOVED***, messages)

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
***REMOVED***
from typing import Any, Dict, Iterator, List, Optional, Tuple

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
        raise ImportError(f"Cannot load KeyPool from {kp_path***REMOVED***")
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
    usage: Dict[str, int***REMOVED*** = field(default_factory=lambda: {
        "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
    ***REMOVED***)
    latency_ms: int = 0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12***REMOVED***)
    cached: bool = False
    fallback_used: bool = False


@dataclass
class StreamChunk:
    """Чанк стриминга."""
    content: str = ""
    finish_reason: str | None = None
    model: str = ""
    usage: Dict[str, int***REMOVED*** | None = None


# ── Провайдеры и модели ──────────────────────────────────────

PROVIDER_ENDPOINTS: Dict[str, Dict[str, Any***REMOVED******REMOVED*** = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": {
            "deepseek-v4-flash": {"max_tokens": 128000***REMOVED***,
            "deepseek-v3-pro": {"max_tokens": 128000***REMOVED***,
            "deepseek-chat": {"max_tokens": 32000***REMOVED***,
        ***REMOVED***,
    ***REMOVED***,
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": {
            "gemini-2.5-flash": {"max_tokens": 1048576***REMOVED***,
            "gemini-2.0-flash": {"max_tokens": 1048576***REMOVED***,
            "gemini-1.5-pro": {"max_tokens": 1048576***REMOVED***,
        ***REMOVED***,
    ***REMOVED***,
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "models": {
            "deepseek/deepseek-chat": {"max_tokens": 128000***REMOVED***,
            "openai/gpt-4o": {"max_tokens": 128000***REMOVED***,
            "anthropic/claude-3.5-sonnet": {"max_tokens": 200000***REMOVED***,
            "google/gemini-2.0-flash-001": {"max_tokens": 1048576***REMOVED***,
        ***REMOVED***,
    ***REMOVED***,
    "sambanova": {
        "base_url": "https://api.sambanova.ai/v1",
        "models": {
            "Meta-Llama-3.3-70B-Instruct": {"max_tokens": 128000***REMOVED***,
            "Meta-Llama-3.1-405B-Instruct": {"max_tokens": 128000***REMOVED***,
            "Qwen2.5-72B-Instruct": {"max_tokens": 128000***REMOVED***,
            "DeepSeek-R1-Distill-Llama-70B": {"max_tokens": 32000***REMOVED***,
        ***REMOVED***,
    ***REMOVED***,
    "ollama": {
        "base_url": "http://localhost:11434",
        "models": {
            "qwen2.5:1.5b": {"max_tokens": 4096***REMOVED***,
            "qwen2.5:0.5b": {"max_tokens": 2048***REMOVED***,
        ***REMOVED***,
    ***REMOVED***,
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": {
            "qwen-max": {"max_tokens": 32000***REMOVED***,
            "qwen-plus": {"max_tokens": 32000***REMOVED***,
            "qwen-turbo": {"max_tokens": 8000***REMOVED***,
        ***REMOVED***,
    ***REMOVED***,
***REMOVED***

# Маппинг: имя модели → провайдер
def _model_to_provider(model_name: str) -> str | None:
    """Определяет провайдера по имени модели."""
    for provider, cfg in PROVIDER_ENDPOINTS.items():
        if model_name in cfg["models"***REMOVED***:
            return provider
    # Fallback: проверяем префиксы
    model_lower = model_name.lower()
    # OpenRouter: модели вида deepseek/deepseek-chat — contain / and provider/ prefix
    if "/" in model_name:
        return "openrouter"
    if any(p in model_lower for p in ["deepseek"***REMOVED***):
        return "deepseek"
    if any(p in model_lower for p in ["gemini"***REMOVED***):
        return "gemini"
    if any(p in model_lower for p in ["qwen", "dashscope"***REMOVED***):
        return "dashscope"
    if any(p in model_lower for p in ["llama", "meta-llama"***REMOVED***):
        return "sambanova"
    if any(p in model_lower for p in ["ollama", "qwen2.5"***REMOVED***):
        return "ollama"
    if any(p in model_lower for p in ["openrouter"***REMOVED***):
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


def count_messages_tokens(messages: List[Dict[str, Any***REMOVED******REMOVED***) -> int:
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
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> ModelResponse:
        ...

    def generate_stream(
        self,
        model: str,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> Iterator[StreamChunk***REMOVED***:
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

    def _headers(self) -> Dict[str, str***REMOVED***:
        return {
            "Authorization": f"Bearer {self.api_key***REMOVED***",
            "Content-Type": "application/json",
        ***REMOVED***

    def _build_body(
        self,
        model: str,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        temperature: float,
        max_tokens: int | None,
        stream: bool = False,
    ) -> Dict[str, Any***REMOVED***:
        body: Dict[str, Any***REMOVED*** = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        ***REMOVED***
        if max_tokens:
            body["max_tokens"***REMOVED*** = max_tokens
        if stream:
            body["stream"***REMOVED*** = True
        return body

    def generate(
        self,
        model: str,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> ModelResponse:
        start = time.monotonic()
        body = self._build_body(model, messages, temperature, max_tokens)

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(
                    f"{self.base_url***REMOVED***/chat/completions",
                    headers=self._headers(),
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"API error {e.response.status_code***REMOVED***: {e.response.text[:200***REMOVED******REMOVED***") from e
        except httpx.TimeoutException:
            raise RuntimeError(f"Timeout after {timeout***REMOVED***s for {model***REMOVED***") from None
        except Exception as e:
            raise RuntimeError(f"Request failed: {e***REMOVED***") from e

        elapsed = int((time.monotonic() - start) * 1000)
        choice = data.get("choices", [{***REMOVED******REMOVED***)[0***REMOVED***
        usage = data.get("usage", {***REMOVED***)

        return ModelResponse(
            content=choice.get("message", {***REMOVED***).get("content", ""),
            model=data.get("model", model),
            provider=self._provider_name,
            finish_reason=choice.get("finish_reason", "stop"),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            ***REMOVED***,
            latency_ms=elapsed,
        )

    def generate_stream(
        self,
        model: str,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> Iterator[StreamChunk***REMOVED***:
        """Streaming via SSE (Server-Sent Events).

        Format: `data: {json_chunk***REMOVED***` lines, terminated by `data: [DONE***REMOVED***`.
        Each chunk has `choices[0***REMOVED***.delta.content` with partial text.
        """
        body = self._build_body(model, messages, temperature, max_tokens, stream=True)

        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url***REMOVED***/chat/completions",
                    headers=self._headers(),
                    json=body,
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        # SSE format: lines start with "data: "
                        if line.startswith("data: "):
                            data_str = line[len("data: "):***REMOVED***
                            if data_str.strip() == "[DONE***REMOVED***":
                                yield StreamChunk(finish_reason="stop", model=model)
                                return
                            try:
                                chunk_data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue
                            choices = chunk_data.get("choices", [***REMOVED***)
                            if not choices:
                                continue
                            delta = choices[0***REMOVED***.get("delta", {***REMOVED***)
                            content = delta.get("content", "")
                            finish = choices[0***REMOVED***.get("finish_reason")
                            usage = chunk_data.get("usage")
                            if content or finish:
                                yield StreamChunk(
                                    content=content,
                                    finish_reason=finish,
                                    model=chunk_data.get("model", model),
                                    usage=usage if usage else None,
                                )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Stream API error {e.response.status_code***REMOVED***: {e.response.text[:200***REMOVED******REMOVED***") from e
        except httpx.TimeoutException:
            raise RuntimeError(f"Stream timeout after {timeout***REMOVED***s for {model***REMOVED***") from None
        except Exception as e:
            raise RuntimeError(f"Stream request failed: {e***REMOVED***") from e


class GeminiProvider(BaseProvider):
    """Провайдер Google Gemini (отдельный API формат)."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def _convert_messages(self, messages: List[Dict[str, Any***REMOVED******REMOVED***) -> Tuple[List[Dict[str, Any***REMOVED******REMOVED***, Optional[str***REMOVED******REMOVED***:
        """Конвертирует OpenAI-формат сообщений в Gemini format.

        Returns:
            (contents, system_instruction)
        """
        contents = [***REMOVED***
        system_instruction = None
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = content
                continue
            gemini_role = "model" if role in ("assistant", "model") else "user"
            contents.append({"role": gemini_role, "parts": [{"text": content***REMOVED******REMOVED******REMOVED***)
        return contents, system_instruction

    def _build_body(
        self,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        temperature: float,
        max_tokens: int | None,
    ) -> Dict[str, Any***REMOVED***:
        contents, system_instruction = self._convert_messages(messages)
        body: Dict[str, Any***REMOVED*** = {
            "contents": contents,
            "generationConfig": {"temperature": temperature***REMOVED***,
        ***REMOVED***
        if system_instruction:
            body["systemInstruction"***REMOVED*** = {"parts": [{"text": system_instruction***REMOVED******REMOVED******REMOVED***
        if max_tokens:
            body["generationConfig"***REMOVED***["maxOutputTokens"***REMOVED*** = max_tokens
        return body

    def generate(
        self,
        model: str,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> ModelResponse:
        start = time.monotonic()
        body = self._build_body(messages, temperature, max_tokens)
        url = f"{self.BASE_URL***REMOVED***/models/{model***REMOVED***:generateContent?key={self.api_key***REMOVED***"

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Gemini error {e.response.status_code***REMOVED***: {e.response.text[:200***REMOVED******REMOVED***") from e
        except Exception as e:
            raise RuntimeError(f"Gemini request failed: {e***REMOVED***") from e

        elapsed = int((time.monotonic() - start) * 1000)
        candidates = data.get("candidates", [***REMOVED***)
        if not candidates:
            return ModelResponse(content="", model=model, provider="gemini", latency_ms=elapsed)

        content_parts = candidates[0***REMOVED***.get("content", {***REMOVED***).get("parts", [***REMOVED***)
        text = "".join(p.get("text", "") for p in content_parts)
        finish = candidates[0***REMOVED***.get("finishReason", "STOP").lower()

        usage = data.get("usageMetadata", {***REMOVED***)
        return ModelResponse(
            content=text,
            model=model,
            provider="gemini",
            finish_reason=finish,
            usage={
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            ***REMOVED***,
            latency_ms=elapsed,
        )

    def generate_stream(
        self,
        model: str,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> Iterator[StreamChunk***REMOVED***:
        """Streaming via Gemini streamGenerateContent endpoint.

        Gemini returns a JSON array of chunk objects (not SSE format).
        Each chunk has `candidates[0***REMOVED***.content.parts[0***REMOVED***.text`.
        """
        body = self._build_body(messages, temperature, max_tokens)
        # streamGenerateContent returns chunked JSON array
        url = f"{self.BASE_URL***REMOVED***/models/{model***REMOVED***:streamGenerateContent?alt=sse&key={self.api_key***REMOVED***"

        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream("POST", url, json=body) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        # Gemini with alt=sse returns SSE format: data: {json***REMOVED***
                        if line.startswith("data: "):
                            data_str = line[len("data: "):***REMOVED***
                            # Gemini doesn't send [DONE***REMOVED***, stream just ends
                            try:
                                chunk_data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue
                            candidates = chunk_data.get("candidates", [***REMOVED***)
                            if not candidates:
                                continue
                            parts = candidates[0***REMOVED***.get("content", {***REMOVED***).get("parts", [***REMOVED***)
                            text = "".join(p.get("text", "") for p in parts)
                            finish = candidates[0***REMOVED***.get("finishReason")
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
                                    ***REMOVED*** if usage else None,
                                )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Gemini stream error {e.response.status_code***REMOVED***: {e.response.text[:200***REMOVED******REMOVED***") from e
        except httpx.TimeoutException:
            raise RuntimeError(f"Gemini stream timeout after {timeout***REMOVED***s") from None
        except Exception as e:
            raise RuntimeError(f"Gemini stream failed: {e***REMOVED***") from e


class OllamaProvider(BaseProvider):
    """Провайдер Ollama (локальный)."""

    BASE_URL = "http://localhost:11434"

    def _build_body(
        self,
        model: str,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        temperature: float,
        max_tokens: int | None,
        stream: bool = False,
    ) -> Dict[str, Any***REMOVED***:
        ollama_messages = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")***REMOVED***
            for msg in messages
        ***REMOVED***
        body: Dict[str, Any***REMOVED*** = {
            "model": model,
            "messages": ollama_messages,
            "options": {"temperature": temperature***REMOVED***,
            "stream": stream,
        ***REMOVED***
        if max_tokens:
            body["options"***REMOVED***["num_predict"***REMOVED*** = max_tokens
        return body

    def generate(
        self,
        model: str,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 120,
    ) -> ModelResponse:
        start = time.monotonic()
        body = self._build_body(model, messages, temperature, max_tokens, stream=False)

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{self.BASE_URL***REMOVED***/api/chat", json=body)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RuntimeError(f"Ollama model '{model***REMOVED***' not found. Run: ollama pull {model***REMOVED***") from e
            raise RuntimeError(f"Ollama error {e.response.status_code***REMOVED***: {e.response.text[:200***REMOVED******REMOVED***") from e
        except httpx.TimeoutException:
            raise RuntimeError(f"Ollama timeout after {timeout***REMOVED***s (model may still be loading)") from None
        except httpx.ConnectError:
            raise RuntimeError("Ollama not running. Start with: ollama serve") from None
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e***REMOVED***") from e

        elapsed = int((time.monotonic() - start) * 1000)
        content = data.get("message", {***REMOVED***).get("content", "")
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
            ***REMOVED***,
            latency_ms=elapsed,
        )

    def generate_stream(
        self,
        model: str,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 120,
    ) -> Iterator[StreamChunk***REMOVED***:
        """Streaming via Ollama newline-delimited JSON.

        Ollama returns individual JSON objects separated by newlines.
        Each object has `message.content` with partial text and `done` flag.
        """
        body = self._build_body(model, messages, temperature, max_tokens, stream=True)

        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream("POST", f"{self.BASE_URL***REMOVED***/api/chat", json=body) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        content = chunk_data.get("message", {***REMOVED***).get("content", "")
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
                                ***REMOVED***,
                            )
                            return
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RuntimeError(f"Ollama model '{model***REMOVED***' not found. Run: ollama pull {model***REMOVED***") from e
            raise RuntimeError(f"Ollama stream error {e.response.status_code***REMOVED***") from e
        except httpx.TimeoutException:
            raise RuntimeError(f"Ollama stream timeout after {timeout***REMOVED***s") from None
        except httpx.ConnectError:
            raise RuntimeError("Ollama not running. Start with: ollama serve") from None
        except Exception as e:
            raise RuntimeError(f"Ollama stream failed: {e***REMOVED***") from e


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

    def __init__(self, event_bus: Any = None):
        self._event_bus = event_bus
        self._keypool: Any = None  # Lazy init to avoid import issues
        self._providers: Dict[str, BaseProvider***REMOVED*** = {***REMOVED***
        self._router: Any = None   # SmartRouter — lazy init
        self._cache: Dict[str, ModelResponse***REMOVED*** = {***REMOVED***

    @property
    def keypool(self):
        if self._keypool is None:
            self._keypool = _import_keypool()
        return self._keypool

    @property
    def router(self):
        if self._router is None:
            from core.router import SmartRouter, ModelCatalog
            self._router = SmartRouter(ModelCatalog.default())
        return self._router

    def _get_provider(self, provider_name: str) -> BaseProvider:
        """Возвращает провайдера (создаёт при первом вызове)."""
        if provider_name not in self._providers:
            cfg = PROVIDER_ENDPOINTS.get(provider_name)
            if not cfg:
                raise ValueError(f"Unknown provider: {provider_name***REMOVED***")

            api_key = self.keypool.rotate(provider_name) or ""

            if provider_name == "gemini":
                self._providers[provider_name***REMOVED*** = GeminiProvider(api_key)
            elif provider_name == "ollama":
                self._providers[provider_name***REMOVED*** = OllamaProvider(api_key)
            elif provider_name in ("deepseek", "openrouter", "sambanova", "dashscope"):
                self._providers[provider_name***REMOVED*** = OpenAICompatibleProvider(
                    base_url=cfg["base_url"***REMOVED***, api_key=api_key,
                    provider_name=provider_name,
                )
            else:
                raise ValueError(f"Unsupported provider: {provider_name***REMOVED***")

        return self._providers[provider_name***REMOVED***

    def _rotate_key(self, provider_name: str):
        """Ротирует ключ для провайдера (принудительно создаёт нового)."""
        if provider_name in self._providers:
            del self._providers[provider_name***REMOVED***

    def generate(
        self,
        model: str | None = None,
        messages: List[Dict[str, Any***REMOVED******REMOVED*** | None = None,
        fallback: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
        capabilities: List[str***REMOVED*** | None = None,
    ) -> ModelResponse:
        """Генерирует ответ модели.

        Args:
            model: имя модели (deepseek-v4-flash, gemini-2.5-flash, ...)
            messages: список сообщений [{"role": "user", "content": "..."***REMOVED******REMOVED***
            fallback: модель для fallback при ошибке
            temperature: температура (0.0-1.0)
            max_tokens: максимальное количество токенов в ответе
            timeout: таймаут запроса в секундах
            capabilities: если указан — маршрутизировать по capabilities

        Returns:
            ModelResponse
        """
        messages = messages or [***REMOVED***
        start = time.monotonic()

        # 1. Определяем модель
        if capabilities and not model:
            # Маршрутизация по capabilities
            decision = self.router.route(required_capabilities=capabilities)
            model = decision.model
            fallback = fallback or (decision.model if not decision.fallback_used else None)

        if not model:
            raise ValueError("Either model or capabilities must be specified")

        provider_name = _model_to_provider(model)
        if not provider_name:
            raise ValueError(f"Cannot determine provider for model: {model***REMOVED***")

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

    def _call_with_fallback(
        self,
        provider_name: str,
        model: str,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
        fallback: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
        attempt: int = 0,
    ) -> ModelResponse:
        """Вызывает модель с автоматическим fallback."""
        max_attempts = 3 if fallback else 2

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

            # 1. Пробуем другой ключ того же провайдера
            if attempt < 1:
                self._rotate_key(provider_name)
                return self._call_with_fallback(
                    provider_name, model, messages, fallback,
                    temperature, max_tokens, timeout, attempt + 1,
                )

            # 2. Пробуем fallback модель
            if fallback and attempt < max_attempts:
                fb_provider = _model_to_provider(fallback)
                if fb_provider and fb_provider != provider_name:
                    result = self._call_with_fallback(
                        fb_provider, fallback, messages, None,
                        temperature, max_tokens, timeout, attempt + 1,
                    )
                    result.fallback_used = True
                    result.model = fallback
                    return result

            raise RuntimeError(
                f"All attempts failed for {model***REMOVED***: {error_msg***REMOVED***"
            ) from e

    def generate_stream(
        self,
        model: str | None = None,
        messages: List[Dict[str, Any***REMOVED******REMOVED*** | None = None,
        fallback: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: int = 60,
    ) -> Iterator[StreamChunk***REMOVED***:
        """Генерирует ответ в streaming-режиме.

        Args:
            model: имя модели (deepseek-v4-flash, gemini-2.5-flash, ...)
            messages: список сообщений [{"role": "user", "content": "..."***REMOVED******REMOVED***
            fallback: модель для fallback при ошибке инициализации стрима
            temperature: температура (0.0-1.0)
            max_tokens: максимальное количество токенов в ответе
            timeout: таймаут запроса в секундах

        Yields:
            StreamChunk с частичным контентом и/или finish_reason
        """
        messages = messages or [***REMOVED***

        if not model:
            raise ValueError("model is required for streaming")

        provider_name = _model_to_provider(model)
        if not provider_name:
            raise ValueError(f"Cannot determine provider for model: {model***REMOVED***")

        try:
            provider = self._get_provider(provider_name)
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
        capabilities: List[str***REMOVED***,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
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
            from scripts.event_bus import Event
            event_type = "model.fallback" if fallback_used else "model.called"
            self._event_bus.publish(Event(
                type=event_type,
                source="model_gateway",
                data={
                    "model": model,
                    "provider": provider,
                    "streaming": True,
                    "fallback_used": fallback_used,
                ***REMOVED***,
            ))
        except Exception:
            pass

    def _publish_event(self, result: ModelResponse, messages: List[Dict[str, Any***REMOVED******REMOVED***):
        """Публикует событие вызова модели."""
        if self._event_bus is None:
            return
        try:
            from scripts.event_bus import Event
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
                ***REMOVED***,
            ))
        except Exception:
            pass

    def status(self) -> Dict[str, Any***REMOVED***:
        """Статус Gateway: доступные провайдеры и модели."""
        providers = {***REMOVED***
        for pname, cfg in PROVIDER_ENDPOINTS.items():
            models = list(cfg["models"***REMOVED***.keys())
            api_key = self.keypool.rotate(pname)
            providers[pname***REMOVED*** = {
                "models": models,
                "has_key": api_key is not None,
                "base_url": cfg["base_url"***REMOVED***,
            ***REMOVED***
        return {
            "providers": providers,
            "total_providers": len(providers),
            "total_models": sum(len(p["models"***REMOVED***) for p in providers.values()),
        ***REMOVED***


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
        messages = [***REMOVED***
        if args.system:
            messages.append({"role": "system", "content": args.system***REMOVED***)
        messages.append({"role": "user", "content": args.prompt***REMOVED***)

        kwargs = {
            "model": args.model,
            "messages": messages,
            "temperature": args.temp,
            "max_tokens": args.max_tokens,
            "fallback": args.fallback,
        ***REMOVED***

        try:
            result = gw.generate(**{k: v for k, v in kwargs.items() if v is not None***REMOVED***)
            print(f"\n{'─' * 60***REMOVED***")
            print(result.content)
            print(f"{'─' * 60***REMOVED***")
            print(f"  Model: {result.model***REMOVED*** ({result.provider***REMOVED***)")
            print(f"  Tokens: {result.usage['total_tokens'***REMOVED******REMOVED*** "
                  f"(prompt {result.usage['prompt_tokens'***REMOVED******REMOVED*** + "
                  f"completion {result.usage['completion_tokens'***REMOVED******REMOVED***)")
            print(f"  Latency: {result.latency_ms***REMOVED***ms"
                  f"{' (fallback)' if result.fallback_used else ''***REMOVED***")
        except Exception as e:
            print(f"❌ Error: {e***REMOVED***", file=sys.stderr)
            sys.exit(1)

    elif args.command == "generate-stream":
        messages = [***REMOVED***
        if args.system:
            messages.append({"role": "system", "content": args.system***REMOVED***)
        messages.append({"role": "user", "content": args.prompt***REMOVED***)

        kwargs = {
            "model": args.model,
            "messages": messages,
            "temperature": args.temp,
            "timeout": args.timeout,
        ***REMOVED***
        if args.max_tokens:
            kwargs["max_tokens"***REMOVED*** = args.max_tokens

        try:
            print(f"\n{'─' * 60***REMOVED***", flush=True)
            for chunk in gw.generate_stream(**kwargs):
                if chunk.content:
                    print(chunk.content, end="", flush=True)
                if chunk.finish_reason == "stop" and chunk.usage:
                    print(f"\n{'─' * 60***REMOVED***")
                    print(f"  Model: {chunk.model***REMOVED***")
                    print(f"  Tokens: {chunk.usage.get('total_tokens', 0)***REMOVED***")
            print(flush=True)
        except Exception as e:
            print(f"\n❌ Stream error: {e***REMOVED***", file=sys.stderr)
            sys.exit(1)

    elif args.command == "status":
        s = gw.status()
        print("📊 MODEL GATEWAY STATUS")
        print(f"   Total providers: {s['total_providers'***REMOVED******REMOVED***")
        print(f"   Total models:    {s['total_models'***REMOVED******REMOVED***")
        for pname, info in s["providers"***REMOVED***.items():
            key_status = "🔑" if info["has_key"***REMOVED*** else "❌"
            print(f"\n   {key_status***REMOVED*** {pname***REMOVED***:")
            print(f"      URL:    {info['base_url'***REMOVED******REMOVED***")
            for m in info["models"***REMOVED***:
                print(f"      • {m***REMOVED***")

    elif args.command == "models":
        print("📋 AVAILABLE MODELS")
        for pname, cfg in PROVIDER_ENDPOINTS.items():
            print(f"\n  {pname***REMOVED***:")
            for mname, minfo in cfg["models"***REMOVED***.items():
                print(f"    • {mname***REMOVED*** ({minfo['max_tokens'***REMOVED******REMOVED*** tok)")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
