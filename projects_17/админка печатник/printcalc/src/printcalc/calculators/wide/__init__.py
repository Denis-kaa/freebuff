"""Калькулятор широкоформатной печати (порт legacy wide_format.py, «Общий калькулятор печати»)."""

from __future__ import annotations

from printcalc.calculators.wide.compute import compute
from printcalc.calculators.wide.config import WideConfig
from printcalc.calculators.wide.spec import SPEC
from printcalc.engine.registry import CalculatorRegistry


def register(registry: CalculatorRegistry) -> None:
    """Регистрирует калькулятор широкоформата (со спекой и чистой функцией)."""
    registry.register(SPEC, compute)


__all__ = ["SPEC", "WideConfig", "compute", "register"]
