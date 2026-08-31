"""Tests for scripts_01/research_web.py (Missing Capability #6, 075_04_research_web_capability)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01 ]search_web as rw


# — fixture: не мутировать реальную БД (data_13/context.db) при каждом вызове

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_side_effects(monkeypatch):
    """Disable observability hooks and avoid writing to real corpus during tests.

    corpus_persistence.persist is stubbed: if a test passes corpus_dir=<Path>
    (e.g. tmp_path), the stub delegates to real persist for hermetic verification;
    otherwise it returns a no-op PersistResult without disk writes.
    """
    monkeypatch.setattr(rw, "_emit_events", lambda report: None)
    from scripts_01 import corpus_persistence as cp_mod
    real_persist = cp_mod.persist

    def _stub_persist(url, source, *, title=None, metadata=None, root=None):
        if root is not None:
            return real_persist(
                url, source, title=title, metadata=metadata, root=root,
            )
        return cp_mod.PersistResult(
            entry=cp_mod.CorpusEntry(
                url=url, source=source, timestamp=cp_mod._now_iso(),
                title=title, metadata=dict(metadata or {}),
            ),
            is_duplicate=False,
        )

    monkeypatch.setattr(cp_mod, "persist", _stub_persist)


# — helpers —


def _make_source(url: str, title: str = "", snippet: str = "", verified: bool = False) -> rw.Source:
    return rw.Source(url=url, title=title, snippet=snippet, verified=verified)


# — functional: input / output —


def test_research_web_returns_report(monkeypatch, tmp_path) -> None:
    """search_web + fetch_page mocked → ResearchReport with sources and synthesis."""
    monkeypatch.setattr(
        rw, "search_web",
        lambda query, max_sources=10, timeout=10.0: [
            _make_source("https://example.com/a", "Alpha", "Workspace OS local-first tooling", True),
            _make_source("https://example.com/b", "Beta", "Workspace OS agents architecture", True),
        ],
    )
    monkeypatch.setattr(rw, "fetch_page", lambda url, timeout=10.0: "<p>content</p>")

    out = tmp_path / "report.md"
    report = rw.research_web("Workspace OS", out=str(out), max_sources=2, timeout=5)

    assert report.query == "Workspace OS"
    assert len(report.sources) == 2
    assert not report.degraded
    assert report.synthesis
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "Research Report" in text
    assert "Найденные источники" in text
    assert "Синтез" in text


def test_research_web_no_save_dry_run(monkeypatch, tmp_path) -> None:
    """--no-save: save=False → file is not created."""
    monkeypatch.setattr(
        rw, "search_web",
        lambda query, max_sources=10, timeout=10.0: [_make_source("https://example.com/a", "Alpha")],
    )
    monkeypatch.setattr(rw, "fetch_page", lambda url, timeout=10.0: "<p>x</p>")

    target = tmp_path / "should_not_exist.md"
    report = rw.research_web("тема", out=str(target), save=False)
    assert report.sources_checked == 1
    assert not target.exists()


def test_json_schema_keys(monkeypatch) -> None:
    """DoD §5.2: JSON contains query, sources[], synthesis, evidence_checked, degraded."""
    monkeypatch.setattr(
        rw, "search_web",
        lambda query, max_sources=10, timeout=10.0: [
            _make_source("https://example.com/a", "Alpha", "Workspace OS", True),
            _make_source("https://example.com/b", "Beta", "Workspace OS agents", True),
        ],
    )
    monkeypatch.setattr(rw, "fetch_page", lambda url, timeout=10.0: "<p>c</p>")

    report = rw.research_web("Workspace OS", save=False)
    payload = report.to_dict()
    for key in ("query", "sources", "synthesis", "evidence_checked", "degraded"):
        assert key in payload, f"missing JSON key: {key}"
    assert isinstance(payload["sources"], list)
    assert payload["sources"][0]["url"].startswith("https://")


def test_cli_json_stdout(monkeypatch, capsys) -> None:
    """CLI --json prints valid JSON with schema keys."""
    monkeypatch.setattr(
        rw, "search_web",
        lambda query, max_sources=10, timeout=10.0: [_make_source("https://example.com/a", "Alpha")],
    )
    monkeypatch.setattr(rw, "fetch_page", lambda url, timeout=10.0: "<p>c</p>")
    monkeypatch.setattr(sys, "argv", ["research_web", "Workspace OS", "--json", "--no-save"])

    assert rw.main() == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["query"] == "Workspace OS"
    assert payload["sources_checked"] == 1
    assert "synthesis" in payload


# — fail-safe: broken source —


def test_fail_safe_broken_source(monkeypatch) -> None:
    """Broken URL (fetch_page raises) → warning, no crash (DoD §5.3)."""
    monkeypatch.setattr(
        rw, "search_web",
        lambda query, max_sources=10, timeout=10.0: [
            _make_source("https://broken.example.com/", "Broken"),
            _make_source("https://ok.example.com/", "OK", "Workspace OS report", True),
        ],
    )

    def _fetch(url: str, timeout: float = 10.0) -> str:
        if "broken" in url:
            raise ConnectionError("connection refused")
        return "<p>Workspace OS is a local-first platform</p>"

    monkeypatch.setattr(rw, "fetch_page", _fetch)

    report = rw.research_web("Workspace OS", save=False)
    assert report.sources_checked == 2
    assert any("broken" in w for w in report.warnings)
    verified_urls = [s.url for s in report.sources if s.verified]
    assert "https://ok.example.com/" in verified_urls
    assert "https://broken.example.com/" not in verified_urls


def test_no_network_degraded(monkeypatch) -> None:
    """No network → degraded report sources_checked: 0, exit 0 (DoD §5.4)."""
    def _boom(*_args, **_kwargs):
        raise ConnectionError("no network")

    monkeypatch.setattr(rw, "search_web", _boom)
    monkeypatch.setattr(rw, "fetch_page", lambda url, timeout=10.0: "")

    report = rw.research_web("тема", save=False)
    assert report.degraded is True
    assert report.sources_checked == 0
    assert report.evidence_checked == 0
    assert any("поиск недоступен" in w for w in report.warnings)


# — vocabulary-drift (ANTI-6b / CON-8) —


def test_research_token_in_known_capabilities() -> None:
    """genuine token research is registered in KNOWN_CAPABILITIES."""
    from core_02.blueprint_v3 import KNOWN_CAPABILITIES

    assert "research" in KNOWN_CAPABILITIES


def test_research_token_in_model_catalog() -> None:
    """Token research exists in ModelCatalog → drift test will not break."""
    from core_02.router import ModelCatalog

    caps: set[str] = set()
    for entry in ModelCatalog.default().all:
        caps.update(entry.capabilities)
    assert "research" in caps


def test_research_web_not_in_known_capabilities() -> None:
    """research_web is a Tool name (kind: tool), NOT a capability token."""
    from core_02.blueprint_v3 import KNOWN_CAPABILITIES

    assert "research_web" not in KNOWN_CAPABILITIES


# — helper-level —


def test_parse_ddg_results_extracts_sources() -> None:
    html = """
    <html><body>
      <div class="result">
        <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fdoc">Example Doc</a>
        <a class="result__snippet">Workspace OS is a local-first environment.</a>
      </div>
      <div class="result">
        <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2F">Org</a>
        <a class="result__snippet">Agents orchestration.</a>
      </div>
    </body></html>
    """
    sources = rw._parse_ddg_results(html, max_sources=10)
    assert len(sources) == 2
    assert sources[0].url == "https://example.com/doc"
    assert sources[0].title == "Example Doc"
    assert sources[0].snippet


def test_parse_ddg_results_respects_max_sources() -> None:
    html = """
    <div class="result"><a class="result__a" href="https://a.example.com">A</a></div>
    <div class="result"><a class="result__a" href="https://b.example.com">B</a></div>
    <div class="result"><a class="result__a" href="https://c.example.com">C</a></div>
    """
    assert len(rw._parse_ddg_results(html, max_sources=2)) == 2


def test_evidence_count_only_verified() -> None:
    sources = [
        _make_source("https://a.example.com", "Workspace OS report", "Workspace OS agents", True),
        _make_source("https://b.example.com", "Workspace OS review", "Workspace OS platform", True),
        _make_source("https://c.example.com", "Workspace OS notes", "Workspace OS", False),
    ]
    # 2 verified sources with overlapping terms → evidence 2 (third one not verified)
    assert rw._count_evidence(sources, "Workspace OS") == 2


# — Corpus persistence integration (v5.189.56) —


class TestCorpusPersistenceIntegration:
    """Corpus is auto-populated on every successful fetch_page (ADR-016 fail-safe).

    Contract:
    - research_web.fetch_page() success → corpus_persistence.persist(...)
    - source='research_web', title=src.title, metadata={'status': 200, 'query': ...}
    - Failures inside persist → warning, NOT exception (ADR-016)
    - persist_corpus=False → persist is NEVER called
    """

    def test_persist_called_per_successful_fetch(self, monkeypatch, tmp_path):
        """Every successful fetch → one persist call with correct args."""
        from scripts_01 import corpus_persistence as cp
        calls: list = []
        real_persist = cp.persist

        def _recorder(url, source, *, title=None, metadata=None, root=None):
            calls.append({
                "url": url, "source": source, "title": title,
                "metadata": dict(metadata or {}), "root": root,
            ])
            return real_persist(url, source, title=title, metadata=metadata, root=root)

        monkeypatch.setattr(cp, "persist", _recorder)
        monkeypatch.setattr(
            rw, "search_web",
            lambda q, max_sources=10, timeout=10.0: [
                _make_source("https://alpha.example.com/", "Alpha source", "snippet1"),
                _make_source("https://beta.example.com/", "Beta source", "snippet2"),
            ],
        )
        monkeypatch.setattr(rw, "fetch_page", lambda url, timeout=10.0: "<p>ok</p>")

        rw.research_web(
            "test query", save=False,
            corpus_dir=tmp_path, persist_corpus=True,
        )

        assert len(calls) == 2
        for c in calls:
            assert c["source"] == "research_web"
            assert c["root"] == tmp_path
            assert c["metadata"]["status"] == 200
            assert c["metadata"]["query"] == "test query"
        urls = {c["url"] for c in calls}
        assert urls == {"https://alpha.example.com/", "https://beta.example.com/"}
        # Title contract: search-result title propagated to corpus (per code-reviewer v5.189.56).
        title_by_url = {c["url"]: c["title"] for c in calls}
        assert title_by_url["https://alpha.example.com/"] == "Alpha source"
        assert title_by_url["https://beta.example.com/"] == "Beta source"

    def test_persist_not_called_on_fetch_failure(self, monkeypatch, tmp_path):
        """Broken URL → fetch raises → persist NOT called (only outer except warn)."""
        from scripts_01 import corpus_persistence as cp
        calls: list = []
        real_persist = cp.persist

        def _recorder(url, source, *, title=None, metadata=None, root=None):
            calls.append({"url": url, "source": source, "root": root})
            return real_persist(url, source, title=title, metadata=metadata, root=root)

        monkeypatch.setattr(cp, "persist", _recorder)
        monkeypatch.setattr(
            rw, "search_web",
            lambda q, max_sources=10, timeout=10.0: [
                _make_source("https://broken.example.com/", "Broken"),
                _make_source("https://ok.example.com/", "OK", "snippet"),
            ],
        )

        def _boom_or_ok(url, timeout=10.0):
            if "broken" in url:
                raise ConnectionError("simulated broken URL")
            return "<p>ok</p>"

        monkeypatch.setattr(rw, "fetch_page", _boom_or_ok)

        rw.research_web(
            "test", save=False,
            corpus_dir=tmp_path, persist_corpus=True,
        )
        assert len(calls) == 1
        assert calls[0]["url"] == "https://ok.example.com/"

    def test_persist_failure_does_not_break_research_web(self, monkeypatch, tmp_path):
        """persist throws → warning + continue (ADR-016 fail-safe), other sources proceed."""
        from scripts_01 import corpus_persistence as cp

        def _boom(url, source, **kwargs):
            raise OSError("simulated disk full")

        monkeypatch.setattr(cp, "persist", _boom)
        monkeypatch.setattr(
            rw, "search_web",
            lambda q, max_sources=10, timeout=10.0: [
                _make_source("https://a.example.com/", "A"),
                _make_source("https://b.example.com/", "B"),
            ],
        )
        monkeypatch.setattr(rw, "fetch_page", lambda url, timeout=10.0: "<p>ok</p>")

        report = rw.research_web(
            "test", save=False,
            corpus_dir=tmp_path, persist_corpus=True,
        )
        assert not report.degraded
        assert report.sources_checked == 2
        corpus_warnings = [w for w in report.warnings if "corpus_persistence error" in w]
        assert len(corpus_warnings) == 2

    def test_persist_corpus_false_skips_persist(self, monkeypatch, tmp_path):
        """persist_corpus=False → zero persist calls (opt-out path)."""
        from scripts_01 import corpus_persistence as cp
        calls: list = []

        def _recorder(*args, **kwargs):
            calls.append({"called": True})
            return cp.PersistResult(
                entry=cp.CorpusEntry(
                    url=args[0], source=args[1], timestamp=cp._now_iso(),
                ),
                is_duplicate=False,
            )

        monkeypatch.setattr(cp, "persist", _recorder)
        monkeypatch.setattr(
            rw, "search_web",
            lambda q, max_sources=10, timeout=10.0: [
                _make_source("https://a.example.com/", "A"),
                _make_source("https://b.example.com/", "B"),
            ],
        )
        monkeypatch.setattr(rw, "fetch_page", lambda url, timeout=10.0: "<p>ok</p>")

        report = rw.research_web(
            "test", save=False,
            corpus_dir=tmp_path, persist_corpus=False,
        )
        assert report.sources_checked == 2
        assert calls == []

    def test_corpus_dir_writes_real_entries(self, monkeypatch, tmp_path):
        """corpus_dir=tmp_path → real JSONL entries, accessible via list_all()."""
        monkeypatch.setattr(
            rw, "search_web",
            lambda q, max_sources=10, timeout=10.0: [
                _make_source("https://real1.example.com/", "Real One", "snippet1"),
                _make_source("https://real2.example.com/", "Real Two", "snippet2"),
            ],
        )
        monkeypatch.setattr(rw, "fetch_page", lambda url, timeout=10.0: "<p>ok</p>")

        from scripts_01 import corpus_persistence as cp

        rw.research_web(
            "test", save=False,
            corpus_dir=tmp_path, persist_corpus=True,
        )

        entries = cp.list_all(root=tmp_path)
        assert len(entries) == 2
        urls = {e.url for e in entries}
        assert urls == {"https://real1.example.com/", "https://real2.example.com/"}
        for e in entries:
            assert e.source == "research_web"
            assert e.metadata.get("status") == 200
            assert e.metadata.get("query") == "test"
        stats = cp.stats(root=tmp_path)
        assert stats.get("research_web") == 2

    def test_no_corpus_cli_flag_disables_persist(self, monkeypatch, tmp_path):
        """CLI flag --no-corpus → persist_corpus=False → no persist calls."""
        from scripts_01 import corpus_persistence as cp
        calls: list = []

        def _recorder(*args, **kwargs):
            calls.append({"called": True})
            return cp.PersistResult(
                entry=cp.CorpusEntry(
                    url=args[0], source=args[1], timestamp=cp._now_iso(),
                ),
                is_duplicate=False,
            )

        monkeypatch.setattr(cp, "persist", _recorder)
        monkeypatch.setattr(
            rw, "search_web",
            lambda q, max_sources=10, timeout=10.0: [_make_source("https://cli.example.com/", "CLI")],
        )
        monkeypatch.setattr(rw, "fetch_page", lambda url, timeout=10.0: "<p>ok</p>")
        monkeypatch.setattr(
            sys, "argv",
            ["research_web", "test", "--no-save", "--no-corpus", "--json"],
        )

        assert rw.main() == 0
        assert calls == []

    def test_persist_raises_unexpected_exception_still_completes(self, monkeypatch, tmp_path):
        """persist throws unexpected exception → research_web completes (ADR-016 fail-safe).

        This test covers the spirit of module-missing/ImportError scenarios by
        simulating persist failure with a broader exception type. Overlaps with
        test_persist_failure_does_not_break_research_web but exercises a different
        exception family.
        """
        from scripts_01 import corpus_persistence as cp

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated unhandled exception")

        monkeypatch.setattr(cp, "persist", _boom)
        monkeypatch.setattr(
            rw, "search_web",
            lambda q, **k: [_make_source("https://x.example.com/", "X")],
        )
        monkeypatch.setattr(rw, "fetch_page", lambda url, **k: "<p>ok</p>")

        report = rw.research_web("t", save=False, persist_corpus=True)
        assert report.sources_checked == 1
        assert not report.degraded
        assert any("corpus_persistence error" in w for w in report.warnings)
