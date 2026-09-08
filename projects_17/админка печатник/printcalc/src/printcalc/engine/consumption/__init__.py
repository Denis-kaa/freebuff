"""Движок производственного расхода материала и раскроя (ТЗ промт_печатник_3).

Публичный API:
    ConsumptionEngine().calculate(material, item, policy) → MaterialConsumptionResult

Разделение движков (ТЗ §33): Nesting (roll.py) → Consumption (engine.py) →
Cost (будущий слой, §32) → Pricing (существующие калькуляторы).
"""

from __future__ import annotations

from printcalc.engine.consumption.engine import ConsumptionEngine
from printcalc.engine.consumption.errors import CONSUMPTION_ERROR_CODES, ConsumptionError
from printcalc.engine.consumption.models import (
    CONSUMPTION_MODES,
    Layout,
    Material,
    MaterialConsumptionPolicy,
    MaterialConsumptionResult,
    Remnant,
)

__all__ = [
    "CONSUMPTION_ERROR_CODES",
    "CONSUMPTION_MODES",
    "ConsumptionEngine",
    "ConsumptionError",
    "Layout",
    "Material",
    "MaterialConsumptionPolicy",
    "MaterialConsumptionResult",
    "Remnant",
]
