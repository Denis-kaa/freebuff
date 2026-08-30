"""BaseTGBot — общий предок Telegram-ботов Freebuff (DEBT-2026-07-31-007).

Делит между двумя ботами общую инфраструктуру, которая раньше дублировалась:

  - `scripts_01/telegram_bot.py` (`TelegramFreebuffBot`) — бот уведомлений/управления
  - `freebuff_plugin_03/tgbot.py` (`ScenarioTGBot`) — сценарный бот (Scenario Engine)

Общие части (вынесены сюда): загрузка `.env`, разрешение токена,
построение python-telegram-bot Application, polling-цикл с управлением
event loop и общий error handler. Боты остаются в своих слоях
(scripts = уведомления, freebuff_plugin = сценарии) и наследуют этот класс.

Использование:
    class MyBot(BaseTGBot):
        logger = logging.getLogger("freebuff.mybot")
        # бот-специфичная логика...

    bot = MyBot(workspace)
    app = bot.build_application()
    # app.add_handler(...)
    raise SystemExit(bot.run_polling(app))
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
}
from typing import Any

logger = logging.getLogger("freebuff.tgbot_base")


def load_dotenv(path: Path) -> None:
    """Load a simple KEY=VALUE .env file, skipping comments and blanks.

    Values are set via `os.environ.setdefault` — существующие переменные
    окружения не перезаписываются.
    """
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            os.environ.setdefault(key, value)


class BaseTGBot:
    """Общий Telegram-предок: токен, приложение, polling, обработка ошибок.

    Логирование через классовый атрибут `logger` — подклассы переопределяют
    его на свой логгер (паттерн: `logger = logging.getLogger("...")`).
    """

    logger = logging.getLogger("freebuff.tgbot_base")

    def __init__(self, workspace: str | Path | None = None) -> None:
        self.workspace = Path(
            workspace
            or os.environ.get(
                "FREEBUFF_ROOT",
                str(Path(__file__).resolve().parent.parent),
            )
        )
        load_dotenv(self.workspace / ".env")
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

    def build_application(self) -> Any:
        """Собрать python-telegram-bot Application из self.token.

        Raises RuntimeError, если токен не задан (до обращения к Bot API).
        """
        if not self.token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN не задан. "
                "Получи токен у @BotFather и добавь его в .env или окружение."
            )
        from telegram.ext import ApplicationBuilder

        return ApplicationBuilder().token(self.token).build()

    async def error_handler(self, update: object, context: Any) -> None:
        """Общий обработчик ошибок: лог + уведомление пользователя (если можно).

        Не падает сам по себе: reply оборачивается в try/except, т.к. ошибка
        может быть вызвана недоступностью сети/Telegram.
        """
        self.logger.error("Exception while handling an update:", exc_info=context.error)
        from telegram import Update

        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ Произошла ошибка при обработке сообщения. Попробуй ещё раз."
                )
            except Exception:
                pass

    def run_polling(self, app: Any) -> int:
        """Запустить polling с управлением event loop; вернуть exit-код.

        Возвращает 0 при штатной остановке (в т.ч. Ctrl+C) и 1 при сбое
        polling — единый контракт для main() обоих ботов.
        """
        # Python 3.12+ требует явного event loop в главном потоке
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            app.run_polling()
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user.")
        except Exception as exc:
            self.logger.exception("Bot polling failed")
            print(f"❌ Bot polling failed: {exc}", file=sys.stderr)
            return 1
        finally:
            try:
                loop.close()
            except Exception:
                pass
        return 0
