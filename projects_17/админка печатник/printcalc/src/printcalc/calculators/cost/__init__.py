"""Калькулятор Себестоимости (порт legacy «Калькулятор себестоимости»)."""

from __future__ import annotations

from printcalc.calculators.cost.compute import compute
from printcalc.calculators.cost.config import (
    PAPER_SIZES_MM,
    CostConfig,
    EconomicsDefaults,
    Equipment,
    MaterialSpec,
    default_equipment,
)
from printcalc.calculators.cost.spec import SPEC
from printcalc.engine.registry import CalculatorRegistry


def register(registry: CalculatorRegistry) -> None:
    """Регистрирует Себестоимость (со спекой и чистой функцией) в реестре."""
    registry.register(SPEC, compute)


__all__ = [
    "PAPER_SIZES_MM",
    "SPEC",
    "CostConfig",
    "EconomicsDefaults",
    "Equipment",
    "MaterialSpec",
    "compute",
    "default_equipment",
    "register",
]
