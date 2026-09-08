"""Калькулятор ризографии RISO RZ300EP (порт legacy riso_calc.py)."""

from __future__ import annotations

from printcalc.calculators.riso.compute import compute
from printcalc.calculators.riso.config import RisoConfig
from printcalc.calculators.riso.spec import SPEC
from printcalc.engine.registry import CalculatorRegistry


def register(registry: CalculatorRegistry) -> None:
    """Регистрирует Riso (со спекой и чистой функцией) в реестре."""
    registry.register(SPEC, compute)


__all__ = ["SPEC", "RisoConfig", "compute", "register"]
