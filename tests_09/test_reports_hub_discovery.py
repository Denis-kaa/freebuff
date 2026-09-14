#!/usr/bin/env python3
"""tests_09/test_reports_hub_discovery.py — тест №5 спеки reports-hub.

Автообход projects_17 (services_08/reports_hub/config.py): проект с доками →
has_data=True; без доков → has_data=False с причиной «нет отчётной
документации» (решение №12, не молча); битый reports_hub.yaml → ошибка в
диагностике (§11); exclude: true пропускает; конфликт slug → DiscoveryError;
служебные каталоги не обходятся. Hermetic: tmp_path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services_08.reports_hub.config import (
    DiscoveryError,
    discover_projects,
    make_slug,
)


def _mk(root: Path, name: str) -> Path:
    d = root / name
    d.mkdir(parents=True)
    return d


# --- проект с отчётностью ---------------------------------------------------


def test_project_with_status_report(tmp_path: Path) -> None:
    root = tmp_path
    _mk(root, "alpha")
    (root / "alpha" / "PROJECT_STATUS_REPORT.md").write_text("# статус", encoding="utf-8")
    found = discover_projects(root)
    assert len(found) == 1
    assert found[0].has_data is True
    assert found[0].reason == ""


def test_project_with_phase_glob(tmp_path: Path) -> None:
    root = tmp_path
    _mk(root, "beta")
    (root / "beta" / "PHASE_RULES_R0_REPORT.md").write_text("#", encoding="utf-8")
    assert discover_projects(root)[0].has_data is True


# --- проект без отчётности ---------------------------------------------------


def test_project_without_reports_is_card_no_data(tmp_path: Path) -> None:
    root = tmp_path
    _mk(root, "empty_project")
    (root / "empty_project" / "src").mkdir()
    found = discover_projects(root)
    assert found[0].has_data is False
    assert found[0].reason == "нет отчётной документации"


# --- профили ----------------------------------------------------------------


def test_broken_yaml_profile_goes_to_diagnostics(tmp_path: Path) -> None:
    root = tmp_path
    d = _mk(root, "broken")
    (d / "PROJECT_STATUS_REPORT.md").write_text("#", encoding="utf-8")
    (d / "reports_hub.yaml").write_text("title: [oops", encoding="utf-8")  # битый YAML
    found = discover_projects(root)
    assert found[0].has_data is False
    assert "профиль невалиден" in found[0].profile_error
    assert found[0].reason == found[0].profile_error  # причина видна (не молча)


def test_exclude_true_skips_project(tmp_path: Path) -> None:
    root = tmp_path
    d = _mk(root, "skipped")
    (d / "PROJECT_STATUS_REPORT.md").write_text("#", encoding="utf-8")
    (d / "reports_hub.yaml").write_text("exclude: true\n", encoding="utf-8")
    assert discover_projects(root) == []


def test_valid_profile_is_loaded(tmp_path: Path) -> None:
    root = tmp_path
    d = _mk(root, "profiled")
    (d / "PROJECT_STATUS_REPORT.md").write_text("#", encoding="utf-8")
    (d / "reports_hub.yaml").write_text('title: "Мой проект"\n', encoding="utf-8")
    found = discover_projects(root)
    assert found[0].profile == {"title": "Мой проект"}


# --- служебные каталоги и сортировка ----------------------------------------


def test_excluded_and_hidden_dirs_skipped(tmp_path: Path) -> None:
    root = tmp_path
    _mk(root, "__pycache__")
    _mk(root, ".git")
    _mk(root, "node_modules")
    assert discover_projects(root) == []


# --- slug-правила ------------------------------------------------------------


def test_slug_cyrillic_is_hashed_deterministically() -> None:
    a = make_slug("админка печатник")
    b = make_slug("админка печатник")
    assert a == b, "слаг детерминирован (идемпотентная генерация, спека §10.1)"
    assert a.startswith("p-")
    assert make_slug("plain-name") == "plain-name"


def test_slug_collision_raises() -> None:
    taken = {"plain-name"}
    with pytest.raises(DiscoveryError, match="конфликт slug"):
        make_slug("plain-name", taken=taken)


def test_discovery_missing_root_raises(tmp_path: Path) -> None:
    with pytest.raises(DiscoveryError, match="не найден"):
        discover_projects(tmp_path / "nope")
