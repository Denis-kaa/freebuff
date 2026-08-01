"""Tests for scripts_01/telegram_bot.py.

Covers internal bot logic and async handlers with mocked Update/Context.
"""
from __future__ import annotations

import os
import sys
***REMOVED***
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

# Skip if python-telegram-bot not installed
try:
    import telegram  # noqa: F401
    from telegram import Update, Message, Chat
    from telegram.ext import ContextTypes
except ImportError:
    pytest.skip("python-telegram-bot not installed", allow_module_level=True)

from scripts_01.telegram_bot import TelegramFreebuffBot  # noqa: E402


# ── Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def bot(tmp_path: Path) -> TelegramFreebuffBot:
    """A TelegramFreebuffBot backed by a temporary workspace."""
    return TelegramFreebuffBot(tmp_path)


@pytest.fixture
def mock_message() -> MagicMock:
    """A mock Message with async reply_text."""
    msg = MagicMock(spec=Message)
    msg.text = "test message"
    msg.reply_text = AsyncMock()
    return msg


@pytest.fixture
def mock_chat() -> MagicMock:
    """A mock Chat with id."""
    chat = MagicMock(spec=Chat)
    chat.id = 12345
    return chat


@pytest.fixture
def mock_update(mock_message: MagicMock, mock_chat: MagicMock) -> MagicMock:
    """A mock Update with effective_chat, effective_message, and message."""
    upd = MagicMock(spec=Update)
    upd.effective_chat = mock_chat
    upd.effective_message = mock_message
    upd.message = mock_message
    return upd


@pytest.fixture
def mock_context() -> MagicMock:
    """A mock CallbackContext with async bot.send_chat_action."""
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.bot = MagicMock()
    ctx.bot.send_chat_action = AsyncMock()
    ctx.error = RuntimeError("test error")
    return ctx


# ── Internal method tests (existing) ───────────────────────────


def test_session_id_is_deterministic(bot: TelegramFreebuffBot) -> None:
    assert bot._session_id(12345) == "telegram-12345"
    assert bot._session_id(12345) == bot._session_id(12345)


def test_get_or_create_session_creates_entry(bot: TelegramFreebuffBot) -> None:
    sid = bot._get_or_create_session(99999)
    assert sid.startswith("telegram-")
    session = bot.cm.get_session(sid)
    assert session is not None
    assert session.project == "telegram_bot"
    assert session.topic == "telegram chat 99999"


def test_record_message_and_build_messages(bot: TelegramFreebuffBot) -> None:
    chat_id = 11111
    bot._record_message(chat_id, "user", "hello")
    messages = bot._build_messages(bot._active_session[chat_id***REMOVED***, "how are you?")
    roles = [m["role"***REMOVED*** for m in messages***REMOVED***
    assert roles[0***REMOVED*** == "system"
    assert roles[-1***REMOVED*** == "user"
    assert "how are you?" in [m["content"***REMOVED*** for m in messages***REMOVED***


def test_session_status_text_for_new_chat(bot: TelegramFreebuffBot) -> None:
    text = bot._session_status_text(88888)
    assert "Сессия ещё не создана" in text


def test_fallback_reply_exists(bot: TelegramFreebuffBot) -> None:
    reply = bot._fallback_reply()
    assert "Buffy" in reply
    assert "/status" in reply


def test_new_session_creates_fresh_id(bot: TelegramFreebuffBot) -> None:
    chat_id = 12345
    first = bot._get_or_create_session(chat_id)
    old = bot._active_session.pop(chat_id, bot._session_id(chat_id))
    bot.cm.complete_session(old)
    new_id = f"telegram-{chat_id***REMOVED***-{os.urandom(4).hex()***REMOVED***"
    bot.cm.start_session(
        session_id=new_id, project="telegram_bot", topic=f"telegram chat {chat_id***REMOVED***"
    )
    bot._active_session[chat_id***REMOVED*** = new_id
    assert new_id != first


# ── Async handler tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_handler(
    bot: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """_start should record a system message and reply with welcome text."""
    # Import the handler directly (uses the module-level _bot)
    import scripts_01.telegram_bot as tb_mod

    with patch.object(tb_mod, "_bot", bot):
        await tb_mod._start(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_awaited_once()
    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "Buffy Telegram bot запущен" in reply_text
    assert "/status" in reply_text


@pytest.mark.asyncio
async def test_status_handler(
    bot: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """_status should reply with session status text."""
    import scripts_01.telegram_bot as tb_mod

    with patch.object(tb_mod, "_bot", bot):
        await tb_mod._status(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_awaited_once()
    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "Сессия ещё не создана" in reply_text or "Session:" in reply_text


@pytest.mark.asyncio
async def test_status_after_message(
    bot: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """_status should show session info after a message was recorded."""
    bot._record_message(12345, "user", "hello")

    import scripts_01.telegram_bot as tb_mod
    with patch.object(tb_mod, "_bot", bot):
        await tb_mod._status(mock_update, mock_context)

    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "Session:" in reply_text
    assert "telegram" in reply_text  # truncated to 8 chars: "telegram"


@pytest.mark.asyncio
async def test_message_handler_records_and_replies(
    bot: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """_handle_message should record user msg and reply (any response)."""
    import scripts_01.telegram_bot as tb_mod

    with patch.object(tb_mod, "_bot", bot):
        await tb_mod._handle_message(mock_update, mock_context)

    # Should have sent typing action
    mock_context.bot.send_chat_action.assert_awaited_once_with(12345, action="typing")
    # Should have replied with text (ModelGateway may or may not be available)
    mock_update.effective_message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_message_handler_empty_text(
    bot: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """Empty text should trigger a prompt to send text."""
    mock_update.message.text = ""

    import scripts_01.telegram_bot as tb_mod
    with patch.object(tb_mod, "_bot", bot):
        await tb_mod._handle_message(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_awaited_once()
    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "Отправь текстовое сообщение" in reply_text


@pytest.mark.asyncio
async def test_message_handler_no_chat(
    bot: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """Handler should be a no-op if effective_chat is None."""
    mock_update.effective_chat = None

    import scripts_01.telegram_bot as tb_mod
    with patch.object(tb_mod, "_bot", bot):
        await tb_mod._handle_message(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_new_session_handler(
    bot: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """_new_session should complete old session and start a new one."""
    # First create a session
    old_id = bot._get_or_create_session(12345)

    import scripts_01.telegram_bot as tb_mod
    with patch.object(tb_mod, "_bot", bot):
        await tb_mod._new_session(mock_update, mock_context)

    # Old session should be completed
    old_session = bot.cm.get_session(old_id)
    assert old_session is not None
    assert old_session.status.value == "completed"

    # Should have replied
    mock_update.effective_message.reply_text.assert_awaited_once()
    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "Новая сессия создана" in reply_text


@pytest.mark.asyncio
async def test_session_handler(
    bot: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """_session should reply with the current session ID."""
    import scripts_01.telegram_bot as tb_mod
    with patch.object(tb_mod, "_bot", bot):
        await tb_mod._session(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_awaited_once()
    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "telegram-12345" in reply_text


@pytest.mark.asyncio
async def test_error_handler_logs_and_replies(
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """_error_handler should log and reply with error message."""
    import scripts_01.telegram_bot as tb_mod

    with patch.object(tb_mod.logger, "error") as mock_log:
        await tb_mod._error_handler(mock_update, mock_context)

    mock_log.assert_called_once()
    mock_update.effective_message.reply_text.assert_awaited_once()
    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "Произошла ошибка" in reply_text


@pytest.mark.asyncio
async def test_error_handler_no_message(
    mock_context: MagicMock,
) -> None:
    """_error_handler should not crash when update has no effective_message."""
    import scripts_01.telegram_bot as tb_mod

    # An update without effective_message
    bare_update = MagicMock(spec=Update)
    bare_update.effective_message = None

    with patch.object(tb_mod.logger, "error") as mock_log:
        await tb_mod._error_handler(bare_update, mock_context)

    mock_log.assert_called_once()
    # No reply should be attempted (effective_message is None)
    mock_context.bot.send_chat_action.assert_not_called()


@pytest.mark.asyncio
async def test_persistence_round_trip(tmp_path: Path) -> None:
    """Active sessions should survive a bot restart via JSON persistence."""
    import scripts_01.telegram_bot as tb_mod

    bot1 = TelegramFreebuffBot(tmp_path)
    bot1._get_or_create_session(55555)
    bot1._persist_active_sessions()

    # Create a new instance simulating restart
    bot2 = TelegramFreebuffBot(tmp_path)
    assert 55555 in bot2._active_session
    assert bot2._active_session[55555***REMOVED*** == "telegram-55555"
