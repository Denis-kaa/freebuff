# Архитектура Realtor OS

## Общая схема

```
┌─────────────────────────────────────┐
│              CLI / UI               │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Orchestrator               │
│  (CLI → command router)            │
└──────┬──────┬──────┬──────┬───────┘
       │      │      │      │
   ┌───┴──┐ ┌─┴───┐ ┌─┴───┐ ┌─┴─────┐
   │ RAG  │ │ OCR │ │ LLM │ │ Sync  │
   └──────┘ └─────┘ └─────┘ └───────┘
       │                         │
   ┌───┴──┐                 ┌───┴───┐
   │ SQLite│                 │ Yandex│
   │  FTS5 │                 │ Disk  │
   └───┬───┘                 └───┬───┘
       │                         │
┌──────┴──────────────────────────┴───┐
│        Security / PII layer       │
│   (encrypt before write/send)       │
└─────────────────────────────────────┘
```

## Принципы

1. **Single Responsibility** — каждый модуль делает одну задачу.
2. **No cloud LLM** — LLM работает локально.
3. **PII-first security** — конфиденциальные данные шифруются до записи.
4. **Termux-native** — POSIX-команды, no-root.
5. **Companion-ready** — Buffy управляет через manifest/state файлы.

## Поток данных

### Ingest (загрузка документа)

1. CLI → `ocr/tesseract.py` (если PDF/изображение) или `rag/engine.py` (если текст).
2. Извлечённый текст проверяется на наличие PII.
3. PII маскируется/шифруется.
4. Данные индексируются в SQLite.

### Ask (вопрос системе)

1. CLI → `rag/engine.py` ищет релевантные фрагменты.
2. Собирается контекст.
3. Запрос отправляется в `llm/local_engine.py`.
4. Ответ возвращается пользователю.

### Sync (синхронизация)

1. CLI → `integrations/yandex_disk.py`.
2. Данные шифруются перед отправкой.
3. Загружаются на Яндекс Диск как зашифрованный архив.

## Форматы данных

### `buffy_manifest.json`

```json
{
  "project": "realtor_os",
  "version": "0.1.0",
  "owner": "realtor_etagi_poykovsky",
  "commands": {
    "status": "PYTHONPATH=src python -m realtor_os.cli status",
    "start": "bash scripts/start_system.sh"
  ***REMOVED***,
  "state_file": "companion/state.json",
  "log_file": "logs/realtor_os.log"
***REMOVED***
```

### `companion/state.json`

```json
{
  "version": "0.1.0",
  "status": "healthy",
  "last_check": "2026-07-29T00:00:00Z",
  "components": {
    "rag": "ok",
    "ocr": "ok",
    "llm": "ok"
  ***REMOVED***
***REMOVED***
```

## Масштабируемость

- Новые интеграции добавляются в `src/realtor_os/integrations/`.
- Новые источники знаний — в `src/realtor_os/curator/`.
- Новые модели LLM — в `src/realtor_os/llm/`.
