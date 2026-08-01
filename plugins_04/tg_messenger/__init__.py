"""
tg_messenger — Telegram Messenger Plugin для Buffy.

Функции:
  - send_message: отправка сообщения через Telegram Bot API
  - start_bot / stop_bot: управление фоновым bot listener (scripts_01/telegram_bot.py)
  - status: статус плагина
  - Авто-форвардинг system.*, plugin.*, collab.* событий в Telegram

Конфигурация (из .env):
  TELEGRAM_BOT_TOKEN — токен бота
  ALLOWED_CHAT_IDS — разрешённые chat_id через запятую
"""

import os
import sys
import threading
***REMOVED***

from scripts_01.plugin_api import BasePlugin, PluginMeta, PluginResult

WORKSPACE = Path(__file__).resolve().parent.parent.parent


class TelegramMessengerPlugin(BasePlugin):
    """Отправка сообщений и авто-форвардинг событий в Telegram."""

    def __init__(self):
        super().__init__(
            name="tg_messenger",
            version="1.0.0",
            description="Telegram Messenger — отправка сообщений и авто-форвардинг событий",
        )
        self._bot_token: str = ""
        self._allowed_chat_ids: set = set()
        self._running: bool = False
        self._bot_thread: threading.Thread | None = None
        self._message_queue: list = [***REMOVED***

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self._name,
            version=self._version,
            description=self._description,
            events_subscribed=self.events_subscribed,
        )

    @property
    def events_subscribed(self):
        return ["system.*", "plugin.*", "collab.*"***REMOVED***

    # ── Lifecycle ───────────────────────────────────────────

    def on_load(self):
        """Загружает конфигурацию из .env."""
        self._bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        allowed = os.environ.get("ALLOWED_CHAT_IDS", "")
        ids = set()
        if allowed:
            for cid in allowed.split(","):
                try:
                    ids.add(int(cid.strip()))
                except (ValueError, TypeError):
                    continue
        self._allowed_chat_ids = ids
        print(
            f"📱 tg_messenger: loaded (token={'✅' if self._bot_token else '❌'***REMOVED***)"
        )

    def on_unload(self):
        self._running = False
        self._bot_thread = None

    # ── Действия ───────────────────────────────────────────

    def do_send_message(self, chat_id=None, text: str = "") -> dict:
        """Отправить сообщение в Telegram.

        Args:
            chat_id: ID чата (число или 'default' для первого разрешённого)
            text: текст сообщения

        Returns:
            dict с success и данными ответа Telegram
        """
        if not self._bot_token:
            return {"success": False, "error": "TELEGRAM_BOT_TOKEN not set"***REMOVED***
        try:
            target_id = self._resolve_chat_id(chat_id)
        except (ValueError, TypeError):
            return {"success": False, "error": "Invalid chat_id"***REMOVED***
        if target_id is None:
            return {
                "success": False,
                "error": "No allowed chat IDs configured and no chat_id provided",
            ***REMOVED***
        try:
            import httpx
        except ImportError:
            return {
                "success": False,
                "error": "httpx not installed. Run: pip install httpx",
            ***REMOVED***
        try:
            url = f"https://api.telegram.org/bot{self._bot_token***REMOVED***/sendMessage"
            resp = httpx.post(
                url,
                json={
                    "chat_id": target_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                ***REMOVED***,
                timeout=10,
            )
            result = resp.json()
            if result.get("ok"):
                data = result.get("result", {***REMOVED***)
                return {
                    "success": True, "data_13": {
                        "chat_id": target_id,
                        "message_id": data.get("message_id"),
                    ***REMOVED***,
                ***REMOVED***
            return {
                "success": False,
                "error": result.get("description", "Unknown error"),
            ***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def do_start_bot(self) -> dict:
        """Запускает Telegram bot listener в фоновом потоке.

        Использует scripts_01/telegram_bot.py как подпроцесс.
        """
        if self._running:
            return {"success": True, "data_13": "Bot already running"***REMOVED***
        if not self._bot_token:
            return {"success": False, "error": "TELEGRAM_BOT_TOKEN not set"***REMOVED***
        try:
            self._bot_thread = threading.Thread(
                target=self._run_bot_process, daemon=True, name="tg-messenger-bot"
            )
            self._bot_thread.start()
            self._running = True
            return {"success": True, "data_13": "Bot started in background"***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def do_stop_bot(self) -> dict:
        """Останавливает Telegram bot."""
        self._running = False
        self._bot_thread = None
        return {"success": True, "data_13": "Bot stopped"***REMOVED***

    def do_status(self) -> dict:
        """Статус плагина."""
        return {
            "name": self._name,
            "enabled": self._enabled,
            "bot_running": self._running,
            "token_configured": bool(self._bot_token),
            "allowed_chats": len(self._allowed_chat_ids),
            "queue_size": len(self._message_queue),
        ***REMOVED***

    # ── Внутреннее ─────────────────────────────────────────

    def _run_bot_process(self):
        """Запускает telegram_bot.py как subprocess."""
        try:
            import subprocess

            bot_script = str(Path(WORKSPACE) / "scripts_01" / "telegram_bot.py")
            env = dict(os.environ)
            env["TELEGRAM_BOT_TOKEN"***REMOVED*** = self._bot_token
            proc = subprocess.Popen(
                [sys.executable, bot_script***REMOVED***,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            proc.wait(timeout=300)
            self._running = False
        except subprocess.TimeoutExpired:
            self._running = False
        except Exception as e:
            print(f"📱 tg_messenger: bot process error: {e***REMOVED***")
            self._running = False

    def _resolve_chat_id(self, chat_id):
        """Определяет целевой chat_id из строки или первого разрешённого."""
        try:
            if chat_id is not None and str(chat_id) != "default":
                return int(chat_id)
            return next(iter(self._allowed_chat_ids), None)
        except (ValueError, TypeError):
            return None

    def _format_event(self, event_type: str, data: dict) -> str:
        """Форматирует событие в Telegram-сообщение."""
        if event_type.startswith("system."):
            message = data.get("message", "")
            level = data.get("level", "info")
            icons = {
                "error": "🚨",
                "warn": "⚠️",
                "info": "ℹ️",
                "critical": "🔥",
            ***REMOVED***
            icon = icons.get(level, "ℹ️")
            action = event_type.split(".", 1)[-1***REMOVED***
            return f"{icon***REMOVED*** *System {action***REMOVED***:* {message***REMOVED***"
        if event_type.startswith("plugin."):
            plugin = data.get("plugin", "?")
            action = event_type.split(".")[-1***REMOVED***
            return f"🔌 *Plugin {plugin***REMOVED***.{action***REMOVED***:* "
        if event_type.startswith("collab."):
            action = event_type.split(".")[-1***REMOVED***
            session_id = data.get("session_id", "")[:8***REMOVED***
            participant = data.get("sender") or data.get("participant", "")
            topic = data.get("topic", "")
            return (
                f"💬 *Collab {action***REMOVED***:* "
                f"{participant***REMOVED*** (session={session_id***REMOVED***, topic={topic***REMOVED***)"
            )
        return ""

    def on_event(self, event):
        """Обрабатывает системные события и отправляет в Telegram."""
        if not self._bot_token:
            return
        event_type = getattr(event, "type", "")
        event_data = getattr(event, "data_13", {***REMOVED***) or {***REMOVED***
        message = self._format_event(event_type, event_data)
        if message:
            self._message_queue.append({"text": message, "type": event_type***REMOVED***)
            self._flush_queue()

    def _flush_queue(self):
        """Отправляет накопленные сообщения."""
        sent = 0
        while self._message_queue:
            msg = self._message_queue[0***REMOVED***
            result = self.do_send_message(text=msg["text"***REMOVED***)
            if result.get("success"):
                self._message_queue.pop(0)
                sent += 1
            else:
                break
        return sent


# Экземпляр плагина (обнаруживается PluginLoader по переменной `plugin`)
plugin = TelegramMessengerPlugin()
