"""Чистая функция расчёта Digital — порт 1:1 DigitalPolyCalc.calculate().

Источник: «Общий калькулятор печати/build_all/calc_digital.py», строки
349–455. Порядок арифметических операций и float-семантика сохранены
сознательно — golden-тесты закрепляют паритет с legacy-EXE. GUI-ветки
(messagebox) заменены CalcInputError с теми же текстами; глобальные
настройки и JSON-конфиг заменены инъекцией DigitalConfig.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from printcalc.calculators.digital.config import DigitalConfig
from printcalc.engine.errors import CalcInputError
from printcalc.engine.result import CalcResult, CostLine

#: Ключ extras-поля spec → key операции legacy (STANDARD_OPERATIONS).
_EXTRA_FIELDS: tuple[tuple[str, str], ...] = (
    ("extras_lamination", "lamination"),
    ("extras_folding", "folding"),
    ("extras_cutting", "cutting"),
    ("extras_rounding", "rounding"),
    ("extras_staple", "staple"),
    ("extras_spring", "spring"),
)


def compute(
    inputs: Mapping[str, Any], config: DigitalConfig | None = None
) -> CalcResult:
    """Считает цену/себестоимость/прибыль Digital по входам и конфигу."""
    cfg = config if config is not None else DigitalConfig()

    product = _str_input(inputs, "product")
    copies = _num_input(inputs, "copies")
    pages = _num_input(inputs, "pages")
    item_w = _num_input(inputs, "width")
    item_h = _num_input(inputs, "height")
    sheet_format = _str_input(inputs, "sheet_format")

    # Тираж (legacy 354-357: copies <= 0 — ошибка).
    if copies <= 0:
        raise CalcInputError("copies", "Тираж должен быть больше 0")

    # Прайс изделия (legacy 359-366 + _get_product_price 335-346).
    price_per_item = _get_product_price(cfg, product, copies)

    # Плотность раскладки (legacy 367-373 + calc_density 315-330).
    density = _calc_density(cfg, item_w, item_h, sheet_format)
    if density <= 0:
        raise CalcInputError(
            "sheet_format", "Изделие не помещается на выбранный лист"
        )

    duplex = _flag_input(inputs, "duplex")

    # Листы (legacy 375-383).
    int_pages = int(pages)
    sheets: float
    if int_pages <= 1:
        sheets = math.ceil(copies / density)
    elif duplex:
        sheets = math.ceil(int_pages / 2) * copies
    else:
        sheets = int_pages * copies
    total_sheets = sheets

    # Доход от печати (legacy 386).
    print_income = price_per_item * copies

    # Материалы (legacy 388-399).
    area_mult = cfg.sheet_area_multiplier(sheet_format)
    paper_name = _str_input(inputs, "paper")
    if paper_name not in cfg.papers:
        raise CalcInputError("paper", "Выберите бумагу")
    color = _str_input(inputs, "color")
    if color not in cfg.ink:
        raise CalcInputError("color", "Цветность не выбрана")

    paper_cost = float(cfg.papers[paper_name]) * area_mult * total_sheets

    ink_per_sheet = float(cfg.ink[color]) * area_mult
    if duplex:
        ink_per_sheet *= 2
    ink_cost = ink_per_sheet * total_sheets

    # Доп. операции (legacy 402-415): чекбоксы → себестоимость.
    extras_cost = 0.0
    extras_lines: list[CostLine] = []
    extras_on: list[str] = []
    for field_name, op_key in _EXTRA_FIELDS:
        if not _flag_input(inputs, field_name):
            continue
        op = next((o for o in cfg.operations if o.key == op_key), None)
        if op is None:
            continue
        extras_on.append(op.label)
        if op.unit == "лист":
            cost = op.price * area_mult * total_sheets
        elif op.unit == "копия":
            cost = op.price * copies
        else:
            cost = op.price
        extras_cost += cost
        extras_lines.append(CostLine(op.label, cost))

    setup_cost = cfg.setup_cost
    full_cost = paper_cost + ink_cost + extras_cost + setup_cost

    # Цена (legacy 419-424): наценка на допы + подготовку; печать — прайс.
    markup = _num_input(inputs, "markup_percent", default=cfg.markup_default) / 100.0
    extras_income = (extras_cost + setup_cost) * (1 + markup)
    price_no_tax = print_income + extras_income

    # Минимальный заказ (legacy 425-428).
    min_applied = False
    if price_no_tax < cfg.min_order_price:
        price_no_tax = cfg.min_order_price
        min_applied = True

    # Налог — как в канонических калькуляторах платформы (6%, incl.).
    tax_rate = 0.06
    price = price_no_tax / (1 - tax_rate)
    net_profit = price * (1 - tax_rate) - full_cost
    unit_price = price_no_tax / copies

    warnings: tuple[str, ...] = ()
    if min_applied:
        warnings = (f"Применён минимальный заказ: {cfg.min_order_price:.0f} ₽",)

    lines: list[CostLine] = [
        CostLine("Печать (прайс × тираж)", print_income),
        CostLine("Бумага", paper_cost),
        CostLine("Краска", ink_cost),
        CostLine("Подготовка", setup_cost),
        *extras_lines,
        CostLine("Себестоимость", full_cost),
        CostLine(
            f"Допы и подготовка (+{markup * 100:.0f}%)", extras_income
        ),
        CostLine("Цена без налога", price_no_tax),
        CostLine(f"Налог ({tax_rate * 100:.0f}%)", price - price_no_tax),
        CostLine("ИТОГО ЦЕНА", price),
    ]

    details: dict[str, Any] = {
        "product": product,
        "width": item_w,
        "height": item_h,
        "sheet_format": sheet_format,
        "density": density,
        "copies": copies,
        "pages": int_pages,
        "duplex": duplex,
        "paper": paper_name,
        "color": color,
        "price_per_item": price_per_item,
        "total_sheets": total_sheets,
        "print_income": print_income,
        "extras_on": extras_on,
        "used_min": min_applied,
        "markup_percent": markup * 100,
    }

    return CalcResult(
        calculator_id="digital",
        price=price,
        price_no_tax=price_no_tax,
        cost=full_cost,
        net_profit=net_profit,
        unit_price=unit_price,
        lines=tuple(lines),
        warnings=warnings,
        details=details,
    )


def _get_product_price(cfg: DigitalConfig, product_name: str, copies: float) -> float:
    """Прайс изделия по диапазону тиража (legacy _get_product_price 335-346)."""
    for r in cfg.price_ranges(product_name):
        if r.end is None and copies >= r.start:
            return r.price_per_item
        if r.end is not None and r.start <= copies <= r.end:
            return r.price_per_item
    raise CalcInputError(
        "product",
        f"Для типа «{product_name}» нет подходящего диапазона цен "
        f"для тиража {copies:.0f}. Задайте диапазон в настройках.",
    )


def _calc_density(
    cfg: DigitalConfig, item_w: float, item_h: float, sheet_format: str
) -> int:
    """Штук на лист (legacy calc_density 315-330)."""
    if sheet_format not in cfg.sheet_formats:
        return 0
    sheet_w, sheet_h = cfg.sheet_formats[sheet_format]
    if item_w <= 0 or item_h <= 0:
        return 0
    cols = math.floor((sheet_w + cfg.gap) / (item_w + cfg.gap))
    rows = math.floor((sheet_h + cfg.gap) / (item_h + cfg.gap))
    return max(0, cols * rows)


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
