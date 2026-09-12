"""Golden-тесты калькулятора широкоформата (порт legacy wide_format.py).

Ожидаемые значения выведены НЕЗАВИСИМО от порта — симуляцией legacy-формулы
calculate() (wide_format.py:660-756) на замороженных константах конфига.
Менять ожидания только осознанно, новой редакцией теста.
"""

from __future__ import annotations

import pytest

from printcalc.calculators.wide import WideConfig, compute
from printcalc.engine.errors import CalcInputError


# ---------- golden: полный состав (тиры + крепёж + работы + люверсы) ----------


def test_golden_banner_tiers_mount_works_grommets() -> None:
    """Баннер 440г 3×1 м × 2 шт, интерьерная печать, монтаж, загибка + люверсы.

    Независимая деривация: area = 300·100/10000·2 = 6.0 м² → тир 5<6<=20:
    материал 180/300, печать 400/700. Периметр одной = 800 см → люверсов
    ceil(800/50) = 16 на штуку, × 2 = 32 шт. Загибка — 16 пог.м.
    cost = 180·6 + 400·6 + 1000 + 100·16 + 10·32 + 150·6 = 7300.0
    sell = 300·6 + 700·6 + 2500 + 200·16 + 20·32 + 250·6 = 13840.0
    """
    result = compute(
        {
            "width": 300.0,
            "height": 100.0,
            "qty": 2.0,
            "material": "Баннер 440г",
            "print": "Интерьерная печать",
            "mount": "Монтаж без подъёма (до 2 м)",
            "work_hemming": True,
            "work_eyelets": True,
            "grommet_interval": 50.0,
        }
    )
    assert result.price == pytest.approx(13840.0)
    assert result.cost == pytest.approx(7300.0)
    assert result.net_profit == pytest.approx(6540.0)
    assert result.unit_price == pytest.approx(6920.0)
    assert result.price_no_tax == result.price  # налог в цене не участвует
    assert result.details["area_total"] == pytest.approx(6.0)
    works = {w["name"]: w["qty"] for w in result.details["works"]}
    assert works["Загибка по периметру"] == pytest.approx(16.0)
    assert works["Люверсы по периметру"] == pytest.approx(32.0)


# ---------- golden: тир по границе и открытый верх ----------


def test_golden_tier_boundary_inclusive() -> None:
    """Площадь ровно 5.0 м²: верхняя граница тира ВКЛЮЧИТЕЛЬНА (area <= max).    Паритет get_price (wide_format.py:118-119): 5.0 <= 5 → первый тир 200/350,
    а не 180/300. sell = 350·5 + 250·5 = 3000.0 (печать «Без печати»).
    """
    result = compute(
        {
            "width": 500.0,
            "height": 100.0,
            "qty": 1.0,
            "material": "Баннер 440г",
            "print": "Без печати",
            "mount": "Без монтажа",
        }
    )
    assert result.price == pytest.approx(3000.0)
    assert result.cost == pytest.approx(1750.0)  # 200·5 + 150·5


def test_golden_open_ended_tier() -> None:
    """Площадь 25 м² > последней границы: открытый тир (max=None).

    Холст 25 м²: тир 2<25 → 380/650. Экстерьерная печать 25 м²: 450/800.
    sell = 280·25 + 800·25 + 250·25 = 7000 + 20000 + 6250 = 33250.0
    """
    result = compute(
        {
            "width": 500.0,
            "height": 500.0,
            "qty": 1.0,
            "material": "Баннер 440г",
            "print": "Экстерьерная печать",
            "mount": "Без монтажа",
        }
    )
    assert result.price == pytest.approx(33250.0)
    assert result.cost == pytest.approx(19000.0)  # 160·25 + 450·25 + 150·25


# ---------- golden: неизвестный материал → бесплатно (паритет get_price) ----------


def test_golden_unknown_material_is_free() -> None:
    """Неизвестное имя материала в legacy НЕ падает: get_price вернёт (0, 0).

    Плёнка 2 м², интерьерная печать (0<2<=5 → 450/800):
    cost = 0 + 450·2 + 150·2 = 1200.0; sell = 0 + 800·2 + 250·2 = 2100.0
    """
    result = compute(
        {
            "width": 200.0,
            "height": 100.0,
            "qty": 1.0,
            "material": "Ткань неизвестная",
            "print": "Интерьерная печать",
            "mount": "Без монтажа",
        }
    )
    assert result.cost == pytest.approx(1200.0)
    assert result.price == pytest.approx(2100.0)


# ---------- golden: минимальная сумма заказа ----------


def test_golden_min_order_bump() -> None:
    """min_order_price поднимает продажную цену (wide_format.py:724-733).

    База как в test_golden_unknown_material_is_free (sell=2100), но конфиг
    с min_order_price=5000: sell → 5000, cost не меняется (1200).
    """
    config = WideConfig(min_order_price=5000.0)
    result = compute(
        {
            "width": 200.0,
            "height": 100.0,
            "qty": 1.0,
            "material": "Ткань неизвестная",
            "print": "Интерьерная печать",
            "mount": "Без монтажа",
        },
        config,
    )
    assert result.price == pytest.approx(5000.0)
    assert result.cost == pytest.approx(1200.0)
    assert result.net_profit == pytest.approx(3800.0)
    assert any("минимальной" in w for w in result.warnings)


# ---------- golden: периметр-работа и крепёж не умножается на тираж ----------


def test_golden_pocket_work_and_flat_mount() -> None:
    """Карман (m) — от ОБЩЕГО периметра; крепёж — фикс за заказ (×1).

    Холст 250×100 см × 3 шт: area = 7.5 м² (тир 2<7.5 → 380/650),
    общий периметр = (250+100)·2/100·3 = 21 пог.м. Карман 250/400 за пог.м.
    Крепёж «Монтаж без подъёма (до 2 м)» — 1000/2500 ОДИН раз.
    cost = 380·7.5 + 1000 + 250·21 + 150·7.5 = 2850+1000+5250+1125 = 10225.0
    sell = 650·7.5 + 2500 + 400·21 + 250·7.5 = 4875+2500+8400+1875 = 17650.0
    """
    result = compute(
        {
            "width": 250.0,
            "height": 100.0,
            "qty": 3.0,
            "material": "Холст",
            "print": "Без печати",
            "mount": "Монтаж без подъёма (до 2 м)",
            "work_pocket": True,
        }
    )
    assert result.cost == pytest.approx(10225.0)
    assert result.price == pytest.approx(17650.0)
    works = {w["name"]: w["qty"] for w in result.details["works"]}
    assert works["Карман"] == pytest.approx(21.0)  # (250+100)·2/100·3


# ---------- golden: единица «шт» без люверсов = тираж ----------


def test_golden_piece_work_qty_equals_run() -> None:
    """Работа «шт» без is_grommet = тираж (ветка else, wide_format.py:708).

    В каноническом конфиге wide таких работ нет — ветка покрыта инъекцией.
    Слаг берётся по умолчанию из имени (WORK_SLUGS.get(name, name)), поэтому
    вход-флаг — "work_Проверка качества". Баннер 440г 200×100 × 4 шт:
    area = 8.0 м² → тир 5<8<=20 → 180/300.
    cost = 180·8 + 150·8 + 5·4 = 1440+1200+20 = 2660.0
    sell = 300·8 + 250·8 + 10·4 = 2400+2000+40 = 4440.0
    """
    from printcalc.calculators.wide.config import WorkPrice

    config = WideConfig(
        works=(
            WorkPrice("Проверка качества", unit="шт", cost=5.0, sell=10.0),
        ),
    )
    result = compute(
        {
            "width": 200.0,
            "height": 100.0,
            "qty": 4.0,
            "material": "Баннер 440г",
            "print": "Без печати",
            "mount": "Без монтажа",
            "work_Проверка качества": True,
        },
        config,
    )
    assert result.cost == pytest.approx(2660.0)
    assert result.price == pytest.approx(4440.0)
    works = {w["name"]: w["qty"] for w in result.details["works"]}
    assert works["Проверка качества"] == pytest.approx(4.0)  # = тираж


def test_golden_plotter_cut_configurable_m2_price() -> None:
    """Ревью цены OP-22 (решение Дениса 2026-09-12, РОАДМАП_v7 §10).

    Цена «Плоттерной резки» — НАСТРАИВАЕМЫЙ параметр: дефолт 0/0, цифры
    вносит владелец инъекцией WideConfig (прайсом). Формула — unit="m2":
    количество = тиражная площадь (ширина×высота×тираж, compute.py:63),
    т.е. цена растёт с размером И тиражом (unit="шт" игнорировал бы размер
    наклейки). Якорь владельца — «Резка по контуру» м² 100/500
    (wide_format_config.json, GUI-редактор).

    Наклейка 50×30 см × 149 шт: area = 0.5·0.3·149 = 22.35 м²
    (width/height — в СМ, паритет legacy wide_format.py:665).
    Плёнка самоклеящаяся 10<22.35 → 280/500; экстерьер 450/800.
    Вклад работы: 100·22.35 = 2235 cost / 500·22.35 = 11175 sell.
    """
    from printcalc.calculators.wide.config import WorkPrice

    inputs = {
        "width": 50.0,
        "height": 30.0,
        "qty": 149.0,
        "material": "Плёнка самоклеящаяся",
        "print": "Экстерьерная печать",
        "mount": "Без монтажа",
        "work_plotter_cut": True,  # ASCII-слаг (WORK_SLUGS), не русское имя
    }

    # Дефолт: работа включена, вклад 0 (цена не задана владельцем).
    base = compute(inputs)
    works_default = {w["name"]: (w["qty"], w["qty"]) for w in base.details["works"]}
    assert works_default["Плоттерная резка"][0] == pytest.approx(22.35)  # м² формулы

    # Инъекция прайса владельца: 100/500 ₽/м².
    config = WideConfig(
        works=(
            WorkPrice("Плоттерная резка", unit="m2", cost=100.0, sell=500.0),
        ),
    )
    priced = compute(inputs, config)
    assert priced.cost == pytest.approx(base.cost + 2235.0)
    assert priced.price == pytest.approx(base.price + 11175.0)


def test_golden_plotter_cut_default_zero_contribution() -> None:
    """Дефолт 0/0 не меняет суммы заказа (настраиваемость без сюрпризов).

    Один и тот же заказ с флагом work_plotter_cut и без него — одинаковые
    суммы при каноническом конфиге; работа видна в детализации с qty=м².
    """
    inputs = {
        "width": 50.0,  # см
        "height": 30.0,  # см
        "qty": 149.0,
        "material": "Плёнка самоклеящаяся",
        "print": "Экстерьерная печать",
        "mount": "Без монтажа",
    }
    without_flag = compute(inputs)
    with_flag = compute({**inputs, "work_plotter_cut": True})
    assert with_flag.cost == pytest.approx(without_flag.cost)
    assert with_flag.price == pytest.approx(without_flag.price)
    works = {w["name"]: w["qty"] for w in with_flag.details["works"]}
    assert works["Плоттерная резка"] == pytest.approx(22.35)


# ---------- ошибки входа (паритет legacy-веток) ----------


def test_error_qty_zero() -> None:
    with pytest.raises(CalcInputError):
        compute(
            {
                "width": 200.0,
                "height": 100.0,
                "qty": 0.0,
                "material": "Баннер 440г",
                "print": "Без печати",
                "mount": "Без монтажа",
            }
        )


def test_error_grommet_interval_zero() -> None:
    """Интервал люверсов <= 0 — ошибка (legacy messagebox, wide_format.py:702-706)."""
    with pytest.raises(CalcInputError):
        compute(
            {
                "width": 300.0,
                "height": 100.0,
                "qty": 1.0,
                "material": "Баннер 440г",
                "print": "Без печати",
                "mount": "Без монтажа",
                "work_eyelets": True,
                "grommet_interval": 0.0,
            }
        )


def test_error_unknown_mount() -> None:
    """Крепёж — членство строго (в legacy next() без дефолта упал бы так же)."""
    with pytest.raises(CalcInputError):
        compute(
            {
                "width": 200.0,
                "height": 100.0,
                "qty": 1.0,
                "material": "Баннер 440г",
                "print": "Без печати",
                "mount": "Нет такого монтажа",
            }
        )
