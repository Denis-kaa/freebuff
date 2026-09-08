"""Тесты ориентации — ТЗ §43 Test 3 + политики выбора (§12)."""

from __future__ import annotations

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


# Test 3: система выбирает ориентацию с меньшим расходом (явная политика MIN_WASTE).
# Плёнка 1000 мм, изделие 600×400, qty=4:
#   A (600×400): across = floor(1000/600) = 1, rows = 4, длина = 1600 → 1.6 м²
#   B (400×600): across = floor(1000/400) = 2, rows = 2, длина = 1200 → 1.2 м²
# Выбор: MIN_WASTE → B «400x600».
def test_rotation_reduces_consumption() -> None:
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 600.0, "height": 400.0, "quantity": 4.0},
        MaterialConsumptionPolicy(
            material_id="film_white", mode="ROLL_NESTING", orientation_policy="MIN_WASTE"
        ),
    )
    assert result.orientation == "400x600"
    assert result.pieces_across == 2
    assert result.rows == 2
    assert result.production_length == pytest_approx(1200.0)
    assert result.alternative_orientation == "600x400"
    assert result.production_area == pytest_approx(1_200_000.0)
    # Предупреждение о выгоде поворота (§39)
    assert any("Поворот" in w for w in result.warnings)


def pytest_approx(value: float):  # локальный хелпер, чтобы не тянуть pytest в сигнатуры
    import pytest

    return pytest.approx(value)


def test_fixed_orientation_policy() -> None:
    """FIXED_ORIENTATION: поворот возможен, но не выбирается автоматически (§12)."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 600.0, "height": 400.0, "quantity": 4.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            orientation_policy="FIXED_ORIENTATION",
        ),
    )
    assert result.orientation == "600x400"  # как введено
    assert result.alternative_orientation == "400x600"


def test_min_length_policy() -> None:
    """MIN_LENGTH: минимизируется длина раскладки, а не площадь."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 600.0, "height": 400.0, "quantity": 4.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            orientation_policy="MIN_LENGTH",
        ),
    )
    # Длина A=1600, B=1200 → B
    assert result.orientation == "400x600"
    assert result.production_length == pytest_approx(1200.0)


def test_rotation_disabled() -> None:
    """allow_rotation=False: только прямая ориентация, альбом недоступен."""
    result = ConsumptionEngine().calculate(
        _film(),
        {"width": 600.0, "height": 400.0, "quantity": 4.0},
        MaterialConsumptionPolicy(
            material_id="film_white",
            mode="ROLL_NESTING",
            allow_rotation=False,
        ),
    )
    assert result.orientation == "600x400"
    assert result.alternative_orientation is None
