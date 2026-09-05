"""tests_09/test_corpus_persistence.py — Tests for scripts_01/corpus_persistence.py.

Per-prompt 096 + design validation (Option C schema):
- 9 test cases covering persist (new + idempotent overwrite + multi-source),
  lookup (found / empty / URL validation), lookup_by_source, list_all, stats,
  corrupt jsonl recovery, atomic write (no leftover .tmp), CLI smoke.
- Все тесты используют ``root=tmp_path`` (hermetic, не загрязняет ``data_13/``).
- CLI subprocess smoke использует ``sys.executable`` вместо ``python`` (Termux §5.1).
"""

from __future__ import annotations

import json
import subprocess
import sys
***REMOVED***

import pytest

from scripts_01.corpus_persistence import (
    CorpusEntry,
    DEFAULT_CORPUS_DIR,
    MAX_URL_LEN,
    PersistResult,
    _entry_path,
    _sha256_url,
    clear,
    list_all,
    lookup,
    lookup_by_source,
    persist,
    stats,
)


# ─── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    """Hermetic corpus root (avoids polluting real ``data_13/corpus``)."""
    return tmp_path / "corpus"


@pytest.fixture(autouse=True)
def _isolate_corpus_root(monkeypatch, corpus_root) -> None:
    """Override DEFAULT_CORPUS_DIR → test tmp; covers persist/lookup если None root."""
    monkeypatch.setattr("scripts_01.corpus_persistence.DEFAULT_CORPUS_DIR", corpus_root)


# ─── helpers / happy paths ───────────────────────────────────────────────────


class TestSha256Key:
    def test_sha256_url_returns_64_hex(self):
        key = _sha256_url("https://example.com")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_sha256_distinguishes_trailing_slash(self):
        # design §3: raw URL (не normalized) → trailing slash даёт другой ключ.
        assert _sha256_url("https://example.com") != _sha256_url(
            "https://example.com/"
        )

    def test_entry_path_uses_sha256(self, corpus_root):
        p = _entry_path("https://example.com", root=corpus_root)
        assert p.name.endswith(".jsonl")
        assert p.stem == _sha256_url("https://example.com")
        assert p.parent == corpus_root


# ─── persist() ───────────────────────────────────────────────────────────────


class TestPersist:
    def test_persist_new_url_creates_jsonl_with_correct_record(
        self, corpus_root,
    ):
        result = persist(
            "https://example.com/article",
            "research_web",
            title="Article Title",
            metadata={"status": 200***REMOVED***,
            root=corpus_root,
        )
        assert isinstance(result, PersistResult)
        assert result.is_duplicate is False
        assert isinstance(result.entry, CorpusEntry)
        assert result.entry.url == "https://example.com/article"
        assert result.entry.source == "research_web"
        assert result.entry.title == "Article Title"
        assert result.entry.metadata == {"status": 200***REMOVED***
        assert result.entry.timestamp.endswith("Z")  # UTC ISO

        # File system: one JSONL in corpus_root, one record, valid JSON.
        jsonl_files = list(corpus_root.glob("*.jsonl"))
        assert len(jsonl_files) == 1
        records = [
            json.loads(line) for line in jsonl_files[0***REMOVED***.read_text(encoding="utf-8").splitlines() if line
        ***REMOVED***
        assert len(records) == 1
        assert records[0***REMOVED***["url"***REMOVED*** == "https://example.com/article"
        assert records[0***REMOVED***["source"***REMOVED*** == "research_web"

    def test_persist_idempotent_overwrites_same_source(self, corpus_root):
        persist(
            "https://example.com", "research_web", title="First",
            root=corpus_root,
        )
        result2 = persist(
            "https://example.com", "research_web", title="Second",
            metadata={"updated": True***REMOVED***, root=corpus_root,
        )
        # is_duplicate=True (existing record для "research_web" был перезаписан).
        assert result2.is_duplicate is True
        # File still has only ONE record для "research_web".
        records = lookup("https://example.com", root=corpus_root)
        assert len(records) == 1
        assert records[0***REMOVED***.title == "Second"     # новая запись
        assert records[0***REMOVED***.metadata == {"updated": True***REMOVED***

    def test_persist_different_source_appends_record(self, corpus_root):
        persist("https://example.com", "research_web", root=corpus_root)
        result2 = persist(
            "https://example.com", "manual", title="Manual bookmark",
            root=corpus_root,
        )
        # Different source → append, NOT overwrite.
        assert result2.is_duplicate is False
        records = lookup("https://example.com", root=corpus_root)
        assert len(records) == 2
        sources = {r.source for r in records***REMOVED***
        assert sources == {"research_web", "manual"***REMOVED***

    def test_persist_atomic_write_no_leftover_tmp(self, corpus_root):
        persist("https://example.com", "research_web", root=corpus_root)
        # After successful persist, no .tmp files in corpus_root.
        tmp_files = list(corpus_root.glob("*.tmp"))
        assert tmp_files == [***REMOVED***, f"atomic write leaked tmp files: {tmp_files***REMOVED***"

    def test_persist_three_sources_for_one_url(self, corpus_root):
        for src in ("research_web", "manual", "research_factory"):
            persist("https://example.com", src, root=corpus_root)
        records = lookup("https://example.com", root=corpus_root)
        assert len(records) == 3
        assert {r.source for r in records***REMOVED*** == {
            "research_web", "manual", "research_factory",
        ***REMOVED***

    def test_persist_handles_cyrillic_url(self, corpus_root):
        # Cyrillic URL (percent-encoded UTF-8).
        url = "https://пример.рф/path"
        result = persist(url, "research_web", root=corpus_root)
        assert result.is_duplicate is False
        records = lookup(url, root=corpus_root)
        assert len(records) == 1
        assert records[0***REMOVED***.url == url


# ─── URL validation (security guard) ─────────────────────────────────────────


class TestUrlValidation:
    def test_rejects_non_string(self, corpus_root):
        with pytest.raises(TypeError):
            persist(12345, "research_web", root=corpus_root)

    @pytest.mark.parametrize("bad_url", [
        "",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "ftp://example.com",
        "not-a-url",
    ***REMOVED***)
    def test_rejects_non_http_schemes(self, corpus_root, bad_url):
        with pytest.raises(ValueError):
            persist(bad_url, "research_web", root=corpus_root)

    def test_rejects_url_over_max_len(self, corpus_root):
        long_url = "https://example.com/" + "a" * (MAX_URL_LEN + 100)
        with pytest.raises(ValueError, match="DoS hardcap"):
            persist(long_url, "research_web", root=corpus_root)

    def test_rejects_empty_source(self, corpus_root):
        with pytest.raises(ValueError, match="source"):
            persist("https://example.com", "", root=corpus_root)

    def test_rejects_non_string_source(self, corpus_root):
        with pytest.raises(ValueError):
            persist("https://example.com", 42, root=corpus_root)  # type: ignore[arg-type***REMOVED***


# ─── lookup / lookup_by_source / list_all / stats ────────────────────────────


class TestLookup:
    def test_lookup_returns_empty_for_unknown_url(self, corpus_root):
        assert lookup("https://never-seen.example.com", root=corpus_root) == [***REMOVED***

    def test_lookup_returns_all_sources(self, corpus_root):
        persist("https://example.com", "research_web", root=corpus_root)
        persist("https://example.com", "manual", root=corpus_root)
        records = lookup("https://example.com", root=corpus_root)
        assert len(records) == 2

    def test_lookup_unknown_source_returns_empty(self, corpus_root):
        persist("https://example.com", "research_web", root=corpus_root)
        assert lookup_by_source(
            "never_used_source", root=corpus_root,
        ) == [***REMOVED***

    def test_lookup_by_source_filters_correctly(self, corpus_root):
        persist("https://a.example.com", "research_web", root=corpus_root)
        persist("https://b.example.com", "research_web", root=corpus_root)
        persist("https://c.example.com", "manual", root=corpus_root)
        web = lookup_by_source("research_web", root=corpus_root)
        assert len(web) == 2
        assert all(r.source == "research_web" for r in web)

    def test_list_all_returns_everything(self, corpus_root):
        for i in range(3):
            persist(
                f"https://example.com/{i***REMOVED***", "research_web",
                root=corpus_root,
            )
        assert len(list_all(root=corpus_root)) == 3

    def test_stats_counts_per_source(self, corpus_root):
        persist("https://a.example.com", "research_web", root=corpus_root)
        persist("https://b.example.com", "research_web", root=corpus_root)
        persist("https://c.example.com", "manual", root=corpus_root)
        s = stats(root=corpus_root)
        assert s == {"research_web": 2, "manual": 1***REMOVED***

    def test_list_all_empty_when_dir_missing(self, tmp_path):
        # corpus_root doesn't exist yet → empty
        fresh_root = tmp_path / "fresh_corpus"
        assert not fresh_root.is_dir()
        assert list_all(root=fresh_root) == [***REMOVED***
        assert stats(root=fresh_root) == {***REMOVED***


# ─── corrupt jsonl recovery ──────────────────────────────────────────────────


class TestCorruptJsonlRecovery:
    def test_lookup_skips_corrupt_lines_without_failing(self, corpus_root):
        # First persist a real record.
        persist("https://example.com", "research_web", root=corpus_root)
        # Now manually corrupt the jsonl by appending garbage.
        path = next(corpus_root.glob("*.jsonl"))
        with path.open("a", encoding="utf-8") as f:
            f.write("THIS_IS_NOT_VALID_JSON\n")
            f.write("{partial json\n")

        # lookup should NOT crash; should return the valid record and skip corrupt.
        records = lookup("https://example.com", root=corpus_root)
        assert len(records) == 1
        assert isinstance(records[0***REMOVED***, CorpusEntry)
        assert records[0***REMOVED***.source == "research_web"


# ─── atomicity: cleanup tmp after error ──────────────────────────────────────


class TestAtomicWrite:
    def test_persist_replaces_existing_file_atomically(self, corpus_root):
        # Persist once (creates file).
        persist("https://a.example.com", "research_web", root=corpus_root)
        # Persist same URL/source — atomic replace should leave NO .tmp.
        persist("https://a.example.com", "research_web", root=corpus_root)
        # No leftover tmp files.
        tmp_files = list(corpus_root.glob("*.tmp"))
        assert tmp_files == [***REMOVED***


# ─── CorpusEntry.from_dict robustness ────────────────────────────────────────


class TestCorpusEntryFromDict:
    def test_from_dict_ignores_unknown_keys(self):
        e = CorpusEntry.from_dict({
            "url": "https://example.com",
            "source": "manual",
            "timestamp": "2026-08-20T12:00:00Z",
            "extra_future_field": "ignored",
        ***REMOVED***)
        assert e.url == "https://example.com"
        assert e.source == "manual"

    def test_from_dict_handles_missing_metadata(self):
        e = CorpusEntry.from_dict({
            "url": "https://example.com",
            "source": "manual",
            "timestamp": "2026-08-20T12:00:00Z",
        ***REMOVED***)
        assert e.metadata == {***REMOVED***

    def test_round_trip_via_to_dict(self):
        original = CorpusEntry(
            url="https://example.com",
            source="research_web",
            timestamp="2026-08-20T12:00:00Z",
            title="Title",
            metadata={"k": "v"***REMOVED***,
        )
        d = original.to_dict()
        restored = CorpusEntry.from_dict(d)
        assert restored == original


# ─── CLI smoke (subprocess) ──────────────────────────────────────────────────


class TestCLI:
    """CLI smoke tests via subprocess (использует sys.executable для Termux-compat)."""

    def _run_cli(self, *args: str, corpus_root: Path) -> subprocess.CompletedProcess:
        # ``--root`` есть parent-level argparse arg; argparse does NOT consume
        # parent-level args after entering subparser, поэтому order matters:
        # parent args ДО subcommand. Re-order here (vs ``*args``-then-``--root``)
        # чтобы избежать "unrecognized argument".
        cmd = [
            sys.executable, "-m", "scripts_01.corpus_persistence",
            "--root", str(corpus_root),
            *args,
        ***REMOVED***
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).resolve().parent.parent),
        )

    def test_cli_add_lookup_list_stats(self, corpus_root):
        # add
        r = self._run_cli(
            "add", "https://cli.example.com", "--source", "research_web",
            "--title", "CLI article",
            corpus_root=corpus_root,
        )
        assert r.returncode == 0, f"add failed: {r.stderr***REMOVED***"
        assert "persisted" in r.stdout

        # lookup (human-readable)
        r = self._run_cli(
            "lookup", "https://cli.example.com",
            corpus_root=corpus_root,
        )
        assert r.returncode == 0, f"lookup failed: {r.stderr***REMOVED***"
        assert "CLI article" in r.stdout

        # stats (JSON output for machine consumption)
        r = self._run_cli(
            "stats", "--json", corpus_root=corpus_root,
        )
        assert r.returncode == 0
        payload = json.loads(r.stdout)
        assert payload == {"research_web": 1***REMOVED***

    def test_cli_add_rejects_non_http(self, corpus_root):
        r = self._run_cli(
            "add", "file:///etc/passwd", "--source", "manual",
            corpus_root=corpus_root,
        )
        assert r.returncode == 2, f"should reject: stdout={r.stdout***REMOVED***, stderr={r.stderr***REMOVED***"
        assert "must match" in r.stderr

    def test_cli_version(self, corpus_root):
        r = self._run_cli("--version", corpus_root=corpus_root)
        assert r.returncode == 0
        assert "corpus_persistence" in r.stdout

    def test_cli_unknown_subcommand_fails(self, corpus_root):
        r = self._run_cli("nonsense", corpus_root=corpus_root)
        assert r.returncode == 2  # argparse usage error

    def test_cli_clear_removes_all(self, corpus_root):
        self._run_cli(
            "add", "https://example.com", "--source", "manual",
            corpus_root=corpus_root,
        )
        # Use module-level ``clear`` (test-helper).
        from scripts_01.corpus_persistence import clear
        n = clear(root=corpus_root)
        assert n >= 1
        assert list(corpus_root.glob("*.jsonl")) == [***REMOVED***


# ─── clear utility ──────────────────────────────────────────────────────────


class TestClear:
    def test_clear_removes_all_files(self, corpus_root):
        persist("https://a.example.com", "research_web", root=corpus_root)
        persist("https://b.example.com", "manual", root=corpus_root)
        n = clear(root=corpus_root)
        assert n == 2
        assert list(corpus_root.glob("*.jsonl")) == [***REMOVED***

    def test_clear_noop_on_missing_dir(self, tmp_path):
        fresh = tmp_path / "fresh_nothing"
        assert clear(root=fresh) == 0
