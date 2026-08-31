"""Общие фикстуры и пути (Phase B+C, Шаг 9). Hermetic: без сети."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "exercism"
SOURCES_YAML = ROOT / "configs" / "sources.yaml"
MAP_YAML = ROOT / "configs" / "competency_map.yaml"
OVERRIDES_YAML = ROOT / "configs" / "exercise_overrides.yaml"


@pytest.fixture()
def fixture_root() -> Path:
    return FIXTURES


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "corpus_test.db"


def pytest_collection_modifyitems(config, items):
    """integration-маркер не запускается по умолчанию (требует реального клона)."""
    if config.getoption("-m") != "" and "integration" in config.option.markexpr:
        return
    skip_integration = pytest.mark.skip(reason="github-клон не требуется для unit; включи: -m integration")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)