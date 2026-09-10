"""Golden-тесты ЧПУ: паритет с legacy cnc_calc.py updatePrice().

Ожидаемые значения получены независимой деривацией формул из исходника
(«Калькулятор фрезерной и лазерной резки/cnc_calc.py», строки 397–427)
и зафиксированы как литералы. Менять их допустимо только вместе с
осознанным изменением формулы (новая редакция контракта, см. README).

Деривация кейса 1 (Лазер, Фанера 6 мм, рез 10 м, 2 шт, 1.0×0.5 м):
    cut_price  = 10 × 25 ₽/м × 2 = 500.0        (laser/Фанера/6 → 25 ₽/м)
    area       = 1.0 × 0.5 = 0.5 м²
    material   = 0.5 × 450 ₽/м² × 2 = 450.0     (Фанера/6 → 450 ₽/м²)
    ИТОГО      = 500 + 450 = 950.0; за шт = 950 / 2 = 475.0

Деривация кейса 2 (Фрезер, Акрил 5 мм, рез 3.5 м, 3 шт, 2.0×1.0 м):
    cut_price  = 3.5 × 50 ₽/м × 3 = 525.0       (frezer/Акрил/5 → 50 ₽/м)
    area       = 2.0 × 1.0 = 2.0 м²
    material   = 2.0 × 1300 ₽/м² × 3 = 7800.0   (Акрил/5 → 1300 ₽/м²)
    ИТОГО      = 525 + 7800 = 8325.0; за шт = 8325 / 3 = 2775.0

Деривация кейса 3 (Лазер, ПВХ 3 мм, рез 0.5 м, 1 шт, без материала):
    cut_price  = 0.5 × 15 ₽/м × 1 = 7.5         (laser/ПВХ/3 → 15 ₽/м)
    material   = 0 (размеры не заданы: W=0)
    ИТОГО      = 7.5; предупреждений нет
"""

from __future__ import annotations

import pytest

from printcalc.calculators.cnc import CncConfig, compute
from printcalc.engine.errors import CalcInputError


def _cfg() -> CncConfig:
    return CncConfig()


# ---------- golden-кейсы ----------


def test_golden_laser_plywood_6() -> None:
    result = compute(
        {
            "machine": "laser",
            "material": "Фанера",
            "thickness": 6,
            "cut_length": 10,
            "qty": 2,
            "product_width": 1.0,
            "product_height": 0.5,
        },
        _cfg(),
    )
    assert result.price == 950.0
    assert result.price_no_tax == 950.0
    assert result.cost == 950.0
    assert result.unit_price == 475.0
    assert result.warnings == ()
    assert result.details["cut_price"] == 500.0
    assert result.details["material_price"] == 450.0


def test_golden_frezer_acryl_5() -> None:
    result = compute(
        {
            "machine": "frezer",
            "material": "Акрил (оргстекло)",
            "thickness": 5,
            "cut_length": 3.5,
            "qty": 3,
            "product_width": 2.0,
            "product_height": 1.0,
        },
        _cfg(),
    )
    assert result.price == 8325.0
    assert result.unit_price == 2775.0
    assert result.details["cut_price"] == 525.0
    assert result.details["material_price"] == 7800.0


def test_golden_laser_pvc_without_material() -> None:
    result = compute(
        {
            "machine": "laser",
            "material": "ПВХ",
            "thickness": 3,
            "cut_length": 0.5,
            "qty": 1,
        },
        _cfg(),
    )
    assert result.price == 7.5
    assert result.warnings == ()


# ---------- ветки «нет ставки» / «нет материала» ----------


def test_missing_rate_warns_and_counts_material_only() -> None:
    # Станок/материал/толщина без ставки: Композит толщины 3 не существует
    # ни в материалах, ни в ставках → оба предупреждения, цена 0.
    result = compute(
        {
            "machine": "laser",
            "material": "Композит",
            "thickness": 3,
            "cut_length": 5,
            "qty": 1,
            "product_width": 1,
            "product_height": 1,
        },
        _cfg(),
    )
    assert result.price == 0.0
    assert any("Нет ставки" in w for w in result.warnings)
    assert any("не найден" in w for w in result.warnings)


def test_material_without_rate_still_counts_material() -> None:
    # Материал есть, ставки нет (parity legacy: рез=0, материал считается).
    # laser/Фанера 18: ставка есть (80), а frezer… тоже есть. Подбираем
    # пару без ставки инъекцией конфига.
    from printcalc.calculators.cnc.config import CutRate, SheetMaterial

    cfg = CncConfig(
        materials=(SheetMaterial("Тест", 3, 100.0),),
        cut_rates=(),  # ставок нет вообще
    )
    result = compute(
        {
            "machine": "laser",
            "material": "Тест",
            "thickness": 3,
            "cut_length": 2,
            "qty": 2,
            "product_width": 1,
            "product_height": 1,
        },
        cfg,
    )
    assert result.price == 200.0  # только материал 1×1×100×2
    assert any("Нет ставки" in w for w in result.warnings)


# ---------- валидация входов ----------


def test_unknown_machine_raises() -> None:
    with pytest.raises(CalcInputError):
        compute({"machine": "cnc3d", "material": "Фанера", "thickness": 3, "qty": 1})


def test_zero_qty_raises() -> None:
    with pytest.raises(CalcInputError):
        compute(
            {
                "machine": "laser",
                "material": "Фанера",
                "thickness": 3,
                "qty": 0,
            }
        )


def test_negative_thickness_raises() -> None:
    with pytest.raises(CalcInputError):
        compute(
            {
                "machine": "laser",
                "material": "Фанера",
                "thickness": -1,
                "qty": 1,
            }
        )


def test_zero_cut_length_ok() -> None:
    # Рез 0 м разрешён: считаем только материал (legacy parseFloat||0).
    result = compute(
        {
            "machine": "laser",
            "material": "Фанера",
            "thickness": 3,
            "cut_length": 0,
            "qty": 1,
            "product_width": 2,
            "product_height": 1,
        },
        _cfg(),
    )
    assert result.price == 600.0  # 2×1×300×1
