"""deduplicator.py — дедупликация лидов (промт 69 §3).

Exact hash (SHA-256 нормализованного текста) — первичный фильтр;
fuzzy (difflib.SequenceMatcher) — вторичный для перефразировок.
"""
from __future__ import annotations

import difflib
import hashlib
from typing import Iterable

from app.models import Lead
from app.processors.intent_classifier import Normalizer


class Deduplicator:
    """Помнит хеши/нормализованные тексты виденных лидов.

    Args:
        fuzzy_threshold: порог similarity для отсева перефразировок (0.0..1.0).
    """

    def __init__(self, fuzzy_threshold: float = 0.9) -> None:
        self.fuzzy_threshold = fuzzy_threshold
        self._exact: set[str] = set()
        self._texts: list[str] = []

    @staticmethod
    def exact_hash(text: str) -> str:
        return hashlib.sha256(Normalizer.normalize(text).encode("utf-8")).hexdigest()

    def is_duplicate(self, lead: Lead) -> bool:
        """True — дубль (регистрирует новый только если НЕ дубль)."""
        norm = Normalizer.normalize(lead.text)
        h = self.exact_hash(norm)  # reuse (нормализация идемпотентна)
        if h in self._exact:
            return True
        # fuzzy: сравниваем с выборкой последних текстов
        for seen in self._texts:
            ratio = difflib.SequenceMatcher(None, norm, seen).ratio()
            if ratio >= self.fuzzy_threshold:
                return True
        self._exact.add(h)
        self._texts.append(norm)
        if len(self._texts) > 5000:  # bound памяти
            self._texts = self._texts[-1000:]
        return False

    def register_many(self, leads: Iterable[Lead]) -> list[Lead]:
        """Пропускает только уникальные лиды."""
        return [lead for lead in leads if not self.is_duplicate(lead)]
