"""
Tests for Plugin Contract Specification (правило 9, промт 37).

Covers:
  - validate_manifest (required fields, name/version format, events, python_version)
  - validate_plugin_entry (manifest + instance contract)
  - severity (WARN vs ERROR)
  - has_errors / format_violations
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add workspace root to path for imports
WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from scripts_01.plugin_api import (
    BasePlugin,
    PluginManifest,
    PluginEntry,
    PluginState,
)
from scripts_01.plugin_contract import (
    ContractSeverity,
    ContractViolation,
    validate_manifest,
    validate_plugin_entry,
    has_errors,
    format_violations,
)


class DemoPlugin(BasePlugin):
    """Минимальный валидный плагин."""

    def __init__(self):
        super().__init__("demo_plugin", "1.0.0", "Test plugin")


def _make_entry(
    manifest: PluginManifest | None = None,
    instance: BasePlugin | None = None,
    name: str | None = None,
) -> PluginEntry:
    entry_name = name
    if entry_name is None and instance is not None:
        try:
            entry_name = instance.name
        except AttributeError:
            entry_name = "unknown"
    if entry_name is None and manifest is not None:
        entry_name = manifest.name
    return PluginEntry(
        name=entry_name or "x",
        path=Path("/tmp/plugin"),
        state=PluginState.LOADED,
        manifest=manifest,
        instance=instance,
    )


# ═══════════════════════════════════════════════════════════════
# validate_manifest
# ═══════════════════════════════════════════════════════════════


class TestValidateManifest:
    def test_valid_manifest_no_violations(self):
        m = PluginManifest(name="my_plugin", version="1.2.3", description="Desc")
        violations = validate_manifest(m)
        assert violations == []

    def test_none_manifest_error(self):
        violations = validate_manifest(None)
        assert len(violations) == 1
        assert violations[0].severity == ContractSeverity.ERROR
        assert violations[0].field == "manifest"

    def test_missing_name_error(self):
        m = PluginManifest(name="", version="1.0.0", description="Desc")
        violations = validate_manifest(m)
        names = [v.field for v in violations]
        assert "manifest.name" in names
        assert all(v.severity == ContractSeverity.ERROR for v in violations)

    def test_missing_description_error(self):
        m = PluginManifest(name="ok", version="1.0.0", description="")
        violations = validate_manifest(m)
        assert any(v.field == "manifest.description" for v in violations)

    def test_invalid_name_format(self):
        m = PluginManifest(name="My Plugin!", version="1.0.0", description="D")
        violations = validate_manifest(m)
        assert any(
            v.field == "manifest.name" and v.severity == ContractSeverity.ERROR
            for v in violations
        )

    def test_invalid_version_format(self):
        m = PluginManifest(name="ok", version="v1.0", description="D")
        violations = validate_manifest(m)
        assert any(
            v.field == "manifest.version" and v.severity == ContractSeverity.ERROR
            for v in violations
        )

    def test_invalid_event_pattern_warn(self):
        m = PluginManifest(
            name="ok", version="1.0.0", description="D",
            events_subscribed=["Invalid Event", "valid.event", "system.*"],
        )
        violations = validate_manifest(m)
        event_fields = [v for v in violations if "events_subscribed" in v.field]
        assert len(event_fields) == 1  # только Invalid Event
        assert event_fields[0].severity == ContractSeverity.WARN

    def test_python_version_incompatible_warn(self):
        m = PluginManifest(
            name="ok", version="1.0.0", description="D",
            python_version=">=99.0",
        )
        violations = validate_manifest(m)
        assert any(
            v.field == "manifest.python_version"
            and v.severity == ContractSeverity.WARN
            for v in violations
        )


# ═══════════════════════════════════════════════════════════════
# validate_plugin_entry
# ═══════════════════════════════════════════════════════════════


class TestValidatePluginEntry:
    def test_valid_entry_no_violations(self):
        entry = _make_entry(
            manifest=PluginManifest(name="demo", version="1.0.0", description="D"),
            instance=DemoPlugin(),
        )
        assert validate_plugin_entry(entry) == []

    def test_entry_without_instance_error(self):
        entry = _make_entry(manifest=PluginManifest(name="demo", version="1.0.0", description="D"))
        violations = validate_plugin_entry(entry)
        assert any(
            v.field == "instance" and v.severity == ContractSeverity.ERROR
            for v in violations
        )

    def test_entry_instance_not_base_plugin_error(self):
        entry = _make_entry(
            manifest=PluginManifest(name="demo", version="1.0.0", description="D"),
            instance=object(),  # type: ignore
            name="demo",
        )
        violations = validate_plugin_entry(entry)
        assert any(
            v.field == "instance" and v.severity == ContractSeverity.ERROR
            for v in violations
        )

    def test_entry_missing_manifest_error(self):
        entry = _make_entry(instance=DemoPlugin())
        violations = validate_plugin_entry(entry)
        assert any(v.field == "manifest" for v in violations)

    def test_entry_combines_manifest_and_instance(self):
        entry = _make_entry(
            manifest=PluginManifest(name="", version="bad", description="D"),
            instance=DemoPlugin(),
        )
        violations = validate_plugin_entry(entry)
        fields = {v.field for v in violations}
        assert "manifest.name" in fields
        assert "manifest.version" in fields


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


class TestHelpers:
    def test_has_errors(self):
        assert not has_errors([])
        assert not has_errors([ContractViolation("f", "m", ContractSeverity.WARN)])
        assert has_errors([ContractViolation("f", "m", ContractSeverity.ERROR)])

    def test_format_violations_ok(self):
        out = format_violations("demo", [])
        assert "✅" in out
        assert "demo" in out

    def test_format_violations_with_errors(self):
        out = format_violations("demo", [
            ContractViolation("manifest.name", "bad name", ContractSeverity.ERROR),
        ])
        assert "❌" in out
        assert "manifest.name" in out
        assert "ERROR" in out
