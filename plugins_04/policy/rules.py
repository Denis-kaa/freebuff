"""Policy rules — constraint evaluation (правило 11, User-Choice Override).

Каждое правило — предикат над runtime_info dict + PolicyContext.
Неизвестный rule_type — fail-closed (False).
"""

from __future__ import annotations

from typing import Any, Dict

from . import CapabilityPolicy, PolicyContext, PolicyRule  # noqa: F401 (re-export)


def evaluate_rule(
    rule: PolicyRule,
    runtime_info: Dict[str, Any],
    context: PolicyContext,
) -> bool:
    """Оценить constraint-правило для кандидата-runtime.

    Args:
        rule: PolicyRule (rule_type + params).
        runtime_info: {"name": str, "confidence": float, "latency_ms": int,
                       "flags": [str], ...} — известное о кандидате.
        context: контекст запроса (exclude, required_flags, max_latency_ms).

    Returns:
        True если кандидат проходит правило. Неизвестный тип — False.
    """
    name = str(runtime_info.get("name", ""))

    if rule.rule_type == "min_confidence":
        return float(runtime_info.get("confidence", 0.0)) >= float(
            rule.params.get("value", 0.0)
        )

    if rule.rule_type == "max_latency":
        latency = runtime_info.get("latency_ms", context.max_latency_ms)
        return float(latency) <= float(rule.params.get("value", context.max_latency_ms))

    if rule.rule_type == "exclude":
        banned = set(rule.params.get("runtimes", [])) | set(context.exclude)
        return name not in banned

    if rule.rule_type == "required_flags":
        required = set(rule.params.get("flags", []))
        have = set(runtime_info.get("flags", []))
        return required.issubset(have)

    # Fail-closed: неизвестное правило блокирует кандидата
    return False


def evaluate_all(
    constraints: list,
    runtime_info: Dict[str, Any],
    context: PolicyContext,
) -> bool:
    """Все правила должны пройти (AND). Constraints — PolicyRule или dict."""
    for c in constraints or []:
        rule = c if isinstance(c, PolicyRule) else PolicyRule(
            rule_type=str(c.get("rule_type", "unknown")),
            params=dict(c.get("params", {})),
        )
        if not evaluate_rule(rule, runtime_info, context):
            return False
    return True
