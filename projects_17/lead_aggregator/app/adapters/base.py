"""base.py — базовый адаптер источника (изоляция, промт 69 п.2).

Правило: падение одного адаптера НЕ должно крашить ядро. Каждый адаптер
возвращает список Lead; ошибки оборачиваются в AdapterError.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import Lead


class AdapterError(Exception):
    """Ошибка конкретного адаптера (ядро её перехватывает и продолжает)."""


class BaseAdapter(ABC):
    """Контракт адаптера источника.

    ordered=True означает: fetch() возвращает лиды от новых к старым, и
    source_id монотонно убывает (напр. t.me/s с числовыми post_id) → пайплайн
    может применять checkpoint-resume по id. ordered=False (напр. Kwork,
    неупорядоченная лента) → resume по id НЕ применяется, дубли отсекаются
    Deduplicator'ом в рамках прогона.
    """

    name: str = "base"
    ordered: bool = False

    @abstractmethod
    async def fetch(self, limit: int = 50) -> list[Lead]:
        """Получить свежие лиды из источника."""
