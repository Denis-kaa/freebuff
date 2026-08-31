"""Tests for freebuff_plugin_03/policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from freebuff_plugin_03.policy import CapabilityPolicy, PolicyContext, PolicyEngine, PolicyRule


@pytest.fixture
def sample_policy_file(tmp_path: Path):
    path = tmp_path / "policies.json"
    path.write_text(
        """{
  \"version\": \"1.0\",
  \"policies\": {
    \"coding\": {
      \"preferred_runtime\": \"claude-code\",
      \"fallback_chain\": [\"freebuff\", \"openclaw\"],
      \"constraints\": [
        {\"rule_type\": \"min_confidence\", \"params\": {\"value\": 0.7}]
      }
    },
    \"research\": {
      \"preferred_runtime\": \"openclaw\",
      \"fallback_chain\": [\"freebuff\"]
    }
  }
]""",
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
            capabilities = ["coding"]
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
        }

    def score_runtime(self, runtime_name: str, capability: str) -> float:
        return self._score


class TestPolicyConfig:
    def test_policy_rule_creation(self):
        rule = PolicyRule(rule_type="max_latency", params={"value": 2000})
        assert rule.rule_type == "max_latency"
        assert rule.params["value"] == 2000

    def test_policy_rule_empty_type_raises(self):
        with pytest.raises(ValueError):
            PolicyRule(rule_type="")

    def test_capability_policy_defaults(self):
        policy = CapabilityPolicy(preferred_runtime="freebuff")
        assert policy.preferred_runtime == "freebuff"
        assert policy.fallback_chain == []
        assert policy.constraints == []

    def test_policy_context_defaults(self):
        ctx = PolicyContext()
        assert ctx.max_latency_ms == 5000
        assert ctx.required_flags == []
        assert ctx.exclude == []


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
        assert policies["coding"].preferred_runtime == "claude-code"

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
        policy_file.write_text('{"version": "1.0", "policies": {)]')
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(policy_file),
        )
        engine.set_preference("coding", "freebuff")
        assert engine.get_policy("coding").preferred_runtime == "freebuff"

    def test_unset_preference_clears(self, tmp_path: Path):
        policy_file = tmp_path / "policies.json"
        policy_file.write_text('{"version": "1.0", "policies": {)]')
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(policy_file),
        )
        engine.set_preference("coding", "freebuff")
        assert engine.unset_preference("coding") is True
        # Пустая политика удаляется целиком → авто-выбор системы восстанавливается
        assert engine.get_policy("coding") is None
        assert engine.select_runtime("coding") == "freebuff"  # через cap registry fallback

    def test_unset_preference_missing_capability(self, tmp_path: Path):
        policy_file = tmp_path / "policies.json"
        policy_file.write_text('{"version": "1.0", "policies": {)]')
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(policy_file),
        )
        assert engine.unset_preference("unknown") is False

    def test_unset_preference_no_preferred(self, sample_policy_file: Path):
        """Политика с fallback_chain, но без preferred_runtime → False, цепь сохраняется."""
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(sample_policy_file),
        )
        # research: preferred_runtime = "openclaw" — сначала сбросим
        assert engine.unset_preference("research") is True
        # повторный unset — уже нет preferred
        assert engine.unset_preference("research") is False
        assert engine.get_policy("research").fallback_chain == ["freebuff"]

    def test_constraint_filters_low_confidence(self, tmp_path: Path):
        policy_file = tmp_path / "policies.json"
        policy_file.write_text(
            """{
  \"version\": \"1.0\",
  \"policies\": {
    \"coding\": {
      \"preferred_runtime\": \"claude-code\",
      \"fallback_chain\": [\"freebuff\"],
      \"constraints\": [
        {\"rule_type\": \"min_confidence\", \"params\": {\"value\": 0.9}]
      }
    }
  }
]""",
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
        assert engine.list_policies() == {}

    def test_malformed_policy_file_ignored(self, tmp_path: Path):
        policy_file = tmp_path / "bad.json"
        policy_file.write_text("not valid json", encoding="utf-8")
        engine = PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(policy_file),
        )
        assert engine.list_policies() == {}


class TestPolicyCLI:
    """CLI `freebuff policy ...` (правило 11 User-Choice Override)."""

    def _make_cli_engine(self, tmp_path: Path):
        """PolicyEngine с мок-реестрами и временным policy-файлом."""
        policy_file = tmp_path / "policies.json"
        policy_file.write_text('{"version": "1.0", "policies": {)]')
        return PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(policy_file),
        )

    def _patch_engine(self, monkeypatch, engine):
        import freebuff_cli
        monkeypatch.setattr(freebuff_cli, "_get_policy_engine", lambda: engine)
        return freebuff_cli

    def test_policy_set(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        cli = self._patch_engine(monkeypatch, self._make_cli_engine(tmp_path))
        cli.cmd_policy("set", "coding", "deepseek-v4-flash")
        out = capsys.readouterr().out
        assert "deepseek-v4-flash" in out
        engine = freebuff_cli._get_policy_engine()
        assert engine.get_policy("coding").preferred_runtime == "deepseek-v4-flash"

    def test_policy_get_assigned(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        engine = self._make_cli_engine(tmp_path)
        engine.set_preference("coding", "claude-code")
        self._patch_engine(monkeypatch, engine)
        freebuff_cli.cmd_policy("get", "coding")
        out = capsys.readouterr().out
        assert "claude-code" in out

    def test_policy_get_unassigned(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        self._patch_engine(monkeypatch, self._make_cli_engine(tmp_path))
        freebuff_cli.cmd_policy("get", "coding")
        out = capsys.readouterr().out
        assert "не назначено" in out

    def test_policy_unset(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        engine = self._make_cli_engine(tmp_path)
        engine.set_preference("coding", "freebuff")
        self._patch_engine(monkeypatch, engine)
        freebuff_cli.cmd_policy("unset", "coding")
        out = capsys.readouterr().out
        assert "сброшено" in out
        assert freebuff_cli._get_policy_engine().get_policy("coding") is None

    def test_policy_list(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        engine = self._make_cli_engine(tmp_path)
        engine.set_preference("coding", "freebuff")
        engine.set_preference("research", "openclaw")
        self._patch_engine(monkeypatch, engine)
        freebuff_cli.cmd_policy("list")
        out = capsys.readouterr().out
        assert "coding" in out
        assert "research" in out

    def test_policy_resolve(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        engine = self._make_cli_engine(tmp_path)
        engine.set_preference("coding", "freebuff")
        self._patch_engine(monkeypatch, engine)
        freebuff_cli.cmd_policy("resolve", "coding")
        out = capsys.readouterr().out
        assert "freebuff" in out

    def test_policy_usage_unknown_action(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        self._patch_engine(monkeypatch, self._make_cli_engine(tmp_path))
        freebuff_cli.cmd_policy("bogus")
        out = capsys.readouterr().out
        assert "policy set" in out

    def test_policy_set_missing_args(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        self._patch_engine(monkeypatch, self._make_cli_engine(tmp_path))
        freebuff_cli.cmd_policy("set", "coding")
        out = capsys.readouterr().out
        assert "capability и runtime" in out


class TestPolicyRules:
    def test_max_latency_rule(self):
        from freebuff_plugin_03.policy.rules import evaluate_rule
        rule = PolicyRule("max_latency", {"value": 1000})
        context = PolicyContext()
        assert evaluate_rule(rule, {"name": "fast", "latency_ms": 500}, context)
        assert not evaluate_rule(rule, {"name": "slow", "latency_ms": 2000}, context)

    def test_exclude_rule(self):
        from freebuff_plugin_03.policy.rules import evaluate_rule
        rule = PolicyRule("exclude", {"runtimes": ["bad"]})
        context = PolicyContext(exclude=["unstable"])
        assert evaluate_rule(rule, {"name": "good"}, context)
        assert not evaluate_rule(rule, {"name": "bad"}, context)
        assert not evaluate_rule(rule, {"name": "unstable"}, context)

    def test_required_flags_rule(self):
        from freebuff_plugin_03.policy.rules import evaluate_rule
        rule = PolicyRule("required_flags", {"flags": ["gpu"]})
        context = PolicyContext()
        assert evaluate_rule(rule, {"name": "gpu-runtime", "flags": ["gpu", "fast"]}, context)
        assert not evaluate_rule(rule, {"name": "cpu-runtime", "flags": []}, context)

    def test_min_confidence_rule(self):
        from freebuff_plugin_03.policy.rules import evaluate_rule
        rule = PolicyRule("min_confidence", {"value": 0.8})
        context = PolicyContext()
        assert evaluate_rule(rule, {"name": "good", "confidence": 0.9}, context)
        assert not evaluate_rule(rule, {"name": "bad", "confidence": 0.5}, context)

    def test_unknown_rule_type_fails_closed(self):
        from freebuff_plugin_03.policy.rules import evaluate_rule
        rule = PolicyRule("unknown", {})
        context = PolicyContext()
        assert not evaluate_rule(rule, {"name": "any"}, context)
