"""Чистая функция расчёта Riso — порт 1:1 RisographCalculator.calculate().

Источник: «Общий калькулятор печати/riso_calc.py», строки 644–760.
Порядок арифметических операций и float-семантика сохранены сознательно —
golden-тесты закрепляют паритет с legacy-EXE. GUI-ветки (messagebox)
заменены CalcInputError с теми же текстами; глобальные настройки
заменены инъекцией RisoConfig.
"""

from __future__ import annotations

from typing import Any, Mapping

from printcalc.calculators.riso.config import AREA_MULTIPLIERS, RisoConfig
from printcalc.engine.errors import CalcInputError
from printcalc.engine.result import CalcResult, CostLine

_SIDES_DUPLEX = 2


def compute(
    inputs: Mapping[str, Any], config: RisoConfig | None = None
) -> CalcResult:
    """Считает цену/себестоимость/прибыль Riso по входам и конфигу."""
    cfg = config if config is not None else RisoConfig()

    fmt = _str_input(inputs, "format")
    qty_raw = _num_input(inputs, "qty")
    orig = _num_input(inputs, "originals")

    # Паритет legacy (riso_calc.py:647-651): qty <= 0 или orig <= 0 — ошибка.
    if qty_raw <= 0 or orig <= 0:
        field_name = "qty" if qty_raw <= 0 else "originals"
        raise CalcInputError(field_name, "Количество и оригиналы должны быть > 0")

    # Минимальный заказ (riso_calc.py:654-658).
    min_order = int(float(cfg.min_order))
    used_min = False
    qty = qty_raw
    if qty < min_order:
        qty = float(min_order)
        used_min = True

    # Диапазон тиража (riso_calc.py:661-670).
    tier_name = _find_tier(cfg, qty)

    # Прайс (riso_calc.py:673-679).
    pair = cfg.prices.get((fmt, tier_name))
    if pair is None:
        raise CalcInputError(
            "format",
            f"Нет цены для формата {fmt} и диапазона {tier_name}. "
            "Добавьте её в настройках.",
        )

    duplex = _flag_input(inputs, "duplex")
    base_rate = pair.two if duplex else pair.one

    # Бумага/краска (riso_calc.py:681-697): членство проверяет конфиг.
    paper_name = _str_input(inputs, "paper")
    if paper_name not in cfg.paper_materials:
        raise CalcInputError("paper", "Выберите бумагу")
    color = _str_input(inputs, "color")
    if color not in cfg.ink_cost_per_sheet:
        raise CalcInputError("color", "Цветность не выбрана")

    amult = AREA_MULTIPLIERS.get(fmt, 1.0)
    paper_price_a4 = float(cfg.paper_materials[paper_name])
    ink_price_a4 = float(cfg.ink_cost_per_sheet[color])

    sides = _SIDES_DUPLEX if duplex else 1
    impressions = qty * sides

    # Себестоимость (riso_calc.py:700-705) — порядок операций сохранён.
    paper_cost = qty * paper_price_a4 * amult
    ink_cost = qty * ink_price_a4 * amult * sides
    master_count = orig * sides
    master_cost = master_count * cfg.master_cost
    work_cost = impressions / 1000.0 * cfg.work_cost_per_1000

    # Доп. услуги (riso_calc.py:707-718).
    extras = 0.0
    if _flag_input(inputs, "cutting"):
        extras += cfg.cutting_cost
    if _flag_input(inputs, "lamination"):
        extras += cfg.lamination_cost_per_sheet * qty
    if _flag_input(inputs, "folding"):
        extras += cfg.folding_cost_per_sheet * qty
    if _flag_input(inputs, "stapling"):
        extras += cfg.stapling_cost
    if _flag_input(inputs, "delivery"):
        extras += cfg.delivery_cost

    cost = paper_cost + ink_cost + master_cost + work_cost + extras

    # Цена (riso_calc.py:722-724): наценка только на мастеров+допы.
    markup = _num_input(inputs, "markup_percent", default=25.0) / 100.0
    price_no_tax = base_rate * qty + (master_cost + extras) * (1 + markup)
    price = price_no_tax / (1 - cfg.tax_rate)
    net_profit = price * (1 - cfg.tax_rate) - cost
    unit_price = price_no_tax / qty

    warnings: tuple[str, ...] = ()
    if used_min:
        warnings = (
            f"Применён минимальный заказ: учтено {qty:.0f} вместо {qty_raw:.0f}",
        )

    lines = (
        CostLine("Бумага", paper_cost),
        CostLine("Краска", ink_cost),
        CostLine("Мастер", master_cost),
        CostLine("Работа", work_cost),
        CostLine("Доп. услуги", extras),
        CostLine("Себестоимость", cost),
        CostLine("База (прайс × листы)", base_rate * qty),
        CostLine(
            f"Мастера и допы (+{markup * 100:.0f}%)",
            (master_cost + extras) * (1 + markup),
        ),
        CostLine("Цена без налога", price_no_tax),
        CostLine(f"Налог ({cfg.tax_rate * 100:.0f}%)", price - price_no_tax),
        CostLine("ИТОГО ЦЕНА", price),
    )

    details: dict[str, Any] = {
        "format": fmt,
        "paper": paper_name,
        "color": color,
        "duplex": duplex,
        "tier": tier_name,
        "base_rate": base_rate,
        "qty_entered": qty_raw,
        "qty": qty,
        "used_min": used_min,
        "sides": sides,
        "impressions": impressions,
        "master_count": master_count,
    }

    return CalcResult(
        calculator_id="riso",
        price=price,
        price_no_tax=price_no_tax,
        cost=cost,
        net_profit=net_profit,
        unit_price=unit_price,
        lines=lines,
        warnings=warnings,
        details=details,
    )


def _find_tier(cfg: RisoConfig, qty: float) -> str:
    """Ищет диапазон тиража; паритет текста ошибки legacy (строка 669)."""
    for tier in cfg.tiers:
        if qty >= tier.min and (tier.max is None or qty <= tier.max):
            return tier.name
    raise CalcInputError("qty", "Не найден диапазон тиража для указанного количества")


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
