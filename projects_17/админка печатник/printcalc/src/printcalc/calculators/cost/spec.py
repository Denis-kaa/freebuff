"""Схема входов калькулятора Себестоимости (CALC-SPEC).

Поля повторяют семантику legacy universal_calc.py: станок (var_equip),
материал (var_material), тираж (var_qty, default «1»), формат листа
(var_sheet_format, default «A4»), нестандартный размер (use_custom +
var_custom_w/h, мм). Экономика цеха (аренда/оператор/наценка/брак/
загрузка) — параметры конфига с дефолтами GUI (строки 192–202), в web
переопределяются инъекцией CostConfig, а не полями каждого расчёта.
equipment/material объявлены STRING: наборы — ключи канонического конфига.
"""

from __future__ import annotations

from printcalc.calculators.cost.config import PAPER_SIZES_MM
from printcalc.engine.spec import CalculatorSpec, FieldKind, FieldSpec

SPEC = CalculatorSpec(
    id="cost",
    title="Себестоимость (по станку)",
    version="1.0.0",
    fields=(
        FieldSpec(
            name="equipment",
            kind=FieldKind.STRING,
            title="Станок",
            default="Roland VP540",
        ),
        FieldSpec(
            name="material",
            kind=FieldKind.STRING,
            title="Материал",
            default="",
        ),
        FieldSpec(
            name="qty",
            kind=FieldKind.NUMBER,
            title="Тираж (м² / листов)",
            default=1.0,
            min_value=0,
            exclusive_min=True,
        ),
        FieldSpec(
            name="sheet_format",
            kind=FieldKind.STRING,
            title="Формат листа",
            default="A4",
            required=False,
            options=tuple(PAPER_SIZES_MM),
        ),
        FieldSpec(
            name="use_custom",
            kind=FieldKind.BOOLEAN,
            title="Нестандартный размер изделия",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="custom_width",
            kind=FieldKind.NUMBER,
            title="Ширина изделия, мм",
            default=90.0,
            required=False,
            min_value=0,
        ),
        FieldSpec(
            name="custom_height",
            kind=FieldKind.NUMBER,
            title="Высота изделия, мм",
            default=50.0,
            required=False,
            min_value=0,
        ),
    ),
)

__all__ = ["SPEC"]
