"""Схема входов калькулятора дизайна (CALC-SPEC).

Поля повторяют семантику legacy design_calc.py: услуга (селект из прайса,
id=service), сторона печати (id=print_side, «4+0»/«4+4» — только для
визиток/листовок/буклета), уровень макета (id=macro_level, вариант прайса).
Тираж/полосы в форме legacy есть, но на цену НЕ влияют (прайс за работу).
service/option объявлены STRING: допустимые наборы — канонические имена
услуг/вариантов DesignConfig, проверка членства — в compute.
"""

from __future__ import annotations

from printcalc.calculators.design.config import DesignConfig
from printcalc.engine.spec import CalculatorSpec, FieldKind, FieldSpec

_CFG = DesignConfig()

SPEC = CalculatorSpec(
    id="design",
    title="Дизайн и обработка макетов",
    version="1.0.0",
    fields=(
        FieldSpec(
            name="service",
            kind=FieldKind.STRING,
            title="Услуга / вид работ",
            default="",
            options=_CFG.services(),
        ),
        FieldSpec(
            name="side",
            kind=FieldKind.STRING,
            title="Сторона печати (4+0/4+4)",
            default="",
            required=False,
            options=("", "4+0", "4+4"),
        ),
        FieldSpec(
            name="option",
            kind=FieldKind.STRING,
            title="Уровень / вариант",
            default="",
            required=False,
        ),
        FieldSpec(
            name="pages",
            kind=FieldKind.NUMBER,
            title="Кол-во страниц / полос",
            default=1.0,
            required=False,
            min_value=0,
        ),
        FieldSpec(
            name="circulation",
            kind=FieldKind.NUMBER,
            title="Тираж",
            default=500.0,
            required=False,
            min_value=0,
        ),
    ),
)

__all__ = ["SPEC"]
