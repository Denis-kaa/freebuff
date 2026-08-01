# Lightpanda Integration Guide

> **Статус:** MVP реализован (v1.0.0)
> **Платформа:** Termux + proot-distro Ubuntu (ARM64)
> **Файлы:**
>   - `scripts_01/install_lightpanda.sh`
>   - `src_06/workers/lightpanda_worker.py`
>   - `LIGHTPANDA_INTEGRATION.md`
>   - `WORKERS.md`
>   - `../core/ARCHITECTURE.md`

---

## Что такое Lightpanda

[Lightpanda***REMOVED***(https://lightpanda.io) — headless-браузер, написанный с нуля на Zig для AI-агентов:

- Не Chromium/WebKit, а новый движок
- Потребляет в 16 раз меньше памяти (≈123 MB vs 2 GB Chrome)
- Работает в 9 раз быстрее на типичных задачах
- Поддерживает JS, DOM, Fetch, XHR
- Имеет Agent Mode, PandaScript, CDP-сервер, MCP-сервер
- ARM64 Linux builds доступны

---

## Установка

```bash
bash scripts_01/install_lightpanda.sh
```

Скрипт выполнит:
1. Установит `proot-distro` (если не установлен)
2. Установит/проверит Ubuntu внутри `proot-distro`
3. Скачает `lightpanda-aarch64-linux` и положит в `/usr/local/bin/lightpanda` внутри Ubuntu
4. Создаст wrapper-скрипт `.tools/lightpanda` в корне freebuff
5. Проверит `lightpanda version`

### Требования

- Termux (Android)
- `pkg install proot-distro`
- ≈ 500 MB свободного места
- Internet для скачивания бинаря

---

## Быстрый старт

```python
from src.workers.lightpanda_worker import LightpandaWorker

worker = LightpandaWorker()

# Агентный режим
result = worker.execute_agent_task(
    "Find the latest release of python/cpython on GitHub",
    provider="ollama",
)
print(result.data)

# PandaScript
result = worker.run_script("examples/save_github_search.js")
print(result.data)

# Простой dump
result = worker.dump_url("https://example.com", format="markdown")
print(result.data)

# CDP-сервер для Puppeteer
worker.serve_cdp(host="127.0.0.1", port=9222)
```

---

## Методы LightpandaWorker

| Метод | Описание |
|-------|----------|
| `execute_agent_task(task, provider, timeout)` | Agent Mode с LLM |
| `run_script(script_path, timeout)` | Запуск PandaScript |
| `dump_url(url, format, timeout)` | Получить страницу как markdown/html/text |
| `serve_cdp(host, port)` | Запустить CDP-сервер |
| `stop_cdp()` | Остановить CDP-сервер |

---

## Архитектурная позиция

```
freebuff/
├── orchestrator.py
├── scripts_01/tool_runtime.py
└── src_06/workers/lightpanda_worker.py  ← новый компонент

proot-distro Ubuntu
└── /usr/local/bin/lightpanda  ← бинарь
```

Взаимодействие через wrapper `.tools/lightpanda`, который делегирует вызовы в proot.

---

## Юзкейсы

1. **Поиск документации по API** — агент открывает сайт, находит раздел Docs, возвращает ссылки.
2. **Парсинг статей в Markdown** — `dump_url(url, format="markdown")`.
3. **Автоматическое тестирование сайта** — PandaScript проверяет наличие элементов.
4. **Сбор данных с маркетплейсов** — Agent Mode исследует страницы и извлекает таблицы.
5. **Мониторинг изменений** — периодический `dump_url` + diff.

---

## Интеграция с MCP

Lightpanda имеет native MCP server. Для включения в `scripts_01/mcp_server.py` добавьте:

```json
{
  "lightpanda": {
    "command": "/storage/emulated/0/PROJECTS/workstation/freebuff/.tools/lightpanda",
    "args": ["mcp"***REMOVED***
  ***REMOVED***
***REMOVED***
```

---

## Тестирование

```bash
cd /storage/emulated/0/PROJECTS/workstation/freebuff
python -m pytest tests_09/test_lightpanda_worker.py -v
```

---

## Риски

- **glibc:** бинарь Lightpanda линкован с gllibc, поэтому не работает напрямую в Termux. Используется proot-distro Ubuntu.
- **OOM:** Android может убить тяжёлый процесс. Избегайте параллельного запуска множества вкладок.
- **Beta:** Lightpanda в активной разработке; некоторые команды могут измениться.
