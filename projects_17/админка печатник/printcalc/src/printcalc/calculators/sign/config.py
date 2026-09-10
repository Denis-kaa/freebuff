"""Канонические константы Вывесок — дословный перенос из legacy-исходника.

Источник: «Общий калькулятор печати/build_all/sign_calc.py», строки 21–74
(MATERIALS, FRAME_PRICES, IMAGE_PRICES, BASE_MODELS, PRODUCT_MODEL,
PRODUCT_UNIT, PART_DEFAULTS, PRICE_PER_CM, MOUNT_*, ELECTRIC_*,
POWER_SUPPLY_COST, SUBSTRATE_WORK_RATE, FRAME_WORK_RATE, DELIVERY_PER_KM,
TAX_RATE, DEFAULT_MARKUP) + коэффициенты из calculate() (строки 782–930):
отношение ширины буквы 0.7, ставки подсветки 900/450 при длине 0.6,
комплексность Простой/Средний/Сложный = 1.0/1.3/1.6.
Golden-тесты закрепляют значения: менять только осознанно, новой редакцией.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

#: Материалы листовые: имя → ₽/м² (legacy MATERIALS, строка 22).
_DEFAULT_MATERIALS: dict[str, float] = {
    "ПВХ 3мм": 350.0,
    "ПВХ 5мм": 450.0,
    "ПВХ 10мм": 700.0,
    "Акрил 3мм": 1500.0,
    "Акрил 5мм": 2200.0,
    "Композит 3мм": 1800.0,
    "Алюкобонд 4мм": 2300.0,
}

#: Каркасы: имя → ₽/м (legacy FRAME_PRICES, строка 25).
_DEFAULT_FRAME_PRICES: dict[str, float] = {
    "Металлический": 300.0,
    "Профтруба": 350.0,
    "Деревянный": 200.0,
}

#: Нанесение изображения: имя → ₽/м² (legacy IMAGE_PRICES, строка 26).
_DEFAULT_IMAGE_PRICES: dict[str, float] = {
    "Без нанесения": 0.0,
    "УФ-печать": 1200.0,
    "Аппликация плёнкой": 600.0,
}


@dataclass(frozen=True)
class ModelSpec:
    """Базовая модель изделия (элемент legacy BASE_MODELS)."""

    light: bool
    work_rate: float


@dataclass(frozen=True)
class PartSpec:
    """Дефолтные детали изделия (элемент legacy PART_DEFAULTS)."""

    front: str | None
    side: str | None
    back: str | None
    side_height: float


#: Модели: имя → световая/ставка работы ₽/м² (legacy BASE_MODELS, строки 29–35).
_DEFAULT_BASE_MODELS: dict[str, ModelSpec] = {
    "Наличная буква": ModelSpec(light=False, work_rate=1000.0),
    "Объёмная буква": ModelSpec(light=False, work_rate=1500.0),
    "Световая буква контражур": ModelSpec(light=True, work_rate=2500.0),
    "Световая буква с подсветкой": ModelSpec(light=True, work_rate=3000.0),
    "Световой короб": ModelSpec(light=True, work_rate=1800.0),
}

#: Типы изделий → модель (legacy PRODUCT_MODEL, строки 38–44).
_DEFAULT_PRODUCT_MODEL: dict[str, str] = {
    "Наличная буква": "Наличная буква",
    "Объёмная несветовая буква": "Объёмная буква",
    "Световая буква контражур": "Световая буква контражур",
    "Световая буква с подсветкой": "Световая буква с подсветкой",
    "Световой короб": "Световой короб",
}

#: Тип изделий → единица расчёта: «cm» (буквы) | «sqm» (короб) (legacy PRODUCT_UNIT).
_DEFAULT_PRODUCT_UNIT: dict[str, str] = {
    "Наличная буква": "cm",
    "Объёмная несветовая буква": "cm",
    "Световая буква контражур": "cm",
    "Световая буква с подсветкой": "cm",
    "Световой короб": "sqm",
}

#: Дефолтные детали по типу (legacy PART_DEFAULTS, строки 47–53).
_DEFAULT_PART_DEFAULTS: dict[str, PartSpec] = {
    "Наличная буква": PartSpec("ПВХ 3мм", None, None, 0.0),
    "Объёмная буква": PartSpec("ПВХ 10мм", "ПВХ 5мм", "ПВХ 10мм", 0.05),
    "Световая буква контражур": PartSpec("Акрил 3мм", "ПВХ 5мм", "ПВХ 10мм", 0.05),
    "Световая буква с подсветкой": PartSpec("Акрил 3мм", "ПВХ 5мм", "ПВХ 10мм", 0.05),
    "Световой короб": PartSpec("Акрил 3мм", "Композит 3мм", "Алюкобонд 4мм", 0.1),
}

#: Прайс за единицу (legacy PRICE_PER_CM): 0 = режим «по себестоимости».
_DEFAULT_PRICE_PER_UNIT: dict[str, float] = {
    "Наличная буква": 0.0,
    "Объёмная несветовая буква": 0.0,
    "Световая буква контражур": 0.0,
    "Световая буква с подсветкой": 0.0,
    "Световой короб": 0.0,
}

#: Монтаж: варианты и процент надбавки по высоте (legacy MOUNT_*).
MOUNT_VARIANTS: tuple[str, ...] = ("нет", "до 2 м", "2-3 м", "3-5 м", "от 5 м")
_DEFAULT_MOUNT_PERCENTS: dict[str, float] = {
    "до 2 м": 0.0,
    "2-3 м": 10.0,
    "3-5 м": 20.0,
    "от 5 м": 30.0,
}

#: Комплексность (legacy calculate, строка 789).
COMPLEXITY_FACTORS: Mapping[str, float] = MappingProxyType(
    {"Простой": 1.0, "Средний": 1.3, "Сложный": 1.6}
)


@dataclass(frozen=True)
class SignConfig:
    """Инъекционный конфиг Вывесок (замена legacy-глобалов и JSON-настроек)."""

    #: Материалы/каркасы/нанесение.
    materials: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_MATERIALS))
    )
    frame_prices: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_FRAME_PRICES))
    )
    image_prices: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_IMAGE_PRICES))
    )

    #: Модели/типы/детали/прайс за единицу.
    base_models: Mapping[str, ModelSpec] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_BASE_MODELS))
    )
    product_model: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_PRODUCT_MODEL))
    )
    product_unit: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_PRODUCT_UNIT))
    )
    part_defaults: Mapping[str, PartSpec] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_PART_DEFAULTS))
    )
    price_per_unit: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_PRICE_PER_UNIT))
    )

    #: Монтаж/электрика/блоки (legacy строки 58–68).
    mount_base_cost: float = 3500.0
    mount_percents: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType(dict(_DEFAULT_MOUNT_PERCENTS))
    )
    electric_base_cost: float = 800.0
    electric_per_meter: float = 350.0
    power_supply_cost: float = 1200.0

    #: Прочие ставки (legacy строки 71–74) + коэффициенты расчёта.
    substrate_work_rate: float = 500.0
    frame_work_rate: float = 400.0
    delivery_per_km: float = 40.0
    markup_default: float = 25.0
    tax_rate: float = 0.06
    letter_width_ratio: float = 0.7
    box_light_rate: float = 900.0
    letter_light_rate: float = 450.0
    letter_light_length: float = 0.6
    unknown_material_price: float = 200.0
    default_frame_price: float = 300.0
    default_substrate_price: float = 700.0

    def parts_for(self, product: str) -> PartSpec:
        """Детали изделия: по типу, иначе по модели (legacy строки 811–812)."""
        spec = self.part_defaults.get(product)
        if spec is not None:
            return spec
        model = self.product_model.get(product, product)
        return self.part_defaults.get(
            model, PartSpec(None, None, None, 0.0)
        )

    def material_price(self, name: str, fallback: float) -> float:
        """Цена материала (legacy get_price/MATERIALS.get с fallback)."""
        return self.materials.get(name, fallback)


__all__ = [
    "COMPLEXITY_FACTORS",
    "MOUNT_VARIANTS",
    "ModelSpec",
    "PartSpec",
    "SignConfig",
]
