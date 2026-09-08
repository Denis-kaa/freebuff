"""Канонические константы Riso — дословный перенос из legacy-исходника.

Источник: «Общий калькулятор печати/riso_calc.py», строки 26–96
(PAPER_MATERIALS, INK_COST_PER_SHEET, MASTER_COST, WORK_COST_PER_1000,
CUTTING/LAMINATION/FOLDING/STAPLING/DELIVERY_COST, TIERS, PRICES, area_mult).
Golden-тесты закрепляют эти значения: менять их можно только осознанно,
через новую редакцию конфига, а не правкой кода.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class PriceTier:
    """Диапазон тиража (legacy TIERS)."""

    name: str
    min: int
    max: int | None


@dataclass(frozen=True)
class PricePair:
    """Пара цен за лист: one — односторонняя, two — двусторонняя (legacy PRICES)."""

    one: float
    two: float


_DEFAULT_PAPER: dict[str, float] = {
    "Офсетная 80 г/м²": 0.03,
    "Офсетная 90 г/м²": 0.04,
    "Газетная": 0.02,
    "Мел. матовая 130 г/м²": 0.08,
    "Мел. глянцевая 150 г/м²": 0.10,
}

_DEFAULT_INK: dict[str, float] = {
    "ч/б": 0.02,
    "1 краска": 0.05,
    "2 краски": 0.09,
}

_DEFAULT_TIERS: tuple[PriceTier, ...] = (
    PriceTier("500-999", 500, 999),
    PriceTier("1000-1999", 1000, 1999),
    PriceTier("2000-2999", 2000, 2999),
    PriceTier("3000-4999", 3000, 4999),
    PriceTier("5000-9999", 5000, 9999),
    PriceTier("от 10000", 10000, None),
)

_DEFAULT_PRICES: dict[tuple[str, str], PricePair] = {
    ("A4", "500-999"): PricePair(one=0.50, two=0.90),
    ("A4", "1000-1999"): PricePair(one=0.45, two=0.80),
    ("A4", "2000-2999"): PricePair(one=0.40, two=0.70),
    ("A4", "3000-4999"): PricePair(one=0.35, two=0.60),
    ("A4", "5000-9999"): PricePair(one=0.30, two=0.55),
    ("A4", "от 10000"): PricePair(one=0.25, two=0.45),
    ("A5", "500-999"): PricePair(one=0.30, two=0.55),
    ("A5", "1000-1999"): PricePair(one=0.27, two=0.50),
    ("A5", "2000-2999"): PricePair(one=0.24, two=0.45),
    ("A5", "3000-4999"): PricePair(one=0.21, two=0.40),
    ("A5", "5000-9999"): PricePair(one=0.18, two=0.35),
    ("A5", "от 10000"): PricePair(one=0.15, two=0.30),
    ("A6", "500-999"): PricePair(one=0.20, two=0.35),
    ("A6", "1000-1999"): PricePair(one=0.18, two=0.32),
    ("A6", "2000-2999"): PricePair(one=0.16, two=0.28),
    ("A6", "3000-4999"): PricePair(one=0.14, two=0.25),
    ("A6", "5000-9999"): PricePair(one=0.12, two=0.22),
    ("A6", "от 10000"): PricePair(one=0.10, two=0.20),
}

#: Множитель площади листа относительно A4 (legacy area_mult, строка 90).
AREA_MULTIPLIERS: Mapping[str, float] = MappingProxyType(
    {"A4": 1.0, "A5": 0.5, "A6": 0.25, "A3": 2.0}
)


def _frozen(mapping: Mapping[str, float]) -> Mapping[str, float]:
    return MappingProxyType(dict(mapping))


@dataclass(frozen=True)
class RisoConfig:
    """Инъекционный конфиг Riso (замена legacy-глобалов и riso_calc_config.json)."""

    tax_rate: float = 0.06
    min_order: int = 500
    master_cost: float = 5.0
    work_cost_per_1000: float = 50.0
    cutting_cost: float = 100.0
    lamination_cost_per_sheet: float = 2.0
    folding_cost_per_sheet: float = 0.5
    stapling_cost: float = 10.0
    delivery_cost: float = 500.0
    paper_materials: Mapping[str, float] = field(
        default_factory=lambda: _frozen(_DEFAULT_PAPER)
    )
    ink_cost_per_sheet: Mapping[str, float] = field(
        default_factory=lambda: _frozen(_DEFAULT_INK)
    )
    tiers: tuple[PriceTier, ...] = _DEFAULT_TIERS
    prices: Mapping[tuple[str, str], PricePair] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_PRICES))
    )
