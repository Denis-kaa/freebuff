"""Tests for conversational User-Choice Override (правило 11, promt37).

Покрывает:
  - parse_override_intent — распознавание фраз «используй X вместо Y» (EN/RU)
  - apply_override — применение через PolicyEngine (persist в policies.json)
  - PolicyEngine.resolve — source-aware резолв (policy vs auto)
  - CLI `freebuff policy override <фраза>`
"""

from __future__ import annotations

***REMOVED***

import pytest

from freebuff_plugin_03.policy import (
    PolicyEngine,
    apply_override,
    parse_override_intent,
)
from freebuff_plugin_03.policy.conversational import DEFAULT_CAPABILITY


class MockRuntimeRegistry:
    """Minimal runtime registry for policy tests."""

    def get(self, name: str):
        class FakeRuntime:
            class Status:
                value = "connected"
            status = Status()
            capabilities = ["coding"***REMOVED***
        return FakeRuntime()

    def is_connected(self, name: str) -> bool:
        return True


class MockCapabilityRegistry:
    """Minimal capability registry for policy tests."""

    def get_runtime_for_capability(self, capability: str, preferred_runtime: str | None = None):
        return {"runtime": "freebuff", "confidence": 0.8, "connected": True***REMOVED***

    def score_runtime(self, runtime_name: str, capability: str) -> float:
        return 0.8


def make_engine(tmp_path: Path) -> PolicyEngine:
    policy_file = tmp_path / "policies.json"
    policy_file.write_text('{"version": "1.0", "policies": {***REMOVED******REMOVED***', encoding="utf-8")
    return PolicyEngine(
        MockRuntimeRegistry(),
        MockCapabilityRegistry(),
        policy_file=str(policy_file),
    )


class TestParseOverrideIntent:
    """Парсинг диалоговых фраз переопределения."""

    def test_en_instead_of_for(self):
        intent = parse_override_intent("use deepseek instead of claude for coding")
        assert intent is not None
        assert intent.runtime == "deepseek"
        assert intent.capability == "coding"

    def test_en_for_only(self):
        intent = parse_override_intent("use claude-code for review")
        assert intent is not None
        assert intent.runtime == "claude-code"
        assert intent.capability == "review"

    def test_ru_use_for(self):
        intent = parse_override_intent("используй deepseek-v4-flash для research")
        assert intent is not None
        assert intent.runtime == "deepseek-v4-flash"
        assert intent.capability == "research"

    def test_ru_reversed(self):
        intent = parse_override_intent("для planning используй freebuff")
        assert intent is not None
        assert intent.runtime == "freebuff"
        assert intent.capability == "planning"

    def test_switch_to(self):
        intent = parse_override_intent("switch coding to claude-code")
        assert intent is not None
        assert intent.runtime == "claude-code"
        assert intent.capability == "coding"

    def test_instead_of_default_capability(self):
        intent = parse_override_intent("use openclaw instead of claude")
        assert intent is not None
        assert intent.runtime == "openclaw"
        assert intent.capability == DEFAULT_CAPABILITY  # coding

    def test_no_override_returns_none(self):
        assert parse_override_intent("просто расскажи про архитектуру") is None
        assert parse_override_intent("") is None
        assert parse_override_intent(None) is None

    def test_case_insensitive(self):
        intent = parse_override_intent("USE DEEPSEEK INSTEAD OF CLAUDE FOR CODING")
        assert intent is not None
        assert intent.runtime == "deepseek"
        assert intent.capability == "coding"

    def test_ru_case_insensitive(self):
        """Cyrillic uppercase фолдится под re.IGNORECASE (правило 11)."""
        intent = parse_override_intent("ИСПОЛЬЗУЙ DEEPSEEK ДЛЯ RESEARCH")
        assert intent is not None
        assert intent.runtime == "deepseek"
        assert intent.capability == "research"


class TestApplyOverride:
    """Применение диалогового переопределения через PolicyEngine."""

    def test_applies_preference(self, tmp_path: Path):
        engine = make_engine(tmp_path)
        result = apply_override("use deepseek instead of claude for coding", engine)
        assert result is not None
        assert result["applied"***REMOVED*** is True
        assert result["capability"***REMOVED*** == "coding"
        assert result["runtime"***REMOVED*** == "deepseek"
        assert result["previous_runtime"***REMOVED*** is None
        # Предпочтение сохранено и учитывается при resolve
        assert engine.get_policy("coding").preferred_runtime == "deepseek"
        assert engine.select_runtime("coding") == "deepseek"

    def test_replaces_existing_preference(self, tmp_path: Path):
        engine = make_engine(tmp_path)
        engine.set_preference("coding", "claude-code")
        result = apply_override("switch coding to freebuff", engine)
        assert result is not None
        assert result["previous_runtime"***REMOVED*** == "claude-code"
        assert engine.get_policy("coding").preferred_runtime == "freebuff"

    def test_unrecognized_returns_none(self, tmp_path: Path):
        engine = make_engine(tmp_path)
        assert apply_override("hello world", engine) is None
        # Ничего не изменилось
        assert engine.list_policies() == {***REMOVED***

    def test_dry_run_does_not_write(self, tmp_path: Path):
        """dry_run=True: интент распознан, но set_preference НЕ вызывается."""
        engine = make_engine(tmp_path)
        result = apply_override(
            "use deepseek instead of claude for coding",
            engine,
            dry_run=True,
        )
        assert result is not None
        assert result["applied"***REMOVED*** is False
        assert result["dry_run"***REMOVED*** is True
        assert result["capability"***REMOVED*** == "coding"
        assert result["runtime"***REMOVED*** == "deepseek"
        # Ничего не записано в policies.json
        assert engine.list_policies() == {***REMOVED***
        assert engine.get_policy("coding") is None

    def test_dry_run_with_existing_preference_shows_previous(self, tmp_path: Path):
        """dry_run показывает текущее значение как previous_runtime, но не меняет его."""
        engine = make_engine(tmp_path)
        engine.set_preference("coding", "claude-code")
        result = apply_override(
            "use deepseek instead of claude for coding",
            engine,
            dry_run=True,
        )
        assert result is not None
        assert result["applied"***REMOVED*** is False
        assert result["previous_runtime"***REMOVED*** == "claude-code"
        # Значение не изменилось
        assert engine.get_policy("coding").preferred_runtime == "claude-code"

    def test_capability_override(self, tmp_path: Path):
        """capability=... переопределяет capability, распознанную из фразы."""
        engine = make_engine(tmp_path)
        result = apply_override(
            "use deepseek instead of claude for coding",
            engine,
            capability="research",
        )
        assert result is not None
        assert result["applied"***REMOVED*** is True
        assert result["capability"***REMOVED*** == "research"
        assert result["runtime"***REMOVED*** == "deepseek"
        # Запись в research, а не coding
        assert engine.get_policy("coding") is None
        assert engine.get_policy("research").preferred_runtime == "deepseek"

    def test_capability_override_with_dry_run(self, tmp_path: Path):
        """capability + dry_run: переопределение распознано, но не записано."""
        engine = make_engine(tmp_path)
        result = apply_override(
            "use deepseek instead of claude for coding",
            engine,
            capability="research",
            dry_run=True,
        )
        assert result is not None
        assert result["applied"***REMOVED*** is False
        assert result["dry_run"***REMOVED*** is True
        assert result["capability"***REMOVED*** == "research"
        assert engine.list_policies() == {***REMOVED***

    def test_dry_run_without_engine_is_safe(self):
        """dry_run=True с engine=None не падает (get_policy в try/except).

        Закрепляет путь, используемый эндпоинтом POST /policy/override:
        dry_run разрешён без PolicyEngine (503 только при реальном применении).
        """
        result = apply_override(
            "use deepseek instead of claude for coding",
            None,
            dry_run=True,
        )
        assert result is not None
        assert result["applied"***REMOVED*** is False
        assert result["dry_run"***REMOVED*** is True
        assert result["previous_runtime"***REMOVED*** is None


class TestPolicyResolve:
    """PolicyEngine.resolve — source-aware резолв (правило 11)."""

    def test_resolve_auto_source(self, tmp_path: Path):
        engine = make_engine(tmp_path)
        resolved = engine.resolve("coding")
        assert resolved["capability"***REMOVED*** == "coding"
        assert resolved["runtime"***REMOVED*** == "freebuff"  # через cap registry fallback
        assert resolved["source"***REMOVED*** == "auto"
        assert resolved["preferred"***REMOVED*** is None

    def test_resolve_policy_source(self, tmp_path: Path):
        engine = make_engine(tmp_path)
        engine.set_preference("coding", "claude-code")
        resolved = engine.resolve("coding")
        assert resolved["runtime"***REMOVED*** == "claude-code"
        assert resolved["source"***REMOVED*** == "policy"
        assert resolved["preferred"***REMOVED*** == "claude-code"


class TestPolicyOverrideCLI:
    """CLI `freebuff policy override <фраза>` (правило 11)."""

    def _patch_engine(self, monkeypatch, engine):
        import freebuff_cli
        monkeypatch.setattr(freebuff_cli, "_get_policy_engine", lambda: engine)
        return freebuff_cli

    def test_override_command(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        engine = make_engine(tmp_path)
        self._patch_engine(monkeypatch, engine)
        freebuff_cli.cmd_policy(
            "override", "use deepseek instead of claude for coding"
        )
        out = capsys.readouterr().out
        assert "coding → deepseek" in out
        assert engine.get_policy("coding").preferred_runtime == "deepseek"

    def test_override_ru(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        engine = make_engine(tmp_path)
        self._patch_engine(monkeypatch, engine)
        freebuff_cli.cmd_policy("override", "используй freebuff для research")
        out = capsys.readouterr().out
        assert "research → freebuff" in out
        assert engine.get_policy("research").preferred_runtime == "freebuff"

    def test_override_unrecognized(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        engine = make_engine(tmp_path)
        self._patch_engine(monkeypatch, engine)
        freebuff_cli.cmd_policy("override", "непонятная фраза")
        out = capsys.readouterr().out
        assert "Не удалось распознать" in out
        assert engine.list_policies() == {***REMOVED***

    def test_override_missing_message(self, tmp_path: Path, monkeypatch, capsys):
        import freebuff_cli
        self._patch_engine(monkeypatch, make_engine(tmp_path))
        freebuff_cli.cmd_policy("override")
        out = capsys.readouterr().out
        assert "Укажи фразу" in out
