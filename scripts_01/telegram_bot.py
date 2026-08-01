"""Telegram bot frontend for Freebuff.

Routes incoming Telegram messages to a ContextManager session so the user can
interact with the project from Telegram.  To start the bot:

    TELEGRAM_BOT_TOKEN=xxx python scripts_01/telegram_bot.py

The bot stores every chat as a ContextManager session, supports a few slash
commands, and answers via the configured LLM through ModelGateway.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import uuid
***REMOVED***
from typing import Any

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from scripts_01.context_manager import ContextManager
from scripts_01.tgbot_base import BaseTGBot, load_dotenv

# Make project root importable
WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

try:
    from scripts_01.model_gateway import ModelGateway
except ImportError:
    ModelGateway = None  # type: ignore[misc, assignment***REMOVED***


load_dotenv(WORKSPACE / ".env")

# In production, restrict this to your own chat IDs.
ALLOWED_CHAT_IDS: set[int***REMOVED*** = set()
if os.environ.get("ALLOWED_CHAT_IDS"):
    ALLOWED_CHAT_IDS = {
        int(cid.strip())
        for cid in os.environ["ALLOWED_CHAT_IDS"***REMOVED***.split(",")
        if cid.strip()
    ***REMOVED***


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("freebuff.telegram_bot")


class TelegramFreebuffBot(BaseTGBot):
    """Simple Telegram frontend backed by ContextManager.

    Наследует общую Telegram-инфраструктуру (BaseTGBot): .env-загрузку,
    токен, ApplicationBuilder, polling-цикл и error handler (DEBT-007).
    """

    logger = logging.getLogger("freebuff.telegram_bot")

    def __init__(self, workspace: str | Path) -> None:
        super().__init__(workspace)
        self.cm = ContextManager(str(self.workspace))
        self._active_session: dict[int, str***REMOVED*** = {***REMOVED***
        self._model_gateway: Any | None = None
        self._load_active_sessions()

    @property
    def model_gateway(self) -> Any | None:
        """Lazy, cached ModelGateway instance."""
        if self._model_gateway is None and ModelGateway is not None:
            self._model_gateway = ModelGateway()
        return self._model_gateway

    def _session_id(self, chat_id: int) -> str:
        # Deterministic but stable mapping from chat to session.
        return f"telegram-{chat_id***REMOVED***"

    def _get_or_create_session(self, chat_id: int) -> str:
        if chat_id in self._active_session:
            return self._active_session[chat_id***REMOVED***
        session_id = self._session_id(chat_id)
        if self.cm.get_session(session_id) is None:
            self.cm.start_session(
                session_id=session_id,
                project="telegram_bot",
                topic=f"telegram chat {chat_id***REMOVED***",
            )
        self._active_session[chat_id***REMOVED*** = session_id
        return session_id

    def _record_message(self, chat_id: int, role: str, text: str) -> None:
        session_id = self._get_or_create_session(chat_id)
        self.cm.add_message(
            session_id=session_id,
            role=role,
            content=text,
            auto_checkpoint_interval=0,
        )

    def _persist_active_sessions(self) -> None:
        """Persist the active session mapping to a small JSON file."""
        path = self.workspace / "data_13" / "telegram_bot_sessions.json"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({str(k): v for k, v in self._active_session.items()***REMOVED***),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to persist active sessions")

    def _load_active_sessions(self) -> None:
        """Load the active session mapping from disk."""
        path = self.workspace / "data_13" / "telegram_bot_sessions.json"
        try:
            if not path.exists():
                return
            data = json.loads(path.read_text(encoding="utf-8"))
            self._active_session = {int(k): v for k, v in data.items()***REMOVED***
        except Exception:
            logger.exception("Failed to load active sessions")

    def _active_session_id(self, chat_id: int) -> str:
        """Return the currently active session ID for a chat, falling back to DB."""
        if chat_id in self._active_session:
            return self._active_session[chat_id***REMOVED***
        # Fallback to the deterministic legacy session ID.
        return self._session_id(chat_id)

    def _session_status_text(self, chat_id: int) -> str:
        session_id = self._active_session_id(chat_id)
        session = self.cm.get_session(session_id)
        if session is None:
            return "Сессия ещё не создана. Отправь любое сообщение."
        return (
            f"🆔 Session: `{session.session_id[:8***REMOVED******REMOVED***`\n"
            f"📁 Project: {session.project***REMOVED***\n"
            f"💬 Messages: {session.message_count***REMOVED***\n"
            f" Tokens (est): {session.token_estimate***REMOVED***\n"
            f" Updated: {session.updated_at[:19***REMOVED******REMOVED***"
        )

    def _agent_reply(self, chat_id: int, text: str) -> str:
        """Generate an LLM reply using the project ModelGateway (if available).

        Falls back to a helpful local response when no API keys/models are
        configured, so the bot is never completely silent.
        """
        session_id = self._get_or_create_session(chat_id)
        messages = self._build_messages(session_id, text)

        gw = self.model_gateway
        if gw is None:
            return self._fallback_reply()

        try:
            response = gw.generate(
                model=os.environ.get("TELEGRAM_BOT_MODEL", "deepseek-v4-flash"),
                messages=messages,
                fallback=os.environ.get("TELEGRAM_BOT_FALLBACK_MODEL"),
                temperature=float(os.environ.get("TELEGRAM_BOT_TEMPERATURE", "0.7")),
            )
            return str(response.content or "").strip() or self._fallback_reply()
        except Exception as exc:
            logger.exception("ModelGateway failed for chat %s", chat_id)
            return (
                "🤖 Buffy (Telegram mode)\n\n"
                f"⚠️ ModelGateway error: {exc***REMOVED***\n\n"
                "Check TELEGRAM_BOT_TOKEN / model env vars, or run local Ollama."
            )

    def _build_messages(self, session_id: str, text: str) -> list[dict[str, str***REMOVED******REMOVED***:
        """Build OpenAI-style message history for the current session."""
        messages: list[dict[str, str***REMOVED******REMOVED*** = [
            {
                "role": "system",
                "content": (
                    "You are Buffy, the strategic coding assistant for the Freebuff "
                    "AI Engineering Workspace. You are chatting with the user via Telegram. "
                    "Be concise, helpful, and action-oriented. If the user asks about code, "
                    "files, or architecture, reason step by step and offer concrete next steps."
                ),
            ***REMOVED***
        ***REMOVED***
        for msg in self.cm.get_messages(session_id, limit=20):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role not in ("user", "assistant", "system"):
                continue
            messages.append({"role": role, "content": content***REMOVED***)
        messages.append({"role": "user", "content": text***REMOVED***)
        return messages

    def _fallback_reply(self) -> str:
        return (
            " Buffy (Telegram mode)\n\n"
            "Я получил твоё сообщение и сохранил в сессию.\n"
            "ModelGateway недоступен (нет ключей или не установлены зависимости).\n\n"
            "Доступные команды:\n"
            "/status — статус сессии\n"
            "/new — начать новую сессию\n"
            "/session — ID текущей сессии"
        )


# ── Handlers ───────────────────────────────────────────────────

_bot = TelegramFreebuffBot(WORKSPACE)


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id  # type: ignore[union-attr***REMOVED***
    _bot._record_message(chat_id, "system", "/start")
    await update.effective_message.reply_text(  # type: ignore[union-attr***REMOVED***
        "🤖 Buffy Telegram bot запущен.\n\n"
        "Отправь текст — я сохраню его в проектной сессии.\n"
        "Команды: /status /new /session"
    )


async def _status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id  # type: ignore[union-attr***REMOVED***
    text = _bot._session_status_text(chat_id)
    await update.effective_message.reply_text(text)  # type: ignore[union-attr***REMOVED***


async def _new_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id  # type: ignore[union-attr***REMOVED***
    old_session_id = _bot._active_session.pop(chat_id, _bot._session_id(chat_id))
    try:
        _bot.cm.complete_session(old_session_id)
    except Exception:
        pass
    # Start a fresh session with a new unique ID.
    new_session_id = f"telegram-{chat_id***REMOVED***-{uuid.uuid4().hex[:8***REMOVED******REMOVED***"
    _bot.cm.start_session(
        session_id=new_session_id,
        project="telegram_bot",
        topic=f"telegram chat {chat_id***REMOVED***",
    )
    _bot._active_session[chat_id***REMOVED*** = new_session_id
    _bot._persist_active_sessions()
    await update.effective_message.reply_text(  # type: ignore[union-attr***REMOVED***
        "🆕 Новая сессия создана.\n" + _bot._session_status_text(chat_id)
    )


async def _session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id  # type: ignore[union-attr***REMOVED***
    session_id = _bot._active_session_id(chat_id)
    await update.effective_message.reply_text(  # type: ignore[union-attr***REMOVED***
        f"Текущая сессия: `{session_id***REMOVED***`"
    )


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_text = (update.message.text or "") if update.message else ""
    if chat_id is None:
        return
    if not user_text:
        if update.effective_message:
            await update.effective_message.reply_text(
                "Отправь текстовое сообщение, и я отвечу."
            )
        return

    try:
        await context.bot.send_chat_action(chat_id, action="typing")
    except Exception:
        pass

    _bot._record_message(chat_id, "user", user_text)
    reply = _bot._agent_reply(chat_id, user_text)
    _bot._record_message(chat_id, "assistant", reply)

    await update.effective_message.reply_text(reply)  # type: ignore[union-attr***REMOVED***


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Делегирует общему обработчику BaseTGBot (DEBT-007)."""
    await _bot.error_handler(update, context)


# ── Entry point ────────────────────────────────────────────────

def main() -> int:
    if not _bot.token:
        print(
            "❌ TELEGRAM_BOT_TOKEN не задан.\n"
            "Получи токен у @BotFather и запусти:\n"
            "    TELEGRAM_BOT_TOKEN=xxx python scripts_01/telegram_bot.py\n"
            "Или добавь TELEGRAM_BOT_TOKEN в .env файл."
        )
        return 1

    app = _bot.build_application()

    app.add_handler(CommandHandler("start", _start))
    app.add_handler(CommandHandler("status", _status))
    app.add_handler(CommandHandler("new", _new_session))
    app.add_handler(CommandHandler("session", _session))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))
    app.add_error_handler(_error_handler)

    logger.info("Starting Freebuff Telegram bot...")
    return _bot.run_polling(app)


if __name__ == "__main__":
    sys.exit(main())
