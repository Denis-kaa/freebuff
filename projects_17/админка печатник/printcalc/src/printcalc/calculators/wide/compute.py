"""Чистая функция расчёта широкоформата — порт 1:1 WideFormatApp.calculate().

Источник: «Общий калькулятор печати/wide_format.py», строки 660–756.
Порядок арифметических операций и float-семантика сохранены сознательно —
golden-тесты закрепляют паритет с legacy-EXE.

Ключевые отличия от табличек/Riso (закреплены golden-тестами):
- ТИРОВАНЫЙ прайс: материал и печать — ₽/м², тир выбирается по ОБЩЕЙ площади
  тиража (area <= max, верхняя граница включительно — get_price:112-122);
  неизвестное имя в legacy НЕ падает, а даёт (0, 0) — «бесплатно»;
- крепёж (монтаж) — ФИКС за заказ: НЕ умножается на тираж (legacy 676-677);
- люверсы (is_grommet, «шт»): per_one = ceil(периметр одной шт в см / интервал),
  общее количество = per_one × тираж (legacy 700-709); интервал <= 0 — ошибка
  (в legacy messagebox + возврат без расчёта);
- остальные работы: m2 — общая площадь, m — общий периметр (× тираж),
  «шт» без is_grommet — тираж;
- «работа за м²» (WORK_RATE) добавляется к себестоимости И продаже;
- мин. сумма заказа поднимает продажную цену (total_sell), если та ниже.

GUI-ветки (messagebox) заменены CalcInputError; глобальные настройки —
инъекцией WideConfig.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from printcalc.calculators.wide.config import PriceTier, WideConfig, WorkPrice
from printcalc.calculators.wide.spec import WORK_SLUGS
from printcalc.engine.errors import CalcInputError
from printcalc.engine.result import CalcResult, CostLine

#: legacy-арифметика: см² → м² (wide_format.py:665) и см → пог.м (671).
_SQCM_PER_SQM = 10000.0
_CM_PER_M = 100.0


def compute(inputs: Mapping[str, Any], config: WideConfig | None = None) -> CalcResult:
    """Считает закупку/продажу широкоформата по входам и конфигу."""
    cfg = config if config is not None else WideConfig()

    width = _num_input(inputs, "width")
    height = _num_input(inputs, "height")
    qty = _num_input(inputs, "qty")
    for field_name, value in (("width", width), ("height", height), ("qty", qty)):
        if value <= 0:
            # Паритет legacy (wide_format.py:666-668): w/h/qty <= 0 — ошибка.
            raise CalcInputError(field_name, "Размеры должны быть > 0")

    material = _tier_name_input(inputs, "material", cfg.material_names, "Материал")
    print_name = _tier_name_input(inputs, "print", cfg.print_names, "Печать")
    mount = _member(inputs, "mount", cfg.mount_names, "Монтаж не выбран")

    # Геометрия (wide_format.py:665, 671): площадь тиража и общий периметр.
    area = (width * height) / _SQCM_PER_SQM * qty
    perim_cm_one = (width + height) * 2
    perim_m_total = perim_cm_one / _CM_PER_M * qty

    # Тированный прайс (wide_format.py:667-669).
    mat_c, mat_s = _get_price(cfg.materials, material, area)
    prn_c, prn_s = _get_price(cfg.prints, print_name, area)
    mount_row = next((m for m in cfg.mounts if m.name == mount), None)
    if mount_row is None:
        raise CalcInputError("mount", "Монтаж не выбран")

    total_cost = 0.0
    total_sell = 0.0

    # Материал + печать по площади (wide_format.py:676-679).
    mat_cost = mat_c * area
    mat_sell = mat_s * area
    print_cost = prn_c * area
    print_sell = prn_s * area
    total_cost += mat_cost + print_cost
    total_sell += mat_sell + print_sell

    # Крепёж — фикс за заказ (wide_format.py:680-681).
    mount_cost = mount_row.cost
    mount_sell = mount_row.sell
    total_cost += mount_cost
    total_sell += mount_sell

    # Доп. работы (wide_format.py:684-709).
    works_cost = 0.0
    works_sell = 0.0
    works_used: list[dict[str, Any]] = []
    for work in cfg.works:
        if not _flag_input(inputs, "work_" + _field_slug(work.name)):
            continue
        q = _work_quantity(inputs, work, width, height, qty, perim_cm_one, perim_m_total, area)
        works_cost += work.cost * q
        works_sell += work.sell * q
        works_used.append({"name": work.name, "unit": work.unit, "qty": q})
    total_cost += works_cost
    total_sell += works_sell

    # Работа за м² (wide_format.py:711-713) + доставка/монтаж (716-721).
    rate_cost = cfg.work_rate_cost * area
    rate_sell = cfg.work_rate_sell * area
    total_cost += rate_cost
    total_sell += rate_sell

    delivery = _flag_input(inputs, "delivery")
    if delivery:
        total_cost += cfg.delivery_cost
        total_sell += cfg.delivery_sell
    install = _flag_input(inputs, "install")
    if install:
        total_cost += cfg.install_cost
        total_sell += cfg.install_sell

    # Мин. сумма заказа (wide_format.py:724-733): поднимает продажную цену.
    used_min = False
    if total_sell < cfg.min_order_price:
        total_sell = cfg.min_order_price
        used_min = True

    profit = total_sell - total_cost

    warnings: tuple[str, ...] = ()
    if used_min:
        warnings = (f"Цена поднята до минимальной: {cfg.min_order_price:g} ₽",)

    lines = _detail_lines(
        mat_cost=mat_cost,
        print_cost=print_cost,
        mount_cost=mount_cost,
        works_cost=works_cost,
        rate_cost=rate_cost,
        delivery_cost=cfg.delivery_cost if delivery else 0.0,
        install_cost=cfg.install_cost if install else 0.0,
        total_cost=total_cost,
        total_sell=total_sell,
    )

    details: dict[str, Any] = {
        "width": width,
        "height": height,
        "qty": qty,
        "area_total": area,
        "perim_m_total": perim_m_total,
        "material": material,
        "print": print_name,
        "mount": mount,
        "works": works_used,
        "delivery": delivery,
        "install": install,
        "used_min": used_min,
    }

    return CalcResult(
        calculator_id="wide",
        price=total_sell,
        price_no_tax=total_sell,  # налог в цене не участвует (legacy sell-пары)
        cost=total_cost,
        net_profit=profit,
        unit_price=total_sell / qty,
        lines=lines,
        warnings=warnings,
        details=details,
    )


def _get_price(
    tiers: tuple[PriceTier, ...], name: str, area: float
) -> tuple[float, float]:
    """Тир по площади — порт legacy get_price (wide_format.py:112-122).

    Сортировка по min_area, первый тир с max is None или area <= max;
    ничего не сошлось → последний тир (по сортировке); неизвестное имя → (0, 0).
    """
    rows = sorted((t for t in tiers if t.name == name), key=lambda t: t.min_area)
    if not rows:
        return (0.0, 0.0)
    for tier in rows:
        if tier.max_area is None or area <= tier.max_area:
            return (tier.cost, tier.sell)
    return (rows[-1].cost, rows[-1].sell)


def _work_quantity(
    inputs: Mapping[str, Any],
    work: WorkPrice,
    width: float,
    height: float,
    qty: float,
    perim_cm_one: float,
    perim_m_total: float,
    area: float,
) -> float:
    """Количество для включённой работы (wide_format.py:686-709)."""
    if work.unit == "m2":
        return area
    if work.unit == "m":
        return perim_m_total
    # «шт»
    if work.is_grommet:
        step = _num_input(inputs, "grommet_interval", default=None)
        if step <= 0:
            # Паритет legacy (wide_format.py:702-706): интервал <= 0 — ошибка.
            raise CalcInputError(
                "grommet_interval", "Интервал люверсов должен быть положительным числом (см)."
            )
        per_one = math.ceil(perim_cm_one / step)
        return float(per_one * qty)
    return qty


def _detail_lines(
    *,
    mat_cost: float,
    print_cost: float,
    mount_cost: float,
    works_cost: float,
    rate_cost: float,
    delivery_cost: float,
    install_cost: float,
    total_cost: float,
    total_sell: float,
) -> tuple[CostLine, ...]:
    """Строки итога для UI: группы + себестоимость + цена клиенту."""
    lines = [
        CostLine("Материал", mat_cost),
        CostLine("Печать", print_cost),
        CostLine("Монтаж", mount_cost),
        CostLine("Доп. работы", works_cost),
        CostLine("Работа за м²", rate_cost),
    ]
    if delivery_cost:
        lines.append(CostLine("Доставка", delivery_cost))
    if install_cost:
        lines.append(CostLine("Монтаж (флаг)", install_cost))
    lines.append(CostLine("Себестоимость", total_cost))
    lines.append(CostLine("ИТОГО ЦЕНА", total_sell))
    return tuple(lines)


def _field_slug(name: str) -> str:
    return WORK_SLUGS.get(name, name)


def _tier_name_input(
    inputs: Mapping[str, Any],
    field_name: str,
    names: Mapping[str, bool],
    label: str,
) -> str:
    """Имя тира: неизвестное значение НЕ падает — legacy get_price вернёт (0, 0)."""
    value = _str_input(inputs, field_name)
    if value not in names:
        # Паритет legacy: неизвестное имя → цена 0 (wide_format.py:114-115).
        return value
    return value


def _member(
    inputs: Mapping[str, Any], field_name: str, members: Mapping[str, bool], message: str
) -> str:
    value = _str_input(inputs, field_name)
    if value not in members:
        raise CalcInputError(field_name, message)
    return value


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
    value = inputs[name]
    if not isinstance(value, str):
        raise CalcInputError(name, "ожидалась строка")
    return value


def _flag_input(inputs: Mapping[str, Any], name: str) -> bool:
    value = inputs.get(name, False)
    if not isinstance(value, bool):
        raise CalcInputError(name, "ожидался логический флаг (true/false)")
    return value
