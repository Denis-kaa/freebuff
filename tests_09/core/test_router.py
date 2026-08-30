"""
Tests for freebuff/core_02/router.py — Capability-based Router.
"""

import pytest
from freebuff.core_02.router import (
    SmartRouter, ModelCatalog, ModelEntry,
    Provider, Preference, RouteDecision,
)


@pytest.fixture
def catalog():
    return ModelCatalog.default()


@pytest.fixture
def router(catalog):
    return SmartRouter(catalog, fallback="gemini-2.5-flash")


class TestModelCatalog:

    def test_default_catalog(self, catalog):
        entries = catalog.all
        assert len(entries) >= 6
        names = {e.name for e in entries}
        assert "qwen2.5:1.5b" in names
        assert "deepseek-v4-flash" in names
        assert "gemini-2.5-flash" in names

    def test_list_by_provider(self, catalog):
        ollama_models = catalog.list_by_provider(Provider.OLLAMA)
        assert len(ollama_models) >= 2
        assert all(e.provider == Provider.OLLAMA for e in ollama_models)

    def test_list_by_capability(self, catalog):
        vision_models = catalog.list_by_capability("vision")
        assert any("gemini" in e.name for e in vision_models)
        assert len(vision_models) == 1

    def test_get_existing(self, catalog):
        e = catalog.get("deepseek-v4-pro")
        assert e is not None
        assert e.provider == Provider.DEEPSEEK

    def test_get_missing(self, catalog):
        assert catalog.get("nonexistent") is None

    def test_add_entry(self, catalog):
        catalog.add(ModelEntry("new-model", Provider.GROQ))
        assert catalog.get("new-model") is not None

    def test_match_by_capability(self, catalog):
        scored = catalog.match(["vision"])
        assert len(scored) >= 1
        best_entry, best_score = scored[0]
        assert best_score == 1
        assert "gemini" in best_entry.name

    def test_match_multiple_capabilities(self, catalog):
        scored = catalog.match(["local", "fast"])
        best_entry, best_score = scored[0]
        assert best_score >= 2
        assert best_entry.provider == Provider.OLLAMA

    def test_match_no_capabilities_returns_all(self, catalog):
        scored = catalog.match([])
        assert len(scored) == len(catalog.all)

    def test_match_context_penalty(self, catalog):
        scored = catalog.match([], max_tokens=100000)
        small_models = [e.name for e, s in scored if "0.5b" in e.name]
        assert "qwen2.5:0.5b" not in small_models

    def test_match_scoring_order(self, catalog):
        scored = catalog.match(["code", "reasoning", "fast"])
        best_entry, best_score = scored[0]
        assert best_score >= 2


class TestSmartRouter:
    """Router tests at module level (not nested)."""

    def test_route_by_vision_capability(self, router):
        decision = router.route(required_capabilities=["vision"])
        assert "gemini" in decision.model.lower()
        assert decision.fallback_used is False

    def test_route_by_local_preference(self, router):
        decision = router.route(
            required_capabilities=["summarize"],
            preference=Preference.LOCAL,
        )
        assert decision.provider == Provider.OLLAMA

    def test_route_by_local_fast(self, router):
        decision = router.route(
            required_capabilities=["local", "fast"],
        )
        assert decision.provider == Provider.OLLAMA
        assert decision.fallback_used is False

    def test_route_by_code_reasoning(self, router):
        decision = router.route(
            required_capabilities=["code", "reasoning"],
        )
        assert decision.provider in (
            Provider.DEEPSEEK, Provider.GROQ, Provider.GEMINI
        )

    def test_route_without_capabilities(self, router):
        decision = router.route(
            preference=Preference.FAST,
        )
        assert isinstance(decision, RouteDecision)
        assert decision.model
        assert decision.fallback_used is False

    def test_route_no_match_fallback(self, router):
        decision = router.route(
            required_capabilities=["impossible_capability_xyz"],
        )
        assert decision.fallback_used is True
        assert "fallback" in decision.reason

    def test_empty_catalog_raises(self):
        empty = SmartRouter(ModelCatalog([]), fallback="nonexistent")
        with pytest.raises(RuntimeError, match="No models"):
            empty.route()

    def test_fallback_model_works(self, router):
        cat = ModelCatalog([
            ModelEntry(
                "gemini-2.5-flash", Provider.GEMINI,
                capabilities=["vision"],
            ),
        ])
        r = SmartRouter(cat, fallback="gemini-2.5-flash")
        decision = r.route(required_capabilities=["impossible"])
        assert decision.model == "gemini-2.5-flash"
        assert decision.fallback_used is True

    def test_route_returns_route_decision_type(self, router):
        decision = router.route(required_capabilities=["code"])
        assert isinstance(decision, RouteDecision)
        assert isinstance(decision.model, str)
        assert isinstance(decision.provider, Provider)


class TestSmartRouterAvailability:
    """Cloud-first роутинг: provider_available фильтрует недоступные провайдеры.

    ANTI-6b defense (core_02/LESSONS.md): если локальная qwen2.5:1.5b
    (Ollama) не запущена, а у облачных провайдеров есть ключи — роутер
    ДОЛЖЕН выбрать облачную модель, а не падать в gen_failed. Без фильтра
    qwen2.5:1.5b выигрывает tie-break по latency (200ms vs 2000ms).
    """

    def test_route_filters_unavailable_local_provider(self, catalog):
        """documenter ['summarize','explain']: недоступный Ollama не выбирается."""
        def available(provider):
            return provider != Provider.OLLAMA
        r = SmartRouter(catalog, fallback="gemini-2.5-flash",
                        provider_available=available)
        decision = r.route(required_capabilities=["summarize", "explain"])
        # Cloud-first contract: selection is data-driven by score/latency;
        # it must not depend on one hard-coded cloud provider winning the tie.
        assert decision.provider in (
            Provider.DEEPSEEK, Provider.GEMINI, Provider.GROQ,
            Provider.SAMBANOVA, Provider.OPENROUTER,
        )
        assert decision.provider != Provider.OLLAMA
        assert decision.model != "qwen2.5:1.5b"
        assert decision.fallback_used is False

    def test_route_prefers_available_cloud_when_availability_known(self, catalog):
        """При известной доступности cloud-first выбирает лучшую cloud-модель."""
        r = SmartRouter(catalog, fallback="gemini-2.5-flash",
                        provider_available=lambda p: True)
        decision = r.route(required_capabilities=["summarize", "explain"])
        assert decision.provider in (
            Provider.DEEPSEEK, Provider.GEMINI, Provider.GROQ,
            Provider.SAMBANOVA, Provider.OPENROUTER,
        )
        assert decision.provider != Provider.OLLAMA
        assert decision.fallback_used is False

    def test_route_all_unavailable_falls_back_to_best_effort(self, catalog):
        """Ни один провайдер не доступен → graceful degradation (не exception)."""
        r = SmartRouter(catalog, fallback="gemini-2.5-flash",
                        provider_available=lambda p: False)
        decision = r.route(required_capabilities=["summarize", "explain"])
        # Best-effort: возвращает какое-то решение (падение поймает вызывающий).
        assert decision.model

    def test_route_no_availability_param_uses_catalog_ranking(self, catalog):
        """Без provider_available используется обычный ranking каталога (BC)."""
        required = ["summarize", "explain"]
        r = SmartRouter(catalog, fallback="gemini-2.5-flash")
        decision = r.route(required_capabilities=required)
        expected = catalog.match(required)[0][0]
        assert decision.model == expected.name
        assert decision.provider == expected.provider
        assert decision.fallback_used is False


class TestSmartRouterIntegration:
    """Integration tests with real scenarios."""

    def test_vision_task(self, router):
        decision = router.route(
            required_capabilities=["vision", "multimodal"],
        )
        assert "gemini" in decision.model.lower()

    def test_simple_offline_task(self, router):
        decision = router.route(
            required_capabilities=["local", "fast"],
        )
        assert decision.provider == Provider.OLLAMA

    def test_deep_reasoning_task(self, router):
        decision = router.route(
            required_capabilities=["deep", "architecture", "review"],
        )
        assert decision.provider == Provider.DEEPSEEK
        assert "pro" in decision.model

    def test_large_context_task(self, router):
        decision = router.route(
            required_capabilities=["long_context"],
            max_tokens_needed=500000,
        )
        assert decision.provider in (Provider.GEMINI, Provider.DEEPSEEK)
