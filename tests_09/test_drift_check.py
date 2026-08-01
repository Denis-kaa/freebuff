"""Tests for scripts_01/drift_check.py."""
from __future__ import annotations

import sys
***REMOVED***

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01 import drift_check as dc


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
    (tmp_path / "docs_10").mkdir()
    (tmp_path / "src_06").mkdir()
    (tmp_path / "BUFFY.md").write_text("""
```
freebuff/
├── docs_10/
├── src_06/
└── missing/
```
""", encoding="utf-8")
    issues = dc.check_directory_structure(tmp_path)
    described = {i["dir"***REMOVED*** for i in issues***REMOVED***
    assert "missing" in described
    assert all(i["issue"***REMOVED*** == "described but does not exist" for i in issues if i["dir"***REMOVED*** == "missing")


def test_check_knowledge_index(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "docs_10").mkdir()
    (tmp_path / "docs_10" / "RULES.md").write_text("# Rules", encoding="utf-8")
    result = dc.check_knowledge_index(tmp_path)
    assert isinstance(result, list)


def test_status_emoji_avoids_false_positive_plan() -> None:
    # "планирование" should not be treated as "план" (not started)
    assert dc._status_emoji("планирование") == "❓"
    assert dc._status_emoji("План") == "🔴"
    assert dc._status_emoji("production ready") == "✅"


def test_should_run_rate_limit(tmp_path) -> None:
    data_dir = tmp_path / "data_13"
    data_dir.mkdir()
    assert dc._should_run(tmp_path) is True
    dc._record_run(tmp_path)
    assert dc._should_run(tmp_path) is False
    assert dc._should_run(tmp_path, force=True) is True


def test_collect_indexed_sources_mirrors_seed(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "docs_10").mkdir()
    (tmp_path / "docs_10" / "RULES.md").write_text("# Rules", encoding="utf-8")
    sources = dc._collect_indexed_sources(tmp_path)
    assert "README.md" in sources
    assert "docs_10/RULES.md" in sources


def test_is_knowledge_doc_excludes_runtime_dirs(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "context_12").mkdir()
    (tmp_path / "context_12" / "summary.md").write_text("# S", encoding="utf-8")
    readme = tmp_path / "README.md"
    runtime = tmp_path / "context_12" / "summary.md"
    assert dc._is_knowledge_doc(readme, tmp_path) is True
    assert dc._is_knowledge_doc(runtime, tmp_path) is False


def test_extract_tree_paths_handles_nested_tree() -> None:
    text = """
```
freebuff/
├── docs_10/
│   ├── architecture/
│   └── RULES.md
├── scripts_01/
└── README.md
```
"""
    paths = dc._extract_tree_paths(text)
    names = [p for p, _ in paths***REMOVED***
    assert "docs_10" in names
    assert "docs_10/architecture" in names
    assert "docs_10/RULES.md" in names
    assert "scripts_01" in names
    assert "README.md" in names


def test_extract_tree_paths_detects_bare_root_node() -> None:
    # A bare first line (no ├/└ branch) is the tree root; child paths are
    # returned relative to that root and the root name is attached.
    text = """
```
freebuff/
└── docs_10/
```
"""
    paths = dc._extract_tree_paths(text)
    assert ("docs_10", "freebuff") in paths
    assert all(root == "freebuff" for _, root in paths)


def test_extract_tree_paths_no_root_block() -> None:
    # A block that starts directly with a branch item has no bare root.
    text = """
```
├── docs_10/
└── README.md
```
"""
    paths = dc._extract_tree_paths(text)
    names = [p for p, _ in paths***REMOVED***
    assert "docs_10" in names
    assert "README.md" in names
    assert all(root == "" for _, root in paths)


def test_extract_tree_paths_deep_nesting() -> None:
    text = """
```
freebuff/
└── docs_10/
    └── core/
        └── RULES.md
```
"""
    names = [p for p, _ in dc._extract_tree_paths(text)***REMOVED***
    assert "docs_10/core/RULES.md" in names
    assert "docs_10/core" in names


def test_check_directory_structure_resolves_docs_subtree_root(tmp_path) -> None:
    # A tree rooted at a real subdirectory (docs_10/) describes that subtree:
    # children must resolve under docs_10/, not be reported missing at root.
    (tmp_path / "docs_10").mkdir()
    (tmp_path / "docs_10" / "INDEX.md").write_text("# I", encoding="utf-8")
    (tmp_path / "docs_10" / "audits").mkdir()
    (tmp_path / "docs_10" / "audits" / "README.md").write_text("# audits", encoding="utf-8")
    (tmp_path / "BUFFY.md").write_text("""
```
docs_10/
├── INDEX.md
└── audits/
```
""", encoding="utf-8")
    issues = dc.check_directory_structure(tmp_path)
    dirs = {i["dir"***REMOVED*** for i in issues***REMOVED***
    assert "docs_10/INDEX.md" not in dirs
    assert "docs_10/audits" not in dirs
    # and the subtree root itself is not flagged as undocumented
    assert "docs_10" not in dirs


def test_check_knowledge_index_excludes_runtime_docs(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "docs_10").mkdir()
    (tmp_path / "docs_10" / "RULES.md").write_text("# Rules", encoding="utf-8")
    (tmp_path / "context_12").mkdir()
    (tmp_path / "context_12" / "summary.md").write_text("# S", encoding="utf-8")
    result = dc.check_knowledge_index(tmp_path)
    assert result == [***REMOVED***


def test_extract_tree_paths_strips_comments() -> None:
    text = """
```
freebuff/
├── docs_10/    # documentation
└── src_06/
```
"""
    paths = dc._extract_tree_paths(text)
    names = {p for p, _ in paths***REMOVED***
    assert "docs_10" in names
    assert "src_06" in names
    assert "#" not in "\n".join(names)


def test_extract_markdown_links_finds_links() -> None:
    text = "See [the rules***REMOVED***(../core_02/RULES.md) and [image***REMOVED***(../img/icon.png)."
    links = dc._extract_markdown_links(text)
    assert len(links) == 2
    assert links[0***REMOVED*** == (1, "the rules", "../core_02/RULES.md")
    assert links[1***REMOVED*** == (1, "image", "../img/icon.png")


def test_is_external_link_skips_urls_and_anchors() -> None:
    assert dc._is_external_link("https://example.com") is True
    assert dc._is_external_link("mailto:test@example.com") is True
    assert dc._is_external_link("#section") is True
    assert dc._is_external_link("../core_02/RULES.md") is False
    assert dc._is_external_link("./file.md") is False


def test_check_markdown_links_reports_broken_link(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("[broken***REMOVED***(../missing/file.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert len(issues) == 1
    assert issues[0***REMOVED***["file"***REMOVED*** == "docs_10/index.md"
    assert issues[0***REMOVED***["target"***REMOVED*** == "../missing/file.md"
    assert issues[0***REMOVED***["issue"***REMOVED*** == "broken relative link"


def test_check_markdown_links_ignores_external_and_anchors(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("[external***REMOVED***(https://example.com) and [anchor***REMOVED***(#section)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == [***REMOVED***


def test_check_markdown_links_ignores_existing_files(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    (tmp_path / "docs_10" / "RULES.md").write_text("# Rules", encoding="utf-8")
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("[rules***REMOVED***(./RULES.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == [***REMOVED***


def test_check_markdown_links_includes_root_level_md(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "index.md").write_text("[README***REMOVED***(./README.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == [***REMOVED***


def test_directory_structure_respects_adr_redirect(tmp_path) -> None:
    (tmp_path / "BUFFY.md").write_text("""
```
freebuff/
├── docs_10/
│   └── decisions/
```
""", encoding="utf-8")
    (tmp_path / "docs_10").mkdir()
    # docs_10/decisions directory is intentionally missing; canonical location exists
    adr_dir = tmp_path / "docs_10" / "engineering-memory" / "decisions"
    adr_dir.mkdir(parents=True)
    adr_dir.joinpath("ADR_001_test.md").write_text("# Test", encoding="utf-8")
    issues = dc.check_directory_structure(tmp_path)
    dirs = {i["dir"***REMOVED*** for i in issues***REMOVED***
    assert "docs_10/decisions" not in dirs


def test_directory_structure_respects_adr_redirect_empty_dir(tmp_path) -> None:
    (tmp_path / "BUFFY.md").write_text("""
```
freebuff/
├── docs_10/
│   └── decisions/
```
""", encoding="utf-8")
    (tmp_path / "docs_10").mkdir()
    # docs_10/decisions exists but is empty; canonical location supersedes it
    (tmp_path / "docs_10" / "decisions").mkdir()
    adr_dir = tmp_path / "docs_10" / "engineering-memory" / "decisions"
    adr_dir.mkdir(parents=True)
    adr_dir.joinpath("ADR_001_test.md").write_text("# Test", encoding="utf-8")
    issues = dc.check_directory_structure(tmp_path)
    dirs = {i["dir"***REMOVED*** for i in issues***REMOVED***
    assert "docs_10/decisions" not in dirs


def test_check_adr_canonical_location_passes(tmp_path) -> None:
    adr_dir = tmp_path / "docs_10" / "engineering-memory" / "decisions"
    adr_dir.mkdir(parents=True)
    adr_dir.joinpath("ADR_001_test.md").write_text("# Test", encoding="utf-8")
    (tmp_path / "docs_10" / "decisions" / "DECISIONS.md").parent.mkdir(parents=True)
    (tmp_path / "docs_10" / "decisions" / "DECISIONS.md").write_text("# Index", encoding="utf-8")
    issues = dc.check_adr_canonical_location(tmp_path)
    assert issues == [***REMOVED***


def test_check_adr_canonical_location_fails_missing_dir(tmp_path) -> None:
    issues = dc.check_adr_canonical_location(tmp_path)
    assert len(issues) == 1
    assert issues[0***REMOVED***["dir"***REMOVED*** == "docs_10/engineering-memory/decisions"


def test_check_adr_canonical_location_fails_empty(tmp_path) -> None:
    adr_dir = tmp_path / "docs_10" / "engineering-memory" / "decisions"
    adr_dir.mkdir(parents=True)
    (tmp_path / "docs_10" / "decisions" / "DECISIONS.md").parent.mkdir(parents=True)
    (tmp_path / "docs_10" / "decisions" / "DECISIONS.md").write_text("# Index", encoding="utf-8")
    issues = dc.check_adr_canonical_location(tmp_path)
    assert len(issues) == 1
    assert "empty" in issues[0***REMOVED***["issue"***REMOVED***


def test_check_markdown_links_ignores_links_in_code_blocks(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("```\n[link***REMOVED***(../missing.md)\n```\n[ok***REMOVED***(./existing.md)", encoding="utf-8")
    (tmp_path / "docs_10" / "existing.md").write_text("# OK", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert len(issues) == 0


def test_check_markdown_links_handles_absolute_paths(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    (tmp_path / "docs_10" / "RULES.md").write_text("# Rules", encoding="utf-8")
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("[rules***REMOVED***(/docs_10/RULES.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == [***REMOVED***


def test_check_markdown_links_reports_absolute_broken_link(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("[rules***REMOVED***(/docs_10/MISSING.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert len(issues) == 1
    assert issues[0***REMOVED***["target"***REMOVED*** == "/docs_10/MISSING.md"
