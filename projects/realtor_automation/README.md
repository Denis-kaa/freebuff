# realtor_automation

Проект локальной автоматизации для риелтора («Этажи», Пойковский).
Хранит и обрабатывает данные локально, не отправляет PII в облачные LLM API.

## Возможности (v0.1 — foundation)

- `rag` — локальный поиск по документам (SQLite FTS5 / fallback LIKE).
- `security` — шифрование конфиденциальных данных перед сохранением/отправкой.
- `ocr` — OCR документов через Tesseract (опционально).
- `llm` — работа с локальной LLM через Ollama / llama.cpp.
- `integrations` — заглушки для Яндекс Диска и Email (без PII в сторонних API).
- `curator` — модуль `/learn` для сбора обучающих материалов.
- `cli` — единый интерфейс командной строки.

## Установка

```bash
cd projects/realtor_automation
pip install -r requirements.txt
```

## Конфигурация

```bash
cp .env.example .env
# Отредактируй .env
```

## Использование

```bash
# Справка
PYTHONPATH=src python -m realtor_automation.cli --help

# Текущий статус проекта
python -m src.realtor_automation.cli status

# Добавить документ в базу знаний
python -m src.realtor_automation.cli ingest --file contract_template.txt --tag contracts

# Запрос к локальному RAG
python -m src.realtor_automation.cli ask "Какие документы нужны для продажи квартиры?"

# Сгенерировать план обучения
python -m src.realtor_automation.cli learn "холодные звонки в недвижимости"
```

## Структура проекта

```
projects/realtor_automation/
├── README.md
├── requirements.txt
├── .env.example
├── config.yaml
├── src/realtor_automation/
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── state.py
│   ├── security.py
│   ├── rag.py
│   ├── ocr.py
│   ├── llm.py
│   ├── integrations.py
│   ├── curator.py
│   └── cli.py
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_state.py
    └── test_security.py
```

## Безопасность

- Секреты хранятся в `.env`.
- PII шифруется перед сохранением.
- Интеграции с внешними сервисами работают только через зашифрованные данные и токены.
- Без root; совместимость с Termux/Android/ARM64.

## Лицензия

MIT / Internal use.
