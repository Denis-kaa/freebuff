"""Чистая функция расчёта ЧПУ-реза — порт 1:1 updatePrice().

Источник: «Калькулятор фрезерной и лазерной резки/cnc_calc.py»,
строки 397–427. Формулы:
    cut_price      = cut_length × rate.price_per_meter × qty   (если ставка есть)
    material_price = width × height × material.price_per_sqm × qty
                     (если материал найден и W>0 и L>0)
    ИТОГО          = cut_price + material_price
Legacy НЕ добавляет наценку/налог/минималку — parity сохранён: price ==
price_no_tax == сумма строк, cost == сумма, net_profit == 0. Ветка «нет
ставки» (rate is None) не ошибка: рез = 0 + warning «нет ставки»
(legacy cut_text = 'нет ставки'). Ключи станка — machine-id legacy
(laser/frezer); человекочитаемое имя — из MACHINES.
"""

from __future__ import annotations

from typing import Any, Mapping

from printcalc.calculators.cnc.config import MACHINES, CncConfig
from printcalc.engine.errors import CalcInputError
from printcalc.engine.result import CalcResult, CostLine

_MACHINE_TITLES: dict[str, str] = dict(MACHINES)


def compute(inputs: Mapping[str, Any], config: CncConfig | None = None) -> CalcResult:
    """Считает цену ЧПУ-реза по входам и конфигу (паритет legacy)."""
    cfg = config if config is not None else CncConfig()

    machine = _str_input(inputs, "machine")
    if machine not in _MACHINE_TITLES:
        raise CalcInputError("machine", f"Неизвестный станок: «{machine}»")

    material_name = _str_input(inputs, "material")
    thickness = _num_input(inputs, "thickness")
    if thickness <= 0:
        raise CalcInputError("thickness", "Толщина должна быть больше 0")

    cut_length = _num_input(inputs, "cut_length", default=0.0)
    if cut_length < 0:
        raise CalcInputError("cut_length", "Длина реза не может быть отрицательной")

    qty = _num_input(inputs, "qty")
    if qty <= 0:
        raise CalcInputError("qty", "Количество должно быть больше 0")

    width = _num_input(inputs, "product_width", default=0.0)
    height = _num_input(inputs, "product_height", default=0.0)
    if width < 0 or height < 0:
        raise CalcInputError("product_width", "Размеры изделия не могут быть отрицательными")

    # Рез (legacy 402–408): ставка не найдена → 0 + пометка, НЕ ошибка.
    rate = cfg.rate(machine, material_name, thickness)
    cut_price = 0.0
    warnings: list[str] = []
    if rate is not None:
        cut_price = cut_length * rate.price_per_meter * qty
    else:
        warnings.append(
            f"Нет ставки реза: {_MACHINE_TITLES[machine]} / {material_name} / {thickness} мм"
        )

    # Материал (legacy 410–418): материал ищется по имени+толщине независимо
    # от ставки; считается только при W>0 и L>0.
    material = cfg.material(material_name, thickness)
    material_price = 0.0
    if material is not None and width > 0 and height > 0:
        area = width * height
        material_price = area * material.price_per_sqm * qty
    elif material is None:
        warnings.append(
            f"Материал не найден в справочнике: {material_name} / {thickness} мм"
        )

    total = cut_price + material_price

    lines: list[CostLine] = [
        CostLine(
            "Рез ("
            + _MACHINE_TITLES[machine]
            + f", {material_name} {thickness:g} мм)",
            cut_price,
        ),
        CostLine(f"Материал ({material_name} {thickness:g} мм)", material_price),
        CostLine("ИТОГО", total),
    ]

    details: dict[str, Any] = {
        "machine": machine,
        "machine_title": _MACHINE_TITLES[machine],
        "material": material_name,
        "thickness": thickness,
        "cut_length_m": cut_length,
        "qty": qty,
        "price_per_meter": rate.price_per_meter if rate is not None else None,
        "price_per_sqm": material.price_per_sqm if material is not None else None,
        "area_sqm": width * height,
        "cut_price": cut_price,
        "material_price": material_price,
        "has_rate": rate is not None,
        "has_material": material is not None,
    }

    return CalcResult(
        calculator_id="cnc",
        price=total,
        price_no_tax=total,
        cost=total,
        net_profit=0.0,
        unit_price=total / qty,
        lines=tuple(lines),
        warnings=tuple(warnings),
        details=details,
    )


def _num_input(
    inputs: Mapping[str, Any], name: str, default: float | None = None
) -> float:
    if name not in inputs:
        if default is not None:
            return default
        raise CalcInputError(name, "обязательное поле не задано")
    value = inputs[name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalcInputError(name, "ожидалось число")
    return float(value)


def _str_input(inputs: Mapping[str, Any], name: str) -> str:
    if name not in inputs:
        raise CalcInputError(name, "обязательное поле не задано")
    value = inputs[name]
    if not isinstance(value, str):
        raise CalcInputError(name, "ожидалась строка")
    return value


__all__ = ["compute"]
