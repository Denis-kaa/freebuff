"""Адаптеры «legacy-калькулятор → движок расхода» (ТЗ §26, §45).

Миграция: Legacy Calculator → Adapter → Consumption Engine, без массового
переписывания формул. Адаптер Wide строит Material + Policy из канонического
WideConfig-материала и возвращает MaterialConsumptionResult, который калькулятор
включает в CalcResult.details["consumption"].

Режимы адаптера Wide:
- "AREA" (дефолт) — текущее поведение: расход = площадь тиража (backward compat);
- "ROLL_NESTING" — opt-in: баннер/плёнка как рулон заданной ширины, расход по
  раскладке (pieces_across/rows/length). Ширина рулона передаётся вызывающим
  кодом (реестр материалов — Phase 3+; ТЗ §36 — Admin).
"""

from __future__ import annotations

from typing import Any

from printcalc.engine.consumption.engine import ConsumptionEngine
from printcalc.engine.consumption.models import (
    Material,
    MaterialConsumptionPolicy,
    MaterialConsumptionResult,
)
from printcalc.engine.errors import CalcInputError


def wide_material_consumption(
    *,
    width_mm: float,
    height_mm: float,
    quantity: float,
    roll_width_mm: float | None = None,
    policy_overrides: dict[str, Any] | None = None,
) -> MaterialConsumptionResult:
    """Расход материала для Wide (ТЗ §26).

    Входы — мм (конвертация из см — на вызывающей стороне: legacy Wide
    оперирует см). Без roll_width_mm — AREA-режим (паритет с текущим
    поведением wide/compute.py: area = Ш×В/10000×Q); с roll_width_mm —
    ROLL_NESTING (продакшн-расход по раскладке).
    """
    if width_mm <= 0 or height_mm <= 0 or quantity <= 0:
        raise CalcInputError("wide_material", "размеры и количество должны быть > 0")

    engine = ConsumptionEngine()
    overrides: dict[str, Any] = dict(policy_overrides or {})

    if roll_width_mm is not None:
        if roll_width_mm <= 0:
            raise CalcInputError("roll_width", "ширина рулона должна быть > 0")
        material = Material(
            id="wide_roll",
            name="Широкоформат: рулонный материал",
            consumption_mode="ROLL_NESTING",
            base_unit="lm",
            purchase_unit="m2",
            roll_width=roll_width_mm,
        )
        overrides.setdefault("mode", "ROLL_NESTING")
    else:
        material = Material(
            id="wide_area",
            name="Широкоформат: площадной материал",
            consumption_mode="AREA",
            base_unit="m2",
            purchase_unit="m2",
        )
        overrides.setdefault("mode", "AREA")

    policy = MaterialConsumptionPolicy(material_id=material.id, **overrides)
    return engine.calculate(
        material,
        {"width": width_mm, "height": height_mm, "quantity": quantity},
        policy,
    )


def compare_with_legacy(
    *,
    width_cm: float,
    height_cm: float,
    qty: float,
    roll_width_mm: float | None = None,
) -> dict[str, Any]:
    """Сравнение «legacy result vs engine result» (ТЗ §44, Phase 2).

    Legacy-расход: area = (Ш×В)/10000×Q (м²), периметр — wide_format.py:665.
    Расхождения регистрируются явно, не маскируются.
    """
    legacy_area_m2 = (width_cm * height_cm) / 10000.0 * qty
    result = wide_material_consumption(
        width_mm=width_cm * 10.0,
        height_mm=height_cm * 10.0,
        quantity=qty,
        roll_width_mm=roll_width_mm,
    )
    engine_area_m2 = result.to_dict()["production_area_m2"]
    return {
        "legacy_area_m2": legacy_area_m2,
        "engine_area_m2": engine_area_m2,
        "differs": abs(legacy_area_m2 - float(engine_area_m2)) > 1e-9,
        "engine_mode": result.layout.get("mode", "ROLL_NESTING"),
        "orientation": result.orientation,
        "waste_area_m2": result.to_dict()["waste_area_m2"],
    }


__all__ = ["compare_with_legacy", "wide_material_consumption"]
