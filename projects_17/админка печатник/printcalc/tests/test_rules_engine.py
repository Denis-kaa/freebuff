"""Тесты S2: движок правил ProductionRule → RuleVerdict (РОАДМАП_v7 §3, промт_6 R2).

DoD РОАДМАП_v7 §3: ready_for_calculator корректен на всех golden-примерах
(бэклит без количества → False); идемпотентность вердикта; анти-тест
авто-применения (auto=False всегда).

Golden-вердикты строятся на РЕАЛЬНОМ пайплайне S0+S1: встроенные паки +
нормализатор — никакого параллельного мира тест-фикстур.
"""

from __future__ import annotations

import pytest

from printcalc_web.rules import (
    MissingItem,
    OperationProposal,
    OrderDraft,
    RuleVerdict,
    evaluate_order,
    evaluate_text,
    load_builtin_packs,
    normalize_order,
)


@pytest.fixture(scope="module")
def packs() -> dict:
    return load_builtin_packs()


# --- 1. Golden-вердикты интервью (промт_6 §4) ----------------------------


class TestInterviewGoldenVerdicts:
    def test_4_1_sticker_contour(self, packs: dict) -> None:
        """«Наклейка 50×30, 149 шт + резка по контуру» — §4.1."""
        verdict = evaluate_text("Наклейка 50×30, 149 шт + резка по контуру", packs)
        assert verdict.matched_pack == "sticker"
        ops = [p.operation_token for p in verdict.proposed_operations]
        assert "OP-22" in ops, "стикер + контур → предложить плоттерную резку"
        assert all(not p.auto for p in verdict.proposed_operations)
        labels = [s.label for s in verdict.suggestions]
        assert any("Макет" in label for label in labels), "вопрос про макет с контуром"
        assert verdict.ready_for_calculator is True, "qty и размер есть"
        assert not any(m.blocking for m in verdict.missing)
        assert "STICKER_CUT_CONTOUR_PLOTTER" in verdict.fired_rules

    def test_4_2_sticker_individual(self, packs: dict) -> None:
        """«Наклейка 20×30, 40 шт, с монтажной, порезать поштучно» — §4.2."""
        verdict = evaluate_text("Наклейка 20×30, 40 шт, с монтажной, порезать поштучно", packs)
        assert verdict.matched_pack == "sticker"
        ops = {p.operation_token for p in verdict.proposed_operations}
        assert "OP-22" in ops and "OP-15" in ops, "поштучно → плоттер; монтажная → накатка"
        assert verdict.ready_for_calculator is True

    def test_4_3_banner_grommets(self, packs: dict) -> None:
        """«Баннер 3×6 + люверсы 30 см» — §4.3: люверсы подтверждаются,
        монтаж и макет только ПРЕДЛАГАЮТСЯ."""
        verdict = evaluate_text("Баннер 3×6 + люверсы 30 см", packs)
        assert verdict.matched_pack == "banner"
        ops = [p.operation_token for p in verdict.proposed_operations]
        assert "OP-13" in ops, "люверсы — факт текста → предложение OP-13"
        labels = [s.label for s in verdict.suggestions]
        assert any("Монтаж" in label for label in labels), "монтаж — предложением, не операцией"
        assert "OP-19" not in ops, "монтаж НИКОГДА не добавляется автоматически (§1)"
        assert verdict.draft.fact("grommets_step_cm") == "30", "шаг из текста сохранён"

    def test_4_3_banner_no_qty_blocks(self, packs: dict) -> None:
        """Баннер без тиража: quantity — blocking missing (тираж нужен всегда)."""
        verdict = evaluate_text("Баннер 3×6 + люверсы 30 см", packs)
        blocking = [m.field for m in verdict.missing if m.blocking]
        assert "quantity" in blocking
        assert verdict.ready_for_calculator is False

    def test_4_4_backlit_no_qty_false(self, packs: dict) -> None:
        """Эталон DoD §3: «Бэклит 80×60, 1440 dpi, резка по контуру» —
        количество НЕ указано → ready_for_calculator=False."""
        verdict = evaluate_text("Бэклит 80×60, 1440 dpi, резка по контуру", packs)
        assert verdict.matched_pack == "backlit"
        assert verdict.ready_for_calculator is False, "бэклит без количества — не считать"
        blocking = [m.field for m in verdict.missing if m.blocking]
        assert blocking == ["quantity"], "размер есть (800×600), не хватает только тиража"
        quantity_missing = next(m for m in verdict.missing if m.field == "quantity")
        assert quantity_missing.question == "Количество?"
        ops = [p.operation_token for p in verdict.proposed_operations]
        assert "OP-22" in ops and "OP-04" in ops, "контур → плоттер; бэклит вообще → печать"
        labels = [s.label for s in verdict.suggestions]
        assert any("Подсветка" in label for label in labels), "уточнение подсветки (не операция)"

    def test_4_4_backlit_with_qty_true(self, packs: dict) -> None:
        verdict = evaluate_text("Бэклит 80×60, 3 шт, резка по контуру", packs)
        assert verdict.ready_for_calculator is True

    def test_vitrine_verdict(self, packs: dict) -> None:
        """Витрина: правило стикера по факту vitrine → OP-04 + макет остекления."""
        verdict = evaluate_text("Оформление витрины плёнкой, 12 м2", packs)
        # Продукт «оформление витрины» пака не имеет (пак — наклейка)…
        # но правило STICKER_WINDOW_VITRINE живёт в паке наклейки по факту
        # vitrine — оно сработает, как только продукт распознан как наклейка.
        draft = normalize_order("Наклейка для оформления витрины 200×100, 5 шт")
        verdict2 = evaluate_order(draft, packs)
        assert verdict2.matched_pack == "sticker"
        ops = [p.operation_token for p in verdict2.proposed_operations]
        assert "OP-04" in ops, "факт vitrine → печать wide (STICKER_WINDOW_VITRINE)"
        assert "STICKER_WINDOW_VITRINE" in verdict2.fired_rules


# --- 2. Missing: источники и дубли ---------------------------------------


class TestMissing:
    def test_sticker_contour_requires_layout_question(self, packs: dict) -> None:
        """require правила «макет с контуром» → unblocking missing с source."""
        verdict = evaluate_text("Наклейка 50×30, 149 шт + резка по контуру", packs)
        layout = [m for m in verdict.missing if m.field == "layout_with_cut_contour"]
        assert len(layout) == 1
        assert layout[0].blocking is False, "макет — производство, расчёт не блокирует"
        assert layout[0].source == "STICKER_CUT_CONTOUR_PLOTTER", "видно правило-источник"

    def test_no_duplicate_blocking_from_rules(self, packs: dict) -> None:
        """require: quantity правила не дублирует blocking из фактов."""
        verdict = evaluate_text("Наклейка 50×30, 149 шт + резка по контуру", packs)
        quantities = [m for m in verdict.missing if m.field == "quantity"]
        assert len(quantities) == 0, "qty указан — missing нет вовсе"
        verdict2 = evaluate_text("Наклейка 50×30 + резка по контуру", packs)  # без qty
        quantities2 = [m for m in verdict2.missing if m.field == "quantity"]
        assert len(quantities2) == 1, "один вопрос «Количество?», не два"

    def test_missingitem_rejects_unknown_field(self) -> None:
        with pytest.raises(ValueError, match="закрытого набора"):
            MissingItem(field="поле_вне_словаря", question="?", blocking=True)

    def test_operation_proposal_rejects_auto(self) -> None:
        with pytest.raises(ValueError, match="запрещён"):
            OperationProposal(operation_token="OP-22", label="x", reason="r", auto=True)


# --- 3. Матчинг when_facts: семантика отсутствия -------------------------


class TestFactMatching:
    def test_absent_fact_does_not_match_false(self, packs: dict) -> None:
        """«Не указано» ≠ «ложь»: usage отсутствует → правило улицы НЕ сработало."""
        verdict = evaluate_text("Наклейка 50×30, 149 шт", packs)
        assert "STICKER_OUTDOOR_EXTERIOR" not in verdict.fired_rules

    def test_outdoor_usage_fires(self, packs: dict) -> None:
        verdict = evaluate_text("Наклейка на улицу 200×100, 5 шт", packs)
        assert "STICKER_OUTDOOR_EXTERIOR" in verdict.fired_rules
        labels = [s.label for s in verdict.suggestions]
        assert any("УФ-стойкостью" in label for label in labels)

    def test_individual_vs_contour_distinct(self, packs: dict) -> None:
        """Поштучно и контур — разные правила (§4.1/§4.2), не пересечение."""
        individual = evaluate_text("Наклейка 20×30, 40 шт, порезать поштучно", packs)
        contour = evaluate_text("Наклейка 50×30, 149 шт + резка по контуру", packs)
        assert "STICKER_CUT_INDIVIDUAL_PLOTTER" in individual.fired_rules
        assert "STICKER_CUT_CONTOUR_PLOTTER" not in individual.fired_rules
        assert "STICKER_CUT_CONTOUR_PLOTTER" in contour.fired_rules
        assert "STICKER_CUT_INDIVIDUAL_PLOTTER" not in contour.fired_rules

    def test_product_level_rules_fire_without_facts(self, packs: dict) -> None:
        """Пустые when_facts: правила уровня продукта срабатывают всегда."""
        verdict = evaluate_text("Бэклит 80×60, 3 шт", packs)
        assert "BACKLIT_PRINT_LUMINOUS" in verdict.fired_rules
        assert "BACKLIT_ILLUMINATION_CLARIFY" in verdict.fired_rules


# --- 4. Продукт вне паков и пустой ввод ----------------------------------


class TestUnknownProduct:
    def test_unrecognized_product_gives_facts_only(self, packs: dict) -> None:
        """Продукт без пака: missing от фактов, предложений нет, не молчим."""
        draft = OrderDraft(text="табличка ПВХ 300×200, 2 шт")
        # продукт не распознан нормализатором (нет в labels) — черновик пуст
        verdict = evaluate_order(draft, packs)
        assert verdict.matched_pack == ""
        assert verdict.proposed_operations == () and verdict.suggestions == ()
        assert verdict.fired_rules == ()

    def test_size_and_qty_missing_for_plain_text(self, packs: dict) -> None:
        verdict = evaluate_text("", packs)
        blocking = sorted(m.field for m in verdict.missing if m.blocking)
        assert blocking == ["quantity", "size_mm"]
        assert verdict.ready_for_calculator is False

    def test_unknown_words_surface_in_verdict(self, packs: dict) -> None:
        verdict = evaluate_text("Наклейка 50×30 со снегозащитой, 5 шт", packs)
        assert any("снегозащит" in w for w in verdict.draft.unknown_words)


# --- 5. Идемпотентность (DoD §3) -----------------------------------------


class TestIdempotence:
    def test_repeated_evaluation_identical(self, packs: dict) -> None:
        text = "Бэклит 80×60, 1440 dpi, резка по контуру"
        first = evaluate_text(text, packs)
        second = evaluate_text(text, packs)
        assert first == second, "повторный прогон — байт-в-байт тот же вердикт"
        assert first.to_json() == second.to_json()

    def test_json_contract_shape(self, packs: dict) -> None:
        """Контракт S3 стабилен: ключи JSON вердикта."""
        payload = evaluate_text("Наклейка 50×30, 149 шт + резка по контуру", packs).to_json()
        expected_keys = {
            "product", "matched_pack", "size_mm", "quantity", "finishings",
            "facts", "unknown_words", "proposed_operations", "missing",
            "suggestions", "fired_rules", "ready_for_calculator",
        }
        assert set(payload) == expected_keys
        assert payload["proposed_operations"][0]["auto"] is False


# --- 6. OP-22 в сиде каталога (задача S0, закрыта в S2) -------------------


class TestOperationSeed:
    def test_op22_seeded_with_plotter_cut_trigger(self) -> None:
        from printcalc_web.store import DEFAULT_OPERATIONS

        op22 = next(op for op in DEFAULT_OPERATIONS if op["code"] == "OP-22")
        assert op22["name"] == "Плоттерная резка"
        assert op22["trigger"] == "work_plotter_cut", "флаг доп-работы wide"

    def test_op22_enters_plan_on_confirmed_flag(self, conn) -> None:
        """Подтверждённая сотрудником резка (work_plotter_cut) → задание OP-22."""
        from printcalc_web import store

        store.seed_operations(conn)
        order = store.create_order(
            conn,
            status="новый",
            payment_method="карта",
            items=[
                {
                    "kind": "calculator",
                    "calculator_id": "wide",
                    "params": {
                        "width": 50, "height": 30, "qty": 149,
                        "material": "Плёнка самоклеящаяся", "print": "Обычная печать",
                        "mount": "Без монтажа",
                        "work_plotter_cut": True,
                    },
                }
            ],
        )
        created = store.generate_production_plan(conn, order["id"])
        codes = [t["operation"]["code"] for t in created]
        assert "OP-22" in codes, "подтверждённый флаг → задание плоттерной резки"
