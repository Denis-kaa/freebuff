"""tests_09/test_doc_code_verify.py — unit tests for PHASE J verifier.

Pattern mirrors tests_09/test_forge_passport.py + tests_09/test_factory_registry.py
(class-based groups, tmp_path fixtures, fail-safe harness).

CAN-16 ADDITIVE: NEW test file. No modifications to existing test suites.

PLATFORM_CODE_MAP reality §A format: `### @entity <id>` followed by
`- **type/file/symbol:**` bullets (state machine), NOT a markdown table.
"""

from __future__ import annotations

import json
}

import pytest

from core_02.doc_code_verify import (
    ANCHOR_NAMESPACES,
    CLASSIFICATIONS,
    Claim,
    VerificationResult,
    check_symbol_exists,
    extract_claims,
    load_code_map,
    main,
    run_verification,
    verify_claim,
)


@pytest.fixture
def workspace_with_doc(tmp_path: Path) -> Path:
    """Workspace with one good doc containing @entity, @contract, @symbol anchors."""
    (tmp_path / "docs_10" / "engineering-memory").mkdir(parents=True)
    (tmp_path / "docs_10" / "engineering-memory" / "README.md").write_text(
        "Header paragraph.\n"
        "@entity scenario.registry is the canonical scenario store.\n"
        "@contract scenario.selection provides role selection.\n"
        "@symbol ScenarioRegistry.find_role resolves the role.\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def workspace_with_code_map(tmp_path: Path) -> Path:
    """Workspace with PLATFORM_CODE_MAP_V1.md SECTION-format (3 entities)."""
    (tmp_path / "docs_10" / "engineering-memory").mkdir(parents=True)
    map_content = (
        "### @entity scenario.registry\n"
        "- **type:** component\n"
        "- **file:** `core_02/scenario_registry.py`\n"
        "- **symbol:** `ScenarioRegistry`\n"
        "\n"
        "### @entity factory.registry\n"
        "- **type:** component\n"
        "- **file:** `core_02/factory_registry.py`\n"
        "- **symbol:** `FactoryRegistry`\n"
        "\n"
        "### @entity fake.missing\n"
        "- **type:** component\n"
        "- **file:** `nonexistent.py`\n"
        "- **symbol:** `FakeClass`\n"
    )
    (tmp_path / "docs_10" / "engineering-memory" / "PLATFORM_CODE_MAP_V1.md").write_text(
        map_content, encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def workspace_full(tmp_path: Path) -> Path:
    """Full workspace: PLATFORM_CODE_MAP + GOOD_CODE files on disk."""
    (tmp_path / "docs_10" / "engineering-memory").mkdir(parents=True)
    (tmp_path / "core_02").mkdir(parents=True)
    map_content = (
        "### @entity scenario.registry\n"
        "- **type:** component\n"
        "- **file:** `core_02/scenario_registry.py`\n"
        "- **symbol:** `ScenarioRegistry`\n"
        "\n"
        "### @entity forge.passport\n"
        "- **type:** component\n"
        "- **file:** `core_02/forge_passport.py`\n"
        "- **symbol:** `ForgePassport`\n"
    )
    (tmp_path / "docs_10" / "engineering-memory" / "PLATFORM_CODE_MAP_V1.md").write_text(
        map_content, encoding="utf-8"
    )
    (tmp_path / "core_02" / "scenario_registry.py").write_text(
        "class ScenarioRegistry:\n"
        "    def find_role(self): pass\n"
        "    def list_scenarios(self): pass\n",
        encoding="utf-8",
    )
    (tmp_path / "core_02" / "forge_passport.py").write_text(
        "class ForgePassport:\n"
        "    def validate(self): pass\n",
        encoding="utf-8",
    )
    return tmp_path


class TestExtractClaims:
    def test_extract_anchors_basic(self, workspace_with_doc: Path):
        doc = workspace_with_doc / "docs_10" / "engineering-memory" / "README.md"
        claims = extract_claims(doc)
        assert len(claims) >= 3
        targets = {c.target for c in claims}
        assert "scenario.registry" in targets
        namespaces = {c.namespace for c in claims}
        assert "@entity" in namespaces
        assert "@contract" in namespaces
        assert "@symbol" in namespaces

    def test_extract_skips_code_fences(self, workspace_with_doc: Path):
        doc = workspace_with_doc / "docs_10" / "engineering-memory" / "README.md"
        with doc.open("a", encoding="utf-8") as f:
            f.write("\n```\n@entity in.fence.should.not.extract\n```\n")
        claims = extract_claims(doc)
        targets = {c.target for c in claims}
        assert "in.fence.should.not.extract" not in targets

    def test_extract_empty_doc(self, tmp_path: Path):
        doc = tmp_path / "empty.md"
        doc.write_text("# Title only\n", encoding="utf-8")
        assert extract_claims(doc) == []

    def test_extract_missing_file(self, tmp_path: Path):
        assert extract_claims(tmp_path / "nonexistent.md") == []

    def test_extract_claim_line_numbering(self, workspace_with_doc: Path):
        doc = workspace_with_doc / "docs_10" / "engineering-memory" / "README.md"
        claims = extract_claims(doc)
        assert claims[0].line_num >= 2
        line_nums = [c.line_num for c in claims]
        assert line_nums == sorted(line_nums)

    def test_extract_skips_unknown_namespace(self, workspace_with_doc: Path):
        doc = workspace_with_doc / "docs_10" / "engineering-memory" / "README.md"
        with doc.open("a", encoding="utf-8") as f:
            f.write("\n@unknown.foo This namespace is not in closed vocab.\n")
        claims = extract_claims(doc)
        unknown_hits = [c for c in claims if c.namespace == "@unknown"]
        assert unknown_hits == []


class TestLoadCodeMap:
    def test_parses_section_basic(self, workspace_with_code_map: Path):
        m = load_code_map(workspace_with_code_map)
        assert "scenario.registry" in m
        assert m["scenario.registry"]["file"] == "core_02/scenario_registry.py"
        assert m["scenario.registry"]["symbol"] == "ScenarioRegistry"
        assert len(m) == 3

    def test_parses_section_empty(self, tmp_path: Path):
        (tmp_path / "docs_10" / "engineering-memory").mkdir(parents=True)
        (tmp_path / "docs_10" / "engineering-memory" / "PLATFORM_CODE_MAP_V1.md").write_text(
            "Empty file\n", encoding="utf-8"
        )
        assert load_code_map(tmp_path) == {}

    def test_parses_section_missing(self, tmp_path: Path):
        assert load_code_map(tmp_path) == {}

    def test_parses_section_with_public_api_fallback(self, tmp_path: Path):
        """public_api bullet can substitute for symbol."""
        (tmp_path / "docs_10" / "engineering-memory").mkdir(parents=True)
        (tmp_path / "docs_10" / "engineering-memory" / "PLATFORM_CODE_MAP_V1.md").write_text(
            "### @entity only.public_api\n"
            "- **type:** component\n"
            "- **file:** `some.py`\n"
            "- **public_api:** `SomeClass`\n",
            encoding="utf-8",
        )
        m = load_code_map(tmp_path)
        assert m["only.public_api"]["symbol"] == "SomeClass"


class TestCheckSymbolExists:
    def test_class_exists(self, workspace_full: Path):
        assert check_symbol_exists(
            workspace_full, "core_02/scenario_registry.py", "ScenarioRegistry"
        ) is True

    def test_class_method_exists(self, workspace_full: Path):
        assert check_symbol_exists(
            workspace_full,
            "core_02/scenario_registry.py",
            "ScenarioRegistry.find_role",
        ) is True

    def test_other_method_exists(self, workspace_full: Path):
        assert check_symbol_exists(
            workspace_full,
            "core_02/scenario_registry.py",
            "ScenarioRegistry.list_scenarios",
        ) is True

    def test_symbol_missing(self, workspace_full: Path):
        assert check_symbol_exists(
            workspace_full,
            "core_02/scenario_registry.py",
            "NonExistentClass",
        ) is False

    def test_file_missing(self, workspace_full: Path):
        assert check_symbol_exists(
            workspace_full, "core_02/nonexistent.py", "Anything"
        ) is False

    def test_parse_error_returns_false(self, tmp_path: Path):
        bad = tmp_path / "bad.py"
        bad.write_text("def broken(:\n    pass\n", encoding="utf-8")
        assert check_symbol_exists(tmp_path, "bad.py", "Anything") is False


class TestVerifyClaim:
    def test_confirmed(self, workspace_full: Path):
        m = load_code_map(workspace_full)
        claim = Claim(
            doc_path="X", line_num=1, namespace="@entity", target="scenario.registry"
        )
        result = verify_claim(claim, m, workspace_full)
        assert result.classification == "CONFIRMED"
        assert result.mapped_file == "core_02/scenario_registry.py"
        assert result.mapped_symbol == "ScenarioRegistry"
        assert "scenario_registry.py::ScenarioRegistry" in result.evidence

    def test_stale_symbol_missing(self, workspace_full: Path):
        m = {
            "stale.entry": {
                "type": "component",
                "file": "core_02/scenario_registry.py",
                "symbol": "GhostSymbol",
            },
        }
        claim = Claim(
            doc_path="X", line_num=1, namespace="@entity", target="stale.entry"
        )
        result = verify_claim(claim, m, workspace_full)
        assert result.classification == "STALE"

    def test_doc_only_target_missing_from_map(self, workspace_full: Path):
        m = load_code_map(workspace_full)
        claim = Claim(
            doc_path="X", line_num=1, namespace="@entity", target="totally.unknown"
        )
        result = verify_claim(claim, m, workspace_full)
        assert result.classification == "DOC_ONLY"

    def test_stale_map_entry_missing_symbol(self, workspace_full: Path):
        m = {
            "incomplete.entry": {
                "type": "component",
                "file": "core_02/scenario_registry.py",
                "symbol": "",
            },
        }
        claim = Claim(
            doc_path="X", line_num=1, namespace="@entity", target="incomplete.entry"
        )
        result = verify_claim(claim, m, workspace_full)
        assert result.classification == "STALE"


class TestRunVerification:
    def test_run_on_dir(self, workspace_full: Path):
        target = workspace_full / "docs_10" / "engineering-memory"
        summary = run_verification(target, workspace_full)
        assert "docs_checked" in summary
        assert "total_claims" in summary
        for c in CLASSIFICATIONS:
            assert c in summary["by_classification"]
        assert "findings" in summary
        assert "strict_exit_code" in summary

    def test_run_on_file_missing_code_map(self, workspace_with_doc: Path):
        doc = workspace_with_doc / "docs_10" / "engineering-memory" / "README.md"
        summary = run_verification(doc, workspace_with_doc)
        assert summary["by_classification"]["DOC_ONLY"] >= 3
        assert summary["by_classification"]["CONFIRMED"] == 0

    def test_warn_mode_exit_0(self, workspace_with_code_map: Path):
        (workspace_with_code_map / "core_02").mkdir(exist_ok=True)
        target = workspace_with_code_map / "docs_10" / "engineering-memory" / "PLATFORM_CODE_MAP_V1.md"
        summary = run_verification(target, workspace_with_code_map, strict=False)
        assert summary["strict_exit_code"] == 0

    def test_strict_mode_exit_1_on_stale(self, workspace_with_code_map: Path):
        """3 entities in map, 0 actual code files on disk → all 3 STALE → strict exit 1."""
        (workspace_with_code_map / "core_02").mkdir(exist_ok=True)
        target = (
            workspace_with_code_map
            / "docs_10"
            / "engineering-memory"
            / "PLATFORM_CODE_MAP_V1.md"
        )
        summary = run_verification(target, workspace_with_code_map, strict=True)
        assert summary["strict_exit_code"] == 1
        assert summary["by_classification"]["STALE"] + summary["by_classification"]["DOC_ONLY"] > 0

    def test_target_not_found_returns_error(self, tmp_path: Path):
        summary = run_verification(tmp_path / "nope", tmp_path)
        assert summary["strict_exit_code"] == 2
        assert "error" in summary

    def test_skips_docs_outside_engineering_memory(self, tmp_path: Path):
        """Use tmp_path (no PLATFORM_CODE_MAP) so only non-eng-memory doc is filtered out."""
        (tmp_path / "README.md").write_text(
            "@entity scenario.registry\n", encoding="utf-8"
        )
        target = tmp_path
        summary = run_verification(target, tmp_path)
        # README.md is filtered out → 0 docs scanned.
        assert summary["docs_checked"] == 0


class TestMainCLI:
    def test_json_output_schema(self, workspace_full: Path, capsys):
        (workspace_full / "docs_10" / "engineering-memory" / "EXTRA.md").write_text(
            "@entity scenario.registry\n", encoding="utf-8"
        )
        target = workspace_full / "docs_10" / "engineering-memory" / "EXTRA.md"
        rc = main([str(target), "--workspace", str(workspace_full), "--json"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "docs_checked" in data
        assert "total_claims" in data
        assert "by_classification" in data
        assert "findings" in data
        assert "strict_exit_code" in data
        assert rc == 0

    def test_target_not_found(self, capsys):
        rc = main(["/nonexistent/path", "--workspace", "."])
        assert rc == 2

    def test_strict_flag_passes_through(self, workspace_full: Path, capsys):
        (workspace_full / "docs_10" / "engineering-memory" / "EXTRA.md").write_text(
            "@entity scenario.registry\n", encoding="utf-8"
        )
        target = workspace_full / "docs_10" / "engineering-memory" / "EXTRA.md"
        rc = main([str(target), "--workspace", str(workspace_full), "--strict"])
        assert rc == 0

    def test_human_format_output(self, workspace_full: Path, capsys):
        (workspace_full / "docs_10" / "engineering-memory" / "EXTRA.md").write_text(
            "@entity scenario.registry\n", encoding="utf-8"
        )
        target = workspace_full / "docs_10" / "engineering-memory" / "EXTRA.md"
        rc = main([str(target), "--workspace", str(workspace_full)])
        out = capsys.readouterr().out
        assert "Docs checked" in out
        assert "Total claims" in out
        assert "CONFIRMED" in out
        assert rc == 0
