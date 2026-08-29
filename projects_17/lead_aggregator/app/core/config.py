"""config.py — конфигурация lead_aggregator.

Загружает YAML-конфиги (keywords, competence_profile) и переменные окружения
(settings.env). Все пути относительно корня пакета lead_aggregator/.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
***REMOVED***
from typing import Any

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent  # lead_aggregator/


def _load_yaml(path: Path) -> dict[str, Any***REMOVED***:
    if not path.exists():
        return {***REMOVED***
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {***REMOVED***
    return data if isinstance(data, dict) else {***REMOVED***


def _load_env_file(path: Path) -> None:
    """Загрузить KEY=VALUE из settings.env в os.environ (не перезаписывая заданные).

    Фаза 4 (Deploy): CLI может запускаться без экспорта переменных —
    settings.env читается автоматически. Формат: строки KEY=VALUE,
    комментарии # и секции [TEMPLATE***REMOVED*** игнорируются. Уже заданные env
    имеют приоритет (не перезаписываем).
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key***REMOVED*** = value.strip()


# КРИТИЧНО: загрузить settings.env ДО вычисления дефолтов Config. Поля с
# os.getenv() в default'ах вычисляются ОДИН РАЗ при импорте модуля — если
# файл прочитать позже (в load_config), значения не дойдут до полей.
_load_env_file(PACKAGE_ROOT / "settings.env")


@dataclass
class Config:
    """Единый конфиг приложения (W-8: competence_profile; policy-гейт W-7)."""

    keywords_path: Path = PACKAGE_ROOT / "config" / "keywords.yaml"
    profile_path: Path = PACKAGE_ROOT / "config" / "competence_profile.yaml"
    # ВСЕ env-поля — через default_factory, а не os.getenv() в default:
    # последний вычисляется один раз при импорте модуля и не видит ни
    # settings.env (загруженного после импорта), ни правок env в рантайме.
    # default_factory читает env при каждом инстанцировании Config.
    checkpoint_db: Path = field(
        default_factory=lambda: Path(
            os.getenv("LA_CHECKPOINT_DB", str(PACKAGE_ROOT / "data" / "checkpoints.db"))
        )
    )
    poll_interval_s: float = field(
        default_factory=lambda: float(os.getenv("LA_POLL_INTERVAL", "600"))
    )
    lead_score_threshold: float = field(
        default_factory=lambda: float(os.getenv("LA_SCORE_THRESHOLD", "50"))
    )
    tg_bot_token: str = field(
        default_factory=lambda: os.getenv("LA_TG_BOT_TOKEN", "")
    )
    tg_chat_id: str = field(
        default_factory=lambda: os.getenv("LA_TG_CHAT_ID", "")
    )
    # Первый адаптер по roadmap: Kwork (рекомендация PHASE2 §8).
    kwork_feed_url: str = field(
        default_factory=lambda: os.getenv("LA_KWORK_FEED", "https://kwork.ru/projects")
    )
    kwork_enabled: bool = field(
        default_factory=lambda: os.getenv("LA_KWORK_ENABLED", "1") == "1"
    )
    tg_channels: list[str***REMOVED*** = field(
        default_factory=lambda: [
            ch.strip()
            for ch in os.getenv("LA_TG_CHANNELS", "freelance_tg,proger_orders").split(",")
            if ch.strip()
        ***REMOVED***
    )

    def __post_init__(self) -> None:
        self.keywords = _load_yaml(self.keywords_path)
        self.profile = _load_yaml(self.profile_path)
        self.checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
        # score_threshold из competence_profile.yaml — если env не задан явно
        if "LA_SCORE_THRESHOLD" not in os.environ:
            yaml_threshold = self.profile.get("score_threshold")
            if isinstance(yaml_threshold, (int, float)):
                self.lead_score_threshold = float(yaml_threshold)

    # ── сигнатуры запросов из competence_profile (W-8) ──────────────
    @property
    def competence_signals(self) -> list[str***REMOVED***:
        """Все сигнатуры компетенций (для L2-таргетинга и L3-скоринга)."""
        signals: list[str***REMOVED*** = [***REMOVED***
        for comp in self.profile.get("competencies", [***REMOVED***):
            signals.extend(comp.get("signals", [***REMOVED***))
        return [s.lower() for s in signals if s***REMOVED***

    # ── стоп-слова L1 (W-7 policy-гейт: спам-зона исключена) ─────────
    @property
    def stopwords(self) -> list[str***REMOVED***:
        return [w.lower() for w in self.keywords.get("stopwords", [***REMOVED***)***REMOVED***

    @property
    def client_markers(self) -> list[str***REMOVED***:
        return [w.lower() for w in self.keywords.get("client_markers", [***REMOVED***)***REMOVED***

    @property
    def seeker_markers(self) -> list[str***REMOVED***:
        return [w.lower() for w in self.keywords.get("seeker_markers", [***REMOVED***)***REMOVED***


def load_config() -> Config:
    """Загрузить settings.env (если есть) и вернуть Config."""
    _load_env_file(PACKAGE_ROOT / "settings.env")
    return Config()
