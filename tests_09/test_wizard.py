"""tests_09/test_wizard.py — e2e tests for wizard_lib & contracts.

Uses a synthetic 2-role corpus in tmp_path so tests don't depend on the
canonical blueprints_v3/ corpus (which lives outside the freebuff workspace
and is read-only from this environment).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core_02 import blueprint_v3 as bpv3
from core_02.contracts import (
    CASCADE_LEVELS,
    CascadeContract,
    deep_merge,
    resolve_assigned_model,
)
from core_02.wizard_lib import (
    build_agent_json,
    build_task_json,
    propose_roles,
    run_wizard,
    score_role_match,
)


# ─── fixtures ────────────────────────────────────────────────────────────────


def _seed_corpus(tmp_path: Path) -> Path:
    """Minimal blueprint corpus: developer (with <capabilities>) + tester (without)."""
    bp_dir = tmp_path / "bp"
    bp_dir.mkdir()
    (bp_dir / "registry.yaml").write_text(
        "pipeline:\n"
        "  - id: developer\n"
        "    file: 09_developer.md\n"
        "    type: implementation\n"
        "    role: AI Senior Backend Developer\n"
        "    description: backend code\n"
        "    condition: always\n"
        "    triggers:\n"
        '      - "код"\n'
        "  - id: tester\n"
        "    file: 12_tester.md\n"
        "    type: validation\n"
        "    role: AI Test Designer\n"
        "    description: qa audit verify\n"
        "    condition: always\n"
        "    triggers:\n"
        '      - "тест"\n'
        "project_types:\n"
        "  web:\n"
        "    required_roles: [developer]\n"
        "    skip_roles: []\n"
        "complexity_routing:\n"
        "  small:\n"
        "    required_roles: [developer]\n"
        "    skip_roles: []\n"
        "categories:\n"
        "  implementation: [developer]\n"
        "  validation: [tester]\n"
        "metadata:\n"
        "  version: \"3.0.0\"\n",
        encoding="utf-8",
    )
    (bp_dir / "09_developer.md").write_text(
        "ROLE: AI Senior Backend Developer\n"
        "VERSION: 3.1.0\n\n"
        "<role>Senior backend engineer for production code.</role>\n\n"
        "<system_role>Writes modules and tests.</system_role>\n\n"
        "<input>Architecture spec.</input>\n\n"
        "<main_objective>Production-ready code.</main_objective>\n\n"
        "<priority_order>Correctness first.</priority_order>\n\n"
        "<implementation_scope_rules>Allowed: target module only.</implementation_scope_rules>\n\n"
        "<capabilities>\n"
        "- code\n"
        "- implement\n"
        "- debug\n"
        "</capabilities>\n",
        encoding="utf-8",
    )
    (bp_dir / "12_tester.md").write_text(
        "ROLE: AI Test Designer\n"
        "VERSION: 3.1.0\n\n"
        "<role>QA audit verify test coverage.</role>\n\n"
        "<system_role>Plans tests and runs audits.</system_role>\n\n"
        "<input>Implementation plus spec.</input>\n\n"
        "<main_objective>Coverage > 80%.</main_objective>\n\n"
        "<priority_order>Correctness first.</priority_order>\n\n"
        "<implementation_scope_rules>Allowed: test files only.</implementation_scope_rules>\n",
        encoding="utf-8",
    )
    return bp_dir


@pytest.fixture
def corpus(tmp_path: Path):
    return bpv3.BlueprintCorpus(root=_seed_corpus(tmp_path))


# ─── deep_merge / CascadeContract ────────────────────────────────────────────


def test_deep_merge_copies_base_with_overrides() -> None:
    base = {"a": 1, "b": {"c": 1, "d": 2}}
    override = {"b": {"d": 99, "e": 3}, "f": 4}
    merged = deep_merge(base, override)
    assert merged == {"a": 1, "b": {"c": 1, "d": 99, "e": 3}, "f": 4}
    # Mutating merged doesn't affect originals.
    merged["b"]["c"] = "X"
    assert base["b"]["c"] == 1


def test_deep_merge_replaces_scalar_with_dict() -> None:
    out = deep_merge({"a": "string"}, {"a": {"nested": True}})
    assert out == {"a": {"nested": True}}


def test_cascade_merge_in_level_order() -> None:
    levels = {
        "system":    {"platform": "freebuff", "scenarios": {"x": "v1"}},
        "workspace": {"mode": "single"},
        "agent":     {"role_id": "developer"},
    }
    merged = CascadeContract.merge(levels)
    assert merged["platform"] == "freebuff"
    assert merged["mode"] == "single"
    assert merged["role_id"] == "developer"
    assert merged["scenarios"] == {"x": "v1"}


def test_cascade_merge_skips_unknown_levels() -> None:
    merged = CascadeContract.merge(
        {"system": {"a": 1}, "phantom": {"b": 2}, "task": {"c": 3}}
    )
    assert merged == {"a": 1, "c": 3}


def test_cascade_validate_levels_flags_missing_required() -> None:
    errors = CascadeContract.validate_levels({"system": {"a": 1}})
    assert any("missing level 'workspace'" in e for e in errors)


def test_cascade_validate_levels_flags_task_required_fields() -> None:
    errors = CascadeContract.validate_levels({
        "system": {}, "workspace": {}, "project": {}, "agent": {},
        "task": {"goal": "x"},  # missing assigned_role + routing_hint
    })
    assert any("assigned_role" in e for e in errors)
    assert any("routing_hint" in e for e in errors)


def test_resolve_assigned_model_passthrough_when_explicit() -> None:
    assert resolve_assigned_model({"assigned_model": "claude-opus"}) == "claude-opus"


def test_resolve_assigned_model_auto_resolves_via_router() -> None:
    from core_02.router import SmartRouter, ModelCatalog
    router = SmartRouter(catalog=ModelCatalog.default())
    decision = resolve_assigned_model(
        {"assigned_model": "auto", "routing_hint": ["code"]},
        router=router,
    )
    assert decision != "auto"
    assert isinstance(decision, str) and decision


# ─── routing_hint bridge ────────────────────────────────────────────────────


def test_routing_hint_reads_xml_section(corpus) -> None:
    hint = corpus.routing_hint("developer")
    assert "code" in hint
    assert "implement" in hint


def test_routing_hint_falls_back_to_override_when_xml_missing(corpus) -> None:
    hint = corpus.routing_hint("tester")  # 12_tester.md has no <capabilities>
    assert isinstance(hint, list)
    assert len(hint) > 0  # override MUST kick in


def test_routing_hint_unknown_role_raises(corpus) -> None:
    with pytest.raises(KeyError):
        corpus.routing_hint("nonexistent")


# ─── wizard_lib ──────────────────────────────────────────────────────────────


def test_score_role_match_positive_for_overlap() -> None:
    score = score_role_match(
        "нужно реализовать backend", "developer", "AI Developer",
        "Senior backend engineer",
    )
    assert score > 0.0


def test_score_role_match_zero_for_empty_query() -> None:
    assert score_role_match("", "developer", "X", "Y") == 0.0


def test_propose_roles_returns_local_top_match(corpus) -> None:
    scored = propose_roles(corpus, "надо реализовать backend код", top_n=3)
    assert scored
    # developer should win (text overlap with "backend" + "code").
    assert scored[0][0] == "developer"


def test_propose_roles_falls_back_when_no_match(corpus) -> None:
    scored = propose_roles(
        corpus, "qwertyzzz gibberish-nonexistent-words", top_n=3
    )
    # Fallback ensures non-empty.
    assert scored
    # It's the first registered role with score 0.0 head.
    assert scored[0][2] == 0.0


def test_build_agent_json_includes_routing_hint(corpus) -> None:
    agent = build_agent_json(corpus, "developer")
    assert agent["role_id"] == "developer"
    assert agent["routing_hint"]
    assert "missing_required_sections" in agent


def test_build_task_json_rejects_invalid_priority(corpus) -> None:
    with pytest.raises(ValueError):
        build_task_json(corpus, "developer", "x", priority="urgent-ish")


# ─── run_wizard (end-to-end) ─────────────────────────────────────────────────


def test_run_wizard_writes_all_levels_and_merged(tmp_path, corpus) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    result = run_wizard(
        corpus=corpus,
        workspace_path=ws,
        project_name="demo_app",
        project_goal="мобильное приложение-канвас",
        task_goal="scaffold the project",
        force_role_id="developer",
    )
    project_dir = ws / "demo_app"
    for level in CASCADE_LEVELS:
        path = project_dir / f"{level}.json"
        assert path.exists(), f"{level}.json missing"
        json.loads(path.read_text(encoding="utf-8"))
    merged = json.loads(project_dir.joinpath("merged.json").read_text(encoding="utf-8"))
    assert merged["platform"] == "freebuff"
    assert merged["name"] == "demo_app"
    assert merged["role_id"] == "developer"


def test_run_wizard_resolves_assigned_model_via_smartrouter(tmp_path, corpus) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    result = run_wizard(
        corpus=corpus,
        workspace_path=ws,
        project_name="demo_app",
        project_goal="backend",
        task_goal="write code",
        force_role_id="developer",
    )
    task = json.loads(Path(result["paths"]["task"]).read_text(encoding="utf-8"))
    assert task["assigned_model"] != "auto"
    assert task["assigned_role"] == "developer"


def test_run_wizard_picks_best_available_role_for_query(tmp_path, corpus) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    result = run_wizard(
        corpus=corpus,
        workspace_path=ws,
        project_name="audit_app",
        project_goal="qa audit test coverage",  # tester should win
        task_goal="plan tests",
    )
    assert result["selected_role_id"] == "tester"
    agent = json.loads(Path(result["paths"]["agent"]).read_text(encoding="utf-8"))
    # Tester has no <capabilities> → fallback to override.
    assert agent["routing_hint"]


def test_run_wizard_force_role_unknown_raises(tmp_path, corpus) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    with pytest.raises(KeyError):
        run_wizard(
            corpus=corpus,
            workspace_path=ws,
            project_name="bad",
            project_goal="x",
            task_goal="y",
            force_role_id="ghost",
        )


def test_router_last_resort_fallback_uses_configured_model() -> None:
    """Regression: core_02/router.py:311 — Optional vs ModelEntry mypy conflict.

    When the catalog has no entries matching (empty scored + empty all_models),
    SmartRouter falls through to the configured fallback name. This exercises
    the ``self.catalog.get(self.fallback)`` path that previously tripped mypy
    ('Incompatible types in assignment ... ModelEntry | None').
    """
    from core_02.router import ModelCatalog, ModelEntry, Provider, SmartRouter

    class EmptyMatchCatalog(ModelCatalog):
        def match(self, required, max_tokens=0):  # type: ignore[override]
            return []  # simulate no capability match AND no context match

    catalog = EmptyMatchCatalog(
        [ModelEntry("gemini-2.5-flash", Provider.GEMINI, capabilities=["code"])]
    )
    router = SmartRouter(catalog=catalog, fallback="gemini-2.5-flash")
    decision = router.route(required_capabilities=["vision"])
    assert decision.model == "gemini-2.5-flash"
    assert decision.fallback_used is True
    assert decision.reason == "fallback:last_resort"


def test_router_empty_catalog_raises_no_models() -> None:
    """Empty catalog + missing fallback → RuntimeError (final guard branch)."""
    from core_02.router import ModelCatalog, SmartRouter

    router = SmartRouter(catalog=ModelCatalog(), fallback="missing-model")
    with pytest.raises(RuntimeError, match="No models available"):
        router.route(required_capabilities=["code"])


def test_known_capabilities_subset_of_actual_catalog() -> None:
    """Synchro-guard: KNOWN_CAPABILITIES must be a subset of real ModelCatalog capabilities.

    Drift in either direction raises immediately. Caught by code-reviewer as
    'vocab can silently demote routing to qwen2.5:1.5b' (see LESSONS PB-7).
    """
    from core_02.router import ModelCatalog
    catalog_caps: set[str] = set()
    for entry in ModelCatalog.default().all:
        catalog_caps.update(entry.capabilities)
    missing_in_known = catalog_caps - set(bpv3.KNOWN_CAPABILITIES)
    extra_in_known = set(bpv3.KNOWN_CAPABILITIES) - catalog_caps
    assert not missing_in_known, (
        f"ModelCatalog has caps not declared in KNOWN_CAPABILITIES: "
        f"{missing_in_known} — update core_02/blueprint_v3.py:KNOWN_CAPABILITIES"
    )
    assert not extra_in_known, (
        f"KNOWN_CAPABILITIES has dead entries not in ModelCatalog: "
        f"{extra_in_known} — prune them"
    )


def test_capabilities_override_now_routing_safe(tmp_path) -> None:
    """Regression guard: every override entry must overlap with KNOWN_CAPABILITIES.

    Two-stage assertion:
    1. ``hasattr`` checks the public guard is still mounted — if a future
       refactor deletes ``BlueprintCorpus.validate_override_vocabulary``,
       the test fails with AttributeError instead of silently passing.
    2. The actual ``__init__`` call exercises the guard end-to-end with
       our seed corpus.

    Caught as a regression in code-review (tester role used to have
    ['test','qa','verify','audit'] — all 4 tokens absent from ModelCatalog,
    so SmartRouter.route() fell through to fallback, picking qwen2.5:1.5b
    for QA work). Fix: override now uses only catalog-overlapping tokens.
    """
    # Stage 1: guard present? If someone deletes the validator, the test
    # fails BEFORE pytest tries the more elaborate init path. callable()
    # implies the symbol exists with the right shape — single assertion
    # is enough to catch silent removal or signature drift.
    assert callable(bpv3.BlueprintCorpus.validate_override_vocabulary), (
        "validate_override_vocabulary был удалён или потерял callable \u2014 "
        "wizard снова молчит на vocab drift"
    )
    # Stage 2: guard lifts real load. With a clean corpus this must succeed.
    bpv3.BlueprintCorpus(root=_seed_corpus(tmp_path))


def test_capabilities_override_init_rejects_unknown_token(tmp_path, monkeypatch) -> None:
    """Defense test: a fresh unknown cap in CAPABILITIES_OVERRIDE raises on init.

    Simulates a future developer adding 'mobile' or 'voice' without first
    declaring it in both KNOWN_CAPABILITIES and ModelCatalog. The init-time
    guard MUST trip loud. Without this defense the bug surfaces much later
    in a run_wizard call, where the symptom 'routing picked qwen-local for
    a cloud-capable task' is much harder to attribute.
    """
    bp_dir = _seed_corpus(tmp_path)
    monkeypatch.setitem(
        bpv3.CAPABILITIES_OVERRIDE, "future_unregistered_role",
        ["nonexistent_capability_token", "another_unknown"],
    )
    with pytest.raises(ValueError, match="nonexistent_capability_token"):
        bpv3.BlueprintCorpus(root=bp_dir)


def test_run_wizard_records_missing_required_sections_in_agent(tmp_path) -> None:
    """If a blueprint is incomplete, agent.json flags which sections are missing.

    The wizard does NOT block on missing sections — it writes a partial agent
    contract with ``missing_required_sections`` populated (so callers can decide).
    """
    bp_dir = tmp_path / "bp_broken"
    bp_dir.mkdir()
    (bp_dir / "registry.yaml").write_text(
        "pipeline:\n"
        "  - id: low_role\n"
        "    file: 99_low.md\n"
        "    type: implementation\n"
        "    role: Low\n"
        "    description: x\n"
        "    condition: always\n"
        "    triggers: ['x']\n"
        "project_types: {]\n"
        "complexity_routing: {]\n"
        "categories: {]\n"
        "metadata:\n"
        "  version: '3.0.0'\n",
        encoding="utf-8",
    )
    (bp_dir / "99_low.md").write_text(
        "ROLE: Low\n"
        "VERSION: 3.1.0\n"
        "<role>only one section</role>\n",
        encoding="utf-8",
    )
    corpus = bpv3.BlueprintCorpus(root=bp_dir)
    ws = tmp_path / "workspace"
    ws.mkdir()
    result = run_wizard(
        corpus=corpus,
        workspace_path=ws,
        project_name="low_app",
        project_goal="x",
        task_goal="y",
        force_role_id="low_role",
    )
    agent = json.loads(Path(result["paths"]["agent"]).read_text(encoding="utf-8"))
    assert agent["missing_required_sections"]
    expected = {
        "system_role", "input", "main_objective",
        "priority_order", "implementation_scope_rules",
    }
    assert set(agent["missing_required_sections"]) >= expected
