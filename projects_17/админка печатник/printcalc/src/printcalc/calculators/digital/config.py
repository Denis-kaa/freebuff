"""Канонические константы Digital — дословный перенос из legacy-исходника.

Источник: «Общий калькулятор печати/build_all/calc_digital.py», строки 21–63
(PAPERS, INK, SETUP_COST, MIN_ORDER_PRICE, MARKUP_DEFAULT, STANDARD_OPERATIONS,
SHEET_FORMATS, GAP, PRODUCT_TEMPLATES, PRODUCT_PRICES/init_default_prices).
Golden-тесты закрепляют эти значения: менять их можно только осознанно,
через новую редакцию конфига, а не правкой кода.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class PriceRange:
    """Диапазон тиража с ценой за изделие (legacy PRODUCT_PRICES)."""

    start: int
    end: int | None
    price_per_item: float


@dataclass(frozen=True)
class ProductTemplate:
    """Шаблон изделия (legacy PRODUCT_TEMPLATES)."""

    name: str
    width: float
    height: float
    pages: int
    copies: int
    color: str
    duplex: bool


#: Бумага: имя → цена листа A4 (legacy PAPERS, строка 21).
_DEFAULT_PAPERS: dict[str, float] = {
    "Офсет 80 г/м²": 0.35,
    "Офсет 90 г/м²": 0.45,
    "Мел. мат. 115 г/м²": 0.90,
    "Мел. глян. 130 г/м²": 1.00,
    "Мел. мат. 170 г/м²": 1.50,
    "Мел. глян. 300 г/м²": 2.30,
    "Картон 250 г/м²": 1.80,
    "Самоклейка": 1.60,
}

#: Краска: ч/б | цветная → цена листа A4 (legacy INK, строка 39).
_DEFAULT_INK: dict[str, float] = {"ч/б": 0.10, "цветная": 1.20}

#: Листы: имя → (ширина, высота) в мм (legacy SHEET_FORMATS, строка 52).
SHEET_FORMATS: Mapping[str, tuple[float, float]] = MappingProxyType(
    {"A4": (210.0, 297.0), "A3": (297.0, 420.0), "SRA3": (320.0, 450.0)}
)

#: Зазор между изделиями при раскладке, мм (legacy GAP, строка 53).
GAP: float = 2.0

#: Шаблоны изделий (legacy PRODUCT_TEMPLATES, строки 55–65).
_DEFAULT_TEMPLATES: tuple[ProductTemplate, ...] = (
    ProductTemplate("Визитка", 90, 50, 1, 100, "цветная", True),
    ProductTemplate("Листовка А5", 148, 210, 1, 100, "цветная", False),
    ProductTemplate("Листовка А4", 210, 297, 1, 100, "цветная", False),
    ProductTemplate("Евробуклет", 100, 210, 2, 100, "цветная", True),
    ProductTemplate("Календарь карманный", 100, 200, 1, 100, "цветная", True),
    ProductTemplate("Открытка", 148, 210, 1, 100, "цветная", True),
    ProductTemplate("Открытка в развороте", 210, 297, 2, 50, "цветная", True),
    ProductTemplate("Приглашение", 148, 210, 1, 50, "цветная", False),
    ProductTemplate("Сертификат", 210, 297, 1, 50, "цветная", False),
)

#: Прайс изделий: имя → диапазоны (legacy init_default_prices, строки 67–76).
_DEFAULT_PRODUCT_PRICES: dict[str, tuple[PriceRange, ...]] = {
    "Визитка": (
        PriceRange(1, 100, 4.0),
        PriceRange(101, 500, 3.0),
        PriceRange(501, None, 2.0),
    ),
    "Листовка А5": (
        PriceRange(1, 50, 8.0),
        PriceRange(51, 200, 5.0),
        PriceRange(201, None, 3.0),
    ),
    "Листовка А4": (
        PriceRange(1, 50, 12.0),
        PriceRange(51, 200, 8.0),
        PriceRange(201, None, 5.0),
    ),
}
_DEFAULT_RANGE: tuple[PriceRange, ...] = (PriceRange(1, None, 10.0),)


@dataclass(frozen=True)
class Operation:
    """Доп. операция (legacy STANDARD_OPERATIONS)."""

    key: str
    label: str
    unit: str  # «лист» | «копия» | «заказ»
    price: float


#: Доп. операции (legacy STANDARD_OPERATIONS, строки 43–50).
_DEFAULT_OPERATIONS: tuple[Operation, ...] = (
    Operation("lamination", "Ламинация", "лист", 1.5),
    Operation("folding", "Фальцовка", "лист", 0.3),
    Operation("cutting", "Резка", "лист", 2.0),
    Operation("rounding", "Скругление углов", "копия", 8.0),
    Operation("staple", "Скрепление скобой", "копия", 15.0),
    Operation("spring", "Переплёт на пружину", "копия", 70.0),
)


@dataclass(frozen=True)
class DigitalConfig:
    """Инъекционный конфиг Digital (замена legacy-глобалов и JSON-настроек)."""

    setup_cost: float = 100.0
    min_order_price: float = 500.0
    markup_default: float = 30.0
    papers: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_PAPERS))
    )
    ink: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_INK))
    )
    sheet_formats: Mapping[str, tuple[float, float]] = SHEET_FORMATS
    gap: float = GAP
    templates: tuple[ProductTemplate, ...] = _DEFAULT_TEMPLATES
    operations: tuple[Operation, ...] = _DEFAULT_OPERATIONS
    product_prices: Mapping[str, tuple[PriceRange, ...]] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_PRODUCT_PRICES))
    )

    def price_ranges(self, product_name: str) -> tuple[PriceRange, ...]:
        """Диапазоны прайса изделия (legacy: нет диапазонов → default 10 ₽)."""
        return self.product_prices.get(product_name, _DEFAULT_RANGE)

    def sheet_area_multiplier(self, sheet_format: str) -> float:
        """Множитель площади листа относительно A4 (legacy area_mult)."""
        sheet_w, sheet_h = self.sheet_formats.get(
            sheet_format, self.sheet_formats["A4"]
        )
        return sheet_w * sheet_h / (210 * 297)


__all__ = [
    "DigitalConfig",
    "Operation",
    "PriceRange",
    "ProductTemplate",
    "SHEET_FORMATS",
]
