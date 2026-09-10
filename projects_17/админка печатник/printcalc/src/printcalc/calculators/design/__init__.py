"""Калькулятор дизайна (порт legacy «Калькулятор макетов/design_calc.py»)."""

from __future__ import annotations

from printcalc.calculators.design.compute import compute
from printcalc.calculators.design.config import (
    LEVELS,
    WIDE_LEVELS,
    DesignConfig,
    DesignPriceItem,
    build_prices,
)
from printcalc.calculators.design.spec import SPEC
from printcalc.engine.registry import CalculatorRegistry


def register(registry: CalculatorRegistry) -> None:
    """Регистрирует Дизайн (со спекой и чистой функцией) в реестре."""
    registry.register(SPEC, compute)


__all__ = [
    "LEVELS",
    "SPEC",
    "WIDE_LEVELS",
    "DesignConfig",
    "DesignPriceItem",
    "build_prices",
    "compute",
    "register",
]
