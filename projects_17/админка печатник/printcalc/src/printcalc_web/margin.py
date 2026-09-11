"""Сшивка Себестоимость ↔ прайс-каталог (роадмап v6, «следующий шаг»).

Маржинальность = прайс vs себестоимость единицы. Себестоимость считается
ТОЛЬКО движком (cost-калькулятор, конфиг equipment_data.json) — никакой
дублирующей математики (Single Source of Truth).

BASIS:
    m2   — qty=1 означает 1 м² (wide-станки);
    page — qty=1 лист стандарта (digital);
    a4   — одна ламинация А4 (sheet_format=A4).
batch_qty — тираж партии, на которую делится себестоимость задачи
(мастер Riso — НА ЗАДАЧУ, поэтому offset-услуги считаются при каноническом
мин. тираже 500 шт; RisoConfig.min_order). Услуга без маршрута попадает в
gaps с ПРИЧИНОЙ (не молча), материалы реестра сравниваются с cost_unit
конфига станка (закупка vs учётная стоимость).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from printcalc.engine.registry import calculate as engine_calculate
from printcalc_web.calculators import get_registry
from printcalc_web.store import list_materials, list_price_items


@dataclass(frozen=True)
class CostRoute:
    """Маршрут себестоимости услуги: станок + материал + база + партия."""

    equipment: str
    material: str
    basis: str  # m2 / page / a4
    batch_qty: float = 1.0  # делитель себестоимости задачи (партия)


#: Канонический мин. тираж Riso (мастер на задачу — честная амортизация).
RISO_BATCH_QTY: float = 500.0

#: Карта «позиция прайса → маршрут себестоимости». Закрытый словарь
#: (ANTI-6b): услуга не из карты = gap с причиной, видимый владельцу.
SERVICE_COST_ROUTES: dict[str, CostRoute] = {
    "Ксерокопия ч/б А4": CostRoute("Riso RZ300EP", "Бумага А4 80г", "page", RISO_BATCH_QTY),
    "Ксерокопия ч/б А3": CostRoute("Riso RZ300EP", "Бумага А3 80г", "page", RISO_BATCH_QTY),
    "Цветная копия А4": CostRoute("Xerox Phaser 7760", "Бумага А4 80г", "page"),
    "Печать документа ч/б А4": CostRoute("Riso RZ300EP", "Бумага А4 80г", "page", RISO_BATCH_QTY),
    "Печать документа цветная А4": CostRoute("Xerox Phaser 7760", "Бумага А4 80г", "page"),
    "Печать ч/б А3": CostRoute("Riso RZ300EP", "Бумага А3 80г", "page", RISO_BATCH_QTY),
    "Ламинация документа": CostRoute(
        "Ламинатор Bulros FM650A", "Плёнка глянцевая 32 мкм", "a4"
    ),
    "Баннер (за м²)": CostRoute("Roland VP540", "Баннер (обычный)", "m2"),
}

#: Причины отсутствия маршрута для остальных услуг P0 (закрытый словарь).
SERVICE_GAP_REASONS: dict[str, str] = {
    "Фото 10×15": "нет фотобумаги в конфиге станков (пополнить equipment)",
    "Фото 15×21": "нет фотобумаги в конфиге станков (пополнить equipment)",
    "Фото 20×30": "нет фотобумаги в конфиге станков (пополнить equipment)",
    "Фото на документы (4 шт)": "составная услуга (съёмка + печать + резка)",
    "Фото на документы (6 шт)": "составная услуга (съёмка + печать + резка)",
    "Фото на документы (срочные)": "составная услуга (съёмка + печать + резка)",
    "Сканирование": "не станочная (труд оператора)",
    "Переплёт на пружину": "не станочная (ручная сборка)",
    "Люверс (установка)": "не станочная (ручная операция)",
    "Табличка ПВХ (от)": "составная (печать + основа ПВХ + резка)",
    "Дизайн макета (от)": "не станочная (труд дизайнера)",
    "Диск/флешка запись": "не станочная (материал + труд)",
}


def _unit_cost(route: CostRoute) -> dict[str, Any]:
    """Себестоимость ЕДИНИЦЫ услуги через движок (cost), делённая на партию."""
    inputs: dict[str, Any] = {
        "equipment": route.equipment,
        "material": route.material,
        "qty": route.batch_qty,
    }
    if route.basis == "a4":
        inputs["sheet_format"] = "A4"
    result = engine_calculate(get_registry(), "cost", inputs)
    return {
        "cost_unit": result.cost / route.batch_qty,
        "price_with_markup": result.price / route.batch_qty,
        "batch_qty": route.batch_qty,
    }


def margin_for_service(item: dict[str, Any]) -> dict[str, Any]:
    """Маржа одной позиции каталога: прайс vs себестоимость единицы."""
    route = SERVICE_COST_ROUTES[item["name"]]
    calc = _unit_cost(route)
    price = float(item["price"])
    cost = calc["cost_unit"]
    margin_abs = price - cost
    margin_pct = (margin_abs / price * 100.0) if price > 0 else None
    return {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "unit": item["unit"],
        "price": price,
        "cost_unit": round(cost, 2),
        "price_with_markup": round(calc["price_with_markup"], 2),
        "margin_abs": round(margin_abs, 2),
        "margin_pct": round(margin_pct, 1) if margin_pct is not None else None,
        "below_markup": price < calc["price_with_markup"],
        "batch_qty": calc["batch_qty"],
        "equipment": route.equipment,
        "material": route.material,
    }


def _norm_words(value: str) -> frozenset[str]:
    """Слова имени без регистра, ё→е (паритет опечаток legacy-конфига)."""
    return frozenset(value.lower().replace("ё", "е").split())


def _config_materials() -> dict[frozenset[str], tuple[str, str, float]]:
    """Индекс материалов cost-конфига: нормализованные слова → (станок, имя, cost_unit)."""
    from printcalc.calculators.cost.config import CostConfig

    cfg = CostConfig()
    assert cfg.equipment is not None
    index: dict[frozenset[str], tuple[str, str, float]] = {}
    for eq in cfg.equipment.values():
        for mat_name, spec in eq.materials.items():
            index[_norm_words(mat_name)] = (eq.name, mat_name, spec.cost_unit)
    return index


def material_margin(
    material: dict[str, Any], config_index: dict[frozenset[str], tuple[str, str, float]] | None = None
) -> dict[str, Any] | None:
    """Материал реестра vs учётная стоимость конфига (cost_unit).

    Сопоставление по нормализованному набору слов (порядок слов и ё/е не
    важны — паритет «Плёнка самоклеящаяся»/«Самоклеющаяся плёнка»).
    """
    index = config_index if config_index is not None else _config_materials()
    keys = [_norm_words(material["name"])]
    keys += [_norm_words(str(a)) for a in material.get("aliases", [])]
    for key in keys:
        hit = index.get(key)
        if hit is not None:
            equipment, mat_name, cost_unit = hit
            purchase = float(material.get("purchase_cost") or 0.0)
            return {
                "id": material["id"],
                "name": material["name"],
                "purchase_cost": purchase,
                "needs_fill": purchase <= 0,
                "config_cost_unit": cost_unit,
                "equipment": equipment,
                "config_material": mat_name,
                "delta": round(purchase - cost_unit, 2),
            }
    return None


def margin_report(conn: sqlite3.Connection) -> dict[str, Any]:
    """Полный отчёт: маржа услуг с маршрутом + gaps с причинами + материалы."""
    items = list_price_items(conn)
    routed: list[dict[str, Any]] = []
    service_gaps: list[dict[str, Any]] = []
    for item in items:
        name = item["name"]
        if name in SERVICE_COST_ROUTES:
            routed.append(margin_for_service(item))
        else:
            reason = SERVICE_GAP_REASONS.get(name) or "маршрут не задан (заполнить карту)"
            service_gaps.append(
                {"id": item["id"], "name": name, "price": item["price"], "reason": reason}
            )

    config_index = _config_materials()
    material_gaps: list[dict[str, Any]] = []
    material_rows: list[dict[str, Any]] = []
    for material in list_materials(conn):
        row = material_margin(material, config_index)
        if row is None:
            material_gaps.append({"id": material["id"], "name": material["name"]})
        else:
            material_rows.append(row)

    with_pct = [r for r in routed if r["margin_pct"] is not None]
    return {
        "services": sorted(routed, key=lambda r: r["margin_pct"] or 0.0),
        "service_gaps": service_gaps,
        "materials": material_rows,
        "material_gaps": material_gaps,
        "summary": {
            "routed": len(routed),
            "gaps": len(service_gaps),
            "avg_margin_pct": round(
                sum(r["margin_pct"] for r in with_pct) / max(1, len(with_pct)), 1
            ),
            "below_markup": sum(1 for r in routed if r["below_markup"]),
        },
    }


__all__ = [
    "CostRoute",
    "RISO_BATCH_QTY",
    "SERVICE_COST_ROUTES",
    "SERVICE_GAP_REASONS",
    "margin_for_service",
    "margin_report",
    "material_margin",
]
