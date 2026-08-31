"""sources/base.py — base adapter contract.

Every source plugs in via `sources/base.py`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class SourceError(Exception):
    """Raised when a source adapter fails; the pipeline catches and continues."""


@dataclass
class Listing:
    """Normalized listing produced by a source adapter."""

    source: str
    external_id: str
    url: str
    title: str | None = None
    price: float | None = None
    currency: str | None = None
    area_m2: float | None = None
    rooms: float | None = None
    address: str | None = None
    property_type: str | None = None
    extra: dict = field(default_factory=dict)


class SourceAdapter(ABC):
    """Contract every source plugs in via `sources/base.py`."""

    @abstractmethod
    async def fetch(self, limit: int = 100) -> list[Listing]:
        """Return up to `limit` normalized listings from this source."""
