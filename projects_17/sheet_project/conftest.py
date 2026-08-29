"""Pytest conftest: гарантирует корень проекта (sheet_project/) в sys.path,
чтобы `from config.schema import ...` работало при `pytest tests/` и
`python -m pytest tests/`."""

# Пустой по замыслу: наличие conftest.py в корне заставляет pytest добавить
# корень проекта в sys.path (prepend import mode), делая пакет `config`
# импортируемым из тестов без хаков с sys.path.
