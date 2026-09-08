"""Мост printcalc_web → движок printcalc: реестр, спеки, результаты.

Реестр — единственный источник цен расчётных позиций: заказ пересчитывает
цены на сервере и не доверяет клиентским значениям. Опции STRING-полей
(format/paper/color у Riso, material/print/mount у табличек) зависят от
канонического конфига калькулятора — для UI они достаются из конфига через
per-calculator резолвер (Phase 3 заменит это динамическими ENUM).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable

from printcalc.calculators.riso import RisoConfig
from printcalc.calculators.riso import register as register_riso
from printcalc.calculators.riso.config import AREA_MULTIPLIERS
from printcalc.calculators.tablichki import TablichkiConfig
from printcalc.calculators.tablichki import register as register_tablichki
from printcalc.calculators.wide import WideConfig
from printcalc.calculators.wide import register as register_wide
from printcalc.engine.registry import CalculatorRegistry
from printcalc.engine.result import CalcResult
from printcalc.engine.spec import CalculatorSpec, FieldKind, FieldSpec


@lru_cache(maxsize=1)
def get_registry() -> CalculatorRegistry:
    """Собирает реестр калькуляторов (Riso + таблички + широкоформат)."""
    registry = CalculatorRegistry()
    register_riso(registry)
    register_tablichki(registry)
    register_wide(registry)
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


@lru_cache(maxsize=1)
def _tablichki_option_lists() -> dict[str, tuple[str, ...]]:
    """Допустимые наборы STRING-полей табличек из канонического конфига."""
    config = TablichkiConfig()
    return {
        "material": tuple(config.materials),
        "print": tuple(config.prints),
        "mount": tuple(config.mounts),
    }


@lru_cache(maxsize=1)
def _wide_option_lists() -> dict[str, tuple[str, ...]]:
    """Допустимые наборы STRING-полей широкоформата из канонического конфига."""
    config = WideConfig()
    return {
        "material": tuple(config.material_names),
        "print": tuple(config.print_names),
        "mount": tuple(config.mount_names),
    }


#: Резолверы опций STRING-полей по id калькулятора.
_OPTION_RESOLVERS: dict[str, Callable[[], dict[str, tuple[str, ...]]]] = {
    "riso": _riso_option_lists,
    "tablichki": _tablichki_option_lists,
    "wide": _wide_option_lists,
}


def _field_to_dict(field_spec: FieldSpec, spec_id: str) -> dict[str, Any]:
    options: list[str] = list(field_spec.options)
    if field_spec.kind is FieldKind.STRING and not options:
        resolver = _OPTION_RESOLVERS.get(spec_id)
        if resolver is not None:
            options = list(resolver().get(field_spec.name, ()))
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
    return [
        spec_to_dict(registry.get(calculator_id).spec)
        for calculator_id in registry.ids()
    ]


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
