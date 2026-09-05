"""Policy-aware transport adapters (P12 + SRC-012/SRC-011).

Live-запросы разрешены исключительно для источника со статусом `allowed`
(двойной гейт: статус `ALLOWED` + `can_poll=True`); во всех остальных
случаях — `AdapterError` без тихого fallback.
"""

from .http_feed import HttpFeedAdapter
from .trudvsem import TrudvsemAdapter

__all__ = ["HttpFeedAdapter", "TrudvsemAdapter"***REMOVED***