"""Калькулятор цифровой печати (порт legacy calc_digital.py)."""

from __future__ import annotations

from printcalc.calculators.digital.compute import compute
from printcalc.calculators.digital.config import DigitalConfig
from printcalc.calculators.digital.spec import SPEC
from printcalc.engine.registry import CalculatorRegistry


def register(registry: CalculatorRegistry) -> None:
    """Регистрирует Digital (со спекой и чистой функцией) в реестре."""
    registry.register(SPEC, compute)


__all__ = ["SPEC", "DigitalConfig", "compute", "register"]
