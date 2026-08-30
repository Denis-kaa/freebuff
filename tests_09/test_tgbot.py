"""Tests for freebuff_plugin_03/tgbot.py.

Covers: imports, scenario list, variable extraction, apply, callback prefixes.
Uses real ScenarioEngine and mocked Telegram Update/Context.
"""

from __future__ import annotations

import os
import sys
}
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

# Skip if python-telegram-bot not installed
try:
    import telegram  # noqa: F401
    from telegram import Update, Message, Chat, InlineKeyboardMarkup
    from telegram.ext import ContextTypes
except ImportError:
    pytest.skip("python-telegram-bot not installed", allow_module_level=True)

from freebuff_plugin_03.tgbot import ScenarioTGBot  # noqa: E402


# ── Helper: extract text from mock (handles positional and **kwargs calls) ──


def _get_text(mock_method: MagicMock) -> str:
    """Извлекает текст из mock вызова (args[0] или kwargs.get('text'))."""
    if mock_method.await_args is None:
        return ""
    if mock_method.await_args.args:
        return str(mock_method.await_args.args[0])
    return mock_method.await_args.kwargs.get("text", "")


# ── Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def bot() -> ScenarioTGBot:
    """ScenarioTGBot using real ScenarioEngine."""
    return ScenarioTGBot()


@pytest.fixture
def mock_message() -> MagicMock:
    msg = MagicMock(spec=Message)
    msg.text = "test"
    msg.reply_text = AsyncMock()
    msg.reply_document = AsyncMock()
    return msg


@pytest.fixture
def mock_chat() -> MagicMock:
    chat = MagicMock(spec=Chat)
    chat.id = 12345
    return chat


@pytest.fixture
def mock_update(mock_message: MagicMock, mock_chat: MagicMock) -> MagicMock:
    upd = MagicMock(spec=Update)
    upd.effective_chat = mock_chat
    upd.effective_message = mock_message
    upd.message = mock_message
    # Callback query
    upd.callback_query = MagicMock()
    upd.callback_query.answer = AsyncMock()
    upd.callback_query.edit_message_text = AsyncMock()
    upd.callback_query.edit_message_reply_markup = AsyncMock()
    upd.callback_query.data = ""
    upd.callback_query.message = mock_message
    return upd


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.args = []
    ctx.bot = MagicMock()
    ctx.bot.send_chat_action = AsyncMock()
    return ctx


# ── Basic tests ───────────────────────────────────────────────


def test_import_and_instantiate(bot: ScenarioTGBot) -> None:
    """Bot can be instantiated with real ScenarioEngine."""
    assert bot.engine is not None
    scenarios = bot.engine.list_scenarios()
    assert len(scenarios) >= 7  # all 7 scenarios loaded


def test_get_categories(bot: ScenarioTGBot) -> None:
    """Categories should include freelancing, agent, templates."""
    cats = bot._get_categories()
    assert "freelancing" in cats
    assert "agent" in cats
    assert "templates" in cats


def test_scenarios_by_category(bot: ScenarioTGBot) -> None:
    """Freelancing should have 5 scenarios."""
    scenarios = bot._scenarios_by_category("freelancing")
    assert len(scenarios) >= 5
    for s in scenarios:
        assert s["category"] == "freelancing"


def test_extract_variable_names(bot: ScenarioTGBot) -> None:
    """Variable names are extracted from template placeholders."""
    names = bot._extract_variable_names("Hello {name), welcome to {place]")
    assert "name" in names
    assert "place" in names


def test_extract_variable_names_no_vars(bot: ScenarioTGBot) -> None:
    """No placeholders returns empty list."""
    names = bot._extract_variable_names("Hello world")
    assert names == []


def test_format_scenario_list(bot: ScenarioTGBot) -> None:
    """Formatting produces markdown with scenario names."""
    scenarios = bot.engine.list_scenarios()
    text = bot._format_scenario_list(scenarios, show_category=False)
    assert "Парсер сайта" in text
    assert "Telegram бот" in text


def test_format_scenario_list_empty(bot: ScenarioTGBot) -> None:
    """Empty list returns 'no scenarios' message."""
    text = bot._format_scenario_list([])
    assert "Нет сценариев" in text


def test_format_scenario_detail(bot: ScenarioTGBot) -> None:
    """Detail formatting includes slug and description."""
    scenario = bot.engine.get_scenario("freelance_parser")
    assert scenario is not None
    text = bot._format_scenario_detail(scenario.to_dict())
    assert "freelance_parser" in text
    assert "Парсер" in text


def test_scenario_apply_no_vars(bot: ScenarioTGBot) -> None:
    """apply_scenario returns prompt for freelance_parser."""
    result = bot.engine.apply_scenario("freelance_parser")
    assert "error" not in result
    assert result["slug"] == "freelance_parser"
    assert len(result["prompt"]) > 50


def test_scenario_apply_with_vars(bot: ScenarioTGBot) -> None:
    """Variable substitution works."""
    result = bot.engine.apply_scenario("freelance_parser", {"URL": "https://test.com"})
    assert "error" not in result
    assert "https://test.com" in result["prompt"]


def test_scenario_apply_not_found(bot: ScenarioTGBot) -> None:
    """Unknown slug returns error."""
    result = bot.engine.apply_scenario("nonexistent")
    assert "error" in result


def test_scenario_search(bot: ScenarioTGBot) -> None:
    """Search finds telegram-related scenarios."""
    results = bot.engine.search_scenarios("telegram")
    slugs = [r["slug"] for r in results]
    assert "freelance_tg_bot" in slugs


def test_scenario_search_no_results(bot: ScenarioTGBot) -> None:
    """Search with nonsense query returns empty."""
    results = bot.engine.search_scenarios("xyznonexistent123")
    assert results == []


def test_categories_keyboard(bot: ScenarioTGBot) -> None:
    """Category keyboard has correct buttons (substring match due to emoji)."""
    kb = bot._categories_keyboard()
    assert isinstance(kb, InlineKeyboardMarkup)
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    texts = [b.text for b in buttons]
    # Substring match because buttons have emoji prefixes like "💼 Freelancing (5)"
    assert any("freelancing" in t.lower() for t in texts)
    assert any("Все сценарии" in t for t in texts)
    assert any("Поиск" in t for t in texts)


def test_scenario_detail_keyboard_with_template(bot: ScenarioTGBot) -> None:
    """Scenarios with prompt_template get 'Apply' button (substring match for emoji)."""
    kb = bot._scenario_detail_keyboard("freelance_parser", "freelancing")
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    texts = [b.text for b in buttons]
    # Substring match: button text is "🚀 Применить", not exact "Применить"
    assert any("Применить" in t for t in texts)
    assert any("Назад" in t for t in texts)


def test_scenario_detail_keyboard_no_template(bot: ScenarioTGBot) -> None:
    """Scenarios without template don't get 'Apply'."""
    kb = bot._scenario_detail_keyboard("task_framework", "templates")
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    texts = [b.text for b in buttons]
    assert "Применить" not in texts  # exact check: no emoji for non-apply buttons


def test_home_keyboard(bot: ScenarioTGBot) -> None:
    """Home keyboard has scenarios and status buttons (substring match for emoji)."""
    kb = bot._home_keyboard()
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    texts = [b.text for b in buttons]
    assert any("Сценарии" in t for t in texts)
    assert any("Статус" in t for t in texts)
    assert any("Помощь" in t for t in texts)


# ── Command handler tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_cmd_start(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """cmd_start sends welcome message with keyboard."""
    await bot.cmd_start(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "Freebuff Plugin" in text
    assert "/scenarios" in text


@pytest.mark.asyncio
async def test_cmd_status(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """cmd_status shows scenario count."""
    await bot.cmd_status(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "Сценариев:" in text
    assert "freelancing" in text


@pytest.mark.asyncio
async def test_cmd_scenarios_no_args(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """cmd_scenarios without args shows category menu."""
    mock_context.args = []
    await bot.cmd_scenarios(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "категорию" in text


@pytest.mark.asyncio
async def test_cmd_scenarios_list(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """/scenarios list shows all scenarios."""
    mock_context.args = ["list"]
    await bot.cmd_scenarios(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "Парсер сайта" in text or "Все сценарии" in text


@pytest.mark.asyncio
async def test_cmd_scenarios_list_freelancing(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """/scenarios list freelancing shows only freelancing scenarios."""
    mock_context.args = ["list", "freelancing"]
    await bot.cmd_scenarios(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "freelancing" in text or "Сценарии" in text


@pytest.mark.asyncio
async def test_cmd_scenarios_apply_with_vars(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """/scenarios apply with URL=... substitutes vars and returns prompt."""
    mock_context.args = ["apply", "freelance_parser", "URL=https://test.com"]
    await bot.cmd_scenarios(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "https://test.com" in text
    assert "Сценарий применён" in text


@pytest.mark.asyncio
async def test_cmd_scenarios_apply_all_vars(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """/scenarios apply with all variables works."""
    mock_context.args = [
        "apply", "freelance_parser",
        "URL=https://test.com",
        "поле1=title",
        "поле2=price",
        "поле3=desc",
        "формат=JSON",
    ]
    await bot.cmd_scenarios(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "Сценарий применён" in text


@pytest.mark.asyncio
async def test_cmd_scenarios_apply_request_vars(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """/scenarios apply without vars requests variable input (freelance_parser needs them)."""
    mock_context.args = ["apply", "freelance_parser"]
    await bot.cmd_scenarios(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    # freelance_parser has variables, so it shows variable request
    assert "Для применения укажи переменные" in text


@pytest.mark.asyncio
async def test_cmd_scenarios_apply_not_found(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """/scenarios apply nonexistent returns error."""
    mock_context.args = ["apply", "nonexistent"]
    await bot.cmd_scenarios(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "не найден" in text


@pytest.mark.asyncio
async def test_cmd_scenarios_apply_no_slug(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """/scenarios apply without slug shows usage."""
    mock_context.args = ["apply"]
    await bot.cmd_scenarios(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "Укажи slug" in text


@pytest.mark.asyncio
async def test_cmd_scenarios_search(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """/scenarios search telegram finds TG bot scenario."""
    mock_context.args = ["search", "telegram"]
    await bot.cmd_scenarios(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "telegram" in text.lower()


@pytest.mark.asyncio
async def test_cmd_scenarios_search_no_query(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """/scenarios search without query shows usage."""
    mock_context.args = ["search"]
    await bot.cmd_scenarios(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "Укажи поисковый запрос" in text


@pytest.mark.asyncio
async def test_cmd_scenarios_unknown_subcommand(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """Unknown subcommand shows available subcommands."""
    mock_context.args = ["blabla"]
    await bot.cmd_scenarios(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "Неизвестная" in text or "list" in text


@pytest.mark.asyncio
async def test_cmd_reload(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """/reload reloads scenarios."""
    await bot.cmd_reload(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "Сценарии перезагружены" in text


# ── Text handler tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_text_greeting(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """Arbitrary text shows greeting."""
    await bot.handle_text(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    # Should mention available commands since no state is set
    assert "Freebuff Plugin" in text or "сценариев" in text or "/start" in text or "/scenarios" in text


@pytest.mark.asyncio
async def test_handle_text_gotovo(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """"готово" text applies scenario without variables."""
    # Set up state as if user clicked "Apply" on freelance_parser
    bot._set_state(12345, {"slug": "freelance_parser", "step": "wait_vars"})
    mock_update.message.text = "готово"
    mock_update.effective_chat.id = 12345
    await bot.handle_text(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    # Should apply the scenario (no variables)
    assert "Сценарий применён" in text
    # State should be cleaned up
    assert bot._get_state(12345) is None


@pytest.mark.asyncio
async def test_handle_text_with_vars(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """key=value text in wait_vars state applies with variables."""
    bot._set_state(12345, {"slug": "freelance_parser", "step": "wait_vars"})
    mock_update.message.text = "URL=https://test.com\nформат=JSON"
    mock_update.effective_chat.id = 12345
    await bot.handle_text(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_awaited_once()
    text = _get_text(mock_update.effective_message.reply_text)
    assert "Сценарий применён" in text
    assert "https://test.com" in text


# ── Callback handler tests ────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_callback_category(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """Category callback shows scenarios list."""
    mock_update.callback_query.data = "sc_cat_freelancing"
    await bot.handle_callback(mock_update, mock_context)
    mock_update.callback_query.answer.assert_awaited_once()
    mock_update.callback_query.edit_message_text.assert_awaited_once()
    text = _get_text(mock_update.callback_query.edit_message_text)
    assert "freelancing" in text or "Сценарии" in text


@pytest.mark.asyncio
async def test_handle_callback_scenario(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """Scenario detail callback shows details."""
    mock_update.callback_query.data = "sc_sc_freelance_parser"
    await bot.handle_callback(mock_update, mock_context)
    mock_update.callback_query.edit_message_text.assert_awaited_once()
    text = _get_text(mock_update.callback_query.edit_message_text)
    assert "freelance_parser" in text


@pytest.mark.asyncio
async def test_handle_callback_back_cat(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """Back to categories shows category menu."""
    mock_update.callback_query.data = "sc_back_cat"
    await bot.handle_callback(mock_update, mock_context)
    mock_update.callback_query.edit_message_text.assert_awaited_once()
    text = _get_text(mock_update.callback_query.edit_message_text)
    assert "категорию" in text


@pytest.mark.asyncio
async def test_handle_callback_back_sc(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """Back to scenario list in category."""
    mock_update.callback_query.data = "sc_back_sc_freelancing"
    await bot.handle_callback(mock_update, mock_context)
    mock_update.callback_query.edit_message_text.assert_awaited_once()
    text = _get_text(mock_update.callback_query.edit_message_text)
    assert "freelancing" in text or "Сценарии" in text


@pytest.mark.asyncio
async def test_handle_callback_status(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """Status callback shows system status."""
    mock_update.callback_query.data = "sc_status"
    await bot.handle_callback(mock_update, mock_context)
    mock_update.callback_query.edit_message_text.assert_awaited_once()
    text = _get_text(mock_update.callback_query.edit_message_text)
    assert "Сценариев" in text


@pytest.mark.asyncio
async def test_handle_callback_help(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """Help callback shows help text."""
    mock_update.callback_query.data = "sc_help"
    await bot.handle_callback(mock_update, mock_context)
    mock_update.callback_query.edit_message_text.assert_awaited_once()
    text = _get_text(mock_update.callback_query.edit_message_text)
    assert "Команды" in text


@pytest.mark.asyncio
async def test_handle_callback_apply_shows_vars_prompt(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """Apply callback for freelance_parser shows variable request (has vars)."""
    mock_update.callback_query.data = "sc_apply_freelance_parser"
    await bot.handle_callback(mock_update, mock_context)
    mock_update.callback_query.edit_message_text.assert_awaited_once()
    text = _get_text(mock_update.callback_query.edit_message_text)
    # freelance_parser has variables, so it asks for them
    assert "Введи переменные" in text


@pytest.mark.asyncio
async def test_handle_callback_vars(bot: ScenarioTGBot, mock_update: MagicMock, mock_context: MagicMock) -> None:
    """Vars callback (apply without vars) returns prompt."""
    mock_update.callback_query.data = "sc_vars_freelance_parser"
    await bot.handle_callback(mock_update, mock_context)
    mock_update.callback_query.edit_message_text.assert_awaited_once()
    text = _get_text(mock_update.callback_query.edit_message_text)
    assert "Сценарий применён" in text


# ── Variable extraction from scenarios ────────────────────────


def test_parser_has_variables(bot: ScenarioTGBot) -> None:
    """freelance_parser has known variables."""
    scenario = bot.engine.get_scenario("freelance_parser")
    assert scenario is not None
    vars_found = bot._extract_variable_names(scenario.prompt_template)
    assert "URL" in vars_found
    assert "формат" in vars_found


def test_tg_bot_has_variables(bot: ScenarioTGBot) -> None:
    """freelance_tg_bot has known variables."""
    scenario = bot.engine.get_scenario("freelance_tg_bot")
    assert scenario is not None
    vars_found = bot._extract_variable_names(scenario.prompt_template)
    assert "описание" in vars_found
    assert "текст" in vars_found
