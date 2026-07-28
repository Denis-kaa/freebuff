# Workers

> **Статус:** MVP
> **Версия:** 1.0.0

В freebuff **worker** — это Python-класс, который делегирует сложную работу внешнему процессу или сервису. Workers живут в `src/workers/` и имеют единый интерфейс:

- чётко определён вход (параметры)
- структурированный выход (dataclass результата)
- обработку ошибок и таймаутов
- минимум зависимостей от остальной системы

---

## Список workers

| Worker | Файл | Назначение |
|--------|------|------------|
| **LightpandaWorker** | `src/workers/lightpanda_worker.py` | Headless browser automation через Lightpanda |

---

## Жизненный цикл (v1)

На текущий момент все workers **stateless и transient**: каждый вызов создаёт subprocess, выполняет задачу, завершает процесс. Это упрощает восстановление после OOM и избавляет от необходимости следить за долгоживущими демонами.

```
оркестратор → worker.execute(...) → subprocess(lightpanda) → result
```

В будущем, если появятся долгоживущие воркеры (CDP-сервер, MCP-сервер), lifecycle будет расширен:

```
оркестратор → worker.start() → background process → commands → stop()
```

---

## Авто-документирование

Изменение воркера автоматически активирует триггер **Worker / tool** в `scripts/buffy_autodoc.py`. Это означает, что при коммите кода в `src/workers/` pre-commit hook ожидает обновления `docs/WORKERS.md` и `CHANGELOG.md`.

- Подробнее о триггерах: [`docs/RULES.md` — Авто-триггер документирования***REMOVED***(RULES.md)
- Установить pre-commit hook: `bash scripts/install_hooks.sh`

## Конвенции

1. **Все пути** рассчитываются от `workspace_root`.
2. **Бинарные зависимости** ищутся сначала в `.tools/`, затем в `PATH`.
3. **Ошибки** не подавляются; они возвращаются в `result.error`.
4. **Таймаут** всегда обязателен для внешних процессов.
5. **Логирование** оставляется на вызывающей стороне.

---

## Добавление нового worker

1. Создай `src/workers/<name>_worker.py`.
2. Определи класс с суффиксом `*Worker`.
3. Возвращай результат через dataclass (`*Result`).
4. Добавь unit-тесты в `tests/test_<name>_worker.py`.
5. Зарегистрируй в `src/workers/__init__.py`.
6. Обнови этот документ и `docs/ARCHITECTURE.md`.
7. Обнови `CHANGELOG.md` и убедись, что pre-commit hook (`bash scripts/install_hooks.sh`) не блокирует коммит.
