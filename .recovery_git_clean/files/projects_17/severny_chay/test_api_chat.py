"""Проверки для POST /api/chat с замоканным Gemini-клиентом.

Ключа GEMINI_API_KEY не требуется — реального обращения к Google AI не
происходит, вместо него подставляется фейковый клиент.
"""

import asyncio
import os
from unittest import mock

# Ключ нужен только чтобы main.py прошёл свою проверку при импорте.
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import main as m  # noqa: E402  (после настройки окружения)

from fastapi import HTTPException  # noqa: E402


# ---------------------------------------------------------------------------
# Вспомогательные средства
# ---------------------------------------------------------------------------

def _fake_client(reply_text: str = "Привет! Чем помочь?", error: Exception | None = None):
    """Возвращает замоканный genai.Client: generate_content -> reply или raise error."""
    client = mock.Mock()
    if error is not None:
        client.models.generate_content.side_effect = error
    else:
        response = mock.Mock()
        response.text = reply_text
        client.models.generate_content.return_value = response
    return client


def run_chat(**kwargs):
    """Вызывает async-хендлер chat() как обычную функцию через asyncio.run."""
    return asyncio.run(m.chat(m.ChatRequest(**kwargs)))


def last_call(client):
    """Возвращает kwargs последнего вызова generate_content."""
    return client.models.generate_content.call_args.kwargs


def last_contents(client):
    """Возвращает список Content, переданный модели в последнем вызове."""
    return last_call(client)["contents"***REMOVED***


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_sessions():
    """Переключает хранилище сессий на изолированную in-memory БД между тестами."""
    m._db_path = ":memory:"
    m._db_conn = None  # при первом обращении создаст чистую in-memory БД
    yield
    m._db_conn = None


@pytest.fixture
def fake_gemini(monkeypatch):
    """Подменяет m._client на фейк и возвращает этот фейк для проверок."""

    def _install(reply_text: str = "Привет! Чем помочь?", error: Exception | None = None):
        client = _fake_client(reply_text=reply_text, error=error)
        monkeypatch.setattr(m, "_client", client)
        return client

    return _install


# ---------------------------------------------------------------------------
# Базовый контракт эндпоинта
# ---------------------------------------------------------------------------

def test_returns_reply_and_creates_session(fake_gemini):
    client = fake_gemini(reply_text="Рекомендую Таёжный сбор")
    result = run_chat(message="Что посоветуете?")
    assert result.reply == "Рекомендую Таёжный сбор"
    assert len(result.session_id) == 32  # uuid4().hex


def test_sends_correct_model_and_system_prompt(fake_gemini):
    client = fake_gemini()
    run_chat(message="Привет")
    kwargs = last_call(client)
    assert kwargs["model"***REMOVED*** == "gemini-2.5-flash"
    # системный промпт передаётся через config.system_instruction
    config = kwargs["config"***REMOVED***
    assert "Северный чай" in config.system_instruction
    assert config.temperature == 0.7


def test_empty_message_rejected(fake_gemini):
    client = fake_gemini()
    try:
        run_chat(message="   ")
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("Ожидали HTTPException 400 для пустого сообщения")
    client.models.generate_content.assert_not_called()


# ---------------------------------------------------------------------------
# Сессии и история диалога
# ---------------------------------------------------------------------------

def test_reuses_session_and_remembers_history(fake_gemini):
    client = fake_gemini(reply_text="ответ")
    sid = "a" * 32

    run_chat(message="первое сообщение", session_id=sid)
    first = last_contents(client)
    assert len(first) == 1  # только текущий ход пользователя

    run_chat(message="второе сообщение", session_id=sid)
    second = last_contents(client)
    # история сессии + новый ход: user(model) -> user(new user)
    assert len(second) == 3
    assert second[0***REMOVED***.parts[0***REMOVED***.text == "первое сообщение"
    assert second[1***REMOVED***.role == "model"
    assert second[2***REMOVED***.parts[0***REMOVED***.text == "второе сообщение"


def test_returns_same_session_id(fake_gemini):
    fake_gemini()
    sid = "b" * 32
    r1 = run_chat(message="hi", session_id=sid)
    r2 = run_chat(message="hi", session_id=sid)
    assert r1.session_id == sid
    assert r2.session_id == sid


def test_sessions_are_isolated(fake_gemini):
    client = fake_gemini(reply_text="ok")
    run_chat(message="привет A", session_id="1" * 32)
    # новая сессия не видит историю первой
    run_chat(message="привет B", session_id="2" * 32)
    contents = last_contents(client)
    assert len(contents) == 1
    assert contents[0***REMOVED***.parts[0***REMOVED***.text == "привет B"


def test_history_is_capped_at_max():
    # прямо через внутренний хелпер: обрезка до MAX_HISTORY_MESSAGES
    sid = "c" * 32
    turns = m.MAX_HISTORY_MESSAGES + 5  # каждый ход = 2 реплики (user+model)
    for i in range(turns):
        m._append_turn(sid, f"u{i***REMOVED***", f"a{i***REMOVED***")
    history = m._get_session_history(sid)
    # в контексте остаётся ровно MAX_HISTORY_MESSAGES реплик = последние N/2 ходов
    assert len(history) == m.MAX_HISTORY_MESSAGES
    # первый сохранённый пользователь — тот, что попадает в хвост из N реплик
    kept_turns = m.MAX_HISTORY_MESSAGES // 2
    assert history[0***REMOVED***.parts[0***REMOVED***.text == f"u{turns - kept_turns***REMOVED***"


# ---------------------------------------------------------------------------
# Операционные ошибки
# ---------------------------------------------------------------------------

def test_gemini_failure_returns_502(fake_gemini):
    fake_gemini(error=RuntimeError("boom"))
    try:
        run_chat(message="hi")
    except HTTPException as exc:
        assert exc.status_code == 502
        assert "Gemini" in exc.detail
    else:
        raise AssertionError("Ожидали HTTPException 502 при сбое модели")


# ---------------------------------------------------------------------------
# Критический медицинский протокол
# ---------------------------------------------------------------------------

def test_medical_question_forces_fixed_phrase(fake_gemini):
    client = fake_gemini(reply_text="Я не даю медицинских рекомендаций, проконсультируйтесь с лечащим врачом")
    run_chat(message="Как этот чай совместим с моими лекарствами?")
    contents = last_contents(client)
    user_part = contents[-1***REMOVED***.parts[0***REMOVED***.text
    assert "Я не даю медицинских рекомендаций" in user_part


def test_normal_message_not_rewritten(fake_gemini):
    client = fake_gemini(reply_text="Таёжный сбор")
    run_chat(message="Расскажи про Таёжный сбор")
    contents = last_contents(client)
    user_part = contents[-1***REMOVED***.parts[0***REMOVED***.text
    assert "Таёжный сбор" in user_part
    assert "медицинских рекомендаций" not in user_part


# ---------------------------------------------------------------------------
# Вспомогательный юнит-тест guard-логики
# ---------------------------------------------------------------------------

def test_guard_detects_medical_vocabulary():
    assert "лечащим врачом" in m._guard_prompt("влияет ли на мою болезнь?")
    assert "лечащим врачом" in m._guard_prompt("совместим с препаратами?")
    assert "лечащим врачом" not in m._guard_prompt("расскажи про Детокс")


# ---------------------------------------------------------------------------
# Фронтенд (генерируемая HTML-страница) — передача session_id
# ---------------------------------------------------------------------------

def serve_html() -> str:
    """Возвращает HTML, который отдаёт GET /."""
    return asyncio.run(m.index()).body.decode("utf-8")


def test_frontend_sends_session_id_in_payload():
    """В JS-коде страницы session_id попадает в тело запроса к /api/chat."""
    html = serve_html()
    assert "fetch('/api/chat'" in html
    assert "payload.session_id = sessionId" in html
    # session_id шлётся только когда он уже есть (иначе сервер создаст новый)
    assert "if (sessionId) payload.session_id = sessionId" in html


def test_frontend_persists_session_id_in_localstorage():
    """session_id хранится в localStorage и переживает перезагрузку страницы."""
    html = serve_html()
    assert "localStorage.getItem(" in html
    assert "localStorage.setItem(" in html
    assert "severny_chay_session_id" in html


def test_frontend_uses_session_id_from_response():
    """Полученный из ответа session_id сохраняется для следующих запросов."""
    html = serve_html()
    assert "ensureSessionId(data.session_id)" in html


def test_frontend_order_button_calls_alert():
    """Постоянная кнопка «Заказать» вызывает alert('Переход в каталог')."""
    html = serve_html()
    assert "alert('Переход в каталог')" in html
    assert "Заказать" in html
