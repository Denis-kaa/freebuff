"""tests_09/test_factory_passport.py — test suite for core_02/factory_passport.py::FactoryPassport.

Pattern mirrors tests_09/test_forge_passport.py (heavy use of tmp_path for isolation).
Coverage per pompts_11/089_19_factory_registry_full.md §TESTS (C-2):
  - from_yaml happy-path
  - missing required fields → ValueError
  - invalid status → ValueError
  - vocabulary drift → validate() violation (ANTI-6b)
  - to_dict roundtrip

CAN-16 ADDITIVE: этот файл НЕ модифицирует core_02/* или runtime_05/*.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core_02.factory_passport import (
    FactoryPassport,
    REQUIRED_FIELDS,
)


# ─── fixture helpers ──────────────────────────────────────────────────────────

def _dump_yaml(path: Path, data: dict) -> Path:
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _valid_meta(**overrides) -> dict:
    meta = {
        "factory_id": "architecture",
        "display_name": "Architecture Factory",
        "version": "1.0.0",
        "status": "production",
        "description": "Forge-семейство для архитектурных решений.",
        "capabilities": ["architecture", "review", "validate"],
        "metadata": {"owner": "core-platform"},
    }
    meta.update(overrides)
    return meta


# ─── Class 1: from_yaml ───────────────────────────────────────────────────────

class TestFactoryPassportFromYaml:
    def test_from_yaml_happy_path(self, tmp_path: Path) -> None:
        p = _dump_yaml(tmp_path / "factory.yaml", _valid_meta())
        fp = FactoryPassport.from_yaml(p)
        assert fp.factory_id == "architecture"
        assert fp.display_name == "Architecture Factory"
        assert fp.version == "1.0.0"
        assert fp.status == "production"
        assert fp.capabilities == ("architecture", "review", "validate")
        assert fp.metadata == {"owner": "core-platform"}
        assert fp.validate() == []

    def test_from_yaml_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            FactoryPassport.from_yaml(tmp_path / "missing.yaml")

    def test_from_yaml_missing_required_field_raises(self, tmp_path: Path) -> None:
        meta = _valid_meta()
        del meta["description"]
        p = _dump_yaml(tmp_path / "factory.yaml", meta)
        with pytest.raises(ValueError):
            FactoryPassport.from_yaml(p)

    def test_from_yaml_invalid_status_raises(self, tmp_path: Path) -> None:
        p = _dump_yaml(tmp_path / "factory.yaml", _valid_meta(status="bogus"))
        with pytest.raises(ValueError):
            FactoryPassport.from_yaml(p)

    def test_from_yaml_invalid_factory_id_slug_raises(self, tmp_path: Path) -> None:
        p = _dump_yaml(tmp_path / "factory.yaml", _valid_meta(factory_id="Bad-ID"))
        with pytest.raises(ValueError):
            FactoryPassport.from_yaml(p)


# ─── Class 2: vocabulary (ANTI-6b) ────────────────────────────────────────────

class TestFactoryPassportVocabulary:
    def test_unknown_capability_violation(self, tmp_path: Path) -> None:
        p = _dump_yaml(tmp_path / "factory.yaml", _valid_meta(capabilities=["unknown_token"]))
        fp = FactoryPassport.from_yaml(p)
        violations = fp.validate()
        assert any("unknown tokens" in v and "unknown_token" in v for v in violations), violations

    def test_known_capabilities_pass(self, tmp_path: Path) -> None:
        p = _dump_yaml(tmp_path / "factory.yaml", _valid_meta(capabilities=["architecture", "review"]))
        fp = FactoryPassport.from_yaml(p)
        assert fp.validate() == []


# ─── Class 3: roundtrip / serialization ───────────────────────────────────────

class TestFactoryPassportRoundtrip:
    def test_to_dict_json_convention(self, tmp_path: Path) -> None:
        p = _dump_yaml(tmp_path / "factory.yaml", _valid_meta())
        fp = FactoryPassport.from_yaml(p)
        d = fp.to_dict()
        assert d["factory_id"] == "architecture"
        assert isinstance(d["capabilities"], list)
        assert d["capabilities"] == ["architecture", "review", "validate"]
        assert d["metadata"] == {"owner": "core-platform"}

    def test_required_fields_exported(self) -> None:
        assert "factory_id" in REQUIRED_FIELDS
        assert "display_name" in REQUIRED_FIELDS
        assert "version" in REQUIRED_FIELDS
        assert "status" in REQUIRED_FIELDS
        assert "description" in REQUIRED_FIELDS
