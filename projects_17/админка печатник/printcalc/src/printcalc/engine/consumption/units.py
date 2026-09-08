"""Единый нормализатор единиц движка расхода (ТЗ §40-41).

Внутренний стандарт: length → mm, area → mm² (вывод в м² на границе),
linear → mm, quantity → число, деньги — НЕ здесь (Cost Engine, §42).
Все конвертации точные (степени 10), без float-накопления.

На границе API разрешены: mm, cm, m, m², пог.м, шт, лист (§41).
Единица материала — атрибут реестра; формула расхода обязана указывать
единицу (урок BR-W3 из MATERIAL_MODEL: люверсы «м» vs «шт»).
"""

from __future__ import annotations

from printcalc.engine.errors import CalcInputError

#: Множители длины → мм (точные).
_LENGTH_TO_MM: dict[str, float] = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
}

#: Человекочитаемые подписи (для trace/UI).
UNIT_LABELS: dict[str, str] = {
    "mm": "мм",
    "cm": "см",
    "m": "м",
    "mm2": "мм²",
    "m2": "м²",
    "lm": "пог.м",
    "шт": "шт",
    "лист": "лист",
}


def length_to_mm(value: float, unit: str) -> float:
    """Длина в мм. Неизвестная единица — CalcInputError INVALID_MATERIAL_UNIT."""
    factor = _LENGTH_TO_MM.get(unit)
    if factor is None:
        raise CalcInputError("unit", f"неизвестная единица длины: {unit}")
    return value * factor


def area_to_m2(value_mm2: float) -> float:
    """Площадь из мм² в м² (граница API — только на выводе, §40)."""
    return value_mm2 / 1_000_000.0


def linear_to_m(value_mm: float) -> float:
    """Погонная длина из мм в м (граница API)."""
    return value_mm / 1000.0


__all__ = ["UNIT_LABELS", "area_to_m2", "length_to_mm", "linear_to_m"]
