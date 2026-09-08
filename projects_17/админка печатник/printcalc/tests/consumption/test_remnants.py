"""Тесты остатков и расчётного следа — ТЗ §43 Test 12, §9, §22-23, §53."""

from __future__ import annotations

import pytest

from printcalc.engine.consumption import (
    ConsumptionEngine,
    Material,
    MaterialConsumptionPolicy,
)


def _film() -> Material:
    return Material(
        id="film_white",
        name="Плёнка",
        consumption_mode="ROLL_NESTING",
        base_unit="lm",
        roll_width=1000.0,
    )


# Test 12: классификация REMNANT/SCRAP по порогам политики (§22).
# Плёнка 1000, изделие 700×800, qty=1 → остаточная полоса 300×800 мм (0.24 м²).
def test_remnant_passes_thresholds() -> None:
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            remnant_min_width=200.0,
            remnant_min_length=500.0,
        ),
    )
    assert result.remnant is not None
    assert result.remnant.status == "REMNANT"
    assert result.remnant.width == pytest.approx(300.0)
    assert result.remnant.length == pytest.approx(800.0)
    assert result.remnant.area_mm2 == pytest.approx(240_000.0)


def test_scrap_below_width_threshold() -> None:
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            remnant_min_width=500.0,  # полоса 300 < 500 → SCRAP
        ),
    )
    assert result.remnant is not None
    assert result.remnant.status == "SCRAP"
    assert "ширина" in result.remnant.reason


def test_scrap_below_area_threshold() -> None:
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            remnant_min_area=300_000.0,  # 240_000 < 300_000 → SCRAP
        ),
    )
    assert result.remnant is not None
    assert result.remnant.status == "SCRAP"


def test_exact_width_fill_no_remnant() -> None:
    """Точное заполнение по ширине → остаточной полосы нет вообще."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 500.0, "height": 700.0, "quantity": 2.0},
        MaterialConsumptionPolicy(material_id="film_white", mode="ROLL_NESTING"),
    )
    assert result.unusable_width == pytest.approx(0.0)
    assert result.remnant is None


def test_remnant_not_auto_used() -> None:
    """§23: остаток только рассчитан/классифицирован — поля расхода не уменьшаются."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            remnant_min_width=200.0,
        ),
    )
    # REMNANT есть, но production_area = полная ширина × длина (0.8 м²), без скидок.
    assert result.remnant.status == "REMNANT"
    assert result.production_area == pytest.approx(800_000.0)


# ---------- Расчётный след: объяснимость «почему 0,8 м²» (§9, §53) ----------


def test_trace_explains_result() -> None:
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(material_id="film_white", mode="ROLL_NESTING"),
    )
    trace = [dict(step) for step in result.calculation_trace]
    steps = {step["step"] for step in trace}
    assert {"roll_width", "usable_width", "effective_piece", "pieces_across",
            "rows", "nesting_length", "production_area", "product_area",
            "waste_area", "waste_percent"} <= steps
    prod = next(step for step in trace if step["step"] == "production_area")
    assert prod["value_m2"] == pytest.approx(0.8)
    across = next(step for step in trace if step["step"] == "pieces_across")
    assert across["value"] == 1


def test_to_dict_boundary_units() -> None:
    """Граница API: площади в м², длины в м (§41, §40 — округление только на выводе)."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(material_id="film_white", mode="ROLL_NESTING"),
    )
    payload = result.to_dict()
    assert payload["product_area_m2"] == pytest.approx(0.56)
    assert payload["production_area_m2"] == pytest.approx(0.8)
    assert payload["production_length_m"] == pytest.approx(0.8)
    assert payload["waste_area_m2"] == pytest.approx(0.24)
    assert payload["waste_percent"] == pytest.approx(30.0)
    assert payload["pieces_across"] == 1
    assert payload["rows"] == 1
