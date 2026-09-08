"""Схема входов калькулятора Riso (CALC-SPEC).

Поля format/paper/color объявлены STRING: их допустимые наборы зависят
от RisoConfig (в legacy они заполнялись динамически из PRICES/PAPER/INK);
проверка членства — в compute с сохранением текстов ошибок legacy.
"""

from __future__ import annotations

from printcalc.engine.spec import CalculatorSpec, FieldKind, FieldSpec

SPEC = CalculatorSpec(
    id="riso",
    title="Калькулятор ризографии RISO RZ300EP",
    version="1.0.0",
    fields=(
        FieldSpec(
            name="format", kind=FieldKind.STRING, title="Формат", default="A4"
        ),
        FieldSpec(
            name="qty",
            kind=FieldKind.NUMBER,
            title="Количество листов",
            min_value=0,
            exclusive_min=True,
        ),
        FieldSpec(
            name="originals",
            kind=FieldKind.NUMBER,
            title="Оригиналы",
            min_value=0,
            exclusive_min=True,
        ),
        FieldSpec(
            name="color", kind=FieldKind.STRING, title="Цветность", default="ч/б"
        ),
        FieldSpec(
            name="paper",
            kind=FieldKind.STRING,
            title="Бумага",
            default="Офсетная 80 г/м²",
        ),
        FieldSpec(
            name="duplex",
            kind=FieldKind.BOOLEAN,
            title="Двусторонняя печать",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="markup_percent",
            kind=FieldKind.NUMBER,
            title="Наценка, %",
            default=25.0,
            required=False,
        ),
        FieldSpec(
            name="cutting",
            kind=FieldKind.BOOLEAN,
            title="Подрезка",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="lamination",
            kind=FieldKind.BOOLEAN,
            title="Ламинация",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="folding",
            kind=FieldKind.BOOLEAN,
            title="Фальцовка",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="stapling",
            kind=FieldKind.BOOLEAN,
            title="Сшивка",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="delivery",
            kind=FieldKind.BOOLEAN,
            title="Доставка",
            default=False,
            required=False,
        ),
    ),
)
