"""Тесты адаптера Wide (Phase 2): паритет AREA + расхождение ROLL_NESTING (ТЗ §26, §44-45)."""

from __future__ import annotations

import pytest

from printcalc.engine.consumption.adapters import (
    compare_with_legacy,
    wide_material_consumption,
)
from printcalc.engine.errors import CalcInputError


# ---------- AREA-режим: паритет с legacy wide (backward compat, §45) ----------


def test_area_mode_matches_legacy() -> None:
    """AREA: расход = площадь тиража (wide_format.py:665): 300×100 см × 2 = 6.0 м²."""
    result = wide_material_consumption(
        width_mm=3000.0, height_mm=1000.0, quantity=2.0
    )
    payload = result.to_dict()
    assert payload["production_area_m2"] == pytest.approx(6.0)
    assert payload["product_area_m2"] == pytest.approx(6.0)
    assert payload["waste_area_m2"] == pytest.approx(0.0)


def test_area_mode_with_waste_percent() -> None:
    """waste_percent — дополнительное правило владельца (§4 ТЗ), не заменяет раскрой."""
    result = wide_material_consumption(
        width_mm=3000.0,
        height_mm=1000.0,
        quantity=2.0,
        policy_overrides={"waste_percent": 10.0},
    )
    payload = result.to_dict()
    assert payload["production_area_m2"] == pytest.approx(6.6)
    assert payload["waste_area_m2"] == pytest.approx(0.6)


# ---------- ROLL_NESTING: расход по раскладке, отличается от legacy ----------


def test_roll_mode_spec_example() -> None:
    """Пример ТЗ §14/§56: рулон 1000, изделие 700×800, qty=1 → 0.8 м², отход 0.24."""
    result = wide_material_consumption(
        width_mm=700.0,
        height_mm=800.0,
        quantity=1.0,
        roll_width_mm=1000.0,
    )
    payload = result.to_dict()
    assert payload["production_area_m2"] == pytest.approx(0.8)
    assert payload["waste_area_m2"] == pytest.approx(0.24)
    assert payload["waste_percent"] == pytest.approx(30.0)
    assert payload["pieces_across"] == 1


def test_compare_registers_divergence() -> None:
    """§44: расхождения legacy vs engine регистрируются явно.

    Рулон 1000, 700×800×1: legacy дал бы 0.56 м² (площадь изделия),
    engine — 0.8 м² (фактический расход). differ = True — это и есть смысл.
    """
    report = compare_with_legacy(
        width_cm=70.0, height_cm=80.0, qty=1.0, roll_width_mm=1000.0
    )
    assert report["legacy_area_m2"] == pytest.approx(0.56)
    assert report["engine_area_m2"] == pytest.approx(0.8)
    assert report["differs"] is True

    # AREA-режим: расхождения нет.
    report_area = compare_with_legacy(width_cm=70.0, height_cm=80.0, qty=1.0)
    assert report_area["differs"] is False
    assert report_area["engine_area_m2"] == pytest.approx(0.56)


# ---------- Ошибки ----------


def test_invalid_dimensions_rejected() -> None:
    with pytest.raises(CalcInputError):
        wide_material_consumption(width_mm=0.0, height_mm=800.0, quantity=1.0)


def test_invalid_roll_width_rejected() -> None:
    with pytest.raises(CalcInputError):
        wide_material_consumption(
            width_mm=700.0,
            height_mm=800.0,
            quantity=1.0,
            roll_width_mm=-5.0,
        )
