"""
hello_world — Демонстрационный плагин для Buffy Plugin API.

Функции:
  - hello: возвращает приветствие
  - echo: возвращает переданный текст
  - log: записывает сообщение в консоль
  - Подписка на system.* события
"""

}
from scripts_01.plugin_api import BasePlugin, PluginMeta, PluginResult


class HelloWorldPlugin(BasePlugin):
    """Плагин, демонстрирующий базовые возможности Plugin API."""

    def __init__(self):
        super().__init__(
            name="hello_world",
            version="1.0.0",
            description="Демонстрационный плагин — приветствие мира и эхо-команда",
        )
        self._greeting_count = 0
        self._events_received: list = []

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
        return ["system.*", "plugin.*"]

    # ── Lifecycle ───────────────────────────────────────────

    def on_load(self):
        self._greeting_count = 0
        self._events_received = []
        print(f"👋 HelloWorld: plugin loaded")

    def on_unload(self):
        print(f"👋 HelloWorld: plugin unloaded (said hello {self._greeting_count} times)")

    def on_enable(self):
        print(f"✅ HelloWorld: plugin enabled, listening to system.* events")

    def on_disable(self):
        print(f"⏸️  HelloWorld: plugin disabled")

    def on_event(self, event):
        """Обработчик событий — просто логирует."""
        self._events_received.append({
            "type": event.type, "data_13": getattr(event, 'data_13', {}),
            "timestamp": getattr(event, 'timestamp', ''),
        ])

    # ── Действия ───────────────────────────────────────────

    def do_hello(self, name: str = "World") -> dict:
        """Возвращает приветствие."""
        self._greeting_count += 1
        return {
            "message": f"Hello, {name}! 🤖",
            "count": self._greeting_count,
            "version": self._version,
        }

    def do_echo(self, text: str = "") -> dict:
        """Эхо — возвращает переданный текст."""
        return {
            "echo": text,
            "length": len(text),
        }

    def do_status(self) -> dict:
        """Статус плагина."""
        return {
            "name": self._name,
            "enabled": self._enabled,
            "greeting_count": self._greeting_count,
            "events_received": len(self._events_received),
            "last_events": self._events_received[-3:] if self._events_received else [],
        }

    def do_log(self, message: str = "") -> dict:
        """Записывает сообщение и возвращает его."""
        print(f"📝 HelloWorld log: {message}")
        return {"logged": True, "message": message}

    def do_reset(self) -> dict:
        """Сбрасывает счётчики."""
        self._greeting_count = 0
        self._events_received = []
        return {"reset": True, "greeting_count": 0}


# Экземпляр плагина (обнаруживается PluginLoader по переменной `plugin`)
plugin = HelloWorldPlugin()
