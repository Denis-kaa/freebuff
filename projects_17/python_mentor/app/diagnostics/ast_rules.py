"""Deterministic AST rule registry and initial Python code detectors."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Callable, Iterable

from app.diagnostics.contract import Diagnostic, DiagnosticSeverity


@dataclass(frozen=True)
class RuleContext:
    """Source context shared by all AST rules."""

    filename: str
    competency_id: str | None = None


@dataclass(frozen=True)
class PatternMatch:
    """Intermediate rule finding before normalization into a Diagnostic."""

    pattern_id: str
    severity: DiagnosticSeverity
    line: int
    column: int
    message: str


RuleFunction = Callable[[ast.AST, RuleContext], Iterable[PatternMatch]]


@dataclass(frozen=True)
class ASTRule:
    """Named deterministic AST detector."""

    rule_id: str
    description: str
    default_severity: DiagnosticSeverity
    detector: RuleFunction

    def run(self, tree: ast.AST, context: RuleContext) -> tuple[Diagnostic, ...]:
        findings = []
        for match in self.detector(tree, context):
            findings.append(
                Diagnostic(
                    source="ast",
                    rule_id=self.rule_id,
                    pattern_id=match.pattern_id,
                    severity=match.severity,
                    file=context.filename,
                    line=match.line,
                    column=match.column,
                    message=match.message,
                    competency_id=context.competency_id,
                )
            )
        return tuple(findings)


class ASTRuleRegistry:
    """Ordered registry; duplicate rule ids are rejected."""

    def __init__(self, rules: Iterable[ASTRule] = ()) -> None:
        self._rules: dict[str, ASTRule] = {}
        for rule in rules:
            self.register(rule)

    def register(self, rule: ASTRule) -> None:
        if rule.rule_id in self._rules:
            raise ValueError(f"duplicate AST rule: {rule.rule_id}")
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> ASTRule:
        try:
            return self._rules[rule_id]
        except KeyError as exc:
            raise KeyError(f"unknown AST rule: {rule_id}") from exc

    def rules(self) -> tuple[ASTRule, ...]:
        return tuple(self._rules.values())

    def analyze(self, source: str, context: RuleContext) -> tuple[Diagnostic, ...]:
        tree = ast.parse(source, filename=context.filename)
        findings: list[Diagnostic] = []
        for rule in self.rules():
            findings.extend(rule.run(tree, context))
        return tuple(sorted(findings, key=Diagnostic.sort_key))


def _walk_with_depth(tree: ast.AST) -> Iterable[tuple[ast.AST, int]]:
    def visit(node: ast.AST, depth: int) -> Iterable[tuple[ast.AST, int]]:
        yield node, depth
        for child in ast.iter_child_nodes(node):
            yield from visit(child, depth + (1 if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.Match)) else 0))

    return visit(tree, 0)


def _mutable_default(tree: ast.AST, _: RuleContext) -> Iterable[PatternMatch]:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        defaults = [*node.args.defaults, *(item for item in node.args.kw_defaults if item is not None)]
        for default in defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                yield PatternMatch(
                    "mutable-default-argument",
                    DiagnosticSeverity.HIGH,
                    default.lineno,
                    default.col_offset,
                    "mutable default argument is evaluated once and shared between calls",
                )


def _bare_except(tree: ast.AST, _: RuleContext) -> Iterable[PatternMatch]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            yield PatternMatch(
                "bare-except",
                DiagnosticSeverity.MEDIUM,
                node.lineno,
                node.col_offset,
                "bare except catches system-exiting exceptions and hides failure causes",
            )


def _excessive_nesting(tree: ast.AST, _: RuleContext) -> Iterable[PatternMatch]:
    threshold = 4
    for node, depth in _walk_with_depth(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.Match)) and depth > threshold:
            yield PatternMatch(
                "excessive-nesting",
                DiagnosticSeverity.MEDIUM,
                node.lineno,
                node.col_offset,
                f"control-flow nesting depth {depth} exceeds {threshold}",
            )


def _suspicious_mutable_state(tree: ast.AST, _: RuleContext) -> Iterable[PatternMatch]:
    if not isinstance(tree, ast.Module):
        return
    for node in tree.body:
        is_mutable_assignment = isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(
            node.value,
            (ast.List, ast.Dict, ast.Set),
        )
        if is_mutable_assignment:
            yield PatternMatch(
                "mutable-module-state",
                DiagnosticSeverity.LOW,
                node.lineno,
                node.col_offset,
                "mutable module-level state can make behavior depend on call history",
            )


def _shadowing(tree: ast.AST, _: RuleContext) -> Iterable[PatternMatch]:
    builtin_names = {"list", "dict", "set", "str", "int", "float", "len", "sum", "id", "type", "input"}
    for node in ast.walk(tree):
        names: list[ast.Name] = []
        if isinstance(node, ast.Assign):
            names = [target for target in node.targets if isinstance(target, ast.Name)]
        elif isinstance(node, ast.arg):
            names = [ast.Name(id=node.arg, ctx=ast.Load(), lineno=node.lineno, col_offset=node.col_offset)]
        for name in names:
            if name.id in builtin_names:
                yield PatternMatch(
                    "builtin-shadowing",
                    DiagnosticSeverity.LOW,
                    name.lineno,
                    name.col_offset,
                    f"assignment shadows built-in name '{name.id}'",
                )


def _unreachable_code(tree: ast.AST, _: RuleContext) -> Iterable[PatternMatch]:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.For, ast.While, ast.If, ast.With, ast.Try)):
            continue
        body = getattr(node, "body", ())
        terminated = False
        for statement in body:
            if terminated:
                yield PatternMatch(
                    "unreachable-code",
                    DiagnosticSeverity.MEDIUM,
                    statement.lineno,
                    statement.col_offset,
                    "statement cannot execute because the previous statement terminates this block",
                )
            if isinstance(statement, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                terminated = True


def _oversized_function(tree: ast.AST, _: RuleContext) -> Iterable[PatternMatch]:
    threshold = 40
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno is not None:
            size = node.end_lineno - node.lineno + 1
            if size > threshold:
                yield PatternMatch(
                    "oversized-function",
                    DiagnosticSeverity.MEDIUM,
                    node.lineno,
                    node.col_offset,
                    f"function spans {size} lines and exceeds {threshold}",
                )


def default_registry() -> ASTRuleRegistry:
    """Return the stable Phase F rule set in deterministic order."""

    return ASTRuleRegistry(
        (
            ASTRule("AST001", "mutable default argument", DiagnosticSeverity.HIGH, _mutable_default),
            ASTRule("AST002", "bare except", DiagnosticSeverity.MEDIUM, _bare_except),
            ASTRule("AST003", "excessive control-flow nesting", DiagnosticSeverity.MEDIUM, _excessive_nesting),
            ASTRule("AST004", "suspicious mutable module state", DiagnosticSeverity.LOW, _suspicious_mutable_state),
            ASTRule("AST005", "obvious builtin shadowing", DiagnosticSeverity.LOW, _shadowing),
            ASTRule("AST006", "unreachable code", DiagnosticSeverity.MEDIUM, _unreachable_code),
            ASTRule("AST007", "oversized function", DiagnosticSeverity.MEDIUM, _oversized_function),
        )
    )
