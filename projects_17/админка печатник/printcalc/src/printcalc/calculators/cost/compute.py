"""Чистая функция расчёта Себестоимости — порт 1:1 calc_price_for_job().

Источник: «Калькулятор себестоимости/universal_calc.py», строки 449–587.
Ветвление по kind станка:
    wide       — qty в м²: материал ₽/м²×qty + чернила ink_per_unit·ink_per_ml×qty;
                 hours = qty/speed
    digital    — листы: custom-размер → раскладка floor по листу, листов =
                 ceil(qty/per_sheet); тонер = toner_per_page·₽/мл × ЛИСТОВ;
                 стандартный формат → qty листов, формат-материал ищется
                 подстрокой («А4» в имени), иначе масштаб от А4-шаблона
    offset     — как digital, но краска = (листов/1000)·(ink_per_1000/1000)·
                 ₽/л + МАСТЕР (мастер на задачу, не на лист)
    lamination — площадь = fmt_м²·qty; материал ₽/м²·площадь; consumables=0
Итог: total = материал + расходники + машина(час) + оператор(час) +
накладные(час); price = total·(1+markup/100). GUI-вызовы ValueError
заменены CalcInputError; отсутствующий материал → первый ключ (parity
строк 470–474).
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from printcalc.calculators.cost.config import (
    PAPER_SIZES_MM,
    CostConfig,
    Equipment,
    MaterialSpec,
)
from printcalc.engine.errors import CalcInputError
from printcalc.engine.result import CalcResult, CostLine


def compute(inputs: Mapping[str, Any], config: CostConfig | None = None) -> CalcResult:
    """Считает себестоимость и цену задачи по входам и конфигу."""
    cfg = config if config is not None else CostConfig()
    assert cfg.equipment is not None

    equipment_name = _str_input(inputs, "equipment")
    eq = cfg.equipment.get(equipment_name)
    if eq is None:
        raise CalcInputError("equipment", f"Неизвестный станок: «{equipment_name}»")

    qty = _num_input(inputs, "qty")
    if qty <= 0:
        raise CalcInputError("qty", "Тираж должен быть больше 0")

    material_name = inputs.get("material", "") or ""
    if not isinstance(material_name, str):
        raise CalcInputError("material", "ожидалась строка")

    # Брак (legacy 450–451): тираж умножается на (1 + waste%).
    waste_percent = cfg.economics.waste_percent
    eff_qty = qty * (1 + waste_percent / 100)

    # Накладные на машино-час (legacy 453–469).
    total_hours_all = cfg.total_machine_hours_per_month()
    if total_hours_all <= 0:
        raise CalcInputError("load_factor", "Коэффициент загрузки должен быть > 0")
    overhead_per_hour = cfg.economics.total_overhead / total_hours_all

    # Материал (legacy 470–474): не найден → первый ключ словаря.
    materials = eq.materials
    if material_name in materials:
        base_mat = materials[material_name]
    else:
        material_name = next(iter(materials))
        base_mat = materials[material_name]

    calc = _calc_by_kind(eq, base_mat, material_name, eff_qty, inputs)

    # Итог (legacy 571–575).
    machine_cost = eq.machine_hour_cost() * calc["hours"]
    labor_cost = cfg.economics.operator_rate * calc["hours"]
    overhead_cost = overhead_per_hour * calc["hours"]
    total = (
        calc["material_cost"]
        + calc["consumables"]
        + machine_cost
        + labor_cost
        + overhead_cost
    )
    price = total * (1 + cfg.economics.markup_percent / 100)

    lines: list[CostLine] = [
        CostLine(f"Материал ({calc['material_used']})", calc["material_cost"]),
        CostLine("Расходники", calc["consumables"]),
        CostLine("Станок (амортизация+сервис+эл-во)", machine_cost),
        CostLine("Оператор", labor_cost),
        CostLine("Накладные", overhead_cost),
        CostLine("Себестоимость", total),
        CostLine("ЦЕНА (с наценкой)", price),
    ]

    details: dict[str, Any] = {
        "equipment": equipment_name,
        "kind": eq.kind,
        "material": material_name,
        "qty": qty,
        "eff_qty": eff_qty,
        "waste_percent": waste_percent,
        "sheet_format": calc.get("fmt"),
        "material_used": calc["material_used"],
        "hours": calc["hours"],
        "sheets": calc.get("sheets"),
        "machine_hour_cost": eq.machine_hour_cost(),
        "overhead_per_hour": overhead_per_hour,
        "markup_percent": cfg.economics.markup_percent,
    }

    return CalcResult(
        calculator_id="cost",
        price=price,
        price_no_tax=price,  # legacy не добавляет налог поверх наценки
        cost=total,
        net_profit=price - total,
        unit_price=price / qty,
        lines=tuple(lines),
        details=details,
    )


def _calc_by_kind(
    eq: Equipment,
    base_mat: MaterialSpec,
    material_name: str,
    qty: float,
    inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Ветка расчёта по kind — порт 476–566 (возвращает компоненты задачи)."""
    if eq.kind == "wide":
        speed = base_mat.speed if base_mat.speed > 0 else eq.default_speed
        material_cost = base_mat.cost_unit * qty
        consumables = base_mat.ink_per_unit * eq.ink_per_ml * qty
        hours_needed = qty / speed if speed > 0 else 0.0
        return {
            "material_cost": material_cost,
            "consumables": consumables,
            "hours": hours_needed,
            "material_used": material_name,
            "fmt": None,
            "sheets": None,
        }

    # Листовые станки: нужен формат.
    fmt = inputs.get("sheet_format", "A4") or "A4"
    if not isinstance(fmt, str):
        raise CalcInputError("sheet_format", "ожидалась строка")
    if fmt not in PAPER_SIZES_MM:
        raise CalcInputError("sheet_format", f"Неизвестный формат: «{fmt}»")
    w_mm, h_mm = PAPER_SIZES_MM[fmt]
    sheet_area_m2 = (w_mm / 1000) * (h_mm / 1000)

    use_custom = inputs.get("use_custom", False) is True
    if use_custom and eq.kind in ("digital", "offset"):
        cw = _num_input(inputs, "custom_width")
        ch = _num_input(inputs, "custom_height")
        if cw <= 0 or ch <= 0:
            raise CalcInputError("custom_width", "Некорректный размер изделия")
        n_x = int(w_mm // cw)
        n_y = int(h_mm // ch)
        if n_x == 0 or n_y == 0:
            raise CalcInputError(
                "custom_width", f"Изделие не помещается на листе {fmt}"
            )
        per_sheet = n_x * n_y
        total_sheets = math.ceil(qty / per_sheet)
        material_cost = base_mat.cost_unit * total_sheets
        if eq.kind == "digital":
            consumables = eq.toner_per_page * eq.toner_price_per_ml * total_sheets
        else:
            ink_cost = (
                (total_sheets / 1000)
                * (eq.ink_per_1000 / 1000)
                * eq.ink_price_per_liter
            )
            consumables = ink_cost + eq.master_price
        hours_needed = total_sheets / base_mat.speed if base_mat.speed > 0 else 0.0
        return {
            "material_cost": material_cost,
            "consumables": consumables,
            "hours": hours_needed,
            "material_used": material_name,
            "fmt": f"{fmt} (по {per_sheet} шт/лист)",
            "sheets": total_sheets,
        }

    # Стандартный формат: материал ищется подстрокой формата (parity 504–510).
    exact = next(
        ((n, m) for n, m in eq.materials.items() if fmt.upper() in n.upper()), None
    )
    if exact is not None:
        t_name, t_mat = exact
        speed = t_mat.speed if t_mat.speed > 0 else eq.default_speed
        if eq.kind == "lamination":
            total_area = sheet_area_m2 * qty
            material_cost = t_mat.cost_unit * total_area
            consumables = 0.0
            hours_needed = total_area / speed if speed > 0 else 0.0
            sheets = None
        else:
            material_cost = t_mat.cost_unit * qty
            consumables = _sheet_consumables(eq, qty)
            hours_needed = qty / speed if speed > 0 else 0.0
            sheets = qty
        used = t_name
        used_fmt: str | None = fmt
    else:
        # Нет точного формата — масштаб от А4-шаблона (parity 524–562).
        template = next(
            ((n, m) for n, m in eq.materials.items() if "А4" in n.upper() or "A4" in n.upper()),
            None,
        )
        if template is None:
            first = next(iter(eq.materials))
            template = (first, eq.materials[first])
        tpl_name, tpl_mat = template
        tpl_fmt = next(
            (k for k in PAPER_SIZES_MM if k.upper() in tpl_name.upper()), "A4"
        )
        tpl_w, tpl_h = PAPER_SIZES_MM[tpl_fmt]
        tpl_area = (tpl_w / 1000) * (tpl_h / 1000)

        if eq.kind == "lamination":
            total_area = sheet_area_m2 * qty
            material_cost = tpl_mat.cost_unit * total_area
            consumables = 0.0
            hours_needed = total_area / tpl_mat.speed if tpl_mat.speed > 0 else 0.0
            sheets = None
        else:
            material_cost = tpl_mat.cost_unit * (sheet_area_m2 / tpl_area) * qty
            consumables = _sheet_consumables(eq, qty)
            hours_needed = qty / tpl_mat.speed if tpl_mat.speed > 0 else 0.0
            sheets = qty
        used = f"{tpl_name} (масштаб {fmt})"
        used_fmt = fmt

    return {
        "material_cost": material_cost,
        "consumables": consumables,
        "hours": hours_needed,
        "material_used": used,
        "fmt": used_fmt,
        "sheets": sheets,
    }


def _sheet_consumables(eq: Equipment, sheets: float) -> float:
    """Расходники листового станка на кол-во листов (legacy 516/519, 556/559)."""
    if eq.kind == "digital":
        return eq.toner_per_page * eq.toner_price_per_ml * sheets
    return (sheets / 1000) * (eq.ink_per_1000 / 1000) * eq.ink_price_per_liter + eq.master_price


def _num_input(inputs: Mapping[str, Any], name: str, default: float | None = None) -> float:
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
