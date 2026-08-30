"""Tests for scripts_01/tgbot_base.py (BaseTGBot, DEBT-2026-07-31-007).

Покрывает общий слой Telegram-ботов, вынесенный из дублей:
  - load_dotenv — загрузка .env (пропуск комментариев/пустых, setdefault)
  - BaseTGBot — workspace/token, build_application, run_polling, error_handler
  - Наследование: TelegramFreebuffBot и ScenarioTGBot являются BaseTGBot
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
    from telegram import Update
    from telegram.ext import ApplicationBuilder
except ImportError:
    pytest.skip("python-telegram-bot not installed", allow_module_level=True)

from scripts_01.tgbot_base import BaseTGBot, load_dotenv  # noqa: E402


# ═══════════════════════════════════════════════════════════════
# load_dotenv
# ═══════════════════════════════════════════════════════════════


class TestLoadDotenv:
    def test_loads_key_values(self, tmp_path: Path, monkeypatch) -> None:
        env = tmp_path / ".env"
        env.write_text("KEY1=value1\nKEY2=value2\n", encoding="utf-8")
        load_dotenv(env)
        assert os.environ.get("KEY1") == "value1"
        assert os.environ.get("KEY2") == "value2"

    def test_skips_comments_and_blanks(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("# comment\n\nEMPTY=\nFOO=bar\n", encoding="utf-8")
        load_dotenv(env)
        assert os.environ.get("FOO") == "bar"

    def test_strips_quotes(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("TOKEN='abc123'\n", encoding="utf-8")
        load_dotenv(env)
        assert os.environ.get("TOKEN") == "abc123"

    def test_setdefault_does_not_overwrite(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("KEEP", "original")
        env = tmp_path / ".env"
        env.write_text("KEEP=overwritten\n", encoding="utf-8")
        load_dotenv(env)
        assert os.environ.get("KEEP") == "original"

    def test_missing_file_is_noop(self, tmp_path: Path) -> None:
        load_dotenv(tmp_path / "missing.env")  # не падает


# ═══════════════════════════════════════════════════════════════
# BaseTGBot
# ═══════════════════════════════════════════════════════════════


class TestBaseTGBot:
    def test_workspace_resolution(self, tmp_path: Path) -> None:
        bot = BaseTGBot(tmp_path)
        assert bot.workspace == Path(tmp_path)

    def test_token_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-xyz")
        bot = BaseTGBot()
        assert bot.token == "test-token-xyz"

    def test_token_empty_by_default(self, tmp_path: Path, monkeypatch) -> None:
        # tmp_path: изолируемся от реального корневого .env, который может
        # задать TELEGRAM_BOT_TOKEN (иначе тест флейки)
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        bot = BaseTGBot(tmp_path)
        assert bot.token == ""

    def test_build_application_without_token_raises(self) -> None:
        bot = BaseTGBot()
        bot.token = ""
        with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
            bot.build_application()

    def test_build_application_with_token(self, monkeypatch) -> None:
        from telegram.ext import Application

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-xyz")
        bot = BaseTGBot()
        app = bot.build_application()
        assert isinstance(app, Application)

    def test_run_polling_clean_exit_returns_zero(self) -> None:
        class _FakeApp:
            def run_polling(self) -> None:
                raise KeyboardInterrupt

        bot = BaseTGBot()
        assert bot.run_polling(_FakeApp()) == 0

    def test_run_polling_success_returns_zero(self) -> None:
        class _FakeApp:
            def run_polling(self) -> None:
                return None

        bot = BaseTGBot()
        assert bot.run_polling(_FakeApp()) == 0

    def test_run_polling_error_returns_one(self) -> None:
        class _FakeApp:
            def run_polling(self) -> None:
                raise RuntimeError("boom")

        bot = BaseTGBot()
        assert bot.run_polling(_FakeApp()) == 1

    @pytest.mark.asyncio
    async def test_error_handler_logs_and_replies(self) -> None:
        bot = BaseTGBot()
        update = MagicMock(spec=Update)
        update.effective_message = MagicMock()
        update.effective_message.reply_text = AsyncMock()
        context = MagicMock()
        context.error = RuntimeError("test error")

        with patch.object(bot.logger, "error") as mock_log:
            await bot.error_handler(update, context)

        mock_log.assert_called_once()
        update.effective_message.reply_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_error_handler_no_message_no_reply(self) -> None:
        bot = BaseTGBot()
        update = MagicMock(spec=Update)
        update.effective_message = None
        context = MagicMock()
        context.error = RuntimeError("test error")

        with patch.object(bot.logger, "error") as mock_log:
            await bot.error_handler(update, context)

        mock_log.assert_called_once()
        # reply_text не вызывался (нет effective_message)


# ═══════════════════════════════════════════════════════════════
# Наследование (DEBT-007: оба бота — BaseTGBot)
# ═══════════════════════════════════════════════════════════════


class TestBotInheritance:
    def test_telegram_freebuff_bot_is_base(self) -> None:
        from scripts_01.telegram_bot import TelegramFreebuffBot

        assert issubclass(TelegramFreebuffBot, BaseTGBot)
        assert TelegramFreebuffBot.logger.name == "freebuff.telegram_bot"

    def test_scenario_tg_bot_is_base(self) -> None:
        from freebuff_plugin_03.tgbot import ScenarioTGBot

        assert issubclass(ScenarioTGBot, BaseTGBot)
        assert ScenarioTGBot.logger.name == "freebuff.tgbot"

    def test_shared_helpers_available(self) -> None:
        from scripts_01.telegram_bot import TelegramFreebuffBot
        from freebuff_plugin_03.tgbot import ScenarioTGBot

        for cls in (TelegramFreebuffBot, ScenarioTGBot):
            assert hasattr(cls, "build_application")
            assert hasattr(cls, "run_polling")
            assert hasattr(cls, "error_handler")
