# PHASE_H2_REPORT.md — H2: extract-слой Reports Hub (markdown/metrics/gitstats/pytestinfo/registry)

> **Статус:** COMPLETE · **Дата:** 2026-09-16
> **Этап:** H2 потока B (Reports Hub) · РОАДМАП_v7 §7 · reports-hub-spec.md §14.2
> **Верификация:** 27 passed (модель 5 + обход 7 + extract 5 + metrics 10) · mypy clean (14 файлов)

---

## 1. Что сделано

| Артефакт | Файл | Суть |
|---|---|---|
| Markdown-парсер | `extract/markdown.py` | h1–h4 → дерево секций, таблицы (заголовок/разделитель/строки), цитаты шапки → `top_quotes` + секция, `find_sections`, `first_paragraph` (пропуск служебных `**Коммит:**`) |
| Regex-метрики | `extract/metrics.py` | `tests_passed/mypy_clean/version/status_emoji`, каждый хит с источником `файл:строка`, `summarize_metrics` (последнее значение) |
| Git-статистика | `extract/gitstats.py` | `git log --format --date=short` по каталогу проекта, вне git → `[]` (раздел скрывается, H3) |
| Счётчик тестов | `extract/pytestinfo.py` | `pytest --collect-only -q` с кэшем по mtime; интерпретатор по умолчанию — `sys.executable` (bare `python3` без pytest — ловушка среды, найдена тестом) |
| Реестр | `extract/registry.py` | Сводка MissingRegistry без зависимости от core_02 (regex `status:`), нет файла → `available=False` |
| Тесты спеки | `tests_09/test_reports_hub_extract.py` (тест 1) + `tests_09/test_reports_hub_metrics.py` (тест 2) | 15 тестов на фикстуре из реального PROJECT_STATUS_REPORT |

## 2. Найдено и исправлено по ходу (честно)

1. Разделитель таблицы `|---|---|` лочился regex с обязательным trailing-pipe — цитата `> Дата: ...` считалась разделителем. Заменён на строгий `_is_table_separator` (только `|-: ` + дефис).
2. Строка `**Коммит:** ...` с `|` внутри считалась строкой таблицы — исключение служебных строк + флаг `in_table`.
3. `first_paragraph` возвращал метаданные вместо сути — пропуск `**Коммит:**` и коротких `**...**`.
4. `count_tests` вызывал bare `python3` (без pytest) — теперь `sys.executable` по умолчанию.
5. Singleton-разделитель `---` ломал состояние таблицы — явная ветка horizontal-rule.

## 3. Живая проверка на печатнике (FACT)

- Секций: 21, верхних цитат: 3; метрики: `tests_passed=249` (PROJECT_STATUS_REPORT.md:132), `mypy_clean=clean (50 файлов)` (там же).
- Git печатника: 5 коммитов; реестр: 52 записи (34 implemented · 16 registered · 1 design_ready · 1 prompt_written); `tests_09`: 2785 collected.

## 4. DoD §7 (H2)

Extract-слой готов; тесты спеки 1 и 2 зелёные; H1-тесты не сломаны (27 суммарно); mypy clean.

## 5. Что НЕ входит (следующие этапы)

- H3: рендер + Apple-токены + главная + отчёт печатника + тесты 6, 9 (golden).
- H4: diff + summaries.json + тесты 4, 8. H5: сервер + отчёт платформы + тест 7. H6: systemd `:8310` + деплой.
