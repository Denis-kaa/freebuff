"""Runtime abstraction types (восстановлено v5.189.88 по контракту тестов)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RuntimeStatus(str, Enum):
    """Жизненный цикл runtime (B10-совместимый закрытый набор)."""

    UNKNOWN = "unknown"
    DISCOVERED = "discovered"
    INSTALLED = "installed"
    CONNECTED = "connected"
    ACTIVE = "active"
    ERROR = "error"
    MISSING = "missing"


class SessionStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    EXPIRED = "expired"


class AdapterType(str, Enum):
    STDIO_MCP = "stdio_mcp"
    HTTP_MCP = "http_mcp"


@dataclass
class RuntimeConfig:
    """Конфигурация запуска runtime."""

    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    url: str = ""
    max_concurrent: int = 1
    timeout_seconds: int = 300
    max_retries: int = 3
    auto_reconnect: bool = True


@dataclass
class RuntimeDefinition:
    """Описание runtime в реестре."""

    name: str = ""
    display_name: str = ""
    version: str = "0.0.0"
    status: RuntimeStatus = RuntimeStatus.UNKNOWN
    capabilities: List[str] = field(default_factory=list)
    description: str = ""
    config: RuntimeConfig = field(default_factory=RuntimeConfig)
    adapter_type: str = AdapterType.STDIO_MCP.value

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "name": self.name,
            "display_name": self.display_name,
            "version": self.version,
            "status": self.status.value,
            "capabilities": list(self.capabilities),
            "description": self.description,
            "adapter_type": self.adapter_type,
            "config": {
                "command": self.config.command,
                "args": list(self.config.args),
                "env": dict(self.config.env),
                "url": self.config.url,
                "max_concurrent": self.config.max_concurrent,
                "timeout_seconds": self.config.timeout_seconds,
                "max_retries": self.config.max_retries,
                "auto_reconnect": self.config.auto_reconnect,
            },
        }
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeDefinition":
        cfg_raw = data.get("config") or {}
        cfg = RuntimeConfig(
            command=cfg_raw.get("command", ""),
            args=list(cfg_raw.get("args", [])),
            env=dict(cfg_raw.get("env", {})),
            url=cfg_raw.get("url", ""),
            max_concurrent=int(cfg_raw.get("max_concurrent", 1)),
            timeout_seconds=int(cfg_raw.get("timeout_seconds", 300)),
            max_retries=int(cfg_raw.get("max_retries", 3)),
            auto_reconnect=bool(cfg_raw.get("auto_reconnect", True)),
        )
        try:
            status = RuntimeStatus(data.get("status", RuntimeStatus.UNKNOWN.value))
        except ValueError:
            status = RuntimeStatus.UNKNOWN
        return cls(
            name=data.get("name", ""),
            display_name=data.get("display_name", ""),
            version=data.get("version", "0.0.0"),
            status=status,
            capabilities=list(data.get("capabilities", [])),
            description=data.get("description", ""),
            adapter_type=data.get("adapter_type", AdapterType.STDIO_MCP.value),
            config=cfg,
        )


@dataclass
class RuntimeResult:
    """Результат генерации через runtime."""

    content: str = ""
    finish_reason: str = "stop"
    latency_ms: int = 0
    cached: bool = False
    runtime: Optional[str] = None
    model_used: Optional[str] = None
    session_id: Optional[str] = None
    error: Optional[str] = None
    provider_used: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeCapability:
    name: str = ""
    description: str = ""
    confidence: float = 0.5
    models: List[str] = field(default_factory=list)


@dataclass
class RuntimeSession:
    runtime: str = ""
    session_id: str = ""
    message_count: int = 0
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: float = 0.0


@dataclass
class RuntimeHealth:
    alive: bool = False
    version: str = "unknown"
    latency_ms: int = 0
    connected: bool = False
    tools_count: int = 0
    error: Optional[str] = None
