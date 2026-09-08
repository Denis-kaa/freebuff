"""Тесты биллинга — ТЗ §43 Test 6 + минимальные расход/оплаты (§18, §6, §19)."""

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


# Test 6: production = 0.8 lm, minimum = 1 lm →
# production остаётся 0.8, billing = 1.0 (истинное значение НЕ подменяется, §18)
def test_min_billing_vs_production() -> None:
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            min_billing_consumption=1.0,
            min_billing_unit="lm",
        ),
    )
    # 700×800×1 на рулоне 1000: длина 800 мм = 0.8 м
    assert result.production_length == pytest.approx(800.0)
    assert result.billing_quantity == pytest.approx(1.0)
    assert result.billing_unit == "lm"
    assert any("минимальный оплачиваемый" in w for w in result.warnings)


def test_min_consumption_without_billing() -> None:
    """min_consumption фиксирует нижний порог расхода, billing — отдельно (§6)."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            min_consumption=1.0,
            min_consumption_unit="lm",
        ),
    )
    assert result.production_length == pytest.approx(800.0)  # факт сохранён
    assert result.billing_quantity == pytest.approx(1.0)
    assert any("минимальный расход" in w for w in result.warnings)


def test_values_not_mixed() -> None:
    """§56: «эти значения не смешиваются» — production < billing остаётся видимым."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            min_billing_consumption=1.0,
        ),
    )
    assert result.production_length < result.billing_quantity * 1000.0
    assert result.to_dict()["production_length_m"] == pytest.approx(0.8)
    assert result.to_dict()["billing_quantity"] == pytest.approx(1.0)


def test_rounding_ceil_to_step() -> None:
    """§19: 0.83 м при шаге 0.1 → 0.9; применяется только к billing (§40)."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 830.0, "quantity": 1.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            rounding_mode="CEIL_TO_STEP",
            rounding_step=0.1,
        ),
    )
    assert result.production_length == pytest.approx(830.0)  # факт — полная точность
    assert result.billing_quantity == pytest.approx(0.9)  # ceil(0.83/0.1)*0.1
    assert any("округлено" in w for w in result.warnings)


def test_big_order_not_billed_by_minimum() -> None:
    """Большой заказ: минимум не применяется, billing = production."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 10.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            min_billing_consumption=1.0,
        ),
    )
    # 700→across=1, rows=10, длина=8000 мм = 8 м > 1 м
    assert result.billing_quantity == pytest.approx(8.0)
    assert result.production_length == pytest.approx(8000.0)
