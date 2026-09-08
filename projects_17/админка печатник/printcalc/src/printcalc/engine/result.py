"""Контракт результата расчёта (CALC-RESULT).

Поле price — финальная цена с налогом; price_no_tax — до налога;
unit_price — price_no_tax / qty. Все суммы float: паритет с legacy-арифметикой
(переезд на Decimal — отдельное решение, см. README).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class CostLine:
    """Одна строка детализации (аналог строк detail-блока legacy)."""

    label: str
    amount: float


@dataclass(frozen=True)
class CalcResult:
    """Результат расчёта одного калькулятора."""

    calculator_id: str
    price: float
    price_no_tax: float
    cost: float
    net_profit: float
    unit_price: float
    lines: tuple[CostLine, ...] = ()
    warnings: tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)
