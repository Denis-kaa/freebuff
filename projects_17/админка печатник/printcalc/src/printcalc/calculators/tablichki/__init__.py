"""Калькулятор табличек (порт legacy tablichki.py, «Общий калькулятор печати»)."""

from __future__ import annotations

from printcalc.calculators.tablichki.compute import compute
from printcalc.calculators.tablichki.config import TablichkiConfig
from printcalc.calculators.tablichki.spec import SPEC
from printcalc.engine.registry import CalculatorRegistry


def register(registry: CalculatorRegistry) -> None:
    """Регистрирует калькулятор табличек (со спекой и чистой функцией)."""
    registry.register(SPEC, compute)


__all__ = ["SPEC", "TablichkiConfig", "compute", "register"]
