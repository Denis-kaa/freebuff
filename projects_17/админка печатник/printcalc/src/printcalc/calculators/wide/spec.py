"""Схема входов калькулятора широкоформатной печати (CALC-SPEC).

Поля повторяют GUI legacy wide_format.py: размеры в см (var_w/var_h —
строки 140–141, дефолты 200×100), тираж, материал/печать/монтаж, чекбоксы
доп. работ, интервал люверсов (см, default «50» — строка 148), доставка,
монтаж-флаг. material/print объявлены STRING: допустимые наборы — уникальные
имена тиров канонического конфига (legacy all_names), проверка членства —
в compute с поведением legacy get_price (неизвестное имя → (0,0), т.е.
«Бесплатно» — закреплено тестом).

Работы — булевы поля из конфига (порядок WORK_PRICES сохранён); интервал
люверсов — одно число-поле (применяется только к is_grommet-работе, как
var_grommet_interval в legacy). Мин. сумма заказа — НЕ вход: в legacy это
настройка калькулятора (config-json), поэтому живёт в WideConfig.
"""

from __future__ import annotations

from printcalc.calculators.wide.config import WideConfig
from printcalc.engine.spec import CalculatorSpec, FieldKind, FieldSpec

#: Слаг для каждой доп. работы: имя в UI остаётся русским (из WORK_PRICES),
#: имя поля — ASCII-слаг (стабильный контракт параметров заказа).
WORK_SLUGS: dict[str, str] = {
    "Загибка по периметру": "hemming",
    "Люверсы по периметру": "eyelets",
    "Карман": "pocket",
    "Накатка на жёсткую основу": "laminate_mount",
    "Монтаж на баннерную сетку": "banner_mesh",
}

_UNIT_TITLES = {"m2": "м²", "m": "пог.м", "шт": "шт"}


def _work_fields(config: WideConfig) -> tuple[FieldSpec, ...]:
    """Поля-переключатели доп. работ из конфига (порядок WORK_PRICES)."""
    fields: list[FieldSpec] = []
    for work in config.works:
        slug = WORK_SLUGS.get(work.name, work.name)
        unit_txt = _UNIT_TITLES.get(work.unit, work.unit)
        fields.append(
            FieldSpec(
                name=f"work_{slug}",
                kind=FieldKind.BOOLEAN,
                title=f"{work.name} ({unit_txt})",
                default=False,
                required=False,
            )
        )
    return tuple(fields)


def build_spec() -> CalculatorSpec:
    """Собирает спеку из канонического конфига (как legacy из своих глобалов)."""
    config = WideConfig()
    return CalculatorSpec(
        id="wide",
        title="Калькулятор широкоформатной печати",
        version="1.0.0",
        fields=(
            FieldSpec(
                name="width",
                kind=FieldKind.NUMBER,
                title="Ширина, см",
                default=200.0,  # var_w — wide_format.py:140
                min_value=0,
                exclusive_min=True,
                unit="см",
            ),
            FieldSpec(
                name="height",
                kind=FieldKind.NUMBER,
                title="Высота, см",
                default=100.0,  # var_h — wide_format.py:141
                min_value=0,
                exclusive_min=True,
                unit="см",
            ),
            FieldSpec(
                name="qty",
                kind=FieldKind.NUMBER,
                title="Кол-во",
                default=1.0,  # var_qty — wide_format.py:142
                min_value=0,
                exclusive_min=True,
                unit="шт",
            ),
            FieldSpec(
                name="material",
                kind=FieldKind.STRING,
                title="Материал",
                default=next(iter(config.material_names)),
            ),
            FieldSpec(
                name="print",
                kind=FieldKind.STRING,
                title="Печать",
                default=next(iter(config.print_names)),
            ),
            FieldSpec(
                name="mount",
                kind=FieldKind.STRING,
                title="Монтаж",
                default=next(iter(config.mount_names)),
            ),
            *_work_fields(config),
            FieldSpec(
                name="grommet_interval",
                kind=FieldKind.NUMBER,
                title="Интервал люверсов, см",
                default=config.grommet_interval_default,
                min_value=0,
                exclusive_min=True,
                unit="см",
                required=False,
            ),
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
                title="Монтаж (флаг)",
                default=False,
                required=False,
            ),
            FieldSpec(
                name="roll_width_mm",
                kind=FieldKind.NUMBER,
                title="Ширина загруженного рулона, мм (для расчёта расхода)",
                default=None,
                min_value=0,
                exclusive_min=True,
                unit="мм",
                required=False,
            ),
        ),
    )


SPEC = build_spec()
