"""intent_classifier.py — Lead Detection Engine L1/L2 (промт 69 §Lead Detection).

L1: быстрый отсев спама/рекламы/казино/репостов по стоп-словам (policy-гейт W-7).
L2: intent — «клиент ищет исполнителя» (горячий лид) vs «исполнитель ищет работу».

ВАЖНО (LA-2): полярность НЕ инвертирована — промт 69 уже считает «ищу
разработчика» горячим лидом, и Attract ищет ровно это же.
"""
from __future__ import annotations

***REMOVED***
from typing import Iterable


class IntentClassifier:
    """Двухуровневый классификатор интента.

    Args:
        stopwords: список стоп-слов L1 (спам/казино/реклама).
        client_markers: маркеры «клиент ищет исполнителя» (L2).
        seeker_markers: маркеры «исполнитель ищет работу» (L2).
    """

    def __init__(
        self,
        stopwords: Iterable[str***REMOVED*** = (),
        client_markers: Iterable[str***REMOVED*** = (),
        seeker_markers: Iterable[str***REMOVED*** = (),
    ) -> None:
        self.stopwords = [s.lower() for s in stopwords***REMOVED***
        self.client_markers = [m.lower() for m in client_markers***REMOVED***
        self.seeker_markers = [m.lower() for m in seeker_markers***REMOVED***

    # ── L1 ──────────────────────────────────────────────────────────
    def check_l1(self, text: str) -> bool:
        """True — прошёл L1 (нет стоп-слов). False — отсев (спам/казино)."""
        lowered = text.lower()
        return not any(w in lowered for w in self.stopwords if w)

    # ── L2 ──────────────────────────────────────────────────────────
    def check_l2(self, text: str) -> str:
        """Возвращает intent: 'client' | 'seeker' | 'neutral'."""
        lowered = text.lower()
        client_hits = sum(1 for m in self.client_markers if m in lowered)
        seeker_hits = sum(1 for m in self.seeker_markers if m in lowered)
        if client_hits > seeker_hits and client_hits > 0:
            return "client"
        if seeker_hits >= client_hits and seeker_hits > 0:
            return "seeker"
        return "neutral"

    # ── combined ────────────────────────────────────────────────────
    def classify(self, text: str) -> tuple[bool, str***REMOVED***:
        """Полный проход: (legal_ok, intent).

        legal_ok=False означает отсев на L1 (спам-зона, W-7).
        """
        if not self.check_l1(text):
            return False, "spam"
        return True, self.check_l2(text)


class Normalizer:
    """Нормализация текста перед хешированием/дедупликацией (промт 69 §3)."""

    _WS = re.compile(r"\s+")

    @staticmethod
    def normalize(text: str) -> str:
        """Нижний регистр, сжатие пробелов, обрезка."""
        return Normalizer._WS.sub(" ", text or "").strip().lower()
