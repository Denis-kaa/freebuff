"""Канонические константы калькулятора табличек — дословный перенос из legacy.

Источник: «Общий калькулятор печати/tablichki.py» (версия «Поддерживает шт»):
- MATERIALS / PRINT_PRICES / MOUNT_PRICES / WORK_PRICES — строки 26–52;
- WORK_RATE_COST/SELL, DELIVERY, INSTALL, MIN_ORDER_PRICE, TAX_RATE — 54–60;
- calculate() — строки 641–744 (формулы ниже в compute.py).

Единицы цен: материалы и печать — ₽/м², крепёж — ₽/табличку, работы — по
своей единице (м² / пог.м / шт). ВАЖНО: налог в цене НЕ участвует — пары
cost/sell уже содержат продажную цену (в отличие от Riso, где применяется
/(1-tax)). Golden-тесты закрепляют значения: менять только осознанно, новой
редакцией конфига, а не правкой кода.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class PricePair:
    """Пара цен: cost — закупка, sell — продажа (legacy dict {cost, sell})."""

    cost: float
    sell: float


@dataclass(frozen=True)
class WorkPrice:
    """Операция обработки: единица измерения и пара цен.

    unit — "m2" | "m" | "шт" (legacy WORK_PRICES; m2/m считаются от геометрии
    таблички, «шт» вводится отдельным количеством).
    """

    unit: str
    cost: float
    sell: float


_DEFAULT_MATERIALS: dict[str, PricePair] = {
    "ПВХ 3 мм": PricePair(cost=800.0, sell=1200.0),
    "ПВХ 5 мм": PricePair(cost=1000.0, sell=1500.0),
    "Акрил 3 мм": PricePair(cost=1300.0, sell=1800.0),
    "Акрил 5 мм": PricePair(cost=1700.0, sell=2200.0),
    "Композит 3 мм": PricePair(cost=1200.0, sell=1600.0),
    "Композит 5 мм": PricePair(cost=1500.0, sell=1900.0),
}

_DEFAULT_PRINTS: dict[str, PricePair] = {
    "Без печати": PricePair(cost=0.0, sell=0.0),
    "УФ-печать": PricePair(cost=1500.0, sell=2400.0),
    "УФ-печать + лак": PricePair(cost=2000.0, sell=3000.0),
}

_DEFAULT_MOUNTS: dict[str, PricePair] = {
    "Без крепежа": PricePair(cost=0.0, sell=0.0),
    "Двусторонний скотч": PricePair(cost=20.0, sell=35.0),
    "Клейкая пена": PricePair(cost=40.0, sell=60.0),
    "Винты (4 шт)": PricePair(cost=25.0, sell=40.0),
    "Дюбели (4 шт)": PricePair(cost=40.0, sell=60.0),
}

_DEFAULT_WORKS: dict[str, WorkPrice] = {
    "Скругление углов": WorkPrice(unit="m2", cost=100.0, sell=200.0),
    "Фрезеровка сложной формы": WorkPrice(unit="m2", cost=500.0, sell=800.0),
    "Нанесение скотча по периметру": WorkPrice(unit="m", cost=70.0, sell=120.0),
    "Установка люверсов": WorkPrice(unit="шт", cost=20.0, sell=35.0),
}


def _frozen_materials() -> Mapping[str, PricePair]:
    return MappingProxyType(dict(_DEFAULT_MATERIALS))


def _frozen_prints() -> Mapping[str, PricePair]:
    return MappingProxyType(dict(_DEFAULT_PRINTS))


def _frozen_mounts() -> Mapping[str, PricePair]:
    return MappingProxyType(dict(_DEFAULT_MOUNTS))


def _frozen_works() -> Mapping[str, WorkPrice]:
    return MappingProxyType(dict(_DEFAULT_WORKS))


@dataclass(frozen=True)
class TablichkiConfig:
    """Инъекционный конфиг табличек (замена legacy-глобалов и конфиг-json)."""

    materials: Mapping[str, PricePair] = field(default_factory=_frozen_materials)
    prints: Mapping[str, PricePair] = field(default_factory=_frozen_prints)
    mounts: Mapping[str, PricePair] = field(default_factory=_frozen_mounts)
    works: Mapping[str, WorkPrice] = field(default_factory=_frozen_works)
    work_rate_cost: float = 400.0  # «Работа за м²» (закупка) — tablichki.py:54
    work_rate_sell: float = 1000.0  # «Работа за м²» (продажа) — tablichki.py:55
    delivery_cost: float = 100.0  # tablichki.py:56
    delivery_sell: float = 300.0  # tablichki.py:57
    install_cost: float = 0.0  # tablichki.py:58 (монтаж — без цены по умолчанию)
    install_sell: float = 0.0  # tablichki.py:59
    min_order_price: float = 0.0  # нижняя граница продажной цены — tablichki.py:60
    tax_rate: float = 0.06  # объявлен в legacy (строка 61), в цене НЕ участвует
