"""
Tests for ModelGateway — providers, fallback, token counting, EventBus integration.
"""

import json
import os
import sys
import tempfile
***REMOVED***
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
            {"role": "user", "content": "Hello"***REMOVED***,
            {"role": "assistant", "content": "Hi there!"***REMOVED***,
        ***REMOVED***
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
        assert r.usage["total_tokens"***REMOVED*** == 0
        assert r.latency_ms == 0
        assert not r.fallback_used
        assert not r.cached

    def test_with_usage(self):
        r = ModelResponse(
            content="Hi",
            model="m",
            provider="p",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15***REMOVED***,
            latency_ms=200,
            fallback_used=True,
        )
        assert r.usage["total_tokens"***REMOVED*** == 15
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
        assert status["total_providers"***REMOVED*** >= 3

    def test_models_available(self):
        """Проверяем, что все модели из PROVIDER_ENDPOINTS имеют корректную конфигурацию."""
        for pname, cfg in PROVIDER_ENDPOINTS.items():
            assert "base_url" in cfg, f"{pname***REMOVED*** missing base_url"
            assert len(cfg["models"***REMOVED***) > 0, f"{pname***REMOVED*** has no models"
            for mname, minfo in cfg["models"***REMOVED***.items():
                assert "max_tokens" in minfo, f"{mname***REMOVED*** missing max_tokens"
                # Проверяем, что _model_to_provider маппит модель
                mapped = _model_to_provider(mname)
                assert mapped is not None, f"{mname***REMOVED*** not mapped by _model_to_provider"
                # OpenRouter модели с / маппятся в openrouter
                if "/" in mname:
                    assert mapped == "openrouter", f"{mname***REMOVED*** should map to openrouter, got {mapped***REMOVED***"

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
            "choices": [{"message": {"content": "Hello from mock"***REMOVED***, "finish_reason": "stop"***REMOVED******REMOVED***,
            "model": "deepseek-v4-flash",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15***REMOVED***,
        ***REMOVED***
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
            messages=[{"role": "user", "content": "Hi"***REMOVED******REMOVED***,
        )

        assert result.content == "Hello from mock"
        assert result.model == "deepseek-v4-flash"
        assert result.usage["total_tokens"***REMOVED*** == 15
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

        received = [***REMOVED***

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
        gw._publish_event(result, [{"role": "user", "content": "test"***REMOVED******REMOVED***)

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
                capabilities=["code", "fast"***REMOVED***,
                messages=[{"role": "user", "content": "write code"***REMOVED******REMOVED***,
            )

            # Проверяем что generate вызван с capabilities
            _, kwargs = mock_gen.call_args
            assert kwargs.get("capabilities") == ["code", "fast"***REMOVED***

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
        c = StreamChunk(content="Hi", model="m", usage={"total_tokens": 42***REMOVED***)
        assert c.usage["total_tokens"***REMOVED*** == 42


class TestStreaming:
    """Тесты streaming для всех провайдеров."""

    @patch("scripts_01.model_gateway.httpx.Client")
    def test_openai_stream_sse_format(self, mock_client):
        """Тест OpenAI-совместимого streaming (SSE format)."""
        # Мокаем SSE ответ: data: {json***REMOVED*** lines + data: [DONE***REMOVED***
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"***REMOVED***, "finish_reason": null***REMOVED******REMOVED***, "model": "deepseek-v4-flash"***REMOVED***',
            'data: {"choices": [{"delta": {"content": " world"***REMOVED***, "finish_reason": null***REMOVED******REMOVED***, "model": "deepseek-v4-flash"***REMOVED***',
            'data: {"choices": [{"delta": {***REMOVED***, "finish_reason": "stop"***REMOVED******REMOVED***, "model": "deepseek-v4-flash", "usage": {"total_tokens": 15***REMOVED******REMOVED***',
            'data: [DONE***REMOVED***',
        ***REMOVED***

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
            messages=[{"role": "user", "content": "Hi"***REMOVED******REMOVED***,
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
            'data: {"candidates": [{"content": {"parts": [{"text": "Hello"***REMOVED******REMOVED******REMOVED***, "finishReason": null***REMOVED******REMOVED******REMOVED***',
            'data: {"candidates": [{"content": {"parts": [{"text": " from Gemini"***REMOVED******REMOVED******REMOVED***, "finishReason": "STOP"***REMOVED******REMOVED***, "usageMetadata": {"totalTokenCount": 20***REMOVED******REMOVED***',
        ***REMOVED***

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
            messages=[{"role": "user", "content": "Hi"***REMOVED******REMOVED***,
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
            '{"model": "qwen2.5:1.5b", "message": {"content": "Hello"***REMOVED***, "done": false***REMOVED***',
            '{"model": "qwen2.5:1.5b", "message": {"content": " world"***REMOVED***, "done": false***REMOVED***',
            '{"model": "qwen2.5:1.5b", "message": {"content": ""***REMOVED***, "done": true, "prompt_eval_count": 10, "eval_count": 5***REMOVED***',
        ***REMOVED***

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
            messages=[{"role": "user", "content": "Hi"***REMOVED******REMOVED***,
        ))

        contents = "".join(c.content for c in chunks)
        assert "Hello" in contents
        assert "world" in contents
        # Final chunk should have usage
        final_chunks = [c for c in chunks if c.usage is not None***REMOVED***
        assert len(final_chunks) >= 1
        assert final_chunks[-1***REMOVED***.usage["total_tokens"***REMOVED*** == 15

    def test_base_provider_stream_fallback(self):
        """Тест fallback streaming в BaseProvider (без реального стриминга)."""
        from scripts_01.model_gateway import BaseProvider

        class FakeProvider(BaseProvider):
            def generate(self, model, messages, temperature=0.7, max_tokens=None, timeout=60):
                return ModelResponse(content="full response", model=model, provider="fake")

        provider = FakeProvider()
        chunks = list(provider.generate_stream(
            model="test",
            messages=[{"role": "user", "content": "Hi"***REMOVED******REMOVED***,
        ))

        # BaseProvider fallback yields content then stop
        assert len(chunks) == 2
        assert chunks[0***REMOVED***.content == "full response"
        assert chunks[1***REMOVED***.finish_reason == "stop"

    @patch("scripts_01.model_gateway.httpx.Client")
    def test_gateway_generate_stream(self, mock_client):
        """Тест ModelGateway.generate_stream() с моком провайдера."""
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hi"***REMOVED***, "finish_reason": null***REMOVED******REMOVED***, "model": "deepseek-v4-flash"***REMOVED***',
            'data: {"choices": [{"delta": {***REMOVED***, "finish_reason": "stop"***REMOVED******REMOVED***, "model": "deepseek-v4-flash"***REMOVED***',
            'data: [DONE***REMOVED***',
        ***REMOVED***

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
            messages=[{"role": "user", "content": "Hello"***REMOVED******REMOVED***,
        ))

        assert len(chunks) >= 1
        assert any(c.content == "Hi" for c in chunks)

    def test_generate_stream_no_model_raises(self):
        """Тест что generate_stream() без model вызывает ValueError."""
        gw = ModelGateway()
        with pytest.raises(ValueError, match="model is required"):
            list(gw.generate_stream(messages=[{"role": "user", "content": "Hi"***REMOVED******REMOVED***))

    @patch("scripts_01.model_gateway.httpx.Client")
    def test_openai_stream_handles_empty_lines(self, mock_client):
        """Тест что streaming игнорирует пустые строки в SSE."""
        sse_lines = [
            '',
            'data: {"choices": [{"delta": {"content": "A"***REMOVED***, "finish_reason": null***REMOVED******REMOVED******REMOVED***',
            '',
            'data: {"choices": [{"delta": {"content": "B"***REMOVED***, "finish_reason": null***REMOVED******REMOVED******REMOVED***',
            '',
            'data: [DONE***REMOVED***',
        ***REMOVED***

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
            messages=[{"role": "user", "content": "Hi"***REMOVED******REMOVED***,
        ))

        contents = "".join(c.content for c in chunks)
        assert "A" in contents
        assert "B" in contents

    @patch("scripts_01.model_gateway.httpx.Client")
    def test_openai_stream_invalid_json_skipped(self, mock_client):
        """Тест что streaming пропускает невалидный JSON в SSE."""
        sse_lines = [
            'data: {invalid json',
            'data: {"choices": [{"delta": {"content": "OK"***REMOVED***, "finish_reason": null***REMOVED******REMOVED******REMOVED***',
            'data: [DONE***REMOVED***',
        ***REMOVED***

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
            messages=[{"role": "user", "content": "Hi"***REMOVED******REMOVED***,
        ))

        # Invalid JSON should be skipped, valid content should pass
        contents = "".join(c.content for c in chunks)
        assert "OK" in contents


class TestProviderEndpoints:
    """Тесты конфигурации провайдеров."""

    def test_all_providers_have_base_url(self):
        for name, cfg in PROVIDER_ENDPOINTS.items():
            assert "base_url" in cfg, f"{name***REMOVED*** missing base_url"
            assert cfg["base_url"***REMOVED***.startswith("http"), f"{name***REMOVED*** invalid base_url"

    def test_all_providers_have_models(self):
        for name, cfg in PROVIDER_ENDPOINTS.items():
            assert len(cfg["models"***REMOVED***) > 0, f"{name***REMOVED*** has no models"
            for mname, minfo in cfg["models"***REMOVED***.items():
                assert "max_tokens" in minfo, f"{mname***REMOVED*** missing max_tokens"
                assert minfo["max_tokens"***REMOVED*** > 0, f"{mname***REMOVED*** invalid max_tokens"

    def test_deepseek_models(self):
        models = PROVIDER_ENDPOINTS["deepseek"***REMOVED***["models"***REMOVED***
        assert "deepseek-v4-flash" in models
        assert "deepseek-chat" in models

    def test_gemini_models(self):
        models = PROVIDER_ENDPOINTS["gemini"***REMOVED***["models"***REMOVED***
        assert "gemini-2.5-flash" in models

    def test_ollama_models(self):
        models = PROVIDER_ENDPOINTS["ollama"***REMOVED***["models"***REMOVED***
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
            ***REMOVED***

    def test_resolve_model_policy_override(self):
        """Policy override возвращает модель назначенного Runtime."""
        gw = ModelGateway(policy_engine=self.FakePolicy())
        model, fallback, source = gw.resolve_model(["coding"***REMOVED***)
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
        model, fallback, source = gw.resolve_model(["code"***REMOVED***)
        assert model == "gemini-2.5-flash"
        assert source == "router"

    def test_generate_uses_policy_model(self):
        """generate(capabilities=...) вызывает модель из policy override."""
        gw = ModelGateway(policy_engine=self.FakePolicy())
        with patch.object(gw, "_call_with_fallback") as mock_call:
            mock_call.return_value = ModelResponse(
                content="ok", model="anthropic/claude-3.5-sonnet", provider="openrouter"
            )
            gw.generate(
                capabilities=["coding"***REMOVED***,
                messages=[{"role": "user", "content": "hi"***REMOVED******REMOVED***,
            )
        kwargs = mock_call.call_args.kwargs
        assert kwargs["model"***REMOVED*** == "anthropic/claude-3.5-sonnet"
