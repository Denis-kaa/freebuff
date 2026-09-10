"""Калькулятор вывесок (порт legacy sign_calc.py)."""

from __future__ import annotations

from printcalc.calculators.sign.compute import compute
from printcalc.calculators.sign.config import SignConfig
from printcalc.calculators.sign.spec import SPEC
from printcalc.engine.registry import CalculatorRegistry


def register(registry: CalculatorRegistry) -> None:
    """Регистрирует Вывески (со спекой и чистой функцией) в реестре."""
    registry.register(SPEC, compute)


__all__ = ["SPEC", "SignConfig", "compute", "register"]
