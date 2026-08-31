"""Загрузка и валидация конфигурации Realtor OS."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import]
except ImportError:  # pragma: no cover - fallback if pyyaml absent
    yaml = None  # type: ignore[assignment]

from realtor_os.constants import CONFIG_PATH, DATA_DIR, LOGS_DIR


class ConfigError(Exception):
    """Ошибка загрузки конфигурации."""


class Config:
    """Конфигурация приложения."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get(self, *path: str, default: Any = None) -> Any:
        """Получить значение по пути вложенных ключей."""
        node: Any = self._data
        for key in path:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def ensure_dirs(self) -> None:
        """Создать директории данных и логов, если их нет."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)


def load_config(path: Path | None = None) -> Config:
    """Загрузить конфигурацию из YAML-файла.

    Args:
        path: Путь к файлу конфигурации. По умолчанию config.yaml.

    Raises:
        ConfigError: если файл не найден или YAML не установлен.
    """
    if path is None:
        path = CONFIG_PATH

    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    if yaml is None:
        raise ConfigError("PyYAML is required to read config.yaml")

    content = path.read_text(encoding="utf-8")
    data: dict[str, Any] = yaml.safe_load(content) or {}
    return Config(data)


def load_env() -> dict[str, str]:
    """Загрузить переменные окружения, относящиеся к приложению."""
    return {
        "PII_ENCRYPTION_KEY": os.environ.get("PII_ENCRYPTION_KEY", ""),
        "LLM_BASE_URL": os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434"),
        "LLM_MODEL": os.environ.get("LLM_MODEL", "qwen2.5:7b"),
        "YANDEX_DISK_TOKEN": os.environ.get("YANDEX_DISK_TOKEN", ""),
        "EMAIL_HOST": os.environ.get("EMAIL_HOST", "smtp.yandex.ru"),
        "EMAIL_USER": os.environ.get("EMAIL_USER", ""),
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO"),
    }
