"""Smoke-тест каркаса (Phase B+C, Шаг 0, CP-0).

Проверяет, что пакет app импортируется — структура собрана корректно.
"""


def test_app_package_importable() -> None:
    import app  # noqa: F401

    assert app.__version__ == "0.1.0"