"""Тесты ассистентских intents (ASST-INTENTS) — TOP-20 MVP исследования."""

from __future__ import annotations

import pytest

from printcalc.assistant import (
    INTENT_IDS_TOP20,
    MvpPriority,
    SYNONYM_TABLE,
    UNMAPPED_RESEARCH_INTENTS,
    build_default_registry,
    clarification_for,
    intent_sources,
    match_intent,
    match_synonym,
    missing_required,
    warnings_for,
)
from printcalc.engine.errors import RegistryError


@pytest.fixture()
def registry():
    return build_default_registry()


# --- реестр ---------------------------------------------------------------


def test_registry_has_top20(registry) -> None:
    assert len(registry.ids()) == 20
    assert set(registry.ids()) == set(INTENT_IDS_TOP20)


def test_duplicate_intent_rejected() -> None:
    registry = build_default_registry()
    duplicate = next(
        s
        for s in (
            # берём любую спеку и пытаемся зарегистрировать повторно
            registry.get("photo_print"),
        )
    )
    with pytest.raises(RegistryError) as exc:
        registry.register(duplicate)
    assert "уже зарегистрирован" in str(exc.value)


def test_unknown_intent_rejected(registry) -> None:
    with pytest.raises(RegistryError) as exc:
        registry.get("nope")
    assert "неизвестный intent" in str(exc.value)


def test_ids_sorted(registry) -> None:
    assert registry.ids() == tuple(sorted(registry.ids()))


# --- содержимое TOP-20 (соответствие research/) ---------------------------


def test_p0_set_matches_mvp_research(registry) -> None:
    expected_p0 = {
        "photo_print",
        "copy_bw",
        "print_document",
        "scan",
        "laminate",
        "document_photo",
        "document_photo_from_file",
        "photo_print_mobile",
        "passport_photo_bring_file_advice",
    }
    assert set(registry.by_priority(MvpPriority.P0)) == expected_p0


def test_phrases_verified_flag_consistent(registry) -> None:
    for intent_id in registry.ids():
        spec = registry.get(intent_id)
        assert spec.phrases_verified == (len(spec.phrases) > 0)


def test_every_intent_has_clarification(registry) -> None:
    for intent_id in registry.ids():
        assert registry.get(intent_id).clarification.strip()


def test_document_photo_vs_from_file_are_distinct(registry) -> None:
    dp = registry.get("document_photo")
    dpff = registry.get("document_photo_from_file")
    assert dp.id != dpff.id
    assert "не угад" not in dp.clarification
    assert dp.never_infer and dpff.required_params


def test_banner_never_infer_material_and_eyelets(registry) -> None:
    spec = registry.get("banner")
    assert "материал" in spec.never_infer
    assert "люверсы" in spec.never_infer


def test_sign_pvc_never_infer_material(registry) -> None:
    spec = registry.get("sign_pvc")
    assert any("материал" in n for n in spec.never_infer)


# --- связка с CalculatorRegistry -----------------------------------------


def test_calculator_ids_do_not_conflict_with_engine_registry(registry) -> None:
    """Существующие calculator_id движка: riso, wide, tablichki (Phase 2)."""
    engine_known = {"riso", "wide", "tablichki"}
    linked = {s.calculator_id for s in (registry.get(i) for i in registry.ids()) if s.calculator_id}
    assert linked.isdisjoint(engine_known) or linked  # сейчас все None; тест закрепляет контракт
    assert linked == set()


# --- мини-хелперы диалога -------------------------------------------------


def test_match_intent_exact_real_phrase(registry) -> None:
    text = "подскажите, хочу распечатать фотографии на 10×15, сколько будет стоить"
    assert match_intent(registry, text) == "photo_print"


def test_match_intent_passport_phrase(registry) -> None:
    assert match_intent(registry, "нужно фото на документы паспорт визу 3х4") == "document_photo"


def test_match_intent_no_match(registry) -> None:
    assert match_intent(registry, "здравствуйте") is None
    assert match_intent(registry, "") is None


def test_clarification_for(registry) -> None:
    assert "какой документ" in clarification_for(registry, "document_photo").lower()


def test_missing_required(registry) -> None:
    assert missing_required(registry, "photo_print", set()) == ("size", "quantity", "files")
    assert missing_required(registry, "photo_print", {"size", "quantity", "files"}) == ()
    assert missing_required(registry, "banner", {"size_m2"}) == ("material",)


# --- линковка корпуса research/04 (CR-ссылки) -----------------------------


def test_intent_sources_covers_corpus_linked_intents(registry) -> None:
    """Каждый intent с фразами имеет CR-ссылки (трассируемость в research/04)."""
    sources = intent_sources(registry)
    assert set(sources) == set(registry.ids())
    for intent_id in registry.ids():
        spec = registry.get(intent_id)
        if spec.phrases_verified:
            assert spec.source_cr, f"{intent_id}: фразы есть, CR-ссылок нет"
        else:
            assert not spec.source_cr, f"{intent_id}: фраз нет, а CR-ссылки есть"


def test_every_source_cr_is_valid_format(registry) -> None:
    """CR-ссылки имеют формат CR-NN и лежат в диапазоне корпуса (01…111)."""
    for intent_id in registry.ids():
        for cr in registry.get(intent_id).source_cr:
            assert cr.startswith("CR-"), f"{intent_id}: {cr}"
            n = int(cr[3:])
            assert 1 <= n <= 111, f"{intent_id}: {cr} вне корпуса"
            assert n not in (17, 18, 19), f"{intent_id}: {cr} — неиспользуемый номер"


def test_corpus_linkage_stats(registry) -> None:
    """18 из 20 intents имеют верифицированные фразы (линковка корпуса)."""
    linked = [i for i in registry.ids() if registry.get(i).phrases_verified]
    assert len(linked) == 18
    unlinked = [i for i in registry.ids() if not registry.get(i).phrases_verified]
    assert set(unlinked) == {"business_cards_design", "sign_pvc"}


# --- knowledge-предупреждения (research/09 + CR-корпус) --------------------


def test_warnings_for_laminate_surfaces_zags_rule(registry) -> None:
    """CR-109/CR-110: ассистент обязан предупредить про документы ЗАГСа."""
    warnings = warnings_for(registry, "laminate")
    assert any("ЗАГС" in w for w in warnings)
    assert any("отказать" in w for w in warnings)


def test_warnings_for_intents_without_knowledge(registry) -> None:
    """Intents без знаний возвращают пустой кортеж — это валидно."""
    assert warnings_for(registry, "scan") == ()
    assert warnings_for(registry, "photo_multi_format_order") == ()


def test_warnings_match_intent_nonconflict(registry) -> None:
    """warnings_for не мешает матчингу; короткие фразы идут через синоним-слой."""
    assert match_intent(registry, "хочу распечатать фотографии на 10×15") == "photo_print"
    # «сканирование нужно» — через match_synonym (match_intent матчит целые фразы).
    assert match_synonym("сканирование нужно").intent_id == "scan"


# --- синоним-слой (research/08_synonyms.md) --------------------------------


def test_synonym_table_targets_exist_in_top20(registry) -> None:
    """CLOSE VOCABULARY: каждый токен ведёт на intent из TOP-20 (ANTI-6b)."""
    for entry in SYNONYM_TABLE:
        assert entry.intent_id in registry, (
            f"токен '{entry.token}' ведёт на неизвестный intent '{entry.intent_id}'"
        )


def test_synonym_table_no_duplicate_tokens() -> None:
    """Один токен — один intent: неоднозначность решается до таблицы."""
    tokens = [e.token for e in SYNONYM_TABLE]
    assert len(tokens) == len(set(tokens))


def test_synonym_confidence_levels_valid() -> None:
    """Уверенности только A/B/C — как в 08_synonyms.md."""
    assert all(e.confidence in {"A", "B", "C"} for e in SYNONYM_TABLE)


def test_match_synonym_everyday_phrases() -> None:
    """Бытовые формулировки из 08 попадают в правильные intents."""
    assert match_synonym("нужно распечатать фотки с телефона") is not None
    # «с телефона» длиннее/специфичнее — побеждает mobile-подвид.
    assert match_synonym("нужно распечатать фотки с телефона").intent_id == "photo_print_mobile"
    assert match_synonym("где сделать ксерокс") .intent_id == "copy_bw"
    assert match_synonym("надо заламинировать свидетельство").intent_id == "laminate"
    assert match_synonym("банер 3 на 6 сколько стоит").intent_id == "banner"  # опечатка
    assert match_synonym("фотка на паспорт").intent_id == "document_photo"
    assert match_synonym("переплет диплом пружина").intent_id == "bind"
    assert match_synonym("визиточка 100 штук").intent_id == "business_cards"


def test_match_synonym_does_not_merge_distinct_services() -> None:
    """§21: разные услуги не сливаются (copy ≠ print_document и т.п.)."""
    assert match_synonym("ксерокопия паспорта").intent_id == "copy_bw"
    assert match_synonym("распечатать реферат").intent_id == "print_document"
    assert match_synonym("табличка на дверь").intent_id == "sign_pvc"
    assert match_synonym("адресная табличка").intent_id == "address_plate"


def test_match_synonym_longest_token_wins() -> None:
    """«печать фотографий до а1» специфичнее общего «печать фотографий»."""
    m = match_synonym("нужна печать фотографий до а1 для выставки")
    assert m is not None and m.intent_id == "photo_print_large"


def test_match_synonym_no_match_returns_none() -> None:
    assert match_synonym("") is None
    assert match_synonym("здравствуйте, подскажите") is None


def test_unmapped_research_intents_accounted(registry) -> None:
    """Intent'ы исследования вне TOP-20 честно перечислены (не потеряны)."""
    assert "flyers" in UNMAPPED_RESEARCH_INTENTS
    assert "stamp" in UNMAPPED_RESEARCH_INTENTS
    assert "photo_restore" in UNMAPPED_RESEARCH_INTENTS
    for intent_id in UNMAPPED_RESEARCH_INTENTS:
        assert intent_id not in registry
