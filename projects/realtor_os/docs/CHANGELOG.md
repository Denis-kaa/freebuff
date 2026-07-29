# Changelog Realtor OS

## [0.1.0***REMOVED*** — 2026-07-29

### Добавлено
- Проектная структура.
- Манифест (`MANIFEST.md`), технический паспорт (`PASSPORT.md`), архитектура (`docs/ARCHITECTURE.md`).
- Модуль `core/security.py` для шифрования/дешифрования PII.
- Модуль `core/pii.py` для работы с персональными данными.
- Модуль `config.py` для загрузки конфигурации.
- Модуль `logger.py` с поддержкой DEBUG/QUIET.
- Модуль `constants.py` с константами.
- CLI (`cli.py`) с командами `status`, `ask`, `ingest`, `ocr`, `learn`, `--help`, `--version`.
- Companion layer: `companion/manifest.py`, `companion/state.py`, `companion/watcher.py`.
- Тесты: `test_security.py`, `test_config.py`, `test_rag.py`, `test_curator.py`.
- Скрипт запуска `scripts/start_system.sh`.
