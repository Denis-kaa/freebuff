"""RSS/Atom source engine для P4.

Модуль работает с переданными bytes/строками и не выполняет сетевых запросов.
"""

from .engine import (
    FeedParseResult,
    FeedWarning,
    FixtureFeedAdapter,
    InMemoryCheckpointStore,
    RSSAtomParser,
    deduplicate_publications,
    normalize_source_item,
)

__all__ = [
    "FeedParseResult",
    "FeedWarning",
    "FixtureFeedAdapter",
    "InMemoryCheckpointStore",
    "RSSAtomParser",
    "deduplicate_publications",
    "normalize_source_item",
***REMOVED***
