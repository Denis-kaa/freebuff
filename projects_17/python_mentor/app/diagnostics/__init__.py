"""Phase F: deterministic AST diagnostics and static-analysis sensors."""

from app.diagnostics.ast_rules import (
    ASTRule,
    ASTRuleRegistry,
    PatternMatch,
    RuleContext,
    default_registry,
)
from app.diagnostics.adapters import (
    AnalyzerAdapter,
    BanditAdapter,
    Flake8Adapter,
    PylintAdapter,
    RadonAdapter,
)
from app.diagnostics.contract import (
    Diagnostic,
    DiagnosticSeverity,
    SensorReport,
    SensorStatus,
)
from app.diagnostics.engine import ASTAnalyzer, analyze_ast
from app.diagnostics.patterns import ErrorPattern, map_diagnostics

__all__ = [
    "ASTAnalyzer",
    "ASTRule",
    "ASTRuleRegistry",
    "AnalyzerAdapter",
    "BanditAdapter",
    "Diagnostic",
    "DiagnosticSeverity",
    "ErrorPattern",
    "Flake8Adapter",
    "PatternMatch",
    "PylintAdapter",
    "RadonAdapter",
    "RuleContext",
    "SensorReport",
    "SensorStatus",
    "analyze_ast",
    "default_registry",
    "map_diagnostics",
]
