"""
AI-ассистент магазина «Северный чай».

Полный бэкенд (FastAPI + Uvicorn + Pydantic) и фронтенд (встроенный HTML/JS)
в одном файле. Модель Gemini (google-genai), ключ — из окружения GEMINI_API_KEY.

Запуск:
    GEMINI_API_KEY=... uvicorn main:app                      # дефолт 0.0.0.0:8000
    GEMINI_API_KEY=... python main.py                        # то же, но читает HOST/PORT
    HOST=127.0.0.1 PORT=9000 GEMINI_API_KEY=... python main.py

Переменные окружения:
    GEMINI_API_KEY — ключ Google AI (обязательно)
    HOST           — хост привязки, по умолчанию "0.0.0.0"
    PORT           — порт, по умолчанию 8000
"""

import asyncio
import os
import sqlite3
import threading
import time
import uuid
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Настройки модели
# ---------------------------------------------------------------------------

MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "Ты — AI-ассистент магазина «Северный чай». "
    "Ассортимент: 4 готовых комплекта и 1 конструктор. "
    "1: Таежный сбор. 2: Спокойный сон. 3: Витаминный заряд. 4: Детокс. "
    "5: Конструктор. Твоя задача — консультировать по составу и плавно "
    "подводить к кнопке Заказать. "
    "КРИТИЧЕСКИЙ ПРОТОКОЛ: Если пользователь задает вопросы о приеме лекарств, "
    "совместимости с медикаментами или влиянии на болезни, ты ОБЯЗАН ответить "
    "фиксированной фразой: «Я не даю медицинских рекомендаций, проконсультируйтесь "
    "с лечащим врачом». Самостоятельно безопасность не оценивать."
)


# ---------------------------------------------------------------------------
# Промпт-инъекция против отказа (защита медицинского протокола)
# ---------------------------------------------------------------------------
def _guard_prompt(user_message: str) -> str:
    """Усиливает критический протокол, если запрос явно касается медицины.

    ИИ-модели иногда «отменяют» инструкции прямой просьбой (prompt injection).
    Дополнительно продублируем протокол уже в самом пользовательском вводе,
    чтобы ответ был фиксированной фразой даже при попытке обойти правила.
    """
    lowered = user_message.lower()
    medical_hints = (
        "лекарств", "медикамент", "препарат", "совместим", "болезн",
        "заболеван", "диагноз", "принимаю", "таблетк", "влияет на болезн",
        "как повлияет", "противопоказан",
    )
    if any(hint in lowered for hint in medical_hints):
        return (
            "ВАЖНО: вопрос пользователя касается приёма лекарств / совместимости "
            "с медикаментами / влияния на болезни. Ответь строго фиксированной "
            "фразой: «Я не даю медицинских рекомендаций, проконсультируйтесь "
            "с лечащим врачом». Больше ничего не добавляй."
        )
    return user_message


# ---------------------------------------------------------------------------
# Инициализация клиента Gemini
# ---------------------------------------------------------------------------

if not os.environ.get("GEMINI_API_KEY"):
    raise RuntimeError(
        "Переменная окружения GEMINI_API_KEY не задана. "
        "Запустите: GEMINI_API_KEY=... uvicorn main:app --host 0.0.0.0 --port 8000"
    )

_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"***REMOVED***)


# ---------------------------------------------------------------------------
# Многопользовательские сессии (история диалога в SQLite)
# ---------------------------------------------------------------------------

# Максимум сообщений (реплик юзер+бот), удерживаемых в одной сессии — чтобы
# история не росла бесконечно и не выходила за лимит контекста модели.
MAX_HISTORY_MESSAGES = 20
# Время бездействия сессии (сек), после которого она удаляется при чистке.
SESSION_TTL_SECONDS = 60 * 60  # 1 час
# Путь к файлу БД (переопределяется через SEVERNY_CHAY_DB).
DB_PATH = os.environ.get("SEVERNY_CHAY_DB", "severny_chay.db")

# Одиночное подключение к SQLite, разделяемое между вызовами и защищённое
# мьютексом (check_same_thread=False, т.к. обращаемся из разных контекстов).
_db_path = DB_PATH
_db_conn: Optional[sqlite3.Connection***REMOVED*** = None
_db_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    last_seen   REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
"""


def _get_db() -> sqlite3.Connection:
    """Возвращает общее подключение, создавая его и схему при первом обращении."""
    global _db_conn
    if _db_conn is None:
        _db_conn = sqlite3.connect(_db_path, check_same_thread=False)
        _db_conn.executescript(_SCHEMA)
        _db_conn.commit()
    return _db_conn


def _new_session_id() -> str:
    """Генерирует новый идентификатор сессии."""
    return uuid.uuid4().hex


def _touch_session(conn: sqlite3.Connection, session_id: str) -> None:
    """Обновляет метку последнего обращения сессии."""
    conn.execute(
        "INSERT INTO sessions(session_id, last_seen) VALUES(?, ?) "
        "ON CONFLICT(session_id) DO UPDATE SET last_seen=excluded.last_seen",
        (session_id, time.time()),
    )


def _get_session_history(session_id: str) -> List[genai_types.Content***REMOVED***:
    """Возвращает историю сессии из БД (хвост последних реплик)."""
    conn = _get_db()
    with _db_lock:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id=? "
            "ORDER BY id DESC LIMIT ?",
            (session_id, MAX_HISTORY_MESSAGES),
        ).fetchall()
        rows.reverse()
        _touch_session(conn, session_id)
        conn.commit()
    return [
        genai_types.Content(role=role, parts=[genai_types.Part(text=content)***REMOVED***)
        for role, content in rows
    ***REMOVED***


def _append_turn(session_id: str, user_text: str, assistant_text: str) -> None:
    """Добавляет реплику user+model в историю сессии, обрезая старые."""
    conn = _get_db()
    with _db_lock:
        conn.execute(
            "INSERT INTO messages(session_id, role, content) VALUES(?, ?, ?)",
            (session_id, "user", user_text),
        )
        conn.execute(
            "INSERT INTO messages(session_id, role, content) VALUES(?, ?, ?)",
            (session_id, "model", assistant_text),
        )
        # держим хвост из последних MAX_HISTORY_MESSAGES реплик
        conn.execute(
            "DELETE FROM messages WHERE session_id=? AND id NOT IN "
            "(SELECT id FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?)",
            (session_id, session_id, MAX_HISTORY_MESSAGES),
        )
        _touch_session(conn, session_id)
        conn.commit()


def _cleanup_expired_sessions() -> None:
    """Удаляет из БД сессии и их сообщения, если те неактивны больше TTL."""
    conn = _get_db()
    cutoff = time.time() - SESSION_TTL_SECONDS
    with _db_lock:
        stale = conn.execute(
            "SELECT session_id FROM sessions WHERE last_seen < ?", (cutoff,)
        ).fetchall()
        ids = [row[0***REMOVED*** for row in stale***REMOVED***
        if ids:
            conn.executemany(
                "DELETE FROM messages WHERE session_id=?", [(i,) for i in ids***REMOVED***
            )
            conn.executemany(
                "DELETE FROM sessions WHERE session_id=?", [(i,) for i in ids***REMOVED***
            )
            conn.commit()
    # возвращаем удалённые для тестов
    return ids


# ---------------------------------------------------------------------------
# Схемы запроса/ответа (Pydantic)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str***REMOVED*** = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


# ---------------------------------------------------------------------------
# FastAPI приложение
# ---------------------------------------------------------------------------

app = FastAPI(title="Северный чай — AI-ассистент")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Принимает { "message": "текст", "session_id": "..." ***REMOVED*** и возвращает
    { "reply": "текст", "session_id": "..." ***REMOVED***.

    Если session_id не передан — создаётся новая сессия. Вся история диалога
    сессии отправляется модели, так что ассистент помнит предыдущие реплики.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")

    _cleanup_expired_sessions()

    # session_id: используют переданный (если валиден) либо создают новый
    session_id = req.session_id or _new_session_id()
    history = _get_session_history(session_id)

    user_text = _guard_prompt(req.message.strip())

    # История сессии + текущий ход пользователя
    contents: List[genai_types.Content***REMOVED*** = list(history)
    contents.append(
        genai_types.Content(role="user", parts=[genai_types.Part(text=user_text)***REMOVED***)
    )

    try:
        # sync SDK блокирует поток — выносим в отдельный поток, чтобы не
        # блокировать event loop
        response = await asyncio.to_thread(
            _client.models.generate_content,
            model=MODEL,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
            ),
        )
        reply = response.text or ""
        if not reply.strip():
            reply = "Извините, не удалось сформировать ответ. Попробуйте ещё раз."
    except Exception as exc:  # noqa: BLE001 — внешний API, ошибки разные
        raise HTTPException(
            status_code=502,
            detail=f"Ошибка обращения к модели Gemini: {exc***REMOVED***",
        ) from exc

    # Запоминаем пару user+model в истории сессии
    _append_turn(session_id, user_text, reply)

    return ChatResponse(reply=reply, session_id=session_id)


# ---------------------------------------------------------------------------
# Фронтенд — HTML-страница с плавающим виджетом чата
# ---------------------------------------------------------------------------

HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Северный чай — AI-ассистент</title>
  <style>
    :root {
      --accent: #2e7d32;
      --accent-dark: #1b5e20;
      --bot-bubble: #e8f5e9;
      --user-bubble: #c8e6c9;
      --bg: #f5f5f0;
      --radius: 16px;
    ***REMOVED***
    * { box-sizing: border-box; margin: 0; padding: 0; ***REMOVED***
    body {
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
      background: var(--bg);
      min-height: 100vh;
    ***REMOVED***

    /* ---------- Плавающая кнопка виджета ---------- */
    .fab {
      position: fixed;
      right: 18px;
      bottom: 18px;
      width: 62px;
      height: 62px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--accent), var(--accent-dark));
      color: #fff;
      border: none;
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      z-index: 999;
      transition: transform .15s ease, box-shadow .15s ease;
    ***REMOVED***
    .fab:active { transform: scale(0.94); ***REMOVED***
    .fab.hidden { display: none; ***REMOVED***

    /* ---------- Окно чата ---------- */
    .chat {
      position: fixed;
      right: 16px;
      bottom: 16px;
      width: 380px;
      max-width: calc(100vw - 32px);
      height: 560px;
      max-height: calc(100vh - 32px);
      background: #fff;
      border-radius: var(--radius);
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      z-index: 1000;
      transform: translateY(0);
      opacity: 1;
      transition: transform .2s ease, opacity .2s ease;
      font-size: 15px;
    ***REMOVED***
    .chat.closed {
      transform: translateY(30px);
      opacity: 0;
      pointer-events: none;
    ***REMOVED***

    .chat-header {
      background: linear-gradient(135deg, var(--accent), var(--accent-dark));
      color: #fff;
      padding: 14px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    ***REMOVED***
    .chat-header .title { font-weight: 700; font-size: 16px; ***REMOVED***
    .chat-header .subtitle { font-size: 12px; opacity: .9; margin-top: 2px; ***REMOVED***
    .chat-close {
      background: rgba(255, 255, 255, 0.2);
      border: none;
      color: #fff;
      width: 30px;
      height: 30px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 16px;
      line-height: 1;
    ***REMOVED***

    .messages {
      flex: 1;
      overflow-y: auto;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      -webkit-overflow-scrolling: touch;
    ***REMOVED***
    .msg {
      max-width: 82%;
      padding: 10px 13px;
      border-radius: var(--radius);
      line-height: 1.45;
      white-space: pre-wrap;
      word-wrap: break-word;
    ***REMOVED***
    .msg.bot {
      background: var(--bot-bubble);
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      color: #1b1b1b;
    ***REMOVED***
    .msg.user {
      background: var(--user-bubble);
      align-self: flex-end;
      border-bottom-right-radius: 4px;
      color: #1b1b1b;
    ***REMOVED***
    .msg.error { background: #ffebee; color: #b71c1c; align-self: flex-start; ***REMOVED***

    .typing {
      align-self: flex-start;
      background: var(--bot-bubble);
      padding: 12px 16px;
      border-radius: var(--radius);
      border-bottom-left-radius: 4px;
      display: inline-flex;
      gap: 5px;
    ***REMOVED***
    .typing span {
      width: 8px; height: 8px;
      border-radius: 50%;
      background: var(--accent);
      animation: blink 1.2s infinite;
    ***REMOVED***
    .typing span:nth-child(2) { animation-delay: .2s; ***REMOVED***
    .typing span:nth-child(3) { animation-delay: .4s; ***REMOVED***
    @keyframes blink { 0%, 80%, 100% { opacity: .3; ***REMOVED*** 40% { opacity: 1; ***REMOVED*** ***REMOVED***

    /* ---------- Постоянная кнопка «Заказать» ---------- */
    .order-bar {
      padding: 10px;
      border-top: 1px solid #ececec;
      background: #fafafa;
    ***REMOVED***
    .order-btn {
      width: 100%;
      padding: 12px;
      border: none;
      border-radius: 12px;
      background: linear-gradient(135deg, #f57c00, #e65100);
      color: #fff;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(245, 124, 0, 0.4);
    ***REMOVED***
    .order-btn:active { transform: scale(0.98); ***REMOVED***

    /* ---------- Поле ввода ---------- */
    .input-bar {
      display: flex;
      gap: 8px;
      padding: 10px;
      border-top: 1px solid #ececec;
      background: #fff;
    ***REMOVED***
    .input-bar input {
      flex: 1;
      padding: 11px 14px;
      border: 1px solid #ddd;
      border-radius: 22px;
      font-size: 15px;
      outline: none;
    ***REMOVED***
    .input-bar input:focus { border-color: var(--accent); ***REMOVED***
    .send-btn {
      border: none;
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: var(--accent);
      color: #fff;
      font-size: 18px;
      cursor: pointer;
      flex-shrink: 0;
    ***REMOVED***
    .send-btn:active { transform: scale(0.94); ***REMOVED***

    /* ---------- Адаптив: мобильные ---------- */
    @media (max-width: 480px) {
      .chat {
        right: 0;
        bottom: 0;
        width: 100vw;
        max-width: 100vw;
        height: 100dvh;
        max-height: 100dvh;
        border-radius: 0;
      ***REMOVED***
      .fab {
        right: 14px;
        bottom: 14px;
      ***REMOVED***
    ***REMOVED***
  </style>
</head>
<body>

  <!-- Плавающая кнопка -->
  <button id="fab" class="fab" aria-label="Открыть чат">💬</button>

  <!-- Окно чата -->
  <div id="chat" class="chat closed">
    <div class="chat-header">
      <div>
        <div class="title">Северный чай</div>
        <div class="subtitle">Задайте вопрос о составе наших чаёв</div>
      </div>
      <button id="chat-close" class="chat-close" aria-label="Закрыть">✕</button>
    </div>

    <div id="messages" class="messages">
      <div class="msg bot">Здравствуйте! 👋 Я ассистент магазина «Северный чай». Могу рассказать о составе наших комплектов: Таёжный сбор, Спокойный сон, Витаминный заряд, Детокс или Конструктор.</div>
    </div>

    <div class="order-bar">
      <button id="order-btn" class="order-btn">🛒 Заказать</button>
    </div>

    <div class="input-bar">
      <input id="input" type="text" placeholder="Введите сообщение…" autocomplete="off">
      <button id="send-btn" class="send-btn" aria-label="Отправить">➤</button>
    </div>
  </div>

  <script>
    const fab = document.getElementById('fab');
    const chat = document.getElementById('chat');
    const closeBtn = document.getElementById('chat-close');
    const messages = document.getElementById('messages');
    const input = document.getElementById('input');
    const sendBtn = document.getElementById('send-btn');
    const orderBtn = document.getElementById('order-btn');

    // Идентификатор сессии — хранится локально, чтобы диалог продолжался
    // между перезагрузками страницы.
    const SID_KEY = 'severny_chay_session_id';
    let sessionId = localStorage.getItem(SID_KEY) || '';
    function ensureSessionId(newId) {
      if (newId && newId !== sessionId) {
        sessionId = newId;
        localStorage.setItem(SID_KEY, newId);
      ***REMOVED***
    ***REMOVED***

    // Открыть / закрыть виджет
    fab.addEventListener('click', () => toggleChat(true));
    closeBtn.addEventListener('click', () => toggleChat(false));

    function toggleChat(open) {
      chat.classList.toggle('closed', !open);
      fab.classList.toggle('hidden', open);
      if (open) { input.focus(); scrollBottom(); ***REMOVED***
    ***REMOVED***

    // Постоянная кнопка «Заказать»
    orderBtn.addEventListener('click', () => {
      alert('Переход в каталог');
    ***REMOVED***);

    // Добавить сообщение в окно
    function addMsg(text, who) {
      const div = document.createElement('div');
      div.className = 'msg ' + who;
      div.textContent = text;
      messages.appendChild(div);
      scrollBottom();
    ***REMOVED***

    function showTyping() {
      const t = document.createElement('div');
      t.className = 'typing';
      t.id = 'typing';
      t.innerHTML = '<span></span><span></span><span></span>';
      messages.appendChild(t);
      scrollBottom();
    ***REMOVED***

    function removeTyping() {
      const t = document.getElementById('typing');
      if (t) t.remove();
    ***REMOVED***

    function scrollBottom() {
      messages.scrollTop = messages.scrollHeight;
    ***REMOVED***

    // Отправка сообщения на /api/chat (с идентификатором сессии)
    async function send() {
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      addMsg(text, 'user');

      const payload = { message: text ***REMOVED***;
      if (sessionId) payload.session_id = sessionId;

      showTyping();
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' ***REMOVED***,
          body: JSON.stringify(payload)
        ***REMOVED***);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Ошибка сервера');
        ensureSessionId(data.session_id);
        addMsg(data.reply, 'bot');
      ***REMOVED*** catch (err) {
        addMsg('Не удалось получить ответ: ' + err.message, 'error');
      ***REMOVED*** finally {
        removeTyping();
      ***REMOVED***
    ***REMOVED***

    sendBtn.addEventListener('click', send);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') send();
    ***REMOVED***);
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Возвращает HTML-страницу с плавающим виджетом чата."""
    return HTMLResponse(content=HTML_PAGE)


# ---------------------------------------------------------------------------
# Точка входа: python main.py (читает HOST и PORT из окружения)
# ---------------------------------------------------------------------------

def _default_host() -> str:
    return os.environ.get("HOST", "0.0.0.0")


def _default_port() -> int:
    raw = os.environ.get("PORT", "8000")
    try:
        port = int(raw)
    except ValueError:
        raise ValueError(f"PORT должен быть целым числом, получено: {raw!r***REMOVED***")
    if not (0 <= port <= 65535):
        raise ValueError(f"PORT вне допустимого диапазона 0-65535: {port***REMOVED***")
    return port


def main() -> None:
    """Запускает сервер. Хост/порт берутся из HOST и PORT (дефолт 0.0.0.0:8000)."""
    import uvicorn

    uvicorn.run(
        "main:app",
        host=_default_host(),
        port=_default_port(),
    )


if __name__ == "__main__":
    main()
