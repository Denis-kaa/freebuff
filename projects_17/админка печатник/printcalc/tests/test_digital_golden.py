"""Golden-тесты Digital: паритет с legacy DigitalPolyCalc.calculate().

Ожидаемые значения получены независимой деривацией формул из исходника
(«Общий калькулятор печати/build_all/calc_digital.py», строки 335–455)
и зафиксированы как литералы. Менять их допустимо только вместе с
осознанным изменением формулы (новая редакция контракта, см. README).

Деривация кейса 1 (Визитка 90×50, A4, 100 шт, duplex, цветная):
    плотность: cols = floor((210+2)/(90+2)) = 2; rows = floor((297+2)/(50+2)) = 5
        → density = 10 шт/лист
    прайс: Визитка, 100 шт → диапазон 1–100 → 4.00 ₽/шт
    листы: pages=1 → ceil(100/10) = 10
    печать: 4.00 × 100 = 400.00
    area_mult(A4) = 210·297/(210·297) = 1.0
    бумага «Офсет 80» 0.35 × 1.0 × 10 = 3.50
    краска «цветная» 1.20 × 1.0 × 2(duplex) × 10 = 24.00
    допов нет; себестоимость = 3.50 + 24.00 + 0 + 100.00 = 127.50
    наценка 30%: допы+подготовка = 100.00 × 1.30 = 130.00
    цена без налога = 400.00 + 130.00 = 530.00 (≥ min 500 — минимум не применён)
    цена = 530.00 / 0.94 = 563.8297872340425...
"""

from __future__ import annotations

import pytest

from printcalc.calculators.digital import DigitalConfig, compute
from printcalc.engine.errors import CalcInputError

BASE = {
    "product": "Визитка",
    "width": 90.0,
    "height": 50.0,
    "copies": 100.0,
    "pages": 1.0,
    "color": "цветная",
    "duplex": True,
    "sheet_format": "A4",
    "paper": "Офсет 80 г/м²",
    "markup_percent": 30.0,
}


def test_golden_case1_vizitka_a4_100_duplex() -> None:
    result = compute(BASE)

    assert result.calculator_id == "digital"
    d = result.details
    assert d["density"] == 10
    assert d["price_per_item"] == pytest.approx(4.0)
    assert d["total_sheets"] == 10
    assert d["used_min"] is False
    assert d["extras_on"] == []

    amounts = {line.label: line.amount for line in result.lines}
    assert amounts["Печать (прайс × тираж)"] == pytest.approx(400.0)
    assert amounts["Бумага"] == pytest.approx(3.5)
    assert amounts["Краска"] == pytest.approx(24.0)
    assert amounts["Подготовка"] == pytest.approx(100.0)
    assert amounts["Себестоимость"] == pytest.approx(127.5)
    assert amounts["Допы и подготовка (+30%)"] == pytest.approx(130.0)
    assert amounts["Цена без налога"] == pytest.approx(530.0)
    assert amounts["Налог (6%)"] == pytest.approx(33.82978723404255)

    assert result.price_no_tax == pytest.approx(530.0)
    assert result.price == pytest.approx(563.8297872340425)
    assert result.cost == pytest.approx(127.5)
    assert result.net_profit == pytest.approx(402.5)  # 530 − 127.5
    assert result.unit_price == pytest.approx(5.3)
    assert result.warnings == ()


def test_golden_case2_min_order_and_lamination() -> None:
    """Листовка А5 10 шт: прайс 8 ₽/шт (1–50), min order 500 применяется.

    Деривация: A5 148×210, лист A4: cols=floor(212/150)=1, rows=floor(299/212)=1
        → density=1; листы = ceil(10/1) = 10; печать = 8×10 = 80.
    Ламинация «лист»: 1.5 × 1.0 × 10 = 15 → себестоимость = 3.5 + 12 + 15 + 100 = 130.5
    (печать — доход, не расход). Допы+подготовка ×1.3 = 115×1.3 = 149.5;
    цена без налога = 80+149.5 = 229.5 < 500 → min_order → 500.
    Цена = 500/0.94 = 531.914893617...
    """
    inputs = dict(BASE)
    inputs.update(
        {
            "product": "Листовка А5",
            "width": 148.0,
            "height": 210.0,
            "copies": 10.0,
            "duplex": False,
            "extras_lamination": True,
        }
    )
    result = compute(inputs)

    d = result.details
    assert d["density"] == 1
    assert d["total_sheets"] == 10
    assert d["used_min"] is True
    assert d["extras_on"] == ["Ламинация"]

    amounts = {line.label: line.amount for line in result.lines}
    assert amounts["Печать (прайс × тираж)"] == pytest.approx(80.0)
    assert amounts["Бумага"] == pytest.approx(3.5)  # 0.35 × 1 × 10
    assert amounts["Краска"] == pytest.approx(12.0)  # 1.2 × 1 × 10 (одностор.)
    assert amounts["Ламинация"] == pytest.approx(15.0)
    assert amounts["Себестоимость"] == pytest.approx(130.5)
    assert result.price_no_tax == pytest.approx(500.0)
    assert result.price == pytest.approx(531.9148936170213)
    assert result.warnings[0].startswith("Применён минимальный заказ")


def test_golden_case3_multipage_duplex_sheets() -> None:
    """Евробуклет 2 полосы duplex: листы = ceil(2/2) × copies.

    Деривация (50 шт): прайс — нет диапазонов для «Евробуклет» → default
    10 ₽/шт; плотность 100×210 на A4: cols=floor(212/102)=2,
    rows=floor(299/212)=1 → 2; duplex, pages=2 → ceil(2/2)=1 → 1×50 = 50 листов.
    Печать = 10×50 = 500. Бумага 0.35×1×50 = 17.5; краска duplex
    1.2×2×50 = 120. Себестоимость = 17.5+120+100 = 237.5.
    Допы ×1.3 = 130; цена без налога = 500+130 = 630; цена = 630/0.94.
    """
    inputs = dict(BASE)
    inputs.update(
        {
            "product": "Евробуклет",
            "width": 100.0,
            "height": 210.0,
            "copies": 50.0,
            "pages": 2.0,
        }
    )
    result = compute(inputs)

    d = result.details
    assert d["density"] == 2
    assert d["total_sheets"] == 50
    assert d["price_per_item"] == pytest.approx(10.0)
    amounts = {line.label: line.amount for line in result.lines}
    assert amounts["Печать (прайс × тираж)"] == pytest.approx(500.0)
    assert amounts["Бумага"] == pytest.approx(17.5)
    assert amounts["Краска"] == pytest.approx(120.0)
    assert result.price_no_tax == pytest.approx(630.0)
    assert result.price == pytest.approx(670.2127659574468)


def test_golden_case4_multipage_simplex_sheets() -> None:
    """2 полосы без duplex: листы = pages × copies (legacy 381-382)."""
    inputs = dict(BASE)
    inputs.update({"pages": 2.0, "duplex": False})
    result = compute(inputs)

    d = result.details
    assert d["total_sheets"] == 200  # 2 × 100
    amounts = {line.label: line.amount for line in result.lines}
    # Печать: 4×100=400; бумага 0.35×200=70; краска 1.2×200=240;
    # себестоимость = 70+240+100 = 410.
    assert amounts["Бумага"] == pytest.approx(70.0)
    assert amounts["Краска"] == pytest.approx(240.0)
    assert amounts["Себестоимость"] == pytest.approx(410.0)
    assert result.price_no_tax == pytest.approx(530.0)  # min не применён (400+130)


def test_sra3_area_multiplier() -> None:
    """SRA3: area_mult = 320×450/(210×297) ≈ 2.306 (materials scale)."""
    inputs = dict(BASE)
    inputs["sheet_format"] = "SRA3"
    result = compute(inputs)

    d = result.details
    # 90×50 на SRA3: cols=floor(322/92)=3, rows=floor(452/52)=8 → 24
    assert d["density"] == 24
    assert d["total_sheets"] == 5  # ceil(100/24)
    amounts = {line.label: line.amount for line in result.lines}
    mult = 320 * 450 / (210 * 297)
    assert amounts["Бумага"] == pytest.approx(0.35 * mult * 5)
    assert amounts["Краска"] == pytest.approx(1.2 * mult * 2 * 5)


def test_errors_item_does_not_fit() -> None:
    """Изделие больше листа → ошибка «Изделие не помещается…» (legacy 369-371)."""
    inputs = dict(BASE)
    inputs["width"] = 500.0
    with pytest.raises(CalcInputError, match="не помещается"):
        compute(inputs)


def test_errors_no_price_range() -> None:
    """Тираж 0 не проходит валидацию; «нет диапазона» недостижим в default-конфиге
    (все изделия получают fallback-диапазон 1..None). Проверяем текст ошибки
    на кастомном конфиге без диапазонов."""

    from dataclasses import replace

    cfg = DigitalConfig(product_prices={})
    inputs = dict(BASE)
    result = compute(inputs, config=cfg)
    # fallback-диапазон 10 ₽/шт всё равно применяется (legacy init_default_prices)
    assert result.details["price_per_item"] == pytest.approx(10.0)


def test_errors_invalid_paper_and_color() -> None:
    inputs = dict(BASE)
    inputs["paper"] = "Несуществующая"
    with pytest.raises(CalcInputError, match="Выберите бумагу"):
        compute(inputs)

    inputs = dict(BASE)
    inputs["color"] = "серая"
    with pytest.raises(CalcInputError, match="Цветность"):
        compute(inputs)


def test_errors_copies_must_be_positive() -> None:
    inputs = dict(BASE)
    inputs["copies"] = 0.0
    with pytest.raises(CalcInputError, match="Тираж должен быть больше 0"):
        compute(inputs)
