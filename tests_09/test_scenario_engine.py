"""Tests for freebuff_plugin_03/scenario_engine.py.

Covers:
  - Scenario class (init, to_dict, apply with variables)
  - YAML parsing (_parse_yaml_front_matter, _parse_yaml_value, _strip_yaml_front_matter)
  - ScenarioEngine (list, get, search, apply, reload)
  - Edge cases: empty dir, no YAML, no template, missing file, partial variables
  - Real scenarios (7 .md files in freebuff_plugin_03/scenarios/)
"""

from __future__ import annotations

import subprocess
import sys
}

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from freebuff_plugin_03.scenario_engine import (  # noqa: E402
    Scenario,
    ScenarioEngine,
    _parse_yaml_front_matter,
    _parse_yaml_value,
    _strip_yaml_front_matter,
)


# ═══════════════════════════════════════════════════════════════
# _parse_yaml_value tests
# ═══════════════════════════════════════════════════════════════


class TestParseYamlValue:
    """Unit tests for the _parse_yaml_value helper."""

    def test_string(self) -> None:
        assert _parse_yaml_value("hello") == "hello"
        assert _parse_yaml_value("hello world") == "hello world"
        assert _parse_yaml_value("freelancing") == "freelancing"

    def test_quoted_string(self) -> None:
        assert _parse_yaml_value('"hello"') == "hello"
        assert _parse_yaml_value("'hello'") == "hello"

    def test_integer(self) -> None:
        assert _parse_yaml_value("42") == 42
        assert _parse_yaml_value("0") == 0
        assert _parse_yaml_value("-5") == -5

    def test_float(self) -> None:
        assert _parse_yaml_value("3.14") == 3.14
        assert _parse_yaml_value("-0.5") == -0.5

    def test_boolean(self) -> None:
        assert _parse_yaml_value("true") is True
        assert _parse_yaml_value("True") is True
        assert _parse_yaml_value("false") is False
        assert _parse_yaml_value("False") is False

    def test_null(self) -> None:
        assert _parse_yaml_value("null") is None
        assert _parse_yaml_value("none") is None
        assert _parse_yaml_value("None") is None

    def test_trimmed_string(self) -> None:
        assert _parse_yaml_value("  hello  ") == "hello"


# ═══════════════════════════════════════════════════════════════
# _parse_yaml_front_matter tests
# ═══════════════════════════════════════════════════════════════


class TestParseYamlFrontMatter:
    """Tests for the YAML front matter parser."""

    def test_no_yaml(self) -> None:
        """No --- markers returns empty dict."""
        text = "# Just a title\n\nSome content"
        assert _parse_yaml_front_matter(text) == {}

    def test_empty_yaml(self) -> None:
        """Empty --- block returns empty dict."""
        text = "---\n---\n# Title"
        assert _parse_yaml_front_matter(text) == {}

    def test_simple_key_value(self) -> None:
        text = """---
category: freelancing
complexity: средняя
---

# Title"""
        result = _parse_yaml_front_matter(text)
        assert result["category"] == "freelancing"
        assert result["complexity"] == "средняя"

    def test_tags_list(self) -> None:
        text = """---
category: freelancing
tags:
  - parser
  - scraper
  - bs4
---

# Title"""
        result = _parse_yaml_front_matter(text)
        assert result["category"] == "freelancing"
        assert isinstance(result["tags"], list)
        assert "parser" in result["tags"]
        assert "scraper" in result["tags"]
        assert "bs4" in result["tags"]
        assert len(result["tags"]) == 3

    def test_tags_single_line(self) -> None:
        text = """---
tags:
  - telegram
---

# Title"""
        result = _parse_yaml_front_matter(text)
        assert result["tags"] == ["telegram"]

    def test_boolean_value(self) -> None:
        text = """---
enabled: true
published: false
---

# Title"""
        result = _parse_yaml_front_matter(text)
        assert result["enabled"] is True
        assert result["published"] is False

    def test_integer_value(self) -> None:
        text = """---
priority: 5
count: 100
---

# Title"""
        result = _parse_yaml_front_matter(text)
        assert result["priority"] == 5
        assert result["count"] == 100

    def test_multiline_description(self) -> None:
        """Description with colons is handled correctly."""
        text = """---
category: test
description: Это описание с : двоеточием и другими символами
---

# Title"""
        result = _parse_yaml_front_matter(text)
        assert result["category"] == "test"
        assert "двоеточием" in result["description"]


# ═══════════════════════════════════════════════════════════════
# _strip_yaml_front_matter tests
# ═══════════════════════════════════════════════════════════════


class TestStripYaml:
    """Tests for stripping YAML front matter from markdown."""

    def test_strip_yaml(self) -> None:
        text = """---
category: test
---

# Title

Content"""
        result = _strip_yaml_front_matter(text)
        assert result.startswith("# Title")
        assert "category" not in result

    def test_no_yaml(self) -> None:
        text = "# Title\nContent"
        assert _strip_yaml_front_matter(text) == text

    def test_only_yaml(self) -> None:
        text = """---
key: value
---
"""
        # No content after YAML
        result = _strip_yaml_front_matter(text)
        assert result == ""


# ═══════════════════════════════════════════════════════════════
# Scenario class tests
# ═══════════════════════════════════════════════════════════════


class TestScenario:
    """Tests for the Scenario dataclass."""

    def test_init_defaults(self) -> None:
        s = Scenario(slug="test", title="Test")
        assert s.slug == "test"
        assert s.title == "Test"
        assert s.category == ""
        assert s.complexity == ""
        assert s.description == ""
        assert s.tags == []
        assert s.prompt_template == ""
        assert s.metadata == {}

    def test_init_full(self) -> None:
        s = Scenario(
            slug="my_scenario",
            title="My Scenario",
            category="freelancing",
            complexity="средняя",
            description="A test scenario",
            tags=["test", "demo"],
            prompt_template="Hello {name]",
            metadata={"version": 1},
        )
        assert s.slug == "my_scenario"
        assert s.title == "My Scenario"
        assert s.category == "freelancing"
        assert s.complexity == "средняя"
        assert s.tags == ["test", "demo"]
        assert s.prompt_template == "Hello {name]"
        assert s.metadata == {"version": 1}

    def test_to_dict(self) -> None:
        s = Scenario(
            slug="test",
            title="Test",
            category="dev",
            complexity="low",
            description="Desc",
            tags=["a", "b"],
            prompt_template="Template {x]",
        )
        d = s.to_dict()
        assert d["slug"] == "test"
        assert d["title"] == "Test"
        assert d["category"] == "dev"
        assert d["complexity"] == "low"
        assert d["description"] == "Desc"
        assert d["tags"] == ["a", "b"]
        assert d["has_template"] is True
        assert "metadata" in d

    def test_to_dict_no_template(self) -> None:
        s = Scenario(slug="test", title="Test")
        assert s.to_dict()["has_template"] is False

    def test_apply_no_vars(self) -> None:
        s = Scenario(slug="test", title="Test", prompt_template="Hello {name)")
        result = s.apply()  # type: ignore[arg-type]
        assert result == "Hello {name]"

    def test_apply_none_vars(self) -> None:
        s = Scenario(slug="test", title="Test", prompt_template="Hello {name)")
        result = s.apply(None)
        assert result == "Hello {name]"

    def test_apply_substitution(self) -> None:
        s = Scenario(slug="test", title="Test", prompt_template="Hello {name) from {city]")
        result = s.apply({"name": "Alice", "city": "Moscow"})
        assert result == "Hello Alice from Moscow"

    def test_apply_partial_substitution(self) -> None:
        """Missing variables remain as {placeholders]."""
        s = Scenario(slug="test", title="Test", prompt_template="Hello {name) from {city]")
        result = s.apply({"name": "Alice"})
        assert "Alice" in result
        assert "{city]" in result

    def test_apply_empty_vars(self) -> None:
        s = Scenario(slug="test", title="Test", prompt_template="Hello {name)")
        result = s.apply({})
        assert result == "Hello {name]"

    def test_apply_no_template(self) -> None:
        s = Scenario(slug="test", title="Test", prompt_template="")
        result = s.apply({"x": "y"})
        assert result == ""


# ═══════════════════════════════════════════════════════════════
# ScenarioEngine tests (with real scenarios directory)
# ═══════════════════════════════════════════════════════════════


class TestScenarioEngineReal:
    """Tests with the actual scenarios/ directory (7 .md files)."""

    def test_engine_loads_all_scenarios(self) -> None:
        engine = ScenarioEngine()
        scenarios = engine.list_scenarios()
        assert len(scenarios) >= 7  # 7+ real scenario files

    def test_list_returns_scenario_dicts(self) -> None:
        engine = ScenarioEngine()
        scenarios = engine.list_scenarios()
        for s in scenarios:
            assert "slug" in s
            assert "title" in s
            assert "category" in s
            assert "description" in s

    def test_list_filter_by_category(self) -> None:
        engine = ScenarioEngine()
        freelancing = engine.list_scenarios(category="freelancing")
        for s in freelancing:
            assert s["category"] == "freelancing"
        assert len(freelancing) >= 5

    def test_list_filter_by_category_nonexistent(self) -> None:
        engine = ScenarioEngine()
        result = engine.list_scenarios(category="nonexistent_category_xyz")
        assert result == []

    def test_list_filter_by_tag(self) -> None:
        engine = ScenarioEngine()
        telegram_scenarios = engine.list_scenarios(tag="telegram")
        for s in telegram_scenarios:
            assert "telegram" in s["tags"]
        assert len(telegram_scenarios) >= 1

    def test_list_filter_by_tag_nonexistent(self) -> None:
        engine = ScenarioEngine()
        result = engine.list_scenarios(tag="nonexistent_tag_xyz")
        assert result == []

    def test_list_filter_by_category_and_tag(self) -> None:
        engine = ScenarioEngine()
        result = engine.list_scenarios(category="freelancing", tag="parser")
        for s in result:
            assert s["category"] == "freelancing"
            assert "parser" in s["tags"]

    def test_get_scenario_exists(self) -> None:
        engine = ScenarioEngine()
        scenario = engine.get_scenario("freelance_parser")
        assert scenario is not None
        assert scenario.slug == "freelance_parser"
        assert scenario.title is not None
        assert len(scenario.title) > 0

    def test_get_scenario_nonexistent(self) -> None:
        engine = ScenarioEngine()
        assert engine.get_scenario("nonexistent") is None

    def test_get_scenario_empty_string(self) -> None:
        engine = ScenarioEngine()
        assert engine.get_scenario("") is None

    def test_search_finds_by_title(self) -> None:
        engine = ScenarioEngine()
        results = engine.search_scenarios("парсер")
        slugs = [r["slug"] for r in results]
        assert "freelance_parser" in slugs

    def test_search_finds_by_description(self) -> None:
        engine = ScenarioEngine()
        results = engine.search_scenarios("telegram")
        slugs = [r["slug"] for r in results]
        assert "freelance_tg_bot" in slugs

    def test_search_finds_by_tag(self) -> None:
        engine = ScenarioEngine()
        results = engine.search_scenarios("api")
        slugs = [r["slug"] for r in results]
        # freelance_api and freelance_integration both have 'api' tag
        assert "freelance_api" in slugs

    def test_search_finds_by_category(self) -> None:
        engine = ScenarioEngine()
        results = engine.search_scenarios("agent")
        slugs = [r["slug"] for r in results]
        assert "agent_setup" in slugs

    def test_search_case_insensitive(self) -> None:
        engine = ScenarioEngine()
        upper = engine.search_scenarios("PARSER")
        lower = engine.search_scenarios("parser")
        assert len(upper) == len(lower)

    def test_search_no_results(self) -> None:
        engine = ScenarioEngine()
        results = engine.search_scenarios("xyznonexistent123456")
        assert results == []

    def test_search_empty_query(self) -> None:
        """Empty query returns everything (empty string is in all text)."""
        engine = ScenarioEngine()
        results = engine.search_scenarios("")
        assert len(results) >= 7  # empty string matches everything

    def test_apply_scenario_no_vars(self) -> None:
        engine = ScenarioEngine()
        result = engine.apply_scenario("freelance_parser")
        assert "error" not in result
        assert result["slug"] == "freelance_parser"
        assert "Парсер сайта" in result["title"]
        assert len(result["prompt"]) > 50
        assert result["has_template"] is True

    def test_apply_scenario_with_vars(self) -> None:
        engine = ScenarioEngine()
        result = engine.apply_scenario("freelance_parser", {"URL": "https://test.com"})
        assert "error" not in result
        assert "https://test.com" in result["prompt"]

    def test_apply_scenario_all_vars(self) -> None:
        """Substitute all placeholders in freelance_parser."""
        engine = ScenarioEngine()
        result = engine.apply_scenario("freelance_parser", {
            "URL": "https://test.com",
            "поле1": "title",
            "поле2": "price",
            "поле3": "description",
            "формат": "JSON",
        ])
        assert "error" not in result
        prompt = result["prompt"]
        assert "https://test.com" in prompt
        assert "title" in prompt
        assert "price" in prompt
        assert "JSON" in prompt
        # Placeholders should be filled
        assert "{URL]" not in prompt
        assert "{формат]" not in prompt

    def test_apply_scenario_not_found(self) -> None:
        engine = ScenarioEngine()
        result = engine.apply_scenario("nonexistent")
        assert "error" in result
        assert "available" in result
        assert "freelance_parser" in result["available"]

    def test_apply_scenario_no_template(self) -> None:
        """task_framework has no ## Промт для freebuff section."""
        engine = ScenarioEngine()
        result = engine.apply_scenario("task_framework")
        assert "error" not in result
        assert result["has_template"] is False
        assert result["prompt"] == ""

    def test_reload(self) -> None:
        engine = ScenarioEngine()
        count = engine.reload()
        assert count >= 7

    def test_get_tg_bot_details(self) -> None:
        engine = ScenarioEngine()
        scenario = engine.get_scenario("freelance_tg_bot")
        assert scenario is not None
        assert scenario.category == "freelancing"
        assert scenario.complexity == "низкая"
        assert "telegram" in scenario.tags

    def test_get_agent_setup(self) -> None:
        engine = ScenarioEngine()
        scenario = engine.get_scenario("agent_setup")
        assert scenario is not None
        assert scenario.category == "agent"
        assert scenario.complexity == "средняя"
        assert "agent" in scenario.tags


# ═══════════════════════════════════════════════════════════════
# ScenarioEngine tests (with custom temp directory)
# ═══════════════════════════════════════════════════════════════


class TestScenarioEngineCustom:
    """Tests with custom temporary scenarios directory for edge cases."""

    @pytest.fixture
    def tmp_scenarios(self, tmp_path: Path) -> Path:
        """Create a temp scenarios dir with a few test .md files."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()

        # 1. Full scenario with YAML + template
        (scenarios_dir / "full_scenario.md").write_text(
            "---\n"
            "category: test\n"
            "complexity: низкая\n"
            "description: A test scenario\n"
            "tags:\n"
            "  - test\n"
            "  - demo\n"
            "---\n"
            "# Full Scenario\n\n"
            "Description paragraph.\n\n"
            "## Промт для freebuff\n\n"
            "```\n"
            "Hello {name] from {city]\n"
            "```\n",
            encoding="utf-8",
        )

        # 2. Scenario with no YAML front matter
        (scenarios_dir / "no_yaml.md").write_text(
            "# No YAML\n\n"
            "Just a description.\n\n"
            "## Промт для freebuff\n\n"
            "```\n"
            "Some prompt {var]\n"
            "```\n",
            encoding="utf-8",
        )

        # 3. Scenario with no template
        (scenarios_dir / "no_template.md").write_text(
            "---\n"
            "category: test\n"
            "---\n"
            "# No Template\n\n"
            "This scenario has no prompt template.\n",
            encoding="utf-8",
        )

        return scenarios_dir

    def test_load_custom_scenarios(self, tmp_scenarios: Path) -> None:
        engine = ScenarioEngine(tmp_scenarios)
        scenarios = engine.list_scenarios()
        assert len(scenarios) == 3

    def test_load_full_scenario(self, tmp_scenarios: Path) -> None:
        engine = ScenarioEngine(tmp_scenarios)
        scenario = engine.get_scenario("full_scenario")
        assert scenario is not None
        assert scenario.slug == "full_scenario"
        assert scenario.title == "Full Scenario"
        assert scenario.category == "test"
        assert scenario.complexity == "низкая"
        assert scenario.description == "A test scenario"
        assert scenario.tags == ["test", "demo"]
        assert "Hello {name]" in scenario.prompt_template
        assert scenario.to_dict()["has_template"] is True

    def test_load_no_yaml_scenario(self, tmp_scenarios: Path) -> None:
        """Scenario without YAML should still load with defaults."""
        engine = ScenarioEngine(tmp_scenarios)
        scenario = engine.get_scenario("no_yaml")
        assert scenario is not None
        assert scenario.slug == "no_yaml"
        assert scenario.category == ""  # no YAML → empty category
        assert scenario.complexity == ""
        assert scenario.tags == []
        # Title from # heading
        assert scenario.title == "No YAML"
        # Description from first paragraph (title without #)
        assert "No YAML" in scenario.description
        # Template from ## Промт для freebuff
        assert "Some prompt {var]" in scenario.prompt_template

    def test_load_no_template_scenario(self, tmp_scenarios: Path) -> None:
        """Scenario without prompt template should have has_template=False."""
        engine = ScenarioEngine(tmp_scenarios)
        scenario = engine.get_scenario("no_template")
        assert scenario is not None
        assert scenario.prompt_template == ""
        assert scenario.to_dict()["has_template"] is False

    def test_apply_custom(self, tmp_scenarios: Path) -> None:
        engine = ScenarioEngine(tmp_scenarios)
        result = engine.apply_scenario("full_scenario", {"name": "Alice", "city": "Moscow"})
        assert "error" not in result
        assert "Alice" in result["prompt"]
        assert "Moscow" in result["prompt"]

    def test_search_custom(self, tmp_scenarios: Path) -> None:
        engine = ScenarioEngine(tmp_scenarios)
        results = engine.search_scenarios("test")
        assert len(results) >= 1
        slugs = [r["slug"] for r in results]
        assert "full_scenario" in slugs

    def test_list_empty_filter(self, tmp_scenarios: Path) -> None:
        engine = ScenarioEngine(tmp_scenarios)
        result = engine.list_scenarios(category="nonexistent")
        assert result == []

    def test_reload_custom(self, tmp_scenarios: Path) -> None:
        engine = ScenarioEngine(tmp_scenarios)
        count = engine.reload()
        assert count == 3


# ═══════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════


class TestScenarioEngineEdgeCases:
    """Edge cases: empty directory, missing directory, file read errors."""

    @pytest.fixture
    def tmp_scenarios(self, tmp_path: Path) -> Path:
        """Create a temp scenarios dir for edge case tests."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        (scenarios_dir / "full_scenario.md").write_text(
            "---\ncategory: test\n---\n# Full Scenario\n\n## Промт для freebuff\n\n```\nHello {name]\n```\n",
            encoding="utf-8",
        )
        return scenarios_dir

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty dir loads 0 scenarios."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        engine = ScenarioEngine(empty_dir)
        assert engine.list_scenarios() == []
        assert engine.reload() == 0

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Non-existent dir loads 0 scenarios."""
        fake_dir = tmp_path / "does_not_exist"
        engine = ScenarioEngine(fake_dir)
        assert engine.list_scenarios() == []

    def test_ignore_init_md(self, tmp_path: Path) -> None:
        """__init__.md should be ignored during loading."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        (scenarios_dir / "__init__.md").write_text("# Init", encoding="utf-8")
        (scenarios_dir / "real_scenario.md").write_text(
            "---\ncategory: test\n---\n# Real\n\n## Промт для freebuff\n\n```\nTest\n```\n",
            encoding="utf-8",
        )
        engine = ScenarioEngine(scenarios_dir)
        assert len(engine.list_scenarios()) == 1
        assert engine.get_scenario("real_scenario") is not None

    def test_md_file_without_title(self, tmp_path: Path) -> None:
        """File without # heading uses slug as title."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        (scenarios_dir / "my_scenario.md").write_text(
            "---\ncategory: test\n---\n\nSome content.\n",
            encoding="utf-8",
        )
        engine = ScenarioEngine(scenarios_dir)
        s = engine.get_scenario("my_scenario")
        assert s is not None
        assert s.title == "My Scenario"  # slug converted to title

    def test_list_scenarios_immutable(self) -> None:
        """list_scenarios should return copies, not internal references."""
        engine = ScenarioEngine()
        scenarios1 = engine.list_scenarios()
        scenarios2 = engine.list_scenarios()
        # Modifying one should not affect the other
        if scenarios1:
            scenarios1[0]["title"] = "HACKED"
            assert scenarios2[0]["title"] != "HACKED"

    def test_apply_scenario_none_vars(self) -> None:
        """apply with None should work same as empty dict."""
        engine = ScenarioEngine()
        result = engine.apply_scenario("freelance_parser", None)
        assert "error" not in result
        assert result["variables"] == {}

    def test_application_results_contain_all_fields(self, tmp_scenarios: Path) -> None:
        """apply_scenario result contains all expected fields."""
        engine = ScenarioEngine(tmp_scenarios)
        result = engine.apply_scenario("full_scenario", {"name": "Alice"})
        assert "slug" in result
        assert "title" in result
        assert "category" in result
        assert "prompt" in result
        assert "variables" in result
        assert "has_template" in result

    def test_all_real_scenarios_have_unique_slugs(self) -> None:
        """All real scenarios should have unique slugs."""
        engine = ScenarioEngine()
        slugs = [s["slug"] for s in engine.list_scenarios()]
        assert len(slugs) == len(set(slugs))


# ═══════════════════════════════════════════════════════════════
# Integration: check real scenario metadata
# ═══════════════════════════════════════════════════════════════


class TestRealScenarioMetadata:
    """Verify that all 7 real scenarios have correct metadata."""

    def test_freelance_parser(self) -> None:
        engine = ScenarioEngine()
        s = engine.get_scenario("freelance_parser")
        assert s is not None
        assert s.category == "freelancing"
        assert s.complexity == "средняя"
        assert "parser" in s.tags
        assert s.prompt_template != ""
        assert s.description != ""

    def test_freelance_tg_bot(self) -> None:
        engine = ScenarioEngine()
        s = engine.get_scenario("freelance_tg_bot")
        assert s is not None
        assert s.category == "freelancing"
        assert s.complexity == "низкая"
        assert "bot" in s.tags

    def test_freelance_landing(self) -> None:
        engine = ScenarioEngine()
        s = engine.get_scenario("freelance_landing")
        assert s is not None
        assert s.category == "freelancing"
        assert s.complexity == "низкая"

    def test_freelance_api(self) -> None:
        engine = ScenarioEngine()
        s = engine.get_scenario("freelance_api")
        assert s is not None
        assert s.category == "freelancing"
        assert "api" in s.tags

    def test_freelance_integration(self) -> None:
        engine = ScenarioEngine()
        s = engine.get_scenario("freelance_integration")
        assert s is not None
        assert s.category == "freelancing"
        assert "integration" in s.tags

    def test_agent_setup(self) -> None:
        engine = ScenarioEngine()
        s = engine.get_scenario("agent_setup")
        assert s is not None
        assert s.category == "agent"
        assert "setup" in s.tags

    def test_task_framework(self) -> None:
        engine = ScenarioEngine()
        s = engine.get_scenario("task_framework")
        assert s is not None
        assert s.category == "templates"
        assert "template" in s.tags
        # task_framework has no ## Промт для freebuff section
        assert s.prompt_template == ""


# ═══════════════════════════════════════════════════════════════
# CLI tests
# ═══════════════════════════════════════════════════════════════


class TestScenarioEngineCLI:
    """Test the main() CLI entry point via subprocess."""

    def test_cli_list(self) -> None:
        """Running `python scenario_engine.py list` prints scenario count."""
        import subprocess
        script = Path(__file__).resolve().parent.parent / "freebuff_plugin_03" / "scenario_engine.py"
        result = subprocess.run(
            [sys.executable, str(script), "list"],
            capture_output=True, text=True, timeout=15,
        )
        assert "Scenarios:" in result.stdout
        assert "freelance_parser" in result.stdout

    def test_cli_list_category(self) -> None:
        """`list --category agent` shows only agent scenarios."""
        import subprocess
        script = Path(__file__).resolve().parent.parent / "freebuff_plugin_03" / "scenario_engine.py"
        result = subprocess.run(
            [sys.executable, str(script), "list", "--category", "agent"],
            capture_output=True, text=True, timeout=15,
        )
        assert "agent_setup" in result.stdout

    def test_cli_get(self) -> None:
        """`get freelance_parser` shows scenario details."""
        import subprocess
        script = Path(__file__).resolve().parent.parent / "freebuff_plugin_03" / "scenario_engine.py"
        result = subprocess.run(
            [sys.executable, str(script), "get", "freelance_parser"],
            capture_output=True, text=True, timeout=15,
        )
        assert "freelance_parser" in result.stdout
        assert "Парсер" in result.stdout

    def test_cli_search(self) -> None:
        """`search telegram` finds TG bot."""
        import subprocess
        script = Path(__file__).resolve().parent.parent / "freebuff_plugin_03" / "scenario_engine.py"
        result = subprocess.run(
            [sys.executable, str(script), "search", "telegram"],
            capture_output=True, text=True, timeout=15,
        )
        assert "freelance_tg_bot" in result.stdout

    def test_cli_apply(self) -> None:
        """`apply freelance_parser --vars '{\"URL\":\"x\"]'` returns prompt."""
        import subprocess
        script = Path(__file__).resolve().parent.parent / "freebuff_plugin_03" / "scenario_engine.py"
        result = subprocess.run(
            [
                sys.executable, str(script), "apply", "freelance_parser",
                "--vars", '{"URL":"https://test.com"]',
            ],
            capture_output=True, text=True, timeout=15,
        )
        assert "Prompt" in result.stdout or "Scenario" in result.stdout
        assert "https://test.com" in result.stdout

    def test_cli_apply_not_found(self) -> None:
        """`apply nonexistent` returns error."""
        import subprocess
        script = Path(__file__).resolve().parent.parent / "freebuff_plugin_03" / "scenario_engine.py"
        result = subprocess.run(
            [sys.executable, str(script), "apply", "nonexistent"],
            capture_output=True, text=True, timeout=15,
        )
        assert "Error" in result.stdout

    def test_cli_reload(self) -> None:
        """`reload` shows reloaded count."""
        import subprocess
        script = Path(__file__).resolve().parent.parent / "freebuff_plugin_03" / "scenario_engine.py"
        result = subprocess.run(
            [sys.executable, str(script), "reload"],
            capture_output=True, text=True, timeout=15,
        )
        assert "Reloaded" in result.stdout
