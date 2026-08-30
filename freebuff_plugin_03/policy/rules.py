"""Policy Engine — rule evaluators.

Each evaluator receives a candidate runtime descriptor and the policy context,
then returns True if the candidate passes the rule.
"""

from __future__ import annotations

from typing import Any, Dict

from freebuff_plugin_03.policy.config import PolicyContext, PolicyRule


class RuleEvaluator:
    """Base class for policy rule evaluators."""

    def evaluate(self, rule: PolicyRule, runtime: Dict[str, Any], context: PolicyContext) -> bool:
        """Return True if the runtime satisfies the rule."""
        raise NotImplementedError  # pragma: no cover


class MaxLatencyEvaluator(RuleEvaluator):
    """Rejects runtimes whose latency exceeds the configured threshold."""

    def evaluate(self, rule: PolicyRule, runtime: Dict[str, Any], context: PolicyContext) -> bool:
        threshold = rule.params.get("value")
        if threshold is None:
            threshold = context.max_latency_ms
        latency = runtime.get("latency_ms")
        if latency is None or threshold is None:
            return True
        return int(latency) <= int(threshold)


class ExcludeEvaluator(RuleEvaluator):
    """Rejects runtimes listed in the rule or context exclude list."""

    def evaluate(self, rule: PolicyRule, runtime: Dict[str, Any], context: PolicyContext) -> bool:
        name = runtime.get("name", "")
        excluded = set(rule.params.get("runtimes", []))
        excluded.update(context.exclude)
        return name not in excluded


class RequiredFlagsEvaluator(RuleEvaluator):
    """Rejects runtimes that don't have all required flags."""

    def evaluate(self, rule: PolicyRule, runtime: Dict[str, Any], context: PolicyContext) -> bool:
        required = set(rule.params.get("flags", []))
        if not required:
            required = set(context.required_flags)
        if not required:
            return True
        flags = set(runtime.get("flags", []))
        return required.issubset(flags)


class MinConfidenceEvaluator(RuleEvaluator):
    """Rejects runtimes with confidence below the threshold."""

    def evaluate(self, rule: PolicyRule, runtime: Dict[str, Any], context: PolicyContext) -> bool:
        threshold = rule.params.get("value", 0.0)
        confidence = runtime.get("confidence", 1.0)
        return float(confidence) >= float(threshold)


# Registry of built-in evaluators
EVALUATORS: Dict[str, RuleEvaluator] = {
    "max_latency": MaxLatencyEvaluator(),
    "exclude": ExcludeEvaluator(),
    "required_flags": RequiredFlagsEvaluator(),
    "min_confidence": MinConfidenceEvaluator(),
}


def evaluate_rule(rule: PolicyRule, runtime: Dict[str, Any], context: PolicyContext) -> bool:
    """Evaluate a single policy rule against a runtime candidate."""
    evaluator = EVALUATORS.get(rule.rule_type)
    if evaluator is None:
        # Unknown rule type fails closed for safety
        return False
    return evaluator.evaluate(rule, runtime, context)
