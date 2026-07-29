"""Tests for freebuff_plugin/policy."""

from __future__ import annotations

***REMOVED***

import pytest

from freebuff_plugin.policy import CapabilityPolicy, PolicyContext, PolicyEngine, PolicyRule


@pytest.fixture
def sample_policy_file(tmp_path: Path):
    path = tmp_path / "policies.json"
    path.write_text(
        """{
  \"version\": \"1.0\",
  \"policies\": {
    \"coding\": {
      \"preferred_runtime\": \"claude-code\",
      \"fallback_chain\": [\"freebuff\", \"openclaw\"***REMOVED***,
      \"constraints\": [
        {\"rule_type\": \"min_confidence\", \"params\": {\"value\": 0.7***REMOVED******REMOVED***
      ***REMOVED***
    ***REMOVED***,
    \"research\": {
      \"preferred_runtime\": \"openclaw\",
      \"fallback_chain\": [\"freebuff\"***REMOVED***
    ***REMOVED***
  ***REMOVED***
***REMOVED***""",
        encoding="utf-8",
    )
    return path


class MockRuntimeRegistry:
    """Minimal runtime registry for policy tests."""

    def __init__(self, connected: str | None = None):
        self._connected = connected or ""

    def get(self, name: str):
        class FakeRuntime:
            class Status:
                value = "connected"
            status = Status()
            capabilities = ["coding"***REMOVED***
        return FakeRuntime()

    def is_connected(self, name: str) -> bool:
        return name == self._connected


class MockCapabilityRegistry:
    """Minimal capability registry for policy tests."""

    def __init__(self, score: float = 0.8):
        self._score = score

    def get_runtime_for_capability(self, capability: str, preferred_runtime: str | None = None):
        return {
            "runtime": "freebuff",
            "confidence": self._score,
            "connected": True,
        ***REMOVED***

    def score_runtime(self, runtime_name: str, capability: str) -> float:
        return self._score


class TestPolicyConfig:
    def test_policy_rule_creation(self):
        rule = PolicyRule(rule_type="max_latency", params={"value": 2000***REMOVED***)
        assert rule.rule_type == "max_latency"
        assert rule.params["value"***REMOVED*** == 2000

    def test_policy_rule_empty_type_raises(self):
        with pytest.raises(ValueError):
            PolicyRule(rule_type="")

    def test_capability_policy_defaults(self):
        policy = CapabilityPolicy(preferred_runtime="freebuff")
        assert policy.preferred_runtime == "freebuff"
        assert policy.fallback_chain == [***REMOVED***
        assert policy.constraints == [***REMOVED***

    def test_policy_context_defaults(self):
        ctx = PolicyContext()
        assert ctx.max_latency_ms == 5000
        assert ctx.required_flags == [***REMOVED***
        assert ctx.exclude == [***REMOVED***


class TestPolicyEngine:
    def test_load_policy(self, sample_policy_file: Path):
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(sample_policy_file),
        )
        policies = engine.list_policies()
        assert "coding" in policies
        assert "research" in policies
        assert policies["coding"***REMOVED***.preferred_runtime == "claude-code"

    def test_select_runtime_preferred(self, sample_policy_file: Path):
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(sample_policy_file),
        )
        runtime = engine.select_runtime("coding")
        assert runtime == "claude-code"

    def test_select_runtime_unknown_capability(self, sample_policy_file: Path):
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(sample_policy_file),
        )
        runtime = engine.select_runtime("unknown")
        assert runtime == "freebuff"

    def test_set_preference(self, tmp_path: Path):
        policy_file = tmp_path / "policies.json"
        policy_file.write_text('{"version": "1.0", "policies": {***REMOVED******REMOVED***')
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(policy_file),
        )
        engine.set_preference("coding", "freebuff")
        assert engine.get_policy("coding").preferred_runtime == "freebuff"

    def test_constraint_filters_low_confidence(self, tmp_path: Path):
        policy_file = tmp_path / "policies.json"
        policy_file.write_text(
            """{
  \"version\": \"1.0\",
  \"policies\": {
    \"coding\": {
      \"preferred_runtime\": \"claude-code\",
      \"fallback_chain\": [\"freebuff\"***REMOVED***,
      \"constraints\": [
        {\"rule_type\": \"min_confidence\", \"params\": {\"value\": 0.9***REMOVED******REMOVED***
      ***REMOVED***
    ***REMOVED***
  ***REMOVED***
***REMOVED***""",
            encoding="utf-8",
        )
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(score=0.5),
            policy_file=str(policy_file),
        )
        runtime = engine.select_runtime("coding")
        assert runtime == "freebuff"

    def test_empty_policy_file(self, tmp_path: Path):
        policy_file = tmp_path / "missing.json"
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(policy_file),
        )
        assert engine.list_policies() == {***REMOVED***

    def test_malformed_policy_file_ignored(self, tmp_path: Path):
        policy_file = tmp_path / "bad.json"
        policy_file.write_text("not valid json", encoding="utf-8")
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(policy_file),
        )
        assert engine.list_policies() == {***REMOVED***


class TestPolicyRules:
    def test_max_latency_rule(self):
        from freebuff_plugin.policy.rules import evaluate_rule
        rule = PolicyRule("max_latency", {"value": 1000***REMOVED***)
        context = PolicyContext()
        assert evaluate_rule(rule, {"name": "fast", "latency_ms": 500***REMOVED***, context)
        assert not evaluate_rule(rule, {"name": "slow", "latency_ms": 2000***REMOVED***, context)

    def test_exclude_rule(self):
        from freebuff_plugin.policy.rules import evaluate_rule
        rule = PolicyRule("exclude", {"runtimes": ["bad"***REMOVED******REMOVED***)
        context = PolicyContext(exclude=["unstable"***REMOVED***)
        assert evaluate_rule(rule, {"name": "good"***REMOVED***, context)
        assert not evaluate_rule(rule, {"name": "bad"***REMOVED***, context)
        assert not evaluate_rule(rule, {"name": "unstable"***REMOVED***, context)

    def test_required_flags_rule(self):
        from freebuff_plugin.policy.rules import evaluate_rule
        rule = PolicyRule("required_flags", {"flags": ["gpu"***REMOVED******REMOVED***)
        context = PolicyContext()
        assert evaluate_rule(rule, {"name": "gpu-runtime", "flags": ["gpu", "fast"***REMOVED******REMOVED***, context)
        assert not evaluate_rule(rule, {"name": "cpu-runtime", "flags": [***REMOVED******REMOVED***, context)

    def test_min_confidence_rule(self):
        from freebuff_plugin.policy.rules import evaluate_rule
        rule = PolicyRule("min_confidence", {"value": 0.8***REMOVED***)
        context = PolicyContext()
        assert evaluate_rule(rule, {"name": "good", "confidence": 0.9***REMOVED***, context)
        assert not evaluate_rule(rule, {"name": "bad", "confidence": 0.5***REMOVED***, context)

    def test_unknown_rule_type_fails_closed(self):
        from freebuff_plugin.policy.rules import evaluate_rule
        rule = PolicyRule("unknown", {***REMOVED***)
        context = PolicyContext()
        assert not evaluate_rule(rule, {"name": "any"***REMOVED***, context)
