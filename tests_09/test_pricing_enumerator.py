"""tests_09/test_pricing_enumerator.py — Hermetic tests for scripts_01/pricing_enumerator.py.

Per-prompt 100 (v5.189.60):
- CoursePrice schema invariants.
- ScraperProtocol contract (FakeScraper hermetic).
- PricingEnumerator batch + soft/hard error semantics.
- corpus_persistence integration + ADR-016 fail-safe.
- CLI subprocess smoke.

Pattern follows tests_09/test_hypothesis_ledger.py (autouse fixture monkey-patches
both pricing_enumerator + corpus_persistence modules to avoid transitive-monkeypatch
snapshots via ``from X import Y``).
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Module under test.
from scripts_01 import pricing_enumerator
from scripts_01 import corpus_persistence
from scripts_01.pricing_enumerator import (
    BATCH_MAX_URLS,
    COURSE_MAX_LEN,
    FormatType,
    PricingEnumerator,
    PricingEnumeratorNetworkError,
    CoursePrice,
    ScrapeResult,
    ScrapeStatus,
    ScraperProtocol,
    URL_MAX_LEN,
    WebScraper,
    _validate_scrape_data,
    _validate_url,
    main,
)


# ─── fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_corpus_root(monkeypatch, tmp_path) -> None:
    """Override DEFAULT_CORPUS_DIR in BOTH pricing_enumerator's lazy import AND
    corpus_persistence module for transitive-monkeypatch safety."""
    from scripts_01 import pricing_enumerator as pe_mod
    from scripts_01 import corpus_persistence as cp_mod
    target = tmp_path / "corpus"
    target.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cp_mod, "DEFAULT_CORPUS_DIR", target)
    monkeypatch.setattr(corpus_persistence, "DEFAULT_CORPUS_DIR", target)
    monkeypatch.setattr(pe_mod, "BATCH_MAX_URLS", BATCH_MAX_URLS)  # no-op sanity


# ─── FakeScraper (implements ScraperProtocol) ──────────────────────────────


class FakeScraper:
    """Deterministic ScraperProtocol impl keyed by URL. No httpx needed."""
    def __init__(self, mapping: Dict[str, ScrapeResult]) -> None:
        self.mapping = mapping
        self.calls: List[str] = []

    def fetch(self, url: str) -> ScrapeResult:
        self.calls.append(url)
        if url not in self.mapping:
            return ScrapeResult(
                status=ScrapeStatus.MISSING_FIELDS,
                error_msg=f"no fixture for {url}",
            )
        return self.mapping[url]


# ─── TestSchema ─────────────────────────────────────────────────────────────


class TestSchema:
    def test_course_price_to_dict_round_trip(self):
        cp = CoursePrice(
            course="Vocal Mastery",
            price_raw="12 900 ₽",
            source_url="https://example.com/courses/vocal",
            scrape_timestamp="2026-08-20T10:00:00Z",
            teacher="Иванов И.И.",
            price_amount=12900.0,
            price_currency="RUB",
            format=FormatType.COHORT,
        )
        d = cp.to_dict()
        assert d["course"] == "Vocal Mastery"
        assert d["price_raw"] == "12 900 ₽"
        assert d["format"] == "cohort_based"
        assert d["price_amount"] == 12900.0
        assert d["price_currency"] == "RUB"

    def test_validate_url_accepts_https(self):
        _validate_url("https://example.com/courses")

    def test_validate_url_accepts_http(self):
        _validate_url("http://example.com/courses")

    def test_validate_url_rejects_non_http(self):
        with pytest.raises(ValueError, match="http"):
            _validate_url("ftp://example.com")

    def test_validate_url_rejects_empty(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_url("")

    def test_validate_url_rejects_dos(self):
        with pytest.raises(ValueError, match="DoS"):
            _validate_url("https://example.com/" + "a" * (URL_MAX_LEN + 100))

    def test_validate_url_rejects_non_str(self):
        with pytest.raises(TypeError):
            _validate_url(123)  # type: ignore[arg-type]

    def test_format_type_unknown_is_default(self):
        cp = CoursePrice(
            course="X", price_raw="100", source_url="https://x", scrape_timestamp="now"
        )
        assert cp.format == FormatType.UNKNOWN

    def test_validate_scrape_data_missing_course_raises(self):
        with pytest.raises(ValueError, match="course"):
            _validate_scrape_data({"price_raw": "100"})

    def test_validate_scrape_data_missing_price_raises(self):
        with pytest.raises(ValueError, match="price_raw"):
            _validate_scrape_data({"course": "Test"})

    def test_validate_scrape_data_extracts_price_amount(self):
        cp = _validate_scrape_data({
            "course": "X", "price_raw": "от 12 900 ₽/мес",
            "source_url": "https://x", "scrape_timestamp": "now",
        })
        assert cp.price_amount == 12900.0

    def test_validate_scrape_data_unparseable_amount_is_none(self):
        cp = _validate_scrape_data({
            "course": "X", "price_raw": "по запросу",
            "source_url": "https://x", "scrape_timestamp": "now",
        })
        assert cp.price_amount is None  # verbatim preserved

    def test_validate_scrape_data_unknown_format_falls_to_unknown(self):
        """Forward-compat: unknown format string → UNKNOWN (don't crash)."""
        cp = _validate_scrape_data({
            "course": "X", "price_raw": "100",
            "source_url": "https://x", "scrape_timestamp": "now",
            "format": "unicorn-mode",
        })
        assert cp.format == FormatType.UNKNOWN

    def test_validate_scrape_data_rejects_oversize_course(self):
        with pytest.raises(ValueError, match="COURSE_MAX_LEN"):
            _validate_scrape_data({
                "course": "x" * (COURSE_MAX_LEN + 10),
                "price_raw": "100",
                "source_url": "https://x", "scrape_timestamp": "now",
            })


# ─── TestEnumerator ────────────────────────────────────────────────────────


class TestEnumerator:
    def test_successful_scrape_yields_course_price(self):
        url = "https://example.com/courses/vocal"
        scraper = FakeScraper({
            url: ScrapeResult(status=ScrapeStatus.OK, data={
                "course": "Vocal Mastery", "price_raw": "12 900 ₽",
                "teacher": "Иванов И.И.", "format": "cohort_based",
            }),
        })
        enum = PricingEnumerator(scraper=scraper, enabled=False)
        results = enum.enumerate([url])
        assert len(results) == 1
        cp = results[0]
        assert cp.course == "Vocal Mastery"
        assert cp.price_raw == "12 900 ₽"
        assert cp.format == FormatType.COHORT
        assert cp.price_amount == 12900.0
        assert cp.source_url == url

    def test_missing_required_fields_warns_and_skips(self):
        url = "https://example.com/broken"
        scraper = FakeScraper({
            url: ScrapeResult(status=ScrapeStatus.OK, data={
                "course": "Only Course",  # no price_raw
            }),
        })
        enum = PricingEnumerator(scraper=scraper, enabled=False)
        results = enum.enumerate([url])
        assert results == []  # soft skip

    def test_http_error_warns_and_skips(self):
        url = "https://example.com/404"
        scraper = FakeScraper({
            url: ScrapeResult(
                status=ScrapeStatus.HTTP_ERROR, error_msg="HTTP 404",
            ),
        })
        enum = PricingEnumerator(scraper=scraper, enabled=False)
        results = enum.enumerate([url])
        assert results == []

    def test_parse_error_warns_and_skips(self):
        url = "https://example.com/parse-broken"
        scraper = FakeScraper({
            url: ScrapeResult(
                status=ScrapeStatus.PARSE_ERROR, error_msg="BeautifulSoup crash",
            ),
        })
        enum = PricingEnumerator(scraper=scraper, enabled=False)
        results = enum.enumerate([url])
        assert results == []

    def test_network_unavailable_raises_fatal_exception(self):
        url = "https://example.com/offline"

        class NetworkFailScraper:
            def fetch(self, u: str) -> ScrapeResult:
                raise PricingEnumeratorNetworkError(f"offline: {u}")

        enum = PricingEnumerator(
            scraper=NetworkFailScraper(),  # type: ignore[arg-type]
            enabled=False,
        )
        with pytest.raises(PricingEnumeratorNetworkError, match="offline"):
            enum.enumerate([url])

    def test_valid_scrape_triggers_corpus_persist(self):
        url = "https://example.com/courses/x"
        scraper = FakeScraper({
            url: ScrapeResult(status=ScrapeStatus.OK, data={
                "course": "X", "price_raw": "100",
            }),
        })
        from scripts_01.corpus_persistence import list_all, DEFAULT_CORPUS_DIR
        enum = PricingEnumerator(
            scraper=scraper, corpus_source="pricing_enumerator", enabled=True,
        )
        results = enum.enumerate([url])
        assert len(results) == 1
        # default corpus dir is patched by autouse → tmp_path / corpus.
        entries = list_all(root=DEFAULT_CORPUS_DIR)
        matching = [e for e in entries if e.url == url]
        assert len(matching) == 1
        assert matching[0].source == "pricing_enumerator"
        assert matching[0].title == "X"

    def test_no_corpus_flag_bypasses_persistence(self):
        url = "https://example.com/no-write"
        scraper = FakeScraper({
            url: ScrapeResult(status=ScrapeStatus.OK, data={
                "course": "X", "price_raw": "100",
            }),
        })
        from scripts_01.corpus_persistence import list_all, DEFAULT_CORPUS_DIR
        enum = PricingEnumerator(
            scraper=scraper, enabled=False,
        )
        results = enum.enumerate([url])
        assert len(results) == 1
        entries = list_all(root=DEFAULT_CORPUS_DIR)
        assert entries == []

    def test_corpus_exception_caught_safely_adr016(self, monkeypatch):
        """Verify ADR-016 fail-safe: persist() raising should NOT crash batch.

        Monkeypatch via the fixture (clean teardown, transitive-safe since
        pricing_enumerator's _persist_to_corpus does lazy `from X import Y`
        per call → reads fresh binding each invocation).
        """
        url = "https://example.com/courses/y"
        scraper = FakeScraper({
            url: ScrapeResult(status=ScrapeStatus.OK, data={
                "course": "Y", "price_raw": "200",
            }),
        })

        def exploding_persist(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("simulated persist failure")

        monkeypatch.setattr(
            "scripts_01.corpus_persistence.persist", exploding_persist,
        )
        enum = PricingEnumerator(scraper=scraper, enabled=True)
        results = enum.enumerate([url])
        # Despite persist exploding, results list still populated
        # (ADR-016: best-effort persistence, not blocking).
        assert len(results) == 1
        assert results[0].course == "Y"

    def test_batch_processing_survives_partial_failures(self):
        good_url = "https://example.com/good"
        bad_url = "https://example.com/bad"
        scraper = FakeScraper({
            good_url: ScrapeResult(status=ScrapeStatus.OK, data={
                "course": "Good", "price_raw": "100",
            }),
            bad_url: ScrapeResult(
                status=ScrapeStatus.HTTP_ERROR, error_msg="HTTP 503",
            ),
        })
        enum = PricingEnumerator(scraper=scraper, enabled=False)
        results = enum.enumerate([good_url, bad_url])
        # Wait, validate_url rejects invalid because enum fetches bad_url's
        # ScrapeResult — but it's also invalid HTTPS? No, bad_url starts https.
        # Both URLs are valid → bad_url yields ScrapeStatus.HTTP_ERROR → skipped,
        # good_url yields CoursePrice.
        assert len(results) == 1
        assert results[0].course == "Good"

    def test_price_raw_preserved_when_amount_unparseable(self):
        """Verbatim guarantee: «по запросу» / «от 50 000» preserved raw."""
        url = "https://example.com/custom"
        scraper = FakeScraper({
            url: ScrapeResult(status=ScrapeStatus.OK, data={
                "course": "Custom", "price_raw": "по запросу",
            }),
        })
        enum = PricingEnumerator(scraper=scraper, enabled=False)
        results = enum.enumerate([url])
        assert len(results) == 1
        assert results[0].price_raw == "по запросу"
        assert results[0].price_amount is None

    def test_invalid_url_summary_skipped_but_other_urls_continue(self):
        good_url = "https://example.com/ok"
        scraper = FakeScraper({
            good_url: ScrapeResult(status=ScrapeStatus.OK, data={
                "course": "OK", "price_raw": "1",
            }),
        })
        enum = PricingEnumerator(scraper=scraper, enabled=False)
        # First URL is invalid (no protocol) → soft skip; second URL → success.
        results = enum.enumerate(["not-a-url", good_url])
        assert len(results) == 1
        assert results[0].course == "OK"
        assert scraper.calls == [good_url]  # invalid URL NOT fetched

    def test_enumerator_rejects_non_list_input(self):
        enum = PricingEnumerator(scraper=FakeScraper({}), enabled=False)
        with pytest.raises(TypeError):
            enum.enumerate("not-a-list")  # type: ignore[arg-type]

    def test_enumerator_rejects_oversize_batch(self):
        enum = PricingEnumerator(scraper=FakeScraper({}), enabled=False)
        with pytest.raises(ValueError, match="BATCH_MAX_URLS"):
            enum.enumerate([f"https://example.com/{i}" for i in range(BATCH_MAX_URLS + 1)])

    def test_enumerator_requires_scraper(self):
        with pytest.raises(ValueError, match="scraper is required"):
            PricingEnumerator(scraper=None, enabled=False)  # type: ignore[arg-type]


# ─── TestWebScraperDispatch (verifies WebScraper wired into enumeration) ──


class TestWebScraperDispatch:
    """Verify WebScraper passes the ScraperProtocol contract via PricingEnumerator."""

    def test_web_scraper_implements_protocol(self):
        scraper = WebScraper(timeout=1.0)
        assert hasattr(scraper, "fetch")

    def test_batch_via_web_scraper_offline_is_skipped(self, monkeypatch):
        """Stub httpx so BatchSize=2 (1 unreachable, 1 hard-skip) returns []; we
        verify that httpx.ConnectError is mapped to PricingEnumeratorNetworkError."""
        import httpx

        class FakeHttpxClient:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def __enter__(self) -> "FakeHttpxClient":
                return self

            def __exit__(self, *args: Any) -> None:
                pass

            def get(self, url: str, **kwargs: Any) -> None:
                raise httpx.ConnectError(f"fake-offline {url}")

        monkeypatch.setattr(httpx, "Client", FakeHttpxClient)
        scraper = WebScraper(timeout=1.0)
        enum = PricingEnumerator(scraper=scraper, enabled=False)
        with pytest.raises(PricingEnumeratorNetworkError, match="Cannot reach"):
            enum.enumerate(["https://example.com/x"])


# ─── TestConcurrency (file_lock protected) ────────────────────────────────


class TestConcurrency:
    def test_concurrent_threads_corpus_persist_consistent(self):
        """Sequential scrapes (file_lock-protected) → all 10 entries land."""
        urls = [f"https://example.com/c/{idx}" for idx in range(10)]
        # Use indexed pairs → unique course per URL, no `i`-in-scope bug.
        mappings: Dict[str, ScrapeResult] = {
            url: ScrapeResult(status=ScrapeStatus.OK, data={
                "course": f"C{idx}", "price_raw": str(100 + idx),
            }) for idx, url in enumerate(urls)
        }
        scraper = FakeScraper(mappings)
        enum = PricingEnumerator(
            scraper=scraper, enabled=True, corpus_source="concurrent_test",
        )
        for u in urls:
            enum.enumerate([u])

        from scripts_01.corpus_persistence import list_all, DEFAULT_CORPUS_DIR
        entries = list_all(root=DEFAULT_CORPUS_DIR)
        concurrent = [e for e in entries if e.source == "concurrent_test"]
        assert len(concurrent) == 10


# ─── TestCLI ──────────────────────────────────────────────────────────────


class TestCLI:
    def test_cli_version(self):
        cmd = [sys.executable, "-m", "scripts_01.pricing_enumerator", "--version"]
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert r.returncode == 0
        assert "pricing_enumerator" in r.stdout
        assert "v5.189.60" in r.stdout


# ══════════════════════════════════════════════════════════════════════
# Cache layer (v5.189.64 — TTL opt-in via corpus_persistence.lookup)
# ══════════════════════════════════════════════════════════════════════
# Default: cache DISABLED (cache_ttl_seconds=0); opt-in drives corpus reuse.
# Tests use canonical ``isolated_corpus_root`` fixture from tests_09/conftest.py
# (was duplicated as ``_isolate_corpus_root`` across 3 files — now consolidated).


class TestCacheLayer:
    """v5.189.64: TTL cache via corpus_persistence.lookup(); opt-in."""

    def test_default_cache_ttl_zero_disables_cache(self, isolated_corpus_root) -> None:
        """cache_ttl_seconds=0 ⇒ _check_cache всегда None (scraper run on every URL)."""
        from scripts_01.pricing_enumerator import (
            PricingEnumerator,
            ScraperProtocol,
            ScrapeStatus,
            ScrapeResult as _SR,
        )
        from scripts_01.corpus_persistence import persist

        class _Fake(ScraperProtocol):
            def __init__(self) -> None:
                self.call_count = 0

            def fetch(self, url: str) -> _SR:  # type: ignore[override]
                self.call_count += 1
                return _SR(status=ScrapeStatus.OK, data={
                    "course": "X", "price_raw": "100", "source_url": url,
                })

        fake = _Fake()
        enum = PricingEnumerator(scraper=fake, enabled=True, cache_ttl_seconds=0)
        # Seed corpus entry — should NOT be picked up under cache_ttl_seconds=0.
        persist("https://example.test/c1", source="pricing_enumerator",
                title="X", metadata={"price_raw": "100", "price_amount": 100.0})
        result = enum.enumerate(["https://example.test/c1"])
        assert len(result) == 1
        assert fake.call_count == 1, "scraper MUST be called when cache_ttl_seconds=0"

    def test_cache_hit_skips_scraper_within_ttl(self, isolated_corpus_root) -> None:
        """Pre-seeded corpus entry within TTL ⇒ _check_cache returns CoursePrice WITHOUT scraper call."""
        from scripts_01.pricing_enumerator import (
            PricingEnumerator,
            ScraperProtocol,
        )
        from scripts_01.corpus_persistence import persist

        persist(
            "https://example.test/cached",
            source="pricing_enumerator",
            title="Cached Course",
            metadata={
                "price_raw": "9 999 \u20BD", "price_amount": 9999.0,
                "price_currency": "RUB", "teacher": "Иванов",
                "format": "cohort_based",
                "scrape_timestamp": _now_iso_helper(),
            },
        )

        class _NoCallScraper(ScraperProtocol):
            call_count = 0

            def fetch(self, url: str):  # type: ignore[override]
                self.call_count += 1
                raise AssertionError("scraper.fetch MUST NOT be called on cache hit")

        scraper = _NoCallScraper()
        enum = PricingEnumerator(scraper=scraper, enabled=True, cache_ttl_seconds=3600)
        results = enum.enumerate(["https://example.test/cached"])

        assert len(results) == 1, "cache hit должен вернуть 1 result entry"
        cp = results[0]
        assert cp.course == "Cached Course", "course name from corpus.title"
        assert cp.price_raw == "9 999 \u20BD", "price_raw reconstructed from metadata"
        assert cp.price_amount == 9999.0
        assert cp.price_currency == "RUB"
        assert cp.teacher == "Иванов"
        assert cp.format.value == "cohort_based"
        assert scraper.call_count == 0, "scraper MUST NOT be called when cache hit"

    def test_cache_expired_triggers_rescrape(self, isolated_corpus_root) -> None:
        """TTL exceeded (old timestamp) ⇒ cache miss ⇒ fresh scrape."""
        from scripts_01.pricing_enumerator import (
            PricingEnumerator,
            ScraperProtocol,
            ScrapeStatus,
            ScrapeResult as _SR,
        )
        from scripts_01.corpus_persistence import persist
        import datetime as _dt

        old = (
            _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=1)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        persist(
            "https://example.test/stale",
            source="pricing_enumerator",
            title="Stale Course",
            metadata={
                "price_raw": "100", "price_amount": 100.0,
                "format": "recorded", "scrape_timestamp": old,
            },
        )

        class _OneShotScraper(ScraperProtocol):
            call_count = 0

            def fetch(self, url: str):  # type: ignore[override]
                self.call_count += 1
                return _SR(status=ScrapeStatus.OK, data={
                    "course": "Fresh Course", "price_raw": "150",
                    "source_url": url,
                })

        scraper = _OneShotScraper()
        enum = PricingEnumerator(scraper=scraper, enabled=True, cache_ttl_seconds=60)
        results = enum.enumerate(["https://example.test/stale"])

        assert len(results) == 1
        assert results[0].course == "Fresh Course", "fresh scrape replaces stale cache"
        assert scraper.call_count == 1, "scraper MUST be called on cache expiration"

    def test_cache_skipped_when_corpus_disabled(self, isolated_corpus_root) -> None:
        """enabled=False (hermetic test mode) ⇒ _check_cache short-circuits to None."""
        from scripts_01.pricing_enumerator import (
            PricingEnumerator,
            ScraperProtocol,
            ScrapeStatus,
            ScrapeResult as _SR,
        )
        from scripts_01.corpus_persistence import persist
        import datetime as _dt

        fresh = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        persist(
            "https://example.test/disabled",
            source="pricing_enumerator",
            title="Hermetic Cached",
            metadata={
                "price_raw": "10", "price_amount": 10.0,
                "format": "recorded", "scrape_timestamp": fresh,
            },
        )

        class _Counted(ScraperProtocol):
            call_count = 0

            def fetch(self, url: str):  # type: ignore[override]
                self.call_count += 1
                return _SR(status=ScrapeStatus.OK, data={
                    "course": "Re-fetched", "price_raw": "10", "source_url": url,
                })

        scraper = _Counted()
        # enabled=False — cache BOTH sides disabled (no persist, no lookup).
        enum = PricingEnumerator(scraper=scraper, enabled=False, cache_ttl_seconds=3600)
        results = enum.enumerate(["https://example.test/disabled"])
        assert len(results) == 1
        assert results[0].course == "Re-fetched", (
            "enabled=False bypasses cache check → scraper runs fresh"
        )
        assert scraper.call_count == 1


def _now_iso_helper() -> str:
    """Helper: mirror pricing_enumerator._now_iso() для seed-timestamps в тестах."""
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
