"""A7: интеграционные тесты 7 реальных фраз ТЗ §37 (Assistant v2.0).

Каждая фраза прогоняется через ЖИВОЙ endpoint POST /api/order/analyze
(ASGI-клиент, как реальный чат-интерфейс). Проверяются по ТЗ §37:
intent (product/matched_pack), dimensions (size_mm), quantity, material
(material_hint), thickness (thickness_mm), print quality (dpi),
operations (OP-*), grommet step, cutting mode, context inheritance,
missing questions, отсутствие ложного ЧПУ, decimal comma, отсутствие
выдуманной цены и выдуманного тиража.

Контракт: канонический пайплайн (parser v2 → normalize → packs), никаких
тест-фикстур параллельного мира (как в test_rules_engine.py).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from printcalc_web import create_app

from asgi_client import ASGITestClient

#: Эталонные фразы ТЗ §37 (7 штук, дословно).
P1_STICKER_CONTOUR = "Наклейка 50 на 30 149 шт плюс резка по контуру"
P2_BANNER_GROMMETS = "Баннер 3 на 6 люверсы через 30"
P3_BACKLIT_DPI = "Бэклит 80 на 60 качество 1440 dpi резка по контуру"
P4_STICKER_MOUNTING = "Наклейка плоттерная 20 на 30 с монтажной 40 шт порезать поштучно"
P5_PVC_PLATE = "Табличка ПВХ 4 мм 80 на 35"
P6_PHOTO_PASSPORT = "Фото на паспорт 6 штук"
P7_MULTI = "Фото на паспорт, табличка пластиковая 0,5 на 0,5, баннер 2 на 2 и 3 на 12"

ALL_SEVEN: tuple[str, ...] = (
    P1_STICKER_CONTOUR,
    P2_BANNER_GROMMETS,
    P3_BACKLIT_DPI,
    P4_STICKER_MOUNTING,
    P5_PVC_PLATE,
    P6_PHOTO_PASSPORT,
    P7_MULTI,
)


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[ASGITestClient]:
    yield ASGITestClient(create_app(db_path=tmp_path / "assistant.db"))


def _analyze(client: ASGITestClient, text: str) -> dict:
    return client.post("/api/order/analyze", json={"text": text}).json()


# --- 1. Наклейка 50 на 30 149 шт плюс резка по контуру ----------------------


def test_p1_sticker_contour(client: ASGITestClient) -> None:
    """§37.1: sticker + OP-22 + qty 149 + 500×300мм; НЕТ ложного ЧПУ."""
    v = _analyze(client, P1_STICKER_CONTOUR)
    assert v["product"] == "наклейка"
    assert v["matched_pack"] == "sticker"
    assert v["size_mm"] == [500.0, 300.0]
    assert v["quantity"] == 149
    assert v["facts"]["cutting_mode"] == "contour"
    ops = [o["operation_token"] for o in v["proposed_operations"]]
    assert ops == ["OP-22"], "резка по контуру — плоттер, НЕ ЧПУ (ложный ЧПУ запрещён)"
    assert v["ready_for_calculator"] is True
    assert v["unknown_words"] == []


# --- 2. Баннер 3 на 6 люверсы через 30 --------------------------------------


def test_p2_banner_grommets(client: ASGITestClient) -> None:
    """§37.2: banner 3000×6000 + OP-13 + шаг люверсов 30 см; qty блокирует."""
    v = _analyze(client, P2_BANNER_GROMMETS)
    assert v["matched_pack"] == "banner"
    assert v["size_mm"] == [3000.0, 6000.0]
    assert v["facts"]["grommets"] is True
    assert v["facts"]["grommets_step_cm"] == 30
    assert "OP-13" in [o["operation_token"] for o in v["proposed_operations"]]
    blocking = [m["field"] for m in v["missing"] if m["blocking"]]
    assert "quantity" in blocking
    assert v["ready_for_calculator"] is False


# --- 3. Бэклит 80 на 60 качество 1440 dpi резка по контуру ------------------


def test_p3_backlit_dpi(client: ASGITestClient) -> None:
    """§37.3: backlit + dpi=1440 (качество) + contour; qty НЕ выдуман (нет 1440)."""
    v = _analyze(client, P3_BACKLIT_DPI)
    assert v["matched_pack"] == "backlit"
    assert v["size_mm"] == [800.0, 600.0]
    assert v["facts"]["dpi"] == 1440, "«качество 1440 dpi» → факт print quality"
    assert v["facts"]["cutting_mode"] == "contour"
    assert v["quantity"] is None, "1440 dpi — НЕ тираж (без выдуманных значений)"
    blocking = [m["field"] for m in v["missing"] if m["blocking"]]
    assert "quantity" in blocking


# --- 4. Наклейка плоттерная 20 на 30 с монтажной 40 шт порезать поштучно ----


def test_p4_sticker_mounting_individual(client: ASGITestClient) -> None:
    """§37.4: sticker + накатка OP-15 + cutting_mode=individual + qty 40."""
    v = _analyze(client, P4_STICKER_MOUNTING)
    assert v["matched_pack"] == "sticker"
    assert v["size_mm"] == [200.0, 300.0]
    assert v["quantity"] == 40
    assert v["facts"]["cutting_mode"] == "individual", "«порезать поштучно»"
    assert v["facts"]["mounting_film"] is True, "«с монтажной» → факт накатки"
    ops = [o["operation_token"] for o in v["proposed_operations"]]
    assert "OP-22" in ops and "OP-15" in ops
    assert v["ready_for_calculator"] is True


# --- 5. Табличка ПВХ 4 мм 80 на 35 -------------------------------------------


def test_p5_pvc_plate_thickness_not_qty(client: ASGITestClient) -> None:
    """§37.5: thickness_mm=4, material_hint=пвх; «4 мм» — НЕ тираж 4.

    Продукт «табличка» вне паков → вердикт без правил (pack=""), но факты
    извлечены честно; qty остаётся блокирующим вопросом, а не выдуманной 4.
    """
    v = _analyze(client, P5_PVC_PLATE)
    assert v["product"] == "табличка"
    assert v["matched_pack"] == ""
    assert v["size_mm"] == [800.0, 350.0]
    assert v["facts"]["thickness_mm"] == 4.0
    assert v["facts"]["material_hint"] == "пвх"
    assert v["quantity"] is None, "«4 мм» — толщина, а НЕ тираж (без выдуманных значений)"
    blocking = [m["field"] for m in v["missing"] if m["blocking"]]
    assert "quantity" in blocking


# --- 6. Фото на паспорт 6 штук ------------------------------------------------


def test_p6_photo_passport_package_warning(client: ASGITestClient) -> None:
    """§37.6: фото-пакетная политика: 6 шт → warning про пакет 4; без цены."""
    v = _analyze(client, P6_PHOTO_PASSPORT)
    assert v["product"] == "фото на документы"
    assert v["quantity"] == 6
    assert v["warnings"], "qty вне пакетов (6 ≠ 4) → политика пакетов предупреждает"
    assert any("4" in w for w in v["warnings"])
    assert v["proposed_operations"] == [], "продукт вне паков — предложений нет (не выдумываем)"
    assert v["ready_for_calculator"] is False, "нет размера — вход калькулятора неполон"


# --- 7. Мульти-фраза: контекст и десятичная запятая ---------------------------


def test_p7_multi_decimal_comma_and_extra_sizes(client: ASGITestClient) -> None:
    """§37.7: decimal comma («0,5 на 0,5» = 500×500мм), extra_sizes, наследование.

    Мульти-заказ: первая пара — основной размер; последующие («2 на 2»,
    «3 на 12») — extra_sizes. Плюс материал «пластиковая» → пвх-подсказка.
    """
    v = _analyze(client, P7_MULTI)
    assert v["product"] == "баннер", "последний intent в мульти-фразе"
    assert v["size_mm"] == [500.0, 500.0], "«0,5 на 0,5» м — decimal comma распознана"
    assert v["facts"]["material_hint"] == "пвх", "«пластиковая» → подсказка материала"
    assert "2000x2000" in v["facts"]["extra_sizes"], "«2 на 2» м — наследует баннер"
    assert v["quantity"] is None
    assert v["unknown_words"] == []


# --- Сквозные гарантии на все 7 фраз (ТЗ §37, чек-лист) ----------------------


@pytest.mark.parametrize("text", ALL_SEVEN)
def test_no_invented_price_anywhere(client: ASGITestClient, text: str) -> None:
    """§37: отсутствие выдуманной цены — вердикт цены вообще не содержит."""
    payload = _analyze(client, text)
    assert "price" not in payload
    assert "total" not in payload


@pytest.mark.parametrize("text", ALL_SEVEN)
def test_verdict_contract_complete(client: ASGITestClient, text: str) -> None:
    """§37: каждый вердикт несёт полный стабильный контракт S3 (+warnings)."""
    payload = _analyze(client, text)
    for key in (
        "product", "matched_pack", "size_mm", "quantity", "finishings",
        "facts", "unknown_words", "proposed_operations", "missing",
        "suggestions", "fired_rules", "ready_for_calculator", "warnings",
    ):
        assert key in payload, f"{text!r}: нет ключа {key}"
