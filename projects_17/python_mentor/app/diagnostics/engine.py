"""Facade for deterministic AST diagnostics."""

from __future__ import annotations

import ast
***REMOVED***

from app.diagnostics.ast_rules import ASTRuleRegistry, RuleContext, default_registry
from app.diagnostics.contract import (
    Diagnostic,
    DiagnosticSeverity,
    SensorReport,
    SensorStatus,
)


class ASTAnalyzer:
    """Run the registered AST rules against a source string or Python file."""

    source = "ast"

    def __init__(self, registry: ASTRuleRegistry | None = None) -> None:
        self.registry = registry or default_registry()

    def analyze_source(
        self,
        source: str,
        *,
        filename: str = "<student.py>",
        competency_id: str | None = None,
    ) -> SensorReport:
        try:
            diagnostics = self.registry.analyze(
                source,
                RuleContext(filename=filename, competency_id=competency_id),
            )
        except SyntaxError as exc:
            diagnostic = Diagnostic(
                source=self.source,
                rule_id="AST000",
                pattern_id="syntax-error",
                severity=DiagnosticSeverity.HIGH,
                file=filename,
                line=max(exc.lineno or 1, 1),
                column=max((exc.offset or 1) - 1, 0),
                message="source cannot be parsed: syntax error",
                competency_id=competency_id,
            )
            return SensorReport(self.source, SensorStatus.INVALID_OUTPUT, (diagnostic,)).ordered()
        return SensorReport(self.source, SensorStatus.OK, diagnostics).ordered()

    def analyze_file(self, path: Path, *, competency_id: str | None = None) -> SensorReport:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            return SensorReport(self.source, SensorStatus.FAILED, stderr=f"{type(exc).__name__***REMOVED***: {exc***REMOVED***")
        return self.analyze_source(source, filename=str(path), competency_id=competency_id)


def analyze_ast(
    source: str,
    *,
    filename: str = "<student.py>",
    competency_id: str | None = None,
) -> SensorReport:
    """Convenience function with the default Phase F registry."""

    return ASTAnalyzer().analyze_source(
        source,
        filename=filename,
        competency_id=competency_id,
    )
