"""Тесты runtime-прайса доп. работ wide (printcalc_web/pricing.py).

Решение Дениса 2026-09-12 (РОАДМАП_v7 §10): цены доп. работ — настраиваемый
параметр; цифры вносит владелец YAML-файлом, код цен не содержит. Покрывают:
merge по имени поверх канона, громкие ошибки (ANTI-6b), отсутствующий файл,
кэш по mtime+size, связку с реестром заказов и живой шаблон.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from printcalc.calculators.wide.compute import compute
from printcalc_web import pricing


_STICKER = {
    "width": 50.0,  # см
    "height": 30.0,  # см
    "qty": 149.0,
    "material": "Плёнка самоклеящаяся",
    "print": "Экстерьерная печать",
    "mount": "Без монтажа",
    "work_plotter_cut": True,
}


@pytest.fixture()
def prices_path(tmp_path: Path) -> Path:
    """Изолированный путь прайс-файла + чистый кэш модуля на каждый тест."""
    pricing._CACHE.clear()
    path = tmp_path / "wide_prices.yaml"
    os.environ[pricing.PRICES_ENV_VAR] = str(path)
    yield path
    os.environ.pop(pricing.PRICES_ENV_VAR, None)
    pricing._CACHE.clear()


# ---------- отсутствующий файл = канон ----------


def test_missing_file_returns_canon(prices_path: Path) -> None:
    config = pricing.get_wide_config()
    canon = type(config)()
    assert [w.name for w in config.works] == [w.name for w in canon.works]
    assert all(
        w.cost == c.cost and w.sell == c.sell
        for w, c in zip(config.works, canon.works)
    )


def test_missing_file_via_env_is_ok(prices_path: Path) -> None:
    # env-путь указан, файла нет — канон, не ошибка.
    assert pricing.get_wide_config().works == type(pricing.get_wide_config())().works


def test_template_copy_noop(prices_path: Path) -> None:
    """Верbatim-копия шаблона (всё закомментировано → works: null) — валидна, канон 1:1."""
    template = Path(__file__).resolve().parents[1] / "wide_prices.template.yaml"
    prices_path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    config = pricing.get_wide_config()
    canon = type(config)()
    assert [(w.cost, w.sell) for w in config.works] == [(w.cost, w.sell) for w in canon.works]


# ---------- merge по имени ----------


def test_override_sell_only_keeps_canon_cost(prices_path: Path) -> None:
    prices_path.write_text(
        "works:\n  Плоттерная резка:\n    sell: 500.0\n",
        encoding="utf-8",
    )
    merged = {w.name: w for w in pricing.get_wide_config().works}
    op22 = merged["Плоттерная резка"]
    assert op22.sell == pytest.approx(500.0)
    assert op22.cost == pytest.approx(0.0)  # канон
    assert op22.unit == "m2"  # формулы канона не трогаем


def test_override_cost_and_sell(prices_path: Path) -> None:
    prices_path.write_text(
        "works:\n  Плоттерная резка:\n    sell: 500.0\n    cost: 100.0\n",
        encoding="utf-8",
    )
    merged = {w.name: w for w in pricing.get_wide_config().works}
    assert merged["Плоттерная резка"].cost == pytest.approx(100.0)
    assert merged["Плоттерная резка"].sell == pytest.approx(500.0)


def test_merge_leaves_other_works_untouched(prices_path: Path) -> None:
    prices_path.write_text(
        "works:\n  Люверсы по периметру:\n    sell: 30.0\n",
        encoding="utf-8",
    )
    merged = {w.name: w for w in pricing.get_wide_config().works}
    assert merged["Люверсы по периметру"].sell == pytest.approx(30.0)
    assert merged["Плоттерная резка"].sell == pytest.approx(0.0)  # не тронута


def test_registry_compute_uses_overrides(
    prices_path: Path,
) -> None:
    """Реестр заказов считает по переопределённым ценам (якорь 100/500 м²)."""
    from printcalc_web.calculators import get_registry
    from printcalc.engine.registry import calculate

    prices_path.write_text(
        "works:\n  Плоттерная резка:\n    sell: 500.0\n    cost: 100.0\n",
        encoding="utf-8",
    )
    result = calculate(get_registry(), "wide", _STICKER)
    result_base = calculate(get_registry(), "wide", {**_STICKER, "work_plotter_cut": False})

    delta = result.price - result_base.price
    assert delta == pytest.approx(500.0 * 22.35)  # 11175 ₽

    works = {w["name"]: w for w in result.details["works"]}
    assert works["Плоттерная резка"]["qty"] == pytest.approx(22.35)


# ---------- громкие ошибки ----------


def test_unknown_work_name_loud(prices_path: Path) -> None:
    prices_path.write_text(
        "works:\n  Несуществующая работа:\n    sell: 100.0\n",
        encoding="utf-8",
    )
    with pytest.raises(pricing.PriceConfigError, match="неизвестные работы"):
        pricing.get_wide_config()


def test_unknown_key_loud(prices_path: Path) -> None:
    prices_path.write_text(
        "works:\n  Плоттерная резка:\n    price: 100.0\n",
        encoding="utf-8",
    )
    with pytest.raises(pricing.PriceConfigError, match="неизвестный ключ"):
        pricing.get_wide_config()


def test_negative_price_loud(prices_path: Path) -> None:
    prices_path.write_text(
        "works:\n  Плоттерная резка:\n    sell: -5.0\n",
        encoding="utf-8",
    )
    with pytest.raises(pricing.PriceConfigError, match="отрицательным"):
        pricing.get_wide_config()


def test_non_numeric_loud(prices_path: Path) -> None:
    prices_path.write_text(
        "works:\n  Плоттерная резка:\n    sell: 'много'\n",
        encoding="utf-8",
    )
    with pytest.raises(pricing.PriceConfigError, match="должен быть числом"):
        pricing.get_wide_config()


def test_empty_entry_loud(prices_path: Path) -> None:
    prices_path.write_text(
        "works:\n  Плоттерная резка: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(pricing.PriceConfigError, match="пуста"):
        pricing.get_wide_config()


def test_works_not_dict_loud(prices_path: Path) -> None:
    prices_path.write_text("works:\n  - Плоттерная резка\n", encoding="utf-8")
    with pytest.raises(pricing.PriceConfigError, match="должен быть словарём"):
        pricing.get_wide_config()


def test_invalid_yaml_loud(prices_path: Path) -> None:
    prices_path.write_text("works: [unclosed\n", encoding="utf-8")
    with pytest.raises(pricing.PriceConfigError, match="YAML"):
        pricing.get_wide_config()


# ---------- кэш / перечитывание ----------


def test_mtime_cache_reload(prices_path: Path) -> None:
    """Правка файла владельцем подхватывается без рестарта (mtime+size)."""
    prices_path.write_text(
        "works:\n  Плоттерная резка:\n    sell: 500.0\n",
        encoding="utf-8",
    )
    first = {w.name: w.sell for w in pricing.get_wide_config().works}
    assert first["Плоттерная резка"] == pytest.approx(500.0)

    # Та же секунда, другой размер файла — size в отпечатке гарантирует перечитывание.
    prices_path.write_text(
        "works:\n  Плоттерная резка:\n    sell: 600.0\n",
        encoding="utf-8",
    )
    second = {w.name: w.sell for w in pricing.get_wide_config().works}
    assert second["Плоттерная резка"] == pytest.approx(600.0)


# ---------- ручной path-аргумент ----------


def test_explicit_path_argument(tmp_path: Path) -> None:
    pricing._CACHE.clear()
    path = tmp_path / "p.yaml"
    path.write_text(
        "works:\n  Плоттерная резка:\n    sell: 700.0\n",
        encoding="utf-8",
    )
    merged = {w.name: w.sell for w in pricing.get_wide_config(path).works}
    assert merged["Плоттерная резка"] == pytest.approx(700.0)
    pricing._CACHE.clear()
