"""Тесты S1: нормализатор текста → OrderDraft (РОАДМАП_v7 §2, промт_6 R1).

DoD РОАДМАП_v7 §2: факты нормализуются однозначно; неизвестное не
теряется (unknown/needs_operator). Golden-примеры: 4 из интервью
(промт_6 §4.1–4.4) + примеры PROJECT_STATUS_REPORT (парсер-контракт v2:
ксерокс/фото с числами, мультизаказ «и»).

Ключевая честная фиксация (проверено живой пробой перед кодом, отчёт
R1 §3): парсер v2 НЕ распознаёт широкоформатные продукты («наклейка»,
«баннер», «бэклит» → unknown; «резка» ложечно матчится cnc). Поэтому
нормализатор читает ТЕКСТ напрямую, а ParseResult — источник qty и
unknown, не продуктов.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from printcalc_web.parser import parse
from printcalc_web.rules import (
    KNOWN_FACT_KEYS,
    KNOWN_FINISHING_TOKENS,
    KNOWN_PRODUCT_LABELS,
    OrderDraft,
    normalize_order,
)

# --- 1. Golden-примеры интервью (промт_6 §4.1–4.4) -----------------------


class TestInterviewGolden:
    def test_4_1_sticker_contour(self) -> None:
        """«Наклейка 50×30, 149 шт + резка по контуру» — эталон §4.1."""
        draft = normalize_order("Наклейка 50×30, 149 шт + резка по контуру")
        assert draft.product == "наклейка"
        assert draft.size_mm == (500.0, 300.0), "50×30 без единицы = см (§4.1: 500×300 мм)"
        assert draft.quantity == 149
        assert draft.finishings == ("плоттерная_резка",)
        assert draft.fact("cutting") == "true"
        assert draft.fact("cutting_mode") == "contour"

    def test_4_2_sticker_individual_mounting(self) -> None:
        """«Наклейка 20×30, 40 шт, с монтажной, порезать поштучно» — §4.2."""
        draft = normalize_order("Наклейка 20×30, 40 шт, с монтажной, порезать поштучно")
        assert draft.product == "наклейка"
        assert draft.size_mm == (200.0, 300.0)
        assert draft.quantity == 40
        assert draft.fact("cutting_mode") == "individual", "«порезать поштучно» → individual"
        assert draft.fact("mounting_film") == "true"
        assert "накатка" in draft.finishings, "монтажная плёнка → накатка (OP-15)"
        assert "плоттерная_резка" in draft.finishings

    def test_4_3_banner_grommets(self) -> None:
        """«Баннер 3×6 + люверсы 30 см» — эталон §4.3."""
        draft = normalize_order("Баннер 3×6 + люверсы 30 см")
        assert draft.product == "баннер"
        assert draft.size_mm == (3000.0, 6000.0), "обе стороны ≤ 10 → метры (§4.3)"
        assert draft.quantity is None, "количество не указано — не теряется, но и не выдумывается"
        assert draft.fact("grommets") == "true"
        assert draft.fact("grommets_step_cm") == "30", "шаг из текста (30) ≠ канон 50 (решение R0 §6.1)"
        assert "люверсы" in draft.finishings

    def test_4_4_backlit_contour(self) -> None:
        """«Бэклит 80×60, 1440 dpi, резка по контуру» — эталон §4.4."""
        draft = normalize_order("Бэклит 80×60, 1440 dpi, резка по контуру")
        assert draft.product == "бэклит"
        assert draft.size_mm == (800.0, 600.0)
        assert draft.quantity is None, "§4.4: количество НЕ указано → S2 спросит (blocking)"
        assert draft.fact("dpi") == "1440"
        assert draft.fact("cutting_mode") == "contour"
        assert draft.finishings == ("плоттерная_резка",)


# --- 2. Примеры PROJECT_STATUS_REPORT (контракт parser v2 не сломан) -----


@pytest.fixture()
def parser_conn() -> sqlite3.Connection:
    """Минимальный каталог для parser v2 (как в пробе R1, отчёт §3)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE price_list_items (id INTEGER PRIMARY KEY, name TEXT,"
        " price REAL, synonyms TEXT, archived INTEGER DEFAULT 0)"
    )
    conn.execute(
        "INSERT INTO price_list_items (name, price, synonyms) VALUES (?, ?, ?)",
        ("Ксерокс", 10.0, '["ксерокопия", "копия"]'),
    )
    conn.execute(
        "INSERT INTO price_list_items (name, price, synonyms) VALUES (?, ?, ?)",
        ("Фото на документы", 200.0, '["фото"]'),
    )
    return conn


class TestStatusReportGolden:
    def test_combined_order_keeps_parse_contract(self, parser_conn: sqlite3.Connection) -> None:
        """«ксерокс 5 и фото 20»: ParseResult не сломан (Backward Compatibility)."""
        result = parse(parser_conn, "ксерокс 5 и фото 20")
        assert len(result["items"]) == 2
        assert [item["qty"] for item in result["items"]] == [5.0, 20.0]
        assert [item["segment_id"] for item in result["items"]] == [0, 1]
        draft = normalize_order("ксерокс 5 и фото 20", parse_result=result)
        assert draft.product == "", "прайсовые позиции — не продукты паков"
        assert draft.quantity is None, "«5 шт» без слова шт — qty парсера не подмешивается к непродукту"

    def test_parse_qty_used_when_same_product(self, parser_conn: sqlite3.Connection) -> None:
        """qty парсера берётся только для распознанного им продукта."""
        # wide-продукты парсером не распознаются (проба R1) — qty из текста.
        result = parse(parser_conn, "Наклейка 50×30, 149 шт + резка по контуру")
        assert any("наклейка" in u for u in result["unknown"]), "проба R1: наклейка в unknown"
        draft = normalize_order("Наклейка 50×30, 149 шт + резка по контуру", parse_result=result)
        assert draft.quantity == 149, "qty пришёл из текста, не из парсера"

    def test_two_copies_stemming(self, parser_conn: sqlite3.Connection) -> None:
        """«2 ксерокса» — стемминг флексий парсера жив (Этап 8)."""
        result = parse(parser_conn, "2 ксерокса")
        assert result["items"][0]["qty"] == 2.0

    def test_flexions_of_product_labels(self) -> None:
        """«наклейки», «стикеры», «баннеры» — флексии, не новые токены."""
        for text, label in (
            ("наклейки 12 шт", "наклейка"),
            ("стикеры 50×50, 3 шт", "наклейка"),
            ("баннеры 3×6", "баннер"),
        ):
            draft = normalize_order(text)
            assert draft.product == label, text


# --- 3. Закрытые словари (ANTI-6b) ---------------------------------------


class TestClosedVocabularies:
    def test_all_extracted_facts_are_known_keys(self) -> None:
        """Любой факт в drafts — ключ KNOWN_FACT_KEYS (контракт паков)."""
        texts = (
            "Наклейка 50×30, 149 шт + резка по контуру",
            "Баннер 3×6 + люверсы 30 см, на улицу",
            "Бэклит 80×60, 1440 dpi, резка по контуру",
            "Оформление витрины плёнкой, двусторонняя",
        )
        for text in texts:
            draft = normalize_order(text)
            assert set(draft.facts) <= set(KNOWN_FACT_KEYS), f"{text}: {set(draft.facts)}"

    def test_finishings_are_closed_tokens(self) -> None:
        """finishings — только токены KNOWN_FINISHING_TOKENS (→ коды каталога)."""
        draft = normalize_order("Наклейка 20×30, 40 шт, с монтажной, порезать поштучно")
        assert set(draft.finishings) <= set(KNOWN_FINISHING_TOKENS)

    def test_product_labels_mirror_schema(self) -> None:
        """PRODUCT_LABEL_PATTERNS зеркалит KNOWN_PRODUCT_LABELS (модульный assert)."""
        from printcalc_web.rules.normalize import PRODUCT_LABEL_PATTERNS

        assert {label for label, _ in PRODUCT_LABEL_PATTERNS} == set(KNOWN_PRODUCT_LABELS)

    def test_finishings_map_targets_exist(self) -> None:
        """Каждый токен обработки ведёт на код каталога (OP-хх)."""
        from printcalc_web.rules.schema import KNOWN_FINISHINGS, KNOWN_OPERATION_CODES

        assert set(KNOWN_FINISHINGS.values()) <= set(KNOWN_OPERATION_CODES)

    def test_fact_method_bool_serialization(self) -> None:
        """fact(): bool → "true"/"false", отсутствие → None (не «ложь»)."""
        draft = normalize_order("Баннер 3×6")
        assert draft.fact("grommets") is None, "люверсы не упомянуты — факта нет"
        assert draft.fact("grommets") != "false", "«не указано» ≠ «ложь» (промт_6 §3.8)"
        with_grommets = normalize_order("Баннер 3×6 + люверсы")
        assert with_grommets.fact("grommets") == "true"


# --- 4. Единицы и формат -------------------------------------------------


class TestUnits:
    def test_explicit_units_override_heuristic(self) -> None:
        draft_mm = normalize_order("Наклейка 500×300 мм, 10 шт")
        assert draft_mm.size_mm == (500.0, 300.0)
        draft_m = normalize_order("Баннер 3×6 м, 1 шт")
        assert draft_m.size_mm == (3000.0, 6000.0)

    def test_canonical_size_string(self) -> None:
        """facts['size'] — каноническая строка в мм (equality-контракт when_facts)."""
        draft = normalize_order("Баннер 3×6 + люверсы")
        assert draft.fact("size") == "3000x6000"
        assert draft.fact("size_unit") == "м"

    def test_grommets_step_units(self) -> None:
        assert normalize_order("Баннер 3×6 + люверсы 30 см").fact("grommets_step_cm") == "30"
        assert normalize_order("Баннер 3×6 + люверсы 500 мм").fact("grommets_step_cm") == "50"
        assert normalize_order("Баннер 3×6 + люверсы 1 м").fact("grommets_step_cm") == "100"

    def test_usage_detection(self) -> None:
        assert normalize_order("Баннер 3×6 на улицу").fact("usage") == "улица"
        assert normalize_order("Наклейка 50×30 в помещение, 2 шт").fact("usage") == "помещение"


# --- 5. Неизвестное не теряется (DoD) ------------------------------------


class TestUnknownPreserved:
    def test_unknown_words_captured(self) -> None:
        draft = normalize_order("Наклейка 50×30 со снегозащитой, 5 шт")
        assert any("снегозащитой" in word or "снегозащит" in word for word in draft.unknown_words), (
            "неизвестное слово не выброшено молча"
        )

    def test_recognized_words_not_unknown(self) -> None:
        """Распознанная лексика интервью не попадает в unknown (не шум)."""
        for text in (
            "Наклейка 50×30, 149 шт + резка по контуру",
            "Наклейка 20×30, 40 шт, с монтажной, порезать поштучно",
            "Баннер 3×6 + люверсы 30 см",
            "Бэклит 80×60, 1440 dpi, резка по контуру",
        ):
            draft = normalize_order(text)
            assert draft.unknown_words == (), f"{text!r}: {draft.unknown_words}"

    def test_parse_unknown_passed_through(self, parser_conn: sqlite3.Connection) -> None:
        result = parse(parser_conn, "наклейка странный_токен 5 шт")
        draft = normalize_order("наклейка странный_токен 5 шт", parse_result=result)
        assert "странный_токен" in draft.unknown_words

    def test_empty_and_nonsense(self) -> None:
        draft = normalize_order("")
        assert draft.product == "" and draft.size_mm is None and draft.quantity is None
        draft2 = normalize_order("абракадабра")
        assert draft2.product == "" and draft2.unknown_words == ("абракадабра",)


# --- 6. Витрина (решение R0 §6.2) и новый факт ---------------------------


class TestVitrine:
    def test_vitrine_product_and_fact(self) -> None:
        draft = normalize_order("Оформление витрины плёнкой, 12 м2")
        assert draft.product == "оформление витрины"
        assert draft.fact("vitrine") == "true"

    def test_vitrine_fact_also_for_sticker_mention(self) -> None:
        """«наклейка для оформления витрины» → наклейка + факт витрины."""
        draft = normalize_order("Наклейка для оформления витрины 200×100, 5 шт")
        assert draft.product == "наклейка", "порядок паттернов: длинная фраза не съедает продукт"
        assert draft.fact("vitrine") == "true"

    def test_no_vitrine_fact_without_word(self) -> None:
        draft = normalize_order("Наклейка 50×30, 149 шт")
        assert "vitrine" not in draft.facts


# --- 7. Идемпотентность (промт_6 R2-требование, закладываем в S1) --------


class TestIdempotence:
    def test_normalize_is_pure(self) -> None:
        text = "Наклейка 20×30, 40 шт, с монтажной, порезать поштучно"
        first = normalize_order(text)
        second = normalize_order(text)
        assert first == second
        assert first.facts == second.facts

    def test_draft_frozen(self) -> None:
        draft = normalize_order("Баннер 3×6 + люверсы")
        with pytest.raises(Exception):  # noqa: B017 — frozen dataclass подменяет тип ошибки
            draft.quantity = 5  # type: ignore[misc]


# --- 8. ParseResult-совместимость: исходные поля не ломаются --------------


class TestParseContractIntact:
    def test_parse_result_fields_superset(self, parser_conn: sqlite3.Connection) -> None:
        """items/unknown/needs_operator/reasons/segment_id/volume_hints живы."""
        result: dict[str, Any] = parse(parser_conn, "ксерокс 5 и фото 20")
        for key in ("items", "unknown", "needs_operator", "reasons", "segment_id", "volume_hints"):
            assert key in result or "segment_id" in str(result["items"][0]), key
        assert all("segment_id" in item for item in result["items"])
