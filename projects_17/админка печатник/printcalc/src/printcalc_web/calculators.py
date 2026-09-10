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

from printcalc.calculators.cnc import CncConfig
from printcalc.calculators.cnc import register as register_cnc
from printcalc.calculators.design import DesignConfig
from printcalc.calculators.design import register as register_design
from printcalc.calculators.digital import DigitalConfig
from printcalc.calculators.digital import register as register_digital
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
from printcalc.calculators.sign import SignConfig
from printcalc.calculators.sign import register as register_sign
from printcalc.calculators.sign.config import COMPLEXITY_FACTORS, MOUNT_VARIANTS


@lru_cache(maxsize=1)
def get_registry() -> CalculatorRegistry:
    """Собирает реестр калькуляторов (Digital + Riso + таблички + широкоформат)."""
    registry = CalculatorRegistry()
    register_digital(registry)
    register_riso(registry)
    register_tablichki(registry)
    register_wide(registry)
    register_sign(registry)
    register_cnc(registry)
    register_design(registry)
    return registry


@lru_cache(maxsize=1)
def _digital_option_lists() -> dict[str, tuple[str, ...]]:
    """Допустимые наборы STRING-полей Digital из канонического конфига."""
    config = DigitalConfig()
    return {
        "product": tuple(t.name for t in config.templates),
        "paper": tuple(config.papers),
        "color": tuple(config.ink),
        "sheet_format": tuple(config.sheet_formats),
    }


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
def _sign_option_lists() -> dict[str, tuple[str, ...]]:
    """Допустимые наборы STRING-полей Вывесок из канонического конфига."""
    config = SignConfig()
    return {
        "product": tuple(config.product_model),
        "complexity": tuple(COMPLEXITY_FACTORS),
        "front_material": ("Авто", *tuple(config.materials)),
        "side_material": ("Авто", *tuple(config.materials)),
        "back_material": ("Авто", *tuple(config.materials)),
        "image_type": tuple(config.image_prices),
        "mounting": MOUNT_VARIANTS,
        "substrate_material": tuple(config.materials),
        "frame_material": tuple(config.frame_prices),
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


@lru_cache(maxsize=1)
def _cnc_option_lists() -> dict[str, tuple[str, ...]]:
    """Допустимые наборы полей ЧПУ из канонического конфига: материал +
    толщины по станку (legacy fillMaterialSelect/fillThicknessSelect)."""
    config = CncConfig()
    return {
        "material": config.material_names(),
        "thickness": tuple(
            str(t) for m in config.material_names() for t in config.thickness_options("laser", m)
        ),
    }


@lru_cache(maxsize=1)
def _design_option_lists() -> dict[str, tuple[str, ...]]:
    """Допустимые наборы полей Дизайна из канонического прайса:
    услуги (42), уровни/варианты и стороны (legacy-зависимые селекты)."""
    config = DesignConfig()
    return {
        "service": config.services(),
        "option": tuple(
            dict.fromkeys(item.option for item in config.prices if item.option)
        ),
    }


#: Резолверы опций STRING-полей по id калькулятора.
_OPTION_RESOLVERS: dict[str, Callable[[], dict[str, tuple[str, ...]]]] = {
    "digital": _digital_option_lists,
    "riso": _riso_option_lists,
    "tablichki": _tablichki_option_lists,
    "wide": _wide_option_lists,
    "sign": _sign_option_lists,
    "cnc": _cnc_option_lists,
    "design": _design_option_lists,
}


@lru_cache(maxsize=1)
def _min_order_hints() -> dict[str, str]:
    """Подсказки R5 (RESEARCH_ADOPTION_PLAN §5-Б.2): min_order КАК ЕСТЬ из
    канонических конфигов — показываем оператору ДО расчёта. Только
    ненулевые пороги; конфиг — единственный источник (ANTI-6b)."""
    digital = DigitalConfig()
    riso = RisoConfig()
    hints: dict[str, str] = {}
    if digital.min_order_price > 0:
        hints["digital"] = f"Минимальная сумма заказа: {digital.min_order_price:.0f} ₽"
    if riso.min_order > 0:
        hints["riso"] = f"Минимальный тираж: {riso.min_order:.0f} шт"
    return hints


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
        "hints": [_min_order_hints()[spec.id]] if spec.id in _min_order_hints() else [],
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
