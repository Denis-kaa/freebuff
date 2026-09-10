"""Golden-тесты Вывесок: паритет с legacy SignCalculator.calculate().

Ожидаемые значения получены независимой деривацией формул из исходника
(«Общий калькулятор печати/build_all/sign_calc.py», строки 782–930)
и зафиксированы как литералы. Менять их допустимо только вместе с
осознанным изменением формулы (новая редакция контракта, см. README).

Деривация кейса 1 (Объёмная несветовая буква, 40 см, 1 шт, Средний):
    геометрия (буквы): h_m = 40/100 = 0.4; w = 0.4·0.7 = 0.28
        area = 0.28·0.4·1 = 0.112 м²; per = 2·(0.28+0.4)·1 = 1.36 м
        units = 40·1 = 40 см
    модель «Объёмная буква»: work_rate 1500, not light
    детали: front ПВХ 10мм (700), side ПВХ 5мм (450, высота 0.05), back ПВХ 10мм (700)
    материалы: 0.112·700 + 1.36·0.05·450 + 0.112·700 = 78.4 + 30.6 + 78.4 = 187.40
    работа: 0.112·1500·1.3 = 218.40
    подсветка: 0 (модель не световая)
    extras: все нулевые → extra = 0
    себестоимость = 187.40 + 218.40 = 405.80
    цена без налога = 405.80·1.25 = 507.25
    цена = 507.25/0.94 = 539.6276595744680...
    прибыль = 507.25 − 405.80 = 101.45

Деривация кейса 2 (Световой короб 1.0×0.6 м, 1 шт, Простой, УФ-печать,
монтаж «2-3 м», электрика, доставка 10 км, 2 блока):
    площадь = 0.6 м²; периметр = 2·(1.0+0.6) = 3.2 м; units = 0.6
    модель «Световой короб»: work_rate 1800, light
    детали: front Акрил 3мм (1500), side Композит 3мм (1800, 0.1), back Алюкобонд 4мм (2300)
    материалы: 0.6·1500 + 3.2·0.1·1800 + 0.6·2300 = 900 + 576 + 1380 = 2856.00
    работа: 0.6·1800·1.0 = 1080.00
    подсветка: 0.6·900 = 540.00
    изображение: 0.6·1200 = 720.00
    монтаж: 3500·1.10 = 3850.00
    электрика: 3.2·350 + 800 = 1920.00
    доставка: 10·40 = 400.00
    блоки: 2·1200 = 2400.00
    extra = 720 + 3850 + 1920 + 400 + 2400 = 9290.00
    себестоимость = 2856 + 1080 + 540 + 9290 = 13766.00
    цена без налога = 13766·1.25 = 17207.50
    цена = 17207.50/0.94 = 18305.85106382978...
"""

from __future__ import annotations

import pytest

from printcalc.calculators.sign import SignConfig, compute
from printcalc.engine.errors import CalcInputError

BASE_LETTER = {
    "product": "Объёмная несветовая буква",
    "height": 40.0,
    "qty": 1.0,
    "complexity": "Средний",
    "markup_percent": 25.0,
    "front_material": "Авто",
    "side_material": "Авто",
    "back_material": "Авто",
    "image_type": "Без нанесения",
    "mounting": "нет",
    "electric": False,
    "delivery_distance_km": 0.0,
    "substrate_area_m2": 0.0,
    "substrate_material": "ПВХ 10мм",
    "frame_length_m": 0.0,
    "frame_material": "Металлический",
    "power_supply_count": 0.0,
}


def test_golden_case1_volume_letter_defaults() -> None:
    result = compute(BASE_LETTER)

    assert result.calculator_id == "sign"
    d = result.details
    assert d["area_m2"] == pytest.approx(0.112)
    assert d["perimeter_m"] == pytest.approx(1.36)
    assert d["units"] == pytest.approx(40.0)
    assert d["price_mode"] == "cost_markup"

    amounts = {line.label: line.amount for line in result.lines}
    assert amounts["Материалы"] == pytest.approx(187.4)
    assert amounts["Работа"] == pytest.approx(218.4)
    assert amounts["Подсветка"] == pytest.approx(0.0)
    assert amounts["Себестоимость"] == pytest.approx(405.8)
    assert amounts["Цена без налога"] == pytest.approx(507.25)
    assert amounts["Налог (6%)"] == pytest.approx(539.627659574468 - 507.25)
    assert amounts["ИТОГО ЦЕНА"] == pytest.approx(539.627659574468)

    assert result.price_no_tax == pytest.approx(507.25)
    assert result.cost == pytest.approx(405.8)
    assert result.net_profit == pytest.approx(101.45)


def test_golden_case2_light_box_full_extras() -> None:
    inputs = {
        "product": "Световой короб",
        "height": 0.6,
        "width": 1.0,
        "qty": 1.0,
        "complexity": "Простой",
        "markup_percent": 25.0,
        "front_material": "Авто",
        "side_material": "Авто",
        "back_material": "Авто",
        "image_type": "УФ-печать",
        "mounting": "2-3 м",
        "electric": True,
        "delivery_distance_km": 10.0,
        "substrate_area_m2": 0.0,
        "substrate_material": "ПВХ 10мм",
        "frame_length_m": 0.0,
        "frame_material": "Металлический",
        "power_supply_count": 2.0,
    }
    result = compute(inputs)

    d = result.details
    assert d["area_m2"] == pytest.approx(0.6)
    assert d["perimeter_m"] == pytest.approx(3.2)
    assert d["extra"] == pytest.approx(9290.0)

    amounts = {line.label: line.amount for line in result.lines}
    assert amounts["Материалы"] == pytest.approx(2856.0)
    assert amounts["Работа"] == pytest.approx(1080.0)
    assert amounts["Подсветка"] == pytest.approx(540.0)
    assert amounts["Изображение"] == pytest.approx(720.0)
    assert amounts["Монтаж"] == pytest.approx(3850.0)
    assert amounts["Электрика"] == pytest.approx(1920.0)
    assert amounts["Доставка"] == pytest.approx(400.0)
    assert amounts["Блоки питания (x2)"] == pytest.approx(2400.0)
    assert amounts["Себестоимость"] == pytest.approx(13766.0)
    assert amounts["Цена без налога"] == pytest.approx(17207.5)
    assert result.price == pytest.approx(18305.85106382978)


def test_golden_case3_contrazhur_light_letter() -> None:
    """Контражур: подсветка по периметру per·0.6·450, работа 2500·complexity."""
    inputs = dict(BASE_LETTER)
    inputs["product"] = "Световая буква контражур"
    inputs["complexity"] = "Сложный"
    result = compute(inputs)

    d = result.details
    # та же геометрия (40 см)
    assert d["area_m2"] == pytest.approx(0.112)
    assert d["perimeter_m"] == pytest.approx(1.36)

    amounts = {line.label: line.amount for line in result.lines}
    # детали контражура: front Акрил 3мм (1500), side ПВХ 5мм (450·0.05), back ПВХ 10мм (700)
    assert amounts["Материалы"] == pytest.approx(0.112 * 1500 + 1.36 * 0.05 * 450 + 0.112 * 700)
    assert amounts["Работа"] == pytest.approx(0.112 * 2500 * 1.6)
    assert amounts["Подсветка"] == pytest.approx(1.36 * 0.6 * 450)


def test_golden_case4_materials_override_and_unknown_fallback() -> None:
    """Явный материал заменяет «Авто»; неизвестный — fallback 200 ₽."""
    inputs = dict(BASE_LETTER)
    inputs["front_material"] = "Акрил 5мм"  # 2200
    result = compute(inputs)
    amounts = {line.label: line.amount for line in result.lines}
    assert amounts["Материалы"] == pytest.approx(
        0.112 * 2200 + 1.36 * 0.05 * 450 + 0.112 * 700
    )

    inputs2 = dict(BASE_LETTER)
    inputs2["front_material"] = "Мифический камень"  # нет в MATERIALS
    result2 = compute(inputs2)
    amounts2 = {line.label: line.amount for line in result2.lines}
    assert amounts2["Материалы"] == pytest.approx(
        0.112 * 200.0 + 1.36 * 0.05 * 450 + 0.112 * 700
    )


def test_golden_case5_price_list_mode() -> None:
    """PRICE_PER_CM > 0 → режим прайса: base_total + extra·(1+markup)."""
    cfg = SignConfig(
        price_per_unit={"Объёмная несветовая буква": 12.0},
    )
    inputs = dict(BASE_LETTER)
    inputs["delivery_distance_km"] = 5.0  # extra = 200
    result = compute(inputs, config=cfg)

    d = result.details
    assert d["price_mode"] == "price_list"
    # units = 40 см → база 480; extra = 5·40 = 200 → 200·1.25 = 250
    assert result.price_no_tax == pytest.approx(480.0 + 250.0)
    # себестоимость в прайс-режиме всё равно считается по материалам
    assert result.cost == pytest.approx(405.8 + 200.0)


def test_input_errors_match_legacy_guards() -> None:
    with pytest.raises(CalcInputError):
        compute({**BASE_LETTER, "qty": 0.0})
    with pytest.raises(CalcInputError):
        compute({**BASE_LETTER, "product": "Чего-то там"})
    # короб без ширины — legacy требует width для sqm
    with pytest.raises(CalcInputError):
        compute({**BASE_LETTER, "product": "Световой короб", "width": 0.0})
    with pytest.raises(CalcInputError):
        compute({**BASE_LETTER, "mounting": "на 10 метров"})
