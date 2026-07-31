"""Tests for scripts/drift_check.py."""
from __future__ import annotations

import sys
***REMOVED***

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import drift_check as dc


def test_parse_markdown_tables_simple() -> None:
    text = """
| Name | Status |
|------|--------|
| A    | OK     |
| B    | Bad    |
"""
    tables = dc._parse_markdown_tables(text)
    assert len(tables) == 1
    assert tables[0***REMOVED*** == [["Name", "Status"***REMOVED***, ["A", "OK"***REMOVED***, ["B", "Bad"***REMOVED******REMOVED***


def test_status_emoji() -> None:
    assert dc._status_emoji("Not started") == "🔴"
    assert dc._status_emoji("MVP") == "🟡"
    assert dc._status_emoji("Production") == "✅"


def test_check_directory_structure(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "BUFFY.md").write_text("""
```
freebuff/
├── docs/
├── src/
└── missing/
```
""", encoding="utf-8")
    issues = dc.check_directory_structure(tmp_path)
    described = {i["dir"***REMOVED*** for i in issues***REMOVED***
    assert "missing" in described
    assert all(i["issue"***REMOVED*** == "described but does not exist" for i in issues if i["dir"***REMOVED*** == "missing")


def test_check_knowledge_index(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "RULES.md").write_text("# Rules", encoding="utf-8")
    result = dc.check_knowledge_index(tmp_path)
    assert isinstance(result, list)


def test_status_emoji_avoids_false_positive_plan() -> None:
    # "планирование" should not be treated as "план" (not started)
    assert dc._status_emoji("планирование") == "❓"
    assert dc._status_emoji("План") == "🔴"
    assert dc._status_emoji("production ready") == "✅"


def test_should_run_rate_limit(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    assert dc._should_run(tmp_path) is True
    dc._record_run(tmp_path)
    assert dc._should_run(tmp_path) is False
    assert dc._should_run(tmp_path, force=True) is True


def test_collect_indexed_sources_mirrors_seed(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "RULES.md").write_text("# Rules", encoding="utf-8")
    sources = dc._collect_indexed_sources(tmp_path)
    assert "README.md" in sources
    assert "docs/RULES.md" in sources


def test_is_knowledge_doc_excludes_runtime_dirs(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "context").mkdir()
    (tmp_path / "context" / "summary.md").write_text("# S", encoding="utf-8")
    readme = tmp_path / "README.md"
    runtime = tmp_path / "context" / "summary.md"
    assert dc._is_knowledge_doc(readme, tmp_path) is True
    assert dc._is_knowledge_doc(runtime, tmp_path) is False


def test_extract_tree_paths_handles_nested_tree() -> None:
    text = """
```
freebuff/
├── docs/
│   ├── architecture/
│   └── RULES.md
├── scripts/
└── README.md
```
"""
    paths = dc._extract_tree_paths(text)
    names = [p for p, _ in paths***REMOVED***
    assert "docs" in names
    assert "docs/architecture" in names
    assert "docs/RULES.md" in names
    assert "scripts" in names
    assert "README.md" in names


def test_check_knowledge_index_excludes_runtime_docs(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "RULES.md").write_text("# Rules", encoding="utf-8")
    (tmp_path / "context").mkdir()
    (tmp_path / "context" / "summary.md").write_text("# S", encoding="utf-8")
    result = dc.check_knowledge_index(tmp_path)
    assert result == [***REMOVED***


def test_extract_tree_paths_strips_comments() -> None:
    text = """
```
freebuff/
├── docs/    # documentation
└── src/
```
"""
    paths = dc._extract_tree_paths(text)
    names = {p for p, _ in paths***REMOVED***
    assert "docs" in names
    assert "src" in names
    assert "#" not in "\n".join(names)


def test_extract_markdown_links_finds_links() -> None:
    text = "See [the rules***REMOVED***(../core/RULES.md) and [image***REMOVED***(../img/icon.png)."
    links = dc._extract_markdown_links(text)
    assert len(links) == 2
    assert links[0***REMOVED*** == (1, "the rules", "../core/RULES.md")
    assert links[1***REMOVED*** == (1, "image", "../img/icon.png")


def test_is_external_link_skips_urls_and_anchors() -> None:
    assert dc._is_external_link("https://example.com") is True
    assert dc._is_external_link("mailto:test@example.com") is True
    assert dc._is_external_link("#section") is True
    assert dc._is_external_link("../core/RULES.md") is False
    assert dc._is_external_link("./file.md") is False


def test_check_markdown_links_reports_broken_link(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    md = tmp_path / "docs" / "index.md"
    md.write_text("[broken***REMOVED***(../missing/file.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert len(issues) == 1
    assert issues[0***REMOVED***["file"***REMOVED*** == "docs/index.md"
    assert issues[0***REMOVED***["target"***REMOVED*** == "../missing/file.md"
    assert issues[0***REMOVED***["issue"***REMOVED*** == "broken relative link"


def test_check_markdown_links_ignores_external_and_anchors(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    md = tmp_path / "docs" / "index.md"
    md.write_text("[external***REMOVED***(https://example.com) and [anchor***REMOVED***(#section)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == [***REMOVED***


def test_check_markdown_links_ignores_existing_files(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "RULES.md").write_text("# Rules", encoding="utf-8")
    md = tmp_path / "docs" / "index.md"
    md.write_text("[rules***REMOVED***(./RULES.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == [***REMOVED***


def test_check_markdown_links_includes_root_level_md(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "index.md").write_text("[README***REMOVED***(./README.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == [***REMOVED***


def test_check_markdown_links_ignores_links_in_code_blocks(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    md = tmp_path / "docs" / "index.md"
    md.write_text("```\n[link***REMOVED***(../missing.md)\n```\n[ok***REMOVED***(./existing.md)", encoding="utf-8")
    (tmp_path / "docs" / "existing.md").write_text("# OK", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert len(issues) == 0


def test_check_markdown_links_handles_absolute_paths(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "RULES.md").write_text("# Rules", encoding="utf-8")
    md = tmp_path / "docs" / "index.md"
    md.write_text("[rules***REMOVED***(/docs/RULES.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == [***REMOVED***


def test_check_markdown_links_reports_absolute_broken_link(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    md = tmp_path / "docs" / "index.md"
    md.write_text("[rules***REMOVED***(/docs/MISSING.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert len(issues) == 1
    assert issues[0***REMOVED***["target"***REMOVED*** == "/docs/MISSING.md"
