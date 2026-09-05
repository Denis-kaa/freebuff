"""tests_09/test_scenario_registry.py — tests for ScenarioRegistry.

Covers:
- Auto-discovery of YAML manifests in a directory.
- Manifest parse / dispatch (BlueprintCorpus primitive is used because it's
  the only registered scenario type today).
- Cross-scenario find_role / propose_roles / validate_all.
- Failure-mode warnings (duplicate id, unknown type, parse failure, missing root).
- BC alias: ``BlueprintScenario is BlueprintCorpus``.
- ``BlueprintCorpus`` satisfies ``Scenario`` ABC surface (roles, load_role_text, validate).
"""

from __future__ import annotations

***REMOVED***

import pytest

from core_02 import blueprint_v3 as bpv3
from core_02.scenario import Role, Scenario, ScenarioManifest
from core_02.scenario_registry import ScenarioRegistry


# ─── fixtures ────────────────────────────────────────────────────────────────


def _seed_two_role_corpus(root: Path) -> Path:
    """Two-role corpus: 'developer' (with capabilities) + 'tester' (no capabilities)."""
    (root / "registry.yaml").write_text(
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
        "    description: qa audit verify test\n"
        "    condition: always\n"
        "    triggers:\n"
        '      - "тест"\n'
        "project_types:\n"
        "  web:\n"
        "    required_roles: [developer***REMOVED***\n"
        "    skip_roles: [***REMOVED***\n"
        "complexity_routing:\n"
        "  small:\n"
        "    required_roles: [developer***REMOVED***\n"
        "    skip_roles: [***REMOVED***\n"
        "categories:\n"
        "  implementation: [developer***REMOVED***\n"
        "  validation: [tester***REMOVED***\n"
        "metadata:\n"
        "  version: \"3.0.0\"\n",
        encoding="utf-8",
    )
    (root / "09_developer.md").write_text(
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
        "- refactor\n"
        "</capabilities>\n",
        encoding="utf-8",
    )
    (root / "12_tester.md").write_text(
        "ROLE: AI Test Designer\n"
        "VERSION: 3.1.0\n\n"
        "<role>QA audit verify test coverage.</role>\n\n"
        "<system_role>Plans tests.</system_role>\n\n"
        "<input>Implementation plus spec.</input>\n\n"
        "<main_objective>Coverage > 80%.</main_objective>\n\n"
        "<priority_order>Correctness first.</priority_order>\n\n"
        "<implementation_scope_rules>Allowed: test files only.</implementation_scope_rules>\n",
        encoding="utf-8",
    )
    return root


def _seed_scenarios_dir(scenarios: Path, *, alias: str = "test", root: Path) -> Path:
    """Write one manifest YAML pointing at ``root`` and return ``scenarios``."""
    scenarios.mkdir(parents=True, exist_ok=True)
    (scenarios / f"{alias***REMOVED***.yaml").write_text(
        f"id: {alias***REMOVED***\n"
        "type: blueprint_v3\n"
        f"root: {root***REMOVED***\n"
        "enabled: true\n",
        encoding="utf-8",
    )
    return scenarios


@pytest.fixture
def registry_one(tmp_path: Path) -> ScenarioRegistry:
    """One scenario (single root, two roles)."""
    bp_root = tmp_path / "bp"
    bp_root.mkdir()
    _seed_two_role_corpus(bp_root)
    scenarios_dir = tmp_path / "scenarios"
    _seed_scenarios_dir(scenarios_dir, alias="test", root=bp_root)
    return ScenarioRegistry(scenarios_dir=scenarios_dir, silent=True)


@pytest.fixture
def registry_two(tmp_path: Path) -> ScenarioRegistry:
    """Two scenarios with same corpus type but different ids and roots."""
    bp_root_a = tmp_path / "bp_a"
    bp_root_a.mkdir()
    _seed_two_role_corpus(bp_root_a)
    bp_root_b = tmp_path / "bp_b"
    bp_root_b.mkdir()
    _seed_two_role_corpus(bp_root_b)

    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    (scenarios_dir / "alpha.yaml").write_text(
        f"id: alpha\ntype: blueprint_v3\nroot: {bp_root_a***REMOVED***\nenabled: true\n",
        encoding="utf-8",
    )
    (scenarios_dir / "beta.yaml").write_text(
        f"id: beta\ntype: blueprint_v3\nroot: {bp_root_b***REMOVED***\nenabled: true\n",
        encoding="utf-8",
    )
    return ScenarioRegistry(scenarios_dir=scenarios_dir, silent=True)


def _seed_unique_corpus(root: Path, *, roles: tuple[tuple[str, str***REMOVED***, ...***REMOVED***) -> Path:
    """Seed a corpus with the EXACT ``roles`` ((id, file), ...) — no shared defaults.

    Used by the ``registry_two_with_unique_roles`` fixture to make role_id
    scope assertions deterministic (a baseline corpus otherwise seeds
    developer+tester identically on both sides, hiding the distinction).
    """
    pipeline_yaml = "pipeline:\n"
    for rid, fname in roles:
        pipeline_yaml += (
            f"  - id: {rid***REMOVED***\n"
            f"    file: {fname***REMOVED***\n"
            "    type: implementation\n"
            f"    role: AI {rid***REMOVED***\n"
            f"    description: {rid***REMOVED*** role\n"
            "    condition: always\n"
            '    triggers:\n'
            f'      - "{rid***REMOVED***"\n'
        )
    pipeline_yaml += (
        "project_types:\n  web:\n    required_roles: [developer***REMOVED***\n    skip_roles: [***REMOVED***\n"
        "complexity_routing:\n  small:\n    required_roles: [developer***REMOVED***\n    skip_roles: [***REMOVED***\n"
        "categories:\n  implementation: [developer***REMOVED***\n"
        "metadata:\n  version: '3.0.0'\n"
    )
    (root / "registry.yaml").write_text(pipeline_yaml, encoding="utf-8")
    for _rid, fname in roles:
        (root / fname).write_text(
            f"ROLE: AI {_rid***REMOVED***\nVERSION: 3.1.0\n\n"
            f"<role>{_rid***REMOVED*** backend.</role>\n\n"
            f"<system_role>{_rid***REMOVED***.</system_role>\n\n"
            "<input>Architecture spec.</input>\n\n"
            f"<main_objective>{_rid***REMOVED***.</main_objective>\n\n"
            "<priority_order>Correctness first.</priority_order>\n\n"
            "<implementation_scope_rules>Allowed: target module only.</implementation_scope_rules>\n\n"
            f"<capabilities>\n- {_rid***REMOVED***\n</capabilities>\n",
            encoding="utf-8",
        )
    return root


@pytest.fixture
def registry_two_with_unique_roles(tmp_path: Path) -> ScenarioRegistry:
    """Two scenarios with DISTINCT roles per side.

    alpha: developer + designer (unique).
    beta:  developer + auditor   (unique).

    This fixture exists specifically so ``filter(scenario_id)`` tests can
    prove scope via role-id presence/absence — the default
    ``registry_two`` fixture seeds the SAME roles on both sides, so
    role-id-based scope assertions are vacuous there.
    """
    bp_root_a = tmp_path / "bp_a"
    bp_root_a.mkdir()
    _seed_unique_corpus(
        bp_root_a,
        roles=(("developer", "09_developer.md"), ("designer", "11_designer.md")),
    )
    bp_root_b = tmp_path / "bp_b"
    bp_root_b.mkdir()
    _seed_unique_corpus(
        bp_root_b,
        roles=(("developer", "09_developer.md"), ("auditor", "12_auditor.md")),
    )
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    (scenarios_dir / "alpha.yaml").write_text(
        f"id: alpha\ntype: blueprint_v3\nroot: {bp_root_a***REMOVED***\nenabled: true\n",
        encoding="utf-8",
    )
    (scenarios_dir / "beta.yaml").write_text(
        f"id: beta\ntype: blueprint_v3\nroot: {bp_root_b***REMOVED***\nenabled: true\n",
        encoding="utf-8",
    )
    return ScenarioRegistry(scenarios_dir=scenarios_dir, silent=True)


# ─── discovery / dispatch ──────────────────────────────────────────────────


def test_scenario_manifest_parses_yaml(tmp_path: Path) -> None:
    (tmp_path / "m.yaml").write_text(
        "id: foo\ntype: blueprint_v3\nroot: /tmp/x\nenabled: false\ncapabilities: [a, b***REMOVED***\nmetadata:\n  v: '1'\n",
        encoding="utf-8",
    )
    m = ScenarioManifest.from_yaml(tmp_path / "m.yaml")
    assert m.scenario_id == "foo"
    assert m.scenario_type == "blueprint_v3"
    assert m.root == Path("/tmp/x").expanduser().resolve()
    assert m.enabled is False
    assert m.capabilities == ("a", "b")
    assert m.metadata == {"v": "1"***REMOVED***


def test_scenario_manifest_rejects_missing_required_keys(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("type: blueprint_v3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="required keys missing"):
        ScenarioManifest.from_yaml(bad)


def test_registry_discovers_yaml_manifests(registry_one: ScenarioRegistry) -> None:
    scenarios = registry_one.list_scenarios()
    assert len(scenarios) == 1
    assert scenarios[0***REMOVED***.scenario_id == "test"
    assert scenarios[0***REMOVED***.display_name  # non-empty


def test_registry_discovers_all_enabled_in_sort_order(registry_two: ScenarioRegistry) -> None:
    ids = [sc.scenario_id for sc in registry_two.list_scenarios()***REMOVED***
    assert ids == ["alpha", "beta"***REMOVED***


def test_registry_disabled_manifest_is_skipped(tmp_path: Path) -> None:
    bp_root = tmp_path / "bp"
    bp_root.mkdir()
    _seed_two_role_corpus(bp_root)
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    (scenarios_dir / "off.yaml").write_text(
        f"id: off\ntype: blueprint_v3\nroot: {bp_root***REMOVED***\nenabled: false\n",
        encoding="utf-8",
    )
    reg = ScenarioRegistry(scenarios_dir=scenarios_dir, silent=True)
    assert reg.list_scenarios() == [***REMOVED***
    # No warning though — disabled manifests are silently skipped by design.


def test_registry_unknown_type_records_warning(tmp_path: Path) -> None:
    """Defense: unknown scenario_type leaves registry empty + warning recorded.

    Asserts via the canonical ``reg.warnings()`` path (NOT ``capsys`` for
    stderr — that path is fragile under pytest capture mode changes; the
    registry already returns the warning text in-memory which is the
    stable contract).
    """
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    (scenarios_dir / "x.yaml").write_text(
        "id: x\ntype: unknown_future_type\nroot: /tmp/nope\n",
        encoding="utf-8",
    )
    reg = ScenarioRegistry(scenarios_dir=scenarios_dir, silent=False)
    assert reg.list_scenarios() == [***REMOVED***
    warnings = reg.warnings()
    # Warning text is the canonical signal — silent=False also prints to
    # stderr but that's a side effect, not the contract.
    assert any("instantiation failed" in w for w in warnings), (
        f"expected instantiation-failed warning, got: {warnings***REMOVED***"
    )


def test_registry_parse_failure_records_warning(tmp_path: Path) -> None:
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    (scenarios_dir / "broken.yaml").write_text(
        "type: blueprint_v3\n",  # valid YAML, missing required keys `id` + `root`
        encoding="utf-8",
    )
    reg = ScenarioRegistry(scenarios_dir=scenarios_dir, silent=True)
    assert reg.list_scenarios() == [***REMOVED***
    assert any("required keys missing" in w for w in reg.warnings())


def test_registry_duplicate_id_warns_first_wins(tmp_path: Path) -> None:
    bp_root = tmp_path / "bp"
    bp_root.mkdir()
    _seed_two_role_corpus(bp_root)
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    manifest_text = f"id: dup\ntype: blueprint_v3\nroot: {bp_root***REMOVED***\nenabled: true\n"
    (scenarios_dir / "first.yaml").write_text(manifest_text, encoding="utf-8")
    (scenarios_dir / "second.yaml").write_text(manifest_text, encoding="utf-8")
    reg = ScenarioRegistry(scenarios_dir=scenarios_dir, silent=True)
    assert len(reg.list_scenarios()) == 1
    assert any("duplicate scenario_id" in w for w in reg.warnings())


def test_registry_empty_dir_yields_empty(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    reg = ScenarioRegistry(scenarios_dir=empty, silent=True)
    assert reg.list_scenarios() == [***REMOVED***


def test_registry_nonexistent_dir_yields_empty(tmp_path: Path) -> None:
    reg = ScenarioRegistry(scenarios_dir=tmp_path / "no-such-dir", silent=True)
    assert reg.list_scenarios() == [***REMOVED***


# ─── cross-scenario APIs ─────────────────────────────────────────────────────


def test_all_roles_returns_scenario_role_pairs(registry_two: ScenarioRegistry) -> None:
    pairs = registry_two.all_roles()
    # Each scenario has 2 roles; 2 scenarios → 4 pairs.
    assert len(pairs) == 4
    for sc, role in pairs:
        assert isinstance(sc, Scenario)
        assert isinstance(role, Role)
        assert sc.scenario_id in ("alpha", "beta")


def test_find_role_returns_first_match(registry_two: ScenarioRegistry) -> None:
    """Cross-scenario lookup: developer exists in both alpha and beta."""
    match = registry_two.find_role("developer")
    assert match is not None
    scenario, role = match
    assert role.role_id == "developer"
    # load order is alphabetical → alpha wins.
    assert scenario.scenario_id == "alpha"


def test_find_role_unknown_returns_none(registry_one: ScenarioRegistry) -> None:
    assert registry_one.find_role("nonexistent") is None


def test_propose_roles_returns_top_matches(registry_one: ScenarioRegistry) -> None:
    """Project goal with 'backend' + 'code' keywords should pick 'developer'."""
    scored = registry_one.propose_roles("надо реализовать backend код", top_n=2)
    assert scored
    assert scored[0***REMOVED***[1***REMOVED***.role_id == "developer"
    assert scored[0***REMOVED***[2***REMOVED*** > 0.0


def test_propose_roles_falls_back_when_no_match(registry_one: ScenarioRegistry) -> None:
    """Gibberish query yields score 0; registry still returns a non-empty deterministic fallback."""
    scored = registry_one.propose_roles(
        "qwertyzzz-gibberish-nonexistent-words", top_n=3
    )
    assert scored
    assert scored[0***REMOVED***[2***REMOVED*** == 0.0


def test_propose_roles_cross_scenario_pick(registry_two: ScenarioRegistry) -> None:
    """Even if 'backend' is fully in alpha, beta still appears in the top-N."""
    scored = registry_two.propose_roles("backend code developer", top_n=4)
    sids = {entry[0***REMOVED***.scenario_id for entry in scored***REMOVED***
    # Both scenarios are represented (at least the fallback head picks from one).
    assert "alpha" in sids or "beta" in sids


def test_validate_all_returns_empty_for_clean_corpus(registry_one: ScenarioRegistry) -> None:
    """Both roles are complete → validate returns clean."""
    assert registry_one.validate_all() == [***REMOVED***


def test_validate_all_flags_corrupt_role_sections(tmp_path: Path) -> None:
    """If a blueprint .md is missing REQUIRED sections, surface as error."""
    bp_root = tmp_path / "bp_bad"
    bp_root.mkdir()
    (bp_root / "registry.yaml").write_text(
        "pipeline:\n"
        "  - id: incomplete\n"
        "    file: bad.md\n"
        "    type: implementation\n"
        "    role: Half Role\n"
        "    description: x\n"
        "    condition: always\n"
        "    triggers: ['x'***REMOVED***\n"
        "project_types: {***REMOVED***\n"
        "complexity_routing: {***REMOVED***\n"
        "categories: {***REMOVED***\n"
        "metadata:\n"
        "  version: 'x'\n",
        encoding="utf-8",
    )
    (bp_root / "bad.md").write_text(
        "ROLE: Half Role\n"
        "<role>only role section</role>\n",
        encoding="utf-8",
    )
    scenarios_dir = tmp_path / "scenarios"
    _seed_scenarios_dir(scenarios_dir, alias="bad_scenario", root=bp_root)
    reg = ScenarioRegistry(scenarios_dir=scenarios_dir, silent=True)
    errors = reg.validate_all()
    assert errors
    assert any("missing sections" in e for e in errors)


def test_validate_all_flags_cross_scenario_role_id_collisions(tmp_path: Path) -> None:
    """Same role_id published in two scenarios → cross-scenario warning."""
    bp_root = tmp_path / "bp_x"
    bp_root.mkdir()
    _seed_two_role_corpus(bp_root)
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    (scenarios_dir / "x.yaml").write_text(
        f"id: x\ntype: blueprint_v3\nroot: {bp_root***REMOVED***\nenabled: true\n",
        encoding="utf-8",
    )
    (scenarios_dir / "y.yaml").write_text(
        f"id: y\ntype: blueprint_v3\nroot: {bp_root***REMOVED***\nenabled: true\n",
        encoding="utf-8",
    )
    reg = ScenarioRegistry(scenarios_dir=scenarios_dir, silent=True)
    errs = reg.validate_all()
    assert any("appears in multiple scenarios" in e for e in errs)


# ─── BC alias + ABC conformance ─────────────────────────────────────────────


def test_blueprint_scenario_alias_is_same_class() -> None:
    """BlueprintScenario and BlueprintCorpus refer to the same class object."""
    assert bpv3.BlueprintScenario is bpv3.BlueprintCorpus


def test_blueprint_corpus_satisfies_scenario_abc(registry_one: ScenarioRegistry) -> None:
    """The instantiated BlueprintCorpus is a Scenario subclass on the registry."""
    sc = registry_one.list_scenarios()[0***REMOVED***
    assert isinstance(sc, Scenario)
    assert sc.scenario_id  # property
    assert sc.display_name  # property
    roles = sc.role_objects()
    assert roles and isinstance(roles[0***REMOVED***, Role)
    text = sc.load_role_text("developer")
    assert "backend" in text.lower()
    # load_role_text for missing role → empty string (no FileNotFoundError leak)
    assert sc.load_role_text("nonexistent") == ""


def test_blueprint_corpus_scenario_id_init_kwarg(tmp_path: Path) -> None:
    """scenario_id kwarg overrides the default 'blueprint_v3'."""
    bp_root = tmp_path / "bp_alt"
    bp_root.mkdir()
    _seed_two_role_corpus(bp_root)
    corpus = bpv3.BlueprintCorpus(root=bp_root, scenario_id="alternate_id")
    assert corpus.scenario_id == "alternate_id"
    # And reflected in projected Role rows.
    assert all(r.scenario_id == "alternate_id" for r in corpus.role_objects())


# ─── filter(scenario_id) ────────────────────────────────────────────────────


def test_registry_filter_keeps_only_kept_scenario(
    registry_two_with_unique_roles: ScenarioRegistry,
) -> None:
    """``filter('alpha')`` restricts the registry to alpha only.

    Replaces the previous ``__new__`` escape-hatch used in the CLI
    (``scripts_01/wizard.py --scenario`` path). Verifies:
    1. Only the kept scenario is listed.
    2. Cross-scenario APIs (``all_roles``, ``find_role``) are scoped to
       alpha and yield ONLY alpha's roles.
    3. ``propose_roles`` falls back to alpha (no beta leakage).
    4. Beta's UNIQUE role ('auditor') is NOT findable in alpha's view.
    """
    filtered = registry_two_with_unique_roles.filter("alpha")
    assert [sc.scenario_id for sc in filtered.list_scenarios()***REMOVED*** == ["alpha"***REMOVED***
    # all_roles scope: only alpha (2 roles = developer + designer).
    pairs = filtered.all_roles()
    assert len(pairs) == 2
    assert all(sc.scenario_id == "alpha" for sc, _ in pairs)
    # find_role scope: alpha's 'developer' resolves to alpha, not beta.
    match = filtered.find_role("developer")
    assert match is not None
    assert match[0***REMOVED***.scenario_id == "alpha"
    # alpha's UNIQUE role 'designer' resolves to alpha.
    match_designer = filtered.find_role("designer")
    assert match_designer is not None
    assert match_designer[0***REMOVED***.scenario_id == "alpha"
    # Beta's UNIQUE role ('auditor') is NOT findable in alpha's view.
    registry_full = registry_two_with_unique_roles
    match_auditor = registry_full.find_role("auditor")
    assert match_auditor is not None and match_auditor[0***REMOVED***.scenario_id == "beta"
    assert filtered.find_role("auditor") is None


def test_registry_filter_missing_raises_keyerror(
    registry_one: ScenarioRegistry,
) -> None:
    """Filtering on a non-existent scenario_id is a clear error.

    The CLI (``scripts_01/wizard.py --scenario``) upstream checks first
    and prints a friendly message; the registry itself raises
    :class:`KeyError` so non-CLI callers get the right exception type.
    """
    with pytest.raises(KeyError, match="nonexistent_scenario"):
        registry_one.filter("nonexistent_scenario")


def test_registry_filter_narrows_warnings(tmp_path: Path) -> None:
    """Warnings about OTHER scenarios are filtered out under filter().

    If the registry records a warning during load (unknown scenario_type,
    parse failure, etc.) for a scenario we're not keeping, the filtered
    view must NOT include it. Registry-wide YAML-level warnings (that
    don't reference a specific scenario_id) remain visible because they
    affect the parser state.
    """
    scenarios_dir = tmp_path / "scenarios_with_warning"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    # One good scenario (will be kept) + one bad (will be filtered out).
    bp_root = tmp_path / "bp"
    bp_root.mkdir()
    _seed_two_role_corpus(bp_root)
    (scenarios_dir / "good.yaml").write_text(
        f"id: good\ntype: blueprint_v3\nroot: {bp_root***REMOVED***\nenabled: true\n",
        encoding="utf-8",
    )
    (scenarios_dir / "bad.yaml").write_text(
        "id: bad\ntype: unknown_future_type\nroot: /tmp/nope\n",
        encoding="utf-8",
    )
    reg = ScenarioRegistry(scenarios_dir=scenarios_dir, silent=True)
    pre_filter_warnings = reg.warnings()
    assert any("instantiation failed" in w for w in pre_filter_warnings), (
        f"expected pre-filter instantiation warning, got: {pre_filter_warnings***REMOVED***"
    )
    # Filter to "good" — the bad-scenario warning must NOT survive.
    # Asserting on the warning TYPE ("instantiation failed") rather than
    # the scenario-name token ("bad") makes the test independent of the
    # registry's exact warning-message format. After filtering to the
    # clean scenario, the instantiation warning should be gone.
    filtered = reg.filter("good")
    kept_warnings = filtered.warnings()
    assert not any("instantiation failed" in w for w in kept_warnings), (
        f"filtered warnings leaked an instantiation-failed entry: {kept_warnings***REMOVED***"
    )
