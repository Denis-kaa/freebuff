"""Калькулятор ЧПУ-реза (порт legacy «Калькулятор фрезерной и лазерной резки»)."""

from __future__ import annotations

from printcalc.calculators.cnc.compute import compute
from printcalc.calculators.cnc.config import (
    CncConfig,
    CutRate,
    DEFAULT_MATERIAL_NAMES,
    MACHINES,
    SheetMaterial,
)
from printcalc.calculators.cnc.spec import SPEC
from printcalc.engine.registry import CalculatorRegistry


def register(registry: CalculatorRegistry) -> None:
    """Регистрирует ЧПУ (со спекой и чистой функцией) в реестре."""
    registry.register(SPEC, compute)


__all__ = [
    "CncConfig",
    "CutRate",
    "DEFAULT_MATERIAL_NAMES",
    "MACHINES",
    "SPEC",
    "SheetMaterial",
    "compute",
    "register",
]
