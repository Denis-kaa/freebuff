"""Golden-тесты Riso: паритет с legacy RisographCalculator.calculate().

Ожидаемые значения получены независимой деривацией формул из исходника
(«Общий калькулятор печати/riso_calc.py», строки 644–760) и зафиксированы
как литералы. Менять их допустимо только вместе с осознанным изменением
формулы (новая редакция контракта, см. README).
"""

from __future__ import annotations

import pytest

from printcalc.calculators.riso import RisoConfig, compute
from printcalc.engine.errors import CalcInputError

BASE = {
    "format": "A4",
    "qty": 1000.0,
    "originals": 1.0,
    "color": "ч/б",
    "paper": "Офсетная 80 г/м²",
    "duplex": False,
    "markup_percent": 25.0,
}


def test_golden_case1_a4_1000_simplex() -> None:
    result = compute(BASE)

    assert result.calculator_id == "riso"
    d = result.details
    assert d["tier"] == "1000-1999"
    assert d["base_rate"] == pytest.approx(0.45)
    assert d["qty"] == pytest.approx(1000.0)
    assert d["used_min"] is False
    assert d["master_count"] == pytest.approx(1.0)

    amounts = {line.label: line.amount for line in result.lines}
    assert amounts["Бумага"] == pytest.approx(30.0)
    assert amounts["Краска"] == pytest.approx(20.0)
    assert amounts["Мастер"] == pytest.approx(5.0)
    assert amounts["Работа"] == pytest.approx(50.0)
    assert amounts["Доп. услуги"] == pytest.approx(0.0)
    assert amounts["Себестоимость"] == pytest.approx(105.0)
    assert amounts["База (прайс × листы)"] == pytest.approx(450.0)
    assert amounts["Мастера и допы (+25%)"] == pytest.approx(6.25)
    assert amounts["Цена без налога"] == pytest.approx(456.25)
    assert amounts["Налог (6%)"] == pytest.approx(29.122340425531953)

    assert result.price_no_tax == pytest.approx(456.25)
    assert result.price == pytest.approx(485.37234042553195)
    assert result.cost == pytest.approx(105.0)
    assert result.net_profit == pytest.approx(351.25)
    assert result.unit_price == pytest.approx(0.45625)
    assert result.warnings == ()


def test_golden_case2_a5_duplex_min_order_all_extras() -> None:
    inputs = {
        "format": "A5",
        "qty": 100.0,
        "originals": 2.0,
        "color": "1 краска",
        "paper": "Мел. глянцевая 150 г/м²",
        "duplex": True,
        "markup_percent": 25.0,
        "cutting": True,
        "lamination": True,
        "folding": True,
        "stapling": True,
        "delivery": True,
    }
    result = compute(inputs)

    d = result.details
    assert d["tier"] == "500-999"
    assert d["base_rate"] == pytest.approx(0.55)
    assert d["used_min"] is True
    assert d["qty"] == pytest.approx(500.0)
    assert d["sides"] == 2
    assert d["impressions"] == pytest.approx(1000.0)
    assert d["master_count"] == pytest.approx(4.0)

    assert result.cost == pytest.approx(1980.0)  # 25+25+20+50+1860
    assert result.price_no_tax == pytest.approx(2625.0)  # 275 + 2350
    assert result.price == pytest.approx(2792.553191489362)
    assert result.net_profit == pytest.approx(645.0)
    assert result.unit_price == pytest.approx(5.25)
    assert result.warnings[0].startswith("Применён минимальный заказ")


def test_golden_case3_a6_10000_zero_markup() -> None:
    inputs = {
        "format": "A6",
        "qty": 10000.0,
        "originals": 1.0,
        "color": "2 краски",
        "paper": "Газетная",
        "markup_percent": 0.0,
    }
    result = compute(inputs)

    d = result.details
    assert d["tier"] == "от 10000"
    assert d["base_rate"] == pytest.approx(0.10)

    assert result.cost == pytest.approx(780.0)  # 50+225+5+500
    assert result.price_no_tax == pytest.approx(1005.0)
    assert result.price == pytest.approx(1069.148936170213)
    assert result.net_profit == pytest.approx(225.0)
    assert result.unit_price == pytest.approx(0.1005)


def test_golden_case4_min_order_boundary_499() -> None:
    result = compute({**BASE, "qty": 499.0})

    d = result.details
    assert d["tier"] == "500-999"
    assert d["used_min"] is True
    assert d["qty"] == pytest.approx(500.0)
    assert result.cost == pytest.approx(55.0)
    assert result.price_no_tax == pytest.approx(256.25)
    assert result.price == pytest.approx(272.60638297872345)
    assert result.net_profit == pytest.approx(201.25)


def test_tier_boundaries_pin_base_rate() -> None:
    # A4 one-sided: 500-999 -> 0.50; 1000-1999 -> 0.45;
    # 5000-9999 -> 0.30; от 10000 -> 0.25 (riso_calc.py:64-70).
    cases = {
        500.0: 0.50,
        999.0: 0.50,
        1000.0: 0.45,
        1999.0: 0.45,
        9999.0: 0.30,
        10000.0: 0.25,
    }
    for qty, expected_rate in cases.items():
        result = compute({**BASE, "qty": float(qty)})
        assert result.details["base_rate"] == pytest.approx(expected_rate), qty


def test_custom_config_injection() -> None:
    # Инъекция конфига вместо legacy-глобалов: мастер 10 ₽, минзаказ 100.
    config = RisoConfig(master_cost=10.0, min_order=100)
    result = compute({**BASE, "qty": 500.0}, config=config)

    assert result.details["used_min"] is False
    assert result.cost == pytest.approx(60.0)  # 15+10+10+25
    assert result.price_no_tax == pytest.approx(262.5)  # 250 + 12.5
    assert result.price == pytest.approx(279.25531914893617)
    assert result.net_profit == pytest.approx(202.5)


def test_legacy_errors_parity() -> None:
    # Тексты ошибок сохранены из legacy (riso_calc.py:649, 669, 675, 684, 692).
    with pytest.raises(CalcInputError) as exc:
        compute({**BASE, "qty": 0.0})
    assert exc.value.message == "Количество и оригиналы должны быть > 0"

    with pytest.raises(CalcInputError) as exc:
        compute({**BASE, "originals": 0.0})
    assert exc.value.message == "Количество и оригиналы должны быть > 0"

    with pytest.raises(CalcInputError) as exc:
        compute({**BASE, "format": "A3", "qty": 500.0})
    assert "Нет цены для формата A3 и диапазона 500-999" in exc.value.message

    with pytest.raises(CalcInputError) as exc:
        compute({**BASE, "paper": "Фантак"})
    assert exc.value.message == "Выберите бумагу"

    with pytest.raises(CalcInputError) as exc:
        compute({**BASE, "color": "5 красок"})
    assert exc.value.message == "Цветность не выбрана"

    # Ниже первого диапазона (при min_order=0 в кастомном конфиге).
    config = RisoConfig(min_order=0)
    with pytest.raises(CalcInputError) as exc:
        compute({**BASE, "qty": 10.0}, config=config)
    assert exc.value.message == "Не найден диапазон тиража для указанного количества"
