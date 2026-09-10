"""Схема входов калькулятора ЧПУ-реза (CALC-SPEC).

Поля повторяют GUI legacy cnc_calc.py: станок (laser/frezer, строка 218),
материал/толщина (зависимые селекты), длина реза, м (id=cut_length,
default «1»), тираж (id=quantity, default 1), размеры изделия в метрах
(id=sheet_width/sheet_length — в GUI поля листа, в формуле это габариты
изделия, строка 416: «Материал: W × L м² (изделие)»). material объявлен
STRING: допустимые наборы — уникальные имена тиров канонического конфига;
thickness NUMBER с проверкой членства в thickness_options — в compute.
"""

from __future__ import annotations

from printcalc.calculators.cnc.config import DEFAULT_MATERIAL_NAMES
from printcalc.engine.spec import CalculatorSpec, FieldKind, FieldSpec

SPEC = CalculatorSpec(
    id="cnc",
    title="ЧПУ-рез (лазер/фрезер)",
    version="1.0.0",
    fields=(
        FieldSpec(
            name="machine",
            kind=FieldKind.ENUM,
            title="Станок",
            default="laser",
            options=("laser", "frezer"),
        ),
        FieldSpec(
            name="material",
            kind=FieldKind.STRING,
            title="Материал",
            default="Фанера",
            options=DEFAULT_MATERIAL_NAMES,
        ),
        FieldSpec(
            name="thickness",
            kind=FieldKind.NUMBER,
            title="Толщина, мм",
            default=3.0,
            min_value=0,
            exclusive_min=True,
        ),
        FieldSpec(
            name="cut_length",
            kind=FieldKind.NUMBER,
            title="Длина реза, м",
            default=1.0,
            min_value=0,
        ),
        FieldSpec(
            name="qty",
            kind=FieldKind.NUMBER,
            title="Количество, шт",
            default=1.0,
            min_value=0,
            exclusive_min=True,
        ),
        FieldSpec(
            name="product_width",
            kind=FieldKind.NUMBER,
            title="Ширина изделия, м",
            default=0.0,
            required=False,
            min_value=0,
        ),
        FieldSpec(
            name="product_height",
            kind=FieldKind.NUMBER,
            title="Длина изделия, м",
            default=0.0,
            required=False,
            min_value=0,
        ),
    ),
)

__all__ = ["SPEC"]
