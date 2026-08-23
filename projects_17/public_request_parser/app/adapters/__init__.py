"""Policy-aware transport adapters (P12).

Реализован только gated HTTP-feed: live-запросы разрешены исключительно для
источника со статусом `allowed`; во всех остальных случаях — `AdapterError`.
Пока G2 (approved source) открыт, адаптер не может быть использован.
"""

from .http_feed import HttpFeedAdapter

__all__ = ["HttpFeedAdapter"***REMOVED***