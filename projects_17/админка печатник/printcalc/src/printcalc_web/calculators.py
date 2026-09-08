"""Мост printcalc_web → движок printcalc: реестр, спеки, результаты.

Реестр — единственный источник цен расчётных позиций: заказ пересчитывает
цены на сервере и не доверяет клиентским значениям. Опции STRING-полей
(format/paper/color у Riso) зависят от RisoConfig — для UI они достаются
из канонического конфига (Phase 3 заменит это динамическими ENUM).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from printcalc.calculators.riso import RisoConfig
from printcalc.calculators.riso import register as register_riso
from printcalc.calculators.riso.config import AREA_MULTIPLIERS
from printcalc.engine.registry import CalculatorRegistry
from printcalc.engine.result import CalcResult
from printcalc.engine.spec import CalculatorSpec, FieldKind


@lru_cache(maxsize=1)
def get_registry() -> CalculatorRegistry:
    """Собирает реестр калькуляторов Phase 1 (пока только Riso)."""
    registry = CalculatorRegistry()
    register_riso(registry)
    return registry


@lru_cache(maxsize=1)
def _riso_option_lists() -> dict[str, tuple[str, ...]]:
    """Допустимые наборы STRING-полей Riso из канонического конфига."""
    config = RisoConfig()
    return {
        "format": tuple(AREA_MULTIPLIERS),
        "paper": tuple(config.paper_materials),
        "color": tuple(config.ink_cost_per_sheet),
    }


def _field_to_dict(field_spec: Any, spec_id: str) -> dict[str, Any]:
    options: list[str] = list(field_spec.options)
    if spec_id == "riso" and field_spec.kind is FieldKind.STRING and not options:
        options = list(_riso_option_lists().get(field_spec.name, ()))
    return {
        "name": field_spec.name,
        "kind": field_spec.kind.value,
        "title": field_spec.title,
        "required": field_spec.required,
        "default": field_spec.default,
        "options": options,
        "min": field_spec.min_value,
        "max": field_spec.max_value,
        "unit": field_spec.unit,
    }


def spec_to_dict(spec: CalculatorSpec) -> dict[str, Any]:
    """Сериализует спеку калькулятора для schema-driven UI."""
    return {
        "id": spec.id,
        "title": spec.title,
        "version": spec.version,
        "fields": [_field_to_dict(field_spec, spec.id) for field_spec in spec.fields],
    }


def list_calculators() -> list[dict[str, Any]]:
    """Список калькуляторов реестра (для диалога расчёта)."""
    registry = get_registry()
    return [spec_to_dict(registration.spec) for calculator_id in registry.ids() for registration in [registry.get(calculator_id)]]


def result_to_dict(result: CalcResult) -> dict[str, Any]:
    """Сериализует CalcResult для API/UI."""
    return {
        "calculator_id": result.calculator_id,
        "price": result.price,
        "price_no_tax": result.price_no_tax,
        "cost": result.cost,
        "net_profit": result.net_profit,
        "unit_price": result.unit_price,
        "lines": [{"label": line.label, "amount": line.amount} for line in result.lines],
        "warnings": list(result.warnings),
        "details": dict(result.details),
    }
