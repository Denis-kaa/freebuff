"""Tests for config loader."""

***REMOVED***

import pytest

from realtor_automation.config import ConfigError, load_config


def test_load_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_load_config_parses_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"app": {"version": "0.1.0"***REMOVED******REMOVED***', encoding="utf-8")
    config = load_config(tmp_path)
    assert config["app"***REMOVED***["version"***REMOVED*** == "0.1.0"
