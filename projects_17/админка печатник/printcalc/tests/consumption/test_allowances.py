"""Тесты припусков и технологических длин — ТЗ §43 Test 4, 5, 7, 8."""

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


# Test 4: gap_x/gap_y влияют на раскладку.
# Плёнка 1000, изделие 480×500, qty=4:
#   без зазора: across = floor(1000/480) = 2, rows = 2, длина = 1000
#   gap_x=40:   step = 520 → across = floor(1000/520) = 1, rows = 4, длина = 2000
def test_gap_changes_layout() -> None:
    base = ConsumptionEngine().calculate(
        _film(),
        {"width": 480.0, "height": 500.0, "quantity": 4.0},
        MaterialConsumptionPolicy(material_id="film_white", mode="ROLL_NESTING"),
    )
    assert base.pieces_across == 2
    assert base.production_length == pytest.approx(1000.0)

    gapped = ConsumptionEngine().calculate(
        _film(),
        {"width": 480.0, "height": 500.0, "quantity": 4.0},
        MaterialConsumptionPolicy(
            material_id="film_white", mode="ROLL_NESTING", gap_x=40.0
        ),
    )
    assert gapped.pieces_across == 1
    assert gapped.rows == 4
    assert gapped.production_length == pytest.approx(2000.0)


def test_gap_y_extends_length() -> None:
    """gap_y добавляется между рядами: 3 ряда по 300 + 2 зазора по 100 = 1100."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 500.0, "height": 300.0, "quantity": 6.0},
        MaterialConsumptionPolicy(
            material_id="film_white", mode="ROLL_NESTING", gap_y=100.0
        ),
    )
    assert result.pieces_across == 2
    assert result.rows == 3
    # (3−1)·(300+100) + 300 = 1100
    assert result.production_length == pytest.approx(1100.0)


# Test 5: bleed_left/right/top/bottom увеличивают эффективные размеры.
# Плёнка 1000, изделие 700×800, qty=1, bleed 10 со всех сторон:
#   effective = 720×820 → across = 1, длина = 820
def test_bleed_effective_dimensions() -> None:
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            bleed_left=10.0,
            bleed_right=10.0,
            bleed_top=10.0,
            bleed_bottom=10.0,
        ),
    )
    assert result.pieces_across == 1
    assert result.production_length == pytest.approx(820.0)
    trace = [dict(step) for step in result.calculation_trace]
    eff = next(step for step in trace if step["step"] == "effective_piece")
    assert eff["value"] == "720x820"


def test_bleed_blocks_rotation_benefit() -> None:
    """Bleed может сделать поворот невыгодным — движок честно пересчитывает оба."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 600.0, "height": 400.0, "quantity": 4.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            bleed_left=150.0,
            bleed_right=150.0,
        ),
    )
    # A: 900×400 → across=1, rows=4, длина=1600; B: 400×900 → across=2, rows=2,
    # длина=1800. MIN_WASTE выбирает A (1000×1600 = 1.6 < 1000×1800 = 1.8).
    assert result.orientation == "900x400"
    assert result.production_area == pytest.approx(1_600_000.0)


# Test 7: setup — nesting=800, setup=500, total=1300; значения хранятся отдельно (§20)
def test_setup_length_separate() -> None:
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(
            material_id="film_white", mode="ROLL_NESTING", setup_length=500.0
        ),
    )
    assert result.layout["nesting_length_mm"] == pytest.approx(800.0)
    assert result.setup_consumption == pytest.approx(500.0)
    assert result.production_length == pytest.approx(1300.0)  # total
    # Площадь расхода — от ПОЛНОЙ длины (рулон физически потрачен).
    assert result.production_area == pytest.approx(1_300_000.0)


# Test 8: leader/trailer — раздельные значения (§21)
def test_leader_trailer_separate() -> None:
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 700.0, "height": 800.0, "quantity": 1.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            leader_length=300.0,
            trailer_length=200.0,
        ),
    )
    assert result.setup_consumption == pytest.approx(0.0)
    assert result.trim_consumption == pytest.approx(500.0)  # leader + trailer
    assert result.production_length == pytest.approx(1300.0)
    trace = [dict(step) for step in result.calculation_trace]
    leader = next(step for step in trace if step["step"] == "leader_length")
    trailer = next(step for step in trace if step["step"] == "trailer_length")
    assert leader["value_mm"] == pytest.approx(300.0)
    assert trailer["value_mm"] == pytest.approx(200.0)
    # Пример ТЗ §21: nesting 2.4 + leader 0.3 + trailer 0.2 = 2.9 — структура та же.
    assert result.layout["nesting_length_mm"] + 300.0 + 200.0 == pytest.approx(
        result.production_length
    )
