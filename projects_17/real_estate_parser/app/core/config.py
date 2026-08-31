"""core/config.py — central configuration, loaded from environment.

Secrets and environment-specific values are ONLY read from env vars / .env,
never hard-coded (see 09_RISK_REGISTER.md).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    """Tiny .env loader (KEY=VALUE lines) — avoids external dependencies."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(PACKAGE_ROOT / "settings.env")


def _env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class Config:
    # ── scraping ────────────────────────────────────────────────
    sources: list[str] = field(default_factory=lambda: _env_list("REP_SOURCES"))
    proxy_urls: list[str] = field(default_factory=lambda: _env_list("REP_PROXY_URLS"))
    concurrency: int = int(os.getenv("REP_CONCURRENCY", "6"))
    request_delay: float = float(os.getenv("REP_REQUEST_DELAY", "1.0"))
    timeout: float = float(os.getenv("REP_TIMEOUT", "20.0"))
    max_retries: int = int(os.getenv("REP_MAX_RETRIES", "3"))
    batch_size: int = int(os.getenv("REP_BATCH_SIZE", "100"))

    # ── storage ─────────────────────────────────────────────────
    database_url: str = os.getenv("REP_DATABASE_URL", "")
    checkpoint_db: Path = field(
        default_factory=lambda: Path(
            os.getenv("REP_CHECKPOINT_DB", str(PACKAGE_ROOT / "data" / "checkpoints.db"))
        )
    )

    # ── telegram ────────────────────────────────────────────────
    bot_token: str = os.getenv("REP_BOT_TOKEN", "")
    admin_chat_id: str = os.getenv("REP_ADMIN_CHAT_ID", "")

    # ── scheduling ──────────────────────────────────────────────
    run_hour: int = int(os.getenv("REP_RUN_HOUR", "3"))
    run_minute: int = int(os.getenv("REP_RUN_MINUTE", "0"))

    def __post_init__(self) -> None:
        self.checkpoint_db.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Config":
        return cls()


# Singleton-style accessor
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
