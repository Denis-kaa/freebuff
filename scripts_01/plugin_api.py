#!/usr/bin/env python3
"""
plugin_api.py — Plugin API для Buffy Project.

Событийно-ориентированная плагинная архитектура. Плагины — это
самостоятельные Python-пакеты в директории plugins_04/, которые могут:
  - Подписываться на события EventBus
  - Регистрировать инструменты в ToolRegistry
  - Добавлять CLI-команды
  - Иметь собственное состояние и lifecycle

Архитектура:
  PluginLoader
  ├── discover()        — сканирует plugins_04/ на наличие плагинов
  ├── load(name)        — загружает плагин через importlib
  └── load_all()        — загружает все обнаруженные

  PluginRegistry
  ├── register(plugin)  — регистрирует загруженный плагин
  ├── enable(name)      — активирует плагин (on_load + subscribe)
  ├── disable(name)     — деактивирует (on_unload + unsubscribe)
  └── execute(name)     — выполнить действие плагина

Жизненный цикл плагина:
  DISCOVERED → LOADED → ENABLED ↔ DISABLED
                          ↓
                        ERROR

Использование:
    from scripts_01.plugin_api import PluginRegistry, PluginLoader

    registry = PluginRegistry(event_bus=bus, tool_registry=tools)
    loader = PluginLoader(registry)
    loader.load_all("plugins_04/")
    registry.enable_all()
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import os
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

WORKSPACE = Path(__file__).resolve().parent.parent
DEFAULT_PLUGINS_DIR = WORKSPACE / "plugins_04"
PLUGIN_VAR_NAME = "plugin"  # имя переменной в __init__.py плагина


# ═══════════════════════════════════════════════════════════════
# Enums & Types
# ═══════════════════════════════════════════════════════════════


class PluginState(Enum):
    """Состояние плагина в жизненном цикле."""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginMeta:
    """Метаданные плагина."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    events_subscribed: List[str] = field(default_factory=list)
    tools_registered: List[str] = field(default_factory=list)
    homepage: str = ""
    license: str = "MIT"


@dataclass
class PluginManifest:
    """manifest.json плагина — статические метаданные."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    events_subscribed: List[str] = field(default_factory=list)
    python_version: str = ">=3.10"
    homepage: str = ""
    license: str = "MIT"

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        """Создаёт манифест из словаря (из JSON)."""
        return cls(
            name=data.get("name", "unknown"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            dependencies=data.get("dependencies", []),
            tags=data.get("tags", []),
            events_subscribed=data.get("events_subscribed", []),
            python_version=data.get("python_version", ">=3.10"),
            homepage=data.get("homepage", ""),
            license=data.get("license", "MIT"),
        )

    def to_dict(self) -> dict:
        """Сериализует в словарь (для JSON)."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "events_subscribed": self.events_subscribed,
            "python_version": self.python_version,
            "homepage": self.homepage,
            "license": self.license,
        }


@dataclass
class PluginEntry:
    """Запись о плагине в реестре."""
    name: str
    path: Path
    state: PluginState = PluginState.DISCOVERED
    meta: Optional[PluginMeta] = None
    manifest: Optional[PluginManifest] = None
    instance: Optional["BasePlugin"] = None
    module: Any = None
    subscriptions: List[Any] = field(default_factory=list)
    error: Optional[str] = None
    loaded_at: Optional[str] = None
    enabled_at: Optional[str] = None


@dataclass
class PluginResult:
    """Результат выполнения действия плагина."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    plugin_name: str = ""


# ═══════════════════════════════════════════════════════════════
# BasePlugin
# ═══════════════════════════════════════════════════════════════


class BasePlugin(ABC):
    """Абстрактный базовый класс для всех плагинов.

    Жизненный цикл:
      1. __init__() — конструктор, задаёт имя и метаданные
      2. on_load() — вызывается при загрузке (инициализация ресурсов)
      3. on_enable() — вызывается при активации (подписка на события)
      4. on_event(event) — обработка событий EventBus
      5. on_disable() — вызывается при деактивации
      6. on_unload() — вызывается при выгрузке

    Дополнительные возможности:
      - get_tools() — вернуть список BaseTool для регистрации в ToolRuntime
      - get_commands() — вернуть список CLI-команд
      - execute(action, params) — выполнить действие плагина
    """

    def __init__(self, name: str = "", version: str = "1.0.0", description: str = ""):
        self._name = name or self.__class__.__name__.lower()
        self._version = version
        self._description = description
        self._enabled = False
        self._loaded = False
        self._event_bus: Any = None
        self._tool_registry: Any = None
        self._subscriptions: List[Any] = []
        self._config: Dict[str, Any] = {}
        self.last_error: Optional[Exception] = None

    # ── Свойства ────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def description(self) -> str:
        return self._description

    @property
    def meta(self) -> PluginMeta:
        """Метаданные плагина. Переопределите для кастомных метаданных."""
        return PluginMeta(
            name=self._name,
            version=self._version,
            description=self._description,
            events_subscribed=self.events_subscribed,
            tools_registered=[t.meta.name for t in self.get_tools()],
        )

    @property
    def events_subscribed(self) -> List[str]:
        """Какие события EventBus слушает плагин. Переопределите."""
        return []

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    # ── Lifecycle Hooks ─────────────────────────────────────

    def on_load(self) -> None:
        """Вызывается при загрузке плагина.

        Здесь плагин инициализирует ресурсы: открывает файлы,
        создаёт соединения, загружает конфигурацию.
        """
        pass

    def on_unload(self) -> None:
        """Вызывается при выгрузке плагина.

        Здесь плагин освобождает ресурсы: закрывает соединения,
        сохраняет состояние.
        """
        pass

    def on_enable(self) -> None:
        """Вызывается при активации плагина.

        Здесь плагин начинает активную работу.
        """
        pass

    def on_disable(self) -> None:
        """Вызывается при деактивации плагина.

        Здесь плагин останавливает активную работу.
        """
        pass

    def on_event(self, event: Any) -> None:
        """Обработчик событий EventBus.

        Срабатывает для всех событий, на которые подписан плагин
        (events_subscribed). Переопределите для кастомной логики.

        Args:
            event: объект события (Event из event_bus)
        """
        pass

    def on_error(self, error: Exception) -> None:
        """Вызывается при ошибке в lifecycle плагина."""
        self.last_error = error
        print(f"⚠️ Plugin '{self._name}' error: {error}")

    # ── Инструменты ─────────────────────────────────────────

    def get_tools(self) -> List[Any]:
        """Возвращает список инструментов (BaseTool) для регистрации.

        По умолчанию пустой список. Переопределите, если плагин
        предоставляет инструменты.
        """
        return []

    def get_commands(self) -> List[Dict[str, Any]]:
        """Возвращает список CLI-команд плагина.

        Каждая команда — словарь с ключами:
          name, description, handler, args (опционально)

        По умолчанию пустой список.
        """
        return []

    # ── Выполнение ──────────────────────────────────────────

    def execute(self, action: str, params: Dict[str, Any]) -> PluginResult:
        """Выполнить действие плагина.

        Args:
            action: название действия (строка)
            params: параметры действия

        Returns:
            PluginResult

        По умолчанию вызывает метод с именем action, если он существует.
        Переопределите для кастомной логики.
        """
        handler = getattr(self, f"do_{action}", None)
        if handler is None:
            return PluginResult(
                success=False,
                error=f"Unknown action: {action}",
                plugin_name=self._name,
            )
        try:
            start = time.time()
            data = handler(**params)
            duration_ms = (time.time() - start) * 1000
            return PluginResult(
                success=True,
                data=data,
                duration_ms=duration_ms,
                plugin_name=self._name,
            )
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return PluginResult(
                success=False,
                error=str(e),
                duration_ms=duration_ms,
                plugin_name=self._name,
            )

    # ── PluginRegistry API (вызываются реестром) ────────────

    def _set_event_bus(self, bus: Any) -> None:
        self._event_bus = bus

    def _set_tool_registry(self, registry: Any) -> None:
        self._tool_registry = registry

    def _set_config(self, config: Dict[str, Any]) -> None:
        self._config = config

    def _do_load(self) -> None:
        try:
            self.on_load()
            self._loaded = True
        except Exception as e:
            self.on_error(e)
            raise

    def _do_unload(self) -> None:
        try:
            # Сначала отключаем, если включён
            if self._enabled:
                self._do_disable()
            self.on_unload()
            self._loaded = False
        except Exception as e:
            self.on_error(e)
            raise

    def _do_enable(self) -> List[Any]:
        """Активирует плагин: подписывается на события, регистрирует инструменты.

        Returns:
            Список Subscription объектов (для отписки)

        Note:
            Если on_enable() вызывает exception, ВСЕ подписки
            отзываются (rollback), чтобы не было частичного состояния.
        """
        subscriptions: List[Any] = []
        try:
            # Подписка на события через EventBus
            if self._event_bus and self.events_subscribed:
                for event_type in self.events_subscribed:
                    sub = self._event_bus.subscribe(event_type, self.on_event)
                    subscriptions.append(sub)

            # Регистрация инструментов в ToolRegistry
            if self._tool_registry:
                for tool in self.get_tools():
                    try:
                        self._tool_registry.register(tool)
                    except Exception as e:
                        print(f"⚠️ Plugin '{self._name}': tool registration error: {e}")

            self.on_enable()
            self._enabled = True
            self._subscriptions = subscriptions
        except Exception as e:
            # Rollback: отзываем все подписки, если on_enable() упал
            if self._event_bus:
                for sub in subscriptions:
                    try:
                        self._event_bus.unsubscribe(sub)
                    except Exception:
                        pass
            self.on_error(e)
            raise

        return subscriptions

    def _do_disable(self) -> None:
        try:
            # Отписка от событий
            if self._event_bus:
                for sub in self._subscriptions:
                    try:
                        self._event_bus.unsubscribe(sub)
                    except Exception:
                        pass
            self._subscriptions.clear()

            self.on_disable()
            self._enabled = False
        except Exception as e:
            self.on_error(e)
            raise


# ═══════════════════════════════════════════════════════════════
# PluginLoader
# ═══════════════════════════════════════════════════════════════


class PluginLoader:
    """Загрузчик плагинов из файловой системы.

    Сканирует директорию plugins_04/, находит поддиректории с
    __init__.py, загружает их через importlib и передаёт
    в PluginRegistry.
    """

    def __init__(self, registry: "PluginRegistry"):
        self._registry = registry
        self._loaded_paths: Set[str] = set()

    def discover(self, plugins_dir: str | Path = "") -> List[Path]:
        """Сканирует директорию на наличие плагинов.

        Args:
            plugins_dir: путь к директории с плагинами

        Returns:
            Список путей к найденным плагинам
        """
        plugins_path = Path(plugins_dir) if plugins_dir else DEFAULT_PLUGINS_DIR
        if not plugins_path.exists():
            return []

        discovered: List[Path] = []
        for entry in sorted(plugins_path.iterdir()):
            if not entry.is_dir():
                continue
            # Плагин — это поддиректория с __init__.py
            init_file = entry / "__init__.py"
            if not init_file.exists():
                continue
            # Пропускаем служебные директории
            if entry.name.startswith("__") or entry.name.startswith("."):
                continue
            discovered.append(entry)

        return discovered

    def load(self, plugin_path: Path) -> Optional[PluginEntry]:
        """Загружает один плагин из директории.

        1. Читает manifest.json (если есть)
        2. Загружает модуль через importlib
        3. Извлекает экземпляр BasePlugin (переменная 'plugin')
        4. Регистрирует в PluginRegistry

        Args:
            plugin_path: путь к директории плагина

        Returns:
            PluginEntry или None при ошибке
        """
        plugin_name = plugin_path.name
        init_file = plugin_path / "__init__.py"
        manifest_file = plugin_path / "manifest.json"

        if str(plugin_path) in self._loaded_paths:
            return self._registry.get(plugin_name)

        try:
            # 1. Читаем manifest.json
            manifest = None
            if manifest_file.exists():
                try:
                    data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    manifest = PluginManifest.from_dict(data)
                except (json.JSONDecodeError, Exception) as e:
                    print(f"⚠️ Plugin '{plugin_name}': invalid manifest.json: {e}")

            # 2. Загружаем модуль
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_name}",
                str(init_file),
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load spec for {plugin_name}")

            module = importlib.util.module_from_spec(spec)
            # Добавляем директорию плагина в sys.path для относительных импортов
            plugin_dir = str(plugin_path.parent)
            if plugin_dir not in sys.path:
                sys.path.insert(0, plugin_dir)

            spec.loader.exec_module(module)

            # 3. Извлекаем экземпляр плагина
            instance = getattr(module, PLUGIN_VAR_NAME, None)
            if instance is None:
                # Ищем первый подкласс BasePlugin в модуле
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and issubclass(obj, BasePlugin)
                            and obj is not BasePlugin):
                        instance = obj()
                        break

            if instance is None:
                raise ValueError(
                    f"Plugin '{plugin_name}' has no '{PLUGIN_VAR_NAME}' "
                    f"variable and no BasePlugin subclass"
                )

            if not isinstance(instance, BasePlugin):
                raise TypeError(
                    f"Plugin '{plugin_name}': '{PLUGIN_VAR_NAME}' is not a BasePlugin instance"
                )

            # 4. Регистрируем в реестре
            entry = self._registry.register(
                instance=instance,
                path=plugin_path,
                manifest=manifest,
            )

            # 5. Правило 9: проверяем контракт плагина (warning, не блокирует)
            try:
                from scripts_01.plugin_contract import (
                    format_violations,
                    validate_plugin_entry,
                )
                violations = validate_plugin_entry(entry)
                if violations:
                    print(format_violations(plugin_name, violations))
            except Exception as e:
                print(f"⚠️ Plugin '{plugin_name}': contract check error: {e}")

            self._loaded_paths.add(str(plugin_path))
            return entry

        except Exception as e:
            error_msg = f"Failed to load plugin '{plugin_name}': {e}"
            print(f"⚠️ {error_msg}")
            # Регистрируем как ошибочный
            self._registry._add_error_entry(plugin_name, plugin_path, str(e))
            return None

    def load_all(self, plugins_dir: str | Path = "") -> List[PluginEntry]:
        """Загружает все найденные плагины.

        Args:
            plugins_dir: путь к директории с плагинами

        Returns:
            Список загруженных PluginEntry
        """
        discovered = self.discover(plugins_dir)
        entries: List[PluginEntry] = []
        for path in discovered:
            entry = self.load(path)
            if entry:
                entries.append(entry)
        return entries


# ═══════════════════════════════════════════════════════════════
# PluginRegistry
# ═══════════════════════════════════════════════════════════════


class PluginRegistry:
    """Реестр плагинов — управляет жизненным циклом плагинов.

    Thread-safe реестр с полным lifecycle management:
      DISCOVERED → LOADED → ENABLED ↔ DISABLED
                              ↓
                            ERROR
    """

    def __init__(
        self,
        event_bus: Any = None,
        tool_registry: Any = None,
    ):
        self._event_bus = event_bus
        self._tool_registry = tool_registry
        self._lock = threading.Lock()
        self._plugins: Dict[str, PluginEntry] = {}  # name → entry

    # ── Регистрация ─────────────────────────────────────────

    def register(
        self,
        instance: BasePlugin,
        path: Optional[Path] = None,
        manifest: Optional[PluginManifest] = None,
        name: Optional[str] = None,
    ) -> PluginEntry:
        """Регистрирует экземпляр плагина в реестре.

        Args:
            instance: экземпляр BasePlugin
            path: опциональный путь к директории плагина
            manifest: опциональный манифест
            name: опциональное имя (по умолчанию instance.name)

        Returns:
            PluginEntry
        """
        plugin_name = name or instance.name
        meta = instance.meta

        entry = PluginEntry(
            name=plugin_name,
            path=path or Path(""),
            state=PluginState.LOADED,
            meta=meta,
            manifest=manifest,
            instance=instance,
            loaded_at=datetime.now(timezone.utc).isoformat(),
        )

        # Настраиваем окружение плагина
        instance._set_event_bus(self._event_bus)
        instance._set_tool_registry(self._tool_registry)

        # Вызываем on_load
        try:
            instance._do_load()
        except Exception as e:
            entry.state = PluginState.ERROR
            entry.error = str(e)

        with self._lock:
            self._plugins[plugin_name] = entry

        return entry

    def _add_error_entry(self, name: str, path: Path, error: str) -> None:
        """Добавляет ошибочную запись (для PluginLoader)."""
        entry = PluginEntry(
            name=name,
            path=path,
            state=PluginState.ERROR,
            error=error,
        )
        with self._lock:
            self._plugins[name] = entry

    # ── Enable / Disable ────────────────────────────────────

    def enable(self, name: str) -> bool:
        """Активирует плагин: подписка на события + регистрация тулов.

        Поддерживаемые переходы:
          LOADED → ENABLED
          DISABLED → ENABLED  (повторная активация)

        Args:
            name: имя плагина

        Returns:
            True если успешно
        """
        entry = self.get(name)
        if entry is None:
            return False

        if entry.state == PluginState.ENABLED:
            return True  # уже активирован

        if entry.state not in (PluginState.LOADED, PluginState.DISABLED):
            return False

        instance = entry.instance
        if instance is None:
            return False

        try:
            subscriptions = instance._do_enable()
            entry.subscriptions = subscriptions
            entry.state = PluginState.ENABLED
            entry.enabled_at = datetime.now(timezone.utc).isoformat()

            # Публикуем событие plugin.enabled
            self._publish_event("plugin.enabled", {
                "plugin": name,
                "version": instance.version,
            })

            return True
        except Exception as e:
            entry.state = PluginState.ERROR
            entry.error = str(e)
            return False

    def disable(self, name: str) -> bool:
        """Деактивирует плагин: отписка + удаление тулов.

        Поддерживаемые переходы:
          ENABLED → DISABLED
          ERROR → DISABLED  (принудительная деактивация после ошибки)

        Args:
            name: имя плагина

        Returns:
            True если успешно
        """
        entry = self.get(name)
        if entry is None:
            return False

        if entry.state == PluginState.DISABLED:
            return True

        if entry.state not in (PluginState.ENABLED, PluginState.ERROR):
            return False

        instance = entry.instance
        if instance is None:
            return False

        try:
            instance._do_disable()
            entry.subscriptions = []
            entry.state = PluginState.DISABLED

            # Публикуем событие plugin.disabled
            self._publish_event("plugin.disabled", {
                "plugin": name,
            })

            return True
        except Exception as e:
            entry.state = PluginState.ERROR
            entry.error = str(e)
            return False

    def enable_all(self) -> int:
        """Активирует все загруженные плагины.

        Returns:
            Количество успешно активированных
        """
        count = 0
        with self._lock:
            names = list(self._plugins.keys())
        for name in names:
            if self.enable(name):
                count += 1
        return count

    def disable_all(self) -> int:
        """Деактивирует все активные плагины.

        Returns:
            Количество успешно деактивированных
        """
        count = 0
        with self._lock:
            names = list(self._plugins.keys())
        for name in names:
            if self.disable(name):
                count += 1
        return count

    # ── Unload / Remove ─────────────────────────────────────

    def unload(self, name: str) -> bool:
        """Выгружает плагин полностью.

        Args:
            name: имя плагина

        Returns:
            True если успешно
        """
        entry = self.get(name)
        if entry is None:
            return False

        # Сначала отключаем
        if entry.state == PluginState.ENABLED:
            self.disable(name)

        instance = entry.instance
        if instance:
            try:
                instance._do_unload()
            except Exception:
                pass

        with self._lock:
            # Удаляем инструменты плагина из ToolRegistry
            if self._tool_registry and instance:
                for tool in instance.get_tools():
                    try:
                        self._tool_registry.unregister(tool.meta.name)
                    except Exception:
                        pass
            del self._plugins[name]

        return True

    def unload_all(self) -> int:
        """Выгружает все плагины.

        Returns:
            Количество выгруженных
        """
        count = 0
        with self._lock:
            names = list(self._plugins.keys())
        for name in names:
            if self.unload(name):
                count += 1
        return count

    # ── Query ───────────────────────────────────────────────

    def get(self, name: str) -> Optional[PluginEntry]:
        """Получает запись плагина по имени."""
        with self._lock:
            return self._plugins.get(name)

    def list(self, state: Optional[PluginState] = None) -> List[PluginEntry]:
        """Список всех плагинов, опционально фильтрованных по состоянию.

        Args:
            state: фильтр по состоянию

        Returns:
            Список PluginEntry
        """
        with self._lock:
            entries = list(self._plugins.values())
        if state:
            entries = [e for e in entries if e.state == state]
        return sorted(entries, key=lambda e: e.name)

    def count(self, state: Optional[PluginState] = None) -> int:
        """Количество плагинов."""
        return len(self.list(state))

    def has(self, name: str) -> bool:
        """Проверяет, есть ли плагин в реестре."""
        with self._lock:
            return name in self._plugins

    # ── Выполнение ──────────────────────────────────────────

    def execute(self, name: str, action: str, params: Dict[str, Any]) -> PluginResult:
        """Выполняет действие плагина.

        Args:
            name: имя плагина
            action: название действия
            params: параметры

        Returns:
            PluginResult
        """
        entry = self.get(name)
        if entry is None:
            return PluginResult(
                success=False,
                error=f"Plugin not found: {name}",
                plugin_name=name,
            )
        if entry.instance is None:
            return PluginResult(
                success=False,
                error=f"Plugin '{name}' has no instance",
                plugin_name=name,
            )
        return entry.instance.execute(action, params)

    # ── Публикация событий ──────────────────────────────────

    def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Публикует событие плагина в EventBus."""
        if self._event_bus is None:
            return
        try:
            from scripts_01.event_bus import Event
            self._event_bus.publish(Event(
                type=event_type,
                source=f"plugin:{event_type.split('.')[1]}",
                data=data,
            ))
        except Exception:
            pass

    # ── Состояние ───────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        """Полное состояние реестра плагинов."""
        entries = self.list()
        return {
            "total": len(entries),
            "enabled": sum(1 for e in entries if e.state == PluginState.ENABLED),
            "loaded": sum(1 for e in entries if e.state == PluginState.LOADED),
            "disabled": sum(1 for e in entries if e.state == PluginState.DISABLED),
            "error": sum(1 for e in entries if e.state == PluginState.ERROR),
            "plugins": [
                {
                    "name": e.name,
                    "state": e.state.value,
                    "version": e.meta.version if e.meta else "?",
                    "description": e.meta.description if e.meta else "",
                    "error": e.error,
                }
                for e in entries
            ],
        }


# ═══════════════════════════════════════════════════════════════
# PluginRegistrar — единая точка интеграции
# ═══════════════════════════════════════════════════════════════


def create_plugin_registrar(
    event_bus: Any = None,
    tool_registry: Any = None,
    plugins_dir: str | Path = "",
) -> Tuple[PluginLoader, PluginRegistry]:
    """Создаёт и настраивает PluginLoader + PluginRegistry.

    Args:
        event_bus: опциональный EventBus
        tool_registry: опциональный ToolRegistry
        plugins_dir: путь к директории с плагинами

    Returns:
        (PluginLoader, PluginRegistry) — готовые к использованию
    """
    registry = PluginRegistry(
        event_bus=event_bus,
        tool_registry=tool_registry,
    )
    loader = PluginLoader(registry)

    # Загружаем все плагины
    entries = loader.load_all(plugins_dir)

    if entries:
        print(f"🔌 Loaded {len(entries)} plugin(s): {', '.join(e.name for e in entries)}")

    return loader, registry


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Plugin API — плагинная система Buffy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # list
    p_list = sub.add_parser("list", help="Список плагинов")
    p_list.add_argument("--state", choices=[s.value for s in PluginState], help="Фильтр по состоянию")

    # enable
    p_enable = sub.add_parser("enable", help="Активировать плагин")
    p_enable.add_argument("name", help="Имя плагина")

    # disable
    p_disable = sub.add_parser("disable", help="Деактивировать плагин")
    p_disable.add_argument("name", help="Имя плагина")

    # execute
    p_exec = sub.add_parser("execute", help="Выполнить действие плагина")
    p_exec.add_argument("name", help="Имя плагина")
    p_exec.add_argument("action", help="Действие")
    p_exec.add_argument("--params", default="{)", help="JSON параметры")

    # status
    sub.add_parser("status", help="Состояние реестра")

    # reload
    sub.add_parser("reload", help="Перезагрузить все плагины")

    # contract — проверка Plugin Contract Specification (правило 9)
    p_contract = sub.add_parser("contract", help="Проверить контракт плагина (правило 9)")
    p_contract.add_argument("name", help="Имя плагина")

    args = parser.parse_args()

    # Создаём реестр (без EventBus и ToolRegistry в CLI)
    _, registry = create_plugin_registrar()

    if args.command == "list":
        state_filter = PluginState(args.state) if args.state else None
        entries = registry.list(state=state_filter)
        if not entries:
            print("📭 No plugins")
            return
        print(f"🔌 Plugins ({len(entries)}):")
        for e in entries:
            state_str = {
                PluginState.DISCOVERED: "🔍",
                PluginState.LOADED: "📦",
                PluginState.ENABLED: "✅",
                PluginState.DISABLED: "⏸️",
                PluginState.ERROR: "❌",
            }.get(e.state, "❓")
            version = e.meta.version if e.meta else "?"
            desc = e.meta.description if e.meta else ""
            error = f" — {e.error}" if e.error else ""
            print(f"  {state_str} {e.name:20} v{version}  {desc}{error}")

    elif args.command == "enable":
        if registry.enable(args.name):
            print(f"✅ Plugin '{args.name}' enabled")
        else:
            print(f"❌ Cannot enable '{args.name}'")

    elif args.command == "disable":
        if registry.disable(args.name):
            print(f"⏸️  Plugin '{args.name}' disabled")
        else:
            print(f"❌ Cannot disable '{args.name}'")

    elif args.command == "execute":
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError:
            params = {}
        result = registry.execute(args.name, args.action, params)
        if result.success:
            print(f"✅ {result.data}")
        else:
            print(f"❌ {result.error}")

    elif args.command == "status":
        state = registry.get_state()
        print(f"📊 PLUGIN REGISTRY STATUS")
        print(f"   Total:   {state['total']}")
        print(f"   Enabled: {state['enabled']}")
        print(f"   Loaded:  {state['loaded']}")
        print(f"   Disabled:{state['disabled']}")
        print(f"   Error:   {state['error']}")
        if state["plugins"]:
            print(f"   Plugins:")
            for p in state["plugins"]:
                icon = "✅" if p["state"] == "enabled" else "📦" if p["state"] == "loaded" else "❌"
                print(f"     {icon} {p['name']:20} {p['state']:10} v{p['version']}")

    elif args.command == "reload":
        count = registry.unload_all()
        _, registry = create_plugin_registrar()
        print(f"🔄 Reloaded — {registry.count()} plugin(s)")

    elif args.command == "contract":
        entry = registry.get(args.name)
        if entry is None:
            print(f"❌ Plugin not found: {args.name}")
            return
        from scripts_01.plugin_contract import (
            format_violations,
            validate_plugin_entry,
        )
        violations = validate_plugin_entry(entry)
        print(format_violations(args.name, violations))

    else:
        parser.print_help()


if __name__ == "__main__":
    # При запуске `python -m scripts_01.plugin_api` модуль исполняется как
    # `__main__` и до завершения НЕ зарегистрирован в sys.modules под своим
    # каноническим именем. Плагины импортируют `from scripts_01.plugin_api
    # import BasePlugin` — без регистрации это порождает ВТОРУЮ копию модуля
    # (и класса BasePlugin), из-за чего isinstance(plugin, BasePlugin) в
    # PluginLoader.load() ломается: "'plugin' is not a BasePlugin instance".
    # Регистрируем себя под каноническим именем до загрузки плагинов.
    sys.modules.setdefault("scripts_01.plugin_api", sys.modules[__name__])
    main()
