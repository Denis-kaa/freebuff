"""Adapters for external static-analysis tools.

The adapters are sensors only: native tool output, scores and exit codes are
normalized into diagnostic-only reports and never become learning evidence.
"""

from __future__ import annotations

import json
***REMOVED***
import subprocess
from abc import ABC, abstractmethod
***REMOVED***
from typing import Any, Sequence

from app.diagnostics.contract import (
    Diagnostic,
    DiagnosticSeverity,
    SensorReport,
    SensorStatus,
)


class AnalyzerAdapter(ABC):
    """Common subprocess boundary for external analyzer sensors."""

    source: str

    def __init__(self, executable: str | None = None, timeout_seconds: float = 60.0) -> None:
        self.executable = executable or self.source
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def analyze(self, path: Path, *, security_eligible: bool = False) -> SensorReport:
        raise NotImplementedError

    def _run(
        self,
        args: Sequence[str***REMOVED***,
        *,
        accepted_exit_codes: tuple[int, ...***REMOVED*** = (0, 1),
    ) -> tuple[SensorStatus, str, str, int | None***REMOVED***:
        try:
            completed = subprocess.run(
                list(args),
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError:
            return SensorStatus.UNAVAILABLE, "", f"{self.executable***REMOVED***: executable not found", None
        except subprocess.TimeoutExpired as exc:
            stderr = _text(exc.stderr)
            return SensorStatus.FAILED, _text(exc.stdout), "analyzer timeout" if not stderr else stderr, None
        except OSError as exc:
            return SensorStatus.FAILED, "", f"{type(exc).__name__***REMOVED***: {exc***REMOVED***", None
        status = SensorStatus.OK if completed.returncode in accepted_exit_codes else SensorStatus.FAILED
        return status, completed.stdout, completed.stderr, completed.returncode


class PylintAdapter(AnalyzerAdapter):
    """Normalize Pylint JSON messages without exposing Pylint's schema."""

    source = "pylint"

    def analyze(self, path: Path, *, security_eligible: bool = False) -> SensorReport:
        status, stdout, stderr, exit_code = self._run(
            (self.executable, "--output-format=json", "--reports=no", str(path)),
            accepted_exit_codes=tuple(range(32)),
        )
        if status is not SensorStatus.OK:
            return SensorReport(self.source, status, stderr=stderr, exit_code=exit_code)
        try:
            payload = json.loads(stdout or "[***REMOVED***")
            if not isinstance(payload, list):
                raise ValueError("expected a JSON list")
            diagnostics = tuple(_pylint_item(item, path) for item in payload)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return SensorReport(
                self.source,
                SensorStatus.INVALID_OUTPUT,
                stderr=f"invalid pylint JSON: {exc***REMOVED***",
                exit_code=exit_code,
            )
        return SensorReport(self.source, SensorStatus.OK, diagnostics, stderr, exit_code).ordered()


class RadonAdapter(AnalyzerAdapter):
    """Normalize Radon complexity, raw, Halstead and maintainability metrics."""

    source = "radon"

    def analyze(self, path: Path, *, security_eligible: bool = False) -> SensorReport:
        diagnostics: list[Diagnostic***REMOVED*** = [***REMOVED***
        errors: list[str***REMOVED*** = [***REMOVED***
        exit_codes: list[int***REMOVED*** = [***REMOVED***
        commands = (
            ("cc", "complexity", self._parse_complexity),
            ("raw", "raw metrics", self._parse_raw),
            ("hal", "Halstead metrics", self._parse_halstead),
            ("mi", "maintainability index", self._parse_mi),
        )
        for command, label, parser in commands:
            status, stdout, stderr, exit_code = self._run(
                (self.executable, command, "-j", str(path))
            )
            if exit_code is not None:
                exit_codes.append(exit_code)
            if status is SensorStatus.UNAVAILABLE:
                return SensorReport(self.source, status, stderr=stderr, exit_code=exit_code)
            if status is not SensorStatus.OK:
                errors.append(f"{label***REMOVED***: {stderr or 'tool failed'***REMOVED***")
                continue
            try:
                diagnostics.extend(parser(stdout, path))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{label***REMOVED***: invalid JSON: {exc***REMOVED***")
        if errors and not diagnostics:
            return SensorReport(
                self.source,
                SensorStatus.INVALID_OUTPUT if any("invalid JSON" in item for item in errors) else SensorStatus.FAILED,
                stderr="; ".join(errors),
                exit_code=exit_codes[-1***REMOVED*** if exit_codes else None,
            )
        return SensorReport(
            self.source,
            SensorStatus.OK if not errors else SensorStatus.FAILED,
            tuple(diagnostics),
            stderr="; ".join(errors),
            exit_code=exit_codes[-1***REMOVED*** if exit_codes else 0,
        ).ordered()

    @staticmethod
    def _parse_complexity(raw: str, path: Path) -> list[Diagnostic***REMOVED***:
        payload = _json_object(raw)
        items = payload.get(str(path), [***REMOVED***)
        if not isinstance(items, list):
            raise ValueError("complexity payload must contain a list")
        result: list[Diagnostic***REMOVED*** = [***REMOVED***
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("complexity item must be an object")
            complexity = item.get("complexity")
            name = str(item.get("name", "<unknown>"))
            line = _positive_int(item.get("lineno", 1))
            result.append(
                _diagnostic(
                    "RADON_CC",
                    "cyclomatic-complexity",
                    "cyclomatic-complexity",
                    DiagnosticSeverity.MEDIUM if _number(complexity) > 10 else DiagnosticSeverity.INFO,
                    path,
                    line,
                    f"{name***REMOVED*** cyclomatic complexity is {complexity***REMOVED***",
                )
            )
        return result

    @staticmethod
    def _parse_raw(raw: str, path: Path) -> list[Diagnostic***REMOVED***:
        payload = _json_object(raw)
        item = payload.get(str(path), {***REMOVED***)
        if not isinstance(item, dict):
            raise ValueError("raw payload must contain an object")
        result: list[Diagnostic***REMOVED*** = [***REMOVED***
        for key, pattern, message in (
            ("loc", "lines-of-code", "logical lines of code"),
            ("lloc", "logical-lines-of-code", "logical lines"),
            ("sloc", "source-lines-of-code", "source lines"),
            ("comments", "comment-lines", "comment lines"),
        ):
            if key in item:
                result.append(_diagnostic("RADON_RAW", pattern, pattern, DiagnosticSeverity.INFO, path, 1, f"{message***REMOVED***: {item[key***REMOVED******REMOVED***"))
        return result

    @staticmethod
    def _parse_halstead(raw: str, path: Path) -> list[Diagnostic***REMOVED***:
        payload = _json_object(raw)
        item = payload.get(str(path), {***REMOVED***)
        if not isinstance(item, dict):
            raise ValueError("Halstead payload must contain an object")
        metrics = item.get("total", item)
        if not isinstance(metrics, dict):
            raise ValueError("Halstead metrics must contain an object")
        result: list[Diagnostic***REMOVED*** = [***REMOVED***
        for key in ("h1", "h2", "N1", "N2", "vocabulary", "length", "volume", "difficulty", "effort", "time", "bugs"):
            if key in metrics:
                result.append(_diagnostic("RADON_HAL", f"halstead-{key.lower()***REMOVED***", f"halstead-{key.lower()***REMOVED***", DiagnosticSeverity.INFO, path, 1, f"Halstead {key***REMOVED***: {metrics[key***REMOVED******REMOVED***"))
        return result

    @staticmethod
    def _parse_mi(raw: str, path: Path) -> list[Diagnostic***REMOVED***:
        payload = _json_object(raw)
        value = payload.get(str(path))
        if isinstance(value, dict):
            value = value.get("mi", value.get("maintainability_index"))
        if value is None:
            raise ValueError("maintainability index is missing")
        return [_diagnostic(
            "RADON_MI",
            "maintainability-index",
            "maintainability-index",
            DiagnosticSeverity.INFO,
            path,
            1,
            f"maintainability index: {value***REMOVED***",
        )***REMOVED***


class Flake8Adapter(AnalyzerAdapter):
    """Normalize Flake8's stable line-oriented output."""

    source = "flake8"
    _line = re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?P<column>\d+):\s*(?P<rule>[A-Z***REMOVED***\d+)\s+(?P<message>.+)$")

    def analyze(self, path: Path, *, security_eligible: bool = False) -> SensorReport:
        status, stdout, stderr, exit_code = self._run((self.executable, str(path)))
        if status is not SensorStatus.OK:
            return SensorReport(self.source, status, stderr=stderr, exit_code=exit_code)
        diagnostics: list[Diagnostic***REMOVED*** = [***REMOVED***
        for line in stdout.splitlines():
            match = self._line.match(line.strip())
            if match is None:
                return SensorReport(self.source, SensorStatus.INVALID_OUTPUT, stderr=f"invalid flake8 line: {line***REMOVED***", exit_code=exit_code)
            diagnostics.append(_diagnostic(
                "FLAKE8",
                match.group("rule"),
                f"flake8-{match.group('rule').lower()***REMOVED***",
                _severity_for_rule(match.group("rule")),
                Path(match.group("file")),
                int(match.group("line")),
                f"{match.group('rule')***REMOVED***: {match.group('message')***REMOVED***",
                column=int(match.group("column")),
            ))
        return SensorReport(self.source, SensorStatus.OK, tuple(diagnostics), stderr, exit_code).ordered()


class BanditAdapter(AnalyzerAdapter):
    """Run Bandit only when the caller explicitly marks code security-eligible."""

    source = "bandit"

    def analyze(self, path: Path, *, security_eligible: bool = False) -> SensorReport:
        if not security_eligible:
            return SensorReport(self.source, SensorStatus.OK, stderr="skipped: security_eligible=false", exit_code=0)
        status, stdout, stderr, exit_code = self._run(
            (self.executable, "-q", "-f", "json", str(path))
        )
        if status is not SensorStatus.OK:
            return SensorReport(self.source, status, stderr=stderr, exit_code=exit_code)
        try:
            payload = json.loads(stdout or '{"results": [***REMOVED******REMOVED***')
            results = payload["results"***REMOVED***
            if not isinstance(results, list):
                raise ValueError("results must be a list")
            diagnostics = tuple(_bandit_item(item, path) for item in results)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return SensorReport(self.source, SensorStatus.INVALID_OUTPUT, stderr=f"invalid bandit JSON: {exc***REMOVED***", exit_code=exit_code)
        return SensorReport(self.source, SensorStatus.OK, diagnostics, stderr, exit_code).ordered()


def _pylint_item(item: Any, default_path: Path) -> Diagnostic:
    if not isinstance(item, dict):
        raise ValueError("pylint item must be an object")
    rule_id = str(item["message-id"***REMOVED***)
    return _diagnostic(
        "PYLINT",
        rule_id,
        f"pylint-{rule_id.lower()***REMOVED***",
        _severity_for_pylint(str(item.get("type", "convention"))),
        _path_value(item.get("path"), default_path),
        _positive_int(item.get("line", 1)),
        str(item.get("message", rule_id)),
        column=_nonnegative_int(item.get("column", 0)),
    )


def _bandit_item(item: Any, default_path: Path) -> Diagnostic:
    if not isinstance(item, dict):
        raise ValueError("bandit item must be an object")
    test_id = str(item["test_id"***REMOVED***)
    return _diagnostic(
        "BANDIT",
        test_id,
        f"bandit-{test_id.lower()***REMOVED***",
        _severity_for_bandit(str(item.get("issue_severity", "low"))),
        _path_value(item.get("filename"), default_path),
        _positive_int(item.get("line_number", 1)),
        str(item.get("issue_text", test_id)),
        column=_nonnegative_int(item.get("col_offset", 0)),
    )


def _diagnostic(
    source: str,
    rule_id: str,
    pattern_id: str,
    severity: DiagnosticSeverity,
    path: Path,
    line: int,
    message: str,
    *,
    column: int = 0,
) -> Diagnostic:
    return Diagnostic(
        source=source,
        rule_id=rule_id,
        pattern_id=pattern_id,
        severity=severity,
        file=str(path),
        line=line,
        column=column,
        message=message,
    )


def _json_object(raw: str) -> dict[str, Any***REMOVED***:
    value = json.loads(raw or "{***REMOVED***")
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def _path_value(value: Any, fallback: Path) -> Path:
    return Path(str(value)) if value else fallback


def _positive_int(value: Any) -> int:
    result = int(value)
    if result < 1:
        raise ValueError("expected positive integer")
    return result


def _nonnegative_int(value: Any) -> int:
    result = int(value)
    if result < 0:
        raise ValueError("expected non-negative integer")
    return result


def _number(value: Any) -> float:
    return float(value)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)


def _severity_for_rule(rule_id: str) -> DiagnosticSeverity:
    return DiagnosticSeverity.MEDIUM if rule_id.startswith(("E9", "F", "B")) else DiagnosticSeverity.LOW


def _severity_for_pylint(kind: str) -> DiagnosticSeverity:
    return {
        "error": DiagnosticSeverity.HIGH,
        "warning": DiagnosticSeverity.MEDIUM,
        "refactor": DiagnosticSeverity.MEDIUM,
        "convention": DiagnosticSeverity.LOW,
    ***REMOVED***.get(kind.lower(), DiagnosticSeverity.INFO)


def _severity_for_bandit(value: str) -> DiagnosticSeverity:
    return {
        "high": DiagnosticSeverity.HIGH,
        "medium": DiagnosticSeverity.MEDIUM,
        "low": DiagnosticSeverity.LOW,
    ***REMOVED***.get(value.lower(), DiagnosticSeverity.INFO)
