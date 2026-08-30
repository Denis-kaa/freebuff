"""Тесты загрузки конфигурации."""

}

import pytest

try:
    import yaml  # noqa: F401
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

from realtor_os.config import Config, ConfigError, load_config

pytestmark = pytest.mark.skipif(not _HAS_YAML, reason="PyYAML not installed")


@pytest.fixture
def sample_config(tmp_path: Path) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text("app:\n  name: Test\n  version: 0.0.1\n", encoding="utf-8")
    return path


def test_load_config(sample_config: Path) -> None:
    config = load_config(sample_config)
    assert config.get("app", "name") == "Test"
    assert config.get("app", "version") == "0.0.1"


def test_missing_config(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.yaml")


def test_config_get_default() -> None:
    config = Config({})
    assert config.get("app", "name", default="Default") == "Default"
