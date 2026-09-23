"""Резюме отчётов Reports Hub: override + детерминированный провайдер (спека §9, §5.3, H3).

Приоритет: override `summaries.json` → LLM-провайдер (hook, H4) →
детерминированное резюме. Цифры всегда из детерминированного слоя.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Protocol

_CYRILLIC_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}

_SUMMARY_SCHEMA_VERSION = 1


def slugify(value: str) -> str:
    """Транслитерировать имя в URL-слаг (кириллица → латиница).

    При пустом результате — хеш (стабильный, `s-<hash>`), правило спеки §11:
    кириллические имена транслитерируются, хеш — при коллизии/пустоте.
    """
    lowered = value.lower()
    translit = "".join(_CYRILLIC_MAP.get(ch, ch) for ch in lowered)
    slug = re.sub(r"[^a-z0-9]+", "-", translit).strip("-")
    if not slug:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
        return f"s-{digest}"
    return slug


class SummaryProvider(Protocol):
    """Провайдер резюме (детерминированный / override / LLM)."""

    def exec_summary(self, key: str, fallback: str) -> str:
        """Резюме отчёта: ключ + детерминированный фолбэк."""
        ...

    def doc_summary(self, key: str, fallback: str) -> str:
        """Резюме документа: ключ + детерминированный фолбэк."""
        ...


class DeterministicProvider:
    """Детерминированные резюме (фолбэк: первые абзацы/цитаты)."""

    def exec_summary(self, key: str, fallback: str) -> str:
        return fallback

    def doc_summary(self, key: str, fallback: str) -> str:
        return fallback


class OverrideProvider:
    """Override-резюме из `summaries.json` (спека §9).

    Неиспользованные ключи не удаляются молча: список осиротевших
    доступен через `orphans()` для диагностики.
    """

    def __init__(self, data: dict[str, str], base: SummaryProvider | None = None) -> None:
        self._data = data
        self._base = base or DeterministicProvider()
        self._used: set[str] = set()

    @classmethod
    def from_file(cls, path: Path) -> OverrideProvider:
        """Загрузить override-файл (битый/отсутствующий → пустой override)."""
        if not path.exists():
            return cls({})
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls({})
        if not isinstance(payload, dict):
            return cls({})
        entries = {
            str(key): str(value)
            for key, value in payload.items()
            if key != "schema_version" and isinstance(value, str) and value.strip()
        }
        return cls(entries)

    def _lookup(self, key: str, fallback: str) -> str:
        value = self._data.get(key)
        if value:
            self._used.add(key)
            return value
        return fallback

    def exec_summary(self, key: str, fallback: str) -> str:
        return self._lookup(key, fallback)

    def doc_summary(self, key: str, fallback: str) -> str:
        return self._lookup(key, fallback)

    def orphans(self) -> list[str]:
        """Ключи override, которые не были использованы при генерации."""
        return sorted(key for key in self._data if key not in self._used)

    def used(self) -> set[str]:
        """Использованные ключи override."""
        return set(self._used)
