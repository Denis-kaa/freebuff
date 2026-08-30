"""tests_09/test_integration_base.py — Hermetic тесты IntegrationAdapter (ADR-020).

Покрывает:
- AuthSpec (декларация доступа: is_public, is_token_based, frozen)
- AdapterRequest / AdapterResponse (round-trip, сериализация)
- INTENT_CAPABILITY_MAP (закрытый словарь, все токены ∈ KNOWN_CAPABILITIES)
- IntegrationAdapter.handle (нормализованный вход/выход)
- route_to_capability (known intent, unknown → fallback)
- call_platform (SmartRouter делегат, fail-safe)
- event_bus observability (log_event no-op / emit)
- Helpers (_ok_response / _err_response)
- 🚫 §7.3: adapter НЕ вызывает ForgePipeline напрямую
"""

from __future__ import annotations

}
from typing import Any, Dict, List

import pytest

from core_02.integration_base import (
    INTENT_CAPABILITY_MAP,
    AdapterDirection,
    AdapterRequest,
    AdapterResponse,
    AuthMethod,
    AuthSpec,
    IntegrationAdapter,
)


# ═══════════════════════════════════════════════════════════════════════
# Fake helpers
# ═══════════════════════════════════════════════════════════════════════

class _FakeEventBus:
    """Фейк event_bus для тестов наблюдаемости."""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def emit(self, event_type: str, **kwargs: Any) -> None:
        self.events.append({"type": event_type, **kwargs})


class _FakeRouteDecision:
    def __init__(self, model: str = "test-model", provider: Any = "local",
                 reason: str = "capability_match", fallback_used: bool = False) -> None:
        self.model = model
        self.provider = provider
        self.reason = reason
        self.fallback_used = fallback_used


class _ConcreteAdapter(IntegrationAdapter):
    """Минимальная реализация IntegrationAdapter для тестов."""

    def handle(
        self,
        request: AdapterRequest,
        *,
        event_bus: Any = None,
    ) -> AdapterResponse:
        capability = self.route_to_capability(request.intent)
        result = self.call_platform(capability, request.payload, event_bus=event_bus)
        response = self._ok_response(
            request,
            data=result,
            capability=capability,
            model=result.get("model_used"),
        )
        self.log_event(event_bus, "adapter.inbound", request, response)
        return response


class _FailOpenAdapter(IntegrationAdapter):
    """Адаптер, у которого call_platform всегда падает — проверяет fail-safe."""

    def handle(
        self,
        request: AdapterRequest,
        *,
        event_bus: Any = None,
    ) -> AdapterResponse:
        # Симулируем сбой платформы
        try:
            raise RuntimeError("platform offline")
        except RuntimeError as exc:
            return self._err_response(request, errors=[str(exc)])


class _AuthAdapter(IntegrationAdapter):
    """Адаптер с нестандартным AuthSpec."""

    def handle(
        self,
        request: AdapterRequest,
        *,
        event_bus: Any = None,
    ) -> AdapterResponse:
        return self._ok_response(request, data={"auth_method": self.auth.method.value})


# ═══════════════════════════════════════════════════════════════════════
# Test: AuthSpec
# ═══════════════════════════════════════════════════════════════════════

class TestAuthSpec:
    """Декларация доступа на границе."""

    def test_none_is_public(self) -> None:
        spec = AuthSpec(method=AuthMethod.NONE, scope="local")
        assert spec.is_public() is True
        assert spec.is_token_based() is False

    def test_bearer_is_token_based(self) -> None:
        spec = AuthSpec(method=AuthMethod.BEARER, scope="freebuff-api")
        assert spec.is_public() is False
        assert spec.is_token_based() is True

    def test_chat_id_scope_not_token_based(self) -> None:
        spec = AuthSpec(method=AuthMethod.CHAT_ID_SCOPE, scope="Saved Messages")
        assert spec.is_token_based() is False
        assert spec.scope == "Saved Messages"

    def test_phone_scope(self) -> None:
        spec = AuthSpec(method=AuthMethod.PHONE_SCOPE, scope="termux-device")
        assert spec.method == AuthMethod.PHONE_SCOPE
        assert spec.is_public() is False

    def test_frozen(self) -> None:
        spec = AuthSpec(method=AuthMethod.NONE)
        with pytest.raises(Exception):  # dataclass frozen
            spec.method = AuthMethod.BEARER  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# Test: AdapterRequest / AdapterResponse
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterRequestResponse:
    """Нормализованный вход/выход."""

    def test_request_to_dict(self) -> None:
        req = AdapterRequest(
            intent="execute_project",
            payload={"project": "demo"},
            meta={"chat_id": 123},
        )
        d = req.to_dict()
        assert d["intent"] == "execute_project"
        assert d["payload"] == {"project": "demo"}
        assert d["meta"] == {"chat_id": 123}

    def test_response_ok(self) -> None:
        resp = AdapterResponse(
            status="ok",
            intent="report",
            data={"lines": 42},
            capability_used="summarize",
            model_used="deepseek-v4-flash",
        )
        assert resp.ok is True
        d = resp.to_dict()
        assert d["status"] == "ok"
        assert d["capability_used"] == "summarize"
        assert d["model_used"] == "deepseek-v4-flash"

    def test_response_error(self) -> None:
        resp = AdapterResponse(
            status="error",
            intent="unknown_intent",
            errors=["unsupported intent"],
            warnings=["deprecated"],
        )
        assert resp.ok is False
        d = resp.to_dict()
        assert "model_used" not in d  # None не сериализуется
        assert "capability_used" not in d

    def test_response_to_dict_omits_none_fields(self) -> None:
        resp = AdapterResponse(status="ok", intent="test")
        d = resp.to_dict()
        assert "capability_used" not in d
        assert "model_used" not in d


# ═══════════════════════════════════════════════════════════════════════
# Test: INTENT_CAPABILITY_MAP
# ═══════════════════════════════════════════════════════════════════════

class TestIntentCapabilityMap:
    """Закрытый словарь: все capability-токены ∈ agent_base.KNOWN_CAPABILITIES."""

    def test_all_tokens_in_known_capabilities(self) -> None:
        from core_02.agent_base import KNOWN_CAPABILITIES

        unknown = set(INTENT_CAPABILITY_MAP.values()) - KNOWN_CAPABILITIES
        assert not unknown, (
            f"INTENT_CAPABILITY_MAP содержит capability-токены вне "
            f"KNOWN_CAPABILITIES: {sorted(unknown)}. "
            f"См. ANTI-6b / ADR-020 §Decision пункт 3."
        )

    def test_fallback_key_exists(self) -> None:
        assert "fallback" in INTENT_CAPABILITY_MAP

    def test_known_intents_have_valid_capability(self) -> None:
        all_caps = set(INTENT_CAPABILITY_MAP.values())
        # Каждый capability — непустая строка
        for cap in all_caps:
            assert isinstance(cap, str)
            assert len(cap) > 0

    def test_fallback_capability_is_summarize(self) -> None:
        assert INTENT_CAPABILITY_MAP["fallback"] == "summarize"


# ═══════════════════════════════════════════════════════════════════════
# Test: route_to_capability
# ═══════════════════════════════════════════════════════════════════════

class TestRouteToCapability:
    """Intent → capability через закрытый словарь."""

    def test_known_intent_maps_to_capability(self) -> None:
        adapter = _ConcreteAdapter(adapter_id="tg")
        assert adapter.route_to_capability("execute_project") == "code"
        assert adapter.route_to_capability("review_code") == "review"
        assert adapter.route_to_capability("report") == "summarize"

    def test_unknown_intent_falls_back(self) -> None:
        adapter = _ConcreteAdapter(adapter_id="tg")
        result = adapter.route_to_capability("nonexistent_intent_xyz")
        assert result == "summarize"  # fallback, НЕ краш

    def test_fallback_intent_returns_summarize(self) -> None:
        adapter = _ConcreteAdapter(adapter_id="tg")
        assert adapter.route_to_capability("fallback") == "summarize"


# ═══════════════════════════════════════════════════════════════════════
# Test: call_platform
# ═══════════════════════════════════════════════════════════════════════

class TestCallPlatform:
    """Capability → SmartRouter → модель (явный вызов)."""

    def test_call_platform_returns_dict_with_model(self) -> None:
        adapter = _ConcreteAdapter(adapter_id="tg")
        result = adapter.call_platform("code", {"task": "test"})
        assert isinstance(result, dict)
        assert result["status"] == "ok"
        assert "model_used" in result
        assert len(result["model_used"]) > 0

    def test_call_platform_with_different_capability(self) -> None:
        adapter = _ConcreteAdapter(adapter_id="http")
        result = adapter.call_platform("review", {"file": "x.py"})
        assert result["status"] == "ok"
        assert "model_used" in result

    def test_call_platform_failsafe_on_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = _ConcreteAdapter(adapter_id="tg")
        original_import = __import__

        def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "core_02.router":
                raise ImportError("router unavailable")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _fake_import)
        result = adapter.call_platform("code", {"task": "test"})
        assert result["status"] == "error"
        assert "error" in result

    def test_call_platform_uses_passed_capability(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Проверяет, что call_platform передаёт capability в router.route."""
        captured_caps: List[List[str]] = []

        class _FakeCatalog:
            @staticmethod
            def default() -> "_FakeCatalog":
                return _FakeCatalog()

        class _FakeRouter:
            def __init__(self, catalog: Any) -> None:
                pass

            def route(self, required_capabilities: List[str] | None = None, **kwargs: Any) -> _FakeRouteDecision:
                captured_caps.append(list(required_capabilities or []))
                return _FakeRouteDecision(model="fake-model")

        monkeypatch.setattr("core_02.router.SmartRouter", _FakeRouter)
        monkeypatch.setattr("core_02.router.ModelCatalog", _FakeCatalog)

        adapter = _ConcreteAdapter(adapter_id="tg")
        result = adapter.call_platform("review", {"file": "x.py"})
        assert result["model_used"] == "fake-model"
        assert len(captured_caps) == 1
        assert captured_caps[0] == ["review"]

    def test_call_platform_marks_fallback_used(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _FakeCatalog:
            @staticmethod
            def default() -> "_FakeCatalog":
                return _FakeCatalog()

        class _FakeRouter:
            def __init__(self, catalog: Any) -> None:
                pass

            def route(self, required_capabilities: Any = None, **kwargs: Any) -> _FakeRouteDecision:
                return _FakeRouteDecision(model="fallback-model", fallback_used=True)

        monkeypatch.setattr("core_02.router.SmartRouter", _FakeRouter)
        monkeypatch.setattr("core_02.router.ModelCatalog", _FakeCatalog)

        adapter = _ConcreteAdapter(adapter_id="tg")
        result = adapter.call_platform("code", {})
        assert result["fallback_used"] is True


# ═══════════════════════════════════════════════════════════════════════
# Test: Concrete adapters
# ═══════════════════════════════════════════════════════════════════════

class TestConcreteAdapter:
    """Работа конкретных адаптеров."""

    def test_handle_routes_and_calls_platform(self) -> None:
        adapter = _ConcreteAdapter(adapter_id="tg", direction=AdapterDirection.INBOUND)
        request = AdapterRequest(intent="execute_project", payload={"project": "demo"})
        response = adapter.handle(request)
        assert response.ok is True
        assert response.capability_used == "code"
        assert response.model_used is not None
        assert "model_used" in response.data

    def test_handle_unknown_intent_still_responds(self) -> None:
        adapter = _ConcreteAdapter(adapter_id="tg")
        request = AdapterRequest(intent="weird_unknown_intent", payload={})
        response = adapter.handle(request)
        assert response.ok is True
        assert response.capability_used == "summarize"  # fallback

    def test_fail_open_adapter_returns_error_response(self) -> None:
        adapter = _FailOpenAdapter(adapter_id="fail-adapter")
        request = AdapterRequest(intent="report")
        response = adapter.handle(request)
        assert response.ok is False
        assert response.errors == ["platform offline"]

    def test_auth_adapter_has_correct_spec(self) -> None:
        auth = AuthSpec(method=AuthMethod.CHAT_ID_SCOPE, scope="Saved Messages")
        adapter = _AuthAdapter(
            adapter_id="tg_auth",
            direction=AdapterDirection.BIDIRECTIONAL,
            auth=auth,
        )
        assert adapter.auth.method == AuthMethod.CHAT_ID_SCOPE
        assert adapter.auth.scope == "Saved Messages"
        response = adapter.handle(AdapterRequest(intent="report"))
        assert response.data["auth_method"] == "chat_id_scope"

    def test_adapter_repr(self) -> None:
        adapter = _ConcreteAdapter(adapter_id="tg_bot")
        r = repr(adapter)
        assert "tg_bot" in r
        assert "inbound" in r
        assert "none" in r


# ═══════════════════════════════════════════════════════════════════════
# Test: event_bus observability
# ═══════════════════════════════════════════════════════════════════════

class TestEventBus:
    """Наблюдаемость: каждый inbound логируется."""

    def test_log_event_emits_on_bus(self) -> None:
        bus = _FakeEventBus()
        adapter = _ConcreteAdapter(adapter_id="tg")
        request = AdapterRequest(intent="report")
        response = adapter.handle(request, event_bus=bus)
        assert len(bus.events) == 1
        evt = bus.events[0]
        assert evt["type"] == "adapter.inbound"
        assert evt["adapter_id"] == "tg"
        assert evt["intent"] == "report"
        assert evt["status"] == "ok"

    def test_log_event_noop_when_bus_is_none(self) -> None:
        adapter = _ConcreteAdapter(adapter_id="tg")
        request = AdapterRequest(intent="report")
        # Не крашится, когда event_bus is None
        response = adapter.handle(request, event_bus=None)
        assert response.ok is True

    def test_log_event_silent_failure(self) -> None:
        """Бросающий event_bus не ломает основной поток."""

        class _ThrowingBus:
            def emit(self, *args: Any, **kwargs: Any) -> None:
                raise RuntimeError("bus down")

        adapter = _ConcreteAdapter(adapter_id="tg")
        request = AdapterRequest(intent="report")
        response = adapter.handle(request, event_bus=_ThrowingBus())
        assert response.ok is True  # основной поток не задет


# ═══════════════════════════════════════════════════════════════════════
# Test: §7.3 grep-инвариант
# ═══════════════════════════════════════════════════════════════════════

class TestForgePipelineInvariant:
    """§7.3: Adapter НЕ вызывает ForgePipeline напрямую."""

    def test_integration_base_does_not_import_forge_pipeline(self) -> None:
        src = __import__("core_02.integration_base").integration_base.__file__
        assert src is not None
        text = open(src, encoding="utf-8").read()
        code_only = re.sub(r'""".*?"""', "", text, flags=re.DOTALL)
        code_only = re.sub(r"#.*", "", code_only)
        assert "ForgePipeline" not in code_only, (
            "§7.3 violation: IntegrationAdapter импортирует ForgePipeline напрямую "
            "(допустим только SmartRouter/ModelCatalog через call_platform)"
        )

    def test_integration_base_only_calls_smart_router(self) -> None:
        import inspect
        src = inspect.getsource(IntegrationAdapter.call_platform)
        code_only = re.sub(r'""".*?"""', "", src, flags=re.DOTALL)
        code_only = re.sub(r"#.*", "", code_only)
        assert "SmartRouter" in code_only
        assert "ModelCatalog" in code_only
        assert "ForgePipeline" not in code_only, (
            "§7.3 violation: call_platform вызывает ForgePipeline напрямую "
            "(допустим только SmartRouter/ModelCatalog)"
        )


# ═══════════════════════════════════════════════════════════════════════
# Test: BrowserUseAdapter integration conformance
# ═══════════════════════════════════════════════════════════════════════

class TestBrowserUseConformance:
    """Adapter skeleton for browser-use agent (CONTRACT_GRAPH §G1: new entry point)."""

    def test_browser_use_adapter_conforms_to_contract(self) -> None:
        """Конформность: адаптер с browser_use id и PHONE_SCOPE auth."""
        adapter = _ConcreteAdapter(
            adapter_id="browser_use",
            direction=AdapterDirection.BIDIRECTIONAL,
            auth=AuthSpec(method=AuthMethod.PHONE_SCOPE, scope="termux-chrome"),
        )
        assert adapter.adapter_id == "browser_use"
        assert adapter.direction == AdapterDirection.BIDIRECTIONAL
        assert adapter.auth.method == AuthMethod.PHONE_SCOPE
        assert adapter.auth.scope == "termux-chrome"

    def test_browser_use_handles_request(self) -> None:
        adapter = _ConcreteAdapter(
            adapter_id="browser_use",
            auth=AuthSpec(method=AuthMethod.PHONE_SCOPE, scope="termux-chrome"),
        )
        request = AdapterRequest(
            intent="mcp_request",
            payload={"url": "https://example.com", "action": "navigate"},
        )
        response = adapter.handle(request)
        assert response.ok is True
        assert response.capability_used == "code"