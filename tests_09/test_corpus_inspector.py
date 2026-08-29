"""tests_09/test_corpus_inspector.py — 8 hermetic tests для scripts_01/corpus_inspector.py.

Per-prompt 098 (corpus_inspector):
- Stats aggregate (counts per source, age buckets, top domains)
- Dedup URL-variant detection (tracking-param stripping + semantic param preservation)
- Evict dry-run + apply (whole-file unlink for fully-stale; partial-evict atomic)
- TTL validation (reject negative days)
- All tests use ``tmp_path`` (no pollution of real ``data_13/corpus``).

Pattern follows ``tests_09/test_corpus_persistence.py``:
- ``_isolate_corpus_root`` autouse monkey-patches ``DEFAULT_CORPUS_DIR`` to tmp.
- All CLI subprocess smoke tests use ``sys.executable`` для Termux-compat (§5.1).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
***REMOVED***
from typing import Any, Dict, List

import pytest

# Import модуля under test.
from scripts_01 import corpus_inspector

# Constants re-exported для test clarity (avoid magic numbers).
from scripts_01.corpus_inspector import (
    AGE_BUCKETS,
    TRACKING_PARAMS,
    VariantGroup,
    dedup,
    evict,
    stats,
)
from scripts_01.corpus_persistence import (
    DEFAULT_CORPUS_DIR,
    FILE_LOCK,
    persist,
    _sha256_url,
)


# ─── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    """Hermetic corpus root. Mirror of fixture in test_corpus_persistence."""
    return tmp_path / "corpus"


@pytest.fixture(autouse=True)
def _isolate_corpus_root(monkeypatch, corpus_root) -> None:
    """Override DEFAULT_CORPUS_DIR в BOTH modules.

    Why both: ``from scripts_01.corpus_persistence import DEFAULT_CORPUS_DIR``
    creates a SNAPSHOT binding в the consumer module's namespace (CPython import
    semantics). monkeypatch a module attribute в corpus_persistence does НЕ
    re-bind the snapshot в corpus_inspector. Patch BOTH для hermetic isolation.
    """
    monkeypatch.setattr(
        "scripts_01.corpus_persistence.DEFAULT_CORPUS_DIR", corpus_root,
    )
    monkeypatch.setattr(
        "scripts_01.corpus_inspector.DEFAULT_CORPUS_DIR", corpus_root,
    )


# ─── helpers (test-only) ─────────────────────────────────────────────────────


def _persist_with_timestamp(
    url: str, source: str, timestamp: str, root: Path,
) -> None:
    """Persist entry with explicit (overridden) timestamp — для deterministic age tests.

    Workaround: ``persist()`` auto-stamps with ``_now_iso()``, so tests cannot use
    it directly for age-bucket assertions. Instead, write the JSONL file directly
    with chosen timestamps.
    """
    from scripts_01.corpus_persistence import _entry_path
    path = _entry_path(url, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = dict(
        url=url, source=source, timestamp=timestamp, title=None, metadata={***REMOVED***,
    )
    # Hand-write ONE jsonl line; append if file exists.
    if path.is_file():
        mode = "a"
        new_content_getter = lambda existing: existing + json.dumps(
            record, ensure_ascii=False,
        ) + "\n"
    else:
        mode = "w"
        new_content_getter = lambda existing: json.dumps(
            record, ensure_ascii=False,
        ) + "\n"
    existing = path.read_text(encoding="utf-8") if mode == "a" else ""
    path.write_text(new_content_getter(existing), encoding="utf-8")


# ─── 1. test_stats_calculates_age_buckets_correctly ──────────────────────────


class TestStats:
    def test_stats_calculates_age_buckets_correctly(self, corpus_root):
        """4-bucket distribution computed correctly per now()-timestamp delta."""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc).replace(microsecond=0)

        # 3 distinct URLs across 4 age buckets (some share source for variety).
        fixtures: List[Dict[str, str***REMOVED******REMOVED*** = [
            # <7d (3 days old)
            {"url": "https://fresh.example.com/a", "ts": (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")***REMOVED***,
            # 7-30d (15 days old)
            {"url": "https://warm.example.com/b", "ts": (now - timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ")***REMOVED***,
            # 30-90d (60 days old)
            {"url": "https://stale.example.com/c", "ts": (now - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")***REMOVED***,
            # >90d (180 days old)
            {"url": "https://ancient.example.com/d", "ts": (now - timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")***REMOVED***,
        ***REMOVED***
        for fx in fixtures:
            _persist_with_timestamp(
                fx["url"***REMOVED***, "research_web", fx["ts"***REMOVED***, root=corpus_root,
            )

        result = stats(root=corpus_root)

        # Assert: 4 entries total, 1 per bucket.
        assert result["total"***REMOVED*** == 4
        assert result["by_source"***REMOVED*** == {"research_web": 4***REMOVED***
        assert result["by_age_bucket"***REMOVED*** == {"<7d": 1, "7-30d": 1, "30-90d": 1, ">90d": 1***REMOVED***
        # No invalid timestamps.
        assert result["invalid_timestamp_count"***REMOVED*** == 0

    def test_stats_handles_invalid_timestamps_gracefully(self, corpus_root):
        """Malformed timestamps → invalid_count; не валят stats."""
        # Mix valid + invalid.
        _persist_with_timestamp(
            "https://valid.example.com", "research_web",
            # Valid: now-derived fixed time.
            "2026-08-01T00:00:00Z", root=corpus_root,
        )
        _persist_with_timestamp(
            "https://bad.example.com", "manual",
            "NOT-A-VALID-TIMESTAMP", root=corpus_root,
        )
        _persist_with_timestamp(
            "https://empty.example.com", "manual",
            "", root=corpus_root,
        )

        result = stats(root=corpus_root)
        assert result["total"***REMOVED*** == 3
        # Exactly 2 entries with bad timestamps (1 valid → bucket).
        assert result["invalid_timestamp_count"***REMOVED*** == 2
        # The 1 valid entry DID land in some bucket (computed against now()).
        assert sum(result["by_age_bucket"***REMOVED***.values()) == 1

    def test_stats_top_domains_sorted_by_count(self, corpus_root):
        """top_domains — top-10 sorted by count desc, tie-break by domain asc."""
        # Build skewed distribution.
        for i in range(5):
            _persist_with_timestamp(
                f"https://alpha.com/{i***REMOVED***", "research_web",
                "2026-08-01T00:00:00Z", root=corpus_root,
            )
        for i in range(3):
            _persist_with_timestamp(
                f"https://beta.com/{i***REMOVED***", "manual",
                "2026-08-01T00:00:00Z", root=corpus_root,
            )
        _persist_with_timestamp(
            "https://gamma.com/only", "research_web",
            "2026-08-01T00:00:00Z", root=corpus_root,
        )

        result = stats(root=corpus_root)
        top = result["top_domains"***REMOVED***
        # alpha.com (5) → first; beta.com (3) → second; gamma.com (1) → third.
        assert [d["domain"***REMOVED*** for d in top***REMOVED*** == ["alpha.com", "beta.com", "gamma.com"***REMOVED***
        assert [d["count"***REMOVED*** for d in top***REMOVED*** == [5, 3, 1***REMOVED***


# ─── 2. test_dedup_groups_tracking_variants_properly ─────────────────────────


class TestDedup:
    def test_dedup_groups_tracking_variants(self, corpus_root):
        """Strategy C: variants of same canonical (stripped tracking) → cluster."""
        # 3 URLs should canonicalize to same canonical (strip utm_* + ref + fragment).
        # Note: same canonical = same netloc + same path after trailing-slash collapse.
        for url in [
            "https://example.com/article",
            "https://example.com/article?utm_source=twitter",
            "https://example.com/article?utm_source=twitter&utm_campaign=foo#section-1",
        ***REMOVED***:
            _persist_with_timestamp(
                url, "research_web", "2026-08-01T00:00:00Z", root=corpus_root,
            )
        # Add an unrelated URL — should NOT cluster.
        _persist_with_timestamp(
            "https://other.com/post", "research_web",
            "2026-08-01T00:00:00Z", root=corpus_root,
        )

        groups = dedup(root=corpus_root)
        # Filter to multi-variant groups (singletons excluded per design doc).
        example_groups = [g for g in groups if "example.com" in g.canonical***REMOVED***
        assert len(example_groups) == 1
        g = example_groups[0***REMOVED***
        assert g.canonical == "https://example.com/article"
        assert g.count == 3
        assert g.occurrences == 3
        assert len(g.variants) == 3

    def test_dedup_preserves_semantic_query_params(self, corpus_root):
        """?page=1 != ?page=2 (semantic params — no cluster)."""
        for url in [
            "https://example.com/doc?page=1",
            "https://example.com/doc?page=2",
            "https://example.com/doc?page=3",
        ***REMOVED***:
            _persist_with_timestamp(
                url, "research_web", "2026-08-01T00:00:00Z", root=corpus_root,
            )

        groups = dedup(root=corpus_root)
        # All 3 should be singletons → no cluster in `groups`.
        assert groups == [***REMOVED***

    def test_dedup_cross_source_count_vs_occurrences(self, corpus_root):
        """Same canonical URL across 2 sources → count=2 (unique URLs),
        occurrences=3 (total source-occurrences incl. duplicates).

        Закрывает reentrant gap в dedup-семантике: single-source scenario
        давал count==occurrences всегда (coincidence); этот тест exercise'ит
        discrimination между ``count`` (unique URLs) и ``occurrences``
        (total source-entries).
        """
        # 3 URLs pointing to same canonical:
        # - 1 entry from research_web (canonical URL itself)
        # - 1 entry from research_web (utm-variant)
        # - 1 entry from manual (utm-variant)
        # → 2 unique URLs (canonical variant of research_web counted once),
        # but 3 total source-occurrences.
        _persist_with_timestamp(
            "https://example.com/article",
            "research_web", "2026-08-01T00:00:00Z", root=corpus_root,
        )
        _persist_with_timestamp(
            "https://example.com/article?utm_source=twitter",
            "research_web", "2026-08-01T00:00:00Z", root=corpus_root,
        )
        _persist_with_timestamp(
            "https://example.com/article?utm_source=twitter",
            "manual", "2026-08-01T00:00:00Z", root=corpus_root,
        )

        groups = dedup(root=corpus_root)
        example_groups = [g for g in groups if "example.com" in g.canonical***REMOVED***
        assert len(example_groups) == 1
        g = example_groups[0***REMOVED***
        # 2 unique original URLs (canonical self + utm=twitter variant).
        assert g.count == 2
        # 3 total source-occurrences: 2x research_web + 1x manual.
        assert g.occurrences == 3
        # count < occurrences — discrimination correctly tested.
        assert g.count < g.occurrences
        # Variants list has 2 distinct URLs.
        assert sorted(g.variants) == sorted([
            "https://example.com/article",
            "https://example.com/article?utm_source=twitter",
        ***REMOVED***)
    def test_evict_dry_run_does_not_delete_files(self, corpus_root):
        """Dry-run (default) → preview only, NO file deletion."""
        # 3 entries older than 100 days.
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc).replace(microsecond=0)
        old_ts = (now - timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for url in [
            "https://old-1.example.com",
            "https://old-2.example.com",
            "https://old-3.example.com",
        ***REMOVED***:
            _persist_with_timestamp(
                url, "research_web", old_ts, root=corpus_root,
            )

        files_before = sorted(p.name for p in corpus_root.glob("*.jsonl"))
        assert len(files_before) == 3

        # Dry-run (apply=False default).
        report = evict(older_than_days=90, apply=False, root=corpus_root)
        assert report["mode"***REMOVED*** == "dry-run"
        # Dry-run reports what WOULD be removed.
        assert report["removed_files"***REMOVED*** == 3
        assert report["removed_entries"***REMOVED*** == 3
        assert report["kept_entries"***REMOVED*** == 0
        assert report["warnings"***REMOVED*** == [***REMOVED***

        # Files STILL on disk (dry-run doesn't mutate).
        files_after = sorted(p.name for p in corpus_root.glob("*.jsonl"))
        assert files_after == files_before

    def test_evict_apply_unlinks_fully_stale_files(self, corpus_root):
        """Apply=True + all entries stale → whole-file unlink (Strategy B)."""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc).replace(microsecond=0)
        old_ts = (now - timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for url in [
            "https://stale-1.example.com",
            "https://stale-2.example.com",
        ***REMOVED***:
            _persist_with_timestamp(
                url, "research_web", old_ts, root=corpus_root,
            )

        assert len(list(corpus_root.glob("*.jsonl"))) == 2

        report = evict(older_than_days=90, apply=True, root=corpus_root)
        assert report["mode"***REMOVED*** == "apply"
        assert report["removed_files"***REMOVED*** == 2
        assert report["removed_entries"***REMOVED*** == 2
        assert report["kept_entries"***REMOVED*** == 0
        # NO .tmp leftover (atomic replacements or unlinks).
        tmp_files = list(corpus_root.glob("*.tmp"))
        assert tmp_files == [***REMOVED***
        # Files actually gone.
        jsonl_files = list(corpus_root.glob("*.jsonl"))
        assert jsonl_files == [***REMOVED***

    def test_evict_apply_partial_evicts_mixed_age_files_atomically(
        self, corpus_root,
    ):
        """Mixed-age file (1 stale, 1 fresh) — atomic partial evict + file kept."""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc).replace(microsecond=0)
        old_ts = (now - timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
        fresh_ts = (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # SAME url — 2 entries (different sources): research_web (stale) + manual (fresh).
        # Corpus_persistence Option-C: one jsonl per URL, multiple sources per file.
        _persist_with_timestamp(
            "https://mixed.example.com", "research_web", old_ts,
            root=corpus_root,
        )
        _persist_with_timestamp(
            "https://mixed.example.com", "manual", fresh_ts,
            root=corpus_root,
        )

        # Before: 1 file with 2 entries.
        before_files = list(corpus_root.glob("*.jsonl"))
        assert len(before_files) == 1

        report = evict(older_than_days=90, apply=True, root=corpus_root)
        assert report["mode"***REMOVED*** == "apply"
        assert report["considered_files"***REMOVED*** == 1
        # Partial eviction: removed 1 (research_web stale), kept 1 (manual fresh).
        assert report["removed_entries"***REMOVED*** == 1
        assert report["kept_entries"***REMOVED*** == 1
        # Whole file NOT removed (kept entry present).
        assert report["removed_files"***REMOVED*** == 0

        # After: file STILL exists with 1 entry (manual/fresh source).
        after_files = list(corpus_root.glob("*.jsonl"))
        assert len(after_files) == 1
        # Re-read: only the fresh entry remains.
        records = [
            json.loads(line) for line in after_files[0***REMOVED***.read_text(
                encoding="utf-8",
            ).splitlines() if line
        ***REMOVED***
        assert len(records) == 1
        assert records[0***REMOVED***["source"***REMOVED*** == "manual"
        assert records[0***REMOVED***["timestamp"***REMOVED*** == fresh_ts
        # No .tmp leftover (atomic write verifies).
        assert list(corpus_root.glob("*.tmp")) == [***REMOVED***

    def test_evict_rejects_negative_ttl(self, corpus_root):
        """older_than_days < 0 → ValueError (NOT silently allowed)."""
        with pytest.raises(ValueError, match="non-negative"):
            evict(older_than_days=-5, apply=False, root=corpus_root)

    def test_evict_zero_days_boundary_evicts_older_than_now(
        self, corpus_root,
    ):
        """older_than_days=0 → cutoff=now(); entries strictly older than now evict.

        Contract: ``older_than_days=0`` semantic is ``cutoff = now - timedelta(0) = now``;
        entries with ``parsed < cutoff`` evict. Именно так any non-'now' entry evicted.
        An entry stamped EXACTLY at now() stays (because ``parsed < cutoff`` is False
        для equality).
        """
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc).replace(microsecond=0)
        # Entry stamped 1 second ago — strictly older than now-stamped reference.
        old_ts = (now - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _persist_with_timestamp(
            "https://just-old.example.com",
            "research_web", old_ts, root=corpus_root,
        )

        report = evict(older_than_days=0, apply=True, root=corpus_root)
        assert report["mode"***REMOVED*** == "apply"
        assert report["removed_files"***REMOVED*** == 1
        assert report["removed_entries"***REMOVED*** == 1
        assert len(list(corpus_root.glob("*.jsonl"))) == 0

    def test_evict_root_none_resolves_to_default_corpus_dir(
        self, monkeypatch, tmp_path,
    ):
        """HERMETICITY CONTRACT (v5.189.58 code-reviewer fix):

        ``evict(root=None)`` ДОЛЖЕН reads/writes the autouse-patched directory
        (computed от ``DEFAULT_CORPUS_DIR`` snapshot attr bei `from import`),
        НЕ a hard-coded ``data_13/corpus``. autouse fixture patches BOTH
        modules' ``DEFAULT_CORPUS_DIR`` (because ``from X import Y`` makes a
        snapshot binding).

        Body of this test patches NOTHING — relies on autouse fixture alone
        (avoids self-defeating earlier draft).
        """
        from datetime import datetime, timezone, timedelta
        from scripts_01.corpus_persistence import _entry_path
        from scripts_01 import corpus_inspector as ci_mod

        # After autouse fixture, ci_mod.DEFAULT_CORPUS_DIR points to the
        # isolated tmp dir (NOT real data_13/corpus).
        isolated_root = Path(ci_mod.DEFAULT_CORPUS_DIR)
        # Write ONE stale entry into the isolated dir.
        url = "https://autouse-default.example.com/evict-test"
        old_ts = (
            datetime.now(timezone.utc)
            - timedelta(days=120)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        jsonl_path = _entry_path(url, root=isolated_root)
        # Ensure parent dir exists (autouse fixture creates isolated_root as
        # tmp_path/"corpus" but the sha256 file deeper в tree needs explicit
        # mkdir since direct write_text doesn't create intermediate dirs).
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        jsonl_path.write_text(
            json.dumps({
                "url": url, "source": "test", "timestamp": old_ts,
                "title": None, "metadata": {***REMOVED***,
            ***REMOVED***, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        # Now call evict WITHOUT explicit root — uses autouse-isolated dir.
        report = evict(older_than_days=90, apply=True, root=None)
        assert report["removed_files"***REMOVED*** >= 1
        assert report["removed_entries"***REMOVED*** >= 1
        # File we placed in isolated dir is gone (proves evict read FROM
        # autouse-patched dir, NOT FROM real data_13/corpus).
        assert not jsonl_path.exists()

    def test_stats_empty_root_returns_zeros(self, tmp_path):
        """``stats(root=tmp_path/empty)`` → dict with all-zero schema fields.

        Critical contract: caller (CLI / downstream tool) can rely на schema
        keys being present и empty values, NOTKEYERROR.
        """
        empty_root = tmp_path / "empty_corpus"
        empty_root.mkdir(parents=True, exist_ok=True)
        # Empty → no .jsonl files.
        result = stats(root=empty_root)
        # Schema-presence SUBSET check (forward-compat: future additional keys
        # don't break this test, but accidental drops ARE caught).
        expected_keys = {
            "by_source", "total", "by_age_bucket",
            "top_domains", "invalid_timestamp_count",
        ***REMOVED***
        assert expected_keys <= set(result.keys()), (
            f"stats() missing required keys: "
            f"{expected_keys - set(result.keys())***REMOVED***"
        )
        # All-zero values.
        assert result["total"***REMOVED*** == 0
        assert result["by_source"***REMOVED*** == {***REMOVED***
        assert result["by_age_bucket"***REMOVED*** == {b: 0 for b in AGE_BUCKETS***REMOVED***
        assert result["top_domains"***REMOVED*** == [***REMOVED***
        assert result["invalid_timestamp_count"***REMOVED*** == 0

    def test_cli_evict_negative_ttl_argparse_rejects(self, corpus_root):
        """CLI: ``--older-than-days -1`` → argparse error exit 2."""
        cmd = [
            sys.executable, "-m", "scripts_01.corpus_inspector",
            "--root", str(corpus_root),
            "evict", "--older-than-days", "-1",
        ***REMOVED***
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 2
        assert "non-negative" in result.stderr.lower() or "older-than-days" in result.stderr

    def test_cli_version(self, corpus_root):
        """Smoke: --version exits 0 with version string."""
        cmd = [
            sys.executable, "-m", "scripts_01.corpus_inspector",
            "--version",
        ***REMOVED***
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0
        assert "corpus_inspector" in result.stdout
        assert "v5.189.58" in result.stdout

    def test_cli_stats_json_outputs_machine_readable(self, corpus_root):
        """CLI: --json emits stable JSON shape, parseable."""
        _persist_with_timestamp(
            "https://cli-test.example.com", "research_web",
            "2026-08-01T00:00:00Z", root=corpus_root,
        )
        cmd = [
            sys.executable, "-m", "scripts_01.corpus_inspector",
            "--root", str(corpus_root),
            "stats", "--json",
        ***REMOVED***
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        # Verify stable schema (per promise).
        assert set(payload.keys()) >= {
            "total", "by_source", "by_age_bucket",
            "top_domains", "invalid_timestamp_count",
        ***REMOVED***
        assert payload["total"***REMOVED*** == 1
        assert payload["by_source"***REMOVED***["research_web"***REMOVED*** == 1

    def test_cli_dedup_json_outputs_machine_readable(self, corpus_root):
        """CLI: ``dedup --json`` → list of variant-group objects."""
        # 3 URLs → same canonical (1 cluster with 3 unique variants).
        for url in [
            "https://example.com/doc",
            "https://example.com/doc?utm_source=tw",
            "https://example.com/doc?utm_source=tw&utm_medium=email",
        ***REMOVED***:
            _persist_with_timestamp(
                url, "research_web", "2026-08-01T00:00:00Z",
                root=corpus_root,
            )
        cmd = [
            sys.executable, "-m", "scripts_01.corpus_inspector",
            "--root", str(corpus_root),
            "dedup", "--json",
        ***REMOVED***
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0, (
            f"dedup --json failed: stdout={result.stdout***REMOVED***, "
            f"stderr={result.stderr***REMOVED***"
        )
        payload = json.loads(result.stdout)
        assert isinstance(payload, list)
        assert len(payload) == 1
        # Verify cluster shape (canonical + variants + count + occurrences).
        cluster = payload[0***REMOVED***
        assert set(cluster.keys()) >= {
            "canonical", "variants", "count", "occurrences",
        ***REMOVED***
        assert cluster["canonical"***REMOVED*** == "https://example.com/doc"
        assert cluster["count"***REMOVED*** == 3
        assert cluster["occurrences"***REMOVED*** == 3

    def test_cli_evict_json_dry_run_report(self, corpus_root):
        """CLI: ``evict --older-than-days N --json`` (no --apply) → dry-run JSON."""
        from datetime import datetime, timezone, timedelta
        old_ts = (
            datetime.now(timezone.utc) - timedelta(days=120)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        for url in ["https://old.example.com/a", "https://old.example.com/b"***REMOVED***:
            _persist_with_timestamp(
                url, "research_web", old_ts, root=corpus_root,
            )
        # Dry-run (no --apply).
        cmd = [
            sys.executable, "-m", "scripts_01.corpus_inspector",
            "--root", str(corpus_root),
            "evict", "--older-than-days", "90", "--json",
        ***REMOVED***
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0, (
            f"evict --json dry-run failed: stderr={result.stderr***REMOVED***"
        )
        payload = json.loads(result.stdout)
        # Verify dry-run report schema (mode + counts + warnings).
        assert set(payload.keys()) >= {
            "mode", "removed_files", "removed_entries",
            "kept_entries", "considered_files", "warnings",
        ***REMOVED***
        assert payload["mode"***REMOVED*** == "dry-run"
        assert payload["removed_files"***REMOVED*** == 2
        assert payload["removed_entries"***REMOVED*** == 2
        # Dry-run default → files STILL on disk.
        assert len(list(corpus_root.glob("*.jsonl"))) == 2
