"""Golden-тесты Дизайна: паритет с legacy design_calc.py.

Ожидаемые значения получены независимой деривацией из исходника
(«Калькулятор макетов/design_calc.py», build_prices() строки 15–33 +
JS updatePrice() + export_pdf-поиск строки 118–126) и зафиксированы
как литералы. Менять их допустимо только вместе с осознанным изменением
прайса (новая редакция контракта, см. README).

Деривация кейсов (цена = позиция прайса по тройке услуга/сторона/уровень):
    «Дизайн визитки 4+0» / Простой  → 600
    «Дизайн визитки 4+4» / Сложный  → 2000
    «Плакат А3» / Средний           → 2600
    «Вёрстка презентации (за страницу)» / «» → 750 (тираж НЕ влияет)
    «Вывеска» / Премиум             → 0 = «Цена по запросу»
    «Ролл-ап / Паук» / Стандарт     → 2250
    «Трассировка…» / Простой        → 1000
    поиск стороны без «4+» имени исключает 4+N-позиции (parity фильтра)
"""

from __future__ import annotations

import pytest

from printcalc.calculators.design import DesignConfig, compute
from printcalc.calculators.design.config import build_prices
from printcalc.engine.errors import CalcInputError


def _cfg() -> DesignConfig:
    return DesignConfig()


# ---------- golden-кейсы ----------


def test_golden_visitka_4plus0_simple() -> None:
    result = compute(
        {"service": "Дизайн визитки", "side": "4+0", "option": "Простой"}, _cfg()
    )
    assert result.price == 600.0
    assert result.price_no_tax == 600.0
    assert result.details["price_item"] == "Дизайн визитки 4+0"
    assert result.details["category"] == "Дизайн полиграфия"
    assert result.warnings == ()


def test_golden_visitka_4plus4_complex() -> None:
    result = compute(
        {"service": "Дизайн визитки", "side": "4+4", "option": "Сложный"}, _cfg()
    )
    assert result.price == 2000.0
    assert result.details["price_item"] == "Дизайн визитки 4+4"


def test_golden_poster_a3_medium() -> None:
    result = compute({"service": "Плакат А3", "option": "Средний"}, _cfg())
    assert result.price == 2600.0


def test_golden_layout_page_circulation_ignored() -> None:
    # Тираж/полосы на цену НЕ влияют (прайс за работу) — parity legacy.
    r1 = compute({"service": "Вёрстка презентации (за страницу)", "pages": 1}, _cfg())
    r2 = compute({"service": "Вёрстка презентации (за страницу)", "pages": 10}, _cfg())
    assert r1.price == 750.0 == r2.price


def test_golden_vyveska_price_on_request() -> None:
    result = compute({"service": "Вывеска", "option": "Премиум"}, _cfg())
    assert result.price == 0.0
    assert result.details["price_on_request"] is True
    assert "Цена по запросу" in result.warnings


def test_golden_rollup_standard() -> None:
    result = compute({"service": "Ролл-ап / Паук", "option": "Стандарт"}, _cfg())
    assert result.price == 2250.0


def test_golden_trace_simple() -> None:
    result = compute(
        {"service": "Трассировка (перевод растра в вектор)", "option": "Простой"},
        _cfg(),
    )
    assert result.price == 1000.0
    assert result.details["category"] == "Дизайн прочие услуги"


# ---------- фильтр стороны (parity updatePrice) ----------


def test_side_filter_excludes_4plus_names_without_side() -> None:
    # Листовка без стороны: только позиции без «4+» в имени… у Листовки все
    # с 4+N → lookup с side='' должен вернуть None («по договорённости»).
    result = compute({"service": "Листовка", "option": "Простой"}, _cfg())
    assert result.price == 0.0
    assert result.details["price_found"] is False
    assert any("по договорённости" in w for w in result.warnings)


def test_side_filter_picks_matching_side() -> None:
    result = compute({"service": "Листовка", "side": "4+4", "option": "Средний"}, _cfg())
    assert result.price == 1950.0


# ---------- справочник ----------


def test_config_counts_parity_legacy() -> None:
    # Полный прайс legacy: 114 позиций / 42 базовых услуги (проверено
    # деривацией build_prices). Меняется только с прайсом.
    prices = build_prices()
    assert len(prices) == 114
    assert len(_cfg().services()) == 42


def test_sides_for_visitka() -> None:
    assert _cfg().sides_for("Дизайн визитки") == ("4+0", "4+4")
    assert _cfg().sides_for("Плакат А3") == ()


# ---------- валидация ----------


def test_empty_service_raises() -> None:
    with pytest.raises(CalcInputError):
        compute({"service": ""}, _cfg())


def test_unknown_service_raises() -> None:
    with pytest.raises(CalcInputError):
        compute({"service": "Портрет маслом"}, _cfg())


def test_negative_pages_raises() -> None:
    with pytest.raises(CalcInputError):
        compute({"service": "Плакат А3", "option": "Простой", "pages": -1}, _cfg())
