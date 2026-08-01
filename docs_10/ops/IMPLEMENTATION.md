# Implementation Details

> **Сессия:** 2026-07-28
> **Фичи:** ContextManager bridge, Lightpanda worker

---

## 1. ContextManager Bridge (`scripts_01/agent_context_bridge.py`)

### Что делает
Singleton-мост, который позволяет `termux-ai-agent` сохранять каждый диалог в `freebuff/data_13/context.db`.

### Поток
1. `termux-ai-agent/main.py` импортирует `get_context_bridge`.
2. При каждом `run(raw_query)`:
   - `log_user(raw_query)`
   - после получения ответа `log_assistant(result_dict)`
   - при ошибке `log_error(exception)`
3. `_maybe_checkpoint()` создаёт чекпоинт каждые 10 сообщений.
4. `auto_conspect()` завершает сессию и сохраняет конспект в `context_12/summaries/`.

### Ключевые файлы
- `scripts_01/agent_context_bridge.py`
- `termux-ai-agent/main.py`
- `scripts_01/context_manager.py`

---

## 2. Lightpanda Worker (`src_06/workers/lightpanda_worker.py`)

### Что делает
Python-обёртка вокруг Lightpanda binary, запускаемого через `.tools/lightpanda` wrapper внутри `proot-distro Ubuntu`.

### Методы
- `execute_agent_task(task, provider, timeout)` — Agent Mode с LLM.
- `run_script(script_path, timeout)` — запуск PandaScript.
- `dump_url(url, output_format, timeout)` — получить текст/HTML страницы.
- `serve_cdp(host, port)` — фоновый CDP-сервер.
- `stop_cdp()` — остановить CDP-сервер.

### Поток
1. `LightpandaWorker` находит wrapper или бинарь.
2. Формирует список аргументов.
3. `subprocess.run` с таймаутом.
4. `LightpandaResult` возвращает stdout/stderr + exit code.

### Ключевые файлы
- `src_06/workers/lightpanda_worker.py`
- `scripts_01/install_lightpanda.sh`
- `../projects_meta/LIGHTPANDA_INTEGRATION.md`

---

## 3. Установка Lightpanda

```bash
bash scripts_01/install_lightpanda.sh
```

Шаги:
1. Установить `proot-distro` через `pkg`.
2. Установить Ubuntu, если отсутствует.
3. Внутри Ubuntu скачать `lightpanda-aarch64-linux.tar.gz` и распаковать в `/usr/local/bin/lightpanda`.
4. Создать wrapper `.tools/lightpanda`.
5. Проверить `lightpanda version`.

---

## 4. Интеграция с ToolRuntime

В будущем `LightpandaWorker` может быть зарегистрирован как tool `browser` в `scripts_01/tool_runtime.py`:

```python
from src.workers.lightpanda_worker import LightpandaWorker

class BrowserTool(BaseTool):
    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="browser",
            parameters=[
                ParamSchema(name="action", enum=["dump", "agent"***REMOVED***, required=True),
                ParamSchema(name="url", type="string"),
                ParamSchema(name="task", type="string"),
            ***REMOVED***,
        )
```

---

## 5. Тестирование

```bash
python -m pytest tests_09/test_agent_context_bridge.py tests_09/test_lightpanda_worker.py -v
```

Тесты используют `unittest.mock` для `subprocess.run`/`Popen` и временные директории для `ContextManager`.
