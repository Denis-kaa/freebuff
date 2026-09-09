"""Тесты SHEET_NESTING (Этап 3b): раскрой листовых материалов (Таблички).

Правило поворота владельца действует и на листах: если изделие не влезает
прямо, пробуется повёрнутая ориентация; ошибка — только когда не влезает ни так.
"""

from __future__ import annotations

import pytest

from printcalc.engine.consumption import (
    ConsumptionEngine,
    ConsumptionError,
    Material,
    MaterialConsumptionPolicy,
)


def _pvc() -> Material:
    return Material(
        id="pvc3",
        name="ПВХ 3 мм",
        consumption_mode="SHEET",
        base_unit="m2",
        sheet_width=3000.0,
        sheet_height=2000.0,
    )


def test_small_signs_fit_many_per_sheet() -> None:
    """50×40 см (500×400 мм) на листе 3000×2000: 60×50 = 30 шт/лист, 4 шт → 1 лист."""
    result = ConsumptionEngine().calculate(
        _pvc(),
        {"width": 500.0, "height": 400.0, "quantity": 4.0},
        MaterialConsumptionPolicy(material_id="pvc3", mode="SHEET"),
    )
    assert result.layout["per_sheet"] == 30
    assert result.layout["sheets"] == 1
    assert result.billing_quantity == pytest.approx(1.0)
    assert result.billing_unit == "лист"
    assert result.product_area == pytest.approx(500.0 * 400.0 * 4)
    assert result.production_area == pytest.approx(3000.0 * 2000.0)  # целые листы
    assert any("30 шт" in w for w in result.warnings)


def test_quantity_crossing_sheet_boundary() -> None:
    """31 изделие по 30 на лист → 2 листа."""
    result = ConsumptionEngine().calculate(
        _pvc(),
        {"width": 500.0, "height": 400.0, "quantity": 31.0},
        MaterialConsumptionPolicy(material_id="pvc3", mode="SHEET"),
    )
    assert result.layout["sheets"] == 2
    assert result.production_area == pytest.approx(3000.0 * 2000.0 * 2)


def test_rotation_chooses_better_fit() -> None:
    """2500×600 на листе 3000×2000: A — 1×3=3 шт; поворот B — 0 (высота 2500 > 2000)."""
    result = ConsumptionEngine().calculate(
        _pvc(),
        {"width": 2500.0, "height": 600.0, "quantity": 7.0},
        MaterialConsumptionPolicy(material_id="pvc3", mode="SHEET"),
    )
    assert result.orientation == "2500x600"
    assert result.layout["per_sheet"] == 3
    assert result.layout["sheets"] == 3  # ceil(7/3)


def test_rotation_rescues_when_portrait_fails() -> None:
    """600×2500: A — floor(3000/600)*floor(2000/2500)=5*0=0; B — 1*3=3 → поворот спасает."""
    result = ConsumptionEngine().calculate(
        _pvc(),
        {"width": 600.0, "height": 2500.0, "quantity": 4.0},
        MaterialConsumptionPolicy(material_id="pvc3", mode="SHEET"),
    )
    assert result.orientation == "2500x600"
    assert result.layout["per_sheet"] == 3


def test_oversize_neither_orientation() -> None:
    """3100×500: длиннее листа в обеих ориентациях — честная ошибка."""
    with pytest.raises(ConsumptionError) as exc:
        ConsumptionEngine().calculate(
            _pvc(),
            {"width": 3100.0, "height": 500.0, "quantity": 1.0},
            MaterialConsumptionPolicy(material_id="pvc3", mode="SHEET"),
        )
    assert exc.value.code == "PRODUCT_DOES_NOT_FIT"


def test_sheet_without_dimensions_falls_back_to_direct() -> None:
    """SHEET-материал без размеров листа → прямой режим (листов = quantity)."""
    material = Material(id="pvc_raw", name="ПВХ", consumption_mode="SHEET", base_unit="m2")
    result = ConsumptionEngine().calculate(
        material,
        {"width": 500.0, "height": 400.0, "quantity": 3.0},
        MaterialConsumptionPolicy(material_id="pvc_raw", mode="SHEET"),
    )
    assert result.layout["mode"] == "SHEET"
    assert result.billing_quantity == pytest.approx(3.0)
    assert result.billing_unit == "m2"
