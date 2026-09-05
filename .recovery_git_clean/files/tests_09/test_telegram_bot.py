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

from scripts_01.telegram_bot import (  # noqa: E402
    TelegramFreebuffBot,
    _reap_subprocess_safe,
    _pending_reapers,
    cmd_task,
)

import scripts_01.telegram_bot as tg_module  # noqa: E402  # Phase 4 forensics fix: alias for tg_module references in dual-path tests


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
    """_start should record a system message and trigger onboarding welcome.

    Update from Phase 5.4: /start теперь стартует workspace-aware onboarding
    (greeting + ASKING_PROJECT prompt), не просто перечисляет /status и т.п.
    """
    # Import the handler directly (uses the module-level _bot)
    import scripts_01.telegram_bot as tb_mod

    with patch.object(tb_mod, "_bot", bot):
        await tb_mod._start(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_awaited_once()
    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "Привет" in reply_text
    assert "У тебя уже есть" in reply_text
    assert "/cancel" in reply_text


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

    # v5.189.10 speedup: _agent_reply вызывает ModelGateway.generate БЕЗ таймаута
    # (реальная LLM-попытка: 3s в изоляции, до 20s под нагрузкой сьюита).
    # Мок сохраняет контракт теста — reply_text вызывается ровно один раз.
    with patch.object(tb_mod, "_bot", bot), patch.object(
        bot, "_agent_reply", return_value="Mock Buffy reply (LLM mocked)",
    ):
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


# ── Onboarding state machine tests (Phase 5.4, closes OQ26-Q31) ────────────


@pytest.fixture
def bot_with_corpus(tmp_path: Path) -> TelegramFreebuffBot:
    """A TelegramFreebuffBot with a synthetic pompts_11/ corpus (3 files)."""
    corpus_dir = tmp_path / "pompts_11"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    # Three minimal markdown files; mtime order matters (older first → after write
    # they'll be the only candidates, top-N by mtime desc returns them by OS order).
    (corpus_dir / "001_07_legacy_thing.md").write_text(
        "# Legacy thing\n\nOldest project, kept for archive.", encoding="utf-8"
    )
    (corpus_dir / "047_06_e2e_platform_test.md").write_text(
        "# E2E Platform Test\n\nEnd-to-end platform test for promt 47 TG round-trip.",
        encoding="utf-8",
    )
    (corpus_dir / "048_07_prompt_conveyor.md").write_text(
        "# Prompt Conveyor\n\nPhase 5.4 onboarding wired through prompt queue.",
        encoding="utf-8",
    )
    return TelegramFreebuffBot(tmp_path)


@pytest.mark.asyncio
async def test_start_suggests_existing_projects(
    bot_with_corpus: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """`/start` should put chat into ASKING_PROJECT state + show prompt."""
    import scripts_01.telegram_bot as tb_mod
    from scripts_01._workspace_onboarding import STATE_ASKING_PROJECT

    with patch.object(tb_mod, "_bot", bot_with_corpus):
        await tb_mod._start(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_awaited_once()
    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "Привет" in reply_text
    assert "У тебя уже есть" in reply_text
    assert "/cancel" in reply_text
    # State should be persisted as ASKING_PROJECT
    state = bot_with_corpus.onboarding_state(12345)
    assert state.state == STATE_ASKING_PROJECT
    assert state.candidates == [***REMOVED***  # not yet populated


@pytest.mark.asyncio
async def test_onboarding_existing_project_path_uses_pompts_11(
    bot_with_corpus: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """«да» → ASKING_PICK_PROJECT + numbered pick list from pompts_11/ corpus."""
    import scripts_01.telegram_bot as tb_mod
    from scripts_01._workspace_onboarding import (
        STATE_ASKING_PROJECT,
        STATE_ASKING_PICK_PROJECT,
    )

    # Transition into ASKING_PROJECT, then send «да»
    state = bot_with_corpus.onboarding_state(12345)
    state.state = STATE_ASKING_PROJECT
    bot_with_corpus.save_onboarding(12345, state)

    mock_update.message.text = "да"
    with patch.object(tb_mod, "_bot", bot_with_corpus):
        await tb_mod._handle_message(mock_update, mock_context)

    # Should NOT have called agent_reply (state != NONE/DONE)
    updated = bot_with_corpus.onboarding_state(12345)
    assert updated.state == STATE_ASKING_PICK_PROJECT
    assert len(updated.candidates) >= 3
    # Reply should include a numbered pick list or some pompts_11 marker.
    mock_update.effective_message.reply_text.assert_awaited_once()
    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert _pompts_11_marker_present(reply_text)


# Module-level helper: loose check that reply mentions at least one corpus marker.
# Defined before consumers per good-housekeeping convention.
_POMPT_11_MARKERS = (
    "E2E Platform Test",
    "Prompt Conveyor",
    "Legacy thing",
    "001_07",
    "047_06",
    "048_07",
    "1.",  # numbered list head
)


def _pompts_11_marker_present(reply_text: str) -> bool:
    return any(marker in reply_text for marker in _POMPT_11_MARKERS)


@pytest.mark.asyncio
async def test_onboarding_idea_path_creates_workspace(
    bot_with_corpus: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """«нет» → idea text → workspace name → DONE + workspace registered."""
    import scripts_01.telegram_bot as tb_mod
    from scripts_01._workspace_onboarding import (
        STATE_ASKING_IDEA,
        STATE_ASKING_WORKSPACE_NAME,
        STATE_DONE,
    )

    # Step 1: ASKING_PROJECT → «нет»
    state = bot_with_corpus.onboarding_state(12345)
    state.state = STATE_ASKING_IDEA  # start here for tighter test
    bot_with_corpus.save_onboarding(12345, state)

    # Send idea text (1-200 chars)
    mock_update.message.text = "приложение для заметок по проектам"
    with patch.object(tb_mod, "_bot", bot_with_corpus):
        await tb_mod._handle_message(mock_update, mock_context)

    state = bot_with_corpus.onboarding_state(12345)
    assert state.state == STATE_ASKING_WORKSPACE_NAME
    assert state.source.startswith("idea:")

    # Step 2: send workspace name → DONE
    mock_update.message.text = "Работа"
    with patch.object(tb_mod, "_bot", bot_with_corpus):
        await tb_mod._handle_message(mock_update, mock_context)

    state = bot_with_corpus.onboarding_state(12345)
    assert state.state == STATE_DONE
    # Workspace should be registered
    from scripts_01._workspace_onboarding import list_workspaces_for_chat

    workspaces = list_workspaces_for_chat(bot_with_corpus.workspace, 12345)
    assert len(workspaces) == 1
    assert workspaces[0***REMOVED***["name"***REMOVED*** == "Работа"
    assert workspaces[0***REMOVED***["source"***REMOVED***.startswith("idea:")
    # Reply should mention workspace name + source preview
    last_reply = mock_update.effective_message.reply_text.await_args_list[-1***REMOVED***[0***REMOVED***[0***REMOVED***
    assert "Работа" in last_reply
    assert "Workspace" in last_reply


@pytest.mark.asyncio
async def test_cancel_clears_state(
    bot_with_corpus: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """`/cancel` clears per-chat onboarding state (STEP_BACK to NONE)."""
    import scripts_01.telegram_bot as tb_mod
    from scripts_01._workspace_onboarding import (
        STATE_ASKING_IDEA,
        STATE_NONE,
        STATE_DONE,
        clear_state as _clear,
    )

    # First put chat into ASKING_IDEA
    state = bot_with_corpus.onboarding_state(12345)
    state.state = STATE_ASKING_IDEA
    state.source = "idea:тест"
    bot_with_corpus.save_onboarding(12345, state)

    with patch.object(tb_mod, "_bot", bot_with_corpus):
        await tb_mod._cancel(mock_update, mock_context)

    cleared = bot_with_corpus.onboarding_state(12345)
    assert cleared.state == STATE_NONE
    assert cleared.source == ""
    # Reply should be informational
    mock_update.effective_message.reply_text.assert_awaited_once()
    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "прерван" in reply_text.lower() or "cancel" in reply_text.lower()


@pytest.mark.asyncio
async def test_cancel_noop_when_no_onboarding(
    bot_with_corpus: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """`/cancel` from NONE/DONE state is a no-op + explanatory reply (defensive check)."""
    import scripts_01.telegram_bot as tb_mod

    with patch.object(tb_mod, "_bot", bot_with_corpus):
        await tb_mod._cancel(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_awaited_once()
    reply_text = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "не в онбординге" in reply_text or "ℹ️" in reply_text


# ── WorkspaceRegistry integration tests (Phase 5.4-OQ26-31 follow-up) ────────


def test_bot_has_registry_attribute(
    bot: TelegramFreebuffBot, tmp_path: Path
) -> None:
    """TelegramFreebuffBot.__init__ должен создать self.registry привязанный к tmp DB."""
    import core_02.workspace_registry as wr_mod

    # bot is backed by tmp_path (per bot fixture); registry should exist + use tmp DB
    assert isinstance(bot.registry, wr_mod.WorkspaceRegistry)
    assert bot.registry.db_path.parent == tmp_path / "data_13"
    # No real data_13/context.db pollution: db_path lives strictly under tmp.
    assert str(tmp_path) in str(bot.registry.db_path)


@pytest.mark.asyncio
async def test_onboarding_persists_to_workspace_registry(
    bot_with_corpus: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """ASKING_WORKSPACE_NAME → DONE должен зарегистрировать workspace в core_02/registry.

    Test fixture создаёт pompts_11/047_06_e2e_platform_test.md; пишем в source чтобы
    избежать зависимости от mtime-ordering при выборе.
    """
    import scripts_01.telegram_bot as tb_mod
    from scripts_01._workspace_onboarding import (
        STATE_ASKING_WORKSPACE_NAME,
    )

    # Pre-set state to ASKING_WORKSPACE_NAME with deterministic source.
    state = bot_with_corpus.onboarding_state(12345)
    state.state = STATE_ASKING_WORKSPACE_NAME
    state.source = "pompts_11/047_06_e2e_platform_test.md"
    bot_with_corpus.save_onboarding(12345, state)

    # Send workspace name.
    mock_update.message.text = "Тестовый Workspace"
    with patch.object(tb_mod, "_bot", bot_with_corpus):
        await tb_mod._handle_message(mock_update, mock_context)

    # Registry должен содержать workspace.
    workspaces = bot_with_corpus.registry.list_workspaces()
    our_workspace = next(
        (w for w in workspaces if w.name == "Тестовый Workspace"), None
    )
    assert our_workspace is not None, (
        "Workspace not registered in registry; got workspaces=%s" % workspaces
    )
    assert our_workspace.owner_chat_id == 12345
    # project_paths должен содержать абсолютный resolved path
    assert len(our_workspace.project_paths) == 1
    bound = our_workspace.project_paths[0***REMOVED***
    assert bound.endswith("047_06_e2e_platform_test.md")
    assert Path(bound).is_absolute()


@pytest.mark.asyncio
async def test_workspace_list_command_filters_by_owner_chat_id(
    bot: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """/workspace list должен показывать только workspace-ы с owner == ours chat_id."""
    import scripts_01.telegram_bot as tb_mod

    # Two workspaces with different owner_chat_ids.
    bot.registry.create_workspace(
        name="Mine Работа",
        project_paths=[***REMOVED***,
        description="owned by 12345",
        owner_chat_id=12345,
    )
    bot.registry.create_workspace(
        name="Someone Else Учёба",
        project_paths=[***REMOVED***,
        description="owned by 99999",
        owner_chat_id=99999,
    )

    with patch.object(tb_mod, "_bot", bot):
        await tb_mod.cmd_workspace(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_awaited_once()
    reply = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    # Наш workspace виден.
    assert "Mine Работа" in reply
    # Чужой workspace НЕ виден.
    assert "Someone Else" not in reply
    # Заголовок со счётчиком.
    assert "Твои workspace-ы" in reply
    assert "(1)" in reply  # 1 наш workspace


@pytest.mark.asyncio
async def test_workspace_list_command_empty_state_message(
    bot: TelegramFreebuffBot,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """Empty registry → exact informative message (для пустого состояния)."""
    import scripts_01.telegram_bot as tb_mod

    with patch.object(tb_mod, "_bot", bot):
        await tb_mod.cmd_workspace(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_awaited_once()
    reply = mock_update.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "нет зарегистрированных workspace-ов" in reply
    assert "📂" in reply


# ── /queue list command tests (v5.80.0) ──────────────────────────


@pytest.fixture
def queue_prompts_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Isolate prompt_queue к tmp_path через FREEBUFF_ROOT. bot & cmd_queue share this."""
    monkeypatch.setenv("FREEBUFF_ROOT", str(tmp_path))
    from scripts_01.prompt_queue import ensure_queue_dirs
    ensure_queue_dirs()
    return tmp_path


def _make_mock_update_for_queue(chat_id: int = 12345) -> MagicMock:
    """Helper: build a mock Update that cmd_queue can call .effective_message.reply_text on."""
    upd = MagicMock(spec=Update)
    chat = MagicMock(spec=Chat)
    chat.id = chat_id
    msg = MagicMock(spec=Message)
    msg.reply_text = AsyncMock()
    upd.effective_chat = chat
    upd.effective_message = msg
    return upd


@pytest.mark.asyncio
async def test_queue_command_empty_state(
    queue_prompts_root: Path,
    tmp_path: Path,
) -> None:
    """Empty queue → counts all zero + dir labels show '(пусто)'."""
    bot = TelegramFreebuffBot(queue_prompts_root)
    upd = _make_mock_update_for_queue()
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.args = [***REMOVED***

    import scripts_01.telegram_bot as tb_mod
    with patch.object(tb_mod, "_bot", bot):
        await tb_mod.cmd_queue(upd, ctx)

    upd.effective_message.reply_text.assert_awaited_once()
    reply = upd.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    # Counts line: all zeros.
    assert "0 user • 0 running • 0 done • 0 failed" in reply
    # All 4 dir labels visible, each '(пусто)'.
    assert "📥 user (ожидают)" in reply
    assert "⚙️ running" in reply
    assert "✅ done" in reply
    assert "❌ failed" in reply
    assert reply.count("(пусто)") == 4


@pytest.mark.asyncio
async def test_queue_command_user_only(
    queue_prompts_root: Path,
) -> None:
    """One task in user/ → '1 файл(ов)' + task title + created timestamp."""
    bot = TelegramFreebuffBot(queue_prompts_root)
    # Setup: 1 task в user/.
    from scripts_01.prompt_queue import write_user_prompt
    write_user_prompt(
        "сделай отчёт по проекту interior_planner",
        chat_id=12345,
        source="telegram",
    )

    upd = _make_mock_update_for_queue()
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.args = [***REMOVED***

    import scripts_01.telegram_bot as tb_mod
    with patch.object(tb_mod, "_bot", bot):
        await tb_mod.cmd_queue(upd, ctx)

    reply = upd.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    # Counts: user=1, others=0.
    assert "1 user" in reply
    assert "0 running" in reply
    # user/ section shows file count + task title preview.
    assert "📥 user (ожидают): 1 файл(ов)" in reply
    assert "interior_planner" in reply or "сделай отчёт" in reply
    assert "Created:" in reply
    assert "mtime:" in reply
    # running/done/failed empty.
    assert reply.count("(пусто)") == 3  # only running, done, failed empty


@pytest.mark.asyncio
async def test_queue_command_running_filter(
    queue_prompts_root: Path,
) -> None:
    """`/queue running` filter → only running/ items, other dirs not shown."""
    bot = TelegramFreebuffBot(queue_prompts_root)
    from scripts_01.prompt_queue import (
        move_to_status,
        prompts_dir,
        queue_dir,
        write_user_prompt,
    )

    # 1 task в user (count=1) + 1 task pre-moved to running/ (count=1).
    user_path = write_user_prompt("user task A", chat_id=12345)
    running_path = write_user_prompt("running task B", chat_id=12345)
    move_to_status(running_path, "running")

    upd = _make_mock_update_for_queue()
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.args = ["running"***REMOVED***

    import scripts_01.telegram_bot as tb_mod
    with patch.object(tb_mod, "_bot", bot):
        await tb_mod.cmd_queue(upd, ctx)

    reply = upd.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    # Only running/ section visible, with 1 file.
    assert "⚙️ running (в работе / resumable): 1 файл(ов)" in reply
    assert "running task B" in reply
    # user/done/failed dir labels NOT present (filter excludes them).
    assert "📥 user (ожидают)" not in reply
    assert "✅ done" not in reply
    assert "❌ failed" not in reply


@pytest.mark.asyncio
async def test_queue_command_invalid_filter(
    queue_prompts_root: Path,
) -> None:
    """`/queue banana` → Usage message (not crash)."""
    bot = TelegramFreebuffBot(queue_prompts_root)
    upd = _make_mock_update_for_queue()
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.args = ["banana"***REMOVED***

    import scripts_01.telegram_bot as tb_mod
    with patch.object(tb_mod, "_bot", bot):
        await tb_mod.cmd_queue(upd, ctx)

    reply = upd.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    assert "Usage: /queue" in reply
    assert "user|running|done|failed" in reply


@pytest.mark.asyncio
async def test_queue_command_multiturn_badge(
    queue_prompts_root: Path,
) -> None:
    """Multi-turn file at iteration 2/3 → badge shows 'running-pending iter 2/3'."""
    bot = TelegramFreebuffBot(queue_prompts_root)
    from scripts_01.prompt_queue import (
        append_iteration,
        move_to_status,
        write_user_prompt,
    )

    p = write_user_prompt("multi turn task", chat_id=12345)
    p = move_to_status(p, "running")  # re-assign: returns NEW path after rename
    append_iteration(p, 2, "Какой порт?", new_status="running-pending")

    upd = _make_mock_update_for_queue()
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.args = [***REMOVED***

    import scripts_01.telegram_bot as tb_mod
    with patch.object(tb_mod, "_bot", bot):
        await tb_mod.cmd_queue(upd, ctx)

    reply = upd.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    # Badge format: "[running-pending iter 2/3***REMOVED***"
    assert "running-pending iter 2/3" in reply
    # Status counted correctly.
    assert "1 running" in reply
    assert "0 user" in reply


@pytest.mark.asyncio
async def test_queue_command_truncates_at_limit(
    queue_prompts_root: Path,
) -> None:
    """cmd_queue truncates TG message at 3800 chars and shows marker (for 50 prompts)."""
    bot = TelegramFreebuffBot(queue_prompts_root)
    from scripts_01.prompt_queue import write_user_prompt
    for i in range(50):
        write_user_prompt(f"test task {i***REMOVED*** - " + ("x" * 100), chat_id=12345)

    upd = _make_mock_update_for_queue()
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.args = [***REMOVED***

    import scripts_01.telegram_bot as tb_mod
    with patch.object(tb_mod, "_bot", bot):
        await tb_mod.cmd_queue(upd, ctx)

    reply = upd.effective_message.reply_text.await_args[0***REMOVED***[0***REMOVED***
    # TG-limit safety margin: <= 4096 chars.
    assert len(reply) <= 4096, f"reply length {len(reply)***REMOVED*** exceeds 4096 TG-limit"
    # Truncation marker present when len > 3800.
    assert "truncated" in reply.lower(), f"missing truncation marker; reply_len={len(reply)***REMOVED***"


def test_telegram_bot_class_scope_indent_guard() -> None:
    """Anti-regression: _fallback_reply MUST stay inside TelegramFreebuffBot class (4-space indent).

    Prior bug (v5.80.0 polish): str_replace accidentally de-indented the method to 0 spaces,
    so callers `bot._fallback_reply()` raised AttributeError. This guard catches that
    regression without booting a Telegram bot.
    """
    ***REMOVED***
    src_path = Path(__file__).resolve().parent.parent / "scripts_01" / "telegram_bot.py"
    text = src_path.read_text(encoding="utf-8")
    match = re.search(r"^( +)def _fallback_reply\(self\)", text, re.MULTILINE)
    assert match is not None, "_fallback_reply def not found in telegram_bot.py"
    indent_spaces = len(match.group(1))
    assert indent_spaces == 4, (
        f"_fallback_reply de-indented outside class scope; current indent = "
        f"{indent_spaces***REMOVED*** spaces (expected 4 inside class)"
    )


@pytest.mark.asyncio
async def test_fallback_reply_includes_queue_command(
    bot: TelegramFreebuffBot,
) -> None:
    """`_fallback_reply()` help-text список должен включать /queue."""
    reply = bot._fallback_reply()
    assert "/queue" in reply
    assert "список задач" in reply.lower() or "очеред" in reply.lower()


# ───────── v5.83.0 dual-path dispatch tests ─────────

@pytest.mark.asyncio
async def test_cmd_task_spawns_dispatcher_subprocess(
    queue_prompts_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """v5.83.0 dual-path: cmd_task spawns prompt_dispatcher.py --once via asyncio.

    cmd_task is module-level (registered as CommandHandler("task", cmd_task)),
    so tests call it directly without bot instance.
    """
    class _FakeProc:
        pid = 12345
        async def wait(self) -> None:
            return None

    calls_made: list = [***REMOVED***
    async def fake_create(*args, **kwargs):
        calls_made.append((args, kwargs))
        return _FakeProc()

    monkeypatch.setattr(tg_module.asyncio, "create_subprocess_exec", fake_create)

    update = _make_mock_update_for_queue()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["test", "task", "body"***REMOVED***
    await cmd_task(update, context)

    assert len(calls_made) == 1, f"expected 1 spawn, got {len(calls_made)***REMOVED***"
    args, _ = calls_made[0***REMOVED***
    script_arg = next((a for a in args if "prompt_dispatcher.py" in str(a)), None)
    assert script_arg is not None, f"prompt_dispatcher.py not in spawn args: {args***REMOVED***"
    assert "--once" in args, f"--once not in spawn args: {args***REMOVED***"


@pytest.mark.asyncio
async def test_cmd_task_spawn_failure_replies_cron_fallback(
    queue_prompts_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """v5.83.0 dual-path: spawn OSError → reply mentions cron safety-net."""
    async def fake_create_raising(*args, **kwargs):
        raise OSError("fake spawn failure")

    monkeypatch.setattr(tg_module.asyncio, "create_subprocess_exec", fake_create_raising)

    update = _make_mock_update_for_queue()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["test"***REMOVED***
    await cmd_task(update, context)

    sent = update.effective_message.reply_text.call_args_list
    texts: list = [***REMOVED***
    for c in sent:
        txt = c.kwargs.get("text") if c.kwargs.get("text") else (str(c.args[0***REMOVED***) if c.args else "")
        texts.append(txt)
    assert any("deferred" in t or "cron safety-net" in t for t in texts), \
        f"expected cron fallback hint, got texts: {texts***REMOVED***"


def test_dispatch_one_race_returns_skipped_locked(
    tmp_path: "Path",
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """v5.83.0 race-safe: dispatch_one returns skipped_locked when move_to_status raises FNF."""
    monkeypatch.setenv("FREEBUFF_ROOT", str(tmp_path))

    from scripts_01.prompt_dispatcher import dispatch_one
    from scripts_01.prompt_queue import write_user_prompt

    write_user_prompt("racing task", source="test")

    import scripts_01.prompt_dispatcher as pd
    # CON-33 (v5.89.0): мокаем pre-check на False — иначе тест зависит от
    # реального окружения (живой freebuff-инстанс → backoff вместо race-пути).
    monkeypatch.setattr(pd, "_live_instance_busy", lambda: False)
    original_move = pd.move_to_status

    def fake_move(path: "Path", status: "str") -> "Path":
        if status == "running":
            raise FileNotFoundError(f"raced: {path***REMOVED***")
        return original_move(path, status)

    monkeypatch.setattr(pd, "move_to_status", fake_move)

    launch_calls: "list[str***REMOVED***" = [***REMOVED***
    def fake_launch(body: "str", ws: "str", timeout: int, model: str = "auto") -> "dict":
        launch_calls.append(body)
        return {"success": True, "output": "should not run"***REMOVED***

    result = dispatch_one(launcher=fake_launch, send_tg=False)

    assert result["handled"***REMOVED*** is False
    assert result["status"***REMOVED*** == "skipped_locked"
    assert launch_calls == [***REMOVED***, f"launcher must NOT run on race; got {launch_calls***REMOVED***"


@pytest.mark.asyncio
async def test_reap_subprocess_safe_unregisters_from_pending(
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """v5.83.0 GC-safety: _reap_subprocess_safe removes itself из _pending_reapers по завершении."""
    import asyncio
    
    # v5.84.0 polish: use POSIX `true` for instant exit — zero wall-clock dependence.
    # Previous `time.sleep(0.05)` was flakable in CI / loaded systems.
    proc = await asyncio.create_subprocess_exec(
        "true",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    reaper = asyncio.create_task(tg_module._reap_subprocess_safe(proc))
    _pending_reapers.add(reaper)
    before = len(_pending_reapers)
    assert before >= 1

    await reaper
    after = len(_pending_reapers)
    assert after == before - 1, f"reaper not unregistered: before={before***REMOVED***, after={after***REMOVED***"


def test_prompt_dispatch_sh_invokes_recover_before_main_flag() -> None:
    """v5.83.0: prompt_dispatch.sh — recover call precedes main $FLAG invocation."""
    ***REMOVED***
    sh = (Path(__file__).resolve().parent.parent / "scripts_01" / "prompt_dispatch.sh").read_text(
        encoding="utf-8"
    )
    # Compare positions of the TWO python dispatcher invocations:
    #   1. recover call (uses literal `--recover --recover-age 3600`)
    #   2. main flag invocation (uses `$FLAG` shell variable)
    recover_idx = sh.find("python scripts_01/prompt_dispatcher.py --recover")
    main_idx = sh.find('python scripts_01/prompt_dispatcher.py "$FLAG"')
    assert recover_idx > 0, f"recover invocation NOT found in dispatch script"
    assert main_idx > 0, f"main $FLAG invocation NOT found in dispatch script"
    assert main_idx > recover_idx, (
        f"recover (idx={recover_idx***REMOVED***) must PRECEDE main dispatch (idx={main_idx***REMOVED***)"
    )
