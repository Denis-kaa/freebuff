# Realtor OS

**Версия:** 0.1.0  
**Среда:** Termux на Android (ARM64, no-root)  
**Статус:** production-ready foundation  

Локальная автономная система для риелтора из «Этажи» (Пойковский). Работает без облачных LLM, шифрует персональные данные, распознаёт документы OCR, поддерживает локальный RAG и базу знаний.

---

## 🎯 Что делает

- **Локальный RAG** — поиск по базе объектов, шаблонов договоров, 152-ФЗ, ГК РФ.
- **Шифрование PII** — паспортные данные, ФИО, телефоны хранятся только в зашифрованном виде.
- **OCR документов** — распознавание через Tesseract без отправки в облако.
- **Локальная LLM** — мост к llama.cpp / Ollama для ответов и проверки данных.
- **Интеграции** — Яндекс Диск / Email с маскированием PII перед отправкой.
- **Knowledge Curator** — режим `/learn` для пополнения базы знаний.
- **Companion layer** — Buffy может контролировать проект через `buffy_manifest.json` и `companion/state.json`.

---

## 📂 Структура

```
realtor_os/
├── README.md                    # этот файл
├── MANIFEST.md                  # паспорт/манифест проекта
├── PASSPORT.md                  # технический паспорт
├── .env.example                 # пример секретов
├── config.yaml                  # конфигурация
├── pyproject.toml               # метаданные пакета
├── requirements.txt             # зависимости
├── scripts/
│   └── start_system.sh          # аудит среды и запуск
├── docs/
│   ├── ARCHITECTURE.md          # архитектура
│   ├── ROADMAP.md               # дорожная карта
│   └── CHANGELOG.md             # история изменений
├── src/realtor_os/
│   ├── core/security.py         # шифрование / дешифрование
│   ├── core/pii.py              # работа с PII
│   ├── rag/engine.py            # локальный RAG
│   ├── ocr/tesseract.py         # OCR
│   ├── llm/local_engine.py      # локальная LLM
│   ├── integrations/yandex_disk.py
│   ├── integrations/email.py
│   ├── curator/knowledge.py     # /learn
│   ├── companion/manifest.py    # генерация манифеста
│   ├── companion/state.py       # состояние для Buffy
│   ├── companion/watcher.py     # наблюдение и heartbeat
│   ├── config.py                # загрузка конфига
│   ├── logger.py                # логирование
│   ├── constants.py             # константы
│   └── cli.py                   # CLI
└── tests/                       # тесты
```

---

## 🚀 Установка

1. Скопируй `.env.example` в `.env` и заполни секреты:
   ```bash
   cp .env.example .env
   ```
2. Установи зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Запусти аудит среды:
   ```bash
   bash scripts/start_system.sh
   ```
4. Инициализируй систему:
   ```bash
   PYTHONPATH=src python -m realtor_os.cli --help
   ```

---

## 🛠 Использование

```bash
# Статус системы
PYTHONPATH=src python -m realtor_os.cli status

# Загрузить документ в RAG
PYTHONPATH=src python -m realtor_os.cli ingest --file docs/contract_template.pdf

# Задать вопрос локальной LLM через RAG
PYTHONPATH=src python -m realtor_os.cli ask "Какие документы нужны для сделки купли-продажи?"

# Распознать документ OCR
PYTHONPATH=src python -m realtor_os.cli ocr --file scans/passport.png

# Режим Knowledge Curator
PYTHONPATH=src python -m realtor_os.cli learn "холодные звонки в недвижимости"
```

---

## 🔐 Безопасность

- Все PII шифруются перед сохранением.
- Секреты только в `.env`.
- Нет `shell=True`, нет `os.system`, нет root.
- Все пути проверяются на path traversal.
- Интеграции маскируют PII перед отправкой.

---

## 📄 Лицензия

MIT — для личного использования риелтором.
