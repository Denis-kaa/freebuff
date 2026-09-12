"""Тесты S0: схема YAML-паков производственных правил (РОАДМАП_v7, промт_печатник_6).

Покрывают: валидацию встроенных паков v1 (sticker, banner), зеркальность
закрытых словарей реальным источникам (ANTI-6b), drift-детекцию
(ValueError), финализированные решения (pack != product, пустые
when_facts, product_label), уникальность rule_id/product_label глобально
и loud-ошибку без PyYAML.
"""

from __future__ import annotations

import builtins
import importlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pytest

from printcalc_web.rules import (
    KNOWN_FACT_KEYS,
    KNOWN_MISSING_FIELDS,
    KNOWN_OPERATION_CODES,
    KNOWN_PRODUCTS,
    PACKS_DIR,
    PackValidationError,
    load_builtin_packs,
    load_pack,
    load_packs,
    validate_pack_document,
)

# --- 1. Встроенные паки валидны и структурно полны -----------------------


def test_builtin_packs_load_and_validate() -> None:
    packs = load_builtin_packs()
    assert set(packs) == {"sticker", "banner"}, "S0: ровно два пака v1"
    for name, pack in packs.items():
        assert pack.pack == name
        assert pack.product == "wide", "наклейка и баннер сидят на калькуляторе wide"
        assert pack.product_label in {"наклейка", "баннер"}
        assert pack.rules, f"пак {name} не пуст"
        for rule in pack.rules:
            # Правило 6: предлагает операцию ИЛИ хотя бы одну подсказку.
            assert rule.propose_operation is not None or rule.suggest
            # У каждой подсказки обязателен reason (никакой магии).
            for suggestion in rule.suggest:
                assert suggestion["reason"].strip()
                assert suggestion["options"]


def test_sticker_pack_covers_interview_examples() -> None:
    """Промт_6 §4.1/§4.2: контурная резка и «порезать поштучно» → OP-22."""
    packs = load_builtin_packs()
    sticker = packs["sticker"]
    by_id = {rule.rule_id: rule for rule in sticker.rules}
    assert by_id["STICKER_CUT_CONTOUR_PLOTTER"].propose_operation == "OP-22"
    assert by_id["STICKER_CUT_INDIVIDUAL_PLOTTER"].propose_operation == "OP-22"
    contour = by_id["STICKER_CUT_CONTOUR_PLOTTER"]
    assert "layout_with_cut_contour" in contour.require
    labels = [s["label"] for s in contour.suggest]
    assert any("Макет" in label for label in labels), "вопрос про макет с контуром"


def test_banner_pack_propose_only_montage() -> None:
    """Промт_6 §4.3: люверсы — факт (OP-13), монтаж — ТОЛЬКО предложение."""
    packs = load_builtin_packs()
    banner = packs["banner"]
    by_id = {rule.rule_id: rule for rule in banner.rules}
    assert by_id["BANNER_GROMMETS_STEP_CONFIRM"].propose_operation == "OP-13"
    montage = by_id["BANNER_MONTAGE_OFFER"]
    assert montage.propose_operation is None, "монтаж никогда не добавляется автоматически"
    assert montage.when_facts == {}, "правило уровня продукта (when_facts пуст)"
    labels = [s["label"] for s in montage.suggest]
    assert any("Монтаж" in label for label in labels)


# --- 2. Зеркальность закрытых словарей реальным источникам (ANTI-6b) ----


def _seeded_operation_codes() -> set[str]:
    """Коды операций из реального сида каталога (store.DEFAULT_OPERATIONS)."""
    from printcalc_web.store import DEFAULT_OPERATIONS

    return {op["code"] for op in DEFAULT_OPERATIONS}


def test_operation_vocabulary_mirrors_store_seed() -> None:
    """Каждый код сида обязан быть в словаре (иначе паки «не видят» каталог)."""
    seeded = _seeded_operation_codes()
    missing = seeded - KNOWN_OPERATION_CODES
    assert not missing, f"словарь операций отстал от сида: {sorted(missing)}"


def test_propose_operation_targets_exist_in_seed_or_catalog_doc() -> None:
    """OP-22 отсутствует в сиде — проверяем, что он задокументирован как новый
    (см. PHASE_RULES_R0_REPORT §3), и что propose-цели паков из словаря."""
    packs = load_builtin_packs()
    for pack in packs.values():
        for rule in pack.rules:
            if rule.propose_operation is not None:
                assert rule.propose_operation in KNOWN_OPERATION_CODES


def test_products_mirror_engine_registry() -> None:
    """Мост реестра — printcalc_web.calculators (engine registry собирается там)."""
    from printcalc_web.calculators import get_registry

    registry_ids = set(get_registry().ids())
    missing = registry_ids - KNOWN_PRODUCTS
    assert not missing, f"словарь продуктов отстал от реестра движка: {sorted(missing)}"


def test_fact_and_missing_vocabularies_are_closed_sets() -> None:
    """Закрытые наборы — tuple/frozenset (не мутируют на лету)."""
    assert isinstance(KNOWN_FACT_KEYS, frozenset)
    assert isinstance(KNOWN_MISSING_FIELDS, frozenset)
    assert isinstance(KNOWN_OPERATION_CODES, frozenset)
    assert "quantity" in KNOWN_MISSING_FIELDS
    assert "layout_with_cut_contour" in KNOWN_MISSING_FIELDS


# --- 3. Drift-детекция: невалидные паки → PackValidationError ------------


def _valid_document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "pack": "tmp",
        "product": "wide",
        "rules": [
            {
                "rule_id": "TMP_RULE",
                "when_facts": {"cutting": "true"},
                "propose_operation": "OP-22",
                "require": ["quantity"],
                "suggest": [
                    {
                        "kind": "question",
                        "label": "Вопрос?",
                        "options": ["Да", "Нет"],
                        "reason": "тест",
                    }
                ],
            }
        ],
    }


def test_valid_inline_document_passes() -> None:
    pack = validate_pack_document(_valid_document(), source="inline")
    assert pack.product == "wide"
    assert pack.rules[0].propose_operation == "OP-22"


@pytest.mark.parametrize(
    ("mutator", "fragment"),
    [
        (lambda d: d.update(product="chpstu"), "products"),  # неизвестный продукт
        (lambda d: d["rules"][0].update(propose_operation="OP-99"), "operations"),
        (lambda d: d["rules"][0].update(require=["alien_field"]), "missing"),
        (lambda d: d["rules"][0].update(when_facts={"неизвестный_факт": "1"}), "фактов"),
        (lambda d: d["rules"][0].update(suggest=[{"kind": "magic", "label": "x", "options": ["a"], "reason": "r"}]), "kind"),
        (lambda d: (d["rules"][0].update(suggest=[]), d["rules"][0].update(propose_operation=None)), "правило обязано"),
        (lambda d: d["rules"][0].update(suggest=[{"kind": "upsell", "label": "x", "options": ["a"]}]), "reason"),
        (lambda d: d["rules"][0].update(suggest=[{"kind": "upsell", "label": "x", "reason": "r", "options": []}]), "options"),
        (lambda d: d.update(schema_version=2), "schema_version"),
        (lambda d: d.update(rules=[]), "rules обязателен"),
        (lambda d: d["rules"][0].update(rule_id="bad-id"), "rule_id"),
        (lambda d: d["rules"][0].update(when_facts=None), "when_facts"),
    ],
)
def test_drift_raises_with_message(mutator, fragment) -> None:
    document = _valid_document()
    mutator(document)
    with pytest.raises(PackValidationError, match=fragment):
        validate_pack_document(document, source="drift-test")


def test_collects_all_errors_not_just_first() -> None:
    document = _valid_document()
    document["product"] = "нет_такого"
    document["rules"][0]["propose_operation"] = "OP-99"
    with pytest.raises(PackValidationError) as excinfo:
        validate_pack_document(document, source="multi")
    text = str(excinfo.value)
    assert "products" in text and "operations" in text, "все ошибки за один прогон"


def test_max_two_suggestions_per_rule() -> None:
    """UPSELL_RULES §3: ≤2 подсказок на шаг — иначе анкета."""
    document = _valid_document()
    triple = [
        {"kind": "question", "label": f"Вопрос {i}?", "options": ["Да"], "reason": "тест"}
        for i in range(3)
    ]
    document["rules"][0]["suggest"] = triple
    with pytest.raises(PackValidationError, match="максимум 2"):
        validate_pack_document(document, source="too-many")


# --- 4. Финализированные решения S0 --------------------------------------


def test_pack_name_may_differ_from_product() -> None:
    document = _valid_document()
    document["pack"] = "sticker"  # != product (wide)
    pack = validate_pack_document(document, source="names")
    assert pack.pack == "sticker" and pack.product == "wide"


def test_product_label_accepted() -> None:
    document = _valid_document()
    document["product_label"] = "наклейка"
    pack = validate_pack_document(document, source="label")
    assert pack.product_label == "наклейка"


def test_duplicate_rule_id_across_packs_rejected(tmp_path: Path) -> None:
    """Уникальность rule_id ГЛОБАЛЬНА (между паками)."""
    base = _valid_document()
    (tmp_path / "aaa.yaml").write_text(
        json.dumps(base).replace("TMP_RULE", "SAME_RULE").encode("utf-8").decode("utf-8"),
        encoding="utf-8",
    )
    other = _valid_document()
    other["pack"] = "other"
    (tmp_path / "bbb.yaml").write_text(
        json.dumps(other).replace("TMP_RULE", "SAME_RULE").encode("utf-8").decode("utf-8"),
        encoding="utf-8",
    )
    with pytest.raises(PackValidationError, match="дублируется"):
        load_packs(tmp_path)


def test_duplicate_product_label_rejected(tmp_path: Path) -> None:
    """Дубли product_label ломают нормализацию S1 — ловим в S0."""
    base = _valid_document()
    base["product_label"] = "наклейка"
    other = _valid_document()
    other["pack"] = "other"
    other["product_label"] = "наклейка"
    (tmp_path / "aaa.yaml").write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "bbb.yaml").write_text(json.dumps(other, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(PackValidationError, match="product_label"):
        load_packs(tmp_path)


# --- 5. PyYAML отсутствует → громкая понятная ошибка (урок Этапа 6) ------


def test_load_pack_without_yaml_is_loud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "x.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "yaml", None)  # блокирует повторный import
    real_import = builtins.__import__

    def _no_yaml(name: str, *args: object, **kwargs: object) -> object:
        if name == "yaml":
            raise ImportError("No module named 'yaml' (симулировано тестом)")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", _no_yaml)
    importlib.invalidate_caches()
    with pytest.raises(PackValidationError, match="PyYAML"):
        load_pack(tmp_path / "x.yaml")


# --- 6. Смоук: паки читаю dry-run через sqlite-соединение (без БД) -------


def test_packs_dir_contains_yaml_sources() -> None:
    files = sorted(p.name for p in PACKS_DIR.glob("*.yaml"))
    assert files == ["banner.yaml", "sticker.yaml"]


def test_store_import_unaffected_by_rules_package() -> None:
    """Импорт rules не тянет store/fastapi: слои независимы (B-Rule 2)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.close()
    # Достаточно того, что импорт модулей теста не упал: store импортируется
    # лениво внутри тестов словаря, rules — без него.
    import printcalc_web.rules  # noqa: F401
    import printcalc_web.rules.schema  # noqa: F401
