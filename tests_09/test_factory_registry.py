"""tests_09/test_factory_registry.py — test suite for core_02/factory_registry.py::FactoryRegistry.

Pattern mirrors tests_09/test_forge_passport.py (heavy use of tmp_path for isolation).
Coverage per pomts_11/078_19_factory_registry.md §2 DoD #4:
  - happy-path auto-discovery
  - cross-check factory_id typo (warning surface)
  - duplicate forge_id (first-wins + warning)
  - find_by_capability crosses factories
  - empty / missing factories_dir (fail-safe)
  - validate_all aggregates violations
  - $FREEBUFF_FACTORIES_DIR env override

CAN-16 ADDITIVE: этот файл НЕ модифицирует core_02/* или runtime_05/*.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from core_02.factory_registry import (
    DEFAULT_FACTORIES_DIR,
    FactoryRegistry,
)


# ─── fixture helpers ──────────────────────────────────────────────────────────

def _dump_yaml(path: Path, data: dict[str, Any]) -> Path:
    """Helper: serialize dict → YAML at path."""
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _make_factory_dir(
    root: Path,
    factory_id: str,
    forge_ids: list[str],
    *,
    factory_meta: dict[str, Any] | None = None,
) -> Path:
    """Create factory_dir/<factory_id>/{factory.yaml, <forge>.yaml...]."""
    fdir = root / factory_id
    fdir.mkdir(parents=True, exist_ok=True)
    # factory.yaml metadata (defaults if not provided)
    meta = factory_meta or {
        "factory_id": factory_id,
        "display_name": f"{factory_id.capitalize()} Factory",
        "version": "1.0.0",
        "status": "production",
        "description": f"{factory_id} factory (test fixture).",
    }
    _dump_yaml(fdir / "factory.yaml", meta)
    # forge manifests
    for forge_id in forge_ids:
        data = {
            "forge_id": forge_id,
            "factory_id": factory_id,
            "version": "1.0.0",
            "status": "material",
            "display_name": f"{forge_id.capitalize()} Forge",
            "capabilities": ["explain", "validate"],
            "metadata": {"prompt_path": "prompts_11/_test.md"},
            "mission": f"Test mission for {forge_id}",
            "outputs": [f"{forge_id}_verdict"],
        }
        _dump_yaml(fdir / f"{forge_id}.yaml", data)
    return fdir


# ─── Class 1: auto-discovery ──────────────────────────────────────────────────

class TestFactoryRegistryDiscovery:
    """Auto-discovery of manifests under factories_dir/<factory_id>/{factory.yaml, <forge>.yaml]."""

    def test_discover_single_factory_with_forges(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "research", ["scanner", "synthesizer"])
        r = FactoryRegistry(tmp_path)

        assert r.list_factories() == ["research"]
        forges = r.list_forges("research")
        assert len(forges) == 2
        assert {f.forge_id for f in forges} == {"scanner", "synthesizer"}

    def test_discover_multiple_factories(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "alpha", ["forge_a1"])
        _make_factory_dir(tmp_path, "beta", ["forge_b1", "forge_b2"])
        _make_factory_dir(tmp_path, "gamma", [])
        r = FactoryRegistry(tmp_path)
        assert r.list_factories() == ["alpha", "beta", "gamma"]
        assert len(r.list_forges("beta")) == 2
        assert r.list_forges("gamma") == []

    def test_factory_metadata_loaded(self, tmp_path: Path) -> None:
        _make_factory_dir(
            tmp_path, "lab",
            ["exp_one"],
            factory_meta={
                "factory_id": "lab",
                "display_name": "Lab Factory",
                "version": "2.0.0",
                "status": "production",
                "description": "Экспериментальная фабрика.",
            },
        )
        r = FactoryRegistry(tmp_path)
        meta = r._factory_meta["lab"]
        assert meta["display_name"] == "Lab Factory"
        assert meta["version"] == "2.0.0"
        assert meta["description"] == "Экспериментальная фабрика."

    def test_warnings_empty_on_clean_load(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "clean", ["happy_path"])
        r = FactoryRegistry(tmp_path)
        assert r.warnings() == []
        assert r.validate_all() == []


# ─── Class 2: query API ───────────────────────────────────────────────────────

class TestFactoryRegistryQuery:
    """list_factories / list_forges / get_forge / find_by_capability."""

    def test_list_factories_sorted(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "zeta", [])
        _make_factory_dir(tmp_path, "alpha", [])
        _make_factory_dir(tmp_path, "middle", [])
        r = FactoryRegistry(tmp_path)
        assert r.list_factories() == ["alpha", "middle", "zeta"]

    def test_get_forge_returns_passport(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "research", ["scanner", "synthesizer"])
        r = FactoryRegistry(tmp_path)
        forge = r.get_forge("research", "scanner")
        assert forge is not None
        assert forge.forge_id == "scanner"
        assert forge.factory_id == "research"
        assert "scanner_verdict" in forge.outputs

    def test_get_forge_missing_returns_none(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "research", ["scanner"])
        r = FactoryRegistry(tmp_path)
        assert r.get_forge("research", "scanner") is not None
        assert r.get_forge("research", "missing") is None
        assert r.get_forge("missing_factory", "anything") is None

    def test_find_by_capability_crosses_factories(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "alpha", ["forge_a1", "forge_a2"])
        _make_factory_dir(tmp_path, "beta", ["forge_b1"])
        # All default manifests use ["explain", "validate"]; both should match.
        r = FactoryRegistry(tmp_path)
        explain_matches = r.find_by_capability("explain")
        assert len(explain_matches) == 3
        validate_matches = r.find_by_capability("validate")
        assert len(validate_matches) == 3

    def test_find_by_capability_no_match_returns_empty(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "alpha", ["forge_a1"])
        r = FactoryRegistry(tmp_path)
        assert r.find_by_capability("research") == []  # not in default caps

    def test_all_forges_returns_sorted(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "alpha", ["z_forge", "a_forge"])
        _make_factory_dir(tmp_path, "beta", ["middle"])
        r = FactoryRegistry(tmp_path)
        all_f = r.all_forges()
        assert len(all_f) == 3
        # Sort key: (factory_id, forge_id)
        ids = [(f.factory_id, f.forge_id) for f in all_f]
        assert ids == sorted(ids), f"All-forges must be sorted: {ids}"


# ─── Class 3: fail-safe discovery ──────────────────────────────────────────────

class TestFactoryRegistryFailSafe:
    """Warnings (not exceptions) for missing dir / corrupt manifest / typo."""

    def test_missing_factories_dir_warns(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "no_such_dir"
        r = FactoryRegistry(nonexistent)
        assert r.list_factories() == []
        assert r.list_forges("anything") == []
        warnings = r.warnings()
        assert any("не существует" in w for w in warnings), warnings

    def test_factory_yaml_missing_warns(self, tmp_path: Path) -> None:
        # Create dir + forge, but NO factory.yaml.
        fdir = tmp_path / "no_meta"
        fdir.mkdir()
        _dump_yaml(
            fdir / "forge.yaml",
            {
                "forge_id": "forge",
                "factory_id": "no_meta",
                "version": "1.0.0",
                "status": "material",
                "display_name": "Forge",
                "capabilities": ["explain"],
                "metadata": {},
                "mission": "m",
                "outputs": ["v"],
            },
        )
        r = FactoryRegistry(tmp_path)
        assert r.list_factories() == ["no_meta"]  # discovered but meta missing
        warnings = r.warnings()
        assert any("factory.yaml отсутствует" in w for w in warnings), warnings

    def test_corrupt_manifest_warns_and_skips(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "good", ["good_forge"])
        # Создаём намеренно невалидный manifest в отдельной фабрике 'bad':
        # пустой `mission` + пустой `outputs` → ForgePassport._from_dict упадёт с ValueError,
        # registry перехватит как warning (fail-safe) и НЕ зарегистрирует forge.
        (tmp_path / "bad").mkdir(parents=True, exist_ok=True)
        _dump_yaml(
            tmp_path / "bad" / "bad.yaml",
            {
                "forge_id": "",
                "factory_id": "bad",
                "version": "1.0.0",
                "status": "material",
                "display_name": "X",
                "capabilities": [],
                "metadata": {},
                "mission": "",  # пустой mission → ValueError в _from_dict
                "outputs": [],  # пустой outputs → ValueError в _from_dict
            },
        )
        r = FactoryRegistry(tmp_path)
        # Хорошая фабрика не порождает warnings про invalid manifest.
        assert any("невалидный manifest" in w for w in r.warnings()), r.warnings()
        # Плохая фабрика не регистрирует forge (пропускается).
        assert r.list_forges("bad") == []




    def test_corrupt_yaml_syntax_warns(self, tmp_path: Path) -> None:
        (tmp_path / "broken").mkdir()
        (tmp_path / "broken" / "factory.yaml").write_text("::not-yaml::\n  bad: [unclosed\n", encoding="utf-8")
        (tmp_path / "broken" / "f.yaml").write_text("also: not-valid\n  : [\n", encoding="utf-8")
        r = FactoryRegistry(tmp_path)
        warnings = r.warnings()
        # Both metadata and forge manifest corruptions emit warnings
        assert sum(1 for w in warnings if "повреждён" in w or "невалидный" in w) >= 1, warnings

    def test_directory_name_mismatch_with_factory_id_warns(self, tmp_path: Path) -> None:
        _make_factory_dir(
            tmp_path, "actual_dir",
            ["forge1"],
            factory_meta={
                "factory_id": "wrong_id",  # ← mismatch with directory name
                "display_name": "X",
                "version": "1.0.0",
                "status": "production",
            },
        )
        r = FactoryRegistry(tmp_path)
        warnings = r.warnings()
        assert any("Cross-check" in w and "actual_dir" in w and "wrong_id" in w for w in warnings), warnings


# ─── Class 4: duplicate forge_id handling ─────────────────────────────────────

class TestFactoryRegistryDuplicate:
    """Duplicate forge_id in same factory → first-wins + warning."""

    def test_duplicate_first_wins(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "research", ["scanner"])
        # Drop a second manifest with same forge_id into same factory dir.
        # We'll use a non-direct filename (allowed extension but not .yaml
        # recognised by forges filter would skip; we need forge_id=='scanner'.
        import yaml
        dupe_payload = {
            "forge_id": "scanner",
            "factory_id": "research",
            "version": "9.9.9",
            "status": "production",
            "display_name": "Scanner DUPE",
            "capabilities": ["code"],
            "metadata": {},
            "mission": "Dupe",
            "outputs": ["dupe_out"],
        }
        (tmp_path / "research").mkdir(exist_ok=True)
        (tmp_path / "research" / "scanner_2.yaml").write_text(
            yaml.safe_dump(dupe_payload, allow_unicode=True), encoding="utf-8"
        )
        r = FactoryRegistry(tmp_path)
        forge = r.get_forge("research", "scanner")
        assert forge is not None
        # First-wins meant original scanner (version not 9.9.9).
        assert forge.display_name == "Scanner Forge"
        # Warning emitted about dupe.
        warnings = r.warnings()
        assert any("дубликат forge_id" in w for w in warnings), warnings


# ─── Class 5: validate_all aggregation ────────────────────────────────────────

class TestFactoryRegistryValidateAll:
    """validate_all aggregates per-passport validate() invocations."""

    def test_validate_all_returns_aggregated_violations(self, tmp_path: Path) -> None:
        # Manually build factories with one valid, one invalid passport.
        valid_dir = tmp_path / "valid_factory"
        valid_dir.mkdir()
        _dump_yaml(
            valid_dir / "factory.yaml",
            {
                "factory_id": "valid_factory",
                "display_name": "VF", "version": "1.0.0", "status": "production",
            },
        )
        _dump_yaml(
            valid_dir / "good.yaml",
            {
                "forge_id": "good",
                "factory_id": "valid_factory",
                "version": "1.0.0", "status": "material", "display_name": "G",
                "capabilities": ["explain"], "metadata": {}, "mission": "m",
                "outputs": ["v"],
            },
        )
        invalid_dir = tmp_path / "invalid_factory"
        invalid_dir.mkdir()
        _dump_yaml(
            invalid_dir / "factory.yaml",
            {
                "factory_id": "invalid_factory",
                "display_name": "IF", "version": "1.0.0", "status": "production",
            },
        )
        _dump_yaml(
            invalid_dir / "bad.yaml",
            {
                "forge_id": "bad",
                "factory_id": "invalid_factory",
                "version": "1.0.0", "status": "material", "display_name": "B",
                "capabilities": ["unknown_token"],  # ← vocab violation
                "metadata": {}, "mission": "m",
                "outputs": ["v"],
            },
        )

        r = FactoryRegistry(tmp_path)
        violations = r.validate_all()
        # At least one violation from invalid_factory/bad (vocab drift).
        assert any("invalid_factory/bad" in v and "unknown_token" in v or "unknown tokens" in v for v in violations), (
            f"Expected vocab violation; got: {violations}"
        )
        assert not any("valid_factory/good" in v for v in violations), (
            f"Valid passport should not appear in violations; got: {violations}"
        )


# ─── Class 6: env var + classmethod + reload ─────────────────────────────────

class TestFactoryRegistryEnvAndReload:
    """$FREEBUFF_FACTORIES_DIR + reload() + from_env() classmethod."""

    def test_from_env_no_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("FREEBUFF_FACTORIES_DIR", raising=False)
        _make_factory_dir(tmp_path, "no_env_factory", ["forge"])
        monkeypatch.setenv("FREEBUFF_FACTORIES_DIR", str(tmp_path))
        r = FactoryRegistry.from_env()
        assert "no_env_factory" in r.list_factories()

    def test_from_env_with_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        env_dir = tmp_path / "env_factory"
        _make_factory_dir(env_dir, "env_factory", ["forge"])
        monkeypatch.setenv("FREEBUFF_FACTORIES_DIR", str(env_dir))
        r = FactoryRegistry.from_env()
        assert "env_factory" in r.list_factories()

    def test_reload_rediscovers(self, tmp_path: Path) -> None:
        _make_factory_dir(tmp_path, "before_reload", ["forge_v1"])
        r = FactoryRegistry(tmp_path)
        assert "before_reload" in r.list_factories()
        # Add new factory AFTER construction.
        _make_factory_dir(tmp_path, "after_reload", ["forge_v2"])
        # Pre-reload: new factory not visible.
        assert "after_reload" not in r.list_factories()
        # After reload(): visible.
        r.reload()
        assert "after_reload" in r.list_factories()
        forges = r.list_forges("after_reload")
        assert len(forges) == 1
        assert forges[0].forge_id == "forge_v2"


# ─── Class 7: C-2 FactoryPassport + capability-каталог + селекция ────────────

class TestFactoryRegistryCapabilityCatalog:
    """C-2 (roadmap 09_FUTURE_GAPS): get_factory / factory_capabilities /
    find_factories_by_capability / select_forge / capability_catalog."""

    @staticmethod
    def _make_cap_factory(
        root: Path,
        factory_id: str,
        status: str,
        factory_caps: list[str],
        forge_ids: list[str],
        forge_caps: list[str],
    ) -> None:
        fdir = root / factory_id
        fdir.mkdir(parents=True, exist_ok=True)
        _dump_yaml(fdir / "factory.yaml", {
            "factory_id": factory_id,
            "display_name": f"{factory_id} Factory",
            "version": "1.0.0",
            "status": status,
            "description": f"{factory_id} factory.",
            "capabilities": factory_caps,
        })
        for fid in forge_ids:
            _dump_yaml(fdir / f"{fid}.yaml", {
                "forge_id": fid,
                "factory_id": factory_id,
                "version": "1.0.0",
                "status": "material",
                "display_name": f"{fid} Forge",
                "capabilities": forge_caps,
                "metadata": {},
                "mission": f"mission {fid}",
                "outputs": [f"{fid}_verdict"],
            })

    def test_get_factory_returns_passport(self, tmp_path: Path) -> None:
        self._make_cap_factory(
            tmp_path, "arch", "production",
            ["architecture", "review"], ["review"], ["review", "explain"],
        )
        r = FactoryRegistry(tmp_path)
        fp = r.get_factory("arch")
        assert fp is not None
        assert fp.factory_id == "arch"
        assert fp.status == "production"
        assert "architecture" in fp.capabilities
        assert r.get_factory("missing") is None

    def test_factory_capabilities_union(self, tmp_path: Path) -> None:
        # factory.yaml capabilities + forge passports capabilities → union.
        self._make_cap_factory(
            tmp_path, "arch", "production",
            ["architecture"], ["review", "governance"], ["explain", "validate"],
        )
        r = FactoryRegistry(tmp_path)
        caps = r.factory_capabilities("arch")
        assert "architecture" in caps   # from factory.yaml
        assert "explain" in caps         # from forge passports
        assert "validate" in caps        # from forge passports
        assert caps == tuple(sorted(caps))
        assert r.factory_capabilities("missing") == ()

    def test_find_factories_by_capability(self, tmp_path: Path) -> None:
        self._make_cap_factory(tmp_path, "alpha", "production", ["architecture"], [], [])
        self._make_cap_factory(tmp_path, "beta", "production", ["research"], [], [])
        r = FactoryRegistry(tmp_path)
        matches = r.find_factories_by_capability("architecture")
        assert [fp.factory_id for fp in matches] == ["alpha"]
        assert r.find_factories_by_capability("nope") == []

    def test_find_factories_by_capability_uses_union(self, tmp_path: Path) -> None:
        # factory.yaml объявляет только "architecture"; forge объявляет "validate".
        # find_factories_by_capability("validate") должен найти фабрику через union.
        self._make_cap_factory(
            tmp_path, "arch", "production",
            ["architecture"], ["review"], ["validate"],
        )
        r = FactoryRegistry(tmp_path)
        matches = r.find_factories_by_capability("validate")
        assert [fp.factory_id for fp in matches] == ["arch"]

    def test_select_forge_status_priority(self, tmp_path: Path) -> None:
        # production factory beats design factory for same capability.
        self._make_cap_factory(tmp_path, "prod_factory", "production", ["review"], ["review"], ["review"])
        self._make_cap_factory(tmp_path, "design_factory", "design", ["review"], ["review"], ["review"])
        r = FactoryRegistry(tmp_path)
        pair = r.select_forge("review")
        assert pair is not None
        fp, fg = pair
        assert fp.factory_id == "prod_factory"
        assert fg.forge_id == "review"

    def test_select_forge_prefer_status_filter(self, tmp_path: Path) -> None:
        # design-only factory excluded when prefer_status='material'.
        self._make_cap_factory(tmp_path, "design_factory", "design", ["review"], ["review"], ["review"])
        r = FactoryRegistry(tmp_path)
        assert r.select_forge("review", prefer_status="material") is None
        assert r.select_forge("review", prefer_status="design") is not None

    def test_select_forge_no_match_returns_none(self, tmp_path: Path) -> None:
        self._make_cap_factory(tmp_path, "arch", "production", ["architecture"], ["review"], ["review"])
        r = FactoryRegistry(tmp_path)
        assert r.select_forge("research") is None

    def test_capability_catalog(self, tmp_path: Path) -> None:
        self._make_cap_factory(tmp_path, "alpha", "production", ["architecture", "review"], [], [])
        self._make_cap_factory(tmp_path, "beta", "production", ["review"], [], [])
        r = FactoryRegistry(tmp_path)
        catalog = r.capability_catalog()
        assert catalog["architecture"] == ["alpha"]
        assert catalog["review"] == ["alpha", "beta"]
        assert catalog == dict(sorted(catalog.items()))
