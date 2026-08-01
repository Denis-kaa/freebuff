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
        names = {e.name for e in entries***REMOVED***
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
        scored = catalog.match(["vision"***REMOVED***)
        assert len(scored) >= 1
        best_entry, best_score = scored[0***REMOVED***
        assert best_score == 1
        assert "gemini" in best_entry.name

    def test_match_multiple_capabilities(self, catalog):
        scored = catalog.match(["local", "fast"***REMOVED***)
        best_entry, best_score = scored[0***REMOVED***
        assert best_score >= 2
        assert best_entry.provider == Provider.OLLAMA

    def test_match_no_capabilities_returns_all(self, catalog):
        scored = catalog.match([***REMOVED***)
        assert len(scored) == len(catalog.all)

    def test_match_context_penalty(self, catalog):
        scored = catalog.match([***REMOVED***, max_tokens=100000)
        small_models = [e.name for e, s in scored if "0.5b" in e.name***REMOVED***
        assert "qwen2.5:0.5b" not in small_models

    def test_match_scoring_order(self, catalog):
        scored = catalog.match(["code", "reasoning", "fast"***REMOVED***)
        best_entry, best_score = scored[0***REMOVED***
        assert best_score >= 2


class TestSmartRouter:
    """Router tests at module level (not nested)."""

    def test_route_by_vision_capability(self, router):
        decision = router.route(required_capabilities=["vision"***REMOVED***)
        assert "gemini" in decision.model.lower()
        assert decision.fallback_used is False

    def test_route_by_local_preference(self, router):
        decision = router.route(
            required_capabilities=["summarize"***REMOVED***,
            preference=Preference.LOCAL,
        )
        assert decision.provider == Provider.OLLAMA

    def test_route_by_local_fast(self, router):
        decision = router.route(
            required_capabilities=["local", "fast"***REMOVED***,
        )
        assert decision.provider == Provider.OLLAMA
        assert decision.fallback_used is False

    def test_route_by_code_reasoning(self, router):
        decision = router.route(
            required_capabilities=["code", "reasoning"***REMOVED***,
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
            required_capabilities=["impossible_capability_xyz"***REMOVED***,
        )
        assert decision.fallback_used is True
        assert "fallback" in decision.reason

    def test_empty_catalog_raises(self):
        empty = SmartRouter(ModelCatalog([***REMOVED***), fallback="nonexistent")
        with pytest.raises(RuntimeError, match="No models"):
            empty.route()

    def test_fallback_model_works(self, router):
        cat = ModelCatalog([
            ModelEntry(
                "gemini-2.5-flash", Provider.GEMINI,
                capabilities=["vision"***REMOVED***,
            ),
        ***REMOVED***)
        r = SmartRouter(cat, fallback="gemini-2.5-flash")
        decision = r.route(required_capabilities=["impossible"***REMOVED***)
        assert decision.model == "gemini-2.5-flash"
        assert decision.fallback_used is True

    def test_route_returns_route_decision_type(self, router):
        decision = router.route(required_capabilities=["code"***REMOVED***)
        assert isinstance(decision, RouteDecision)
        assert isinstance(decision.model, str)
        assert isinstance(decision.provider, Provider)


class TestSmartRouterIntegration:
    """Integration tests with real scenarios."""

    def test_vision_task(self, router):
        decision = router.route(
            required_capabilities=["vision", "multimodal"***REMOVED***,
        )
        assert "gemini" in decision.model.lower()

    def test_simple_offline_task(self, router):
        decision = router.route(
            required_capabilities=["local", "fast"***REMOVED***,
        )
        assert decision.provider == Provider.OLLAMA

    def test_deep_reasoning_task(self, router):
        decision = router.route(
            required_capabilities=["deep", "architecture", "review"***REMOVED***,
        )
        assert decision.provider == Provider.DEEPSEEK
        assert "pro" in decision.model

    def test_large_context_task(self, router):
        decision = router.route(
            required_capabilities=["long_context"***REMOVED***,
            max_tokens_needed=500000,
        )
        assert decision.provider in (Provider.GEMINI, Provider.DEEPSEEK)
