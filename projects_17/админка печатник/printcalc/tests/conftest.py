"""Фикстуры тестов printcalc_web: изолированная БД в tmp_path на тест."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from printcalc_web.db import connect


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture()
def conn(db_path: Path) -> Iterator:
    connection = connect(db_path)
    yield connection
    connection.close()
