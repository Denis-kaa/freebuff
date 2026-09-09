"""Тесты рулонной раскладки — ТЗ §43 Test 1, 2, 9, 10, 11."""

from __future__ import annotations

import pytest

from printcalc.engine.consumption import (
    ConsumptionEngine,
    ConsumptionError,
    Material,
    MaterialConsumptionPolicy,
)


def _film(roll_width: float = 1000.0) -> Material:
    return Material(
        id="film_white",
        name="Самоклеящаяся плёнка",
        consumption_mode="ROLL_NESTING",
        base_unit="lm",
        purchase_unit="lm",
        roll_width=roll_width,
    )


# Test 1: roll=1000, piece=700×800, qty=1 → across=1, rows=1, length=800, area=0.8, waste=0.24
def test_golden_single_piece() -> None:
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(material_id="film_white", mode="ROLL_NESTING"),
    )
    assert result.pieces_across == 1
    assert result.rows == 1
    assert result.production_length == pytest.approx(800.0)
    assert result.production_area == pytest.approx(800_000.0)  # мм² = 0.8 м²
    assert result.waste_area == pytest.approx(240_000.0)  # 0.24 м²
    assert result.waste_percent == pytest.approx(30.0)
    assert result.orientation == "700x800"


# Test 2: roll=1000, piece=400×500, qty=5 → across=2, rows=3, length=1500, area=1.5
def test_golden_multi_piece() -> None:
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 400.0, "height": 500.0, "quantity": 5.0},
        MaterialConsumptionPolicy(material_id="film_white", mode="ROLL_NESTING"),
    )
    assert result.pieces_across == 2
    assert result.rows == 3
    assert result.production_length == pytest.approx(1500.0)
    assert result.production_area == pytest.approx(1_500_000.0)
    # Площадь изделий 5×0.4×0.5 = 1.0 м² → отход 0.5 м²
    assert result.product_area == pytest.approx(1_000_000.0)
    assert result.waste_area == pytest.approx(500_000.0)


# Test 9 (обновлён 2026-09-09, правило владельца): изделие шире рулона —
# разворачивается (ширина↔высота) и считается повёрнутым; ошибка только если
# не влезает НИ прямо, НИ поворотом (см. test_product_does_not_fit_at_all).
def test_product_wider_than_roll_is_rotated() -> None:
    result = ConsumptionEngine().calculate(
        _film(1000.0),
        {"width": 1200.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(material_id="film_white", mode="ROLL_NESTING"),
    )
    assert result.orientation == "800x1200"
    assert result.production_area == pytest.approx(1_200_000.0)
    assert any("повёрнутым" in w for w in result.warnings)


def test_product_does_not_fit_at_all() -> None:
    """Ни прямо, ни поворотом — честная ошибка, не приблизительный результат."""
    with pytest.raises(ConsumptionError) as exc:
        ConsumptionEngine().calculate(
            _film(1000.0),
            {"width": 1200.0, "height": 1300.0, "quantity": 1.0},
            MaterialConsumptionPolicy(material_id="film_white", mode="ROLL_NESTING"),
        )
    assert exc.value.code == "PRODUCT_DOES_NOT_FIT"


def test_product_fits_only_rotated() -> None:
    """800×1200 на рулон 1000: портрет 800 помещается, альбом 1200 — нет."""
    result = ConsumptionEngine().calculate(
        _film(1000.0),
        {"width": 800.0, "height": 1200.0, "quantity": 1.0},
        MaterialConsumptionPolicy(material_id="film_white", mode="ROLL_NESTING"),
    )
    assert result.orientation == "800x1200"
    assert result.pieces_across == 1


# Test 10: точное заполнение roll=1000, piece=500, qty=2 → отхода по ширине нет
def test_exact_width_fill() -> None:
    result = ConsumptionEngine().calculate(
        _film(1000.0),
        {"width": 500.0, "height": 700.0, "quantity": 2.0},
        MaterialConsumptionPolicy(material_id="film_white", mode="ROLL_NESTING"),
    )
    assert result.pieces_across == 2
    assert result.rows == 1
    assert result.unusable_width == pytest.approx(0.0)


# Test 11: граница roll=1000, piece=501 → across=1, а не 2
def test_boundary_floor() -> None:
    result = ConsumptionEngine().calculate(
        _film(1000.0),
        {"width": 501.0, "height": 700.0, "quantity": 2.0},
        MaterialConsumptionPolicy(material_id="film_white", mode="ROLL_NESTING"),
    )
    assert result.pieces_across == 1
    assert result.rows == 2
