"""Deterministic explainable matcher для P5.

Модуль сопоставляет нормализованные публикации с версионированными профилями
поиска и возвращает `MatchDecision` с воспроизводимым объяснением. Не имеет
сетевых вызовов и не зависит от платформенного кода.
"""

from .engine import (
    OFFER_MARKERS,
    STOPWORDS,
    RuleMatcher,
    is_stopword,
    normalize_text,
)

__all__ = [
    "OFFER_MARKERS",
    "STOPWORDS",
    "RuleMatcher",
    "is_stopword",
    "normalize_text",
***REMOVED***