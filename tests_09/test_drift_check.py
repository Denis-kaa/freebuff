"""Tests for scripts_01/drift_check.py."""
from __future__ import annotations

import sys
from pathlib import Path

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
    assert tables[0] == [["Name", "Status"], ["A", "OK"], ["B", "Bad"]]


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
    described = {i["dir"] for i in issues}
    assert "missing" in described
    assert all(i["issue"] == "described but does not exist" for i in issues if i["dir"] == "missing")


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
    names = [p for p, _ in paths]
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
    names = [p for p, _ in paths]
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
    names = [p for p, _ in dc._extract_tree_paths(text)]
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
    dirs = {i["dir"] for i in issues}
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
    assert result == []


def test_extract_tree_paths_strips_comments() -> None:
    text = """
```
freebuff/
├── docs_10/    # documentation
└── src_06/
```
"""
    paths = dc._extract_tree_paths(text)
    names = {p for p, _ in paths}
    assert "docs_10" in names
    assert "src_06" in names
    assert "#" not in "\n".join(names)


def test_extract_markdown_links_finds_links() -> None:
    text = "See [the rules](../core_02/RULES.md) and [image](../img/icon.png)."
    links = dc._extract_markdown_links(text)
    assert len(links) == 2
    assert links[0] == (1, "the rules", "../core_02/RULES.md")
    assert links[1] == (1, "image", "../img/icon.png")


def test_is_external_link_skips_urls_and_anchors() -> None:
    assert dc._is_external_link("https://example.com") is True
    assert dc._is_external_link("mailto:test@example.com") is True
    assert dc._is_external_link("#section") is True
    assert dc._is_external_link("../core_02/RULES.md") is False
    assert dc._is_external_link("./file.md") is False


def test_check_markdown_links_reports_broken_link(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("[broken)(../missing/file.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert len(issues) == 1
    assert issues[0]["file"] == "docs_10/index.md"
    assert issues[0]["target"] == "../missing/file.md"
    assert issues[0]["issue"] == "broken relative link"


def test_check_markdown_links_ignores_external_and_anchors(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("[external)(https://example.com) and [anchor](#section)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == []


def test_check_markdown_links_ignores_existing_files(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    (tmp_path / "docs_10" / "RULES.md").write_text("# Rules", encoding="utf-8")
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("[rules)(./RULES.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == []


def test_check_markdown_links_includes_root_level_md(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "index.md").write_text("[README)(./README.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == []


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
    dirs = {i["dir"] for i in issues}
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
    dirs = {i["dir"] for i in issues}
    assert "docs_10/decisions" not in dirs


def test_check_adr_canonical_location_passes(tmp_path) -> None:
    adr_dir = tmp_path / "docs_10" / "engineering-memory" / "decisions"
    adr_dir.mkdir(parents=True)
    adr_dir.joinpath("ADR_001_test.md").write_text("# Test", encoding="utf-8")
    (tmp_path / "docs_10" / "decisions" / "DECISIONS.md").parent.mkdir(parents=True)
    (tmp_path / "docs_10" / "decisions" / "DECISIONS.md").write_text("# Index", encoding="utf-8")
    issues = dc.check_adr_canonical_location(tmp_path)
    assert issues == []


def test_check_adr_canonical_location_fails_missing_dir(tmp_path) -> None:
    issues = dc.check_adr_canonical_location(tmp_path)
    assert len(issues) == 1
    assert issues[0]["dir"] == "docs_10/engineering-memory/decisions"


def test_check_adr_canonical_location_fails_empty(tmp_path) -> None:
    adr_dir = tmp_path / "docs_10" / "engineering-memory" / "decisions"
    adr_dir.mkdir(parents=True)
    (tmp_path / "docs_10" / "decisions" / "DECISIONS.md").parent.mkdir(parents=True)
    (tmp_path / "docs_10" / "decisions" / "DECISIONS.md").write_text("# Index", encoding="utf-8")
    issues = dc.check_adr_canonical_location(tmp_path)
    assert len(issues) == 1
    assert "empty" in issues[0]["issue"]


def test_check_markdown_links_ignores_links_in_code_blocks(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("```\n[link)(../missing.md)\n```\n[ok](./existing.md)", encoding="utf-8")
    (tmp_path / "docs_10" / "existing.md").write_text("# OK", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert len(issues) == 0


def test_check_markdown_links_handles_absolute_paths(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    (tmp_path / "docs_10" / "RULES.md").write_text("# Rules", encoding="utf-8")
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("[rules)(/docs_10/RULES.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert issues == []


def test_check_markdown_links_reports_absolute_broken_link(tmp_path) -> None:
    (tmp_path / "docs_10").mkdir()
    md = tmp_path / "docs_10" / "index.md"
    md.write_text("[rules)(/docs_10/MISSING.md)", encoding="utf-8")
    issues = dc.check_markdown_links(tmp_path)
    assert len(issues) == 1
    assert issues[0]["target"] == "/docs_10/MISSING.md"


# ─────────────────────────────────────────────────────────────────────────────
# Legacy top-level redirect (compat-shim) handling — `_LEGACY_TOP_LEVEL_REDIRECTS`
# + `_is_legacy_redirect_satisfied`. The skipped branch ONLY protects against
# "exists but not described" drift; an empty shim dir is still flagged because
# that usually means the canonical location itself was moved or removed.
# ─────────────────────────────────────────────────────────────────────────────


def test_legacy_redirect_satisfied_when_canonical_exists(tmp_path) -> None:
    """Legacy shim dir + real canonical target → NOT flagged as undeclared."""
    (tmp_path / "freebuff_plugin").mkdir()
    (tmp_path / "freebuff_plugin_03").mkdir()
    # Empty BUFFY.md → describes nothing; every real top-level dir is "undeclared"
    (tmp_path / "BUFFY.md").write_text("", encoding="utf-8")
    issues = dc.check_directory_structure(tmp_path)
    dirs = {i["dir"] for i in issues}
    assert "freebuff_plugin" not in dirs


def test_legacy_redirect_flagged_when_canonical_missing(tmp_path) -> None:
    """Legacy shim whose canonical target no longer exists → must be flagged.

    Without this guard the silent-skip would mask a real architectural drift:
    if the canonical location disappeared, the shim itself is no longer a shim
    and should surface in the report for human triage.
    """
    (tmp_path / "freebuff_plugin").mkdir()
    # freebuff_plugin_03 intentionally missing
    (tmp_path / "BUFFY.md").write_text("", encoding="utf-8")
    issues = dc.check_directory_structure(tmp_path)
    dirs = {i["dir"] for i in issues}
    assert "freebuff_plugin" in dirs
    assert any(
        i["dir"] == "freebuff_plugin"
        and i["issue"] == "exists but not described in BUFFY.md/RULES.md"
        for i in issues
    )


def test_non_legacy_undeclared_dir_still_flagged(tmp_path) -> None:
    """A regular undeclared top-level directory is still flagged (no false skips)."""
    (tmp_path / "totally_random_dir").mkdir()
    (tmp_path / "BUFFY.md").write_text("", encoding="utf-8")
    issues = dc.check_directory_structure(tmp_path)
    dirs = {i["dir"] for i in issues}
    assert "totally_random_dir" in dirs


def test_legacy_redirect_helper_unit(tmp_path) -> None:
    """In isolation: helper returns True/False exactly per redirect resolution."""
    # Empty workspace (no canonical present anywhere)
    assert dc._is_legacy_redirect_satisfied(tmp_path, "freebuff_plugin") is False
    # Canonical present → True for the listed shim, False for unrelated dirs
    (tmp_path / "freebuff_plugin_03").mkdir()
    assert dc._is_legacy_redirect_satisfied(tmp_path, "freebuff_plugin") is True
    assert dc._is_legacy_redirect_satisfied(tmp_path, "totally_not_a_real_dir") is False


# ─────────────────────────────────────────────────────────────────────────────
# Multi-target tuples via real monkeypatch (NOT vacuous): exercises the actual
# helper after patching `_LEGACY_TOP_LEVEL_REDIRECTS`, so future shape-changes
# (e.g. `any()` → `all()`, `.is_dir()` → other) are caught. Caught as
# «vacuous synthetic comprehension» by `code-reviewer-minimax-m3` in v5.37.1
# review (commit `19b4356`); replaced with real-call form in this fix.
# ─────────────────────────────────────────────────────────────────────────────


def test_legacy_redirect_multi_target_tuple(tmp_path, monkeypatch) -> None:
    """Multi-target redirects: real monkeypatch + actual helper call.

    The data structure is ``tuple[str, ...]``. The default
    `_LEGACY_TOP_LEVEL_REDIRECTS` constant has only single-target entries;
    monkeypatch lets us inject a multi-target dict to exercise branches the
    default config can't reach.

    Helper contract pinned here:
    * `any(...)` — satisfied if **at least one** target is a real directory.
    * `.is_dir()` — not `.exists()`, so a stale file at the target path
      MUST NOT satisfy the redirect.
    """
    # Positive: 1 of 3 targets is a real directory → satisfied.
    monkeypatch.setattr(
        dc, "_LEGACY_TOP_LEVEL_REDIRECTS",
        {"legacy_multi_a": ("does_not_exist_1", "does_not_exist_2", "freebuff_plugin_03")},
    )
    (tmp_path / "freebuff_plugin_03").mkdir()
    assert dc._is_legacy_redirect_satisfied(tmp_path, "legacy_multi_a") is True

    # Negative: all 3 targets missing → not satisfied.
    monkeypatch.setattr(
        dc, "_LEGACY_TOP_LEVEL_REDIRECTS",
        {"legacy_multi_b": ("missing_a", "missing_b", "missing_c")},
    )
    assert dc._is_legacy_redirect_satisfied(tmp_path, "legacy_multi_b") is False

    # Negative: target exists as a stale regular file (NOT a dir) → not satisfied.
    # Locks in the `.is_dir()` semantic precision (vs. `.exists()`).
    monkeypatch.setattr(
        dc, "_LEGACY_TOP_LEVEL_REDIRECTS",
        {"legacy_multi_c": ("stale_file_target",)},
    )
    (tmp_path / "stale_file_target").write_text("not a directory", encoding="utf-8")
    assert dc._is_legacy_redirect_satisfied(tmp_path, "legacy_multi_c") is False

    # Degenerate: empty target tuple → not satisfied.
    monkeypatch.setattr(
        dc, "_LEGACY_TOP_LEVEL_REDIRECTS",
        {"legacy_multi_d": ()},
    )
    assert dc._is_legacy_redirect_satisfied(tmp_path, "legacy_multi_d") is False
