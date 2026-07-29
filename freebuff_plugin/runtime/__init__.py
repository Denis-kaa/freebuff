"""
Runtime Abstraction Layer — типы и интерфейсы.

Спецификация: docs/core/RUNTIME_ABSTRACTION_SPECIFICATION.md
Основание: VISION_3.0.md §3.2, ARCHITECTURE_3.0.md §4.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from freebuff_plugin.runtime.registry import RuntimeCapabilityRegistry, RuntimeRegistry


# ═══════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════


class RuntimeStatus(Enum):
    """Статус Runtime в реестре."""
    UNKNOWN = "unknown"
    INSTALLED = "installed"          # Бинарник найден, но не подключён
    DISCOVERED = "discovered"        # Автоматически обнаружен
    CONNECTED = "connected"          # Подключён, handshake пройден
    ACTIVE = "active"                # Активно используется
    ERROR = "error"                  # Ошибка подключения/работы
    DISCONNECTED = "disconnected"    # Был подключён, но отключён


class SessionStatus(Enum):
    """Статус сессии Runtime."""
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"
    CLOSED = "closed"


class AdapterType(Enum):
    """Тип адаптера Runtime."""
    STDIO_MCP = "stdio_mcp"          # STDIO MCP протокол
    HTTP_MCP = "http_mcp"            # HTTP MCP протокол
    SUBPROCESS = "subprocess"        # Прямой subprocess
    HTTP_API = "http_api"            # HTTP API (OpenAI-compatible)
    BRIDGE = "bridge"                # Через Bridge Layer


# ═══════════════════════════════════════════════════════════════
# Core Data Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class RuntimeConfig:
    """Конфигурация Runtime.

    Определяет параметры подключения и поведения Runtime.
    """
    max_concurrent: int = 1
    timeout_seconds: int = 300
    max_retries: int = 3
    env_vars: Dict[str, str***REMOVED*** = field(default_factory=dict)
    args: List[str***REMOVED*** = field(default_factory=list)
    work_dir: Optional[str***REMOVED*** = None
    endpoint: Optional[str***REMOVED*** = None       # Для HTTP Runtime
    api_key: Optional[str***REMOVED*** = None        # Для HTTP Runtime
    command: Optional[str***REMOVED*** = None        # Для stdio Runtime
    auto_reconnect: bool = True


@dataclass
class RuntimeDefinition:
    """Метаданные AI Runtime.

    Описывает установленный или доступный AI Runtime.
    """
    name: str = ""                           # "freebuff", "claude-code"
    display_name: str = ""                   # "Freebuff CLI", "Claude Code"
    version: str = "0.0.0"
    adapter_type: str = AdapterType.STDIO_MCP.value  # Тип адаптера
    status: RuntimeStatus = RuntimeStatus.UNKNOWN
    config: Optional[RuntimeConfig***REMOVED*** = None
    capabilities: List[str***REMOVED*** = field(default_factory=list)
    bin_path: Optional[str***REMOVED*** = None           # Путь к бинарнику
    error: Optional[str***REMOVED*** = None              # Последняя ошибка


@dataclass
class RuntimeResult:
    """Результат генерации Runtime."""
    content: str = ""
    runtime: str = ""
    finish_reason: str = "stop"
    usage: Dict[str, int***REMOVED*** = field(default_factory=dict)
    latency_ms: int = 0
    model_used: Optional[str***REMOVED*** = None
    provider_used: Optional[str***REMOVED*** = None
    cached: bool = False
    fallback_used: bool = False
    error: Optional[str***REMOVED*** = None


@dataclass
class RuntimeCapability:
    """Возможность Runtime — что Runtime умеет делать."""
    name: str = ""                           # "coding", "planning", "review"
    description: str = ""
    confidence: float = 1.0                  # 0.0 - 1.0
    models: List[str***REMOVED*** = field(default_factory=list)


@dataclass
class RuntimeSession:
    """Сессия с конкретным Runtime.

    Хранит контекст взаимодействия с Runtime — историю сообщений,
    количество токенов, состояние.
    """
    runtime: str = ""
    session_id: str = ""
    context: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    message_count: int = 0
    token_estimate: int = 0
    status: SessionStatus = SessionStatus.IDLE
    error: Optional[str***REMOVED*** = None


@dataclass
class RuntimeHealth:
    """Результат health-проверки Runtime."""
    alive: bool = False
    version: str = ""
    latency_ms: int = 0
    connected: bool = False
    tools_count: int = 0
    error: Optional[str***REMOVED*** = None


__all__ = [
    "RuntimeStatus",
    "SessionStatus",
    "AdapterType",
    "RuntimeConfig",
    "RuntimeDefinition",
    "RuntimeResult",
    "RuntimeCapability",
    "RuntimeSession",
    "RuntimeHealth",
    "RuntimeRegistry",
    "RuntimeCapabilityRegistry",
***REMOVED***


# Lazy re-export to avoid circular imports: registry.py imports types from this module
# and should not be loaded until actually needed.
def __getattr__(name: str) -> Any:
    if name == "RuntimeRegistry":
        from freebuff_plugin.runtime.registry import RuntimeRegistry
        return RuntimeRegistry
    if name == "RuntimeCapabilityRegistry":
        from freebuff_plugin.runtime.registry import RuntimeCapabilityRegistry
        return RuntimeCapabilityRegistry
    raise AttributeError(f"module {__name__!r***REMOVED*** has no attribute {name!r***REMOVED***")
