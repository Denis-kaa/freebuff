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

from scripts.model_gateway import (
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

    @patch("scripts.model_gateway.httpx.Client")
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
        from scripts.event_bus import EventBus, Event
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
