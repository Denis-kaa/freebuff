"""
Tests for ModelGateway — providers, fallback, token counting, EventBus integration.
"""

import json
import os
import sys
import tempfile
}
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts_01.model_gateway import (
    ModelGateway,
    ModelResponse,
    StreamChunk,
    count_tokens,
    count_messages_tokens,
    _model_to_provider,
    PROVIDER_ENDPOINTS,
)


class TestTokenCounter:
    """Тесты подсчёта токенов."""

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_count_tokens_short(self):
        assert count_tokens("Hello") >= 1

    def test_count_tokens_long(self):
        t = "Тестовый текст " * 100
        assert count_tokens(t) > 10

    def test_count_messages(self):
        msgs = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        n = count_messages_tokens(msgs)
        assert n > 0


class TestModelToProvider:
    """Тесты определения провайдера по модели."""

    def test_deepseek(self):
        assert _model_to_provider("deepseek-v4-flash") == "deepseek"
        assert _model_to_provider("deepseek-chat") == "deepseek"

    def test_gemini(self):
        assert _model_to_provider("gemini-2.5-flash") == "gemini"

    def test_ollama(self):
        assert _model_to_provider("qwen2.5:1.5b") == "ollama"

    def test_unknown(self):
        assert _model_to_provider("unknown-model-42") is None

    def test_sambanova(self):
        assert _model_to_provider("Meta-Llama-3.3-70B-Instruct") == "sambanova"


class TestModelResponse:
    """Тесты ModelResponse."""

    def test_default_values(self):
        r = ModelResponse(content="Hello", model="test", provider="test")
        assert r.finish_reason == "stop"
        assert r.usage["total_tokens"] == 0
        assert r.latency_ms == 0
        assert not r.fallback_used
        assert not r.cached

    def test_with_usage(self):
        r = ModelResponse(
            content="Hi",
            model="m",
            provider="p",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            latency_ms=200,
            fallback_used=True,
        )
        assert r.usage["total_tokens"] == 15
        assert r.latency_ms == 200
        assert r.fallback_used


class TestModelGateway:
    """Тесты ModelGateway (с моками HTTP)."""

    def test_init(self):
        gw = ModelGateway()
        assert gw._event_bus is None
        assert gw._keypool is None
        assert gw._router is None

    def test_status(self):
        gw = ModelGateway()
        status = gw.status()
        assert "providers" in status
        assert status["total_providers"] >= 3

    def test_models_available(self):
        """Проверяем, что все модели из PROVIDER_ENDPOINTS имеют корректную конфигурацию."""
        for pname, cfg in PROVIDER_ENDPOINTS.items():
            assert "base_url" in cfg, f"{pname} missing base_url"
            assert len(cfg["models"]) > 0, f"{pname} has no models"
            for mname, minfo in cfg["models"].items():
                assert "max_tokens" in minfo, f"{mname} missing max_tokens"
                # Проверяем, что _model_to_provider маппит модель
                mapped = _model_to_provider(mname)
                assert mapped is not None, f"{mname} not mapped by _model_to_provider"
                # OpenRouter модели с / маппятся в openrouter
                if "/" in mname:
                    assert mapped == "openrouter", f"{mname} should map to openrouter, got {mapped}"

    def test_unknown_model_raises(self):
        gw = ModelGateway()
        with pytest.raises(ValueError, match="model or capabilities"):
            gw.generate()

    @patch("scripts_01.model_gateway.httpx.Client")
    def test_mock_openai_call(self, mock_client):
        """Тест OpenAI-совместимого вызова с моком."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello from mock"}, "finish_reason": "stop"}],
            "model": "deepseek-v4-flash",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_instance = MagicMock()
        mock_instance.post.return_value = mock_resp
        mock_client.return_value.__enter__.return_value = mock_instance

        gw = ModelGateway()
        # Мокаем keypool чтобы вернуть тестовый ключ
        mock_pool = MagicMock()
        mock_pool.rotate.return_value = "sk-test-key"
        gw._keypool = mock_pool

        result = gw.generate(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert result.content == "Hello from mock"
        assert result.model == "deepseek-v4-flash"
        assert result.usage["total_tokens"] == 15
        assert result.latency_ms >= 0

    def test_fallback_marked_in_response(self):
        """Тест, что флаг fallback_used проставляется в ModelResponse."""
        r = ModelResponse(content="ok", model="m", provider="p", fallback_used=True)
        assert r.fallback_used

        r2 = ModelResponse(content="ok", model="m", provider="p")
        assert not r2.fallback_used

    def test_event_bus_integration(self):
        """Тест, что события публикуются при наличии EventBus."""
        from scripts_01.event_bus import EventBus, Event
        import tempfile

        received = []

        def handler(e):
            received.append(e.type)

        db_path = tempfile.mktemp(suffix=".db")
        bus = EventBus(db_path)
        bus.subscribe("*", handler)

        gw = ModelGateway(event_bus=bus)
        mock_pool = MagicMock()
        mock_pool.rotate.return_value = "sk-test"
        gw._keypool = mock_pool

        # Публикуем вручную (API call не делаем)
        result = ModelResponse(content="test", model="m", provider="p")
        gw._publish_event(result, [{"role": "user", "content": "test"}])

        assert "model.called" in received

    def test_generate_by_capabilities(self):
        """Тест маршрутизации по capabilities."""
        gw = ModelGateway()
        mock_pool = MagicMock()
        mock_pool.rotate.return_value = "sk-test"
        gw._keypool = mock_pool

        # Проверяем что метод существует и принимает capabilities
        with patch.object(gw, 'generate') as mock_gen:
            mock_gen.return_value = ModelResponse(content="ok", model="m", provider="p")

            gw.generate_by_capabilities(
                capabilities=["code", "fast"],
                messages=[{"role": "user", "content": "write code"}],
            )

            # Проверяем что generate вызван с capabilities
            _, kwargs = mock_gen.call_args
            assert kwargs.get("capabilities") == ["code", "fast"]

    def test_provider_rotation(self):
        """Тест ротации ключей."""
        gw = ModelGateway()
        mock_pool = MagicMock()
        mock_pool.rotate.return_value = "key1"
        gw._keypool = mock_pool

        # Создаём провайдера — он берёт ключ
        provider = gw._get_provider("deepseek")
        assert provider.api_key == "key1"

        # Ротируем ключ
        mock_pool.rotate.return_value = "key2"
        gw._rotate_key("deepseek")

        # Новый провайдер с новым ключом
        provider2 = gw._get_provider("deepseek")
        assert provider2.api_key == "key2"


class TestStreamChunk:
    """Тесты StreamChunk."""

    def test_default_values(self):
        c = StreamChunk()
        assert c.content == ""
        assert c.finish_reason is None
        assert c.model == ""
        assert c.usage is None

    def test_with_content(self):
        c = StreamChunk(content="Hello", finish_reason="stop", model="m")
        assert c.content == "Hello"
        assert c.finish_reason == "stop"
        assert c.model == "m"

    def test_with_usage(self):
        c = StreamChunk(content="Hi", model="m", usage={"total_tokens": 42})
        assert c.usage["total_tokens"] == 42


class TestStreaming:
    """Тесты streaming для всех провайдеров."""

    @patch("scripts_01.model_gateway.httpx.Client")
    def test_openai_stream_sse_format(self, mock_client):
        """Тест OpenAI-совместимого streaming (SSE format)."""
        # Мокаем SSE ответ: data: {json} lines + data: [DONE]
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"], "finish_reason": null]], "model": "deepseek-v4-flash"]',
            'data: {"choices": [{"delta": {"content": " world"], "finish_reason": null]], "model": "deepseek-v4-flash"]',
            'data: {"choices": [{"delta": {], "finish_reason": "stop"]], "model": "deepseek-v4-flash", "usage": {"total_tokens": 15]]',
            'data: [DONE]',
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = iter(sse_lines)
        mock_resp.raise_for_status = MagicMock()

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__.return_value = mock_resp
        mock_stream_ctx.__exit__.return_value = False

        mock_instance = MagicMock()
        mock_instance.stream.return_value = mock_stream_ctx
        mock_client.return_value.__enter__.return_value = mock_instance

        from scripts_01.model_gateway import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test",
            provider_name="deepseek",
        )

        chunks = list(provider.generate_stream(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": "Hi"}],
        ))

        # Should get content chunks + final stop chunk
        assert len(chunks) >= 2
        contents = "".join(c.content for c in chunks)
        assert "Hello" in contents
        assert "world" in contents
        # Last chunk should have finish_reason=stop
        assert any(c.finish_reason == "stop" for c in chunks)

    @patch("scripts_01.model_gateway.httpx.Client")
    def test_gemini_stream_sse_format(self, mock_client):
        """Тест Gemini streaming (streamGenerateContent with alt=sse)."""
        sse_lines = [
            'data: {"candidates": [{"content": {"parts": [{"text": "Hello"]]], "finishReason": null]]]',
            'data: {"candidates": [{"content": {"parts": [{"text": " from Gemini"]]], "finishReason": "STOP"]], "usageMetadata": {"totalTokenCount": 20]]',
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = iter(sse_lines)
        mock_resp.raise_for_status = MagicMock()

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__.return_value = mock_resp
        mock_stream_ctx.__exit__.return_value = False

        mock_instance = MagicMock()
        mock_instance.stream.return_value = mock_stream_ctx
        mock_client.return_value.__enter__.return_value = mock_instance

        from scripts_01.model_gateway import GeminiProvider
        provider = GeminiProvider(api_key="test-key")

        chunks = list(provider.generate_stream(
            model="gemini-2.5-flash",
            messages=[{"role": "user", "content": "Hi"}],
        ))

        contents = "".join(c.content for c in chunks)
        assert "Hello" in contents
        assert "Gemini" in contents
        # Should have a finish chunk
        assert any(c.finish_reason == "stop" for c in chunks)

    @patch("scripts_01.model_gateway.httpx.Client")
    def test_ollama_stream_newline_json(self, mock_client):
        """Тест Ollama streaming (newline-delimited JSON)."""
        json_lines = [
            '{"model": "qwen2.5:1.5b", "message": {"content": "Hello"], "done": false]',
            '{"model": "qwen2.5:1.5b", "message": {"content": " world"], "done": false]',
            '{"model": "qwen2.5:1.5b", "message": {"content": ""], "done": true, "prompt_eval_count": 10, "eval_count": 5]',
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = iter(json_lines)
        mock_resp.raise_for_status = MagicMock()

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__.return_value = mock_resp
        mock_stream_ctx.__exit__.return_value = False

        mock_instance = MagicMock()
        mock_instance.stream.return_value = mock_stream_ctx
        mock_client.return_value.__enter__.return_value = mock_instance

        from scripts_01.model_gateway import OllamaProvider
        provider = OllamaProvider(api_key="")

        chunks = list(provider.generate_stream(
            model="qwen2.5:1.5b",
            messages=[{"role": "user", "content": "Hi"}],
        ))

        contents = "".join(c.content for c in chunks)
        assert "Hello" in contents
        assert "world" in contents
        # Final chunk should have usage
        final_chunks = [c for c in chunks if c.usage is not None]
        assert len(final_chunks) >= 1
        assert final_chunks[-1].usage["total_tokens"] == 15

    def test_base_provider_stream_fallback(self):
        """Тест fallback streaming в BaseProvider (без реального стриминга)."""
        from scripts_01.model_gateway import BaseProvider

        class FakeProvider(BaseProvider):
            def generate(self, model, messages, temperature=0.7, max_tokens=None, timeout=60):
                return ModelResponse(content="full response", model=model, provider="fake")

        provider = FakeProvider()
        chunks = list(provider.generate_stream(
            model="test",
            messages=[{"role": "user", "content": "Hi"}],
        ))

        # BaseProvider fallback yields content then stop
        assert len(chunks) == 2
        assert chunks[0].content == "full response"
        assert chunks[1].finish_reason == "stop"

    @patch("scripts_01.model_gateway.httpx.Client")
    def test_gateway_generate_stream(self, mock_client):
        """Тест ModelGateway.generate_stream() с моком провайдера."""
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hi"], "finish_reason": null]], "model": "deepseek-v4-flash"]',
            'data: {"choices": [{"delta": {], "finish_reason": "stop"]], "model": "deepseek-v4-flash"]',
            'data: [DONE]',
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = iter(sse_lines)
        mock_resp.raise_for_status = MagicMock()

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__.return_value = mock_resp
        mock_stream_ctx.__exit__.return_value = False

        mock_instance = MagicMock()
        mock_instance.stream.return_value = mock_stream_ctx
        mock_client.return_value.__enter__.return_value = mock_instance

        gw = ModelGateway()
        mock_pool = MagicMock()
        mock_pool.rotate.return_value = "sk-test"
        gw._keypool = mock_pool

        chunks = list(gw.generate_stream(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": "Hello"}],
        ))

        assert len(chunks) >= 1
        assert any(c.content == "Hi" for c in chunks)

    def test_generate_stream_no_model_raises(self):
        """Тест что generate_stream() без model вызывает ValueError."""
        gw = ModelGateway()
        with pytest.raises(ValueError, match="model is required"):
            list(gw.generate_stream(messages=[{"role": "user", "content": "Hi"}]))

    @patch("scripts_01.model_gateway.httpx.Client")
    def test_openai_stream_handles_empty_lines(self, mock_client):
        """Тест что streaming игнорирует пустые строки в SSE."""
        sse_lines = [
            '',
            'data: {"choices": [{"delta": {"content": "A"], "finish_reason": null]]]',
            '',
            'data: {"choices": [{"delta": {"content": "B"], "finish_reason": null]]]',
            '',
            'data: [DONE]',
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = iter(sse_lines)
        mock_resp.raise_for_status = MagicMock()

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__.return_value = mock_resp
        mock_stream_ctx.__exit__.return_value = False

        mock_instance = MagicMock()
        mock_instance.stream.return_value = mock_stream_ctx
        mock_client.return_value.__enter__.return_value = mock_instance

        from scripts_01.model_gateway import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            base_url="https://api.test.com/v1",
            api_key="sk-test",
        )

        chunks = list(provider.generate_stream(
            model="test-model",
            messages=[{"role": "user", "content": "Hi"}],
        ))

        contents = "".join(c.content for c in chunks)
        assert "A" in contents
        assert "B" in contents

    @patch("scripts_01.model_gateway.httpx.Client")
    def test_openai_stream_invalid_json_skipped(self, mock_client):
        """Тест что streaming пропускает невалидный JSON в SSE."""
        sse_lines = [
            'data: {invalid json',
            'data: {"choices": [{"delta": {"content": "OK"], "finish_reason": null]]]',
            'data: [DONE]',
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = iter(sse_lines)
        mock_resp.raise_for_status = MagicMock()

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__.return_value = mock_resp
        mock_stream_ctx.__exit__.return_value = False

        mock_instance = MagicMock()
        mock_instance.stream.return_value = mock_stream_ctx
        mock_client.return_value.__enter__.return_value = mock_instance

        from scripts_01.model_gateway import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            base_url="https://api.test.com/v1",
            api_key="sk-test",
        )

        chunks = list(provider.generate_stream(
            model="test-model",
            messages=[{"role": "user", "content": "Hi"}],
        ))

        # Invalid JSON should be skipped, valid content should pass
        contents = "".join(c.content for c in chunks)
        assert "OK" in contents


class TestProviderEndpoints:
    """Тесты конфигурации провайдеров."""

    def test_all_providers_have_base_url(self):
        for name, cfg in PROVIDER_ENDPOINTS.items():
            assert "base_url" in cfg, f"{name} missing base_url"
            assert cfg["base_url"].startswith("http"), f"{name} invalid base_url"

    def test_all_providers_have_models(self):
        for name, cfg in PROVIDER_ENDPOINTS.items():
            assert len(cfg["models"]) > 0, f"{name} has no models"
            for mname, minfo in cfg["models"].items():
                assert "max_tokens" in minfo, f"{mname} missing max_tokens"
                assert minfo["max_tokens"] > 0, f"{mname} invalid max_tokens"

    def test_deepseek_models(self):
        models = PROVIDER_ENDPOINTS["deepseek"]["models"]
        assert "deepseek-v4-flash" in models
        assert "deepseek-chat" in models

    def test_gemini_models(self):
        models = PROVIDER_ENDPOINTS["gemini"]["models"]
        assert "gemini-2.5-flash" in models

    def test_ollama_models(self):
        models = PROVIDER_ENDPOINTS["ollama"]["models"]
        assert "qwen2.5:1.5b" in models


class TestPolicyRouting:
    """Правило 11 (User-Choice Override): policy resolve → модель в ModelGateway."""

    class FakePolicy:
        """Policy с пользовательским override на coding → claude-code."""

        def resolve(self, capability):
            return {
                "capability": capability,
                "runtime": "claude-code",
                "source": "policy",
                "preferred": "claude-code",
            }

    def test_resolve_model_policy_override(self):
        """Policy override возвращает модель назначенного Runtime."""
        gw = ModelGateway(policy_engine=self.FakePolicy())
        model, fallback, source = gw.resolve_model(["coding"])
        assert model == "anthropic/claude-3.5-sonnet"
        assert fallback is None
        assert source == "policy:claude-code"

    def test_resolve_model_router_fallback(self):
        """Без policy — авто-выбор SmartRouter."""
        gw = ModelGateway()

        class FakeRouter:
            def route(self, required_capabilities=None, **kwargs):
                class Decision:
                    model = "gemini-2.5-flash"
                    model_id = "gemini-2.5-flash"
                    fallback_used = False
                return Decision()

        gw._router = FakeRouter()
        model, fallback, source = gw.resolve_model(["code"])
        assert model == "gemini-2.5-flash"
        assert source == "router"

    def test_resolve_model_cloud_first_when_ollama_down(self, monkeypatch):
        """Cloud-first (ANTI-6b): Ollama недоступен + есть ключи → облачная модель.

        documenter routing_hint ['summarize','explain']: без фильтра SmartRouter
        выбирает qwen2.5:1.5b (tie-break по latency). С health-check, где Ollama
        не отвечает, а у DeepSeek есть ключ — должен уйти на deepseek-v4-flash.
        """
        gw = ModelGateway()
        # Ollama не отвечает (health-check False) + DeepSeek имеет ключ.
        monkeypatch.setattr(gw, "_ollama_reachable", lambda: False)
        mock_pool = MagicMock()
        mock_pool.has_key.side_effect = lambda p: p == "deepseek"
        gw._keypool = mock_pool
        model, fallback, source = gw.resolve_model(["summarize", "explain"])
        assert model == "deepseek-v4-flash"
        assert source == "router"

    def test_resolve_model_picks_cloud_with_caps_when_keys_and_ollama_up(self, monkeypatch):
        """CON-65 (v5.189.52): availability-aware cloud-first.

        Когда Ollama доступен И облачные провайдеры имеют валидный ключ И их
        capabilities совпадают с запросом ['summarize', 'explain'] — SmartRouter
        предпочитает CLOUD (gemini-2.5-flash / llama-3.3-70b-versatile / deepseek-v4-flash)
        over local qwen2.5:1.5b. Это закрывает ANTI-6b trap: local НЕ выигрывает
        latency tie-break когда у облака есть ключ (CON-65 / v5.189.52).
        """
        gw = ModelGateway()
        monkeypatch.setattr(gw, "_ollama_reachable", lambda: True)
        mock_pool = MagicMock()
        mock_pool.has_key.return_value = True
        gw._keypool = mock_pool
        model, _fallback, _source = gw.resolve_model(["summarize", "explain"])
        # Cloud-wins over local (CON-65 closes ANTI-6b latency tie-break).
        assert model != "qwen2.5:1.5b", (
            f"CON-65: cloud с summarize+explain caps должен выиграть у "
            f"qwen2.5:1.5b когда has_key=True; got {model}"
        )
        # deepseek-v4-flash имеет только `summarize` (без `explain`),
        # поэтому для routing ["summarize","explain"] score=1 — НЕ выигрывает
        # tie-break у gemini/llama (score=2). Поэтому deepseek исключён.
        assert model in (
            "gemini-2.5-flash",
            "llama-3.3-70b-versatile",
        ), f"model {model} not in summarize+explain-capable cloud tier (CON-65 expectation)"

    def test_resolve_model_local_wins_when_no_cloud_keys(self, monkeypatch):
        """CON-65 negative case: Ollama reachable + NO cloud keys → local qwen wins.

        Symmetric pair to test_resolve_model_picks_cloud_with_caps_when_keys_and_ollama_up:
        asserts что "cloud preferred" НЕ переходит в "local dead даже когда offline".
        Local fallback remains the path when cloud keypool пуст (offline-режим).
        Без этого теста future over-correction (например, hardcoded
        `assert model != 'qwen'` everywhere) молча сломает offline/degraded-key
        scenarios.
        """
        gw = ModelGateway()
        monkeypatch.setattr(gw, "_ollama_reachable", lambda: True)
        mock_pool = MagicMock()
        mock_pool.has_key.return_value = False  # NO cloud keys
        gw._keypool = mock_pool
        model, _fallback, _source = gw.resolve_model(["summarize", "explain"])
        # CON-65 closed-loop: без cloud keys → local fallback обязателен.
        assert model == "qwen2.5:1.5b", (
            f"CON-65 negative case violated: when no cloud keys, local "
            f"qwen должен выиграть; got {model}. Убедиться что ANTI-6b "
            f"fix (cloud-first) не превратился в local-dead."
        )

    def test_resolve_model_cloud_first_on_tied_capability_score(self, monkeypatch):
        """CON-65 (v5.189.52): cloud-first при РАВНОМ capability-score.

        Для ['summarize'] qwen2.5:1.5b (local, 200ms), deepseek-v4-flash,
        gemini-2.5-flash, llama-3.3-70b-versatile — все score=1. БЕЗ
        cloud-first tie-break latency отдаёт local qwen (200ms). С ним —
        облако (llama 800ms). Честно закрывает ANTI-6b latency trap, а не
        только через score-differential (score 2 vs 1).
        """
        gw = ModelGateway()
        monkeypatch.setattr(gw, "_ollama_reachable", lambda: True)
        mock_pool = MagicMock()
        mock_pool.has_key.return_value = True  # all cloud have keys
        gw._keypool = mock_pool
        model, _fallback, _source = gw.resolve_model(["summarize"])
        assert model != "qwen2.5:1.5b", (
            f"CON-65 tied-score cloud-first violated: local qwen won latency "
            f"tie-break for ['summarize']; got {model}"
        )

    def test_provider_available_failsafe_when_keypool_broken(self, monkeypatch):
        """Кейпул недоступен → _provider_available не ломает роутинг (True)."""
        gw = ModelGateway()
        gw._keypool = None  # триггерит ленивый _import_keypool()

        def boom(*a, **k):
            raise RuntimeError("keypool import failed")

        monkeypatch.setattr("scripts_01.model_gateway._import_keypool", boom)
        from core_02.router import Provider
        assert gw._provider_available(Provider.DEEPSEEK) is True

    def test_generate_uses_policy_model(self):
        """generate(capabilities=...) вызывает модель из policy override."""
        gw = ModelGateway(policy_engine=self.FakePolicy())
        with patch.object(gw, "_call_with_fallback") as mock_call:
            mock_call.return_value = ModelResponse(
                content="ok", model="anthropic/claude-3.5-sonnet", provider="openrouter"
            )
            gw.generate(
                capabilities=["coding"],
                messages=[{"role": "user", "content": "hi"}],
            )
        kwargs = mock_call.call_args.kwargs
        assert kwargs["model"] == "anthropic/claude-3.5-sonnet"


# ─── v5.189.49: cross-provider cloud fallback (chain [deepseek, gemini, dashscope]) ─

from scripts_01.model_gateway import (
    PROVIDER_ENDPOINTS,
    _is_hard_error,
    _CLOUD_FALLBACK_CHAIN,
)


class TestCrossProviderFallback:
    """v5.189.49: cross-provider cloud fallback в `_call_with_fallback`.

    Hard error {'402/billing', '401/auth', '5xx/server'} → switch to next
    cloud provider WITH a key (e.g. deepseek → gemini → dashscope). НЕ
    повторяем тот же провайдер на hard error (ANTI-6b defense).
    """

    def test_cloud_fallback_402_switches_provider_once(self) -> None:
        """402 (billing) on deepseek → switch to gemini; failsafe: only 1 attempt at deepseek.

        ANTI-6b defense: повтор deepseek после 402 = трата attempt'а на
        заведомо failable payload (402 → снова 402). _call_with_fallback
        должен пойти по CLOUD_FALLBACK_CHAIN.
        """
        gw = ModelGateway()
        # Мок KeyPool: deepseek НЕТ ключа (force skip), gemini ЕСТЬ.
        mock_pool = MagicMock()
        mock_pool.has_key.side_effect = lambda p: p == "gemini"
        mock_pool.rotate.return_value = "sk-gemini-fake-key"
        gw._keypool = mock_pool

        call_count = {"deepseek": 0, "gemini": 0}

        def fake_generate(self, model, messages, temperature=0.7, max_tokens=None, timeout=60):
            pname = getattr(self, "_provider_name", "gemini")
            call_count[pname] += 1
            if pname == "deepseek":
                # Hard error 402 — provider error format: "API error 402: ..."
                raise RuntimeError("API error 402: Payment Required")
            return ModelResponse(
                content="ok-from-gemini", model=model, provider=pname,
            )

        with patch(
            "scripts_01.model_gateway.OpenAICompatibleProvider.generate", new=fake_generate
        ), patch(
            "scripts_01.model_gateway.GeminiProvider.generate", new=fake_generate
        ):
            result = gw.generate(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": "hi"}],
            )

        # Asserts: cross-provider switch from deepseek → gemini
        assert call_count["deepseek"] == 1, (
            f"expected ONLY 1 deepseek attempt (fail-fast), got {call_count['deepseek']}"
        )
        assert call_count["gemini"] == 1, (
            f"expected 1 gemini attempt (chain fallback), got {call_count['gemini']}"
        )
        assert result.fallback_used is True
        assert result.provider == "gemini"
        assert result.content == "ok-from-gemini"

    def test_cloud_fallback_5xx_switches_provider(self) -> None:
        """5xx (server error) on deepseek → switch to next provider."""
        gw = ModelGateway()
        mock_pool = MagicMock()
        mock_pool.has_key.side_effect = lambda p: p == "gemini"
        mock_pool.rotate.return_value = "sk-gemini-fake"
        gw._keypool = mock_pool

        def fake_generate(self, model, messages, temperature=0.7, max_tokens=None, timeout=60):
            if getattr(self, "_provider_name", "gemini") == "deepseek":
                raise RuntimeError("Stream API error 502: Bad Gateway")
            return ModelResponse(content="ok-from-gemini", model=model, provider="gemini")

        with patch(
            "scripts_01.model_gateway.OpenAICompatibleProvider.generate", new=fake_generate
        ), patch(
            "scripts_01.model_gateway.GeminiProvider.generate", new=fake_generate
        ):
            result = gw.generate(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": "hi"}],
            )
        assert result.fallback_used is True
        assert result.provider == "gemini"

    def test_no_key_for_next_provider_falls_to_next(self) -> None:
        """No key for gemini → fall to dashscope (NOT retry gemini)."""
        gw = ModelGateway()
        # KeyPool: deepseek has none, gemini has none, dashscope has one.
        mock_pool = MagicMock()
        mock_pool.has_key.side_effect = lambda p: p == "dashscope"
        mock_pool.rotate.return_value = "sk-dashscope-fake"
        gw._keypool = mock_pool

        def fake_generate(self, model, messages, temperature=0.7, max_tokens=None, timeout=60):
            if self._provider_name == "deepseek":
                raise RuntimeError("API error 402: Payment Required")
            return ModelResponse(
                content="ok-from-dashscope", model=model, provider=self._provider_name,
            )

        with patch(
            "scripts_01.model_gateway.OpenAICompatibleProvider.generate", new=fake_generate
        ):
            result = gw.generate(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": "hi"}],
            )
        # dashscope chosen (not gemini, because gemini.has_key=False)
        assert result.provider == "dashscope"
        assert result.fallback_used is True

    def test_fallback_exhaust_raises_runtime_error_with_provider_trail(self) -> None:
        """All 3 cloud providers fail (no keys, hard errors) → raise с trial_trail."""
        gw = ModelGateway()
        mock_pool = MagicMock()
        mock_pool.has_key.return_value = False  # NO keys
        gw._keypool = mock_pool

        def fake_generate(self, model, messages, temperature=0.7, max_tokens=None, timeout=60):
            raise RuntimeError(f"API error 503: Service Unavailable for {self._provider_name}")

        with patch(
            "scripts_01.model_gateway.OpenAICompatibleProvider.generate", new=fake_generate
        ):
            with pytest.raises(RuntimeError, match="All fallback providers exhausted"):
                gw.generate(
                    model="deepseek-v4-flash",
                    messages=[{"role": "user", "content": "hi"}],
                )

        # CON-17 white-box contract guard: chain order is part of platform
        # contract (CON-65). Surgical failure (this test only) if chain
        # grows; avoids import-time blast radius.
        assert tuple(_CLOUD_FALLBACK_CHAIN) == ("deepseek", "gemini", "dashscope"), (
            "CON-65 cloud fallback chain mutated without test coverage update"
        )

    def test_default_catalog_has_two_cloud_providers_with_summarize_explain(self) -> None:
        """v5.189.49: ≥2 cloud providers в ModelCatalog.default() must have
        'summarize' AND 'explain' capabilities, чтобы LLM-роли имели резервный маршрут при cloud outage.
        """
        from core_02.router import ModelCatalog, Provider

        catalog = ModelCatalog.default()
        cloud_providers_with_caps: list[tuple[str, Provider, list[str]]] = []
        for entry in catalog.all:
            if entry.provider == Provider.OLLAMA:
                continue  # only cloud
            cloud_providers_with_caps.append(
                (entry.name, entry.provider, entry.capabilities)
            )

        qualifying = [
            (name, prov) for name, prov, caps in cloud_providers_with_caps
            if "summarize" in caps and "explain" in caps
        ]
        assert len(qualifying) >= 2, (
            f"expected ≥2 cloud providers with summarize+explain, "
            f"got {len(qualifying)}: {[n for n, _ in qualifying]}"
        )

    def test_provider_available_ollama_true_when_reachable(self) -> None:
        """_provider_available(OLLAMA) → True когда локальная машина отвечает.

        Sanity-preserving: проверяет, что health-check Ollama корректно
        пробрасывается в _provider_available (True при reachable), не трогая
        cascade-логику cross-provider cloud fallback.
        """
        from core_02.router import ModelCatalog, Provider

        # _ollama_reachable True → первый роутер выберет локальную модель
        # без cloud fallback. Просто smoke: вызвать _ollama_reachable mock
        # и проверить что _provider_available(OLLAMA) → True.
        gw = ModelGateway()
        # Stub keypool
        mock_pool = MagicMock()
        mock_pool.has_key.return_value = False  # no cloud keys
        gw._keypool = mock_pool
        # Configure ollama_reachable to return True
        with patch(
            "scripts_01.model_gateway.ModelGateway._ollama_reachable",
            return_value=True,
        ):
            assert gw._provider_available(Provider.OLLAMA) is True
