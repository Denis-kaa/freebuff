"""Схема входов калькулятора вывесок (CALC-SPEC).

Поля повторяют GUI legacy sign_calc.py: тип изделия (продукт), размеры,
тираж, комплексность, наценка, материалы лица/борта/задника, нанесение,
монтаж, электрика, доставка, подложка, каркас, блоки питания. Числовые
поля с чекбоксом в GUI (доставка/подложка/каркас) смоделированы парой
полей: флаг + значение (0 = выключено, паритет legacy default False).
"""
# Copyright: порт legacy sign_calc.py (строки 122–170, 312–410).

from __future__ import annotations

from printcalc.calculators.sign.config import COMPLEXITY_FACTORS, MOUNT_VARIANTS
from printcalc.calculators.sign.config import SignConfig  # noqa: F401 (инъекция)
from printcalc.engine.spec import CalculatorSpec, FieldKind, FieldSpec

_CFG = SignConfig()

SPEC = CalculatorSpec(
    id="sign",
    title="Вывески (Sign)",
    version="1.0.0",
    fields=(
        FieldSpec(
            name="product", kind=FieldKind.STRING, title="Изделие", default="Наличная буква"
        ),
        FieldSpec(
            name="height",
            kind=FieldKind.NUMBER,
            title="Высота (см для букв, м для короба)",
            default=40.0,
            min_value=0,
            exclusive_min=True,
        ),
        FieldSpec(
            name="width",
            kind=FieldKind.NUMBER,
            title="Ширина, м (только для короба)",
            default=0.5,
            required=False,
            min_value=0,
        ),
        FieldSpec(
            name="qty",
            kind=FieldKind.NUMBER,
            title="Количество",
            default=1.0,
            min_value=0,
            exclusive_min=True,
        ),
        FieldSpec(
            name="complexity",
            kind=FieldKind.STRING,
            title="Комплексность",
            default="Средний",
            options=tuple(COMPLEXITY_FACTORS),
        ),
        FieldSpec(
            name="markup_percent",
            kind=FieldKind.NUMBER,
            title="Наценка, %",
            default=_CFG.markup_default,
            required=False,
        ),
        FieldSpec(
            name="front_material", kind=FieldKind.STRING, title="Материал лица", default="Авто"
        ),
        FieldSpec(
            name="side_material", kind=FieldKind.STRING, title="Материал борта", default="Авто"
        ),
        FieldSpec(
            name="back_material", kind=FieldKind.STRING, title="Материал задника", default="Авто"
        ),
        FieldSpec(
            name="image_type", kind=FieldKind.STRING, title="Нанесение", default="Без нанесения"
        ),
        FieldSpec(
            name="mounting", kind=FieldKind.STRING, title="Монтаж по высоте", default="нет"
        ),
        FieldSpec(
            name="electric",
            kind=FieldKind.BOOLEAN,
            title="Электрика",
            default=False,
            required=False,
        ),
        FieldSpec(
            name="delivery_distance_km",
            kind=FieldKind.NUMBER,
            title="Доставка: км (0 = нет)",
            default=0.0,
            required=False,
            min_value=0,
        ),
        FieldSpec(
            name="substrate_area_m2",
            kind=FieldKind.NUMBER,
            title="Подложка: площадь м² (0 = нет)",
            default=0.0,
            required=False,
            min_value=0,
        ),
        FieldSpec(
            name="substrate_material", kind=FieldKind.STRING, title="Материал подложки", default="ПВХ 10мм"
        ),
        FieldSpec(
            name="frame_length_m",
            kind=FieldKind.NUMBER,
            title="Каркас: длина м (0 = нет)",
            default=0.0,
            required=False,
            min_value=0,
        ),
        FieldSpec(
            name="frame_material", kind=FieldKind.STRING, title="Материал каркаса", default="Металлический"
        ),
        FieldSpec(
            name="power_supply_count",
            kind=FieldKind.NUMBER,
            title="Блоки питания, шт",
            default=0.0,
            required=False,
            min_value=0,
        ),
    ),
)

__all__ = ["SPEC"]
