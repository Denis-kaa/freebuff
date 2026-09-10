"""Канонические константы ЧПУ — дословный перенос из legacy-исходника.

Источник: «Калькулятор фрезерной и лазерной резки/cnc_calc.py», строки
15–61 (default_settings: materials 13 позиций, cut_rates 26 ставок),
UI-формулы updatePrice() (строки 397–427): рез = длина × ставка ₽/м ×
кол-во; материал = ширина×длина × ₽/м² × кол-во; ИТОГО = рез + материал.
Legacy НЕ содержит наценку/налог/минималку — портируем как есть.
Golden-тесты закрепляют значения: менять только осознанно, новой
редакцией конфига.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Станки (legacy select id="machine", строка 218).
MACHINES: tuple[tuple[str, str], ...] = (("laser", "Лазер"), ("frezer", "Фрезер"))


@dataclass(frozen=True)
class SheetMaterial:
    """Листовой материал ЧПУ (элемент legacy materials)."""

    name: str
    thickness: float
    price_per_sqm: float


@dataclass(frozen=True)
class CutRate:
    """Ставка реза (элемент legacy cut_rates)."""

    machine: str
    material: str
    thickness: float
    price_per_meter: float


_DEFAULT_MATERIALS: tuple[SheetMaterial, ...] = (
    SheetMaterial("Фанера", 3, 300),
    SheetMaterial("Фанера", 6, 450),
    SheetMaterial("Фанера", 10, 700),
    SheetMaterial("Фанера", 12, 900),
    SheetMaterial("Фанера", 18, 1200),
    SheetMaterial("Акрил (оргстекло)", 3, 800),
    SheetMaterial("Акрил (оргстекло)", 4, 1000),
    SheetMaterial("Акрил (оргстекло)", 5, 1300),
    SheetMaterial("ПВХ", 3, 500),
    SheetMaterial("ПВХ", 4, 650),
    SheetMaterial("ПВХ", 5, 800),
    SheetMaterial("Композит", 4, 1500),
    SheetMaterial("Композит", 5, 1900),
)

_DEFAULT_CUT_RATES: tuple[CutRate, ...] = (
    CutRate("laser", "Фанера", 3, 15),
    CutRate("laser", "Фанера", 6, 25),
    CutRate("laser", "Фанера", 10, 40),
    CutRate("laser", "Фанера", 12, 55),
    CutRate("laser", "Фанера", 18, 80),
    CutRate("laser", "Акрил (оргстекло)", 3, 20),
    CutRate("laser", "Акрил (оргстекло)", 4, 30),
    CutRate("laser", "Акрил (оргстекло)", 5, 40),
    CutRate("laser", "ПВХ", 3, 15),
    CutRate("laser", "ПВХ", 4, 20),
    CutRate("laser", "ПВХ", 5, 25),
    CutRate("laser", "Композит", 4, 35),
    CutRate("laser", "Композит", 5, 45),
    CutRate("frezer", "Фанера", 3, 20),
    CutRate("frezer", "Фанера", 6, 35),
    CutRate("frezer", "Фанера", 10, 55),
    CutRate("frezer", "Фанера", 12, 75),
    CutRate("frezer", "Фанера", 18, 100),
    CutRate("frezer", "Акрил (оргстекло)", 3, 25),
    CutRate("frezer", "Акрил (оргстекло)", 4, 35),
    CutRate("frezer", "Акрил (оргстекло)", 5, 50),
    CutRate("frezer", "ПВХ", 3, 20),
    CutRate("frezer", "ПВХ", 4, 30),
    CutRate("frezer", "ПВХ", 5, 40),
    CutRate("frezer", "Композит", 4, 45),
    CutRate("frezer", "Композит", 5, 60),
)


@dataclass(frozen=True)
class CncConfig:
    """Инъекционный конфиг ЧПУ (замена legacy cnc_settings.json).

    Поведение «нет ставки»: материал есть в справочнике, но ставки реза
    для пары станок/материал/толщина нет — рез считается 0 (с warning),
    материал считается (parity updatePrice(), строки 399–427).
    """

    materials: tuple[SheetMaterial, ...] = _DEFAULT_MATERIALS
    cut_rates: tuple[CutRate, ...] = _DEFAULT_CUT_RATES

    def material(self, name: str, thickness: float) -> SheetMaterial | None:
        """Материал по имени и толщине (legacy find: name === && thickness ==)."""
        for m in self.materials:
            if m.name == name and m.thickness == thickness:
                return m
        return None

    def rate(self, machine: str, material: str, thickness: float) -> CutRate | None:
        """Ставка реза по станку/материалу/толщине (legacy getCurrentRate)."""
        for r in self.cut_rates:
            if r.machine == machine and r.material == material and r.thickness == thickness:
                return r
        return None

    def thickness_options(self, machine: str, material: str) -> tuple[float, ...]:
        """Доступные толщины (legacy fillThicknessSelect, отсортированы)."""
        return tuple(
            sorted({r.thickness for r in self.cut_rates if r.machine == machine and r.material == material})
        )

    def material_names(self) -> tuple[str, ...]:
        """Уникальные имена материалов (legacy fillMaterialSelect)."""
        return tuple(dict.fromkeys(m.name for m in self.materials))


#: Уникальные имена материалов для опций UI-спеки (без инстанса конфига).
DEFAULT_MATERIAL_NAMES: tuple[str, ...] = tuple(
    dict.fromkeys(m.name for m in _DEFAULT_MATERIALS)
)

__all__ = [
    "CncConfig",
    "CutRate",
    "DEFAULT_MATERIAL_NAMES",
    "MACHINES",
    "SheetMaterial",
]
