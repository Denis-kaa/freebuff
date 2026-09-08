"""Чистая функция расчёта табличек — порт 1:1 TableCalculator.calculate().

Источник: «Общий калькулятор печати/tablichki.py», строки 641–744.
Порядок арифметических операций и float-семантика сохранены сознательно —
golden-тесты закрепляют паритет с legacy-EXE.

Ключевые отличия от Riso (закреплены golden-тестами):
- налог в цене НЕ участвует: пары cost/sell уже содержат продажную цену,
  финальная цена клиенту = total_sell без деления на (1-tax);
- работа «за м²» (WORK_RATE) добавляется к себестоимости И продаже;
- обработка считается по единице работы: м² — от общей площади, пог.м —
  от общего периметра, «шт» — по введённому количеству;
- «Мин. цена заказа» поднимает продажную цену (total_sell), если та ниже.

GUI-ветки (messagebox) заменены CalcInputError; глобальные настройки —
инъекцией TablichkiConfig. Строки детализации — честные промежуточные суммы
групп, накопленные по ходу расчёта (в legacy себестоимость копилась одним
аккумулятором, а итог печатался в detail-блоке, строки 721–741).
"""

from __future__ import annotations

from typing import Any, Mapping

from printcalc.calculators.tablichki.config import TablichkiConfig, WorkPrice
from printcalc.calculators.tablichki.spec import WORK_SLUGS
from printcalc.engine.errors import CalcInputError
from printcalc.engine.result import CalcResult, CostLine

#: legacy-арифметика: см → м² (деление на 10000) и см → пог.м (на 100).
_SQCM_PER_SQM = 10000.0
_CM_PER_M = 100.0
_DOUBLE_SIDED = 2.0


def compute(
    inputs: Mapping[str, Any], config: TablichkiConfig | None = None
) -> CalcResult:
    """Считает закупку/продажу табличек по входам и конфигу."""
    cfg = config if config is not None else TablichkiConfig()

    width = _num_input(inputs, "width")
    height = _num_input(inputs, "height")
    qty = _num_input(inputs, "qty")
    for field_name in ("width", "height", "qty"):
        value = {"width": width, "height": height, "qty": qty}[field_name]
        if value <= 0:
            # Паритет legacy (tablichki.py:644-646): w/h/qty <= 0 — ошибка.
            raise CalcInputError(field_name, "Размеры и количество должны быть > 0")

    material = _member(inputs, "material", cfg.materials, "Материал не выбран")
    print_name = _member(inputs, "print", cfg.prints, "Печать не выбрана")
    mount = _member(inputs, "mount", cfg.mounts, "Крепёж не выбран")

    # Геометрия (tablichki.py:650-657) — порядок операций сохранён.
    area_one = (width * height) / _SQCM_PER_SQM
    total_area = area_one * qty
    perim_one = (width + height) * 2 / _CM_PER_M
    total_perim = perim_one * qty

    double_sided = _flag_input(inputs, "double_sided")
    side_multiplier = _DOUBLE_SIDED if double_sided else 1.0
    print_area = total_area * side_multiplier

    # Закупка/продажа (tablichki.py:659-671).
    total_cost = 0.0
    total_sell = 0.0
    mat_cost = cfg.materials[material].cost * total_area
    mat_sell = cfg.materials[material].sell * total_area
    print_cost = cfg.prints[print_name].cost * print_area
    print_sell = cfg.prints[print_name].sell * print_area
    mount_cost = cfg.mounts[mount].cost * qty
    mount_sell = cfg.mounts[mount].sell * qty
    total_cost += mat_cost + print_cost + mount_cost
    total_sell += mat_sell + print_sell + mount_sell

    # Обработка (tablichki.py:673-685): количество по единице работы.
    works_used: list[dict[str, Any]] = []
    works_cost = 0.0
    works_sell = 0.0
    for name, work in cfg.works.items():
        if not _flag_input(inputs, "work_" + _field_slug(name)):
            continue
        q = _work_quantity(inputs, name, work, total_area, total_perim)
        works_cost += work.cost * q
        works_sell += work.sell * q
        works_used.append({"name": name, "unit": work.unit, "qty": q})
    total_cost += works_cost
    total_sell += works_sell

    # Работа за м² (tablichki.py:687-689) + доставка/монтаж (691-695).
    rate_cost = cfg.work_rate_cost * total_area
    rate_sell = cfg.work_rate_sell * total_area
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

    # Мин. цена заказа (tablichki.py:697-699): поднимает продажную цену.
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
        "double_sided": double_sided,
        "area_one": area_one,
        "total_area": total_area,
        "total_perim": total_perim,
        "print_area": print_area,
        "material": material,
        "print": print_name,
        "mount": mount,
        "works": works_used,
        "delivery": delivery,
        "install": install,
        "used_min": used_min,
    }

    return CalcResult(
        calculator_id="tablichki",
        price=total_sell,
        price_no_tax=total_sell,  # налог в цене не участвует (legacy sell-пары)
        cost=total_cost,
        net_profit=profit,
        unit_price=total_sell / qty,
        lines=lines,
        warnings=warnings,
        details=details,
    )


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
        CostLine("Крепёж", mount_cost),
        CostLine("Обработка", works_cost),
        CostLine("Работа за м²", rate_cost),
    ]
    if delivery_cost:
        lines.append(CostLine("Доставка", delivery_cost))
    if install_cost:
        lines.append(CostLine("Монтаж", install_cost))
    lines.append(CostLine("Себестоимость", total_cost))
    lines.append(CostLine("ИТОГО ЦЕНА", total_sell))
    return tuple(lines)


def _work_quantity(
    inputs: Mapping[str, Any],
    name: str,
    work: WorkPrice,
    total_area: float,
    total_perim: float,
) -> float:
    """Количество для включённой работы по единице (tablichki.py:675-684)."""
    if work.unit == "m":
        return total_perim
    if work.unit == "шт":
        # В legacy строка количества появлялась только при включённом
        # чекбоксе (по умолчанию 1); здесь — optional-поле со default=1.
        return _num_input(inputs, "work_" + _field_slug(name) + "_qty", default=1.0)
    return total_area  # m2 — legacy-ветка else


def _field_slug(name: str) -> str:
    return WORK_SLUGS.get(name, name)


def _member(
    inputs: Mapping[str, Any],
    field_name: str,
    members: Mapping[str, object],
    message: str,
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
