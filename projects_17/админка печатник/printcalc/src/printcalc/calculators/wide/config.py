"""Канонические константы калькулятора широкоформатной печати — дословный перенос.

Источник: «Общий калькулятор печати/wide_format.py»:
- PRICE_MATERIALS / PRICE_PRINTS (тиры по площади) — строки 25–48;
- MOUNT_PRICES (фикс. цена за заказ, НЕ за штуку) — 51–60;
- WORK_PRICES (доп. работы: m2 / m / шт; люверсы — is_grommet) — 63–70;
- WORK_RATE_COST/SELL, DELIVERY_*, INSTALL_* — 73–78;
- calculate() — строки 660–756 (формулы в compute.py);
- интервал люверсов — GUI var_grommet_interval, значение по умолчанию «50» (строка 148);
- мин. сумма заказа — настройка GUI (config-json), по умолчанию 0.

Единицы: материалы и печать — ₽/м² ТИРАЖНОЙ площади (тир выбирается по общей
площади: area <= max, верхняя граница включительно); крепёж — ₽ за ЗАКАЗ;
работы — по своей единице (м² — от общей площади, пог.м — от общего периметра,
«шт» — люверсы: ceil(периметр_одной_шт_см / интервал) × тираж). Налог в цене
НЕ участвует — пары cost/sell уже содержат продажную цену. Golden-тесты
закрепляют значения: менять только осознанно, новой редакцией конфига.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class PriceTier:
    """Ступень прайса по площади: cost/sell действуют при min < area <= max.

    max_area=None — открытая верхняя граница (legacy {"max": None}).
    Выбор тира — legacy get_price (wide_format.py:112-122): сортировка по min,
    первый тир, у которого max is None или area <= max; включительность
    верхней границы закреплена golden-тестом (area == max → предыдущий тир).
    """

    name: str
    min_area: float
    max_area: float | None
    cost: float
    sell: float


@dataclass(frozen=True)
class MountPrice:
    """Крепёж: фиксированная пара цен за заказ (не умножается на тираж)."""

    name: str
    cost: float
    sell: float


@dataclass(frozen=True)
class WorkPrice:
    """Доп. работа: единица и пара цен.

    unit — "m2" | "m" | "шт" (legacy WORK_PRICES). Для "шт" с is_grommet=True
    количество выводится из интервала люверсов (см), иначе равно тиражу.
    """

    name: str
    unit: str
    cost: float
    sell: float
    is_grommet: bool = False


_DEFAULT_MATERIAL_TIERS: tuple[PriceTier, ...] = (
    PriceTier("Баннер 440г", min_area=0.0, max_area=5.0, cost=200.0, sell=350.0),
    PriceTier("Баннер 440г", min_area=5.0, max_area=20.0, cost=180.0, sell=300.0),
    PriceTier("Баннер 440г", min_area=20.0, max_area=None, cost=160.0, sell=280.0),
    PriceTier("Баннер 510г", min_area=0.0, max_area=5.0, cost=250.0, sell=420.0),
    PriceTier("Баннер 510г", min_area=5.0, max_area=20.0, cost=230.0, sell=380.0),
    PriceTier("Баннер 510г", min_area=20.0, max_area=None, cost=210.0, sell=350.0),
    PriceTier("Плёнка самоклеящаяся", min_area=0.0, max_area=3.0, cost=320.0, sell=600.0),
    PriceTier("Плёнка самоклеящаяся", min_area=3.0, max_area=10.0, cost=300.0, sell=550.0),
    PriceTier("Плёнка самоклеящаяся", min_area=10.0, max_area=None, cost=280.0, sell=500.0),
    PriceTier("Холст", min_area=0.0, max_area=2.0, cost=400.0, sell=700.0),
    PriceTier("Холст", min_area=2.0, max_area=None, cost=380.0, sell=650.0),
)

_DEFAULT_PRINT_TIERS: tuple[PriceTier, ...] = (
    PriceTier("Без печати", min_area=0.0, max_area=None, cost=0.0, sell=0.0),
    PriceTier("Интерьерная печать", min_area=0.0, max_area=5.0, cost=450.0, sell=800.0),
    PriceTier("Интерьерная печать", min_area=5.0, max_area=20.0, cost=400.0, sell=700.0),
    PriceTier("Интерьерная печать", min_area=20.0, max_area=None, cost=350.0, sell=650.0),
    PriceTier("Экстерьерная печать", min_area=0.0, max_area=5.0, cost=550.0, sell=1000.0),
    PriceTier("Экстерьерная печать", min_area=5.0, max_area=20.0, cost=500.0, sell=900.0),
    PriceTier("Экстерьерная печать", min_area=20.0, max_area=None, cost=450.0, sell=800.0),
    PriceTier("УФ-печать", min_area=0.0, max_area=3.0, cost=800.0, sell=1400.0),
    PriceTier("УФ-печать", min_area=3.0, max_area=None, cost=700.0, sell=1200.0),
)

_DEFAULT_MOUNTS: tuple[MountPrice, ...] = (
    MountPrice("Без монтажа", cost=0.0, sell=0.0),
    MountPrice("Монтаж без подъёма (до 2 м)", cost=1000.0, sell=2500.0),
    MountPrice("Монтаж без подъёма (2-3 м)", cost=1300.0, sell=3000.0),
    MountPrice("Монтаж без подъёма (свыше 3 м)", cost=1800.0, sell=4000.0),
    MountPrice("Монтаж с автовышкой (до 2 м)", cost=3000.0, sell=5000.0),
    MountPrice("Монтаж с автовышкой (2-3 м)", cost=4000.0, sell=7000.0),
    MountPrice("Монтаж с автовышкой (свыше 3 м)", cost=6000.0, sell=10000.0),
)

_DEFAULT_WORKS: tuple[WorkPrice, ...] = (
    WorkPrice("Загибка по периметру", unit="m", cost=100.0, sell=200.0),
    WorkPrice("Люверсы по периметру", unit="шт", cost=10.0, sell=20.0, is_grommet=True),
    WorkPrice("Карман", unit="m", cost=250.0, sell=400.0),
    WorkPrice("Накатка на жёсткую основу", unit="m2", cost=500.0, sell=900.0),
    WorkPrice("Монтаж на баннерную сетку", unit="m2", cost=300.0, sell=600.0),
)


def _frozen_material_tiers() -> tuple[PriceTier, ...]:
    return _DEFAULT_MATERIAL_TIERS


def _frozen_print_tiers() -> tuple[PriceTier, ...]:
    return _DEFAULT_PRINT_TIERS


def _frozen_mounts() -> tuple[MountPrice, ...]:
    return _DEFAULT_MOUNTS


def _frozen_works() -> tuple[WorkPrice, ...]:
    return _DEFAULT_WORKS


@dataclass(frozen=True)
class WideConfig:
    """Инъекционный конфиг широкоформата (замена legacy-глобалов и config-json)."""

    materials: tuple[PriceTier, ...] = field(default_factory=_frozen_material_tiers)
    prints: tuple[PriceTier, ...] = field(default_factory=_frozen_print_tiers)
    mounts: tuple[MountPrice, ...] = field(default_factory=_frozen_mounts)
    works: tuple[WorkPrice, ...] = field(default_factory=_frozen_works)
    work_rate_cost: float = 150.0  # производственные расходы ₽/м² — wide_format.py:73
    work_rate_sell: float = 250.0  # wide_format.py:74
    delivery_cost: float = 500.0  # wide_format.py:75
    delivery_sell: float = 1200.0  # wide_format.py:76
    install_cost: float = 0.0  # wide_format.py:77 (в legacy GUI не выставляется)
    install_sell: float = 0.0  # wide_format.py:78
    min_order_price: float = 0.0  # «Минимальная сумма заказа» — GUI, по умолчанию 0
    grommet_interval_default: float = 50.0  # см — var_grommet_interval, wide_format.py:148

    @property
    def material_names(self) -> Mapping[str, bool]:
        """Уникальные имена материалов (порядок первого появления) — all_names()."""
        return MappingProxyType({t.name: True for t in self.materials})

    @property
    def print_names(self) -> Mapping[str, bool]:
        """Уникальные имена видов печати — all_names()."""
        return MappingProxyType({t.name: True for t in self.prints})

    @property
    def mount_names(self) -> Mapping[str, bool]:
        """Имена крепежа (legacy — список MOUNT_PRICES)."""
        return MappingProxyType({m.name: True for m in self.mounts})
