from __future__ import annotations

import json
import stat
***REMOVED***

import pytest

from app.diagnostics import (
    ASTAnalyzer,
    BanditAdapter,
    Diagnostic,
    DiagnosticSeverity,
    Flake8Adapter,
    PylintAdapter,
    RadonAdapter,
    SensorStatus,
    default_registry,
    map_diagnostics,
)


def test_registry_has_stable_initial_rule_set() -> None:
    registry = default_registry()
    assert [rule.rule_id for rule in registry.rules()***REMOVED*** == [
        "AST001",
        "AST002",
        "AST003",
        "AST004",
        "AST005",
        "AST006",
        "AST007",
    ***REMOVED***
    with pytest.raises(ValueError):
        registry.register(registry.get("AST001"))


def test_ast_rules_report_expected_positive_findings() -> None:
    source = """\
state = [***REMOVED***

def f(items=[***REMOVED***, list=1):
    try:
        if items:
            for item in items:
                while item:
                    with open('x') as handle:
                        if handle:
                            if item:
                                if item:
                                    return item
    except:
        pass
    return None
    print('never')
"""
    report = ASTAnalyzer().analyze_source(source, filename="student.py", competency_id="code-structure")
    ***REMOVED***item.pattern_id for item in report.diagnostics***REMOVED***
    assert report.status is SensorStatus.OK
    assert {
        "mutable-default-argument",
        "builtin-shadowing",
        "excessive-nesting",
        "bare-except",
        "unreachable-code",
        "mutable-module-state",
    ***REMOVED*** <= patterns
    assert all(item.diagnostic_only for item in report.diagnostics)
    assert all(item.competency_id == "code-structure" for item in report.diagnostics)


def test_ast_rules_negative_and_edge_cases_do_not_flag_safe_code() -> None:
    source = """\
def f(items=None):
    if items is None:
        items = [***REMOVED***
    try:
        return len(items)
    except ValueError:
        return 0

class Example:
    def method(self):
        return 1
"""
    report = ASTAnalyzer().analyze_source(source)
    assert report.status is SensorStatus.OK
    assert {item.pattern_id for item in report.diagnostics***REMOVED*** == set()


def test_ast_syntax_error_is_normalized() -> None:
    report = ASTAnalyzer().analyze_source("def broken(:\n", filename="broken.py")
    assert report.status is SensorStatus.INVALID_OUTPUT
    assert [item.pattern_id for item in report.diagnostics***REMOVED*** == ["syntax-error"***REMOVED***
    assert report.diagnostics[0***REMOVED***.severity is DiagnosticSeverity.HIGH


def test_oversized_function_is_deterministic() -> None:
    source = "def large():\n" + "    value = 1\n" * 41
    first = ASTAnalyzer().analyze_source(source).to_dict()
    second = ASTAnalyzer().analyze_source(source).to_dict()
    assert first == second
    assert any(item["pattern_id"***REMOVED*** == "oversized-function" for item in first["diagnostics"***REMOVED***)


def test_patterns_are_reference_metadata_only() -> None:
    finding = Diagnostic(
        source="radon",
        rule_id="RADON_MI",
        pattern_id="maintainability-index",
        severity=DiagnosticSeverity.INFO,
        file="student.py",
        line=1,
        column=0,
        message="maintainability index: 42",
    )
    patterns = map_diagnostics((finding,))
    assert patterns[0***REMOVED***.hint_key == "review-code-structure"
    assert patterns[0***REMOVED***.diagnostic_only is True
    assert not hasattr(patterns[0***REMOVED***, "evidence_candidates")


def _make_fake_tool(tmp_path: Path, payload: str, exit_code: int = 0) -> Path:
    script = tmp_path / "fake-tool.py"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        f"print({payload!r***REMOVED***)\n"
        f"raise SystemExit({exit_code***REMOVED***)\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def test_pylint_adapter_normalizes_json_and_nonzero_diagnostic_exit(tmp_path: Path) -> None:
    payload = json.dumps([
        {
            "type": "warning",
            "module": "student",
            "obj": "f",
            "line": 3,
            "column": 2,
            "message": "bad thing",
            "message-id": "W0612",
            "path": "student.py",
        ***REMOVED***
    ***REMOVED***)
    tool = _make_fake_tool(tmp_path, payload, exit_code=4)
    report = PylintAdapter(executable=str(tool)).analyze(tmp_path / "student.py")
    assert report.status is SensorStatus.OK
    assert report.exit_code == 4
    assert report.diagnostics[0***REMOVED***.rule_id == "W0612"
    assert report.diagnostics[0***REMOVED***.severity is DiagnosticSeverity.MEDIUM


def test_pylint_adapter_rejects_malformed_output(tmp_path: Path) -> None:
    malformed = _make_fake_tool(tmp_path, "not-json", exit_code=0)
    report = PylintAdapter(executable=str(malformed)).analyze(tmp_path / "student.py")
    assert report.status is SensorStatus.INVALID_OUTPUT


def test_flake8_adapter_parses_lines_and_rejects_malformed_output(tmp_path: Path) -> None:
    source = tmp_path / "flake-output"
    source.write_text("student.py:4:2: E302 expected 2 blank lines\n", encoding="utf-8")
    tool = _make_fake_tool(tmp_path, "student.py:4:2: E302 expected 2 blank lines", exit_code=1)
    report = Flake8Adapter(executable=str(tool)).analyze(source)
    assert report.status is SensorStatus.OK
    assert report.diagnostics[0***REMOVED***.rule_id == "E302"

    malformed = _make_fake_tool(tmp_path, "unexpected output", exit_code=0)
    malformed_report = Flake8Adapter(executable=str(malformed)).analyze(source)
    assert malformed_report.status is SensorStatus.INVALID_OUTPUT


def test_radon_adapter_normalizes_all_metric_families(tmp_path: Path) -> None:
    tool = tmp_path / "radon-fake.py"
    tool.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "path = sys.argv[-1***REMOVED***\n"
        "command = sys.argv[1***REMOVED***\n"
        "payloads = {\n"
        "  'cc': {path: [{'name': 'f', 'lineno': 2, 'complexity': 12***REMOVED******REMOVED******REMOVED***,\n"
        "  'raw': {path: {'loc': 10, 'lloc': 8, 'sloc': 9, 'comments': 1***REMOVED******REMOVED***,\n"
        "  'hal': {path: {'total': {'h1': 1, 'h2': 2, 'N1': 3, 'N2': 4, 'volume': 5***REMOVED******REMOVED******REMOVED***,\n"
        "  'mi': {path: {'mi': 77.5***REMOVED******REMOVED***,\n"
        "***REMOVED***\n"
        "print(json.dumps(payloads[command***REMOVED***))\n",
        encoding="utf-8",
    )
    tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    report = RadonAdapter(executable=str(tool)).analyze(tmp_path / "student.py")
    assert report.status is SensorStatus.OK
    ***REMOVED***item.pattern_id for item in report.diagnostics***REMOVED***
    assert {"cyclomatic-complexity", "lines-of-code", "halstead-volume", "maintainability-index"***REMOVED*** <= patterns
    assert all(item.diagnostic_only for item in report.diagnostics)


def test_bandit_adapter_normalizes_security_findings(tmp_path: Path) -> None:
    payload = json.dumps({
        "results": [
            {
                "test_id": "B602",
                "issue_severity": "HIGH",
                "issue_text": "subprocess with shell=True",
                "filename": "student.py",
                "line_number": 4,
                "col_offset": 2,
            ***REMOVED***
        ***REMOVED***
    ***REMOVED***)
    tool = _make_fake_tool(tmp_path, payload, exit_code=1)
    report = BanditAdapter(executable=str(tool)).analyze(
        tmp_path / "student.py",
        security_eligible=True,
    )
    assert report.status is SensorStatus.OK
    assert report.diagnostics[0***REMOVED***.pattern_id == "bandit-b602"
    assert report.diagnostics[0***REMOVED***.severity is DiagnosticSeverity.HIGH


def test_bandit_security_gate_and_unavailable_tool(tmp_path: Path) -> None:
    source = tmp_path / "student.py"
    source.write_text("import subprocess\n", encoding="utf-8")
    skipped = BanditAdapter(executable="missing-bandit").analyze(source)
    assert skipped.status is SensorStatus.OK
    assert skipped.diagnostics == ()
    assert "security_eligible=false" in skipped.stderr

    unavailable = BanditAdapter(executable="missing-bandit").analyze(source, security_eligible=True)
    assert unavailable.status is SensorStatus.UNAVAILABLE


def test_radon_adapter_unavailable_and_tool_failure_are_explicit(tmp_path: Path) -> None:
    report = RadonAdapter(executable="missing-radon").analyze(tmp_path / "student.py")
    assert report.status is SensorStatus.UNAVAILABLE

    failed = _make_fake_tool(tmp_path, "failure", exit_code=9)
    failed_report = RadonAdapter(executable=str(failed)).analyze(tmp_path / "student.py")
    assert failed_report.status is SensorStatus.FAILED


def test_diagnostic_contract_rejects_non_diagnostic_values() -> None:
    with pytest.raises(ValueError):
        Diagnostic(
            source="test",
            rule_id="R",
            pattern_id="p",
            severity=DiagnosticSeverity.INFO,
            file="x.py",
            line=1,
            column=0,
            message="bad",
            diagnostic_only=False,
        )
