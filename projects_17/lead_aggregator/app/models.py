"""models.py — доменные модели лида (W-11: интент-профиль заказчика)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Lead:
    """Один потенциальный клиент из источника.

    Поля:
      source      — имя адаптера (kwork / tg_channel / ...)
      source_id   — стабильный id в источнике (для checkpoint + dedup)
      text        — нормализованный текст объявления
      url         — ссылка на источник
      author      — автор объявления
      intent      — client | seeker | neutral (L2)
      score       — lead_score 0..100 (L3)
      legal_ok    — прошёл policy-гейт (W-7)
      raw         — сырые данные источника
    """

    source: str
    source_id: str
    text: str = ""
    url: str = ""
    author: str = ""
    intent: str = "unknown"
    score: float = 0.0
    legal_ok: bool = True
    raw: dict[str, Any***REMOVED*** = field(default_factory=dict)
