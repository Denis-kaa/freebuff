"""Knowledge Curator — /learn команда."""

from __future__ import annotations

import json
***REMOVED***

from realtor_os.constants import DATA_DIR
from realtor_os.logger import setup_logger

_LOGGER = setup_logger("realtor_os.curator")


class KnowledgeCurator:
    """Сохраняет источники по темам."""

    def __init__(self, store_path: Path | None = None) -> None:
        self._store = store_path or DATA_DIR / "knowledge.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def learn(self, topic: str, sources: list[dict[str, str***REMOVED******REMOVED*** | None = None) -> dict[str, list[dict[str, str***REMOVED******REMOVED******REMOVED***:
        """Сохранить источники по теме.

        Args:
            topic: Тема.
            sources: Список источников.

        Returns:
            Текущее состояние базы знаний по теме.
        """
        if sources is None:
            sources = [***REMOVED***

        data: dict[str, list[dict[str, str***REMOVED******REMOVED******REMOVED*** = {***REMOVED***
        if self._store.exists():
            try:
                raw = self._store.read_text(encoding="utf-8")
                data = json.loads(raw)
            except (json.JSONDecodeError, OSError) as exc:
                _LOGGER.warning("Failed to load knowledge store: %s", exc)

        data[topic***REMOVED*** = sources
        self._store.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {topic: sources***REMOVED***

    def list_topics(self) -> list[str***REMOVED***:
        if not self._store.exists():
            return [***REMOVED***
        try:
            raw = self._store.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, OSError) as exc:
            _LOGGER.warning("Failed to load knowledge store: %s", exc)
            return [***REMOVED***
        return list(data.keys())
