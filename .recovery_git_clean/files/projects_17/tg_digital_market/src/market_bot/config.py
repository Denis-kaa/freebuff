"""config.py — загрузка конфигурации из окружения.

Намеренно без сторонних библиотек (без `dotenv`/pydantic-settings): достаточно
stdlib + пары хелперов, что уменьшает поставку и поверхность отказа. Значения,
не выставленные через env, подставляются дефолтно для удобства dev-сценария.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
***REMOVED***
from typing import FrozenSet

from .models import UserRole


def _split_csv(raw: str) -> list[str***REMOVED***:
    return [x.strip() for x in raw.split(",") if x.strip()***REMOVED***


def _split_csv_ints(raw: str) -> list[int***REMOVED***:
    out: list[int***REMOVED*** = [***REMOVED***
    for x in _split_csv(raw):
        try:
            out.append(int(x))
        except ValueError:
            continue
    return out


def _read_env_file(path: Path) -> None:
    """Загружает пары `KEY=VALUE` в `os.environ` (без вытеснения существующих)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: FrozenSet[int***REMOVED***
    database_path: str
    payment_provider: str
    payment_provider_token: str
    payment_ttl_seconds: int
    log_level: int
    project_root: Path = field(default_factory=Path.cwd)

    # ── производные свойства ────────────────────────────────────────────────

    @property
    def default_payment_kind(self) -> str:
        return self.payment_provider.lower()

    @property
    def admin_id_list(self) -> list[int***REMOVED***:
        return sorted(self.admin_ids)

    def role_for_user_id(self, user_id: int) -> UserRole:
        if user_id in self.admin_ids:
            return UserRole.ADMIN
        return UserRole.USER


def load_config(env_path: str | Path | None = ".env") -> Config:
    """Загрузить конфиг из `.env` (если есть) + реального окружения.

    BOT_TOKEN обязателен. ADMIN_IDS через запятую. DATABASE_PATH от корня
    проекта — относительный путь.
    """
    if env_path is not None:
        _read_env_file(Path(env_path))

    bot_token = os.environ.get("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError(
            "BOT_TOKEN не задан. Укажите токен от @BotFather в .env или окружении."
        )

    admin_ids = frozenset(_split_csv_ints(os.environ.get("ADMIN_IDS", "")))
    database_path = os.environ.get("DATABASE_PATH", "data/market.sqlite").strip()
    payment_provider = os.environ.get("PAYMENT_PROVIDER", "mock").strip().lower()
    payment_provider_token = os.environ.get("PAYMENT_PROVIDER_TOKEN", "").strip()
    payment_ttl = int(os.environ.get("PAYMENT_TTL_SECONDS", "900"))

    log_level_name = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    return Config(
        bot_token=bot_token,
        admin_ids=admin_ids,
        database_path=database_path,
        payment_provider=payment_provider,
        payment_provider_token=payment_provider_token,
        payment_ttl_seconds=payment_ttl,
        log_level=log_level,
    )
