"""Схемная валидация входов (CALC-VALIDATE).

Проверяет типы/диапазоны/опции по FieldSpec и прерывается на первом
нарушении (паритет с legacy «одна ошибка за раз»). Семантические проверки,
зависящие от конфига (членство формата/бумаги/цветности), остаются в compute.
"""

from __future__ import annotations

from typing import Any, Mapping

from printcalc.engine.errors import CalcInputError
from printcalc.engine.spec import CalculatorSpec, FieldKind, FieldSpec


def validate_inputs(spec: CalculatorSpec, inputs: Mapping[str, Any]) -> None:
    """Валидирует входы по схеме. Raises CalcInputError на первом нарушении."""
    known = {fs.name for fs in spec.fields}
    for name in inputs:
        if name not in known:
            raise CalcInputError(name, "неизвестное поле входа")
    for fs in spec.fields:
        _validate_field(fs, inputs)


def _validate_field(fs: FieldSpec, inputs: Mapping[str, Any]) -> None:
    value = inputs.get(fs.name)
    if value is None:
        if fs.required and fs.default is None:
            raise CalcInputError(fs.name, "обязательное поле не задано")
        return
    if fs.kind is FieldKind.NUMBER:
        _check_range(fs, _as_number(fs, value))
    elif fs.kind is FieldKind.INTEGER:
        num = _as_number(fs, value)
        if num != int(num):
            raise CalcInputError(fs.name, "ожидалось целое число")
        _check_range(fs, num)
    elif fs.kind is FieldKind.BOOLEAN:
        if not isinstance(value, bool):
            raise CalcInputError(fs.name, "ожидался логический флаг (true/false)")
    elif fs.kind is FieldKind.ENUM:
        if not isinstance(value, str) or value not in fs.options:
            raise CalcInputError(fs.name, f"допустимые значения: {', '.join(fs.options)}")
    elif fs.kind is FieldKind.STRING:
        if not isinstance(value, str):
            raise CalcInputError(fs.name, "ожидалась строка")


def _as_number(fs: FieldSpec, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise CalcInputError(fs.name, "ожидалось число")
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            raise CalcInputError(fs.name, "ожидалось число") from None
    return float(value)


def _check_range(fs: FieldSpec, num: float) -> None:
    if fs.min_value is not None:
        if fs.exclusive_min and num <= fs.min_value:
            raise CalcInputError(fs.name, f"значение должно быть больше {fs.min_value:g}")
        if not fs.exclusive_min and num < fs.min_value:
            raise CalcInputError(fs.name, f"значение должно быть не меньше {fs.min_value:g}")
    if fs.max_value is not None and num > fs.max_value:
        raise CalcInputError(fs.name, f"значение должно быть не больше {fs.max_value:g}")
