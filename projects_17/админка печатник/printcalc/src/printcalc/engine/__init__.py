"""Публичный интерфейс движка printcalc.engine."""

from __future__ import annotations

from printcalc.engine.errors import CalcError, CalcInputError, RegistryError, ValidationIssue
from printcalc.engine.registry import CalculatorRegistry, calculate
from printcalc.engine.result import CalcResult, CostLine
from printcalc.engine.spec import CalculatorRegistration, CalculatorSpec, ComputeFn, FieldKind, FieldSpec
from printcalc.engine.validate import validate_inputs

__all__ = [
    "CalcError",
    "CalcInputError",
    "CalcResult",
    "CalculatorRegistration",
    "CalculatorRegistry",
    "CalculatorSpec",
    "ComputeFn",
    "CostLine",
    "FieldKind",
    "FieldSpec",
    "RegistryError",
    "ValidationIssue",
    "calculate",
    "validate_inputs",
]
