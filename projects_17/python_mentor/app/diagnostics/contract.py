"""Normalized diagnostic contracts for deterministic static-analysis sensors."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DiagnosticSeverity(str, Enum):
    """Stable severity vocabulary independent of an analyzer's native labels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SensorStatus(str, Enum):
    """Execution status for an analyzer sensor."""

    OK = "ok"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    INVALID_OUTPUT = "invalid_output"


@dataclass(frozen=True)
class Diagnostic:
    """One normalized finding; always diagnostic-only by construction."""

    source: str
    rule_id: str
    pattern_id: str
    severity: DiagnosticSeverity
    file: str
    line: int
    column: int
    message: str
    diagnostic_only: bool = True
    competency_id: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.rule_id.strip() or not self.pattern_id.strip():
            raise ValueError("diagnostic identifiers must not be empty")
        if self.line < 1 or self.column < 0:
            raise ValueError("diagnostic location is invalid")
        if not self.message.strip():
            raise ValueError("diagnostic message must not be empty")
        if not self.diagnostic_only:
            raise ValueError("Phase F diagnostics must be diagnostic_only")

    def sort_key(self) -> tuple[str, int, int, str, str, str***REMOVED***:
        return (
            self.file,
            self.line,
            self.column,
            self.source,
            self.rule_id,
            self.message,
        )

    def to_dict(self) -> dict[str, Any***REMOVED***:
        return {
            "source": self.source,
            "rule_id": self.rule_id,
            "pattern_id": self.pattern_id,
            "severity": self.severity.value,
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "diagnostic_only": self.diagnostic_only,
            "competency_id": self.competency_id,
        ***REMOVED***


@dataclass(frozen=True)
class SensorReport:
    """Normalized adapter result; it carries no score or evidence fields."""

    source: str
    status: SensorStatus
    diagnostics: tuple[Diagnostic, ...***REMOVED*** = ()
    stderr: str = ""
    exit_code: int | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("sensor source must not be empty")
        if any(not finding.diagnostic_only for finding in self.diagnostics):
            raise ValueError("sensor reports cannot contain learning evidence")

    def ordered(self) -> SensorReport:
        return SensorReport(
            source=self.source,
            status=self.status,
            diagnostics=tuple(sorted(self.diagnostics, key=Diagnostic.sort_key)),
            stderr=self.stderr,
            exit_code=self.exit_code,
        )

    def to_dict(self) -> dict[str, Any***REMOVED***:
        ordered = self.ordered()
        return {
            "source": ordered.source,
            "status": ordered.status.value,
            "diagnostics": [item.to_dict() for item in ordered.diagnostics***REMOVED***,
            "stderr": ordered.stderr,
            "exit_code": ordered.exit_code,
        ***REMOVED***
