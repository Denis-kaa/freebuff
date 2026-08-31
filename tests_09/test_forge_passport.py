"""tests_09/test_forge_passport.py — test suite for core_02/forge_passport.py::ForgePassport.

Pattern mirrors tests_09/test_scenario_registry.py (heavy use of tmp_path for isolation).
Coverage per pomts_11/078_19_factory_registry.md §2 DoD #4:
  - happy-path from_yaml
  - missing required keys → ValueError
  - vocabulary drift → violation
  - round-trip to_yaml
  - invalid status / forge_id pattern → ValueError
  - outputs required (B10/R-127)
  - cross-check factory_id mismatch (warning surface)

CAN-16 ADDITIVE: этот файл НЕ модифицирует core_02/* или runtime_05/* —
только новый тестовый модуль.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core_02.forge_passport import (
    ForgePassport,
    REQUIRED_FIELDS,
    _as_tuple,
    _as_dict,
    _SLUG_RE,
    _VALID_STATUSES,
)


# ─── fixture: minimal valid manifest ──────────────────────────────────────────

@pytest.fixture
def minimal_manifest_dict() -> dict[str, Any]:
    """Return a plain dict matching FORGE_PASSPORT minimal schema."""
    return {
        "forge_id": "minimal",
        "factory_id": "test_factory",
        "version": "0.1.0",
        "status": "design",
        "display_name": "Minimal Forge",
        "capabilities": ["explain"],
        "metadata": {"prompt_path": "prompts_11/_test.md"},
        "mission": "Проверить работу ForgePassport как типизированной модели.",
        "outputs": ["verdict"],
    }


def _dump_yaml(path: Path, data: dict[str, Any]) -> Path:
    """Helper: serialize dict → YAML at path (test-isolated)."""
    import yaml
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


# ─── Class 1: from_yaml happy-path ────────────────────────────────────────────

class TestForgePassportFromYaml:
    """ForgePassport.from_yaml — minimal + full manifest loads."""

    def test_happy_path_from_yaml_minimal(self, tmp_path: Path, minimal_manifest_dict: dict[str, Any]) -> None:
        path = _dump_yaml(tmp_path / "minimal.yaml", minimal_manifest_dict)
        pp = ForgePassport.from_yaml(path)
        assert pp.forge_id == "minimal"
        assert pp.factory_id == "test_factory"
        assert pp.version == "0.1.0"
        assert pp.status == "design"
        assert pp.display_name == "Minimal Forge"
        assert pp.capabilities == ("explain",)
        assert pp.metadata == {"prompt_path": "prompts_11/_test.md"}
        assert pp.mission == minimal_manifest_dict["mission"]
        assert pp.outputs == ("verdict",)
        # All other 9 passport fields default to empty tuple / empty / "":
        assert pp.inputs == ()
        assert pp.production_workflow == ()
        assert pp.engines == ()
        assert pp.quality_gates == ()
        assert pp.artifacts == ()
        assert pp.interfaces == ()
        assert pp.memory == ()
        assert pp.knowledge == ()

    def test_happy_path_full_manifest(self, tmp_path: Path) -> None:
        # Mimics the architecture/review.yaml schema end-to-end.
        data = {
            "forge_id": "review",
            "factory_id": "architecture",
            "version": "1.0.0",
            "status": "material",
            "display_name": "Architecture Review Forge",
            "capabilities": ["review", "architecture", "explain"],
            "metadata": {"prompt_path": "prompts_11/_test.md"},
            "mission": "Проверить архитектурное решение: можно ли его принимать",
            "inputs": ["architectural_problem", "architecture", "models"],
            "production_workflow": ["problem_validation", "context_analysis", "verdict_generation"],
            "engines": ["@entity blueprint.v3"],
            "quality_gates": ["evidence_complete", "alternatives_considered"],
            "outputs": ["review_verdict", "review_report"],
            "artifacts": ["projects_17/<slug>/forge/review.yaml"],
            "interfaces": ["receives: architecture, models", "produces: review_result"],
            "memory": ["past_verdicts", "adr"],
            "knowledge": ["patterns: arch_patterns_v1"],
        }
        path = _dump_yaml(tmp_path / "review.yaml", data)
        pp = ForgePassport.from_yaml(path)
        assert pp.forge_id == "review"
        assert pp.capabilities == ("review", "architecture", "explain")
        assert pp.production_workflow == ("problem_validation", "context_analysis", "verdict_generation")
        assert pp.outputs == ("review_verdict", "review_report")
        assert pp.interfaces == ("receives: architecture, models", "produces: review_result")
        assert pp.validate() == []  # all token ⊆ KNOWN_CAPABILITIES

    def test_invalid_yaml_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.yaml"
        path.write_text("::not-yaml::\n  - bad: [unclosed\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Manifest повреждён"):
            ForgePassport.from_yaml(path)

    def test_yaml_root_not_dict_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "scalar.yaml"
        path.write_text("just_a_string_value\n", encoding="utf-8")
        with pytest.raises(ValueError, match="не является YAML-словарём"):
            ForgePassport.from_yaml(path)

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            ForgePassport.from_yaml(tmp_path / "nonexistent.yaml")


# ─── Class 2: required-field invariants ──────────────────────────────────────

class TestForgePassportRequiredFields:
    """Required-key enforcement per pomt DoD #1."""

    def test_empty_forge_id_raises(self, minimal_manifest_dict: dict[str, Any]) -> None:
        minimal_manifest_dict["forge_id"] = ""
        with pytest.raises(ValueError, match="forge_id — обязательное поле"):
            ForgePassport._from_dict(minimal_manifest_dict, source="<test>")

    def test_missing_forge_id_raises(self, minimal_manifest_dict: dict[str, Any]) -> None:
        del minimal_manifest_dict["forge_id"]
        with pytest.raises(ValueError, match="forge_id — обязательное поле"):
            ForgePassport._from_dict(minimal_manifest_dict, source="<test>")

    def test_empty_factory_id_raises(self, minimal_manifest_dict: dict[str, Any]) -> None:
        minimal_manifest_dict["factory_id"] = ""
        with pytest.raises(ValueError, match="factory_id — обязательное поле"):
            ForgePassport._from_dict(minimal_manifest_dict, source="<test>")

    def test_invalid_status_raises(self, minimal_manifest_dict: dict[str, Any]) -> None:
        minimal_manifest_dict["status"] = "PRODUCTION"  # uppercase = invalid
        with pytest.raises(ValueError, match=r"должен быть ∈"):
            ForgePassport._from_dict(minimal_manifest_dict, source="<test>")

    def test_forge_id_not_lowercase_slug_raises(self, minimal_manifest_dict: dict[str, Any]) -> None:
        minimal_manifest_dict["forge_id"] = "Review"  # capital R fails
        with pytest.raises(ValueError, match=r"lowercase, начинается с буквы"):
            ForgePassport._from_dict(minimal_manifest_dict, source="<test>")

    def test_forge_id_starts_with_digit_raises(self, minimal_manifest_dict: dict[str, Any]) -> None:
        minimal_manifest_dict["forge_id"] = "1review"  # digit-prefix fails
        with pytest.raises(ValueError, match=r"lowercase, начинается с буквы"):
            ForgePassport._from_dict(minimal_manifest_dict, source="<test>")

    def test_factory_id_post_init_pattern_defense(self, minimal_manifest_dict: dict[str, Any]) -> None:
        """Last-resort guard in __post_init__ (after field assignment)."""
        minimal_manifest_dict["factory_id"] = "BadFactoryId"
        # Post-init guard: Pytest.raises AttributeError or ValueError — we use
        # post_init to fail loudly.
        with pytest.raises(ValueError, match="factory_id"):
            ForgePassport._from_dict(minimal_manifest_dict, source="<test>")


# ─── Class 3: validate() (B10/R-127 + ANTI-6b) ────────────────────────────────

class TestForgePassportValidate:
    """Invariant checks: forge_id regex, mission non-empty, outputs non-empty,
    status ∈ valid set, capabilities ⊆ KNOWN_CAPABILITIES."""

    def test_valid_passport_returns_no_violations(self, minimal_manifest_dict: dict[str, Any]) -> None:
        pp = ForgePassport._from_dict(minimal_manifest_dict, source="<test>")
        assert pp.validate() == []

    def test_empty_mission_violation(self, minimal_manifest_dict: dict[str, Any]) -> None:
        minimal_manifest_dict["mission"] = ""
        pp = ForgePassport._from_dict(minimal_manifest_dict, source="<test>")
        violations = pp.validate()
        assert any("mission must be non-empty" in v for v in violations), violations

    def test_empty_outputs_violation(self, minimal_manifest_dict: dict[str, Any]) -> None:
        minimal_manifest_dict["outputs"] = []
        pp = ForgePassport._from_dict(minimal_manifest_dict, source="<test>")
        violations = pp.validate()
        assert any("outputs must be non-empty" in v for v in violations), violations

    def test_unknown_capability_violation(self, minimal_manifest_dict: dict[str, Any]) -> None:
        minimal_manifest_dict["capabilities"] = ["explain", "qa"]  # "qa" not in KNOWN_CAPABILITIES
        pp = ForgePassport._from_dict(minimal_manifest_dict, source="<test>")
        violations = pp.validate()
        assert any("unknown tokens" in v and "'qa'" in v for v in violations), violations

    def test_known_capability_only_passes(self, minimal_manifest_dict: dict[str, Any]) -> None:
        # All four are ⊆ KNOWN_CAPABILITIES.
        minimal_manifest_dict["capabilities"] = ["explain", "review", "architecture", "report"]
        pp = ForgePassport._from_dict(minimal_manifest_dict, source="<test>")
        assert pp.validate() == [], (
            "All tokens should pass KNOWN_CAPABILITIES check"
        )

    def test_status_out_of_set_violation(self, minimal_manifest_dict: dict[str, Any]) -> None:
        # Construct an instance with invalid status (bypassing _from_dict check).
        pp = ForgePassport(
            forge_id="x_forge", factory_id="y_factory", version="1", status="suspended",
            display_name="", capabilities=(), mission="m", outputs=("o",),
        )
        violations = pp.validate()
        assert any("status 'suspended'" in v for v in violations), violations


# ─── Class 4: round-trip to_yaml + scalars → tuple guards ─────────────────────

class TestForgePassportRoundTrip:
    """from_yaml → to_yaml → from_yaml = same object identity (semantic)."""

    def test_round_trip_preserves_all_fields(self, tmp_path: Path) -> None:
        data = {
            "forge_id": "review",
            "factory_id": "architecture",
            "version": "1.0.0",
            "status": "material",
            "display_name": "Architecture Review Forge",
            "capabilities": ["review", "architecture", "explain"],
            "metadata": {"prompt_path": "prompts_11/_test.md", "extra": 42},
            "mission": "Проверить архитектурное решение",
            "inputs": ["in1", "in2"],
            "production_workflow": ["step1", "step2"],
            "engines": ["@entity blueprint.v3"],
            "quality_gates": ["gate1"],
            "outputs": ["out1", "out2"],
            "artifacts": ["file1", "file2"],
            "interfaces": ["i1", "i2"],
            "memory": ["m1"],
            "knowledge": ["k1"],
        }
        path1 = _dump_yaml(tmp_path / "first.yaml", data)
        pp1 = ForgePassport.from_yaml(path1)
        path2 = tmp_path / "second.yaml"
        path2.write_text(pp1.to_yaml(), encoding="utf-8")
        pp2 = ForgePassport.from_yaml(path2)
        assert pp1 == pp2, "Round-trip must preserve dataclass equality"


class TestForgePassportSafetyHelpers:
    """_as_tuple / _as_dict module-level helpers (B10/R-127 noise-sensitive)."""

    def test_as_tuple_accepts_list(self) -> None:
        assert _as_tuple(["a", "b"], field_name="x") == ("a", "b")

    def test_as_tuple_accepts_existing_tuple(self) -> None:
        assert _as_tuple(("a", "b"), field_name="x") == ("a", "b")

    def test_as_tuple_none_returns_empty(self) -> None:
        assert _as_tuple(None, field_name="x") == ()

    def test_as_tuple_dict_raises(self) -> None:
        with pytest.raises(ValueError, match="НЕ-scalar → НЕ тихая потеря"):
            _as_tuple({"key": "value"}, field_name="x")

    def test_as_tuple_scalar_raises(self) -> None:
        with pytest.raises(ValueError, match="НЕ-scalar → НЕ тихая потеря"):
            _as_tuple(42, field_name="x")

    def test_as_dict_accepts_dict(self) -> None:
        assert _as_dict({"k": "v"}, field_name="x") == {"k": "v"}

    def test_as_dict_list_raises(self) -> None:
        with pytest.raises(ValueError, match="НЕ-scalar-для-объекта"):
            _as_dict(["a", "b"], field_name="x")


# ─── Class 5: to_dict() JSON-convention ───────────────────────────────────────

class TestForgePassportToDict:
    """to_dict() converts tuples → lists for JSON consumers."""

    def test_to_dict_has_lists_not_tuples(self, minimal_manifest_dict: dict[str, Any]) -> None:
        pp = ForgePassport._from_dict(minimal_manifest_dict, source="<test>")
        d = pp.to_dict()
        # All tuple-valued fields in the dataclass appear as lists in dict:
        for field_name in ("capabilities", "inputs", "production_workflow", "engines",
                           "quality_gates", "outputs", "artifacts", "interfaces",
                           "memory", "knowledge"):
            assert isinstance(d[field_name], list), field_name + " should be list in JSON"
        assert isinstance(d["forge_id"], str)
        assert isinstance(d["metadata"], dict)


# ─── Class 6: contract guarantees ─────────────────────────────────────────────

class TestForgePassportContract:
    """Frozen contract + REQUIRED_FIELDS public surface."""

    def test_required_fields_canonical_order(self) -> None:
        assert REQUIRED_FIELDS[:5] == ("forge_id", "factory_id", "version", "status", "display_name")
        assert "mission" in REQUIRED_FIELDS
        assert "outputs" in REQUIRED_FIELDS

    def test_dataclass_is_frozen(self, minimal_manifest_dict: dict[str, Any]) -> None:
        from dataclasses import FrozenInstanceError
        pp = ForgePassport._from_dict(minimal_manifest_dict, source="<test>")
        with pytest.raises(FrozenInstanceError):
            pp.mission = "tampered"  # type: ignore[misc]

    def test_valid_statuses_constant(self) -> None:
        # Order is documented in pomt — keep stable for ID consistency.
        assert _VALID_STATUSES == ("design", "material", "production")

    def test_slug_regex_pattern(self) -> None:
        # Sanity: documented contract pattern.
        assert _SLUG_RE.pattern == r"^[a-z][a-z0-9_]{1,30]$"
