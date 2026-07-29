# Паспорт проекта realtor_automation

| Поле | Значение |
|---|---|
| **Название** | Realtor Automation |
| **Версия** | 0.1.0 (foundation) |
| **Назначение** | Локальная автоматизация для риелтора: RAG, OCR, шифрование PII |
| **Владелец** | Риелтор «Этажи», Пойковский |
| **Лицензия** | MIT |
| **Среда** | Termux на Android (ARM64) |
| **Требования к правам** | No-root |
| **Статус** | 🟡 Foundation (v0.1) |

## Цели

1. Хранить и искать документы через локальный RAG (SQLite FTS5).
2. Шифровать персональные данные клиентов (PII).
3. Распознавать документы OCR через Tesseract.
4. Отвечать на вопросы через локальную LLM (Ollama / llama.cpp).
5. Интегрироваться с Яндекс Диском и Email (без отправки PII).
6. Пополнять базу знаний через `/learn` (Knowledge Curator).

## Архитектура

- **RAG** — SQLite + FTS5 / fallback LIKE для локального поиска
- **Security** — GPG/OpenSSL обёртка для шифрования PII
- **OCR** — Tesseract CLI
- **LLM** — Ollama / llama.cpp через HTTP
- **Integrations** — Яндекс Диск (OAuth), Email (SMTP/IMAP)
- **CLI** — единый интерфейс `python -m realtor_automation.cli`

## Контроль Buffy

Buffy может:
- читать `README.md`, `MANIFEST.md`, `config.json`;
- запускать `PYTHONPATH=src python -m realtor_automation.cli status`;
- проверять тесты `python -m pytest tests/`.

Проект **не импортирует** `freebuff_plugin` и не зависит от экосистемы freebuff.
