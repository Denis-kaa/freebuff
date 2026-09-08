"""Golden-тесты калькулятора табличек: паритет с legacy TableCalculator.

Ожидаемые значения получены независимой деривацией формул из исходника
(«Общий калькулятор печати/tablichki.py», calculate() строки 641–744) и
зафиксированы как литералы. Менять их допустимо только вместе с осознанным
изменением формулы (новая редакция контракта, см. README).

Отличие от Riso: налог в финальной цене НЕ участвует — sell-пары уже
содержат продажную цену, поэтому price == price_no_tax.
"""

from __future__ import annotations

import pytest

from printcalc.calculators.tablichki import TablichkiConfig, compute
from printcalc.calculators.tablichki.config import PricePair
from printcalc.engine.errors import CalcInputError

BASE = {
    "width": 20.0,
    "height": 10.0,
    "qty": 1.0,
    "material": "ПВХ 3 мм",
    "print": "Без печати",
    "mount": "Без крепежа",
}


def test_golden_case1_simple_plaque() -> None:
    # 20×10 см, 1 шт, ПВХ 3 мм, без печати/крепежа: sell-пары + ставка за м².
    result = compute(BASE)

    assert result.calculator_id == "tablichki"
    d = result.details
    assert d["total_area"] == pytest.approx(0.02)
    assert d["total_perim"] == pytest.approx(0.6)
    assert d["print_area"] == pytest.approx(0.02)
    assert d["double_sided"] is False
    assert d["used_min"] is False

    # Материал 16 + ставка 8 → себестоимость 24; продажа 24+20=44.
    assert result.cost == pytest.approx(24.0)
    assert result.price == pytest.approx(44.0)
    assert result.price_no_tax == pytest.approx(44.0)
    assert result.net_profit == pytest.approx(20.0)
    assert result.unit_price == pytest.approx(44.0)
    assert result.warnings == ()

    amounts = {line.label: line.amount for line in result.lines}
    assert amounts["Материал"] == pytest.approx(16.0)
    assert amounts["Печать"] == pytest.approx(0.0)
    assert amounts["Крепёж"] == pytest.approx(0.0)
    assert amounts["Обработка"] == pytest.approx(0.0)
    assert amounts["Работа за м²"] == pytest.approx(8.0)
    assert amounts["Себестоимость"] == pytest.approx(24.0)
    assert amounts["ИТОГО ЦЕНА"] == pytest.approx(44.0)


def test_golden_case2_double_sided_print_mount_delivery() -> None:
    # ПВХ 5 мм + УФ-печать, двусторонняя, клейкая пена, доставка, qty=2.
    inputs = {
        **BASE,
        "qty": 2.0,
        "material": "ПВХ 5 мм",
        "print": "УФ-печать",
        "mount": "Клейкая пена",
        "double_sided": True,
        "delivery": True,
    }
    result = compute(inputs)

    d = result.details
    assert d["total_area"] == pytest.approx(0.04)  # 0.02 × 2
    assert d["print_area"] == pytest.approx(0.08)  # ×2 за две стороны
    assert d["total_perim"] == pytest.approx(1.2)
    assert d["delivery"] is True

    # cost: 40 (мат) + 120 (печать) + 80 (крепёж) + 16 (ставка) + 100 = 356
    assert result.cost == pytest.approx(356.0)
    # sell: 60 + 192 + 120 + 40 + 300 = 712
    assert result.price == pytest.approx(712.0)
    assert result.net_profit == pytest.approx(356.0)
    assert result.unit_price == pytest.approx(356.0)

    amounts = {line.label: line.amount for line in result.lines}
    assert amounts["Материал"] == pytest.approx(40.0)
    assert amounts["Печать"] == pytest.approx(120.0)
    assert amounts["Крепёж"] == pytest.approx(80.0)
    assert amounts["Доставка"] == pytest.approx(100.0)
    assert amounts["ИТОГО ЦЕНА"] == pytest.approx(712.0)


def test_golden_case3_works_by_units() -> None:
    # Обработка по трём единицам: м² (скругление), пог.м (скотч по периметру),
    # шт (люверсы ×6). 30×20 см, qty=3, двусторонняя, УФ-печать + лак.
    inputs = {
        **BASE,
        "width": 30.0,
        "height": 20.0,
        "qty": 3.0,
        "print": "УФ-печать + лак",
        "double_sided": True,
        "work_rounding": True,
        "work_tape": True,
        "work_eyelets": True,
        "work_eyelets_qty": 6.0,
    }
    result = compute(inputs)

    d = result.details
    assert d["total_area"] == pytest.approx(0.18)  # 0.06 × 3
    assert d["total_perim"] == pytest.approx(3.0)  # 1.0 м × 3
    assert d["print_area"] == pytest.approx(0.36)
    assert [w["name"] for w in d["works"]] == [
        "Скругление углов",
        "Нанесение скотча по периметру",
        "Установка люверсов",
    ]

    # cost: 144 + 720 + 0 + (18+210+120) + 72 = 1284
    assert result.cost == pytest.approx(1284.0)
    # sell: 216 + 1080 + 0 + (36+360+210) + 180 = 2082
    assert result.price == pytest.approx(2082.0)
    assert result.net_profit == pytest.approx(798.0)
    assert result.unit_price == pytest.approx(694.0)  # 2082 / 3

    amounts = {line.label: line.amount for line in result.lines}
    assert amounts["Обработка"] == pytest.approx(348.0)  # 18 + 210 + 120
    assert amounts["Материал"] == pytest.approx(144.0)
    assert amounts["Печать"] == pytest.approx(720.0)
    assert amounts["Работа за м²"] == pytest.approx(72.0)


def test_golden_case4_piece_work_default_qty() -> None:
    # Люверсы включены без количества → legacy-значение по умолчанию 1 шт.
    result = compute({**BASE, "work_eyelets": True})

    assert result.cost == pytest.approx(44.0)  # 24 + 20
    assert result.price == pytest.approx(79.0)  # 44 + 35
    assert [w["qty"] for w in result.details["works"]] == [1.0]


def test_min_order_price_raises_sell() -> None:
    # «Мин. цена заказа» поднимает продажную цену (таблички по умолчанию 0 —
    # эффекта нет; здесь конфиг с порогом 500, как в legacy).
    config = TablichkiConfig(min_order_price=500.0)
    result = compute(BASE, config=config)

    assert result.details["used_min"] is True
    assert result.price == pytest.approx(500.0)
    assert result.cost == pytest.approx(24.0)
    assert result.net_profit == pytest.approx(476.0)
    assert result.warnings[0].startswith("Цена поднята до минимальной")


def test_custom_config_injection() -> None:
    # Инъекция конфига вместо legacy-глобалов: свой материал и своя ставка.
    config = TablichkiConfig(
        materials={"Сталь 2 мм": PricePair(cost=2000.0, sell=3500.0)},
        work_rate_cost=0.0,  # работа бесплатная — чистый материал
        work_rate_sell=0.0,
    )
    result = compute({**BASE, "material": "Сталь 2 мм"}, config=config)

    # 20×10 см = 0.02 м²: материал 2000*0.02=40 (закупка) / 3500*0.02=70.
    assert result.cost == pytest.approx(40.0)
    assert result.price == pytest.approx(70.0)
    assert result.net_profit == pytest.approx(30.0)
    assert result.details["material"] == "Сталь 2 мм"


def test_errors_parity() -> None:
    # Размеры и количество должны быть > 0 (как ValueError в legacy:644-646).
    with pytest.raises(CalcInputError) as exc:
        compute({**BASE, "width": 0.0})
    assert exc.value.field == "width"
    assert "должны быть > 0" in exc.value.message

    with pytest.raises(CalcInputError) as exc:
        compute({**BASE, "qty": -2.0})
    assert exc.value.field == "qty"

    # Членство material/print/mount проверяет конфиг (как legacy-словари).
    with pytest.raises(CalcInputError) as exc:
        compute({**BASE, "material": "Картон"})
    assert exc.value.message == "Материал не выбран"

    with pytest.raises(CalcInputError) as exc:
        compute({**BASE, "print": "Лазерная"})
    assert exc.value.message == "Печать не выбрана"

    with pytest.raises(CalcInputError) as exc:
        compute({**BASE, "mount": "Шурупы"})
    assert exc.value.message == "Крепёж не выбран"
