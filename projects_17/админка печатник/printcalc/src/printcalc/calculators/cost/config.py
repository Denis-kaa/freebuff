"""Канонические константы Себестоимости — дословный перенос из legacy.

Источник: «Калькулятор себестоимости/universal_calc.py» + equipment.json.
Три источника затрат (строки 432–439, 560–576):
    machine_hour = price/(life_years·hours_year)                (амортизация)
                 + maintenance_month·12/(life_years·hours_year) (сервис)
                 + electricity_kw·tariff_kw                     (электричество)
    overhead_per_hour = (аренда+коммуналка+офис+реклама+связь+прочее)
                        / ((hours_year/12)·load_factor · N_станков)
    labor = operator_rate · hours;   total = mat + cons + machine + labor + OH
    price = total · (1 + markup/100)   — наценка ДЕФОЛТ 30% (строка 201)
Режимы станков: wide (₽/м² + чернила ₽/мл на м²), digital (листы: тонер
мл/лист · ₽/мл; раскладка custom-размера), offset (краска л/1000 + мастер
НА ЛИСТ-ЗАДАЧУ), lamination (₽/м² площади, consumables=0).
Golden-тесты закрепляют значения: менять только осознанно, новой редакцией.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

#: Форматы листа (legacy PAPER_SIZES_MM, строки 9–18).
PAPER_SIZES_MM: dict[str, tuple[float, float]] = {
    "A7": (74.0, 105.0),
    "A6": (105.0, 148.0),
    "A5": (148.0, 210.0),
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
    "A0": (841.0, 1189.0),
}

#: Режимы станков (legacy kind).
KINDS: tuple[str, ...] = ("wide", "digital", "offset", "lamination")


@dataclass(frozen=True)
class MaterialSpec:
    """Материал станка (элемент legacy materials)."""

    cost_unit: float  # ₽ за единицу (м²/лист)
    speed: float  # производительность (unit/час)
    ink_per_unit: float = 0.0  # чернила мл/м² (только wide)


@dataclass(frozen=True)
class Equipment:
    """Станок (элемент legacy equipment.json)."""

    name: str
    kind: str  # wide / digital / offset / lamination
    price: float
    life_years: float
    hours_year: float
    maintenance_month: float
    electricity_kw: float
    tariff_kw: float
    unit: str
    default_speed: float
    materials: dict[str, MaterialSpec]
    ink_per_ml: float = 0.0  # wide
    toner_per_page: float = 0.0  # digital
    toner_price_per_ml: float = 0.0  # digital
    ink_price_per_liter: float = 0.0  # offset
    ink_per_1000: float = 20.0  # offset (дефолт legacy get)
    master_price: float = 0.0  # offset

    @property
    def hours_life(self) -> float:
        return self.life_years * self.hours_year

    def machine_hour_cost(self) -> float:
        """Себестоимость машино-часа (legacy machine_hour_cost, строки 432–439)."""
        if self.hours_life <= 0:
            return 0.0
        amort = self.price / self.hours_life
        maint = self.maintenance_month * 12 / self.hours_life
        elec = self.electricity_kw * self.tariff_kw
        return amort + maint + elec


@dataclass(frozen=True)
class EconomicsDefaults:
    """Экономика цеха — дефолты GUI (строки 192–202)."""

    rent: float = 30000.0
    communal: float = 8000.0
    admin_salary: float = 25000.0
    advertising: float = 5000.0
    comm_internet: float = 3000.0
    other: float = 9000.0
    load_factor: float = 0.8
    operator_rate: float = 300.0
    markup_percent: float = 30.0
    waste_percent: float = 0.0

    @property
    def total_overhead(self) -> float:
        """Сумма накладных за месяц (legacy 456–459)."""
        return (
            self.rent
            + self.communal
            + self.admin_salary
            + self.advertising
            + self.comm_internet
            + self.other
        )


def _material(raw: dict[str, object]) -> MaterialSpec:
    return MaterialSpec(
        cost_unit=float(raw.get("cost_unit", 0.0)),  # type: ignore[arg-type]
        speed=float(raw.get("speed", 0.0)),  # type: ignore[arg-type]
        ink_per_unit=float(raw.get("ink_per_unit", 0.0)),  # type: ignore[arg-type]
    )


def _equipment(name: str, raw: dict[str, object]) -> Equipment:
    materials_raw = raw.get("materials") or {}
    assert isinstance(materials_raw, dict)
    materials = {m_name: _material(m_raw) for m_name, m_raw in materials_raw.items()}
    return Equipment(
        name=name,
        kind=str(raw["kind"]),
        price=float(raw["price"]),  # type: ignore[arg-type]
        life_years=float(raw["life_years"]),  # type: ignore[arg-type]
        hours_year=float(raw["hours_year"]),  # type: ignore[arg-type]
        maintenance_month=float(raw["maintenance_month"]),  # type: ignore[arg-type]
        electricity_kw=float(raw["electricity_kw"]),  # type: ignore[arg-type]
        tariff_kw=float(raw["tariff_kw"]),  # type: ignore[arg-type]
        unit=str(raw.get("unit", "")),
        default_speed=float(raw.get("default_speed", 10.0)),  # type: ignore[arg-type]
        materials=materials,
        ink_per_ml=float(raw.get("ink_per_ml", 0.0)),  # type: ignore[arg-type]
        toner_per_page=float(raw.get("toner_per_page", 0.0)),  # type: ignore[arg-type]
        toner_price_per_ml=float(raw.get("toner_price_per_ml", 0.0)),  # type: ignore[arg-type]
        ink_price_per_liter=float(raw.get("ink_price_per_liter", 0.0)),  # type: ignore[arg-type]
        ink_per_1000=float(raw.get("ink_per_1000", 20.0)),  # type: ignore[arg-type]
        master_price=float(raw.get("master_price", 0.0)),  # type: ignore[arg-type]
    )


def default_equipment() -> dict[str, Equipment]:
    """Каноническая база станков — дословный перенос equipment.json."""
    raw = json.loads(
        (Path(__file__).parent / "equipment_data.json").read_text(encoding="utf-8")
    )
    return {name: _equipment(name, eq_raw) for name, eq_raw in raw.items()}


@dataclass(frozen=True)
class CostConfig:
    """Инъекционный конфиг Себестоимости (замена legacy settings.json)."""

    equipment: dict[str, Equipment] | None = None
    economics: EconomicsDefaults = EconomicsDefaults()

    def __post_init__(self) -> None:
        if self.equipment is None:
            object.__setattr__(self, "equipment", default_equipment())

    def total_machine_hours_per_month(self) -> float:
        """Сумма машино-часов всех станков за месяц (legacy 442–448)."""
        assert self.equipment is not None
        total = 0.0
        for eq in self.equipment.values():
            total += (eq.hours_year / 12) * self.economics.load_factor
        return total


__all__ = [
    "CostConfig",
    "EconomicsDefaults",
    "Equipment",
    "KINDS",
    "MaterialSpec",
    "PAPER_SIZES_MM",
    "default_equipment",
]
