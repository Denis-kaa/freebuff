# Технический паспорт Realtor OS

## Общие сведения

| Параметр | Значение |
|---|---|
| Название | Realtor OS |
| Версия | 0.1.0 |
| Язык | Python 3.11+ |
| Платформа | Termux / Android / ARM64 |
| Права | No-root |
| Лицензия | MIT |

## Стек

- Python 3.11+
- SQLite (FTS5 / sqlite-vec)
- Tesseract OCR
- llama.cpp / Ollama
- curl (POSIX) для внешних интеграций
- GPG / OpenSSL для шифрования

## Зависимости

См. `requirements.txt` и `pyproject.toml`.

## Компоненты

| Модуль | Назначение | Ключевые файлы |
|---|---|---|
| `core` | Безопасность и PII | `security.py`, `pii.py` |
| `rag` | Индексирование и поиск | `engine.py` |
| `ocr` | Распознавание документов | `tesseract.py` |
| `llm` | Локальная LLM | `local_engine.py` |
| `integrations` | Яндекс Диск, Email | `yandex_disk.py`, `email.py` |
| `curator` | Knowledge Curator | `knowledge.py` |
| `companion` | Интерфейс для Buffy | `manifest.py`, `state.py`, `watcher.py` |
| `cli` | Командная строка | `cli.py` |

## Интерфейсы

- CLI: `python -m realtor_os.cli <command>`
- Manifest: `buffy_manifest.json`
- State: `companion/state.json`
- Logs: `logs/realtor_os.log`

## Требования к окружению

- Termux из F-Droid
- Python 3.11+
- tesseract (pkg install tesseract)
- ollama или llama.cpp (опционально)
- 2+ ГБ свободного места
