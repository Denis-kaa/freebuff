"""Контракт калькулятора (CALC-SPEC): метаданные + схема входов.

Схема одна и та же для валидации и для будущего schema-driven UI
(web-фаза). Поля с конфигурируемыми наборами значений (формат/бумага/
цветность у Riso) объявляются STRING: наборы зависят от RisoConfig,
проверка членства выполняется в compute (паритет сообщений legacy).
Расширение движка «динамические ENUM-опции» — Phase 3.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Mapping

from printcalc.engine.result import CalcResult


class FieldKind(StrEnum):
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ENUM = "enum"
    STRING = "string"


@dataclass(frozen=True)
class FieldSpec:
    """Описание одного поля входа."""

    name: str
    kind: FieldKind
    title: str
    required: bool = True
    default: Any = None
    options: tuple[str, ...] = ()
    min_value: float | None = None
    max_value: float | None = None
    exclusive_min: bool = False
    unit: str | None = None


@dataclass(frozen=True)
class CalculatorSpec:
    """Метаданные калькулятора + схема входов."""

    id: str
    title: str
    version: str
    fields: tuple[FieldSpec, ...]


ComputeFn = Callable[[Mapping[str, Any]], CalcResult]


@dataclass(frozen=True)
class CalculatorRegistration:
    """Пара «спека + чистая функция расчёта» в реестре."""

    spec: CalculatorSpec
    compute: ComputeFn
