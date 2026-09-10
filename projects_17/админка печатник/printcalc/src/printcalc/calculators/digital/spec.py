"""Схема входов калькулятора цифровой печати (CALC-SPEC).

Legacy GUI (calc_digital.py) заполняет width/height/pages/copies/color/duplex
из шаблона изделия (PRODUCT_TEMPLATES); в web-версии шаблон — это подсказка
UI, а входы явные. Поля product/paper/color/sheet_format объявлены STRING:
допустимые наборы — канонические ключи DigitalConfig (шаблоны/бумага/краска/
листы), проверка членства — в compute с поведением legacy.
Поля extras_* — чекбоксы доп. операций из STANDARD_OPERATIONS.
"""

from __future__ import annotations

from printcalc.engine.spec import CalculatorSpec, FieldKind, FieldSpec

SPEC = CalculatorSpec(
    id="digital",
    title="Цифровая печать (Digital)",
    version="1.0.0",
    fields=(
        FieldSpec(
            name="product", kind=FieldKind.STRING, title="Изделие", default="Визитка"
        ),
        FieldSpec(
            name="width",
            kind=FieldKind.NUMBER,
            title="Ширина, мм",
            default=90.0,
            min_value=0,
            exclusive_min=True,
        ),
        FieldSpec(
            name="height",
            kind=FieldKind.NUMBER,
            title="Высота, мм",
            default=50.0,
            min_value=0,
            exclusive_min=True,
        ),
        FieldSpec(
            name="copies",
            kind=FieldKind.NUMBER,
            title="Тираж",
            default=100.0,
            min_value=0,
            exclusive_min=True,
        ),
        FieldSpec(
            name="pages",
            kind=FieldKind.NUMBER,
            title="Полос",
            default=1.0,
            min_value=0,
            exclusive_min=True,
        ),
        FieldSpec(
            name="color", kind=FieldKind.STRING, title="Цветность", default="цветная"
        ),
        FieldSpec(
            name="duplex",
            kind=FieldKind.BOOLEAN,
            title="Двусторонняя печать",
            default=True,
            required=False,
        ),
        FieldSpec(
            name="sheet_format", kind=FieldKind.STRING, title="Лист", default="A4"
        ),
        FieldSpec(
            name="paper",
            kind=FieldKind.STRING,
            title="Бумага",
            default="Офсет 80 г/м²",
        ),
        FieldSpec(
            name="markup_percent",
            kind=FieldKind.NUMBER,
            title="Наценка, %",
            default=30.0,
            required=False,
        ),
        FieldSpec(
            name="extras_lamination",
            kind=FieldKind.BOOLEAN,
            title="Ламинация",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="extras_folding",
            kind=FieldKind.BOOLEAN,
            title="Фальцовка",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="extras_cutting",
            kind=FieldKind.BOOLEAN,
            title="Резка",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="extras_rounding",
            kind=FieldKind.BOOLEAN,
            title="Скругление углов",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="extras_staple",
            kind=FieldKind.BOOLEAN,
            title="Скрепление скобой",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="extras_spring",
            kind=FieldKind.BOOLEAN,
            title="Переплёт на пружину",
            default=False,
            required=False,
        ),
    ),
)
