"""
Tests for Plugin API — plugin_api.py + plugins/ directory.

Covers:
  - BasePlugin lifecycle (on_load, on_enable, on_disable, on_unload)
  - PluginRegistry (register, enable, disable, unload, list, get)
  - PluginLoader (discover, load, load_all)
  - EventBus integration (subscription, events)
  - Plugin execution (execute, actions)
  - Error handling
  - Edge cases
"""

from __future__ import annotations

import json
import os
import sys
import time
***REMOVED***
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Add workspace root to path for imports
WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from scripts.event_bus import EventBus, Event
from scripts.plugin_api import (
    BasePlugin,
    PluginState,
    PluginMeta,
    PluginManifest,
    PluginEntry,
    PluginResult,
    PluginRegistry,
    PluginLoader,
    create_plugin_registrar,
    PLUGIN_VAR_NAME,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def event_bus():
    return EventBus(db_path=":memory:")


@pytest.fixture
def registry():
    return PluginRegistry()


@pytest.fixture
def registry_with_bus(event_bus):
    return PluginRegistry(event_bus=event_bus)


@pytest.fixture
def mock_tool_registry():
    return MagicMock()


@pytest.fixture
def demo_plugin():
    """Стандартный демо-плагин для тестов."""
    return DemoPlugin()


class DemoPlugin(BasePlugin):
    """Тестовый плагин с известным поведением."""

    def __init__(self):
        super().__init__("demo", "2.0.0", "Test plugin")
        self.load_called = False
        self.unload_called = False
        self.enable_called = False
        self.disable_called = False
        self.events_received: List[Event***REMOVED*** = [***REMOVED***
        self.last_error: Optional[Exception***REMOVED*** = None

    @property
    def events_subscribed(self):
        return ["demo.*", "test.*"***REMOVED***

    @property
    def meta(self):
        return PluginMeta(
            name=self._name,
            version=self._version,
            description=self._description,
            tags=["test", "demo"***REMOVED***,
            events_subscribed=self.events_subscribed,
        )

    def get_tools(self):
        from scripts.tool_runtime import FileTool
        return [FileTool()***REMOVED***

    def on_load(self):
        self.load_called = True

    def on_unload(self):
        self.unload_called = True

    def on_enable(self):
        self.enable_called = True

    def on_disable(self):
        self.disable_called = True

    def on_event(self, event):
        self.events_received.append(event)

    def on_error(self, error: Exception):
        self.last_error = error

    def do_test_action(self, value: str = "default") -> dict:
        return {"action": "test", "value": value, "plugin": self._name***REMOVED***

    def do_echo(self, message: str = "") -> dict:
        return {"echo": message, "length": len(message)***REMOVED***


class FailingPlugin(BasePlugin):
    """Плагин, который падает при загрузке."""

    def __init__(self):
        super().__init__("failing", "1.0.0", "Always fails")

    def on_load(self):
        raise RuntimeError("Intentional load failure")


class SlowPlugin(BasePlugin):
    """Плагин с медленной загрузкой."""

    def __init__(self):
        super().__init__("slow", "1.0.0", "Slow loader")

    def on_load(self):
        time.sleep(0.05)

    def on_enable(self):
        time.sleep(0.05)


# ═══════════════════════════════════════════════════════════════
# BasePlugin Tests
# ═══════════════════════════════════════════════════════════════


class TestBasePlugin:
    def test_init(self, demo_plugin):
        assert demo_plugin.name == "demo"
        assert demo_plugin.version == "2.0.0"
        assert demo_plugin.description == "Test plugin"
        assert not demo_plugin.is_enabled
        assert not demo_plugin.is_loaded

    def test_meta(self, demo_plugin):
        meta = demo_plugin.meta
        assert meta.name == "demo"
        assert meta.version == "2.0.0"
        assert "test" in meta.tags

    def test_events_subscribed(self, demo_plugin):
        assert demo_plugin.events_subscribed == ["demo.*", "test.*"***REMOVED***

    def test_get_tools(self, demo_plugin):
        tools = demo_plugin.get_tools()
        assert len(tools) == 1
        assert tools[0***REMOVED***.meta.name == "file"

    def test_get_commands_default(self, demo_plugin):
        assert demo_plugin.get_commands() == [***REMOVED***

    def test_execute_success(self, demo_plugin):
        result = demo_plugin.execute("test_action", {"value": "hello"***REMOVED***)
        assert result.success
        assert result.data["value"***REMOVED*** == "hello"
        assert result.data["action"***REMOVED*** == "test"
        assert result.plugin_name == "demo"

    def test_execute_unknown_action(self, demo_plugin):
        result = demo_plugin.execute("nonexistent", {***REMOVED***)
        assert not result.success
        assert "Unknown action" in result.error

    def test_execute_with_defaults(self, demo_plugin):
        result = demo_plugin.execute("test_action", {***REMOVED***)
        assert result.success
        assert result.data["value"***REMOVED*** == "default"

    def test_execute_echo(self, demo_plugin):
        result = demo_plugin.execute("echo", {"message": "hello world"***REMOVED***)
        assert result.success
        assert result.data["echo"***REMOVED*** == "hello world"
        assert result.data["length"***REMOVED*** == 11

    def test_on_error_called(self):
        plugin = FailingPlugin()
        with pytest.raises(RuntimeError, match="Intentional load failure"):
            plugin._do_load()
        # on_error был вызван ДО raise (проверяем по last_error)
        assert plugin.last_error is not None
        assert "Intentional load failure" in str(plugin.last_error)


# ═══════════════════════════════════════════════════════════════
# PluginLifecycle Tests
# ═══════════════════════════════════════════════════════════════


class TestPluginLifecycle:
    def test_load_lifecycle(self, registry, demo_plugin):
        entry = registry.register(demo_plugin)
        assert entry.state == PluginState.LOADED
        assert demo_plugin.load_called
        assert demo_plugin.is_loaded
        assert not demo_plugin.is_enabled

    def test_enable_lifecycle(self, registry_with_bus, demo_plugin):
        registry = registry_with_bus
        entry = registry.register(demo_plugin)
        assert entry.state == PluginState.LOADED

        result = registry.enable("demo")
        assert result
        assert demo_plugin.enable_called
        assert demo_plugin.is_enabled
        assert entry.state == PluginState.ENABLED

    def test_disable_lifecycle(self, registry_with_bus, demo_plugin):
        registry = registry_with_bus
        registry.register(demo_plugin)
        registry.enable("demo")
        assert demo_plugin.is_enabled

        result = registry.disable("demo")
        assert result
        assert demo_plugin.disable_called
        assert not demo_plugin.is_enabled
        assert registry.get("demo").state == PluginState.DISABLED

    def test_unload_lifecycle(self, registry, demo_plugin):
        registry.register(demo_plugin)
        assert demo_plugin.load_called

        result = registry.unload("demo")
        assert result
        assert demo_plugin.unload_called
        assert not registry.has("demo")

    def test_full_lifecycle(self, registry_with_bus, demo_plugin):
        """Load → Enable → Disable → Unload"""
        registry = registry_with_bus

        # Load
        registry.register(demo_plugin)
        assert demo_plugin.load_called
        assert not demo_plugin.enable_called

        # Enable
        registry.enable("demo")
        assert demo_plugin.enable_called
        assert demo_plugin.is_enabled

        # Disable
        registry.disable("demo")
        assert demo_plugin.disable_called
        assert not demo_plugin.is_enabled

        # Unload
        registry.unload("demo")
        assert demo_plugin.unload_called
        assert not registry.has("demo")

    def test_enable_all(self, registry_with_bus):
        registry = registry_with_bus
        p1 = DemoPlugin()
        p2 = DemoPlugin()
        p2._name = "demo2"
        registry.register(p1)
        registry.register(p2)

        count = registry.enable_all()
        assert count == 2
        assert p1.is_enabled
        assert p2.is_enabled

    def test_disable_all(self, registry_with_bus):
        registry = registry_with_bus
        p1 = DemoPlugin()
        p2 = DemoPlugin()
        p2._name = "demo2"
        registry.register(p1)
        registry.register(p2)
        registry.enable_all()

        count = registry.disable_all()
        assert count == 2
        assert not p1.is_enabled
        assert not p2.is_enabled

    def test_unload_all(self, registry):
        p1 = DemoPlugin()
        p2 = DemoPlugin()
        p2._name = "demo2"
        registry.register(p1)
        registry.register(p2)

        count = registry.unload_all()
        assert count == 2
        assert not registry.has("demo")
        assert not registry.has("demo2")
        assert p1.unload_called
        assert p2.unload_called


# ═══════════════════════════════════════════════════════════════
# PluginRegistry Tests
# ═══════════════════════════════════════════════════════════════


class TestPluginRegistry:
    def test_register(self, registry, demo_plugin):
        entry = registry.register(demo_plugin)
        assert entry.name == "demo"
        assert entry.state == PluginState.LOADED
        assert entry.instance is demo_plugin

    def test_register_duplicate(self, registry, demo_plugin):
        registry.register(demo_plugin)
        entry2 = registry.register(DemoPlugin())
        # Second register overwrites
        assert registry.get("demo") is entry2

    def test_get_existing(self, registry, demo_plugin):
        registry.register(demo_plugin)
        entry = registry.get("demo")
        assert entry is not None
        assert entry.name == "demo"

    def test_get_nonexistent(self, registry):
        entry = registry.get("nonexistent")
        assert entry is None

    def test_has(self, registry, demo_plugin):
        assert not registry.has("demo")
        registry.register(demo_plugin)
        assert registry.has("demo")
        assert not registry.has("other")

    def test_list_all(self, registry):
        registry.register(DemoPlugin())
        p2 = DemoPlugin()
        p2._name = "demo2"
        registry.register(p2)

        entries = registry.list()
        assert len(entries) == 2

    def test_list_by_state(self, registry, demo_plugin):
        registry.register(demo_plugin)
        loaded = registry.list(state=PluginState.LOADED)
        assert len(loaded) == 1
        assert loaded[0***REMOVED***.name == "demo"

        enabled = registry.list(state=PluginState.ENABLED)
        assert len(enabled) == 0

    def test_count(self, registry):
        assert registry.count() == 0
        registry.register(DemoPlugin())
        registry.register(DemoPlugin())
        # Second has same name, overwrites
        assert registry.count() == 1

    def test_execute_plugin_action(self, registry, demo_plugin):
        registry.register(demo_plugin)
        result = registry.execute("demo", "test_action", {"value": "registry_test"***REMOVED***)
        assert result.success
        assert result.data["value"***REMOVED*** == "registry_test"

    def test_execute_nonexistent_plugin(self, registry):
        result = registry.execute("ghost", "action", {***REMOVED***)
        assert not result.success
        assert "not found" in result.error

    def test_get_state(self, registry):
        registry.register(DemoPlugin())
        state = registry.get_state()
        assert state["total"***REMOVED*** == 1
        assert state["loaded"***REMOVED*** == 1
        assert state["enabled"***REMOVED*** == 0
        assert state["disabled"***REMOVED*** == 0
        assert state["error"***REMOVED*** == 0
        assert len(state["plugins"***REMOVED***) == 1

    def test_enable_nonexistent(self, registry):
        assert not registry.enable("ghost")

    def test_disable_nonexistent(self, registry):
        assert not registry.disable("ghost")

    def test_enable_already_enabled(self, registry_with_bus, demo_plugin):
        registry = registry_with_bus
        registry.register(demo_plugin)
        registry.enable("demo")
        assert registry.enable("demo")  # should still return True

    def test_disable_already_disabled(self, registry, demo_plugin):
        registry.register(demo_plugin)
        assert registry.disable("demo") is False  # can't disable if not enabled

    def test_enable_without_event_bus(self, registry, demo_plugin):
        """Плагин включается и без EventBus."""
        registry.register(demo_plugin)
        assert registry.enable("demo")
        assert demo_plugin.is_enabled

    def test_unload_removes_tools(self, registry, mock_tool_registry):
        reg = PluginRegistry(tool_registry=mock_tool_registry)
        reg.register(DemoPlugin())
        reg.enable("demo")
        reg.unload("demo")
        # ToolRegistry.unregister was called for FileTool
        mock_tool_registry.unregister.assert_called_once_with("file")

    def test_add_error_entry(self, registry):
        registry._add_error_entry("broken", Path("/tmp"), "Test error")
        entry = registry.get("broken")
        assert entry is not None
        assert entry.state == PluginState.ERROR
        assert entry.error == "Test error"


# ═══════════════════════════════════════════════════════════════
# EventBus Integration Tests
# ═══════════════════════════════════════════════════════════════


class TestEventBusIntegration:
    def test_plugin_subscribes_to_events(self, event_bus):
        registry = PluginRegistry(event_bus=event_bus)
        demo = DemoPlugin()
        registry.register(demo)
        registry.enable("demo")

        # Публикуем событие, на которое подписан плагин
        event_bus.publish(Event("demo.test", {"key": "value"***REMOVED***, source="test"))
        event_bus.publish(Event("test.hello", {***REMOVED***, source="test"))

        assert len(demo.events_received) == 2
        assert demo.events_received[0***REMOVED***.type == "demo.test"
        assert demo.events_received[0***REMOVED***.data["key"***REMOVED*** == "value"

    def test_plugin_receives_only_subscribed_events(self, event_bus):
        registry = PluginRegistry(event_bus=event_bus)
        demo = DemoPlugin()
        registry.register(demo)
        registry.enable("demo")

        # Событие, на которое НЕ подписан
        event_bus.publish(Event("other.event", {***REMOVED***, source="test"))

        assert len(demo.events_received) == 0

    def test_plugin_stops_receiving_after_disable(self, event_bus):
        registry = PluginRegistry(event_bus=event_bus)
        demo = DemoPlugin()
        registry.register(demo)
        registry.enable("demo")
        registry.disable("demo")

        event_bus.publish(Event("demo.test", {***REMOVED***, source="test"))

        assert len(demo.events_received) == 0

    def test_plugin_enabled_event_published(self, event_bus):
        registry = PluginRegistry(event_bus=event_bus)
        demo = DemoPlugin()
        registry.register(demo)

        events_log = [***REMOVED***
        event_bus.subscribe("plugin.enabled", lambda e: events_log.append(e))

        registry.enable("demo")

        assert len(events_log) == 1
        assert events_log[0***REMOVED***.data["plugin"***REMOVED*** == "demo"

    def test_plugin_disabled_event_published(self, event_bus):
        registry = PluginRegistry(event_bus=event_bus)
        demo = DemoPlugin()
        registry.register(demo)
        registry.enable("demo")

        events_log = [***REMOVED***
        event_bus.subscribe("plugin.disabled", lambda e: events_log.append(e))

        registry.disable("demo")

        assert len(events_log) == 1
        assert events_log[0***REMOVED***.data["plugin"***REMOVED*** == "demo"


# ═══════════════════════════════════════════════════════════════
# PluginLoader Tests
# ═══════════════════════════════════════════════════════════════


class TestPluginLoader:
    def test_discover_plugins(self):
        """Проверяет, что PluginLoader находит плагины в plugins/"""
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        discovered = loader.discover(str(WORKSPACE / "plugins"))
        assert len(discovered) >= 1
        # Должен найти hello_world
        names = [p.name for p in discovered***REMOVED***
        assert "hello_world" in names

    def test_load_existing_plugin(self):
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        plugin_path = WORKSPACE / "plugins" / "hello_world"
        entry = loader.load(plugin_path)
        assert entry is not None
        assert entry.name == "hello_world"
        assert entry.state == PluginState.LOADED
        assert entry.instance is not None

    def test_load_nonexistent_plugin(self):
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        entry = loader.load(Path("/nonexistent/plugin"))
        assert entry is None

    def test_load_all(self):
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        entries = loader.load_all(str(WORKSPACE / "plugins"))
        assert len(entries) >= 1
        names = [e.name for e in entries***REMOVED***
        assert "hello_world" in names

    def test_loaded_plugin_can_be_enabled(self, event_bus):
        """Интеграционный тест: загрузить плагин → активировать → выполнить действие."""
        registry = PluginRegistry(event_bus=event_bus)
        loader = PluginLoader(registry)
        entries = loader.load_all(str(WORKSPACE / "plugins"))

        # Активируем hello_world
        assert registry.enable("hello_world")

        # Выполняем действие
        result = registry.execute("hello_world", "hello", {"name": "Buffy"***REMOVED***)
        assert result.success
        assert "Hello, Buffy" in result.data["message"***REMOVED***
        assert result.data["count"***REMOVED*** == 1

    def test_loaded_plugin_echo_action(self, event_bus):
        registry = PluginRegistry(event_bus=event_bus)
        loader = PluginLoader(registry)
        loader.load_all(str(WORKSPACE / "plugins"))
        registry.enable("hello_world")

        result = registry.execute("hello_world", "echo", {"text": "test echo"***REMOVED***)
        assert result.success
        assert result.data["echo"***REMOVED*** == "test echo"

    def test_hello_world_receives_system_events(self, event_bus):
        registry = PluginRegistry(event_bus=event_bus)
        loader = PluginLoader(registry)
        loader.load_all(str(WORKSPACE / "plugins"))
        registry.enable("hello_world")

        # После enable плагин уже получил plugin.enabled (через plugin.*)
        # Публикуем ещё 2 события
        event_bus.publish(Event("system.startup", {"mode": "test"***REMOVED***, source="pytest"))
        event_bus.publish(Event("plugin.loaded", {"plugin": "test"***REMOVED***, source="pytest"))

        # Проверяем статус: 1 (plugin.enabled) + 2 новых = 3
        result = registry.execute("hello_world", "status", {***REMOVED***)
        assert result.success
        assert result.data["events_received"***REMOVED*** == 3

    def test_loaded_plugin_has_manifest(self):
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        plugin_path = WORKSPACE / "plugins" / "hello_world"
        entry = loader.load(plugin_path)
        assert entry is not None
        assert entry.manifest is not None
        assert entry.manifest.version == "1.0.0"
        assert entry.manifest.author == "Buffy"
        assert "demo" in entry.manifest.tags


# ═══════════════════════════════════════════════════════════════
# PluginManifest Tests
# ═══════════════════════════════════════════════════════════════


class TestPluginManifest:
    def test_from_dict_full(self):
        data = {
            "name": "test",
            "version": "2.0.0",
            "description": "Test manifest",
            "author": "Tester",
            "tags": ["test", "demo"***REMOVED***,
            "events_subscribed": ["test.*"***REMOVED***,
            "homepage": "https://example.com",
            "license": "MIT",
        ***REMOVED***
        m = PluginManifest.from_dict(data)
        assert m.name == "test"
        assert m.version == "2.0.0"
        assert m.description == "Test manifest"
        assert m.author == "Tester"
        assert m.tags == ["test", "demo"***REMOVED***
        assert m.events_subscribed == ["test.*"***REMOVED***
        assert m.homepage == "https://example.com"

    def test_from_dict_empty(self):
        m = PluginManifest.from_dict({***REMOVED***)
        assert m.name == "unknown"
        assert m.version == "1.0.0"
        assert m.description == ""

    def test_to_dict(self):
        m = PluginManifest(name="my_plugin", version="1.5.0", tags=["ai", "tools"***REMOVED***)
        d = m.to_dict()
        assert d["name"***REMOVED*** == "my_plugin"
        assert d["version"***REMOVED*** == "1.5.0"
        assert d["tags"***REMOVED*** == ["ai", "tools"***REMOVED***


# ═══════════════════════════════════════════════════════════════
# PluginResult Tests
# ═══════════════════════════════════════════════════════════════


class TestPluginResult:
    def test_success_result(self):
        r = PluginResult(success=True, data="ok", plugin_name="test")
        assert r.success
        assert r.data == "ok"
        assert r.plugin_name == "test"

    def test_error_result(self):
        r = PluginResult(success=False, error="fail", plugin_name="test")
        assert not r.success
        assert r.error == "fail"


# ═══════════════════════════════════════════════════════════════
# Edge Cases & Error Handling
# ═══════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_plugin_without_events(self):
        """Плагин без подписки на события работает нормально."""
        class SilentPlugin(BasePlugin):
            def __init__(self):
                super().__init__("silent", "1.0.0", "Silent")

        registry = PluginRegistry()
        plugin = SilentPlugin()
        entry = registry.register(plugin)
        assert entry.state == PluginState.LOADED
        assert registry.enable("silent")  # enable without events = ok

    def test_plugin_without_tools(self):
        """Плагин без инструментов работает нормально."""
        class SimplePlugin(BasePlugin):
            def __init__(self):
                super().__init__("simple", "1.0.0", "Simple")

        registry = PluginRegistry()
        plugin = SimplePlugin()
        registry.register(plugin)
        assert registry.enable("simple")

    def test_failing_plugin_on_enable(self):
        """Плагин, падающий при on_enable, переходит в ERROR."""
        class BrokenPlugin(BasePlugin):
            def on_enable(self):
                raise RuntimeError("Enable failed")

        registry = PluginRegistry()
        plugin = BrokenPlugin("broken")
        registry.register(plugin)
        assert not registry.enable("broken")
        entry = registry.get("broken")
        assert entry.state == PluginState.ERROR
        assert "Enable failed" in entry.error

    def test_re_register_with_same_name(self, registry):
        """Повторная регистрация перезаписывает плагин."""
        p1 = DemoPlugin()
        p1._name = "same"
        p2 = DemoPlugin()
        p2._name = "same"

        registry.register(p1)
        assert p1.load_called

        registry.register(p2)
        # p1.unload не вызван (нет прямой отчистки при перезаписи)
        # но реестр теперь содержит p2
        entry = registry.get("same")
        assert entry.instance is p2

    def test_loading_plugin_from_subdir(self, tmp_path):
        """Загрузка плагина из временной директории."""
        # Создаём временный плагин
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        init_file = plugin_dir / "__init__.py"
        init_file.write_text("""
from scripts.plugin_api import BasePlugin

class TempPlugin(BasePlugin):
    def __init__(self):
        super().__init__("temp_plugin", "0.1.0", "Temp plugin for testing")
    def on_load(self):
        self._loaded = True

plugin = TempPlugin()
""")
        manifest_file = plugin_dir / "manifest.json"
        manifest_file.write_text(json.dumps({
            "name": "temp_plugin",
            "version": "0.1.0",
        ***REMOVED***))

        registry = PluginRegistry()
        loader = PluginLoader(registry)
        entry = loader.load(plugin_dir)
        assert entry is not None
        assert entry.name == "temp_plugin"
        assert entry.manifest is not None
        assert entry.manifest.version == "0.1.0"
        assert entry.instance is not None

    def test_plugin_state_machine(self, registry_with_bus):
        """Проверяет, что плагин проходит правильные состояния."""
        registry = registry_with_bus
        p = DemoPlugin()

        # DISCOVERED → нет, сразу LOADED после register
        registry.register(p)
        assert registry.get("demo").state == PluginState.LOADED

        # LOADED → ENABLED
        registry.enable("demo")
        assert registry.get("demo").state == PluginState.ENABLED

        # ENABLED → DISABLED
        registry.disable("demo")
        assert registry.get("demo").state == PluginState.DISABLED

        # DISABLED → ENABLED (снова)
        registry.enable("demo")
        assert registry.get("demo").state == PluginState.ENABLED

    def test_multiple_plugins_independent(self, event_bus):
        """Несколько плагинов работают независимо."""
        registry = PluginRegistry(event_bus=event_bus)

        p1 = DemoPlugin()
        p2 = DemoPlugin()
        p2._name = "demo2"
        registry.register(p1)
        registry.register(p2)
        registry.enable("demo")
        registry.enable("demo2")

        # Оба получают события
        event_bus.publish(Event("demo.test", {***REMOVED***, source="test"))
        assert len(p1.events_received) == 1
        assert len(p2.events_received) == 1

        # Отключаем один
        registry.disable("demo")
        event_bus.publish(Event("demo.test", {***REMOVED***, source="test"))
        assert len(p1.events_received) == 1  # больше не получает
        assert len(p2.events_received) == 2  # продолжает получать

    def test_create_plugin_registrar(self, event_bus):
        """create_plugin_registrar работает и загружает плагины."""
        from scripts.tool_runtime import ToolRegistry

        tool_registry = ToolRegistry()
        loader, registry = create_plugin_registrar(
            event_bus=event_bus,
            tool_registry=tool_registry,
            plugins_dir=str(WORKSPACE / "plugins"),
        )

        assert isinstance(loader, PluginLoader)
        assert isinstance(registry, PluginRegistry)
        assert registry.count() >= 1
        assert registry.has("hello_world")


# ═══════════════════════════════════════════════════════════════
# Create plugin registrar integration
# ═══════════════════════════════════════════════════════════════


class TestPluginRegistrar:
    def test_hello_world_status(self, event_bus):
        """Интеграционный тест полного цикла: загрузка → enable → execute."""
        registry = PluginRegistry(event_bus=event_bus)
        loader = PluginLoader(registry)
        loader.load_all(str(WORKSPACE / "plugins"))
        registry.enable("hello_world")

        # Status
        result = registry.execute("hello_world", "status", {***REMOVED***)
        assert result.success
        assert result.data["name"***REMOVED*** == "hello_world"
        assert result.data["enabled"***REMOVED*** is True
        assert result.data["greeting_count"***REMOVED*** == 0

        # Hello несколько раз
        registry.execute("hello_world", "hello", {"name": "Alice"***REMOVED***)
        registry.execute("hello_world", "hello", {"name": "Bob"***REMOVED***)
        result = registry.execute("hello_world", "hello", {"name": "Charlie"***REMOVED***)
        assert result.data["count"***REMOVED*** == 3

        # Reset
        registry.execute("hello_world", "reset", {***REMOVED***)
        result = registry.execute("hello_world", "status", {***REMOVED***)
        assert result.data["greeting_count"***REMOVED*** == 0

    def test_event_subscription_hello_world(self, event_bus):
        """Проверяет, что hello_world получает system.* события."""
        registry = PluginRegistry(event_bus=event_bus)
        loader = PluginLoader(registry)
        loader.load_all(str(WORKSPACE / "plugins"))
        registry.enable("hello_world")

        # Отправляем system события
        for i in range(3):
            event_bus.publish(Event(f"system.event_{i***REMOVED***", {"n": i***REMOVED***, source="test"))

        # Проверяем через статус
        result = registry.execute("hello_world", "status", {***REMOVED***)
        assert result.success
        assert result.data["events_received"***REMOVED*** >= 3

    def test_create_registrar_integration(self, event_bus):
        """create_plugin_registrar с полной интеграцией."""
        from scripts.tool_runtime import ToolRegistry

        tool_registry = ToolRegistry()
        loader, registry = create_plugin_registrar(
            event_bus=event_bus,
            tool_registry=tool_registry,
            plugins_dir=str(WORKSPACE / "plugins"),
        )

        # Включаем hello_world
        registry.enable("hello_world")

        # Проверяем выполнение
        result = registry.execute("hello_world", "echo", {"text": "integration works"***REMOVED***)
        assert result.success
        assert result.data["echo"***REMOVED*** == "integration works"
