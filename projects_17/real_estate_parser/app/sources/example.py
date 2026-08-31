"""sources/example.py — example SSR source adapter for real-estate listings.

Serves as the template for writing adapters against concrete sites and as the
working fallback in hermetic tests (no network — data is fed via fixture).

Real adapters are added additively: one file per source
(see 05_IMPLEMENTATION_PLAN.md, Phase 2).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.core.tls_client import TLSClient
from .base import Listing, SourceAdapter


class ExampleSourceAdapter(SourceAdapter):
    """SSR-adapter template: listing page → card URLs → per-card parse.

    Replace selectors/discovery with the real site's markup after a live
    curl check (see 03_TOOL_RESEARCH.md: verify SSR before writing the parser).
    """

    name = "example"
    ordered = False

    # Discovery: the listing page that links cards (with pagination).
    listing_url = "https://example.com/listings?page={page}"
    max_pages = 3

    def __init__(self, client: TLSClient | None = None) -> None:
        self.client = client or TLSClient()

    async def fetch(self, limit: int = 100) -> list[Listing]:
        out: list[Listing] = []
        for page in range(1, self.max_pages + 1):
            html = await self.client.get(self.listing_url.format(page=page))
            out.extend(self.parse_listing(html))
            if len(out) >= limit:
                break
        return out[:limit]

    def parse_listing(self, html: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        props: list[Listing] = []
        for card in soup.select(".listing-card"):
            prop = self.parse_card(str(card))
            if prop is not None:
                props.append(prop)
        return props

    def parse_card(self, html: str) -> Listing | None:
        """Parse one card; return None when required fields are missing."""
        soup = BeautifulSoup(html, "html.parser")
        link = soup.select_one("a.listing-link")
        if link is None:
            return None
        url = link.get("href", "")
        external_id = re.search(r"/(\d+)(?:/|$)", url)
        if not url or external_id is None:
            return None
        price = _parse_price(soup.select_one(".price").get_text() if soup.select_one(".price") else "")
        area = _parse_area(soup.select_one(".area").get_text() if soup.select_one(".area") else "")
        rooms = _parse_rooms(soup.select_one(".rooms").get_text() if soup.select_one(".rooms") else "")
        if price is None or area is None:
            return None  # validator: required fields
        return Listing(
            source=self.name,
            external_id=external_id.group(1),
            url=url,
            title=soup.get_text(" ", strip=True)[:200],
            price=price,
            currency="USD",
            area_m2=area,
            rooms=rooms,
            property_type="apartment",
        )


def _parse_price(text: str) -> float | None:
    m = re.search(r"[\d\s.,]+", text or "")
    if not m:
        return None
    digits = re.sub(r"[^\d.]", "", m.group(0))
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def _parse_area(text: str) -> float | None:
    m = re.search(r"([\d.,]+)\s*(m²|sqm|m2)", text or "", re.IGNORECASE)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _parse_rooms(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)", text or "")
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None
