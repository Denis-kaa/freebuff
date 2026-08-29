"""scripts_01/pricing_enumerator.py — verified course pricing scraper.

AGENTS.md §5 REGISTER-FIRST lifecycle (v5.189.60):
    registered → prompt_written (pompts_11/100_19_pricing_enumerator.md) → implemented (this file).

Sibling: scripts_01/research_web.py (corpus_persistence integration pattern);
scripts_01/corpus_persistence.py (atomic-jsonl persistence).
Pattern mirroring:
- dataclasses + to_dict/from_dict serialization.
- Protocol-based ScraperProtocol → FakeScraper provides hermetic tests.
- Lazy import of corpus_persistence + ADR-016 fail-safe (persist errors → stderr warning).
- CLI subcommand pattern with --no-corpus / --json / --source / --root / --version.

Use cases::

    from scripts_01.pricing_enumerator import (
        CoursePrice, FormatType, PricingEnumerator, ScraperProtocol,
        WebScraper, PricingEnumeratorNetworkError,
    )

    scraper = WebScraper(timeout=10.0)  # real (httpx + bs4)
    enum = PricingEnumerator(scraper=scraper, corpus_source="pricing_enumerator")
    results = enum.enumerate(["https://geekbrains.ru/courses/123", ...***REMOVED***)
    # results: List[CoursePrice***REMOVED***; persisted via corpus_persistence (per-URL).

Design invariants (per thinker v5.189.60):
- **Verbatim + numeric:** price_raw (verbatim string) + optional price_amount/currency.
- **Format enum:** FormatType from vocal/задача.md §10 course categories.
- **Soft + hard errors:** ScrapeStatus distinguishes recoverable (http_error, parse_error,
  missing_required_fields) → skip + warn; ``PricingEnumeratorNetworkError`` for fatal
  network outage (reraise → exit 2).
- **Write-forward (WORM):** each scrape creates new CoursePrice event; dedup at query-time.
- **ScraperProtocol for hermetic tests:** DI-friendly; FakeScraper implements the protocol
  without httpx/bs4 mocking.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import enum
import json
***REMOVED***
import sys
from dataclasses import dataclass
***REMOVED***
from typing import Any, Dict, List, Optional, Protocol

__all__ = [
    "FormatType",
    "ScrapeStatus",
    "CoursePrice",
    "ScrapeResult",
    "ScraperProtocol",
    "WebScraper",
    "PricingEnumerator",
    "PricingEnumeratorNetworkError",
    "main",
***REMOVED***

# DoS hardcaps (input validation).
URL_MAX_LEN: int = 2048
COURSE_MAX_LEN: int = 512
PRICE_RAW_MAX_LEN: int = 256
TEACHER_MAX_LEN: int = 256
BATCH_MAX_URLS: int = 1000


# ─── enums ─────────────────────────────────────────────────────────────────


class FormatType(str, enum.Enum):
    """Course format taxonomy from vocal/задача.md §10 course categories."""

    RECORDED = "recorded"
    COHORT = "cohort_based"
    MICRO = "micro_course"
    LIVE = "live_group"
    HYBRID = "hybrid"
    MEMBERSHIP = "membership"
    COMMUNITY = "community"
    CHALLENGE = "challenge"
    INTENSIVE = "intensive"
    UNKNOWN = "unknown"


class ScrapeStatus(str, enum.Enum):
    """Outcome of one URL scrape — used by ScraperProtocol contract."""

    OK = "ok"
    HTTP_ERROR = "http_error"
    PARSE_ERROR = "parse_error"
    MISSING_FIELDS = "missing_required_fields"


# ─── dataclasses ──────────────────────────────────────────────────────────


@dataclass
class CoursePrice:
    """Verbatim + numeric representation of one course price observation.

    Required fields: course, price_raw, source_url, scrape_timestamp.
    Optional: teacher, price_amount (float if parseable), price_currency, format.
    """

    course: str
    price_raw: str
    source_url: str
    scrape_timestamp: str  # ISO 8601 UTC 'Z'
    teacher: Optional[str***REMOVED*** = None
    price_amount: Optional[float***REMOVED*** = None
    price_currency: Optional[str***REMOVED*** = None
    format: FormatType = FormatType.UNKNOWN

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return {
            "course": self.course,
            "price_raw": self.price_raw,
            "source_url": self.source_url,
            "scrape_timestamp": self.scrape_timestamp,
            "teacher": self.teacher,
            "price_amount": self.price_amount,
            "price_currency": self.price_currency,
            "format": self.format.value,
        ***REMOVED***


@dataclass
class ScrapeResult:
    """Wrapper for one scraper.fetch() call — typed payload + status."""

    status: ScrapeStatus
    data: Optional[Dict[str, Any***REMOVED******REMOVED*** = None  # expected: course, price_raw, teacher, format
    error_msg: Optional[str***REMOVED*** = None


class ScraperProtocol(Protocol):
    """Contract for course-page scrapers. FakeScraper implements this in tests."""

    def fetch(self, url: str) -> ScrapeResult: ...


# ─── errors ────────────────────────────────────────────────────────────────


class PricingEnumeratorNetworkError(RuntimeError):
    """Network fatal: reraised to caller for batch-level abort."""

    pass


# ─── validators + helpers ──────────────────────────────────────────────────


def _validate_url(url: Any) -> None:
    if not isinstance(url, str):
        raise TypeError(f"url must be str, got {type(url).__name__***REMOVED***")
    if not url or not url.strip():
        raise ValueError("url is empty")
    if len(url) > URL_MAX_LEN:
        raise ValueError(f"url len={len(url)***REMOVED*** > URL_MAX_LEN={URL_MAX_LEN***REMOVED*** (DoS hardcap)")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("url must be http(s)")


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(timestamp: str) -> _dt.datetime:
    """Parse ISO 8601 'Z' format → aware UTC datetime. Lenient on missing 'Z'.

    Returns ``datetime.min`` if timestamp is empty or unparseable (defensive
    default → caller treats it as cache miss without crashing on corrupt rows).
    """
    if not timestamp:
        return _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)
    s = timestamp.rstrip("Z")
    try:
        return _dt.datetime.fromisoformat(s).replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)


def _is_fresh(timestamp: str, ttl_seconds: int) -> bool:
    """True iff ``timestamp`` is within ``ttl_seconds`` of now (UTC).

    Negative ages (future-dated timestamps, e.g. clock skew) are NOT fresh:
    anti-clock-skew guard — local-clock forward-jump protection.
    """
    if ttl_seconds <= 0:
        return False
    parsed = _parse_iso(timestamp)
    if parsed == _dt.datetime.min.replace(tzinfo=_dt.timezone.utc):
        return False
    age = (_dt.datetime.now(_dt.timezone.utc) - parsed).total_seconds()
    return 0 <= age <= ttl_seconds


_PRICE_AMOUNT_RE = re.compile(r"\d[\d\s\u00A0***REMOVED****([.,***REMOVED***\d+)?")


def _extract_price_amount(raw: str) -> Optional[float***REMOVED***:
    """Best-effort parse of verbatim price → float."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    m = _PRICE_AMOUNT_RE.search(raw)
    if not m:
        return None
    amount_str = m.group(0).replace(" ", "").replace("\u00A0", "").replace(",", ".")
    try:
        return float(amount_str)
    except ValueError:
        return None


def _validate_scrape_data(data: Dict[str, Any***REMOVED***) -> CoursePrice:
    """Convert ScrapeResult.data dict → CoursePrice (raise ValueError on missing/invalid)."""
    if not isinstance(data, dict):
        raise ValueError(f"data must be dict, got {type(data).__name__***REMOVED***")
    course = data.get("course")
    price_raw = data.get("price_raw")
    if not isinstance(course, str) or not course.strip():
        raise ValueError("missing required field 'course' (non-empty str)")
    if not isinstance(price_raw, str) or not price_raw.strip():
        raise ValueError("missing required field 'price_raw' (non-empty str)")
    if len(course) > COURSE_MAX_LEN:
        raise ValueError(f"course len={len(course)***REMOVED*** > COURSE_MAX_LEN={COURSE_MAX_LEN***REMOVED***")
    if len(price_raw) > PRICE_RAW_MAX_LEN:
        raise ValueError(
            f"price_raw len={len(price_raw)***REMOVED*** > PRICE_RAW_MAX_LEN={PRICE_RAW_MAX_LEN***REMOVED***"
        )

    teacher = data.get("teacher")
    if teacher is not None and not isinstance(teacher, str):
        raise ValueError(f"teacher must be str, got {type(teacher).__name__***REMOVED***")
    if isinstance(teacher, str) and len(teacher) > TEACHER_MAX_LEN:
        raise ValueError(f"teacher len > TEACHER_MAX_LEN={TEACHER_MAX_LEN***REMOVED***")

    # price_amount — explicit if provided, else best-effort parse from price_raw.
    provided_amount = data.get("price_amount")
    if provided_amount is not None:
        if not isinstance(provided_amount, (int, float)):
            raise ValueError(
                f"price_amount must be numeric, got {type(provided_amount).__name__***REMOVED***"
            )
        price_amount: Optional[float***REMOVED*** = float(provided_amount)
    else:
        price_amount = _extract_price_amount(price_raw)

    price_currency = data.get("price_currency")
    if price_currency is not None and not isinstance(price_currency, str):
        raise ValueError(
            f"price_currency must be str, got {type(price_currency).__name__***REMOVED***"
        )

    fmt_raw = data.get("format")
    if fmt_raw is None:
        fmt = FormatType.UNKNOWN
    elif isinstance(fmt_raw, str):
        try:
            fmt = FormatType(fmt_raw)
        except ValueError:
            fmt = FormatType.UNKNOWN  # unknown format → don't crash (forward-compat)
    else:
        raise ValueError(f"format must be str or None, got {type(fmt_raw).__name__***REMOVED***")

    return CoursePrice(
        course=course.strip(),
        price_raw=price_raw.strip(),
        source_url=str(data.get("source_url", "")),
        scrape_timestamp=str(data.get("scrape_timestamp") or _now_iso()),
        teacher=(teacher.strip() if isinstance(teacher, str) else None),
        price_amount=price_amount,
        price_currency=(
            price_currency.strip() if isinstance(price_currency, str) else None
        ),
        format=fmt,
    )


# ─── web-scraper (real implementation) ──────────────────────────────────


class WebScraper:
    """Default ScraperProtocol using httpx + BeautifulSoup.

    Strategy: try Schema.org microdata (Course / Product) first; fallback to
    ``<h1>`` for course title + ``.price`` CSS class for verbatim. Anti-bot /
    JS-only pages are out of scope per promt.
    """

    def __init__(self, *, timeout: float = 10.0) -> None:
        self.timeout = float(timeout)

    def fetch(self, url: str) -> ScrapeResult:
        try:
            import httpx  # noqa: F401  (lazy import — DRY for test isolation)
            from bs4 import BeautifulSoup
        except ImportError as exc:
            raise PricingEnumeratorNetworkError(
                f"httpx + bs4 not available: {exc***REMOVED***. "
                f"Install: pip install httpx beautifulsoup4"
            )
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, follow_redirects=True)
        except httpx.ConnectError as exc:
            raise PricingEnumeratorNetworkError(
                f"Cannot reach {url***REMOVED***: {exc***REMOVED***"
            )
        except httpx.TimeoutException as exc:
            return ScrapeResult(
                status=ScrapeStatus.HTTP_ERROR,
                error_msg=f"timeout on {url***REMOVED***: {exc***REMOVED***",
            )
        if response.status_code >= 400:
            return ScrapeResult(
                status=ScrapeStatus.HTTP_ERROR,
                error_msg=f"HTTP {response.status_code***REMOVED*** on {url***REMOVED***",
            )
        try:
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as exc:  # noqa: BLE001
            return ScrapeResult(
                status=ScrapeStatus.PARSE_ERROR,
                error_msg=f"BeautifulSoup parse error on {url***REMOVED***: {exc***REMOVED***",
            )
        data = self._extract(soup, url)
        if not data:
            return ScrapeResult(
                status=ScrapeStatus.MISSING_FIELDS,
                error_msg=f"missing course/price on {url***REMOVED***",
            )
        return ScrapeResult(status=ScrapeStatus.OK, data=data)

    @staticmethod
    def _extract(soup: Any, url: str) -> Optional[Dict[str, Any***REMOVED******REMOVED***:
        """Schema.org microdata first → <h1>+CSS-class fallback."""
        data: Dict[str, Any***REMOVED*** = {"source_url": url***REMOVED***

        # 1) Schema.org microdata (Course / Product / Event).
        micro_course = soup.find(
            attrs={"itemtype": re.compile(r"schema\.org/(Course|Product|Event)", re.I)***REMOVED***
        )
        if micro_course:
            name = micro_course.find(attrs={"itemprop": "name"***REMOVED***)
            if name and name.get_text(strip=True):
                data["course"***REMOVED*** = name.get_text(strip=True)
            teacher = micro_course.find(attrs={"itemprop": "instructor"***REMOVED***)
            if not teacher:
                teacher = micro_course.find(attrs={"itemprop": "author"***REMOVED***)
            if teacher and teacher.get_text(strip=True):
                data["teacher"***REMOVED*** = teacher.get_text(strip=True)
            price = micro_course.find(attrs={"itemprop": "price"***REMOVED***)
            if price and price.get_text(strip=True):
                data["price_raw"***REMOVED*** = price.get_text(strip=True)
            currency = micro_course.find(attrs={"itemprop": "priceCurrency"***REMOVED***)
            if currency and currency.get("content"):
                data["price_currency"***REMOVED*** = currency["content"***REMOVED***
            amount = micro_course.find(attrs={"itemprop": "amount"***REMOVED***)
            if amount and amount.get_text(strip=True):
                try:
                    data["price_amount"***REMOVED*** = float(amount.get_text(strip=True))
                except ValueError:
                    pass

        # 2) Fallback: first <h1> + .price CSS class.
        if "course" not in data:
            h1 = soup.find("h1")
            if h1 and h1.get_text(strip=True):
                data["course"***REMOVED*** = h1.get_text(strip=True)
        if "price_raw" not in data:
            price_match = soup.find(class_=re.compile(r"price", re.I))
            if price_match and price_match.get_text(strip=True):
                data["price_raw"***REMOVED*** = price_match.get_text(strip=True)

        if "course" not in data or "price_raw" not in data:
            return None
        return data


# ─── enumerator ───────────────────────────────────────────────────────────


class PricingEnumerator:
    """Batch scrape + per-URL persist via corpus_persistence (ADR-016)."""

    def __init__(
        self,
        *,
        scraper: ScraperProtocol,
        corpus_source: str = "pricing_enumerator",
        enabled: bool = True,
        cache_ttl_seconds: int = 0,
    ) -> None:
        if scraper is None:
            raise ValueError("scraper is required (ScraperProtocol)")
        if not isinstance(cache_ttl_seconds, int) or cache_ttl_seconds < 0:
            raise ValueError(
                f"cache_ttl_seconds must be non-negative int, got {cache_ttl_seconds!r***REMOVED*** "
                f"(0 ⇒ cache disabled; opt-in via caller)"
            )
        self.scraper = scraper
        self.corpus_source = corpus_source
        self.enabled = enabled  # False ⇒ skip corpus persistence (testing)
        self.cache_ttl_seconds = cache_ttl_seconds  # 0 ⇒ cache disabled (opt-in)

    def enumerate(self, urls: List[str***REMOVED***) -> List[CoursePrice***REMOVED***:
        if not isinstance(urls, list):
            raise TypeError(
                f"urls must be list[str***REMOVED***, got {type(urls).__name__***REMOVED***"
            )
        if len(urls) > BATCH_MAX_URLS:
            raise ValueError(
                f"batch size={len(urls)***REMOVED*** > BATCH_MAX_URLS={BATCH_MAX_URLS***REMOVED***"
            )

        results: List[CoursePrice***REMOVED*** = [***REMOVED***
        for raw in urls:
            # Soft input validation: skip bad URL, continue batch.
            try:
                _validate_url(raw)
            except (TypeError, ValueError) as exc:
                sys.stderr.write(
                    f"pricing_enumerator: skip invalid url: {exc***REMOVED***\n"
                )
                continue

            # Cache layer (v5.189.64): re-use within TTL window. Skip scrape + persist
            # if a fresh corpus_persistence entry already exists for (url, source).
            if self.enabled and self.cache_ttl_seconds > 0:
                cached = self._check_cache(raw)
                if cached is not None:
                    results.append(cached)
                    continue

            # Hard error from scraper (network fatal): abort entire batch.
            try:
                scrape_result = self.scraper.fetch(raw)
            except PricingEnumeratorNetworkError:
                raise
            except Exception as exc:  # noqa: BLE001 — soft crash recovery
                sys.stderr.write(
                    f"pricing_enumerator: scraper crash on {raw***REMOVED***: {exc***REMOVED***\n"
                )
                continue

            if scrape_result.status != ScrapeStatus.OK or scrape_result.data is None:
                sys.stderr.write(
                    f"pricing_enumerator: {raw***REMOVED*** → {scrape_result.status.value***REMOVED***"
                    f" ({scrape_result.error_msg or 'no data'***REMOVED***); skipped\n"
                )
                continue

            # Apply URL/timestamp overrides + validate required fields.
            try:
                payload = dict(scrape_result.data)
                payload["source_url"***REMOVED*** = raw
                payload.setdefault("scrape_timestamp", _now_iso())
                cp = _validate_scrape_data(payload)
            except ValueError as exc:
                sys.stderr.write(
                    f"pricing_enumerator: {raw***REMOVED*** → MISSING_FIELDS ({exc***REMOVED***); "
                    f"skipped\n"
                )
                continue

            results.append(cp)
            if self.enabled:
                self._persist_to_corpus(cp)
        return results

    def _check_cache(self, url: str) -> Optional[CoursePrice***REMOVED***:
        """Look up cached CoursePrice в corpus_persistence within TTL window.

        Uses ``corpus_persistence.lookup()`` filtered by ``(url, source)``.
        Fail-safe: returns None on any error / cache miss / expired entry.
        Never raises — callers treat None as 're-scrape this URL'.
        """
        if not self.enabled or self.cache_ttl_seconds <= 0:
            return None
        try:
            from scripts_01.corpus_persistence import lookup  # lazy
        except ImportError:
            return None
        try:
            entries = lookup(url)
        except Exception:
            return None
        # `corpus_persistence.lookup()` returns all entries для url across
        # sources; filter to our subtype (skip cross-source contamination per
        # design — each source is operated independently).
        entries = [e for e in entries if e.source == self.corpus_source***REMOVED***
        if not entries:
            return None
        try:
            latest = max(entries, key=lambda e: _parse_iso(e.timestamp))
        except Exception:
            return None
        # TTL semantics: for course prices, "fresh" means "page was scraped recently",
        # NOT "corpus row was written recently". persist() rewrites timestamp каждого
        # call, so use metadata['scrape_timestamp'***REMOVED*** как source of truth (written by
        # pricing_enumerator when the page was actually fetched). Fallback to
        # latest.timestamp for entries persisted without metadata['scrape_timestamp'***REMOVED***
        # (e.g., manual corpus writes).
        md = latest.metadata or {***REMOVED***
        scraped_at = md.get("scrape_timestamp") or latest.timestamp
        if not _is_fresh(scraped_at, self.cache_ttl_seconds):
            return None
        fmt_raw = md.get("format", "unknown")
        try:
            fmt = FormatType(fmt_raw)
        except ValueError:
            fmt = FormatType.UNKNOWN
        return CoursePrice(
            course=latest.title or "(cached)",
            price_raw=str(md.get("price_raw", "")),
            source_url=url,
            scrape_timestamp=scraped_at,
            teacher=md.get("teacher"),
            price_amount=md.get("price_amount"),
            price_currency=md.get("price_currency"),
            format=fmt,
        )

    def _persist_to_corpus(self, cp: CoursePrice) -> None:
        """Lazy import + ADR-016 fail-safe persist."""
        try:
            from scripts_01.corpus_persistence import persist  # noqa: WPS433
        except ImportError as exc:
            sys.stderr.write(
                f"pricing_enumerator: corpus_persistence unavailable: {exc***REMOVED***; "
                f"persistence disabled for this run\n"
            )
            return
        try:
            persist(
                cp.source_url,
                source=self.corpus_source,
                title=cp.course,
                metadata={
                    "price_raw": cp.price_raw,
                    "price_amount": cp.price_amount,
                    "price_currency": cp.price_currency,
                    "teacher": cp.teacher,
                    "format": cp.format.value,
                    "scrape_timestamp": cp.scrape_timestamp,
                ***REMOVED***,
            )
        except Exception as exc:  # noqa: BLE001 — ADR-016
            sys.stderr.write(
                f"pricing_enumerator: persist failed for "
                f"{cp.source_url***REMOVED***: {exc***REMOVED***; continuing\n"
            )


# ─── CLI ───────────────────────────────────────────────────────────────────


def _print_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def _format_text(cp: CoursePrice) -> str:
    teacher = cp.teacher or "(unknown)"
    return (
        f"- {cp.course***REMOVED*** [{cp.format.value***REMOVED******REMOVED*** — {cp.price_raw***REMOVED*** "
        f"({cp.source_url***REMOVED***) teacher={teacher***REMOVED***"
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pricing_enumerator",
        description=(
            "Verified course pricing scraper. Writes per-URL results to "
            "corpus_persistence (use --no-corpus to disable)."
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version="pricing_enumerator 1.0.0 (v5.189.60)",
    )
    p.add_argument(
        "urls",
        nargs="+",
        help="Target course URLs (one or more; HTTPS recommended)",
    )
    p.add_argument(
        "--source",
        default="pricing_enumerator",
        help="corpus source tag (default: pricing_enumerator)",
    )
    p.add_argument(
        "--no-corpus",
        action="store_true",
        help="Disable corpus_persistence writes (default: enabled)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="WebScraper timeout seconds (default: 10.0)",
    )
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="corpus root override (default=data_13/corpus); for tests/staging",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="JSON output (machine-readable; default: text)",
    )
    return p


def main(argv: Optional[List[str***REMOVED******REMOVED*** = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    scraper = WebScraper(timeout=args.timeout)
    enum = PricingEnumerator(
        scraper=scraper,
        corpus_source=args.source,
        enabled=(not args.no_corpus),
    )
    try:
        results = enum.enumerate(args.urls)
    except PricingEnumeratorNetworkError as exc:
        sys.stderr.write(f"pricing_enumerator: NETWORK FATAL: {exc***REMOVED***\n")
        return 2

    if args.json:
        _print_json([cp.to_dict() for cp in results***REMOVED***)
        return 0
    if not results:
        sys.stdout.write("(no prices extracted — all URLs returned soft errors)\n")
        return 0
    for cp in results:
        sys.stdout.write(_format_text(cp) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
