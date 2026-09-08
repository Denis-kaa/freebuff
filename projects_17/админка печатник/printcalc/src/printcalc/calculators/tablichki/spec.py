"""Схема входов калькулятора табличек (CALC-SPEC).

material/print/mount объявлены STRING: наборы зависят от TablichkiConfig
(в legacy — глобалы MATERIALS/PRINT_PRICES/MOUNT_PRICES, перезаписываемые
конфиг-json); проверка членства — в compute с сохранением поведения legacy.

Работы (обработка) в legacy — динамические чекбоксы из WORK_PRICES, поэтому
поле для каждой работы порождается из канонического конфига при сборке
спеки: boolean «включить»; для работ с единицей «шт» дополнительно поле
количества (в legacy строка ввода появлялась только при включённом чекбоксе,
по умолчанию 1). Имена полей — стабильные слаги (не зависят от регистра/
раскладки), чтобы параметры заказа не ломались при переименовании.
"""

from __future__ import annotations

from printcalc.calculators.tablichki.config import TablichkiConfig
from printcalc.engine.spec import CalculatorSpec, FieldKind, FieldSpec

#: Слаг для каждой работы: имя в UI остаётся русским (из WORK_PRICES),
#: имя поля — ASCII-слаг (стабильный контракт параметров заказа).
WORK_SLUGS: dict[str, str] = {
    "Скругление углов": "rounding",
    "Фрезеровка сложной формы": "milling",
    "Нанесение скотча по периметру": "tape",
    "Установка люверсов": "eyelets",
}

#: Единица → текст в заголовке (как чекбоксы legacy «(м²)/(пог.м)/(шт)»).
_UNIT_TITLES = {"m2": "м²", "m": "пог.м", "шт": "шт"}

#: Число работ, у которых «шт» (количество вводится руками).
_PIECE_UNITS = {"шт"}


def _work_fields(config: TablichkiConfig) -> tuple[FieldSpec, ...]:
    """Поля-переключатели работ из конфига (порядок WORK_PRICES сохранён)."""
    fields: list[FieldSpec] = []
    for name, work in config.works.items():
        slug = WORK_SLUGS.get(name, name)
        unit_txt = _UNIT_TITLES.get(work.unit, work.unit)
        fields.append(
            FieldSpec(
                name=f"work_{slug}",
                kind=FieldKind.BOOLEAN,
                title=f"{name} ({unit_txt})",
                default=False,
                required=False,
            )
        )
        if work.unit in _PIECE_UNITS:
            fields.append(
                FieldSpec(
                    name=f"work_{slug}_qty",
                    kind=FieldKind.NUMBER,
                    title=f"{name}, количество",
                    default=1.0,
                    min_value=0,
                    exclusive_min=True,
                    required=False,
                    unit="шт",
                )
            )
    return tuple(fields)


def build_spec() -> CalculatorSpec:
    """Собирает спеку из канонического конфига (как legacy из своих глобалов)."""
    config = TablichkiConfig()
    return CalculatorSpec(
        id="tablichki",
        title="Калькулятор табличек (закупка/продажа)",
        version="1.0.0",
        fields=(
            FieldSpec(
                name="width",
                kind=FieldKind.NUMBER,
                title="Ширина таблички",
                default=20.0,
                min_value=0,
                exclusive_min=True,
                unit="см",
            ),
            FieldSpec(
                name="height",
                kind=FieldKind.NUMBER,
                title="Высота таблички",
                default=10.0,
                min_value=0,
                exclusive_min=True,
                unit="см",
            ),
            FieldSpec(
                name="qty",
                kind=FieldKind.NUMBER,
                title="Количество табличек",
                default=1.0,
                min_value=0,
                exclusive_min=True,
                unit="шт",
            ),
            FieldSpec(
                name="material",
                kind=FieldKind.STRING,
                title="Материал",
                default=next(iter(config.materials)),
            ),
            FieldSpec(
                name="print",
                kind=FieldKind.STRING,
                title="Печать",
                default="Без печати",
            ),
            FieldSpec(
                name="mount",
                kind=FieldKind.STRING,
                title="Крепёж",
                default="Без крепежа",
            ),
            FieldSpec(
                name="double_sided",
                kind=FieldKind.BOOLEAN,
                title="Двусторонняя табличка",
                default=False,
                required=False,
            ),
            *_work_fields(config),
            FieldSpec(
                name="delivery",
                kind=FieldKind.BOOLEAN,
                title="Доставка",
                default=False,
                required=False,
            ),
            FieldSpec(
                name="install",
                kind=FieldKind.BOOLEAN,
                title="Монтаж",
                default=False,
                required=False,
            ),
        ),
    )


SPEC = build_spec()
