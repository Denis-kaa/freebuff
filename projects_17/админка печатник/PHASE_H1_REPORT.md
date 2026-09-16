# PHASE_H1_REPORT.md — H1: каркас Reports Hub + ReportModel + автообход

> **Статус:** COMPLETE · **Дата:** 2026-09-16
> **Этап:** H1 потока B (Reports Hub) · РОАДМАП_v7 §7 · reports-hub-spec.md §14.1
> **Верификация:** 12 passed (test_reports_hub_model + test_reports_hub_discovery) · mypy clean (6 файлов reports_hub) · живой обход: 31 проект (печатник has-docs)

---

## 1. Что сделано

| Артефакт | Файл | Суть |
|---|---|---|
| Пакет сервиса | `services_08/reports_hub/__init__.py` | `SCHEMA_VERSION=1`, docstring-контракт (Additive/Contract First/SSOT/Observability/Graceful) |
| Модель | `services_08/reports_hub/report/model.py` | `ReportModel` + `MetricTile/TimelineEntry/DocCard/ReportSection` (frozen dataclasses, `to_json/from_json`, guard будущей версии) |
| Конфиг + автообход | `services_08/reports_hub/config.py` | `ProjectProfile`, `discover_projects(projects_17/)`, owner-файл `reports_hub.yaml` (свой парсер без зависимостей: скаляры + списки + `metrics.loc_paths`), сигнатуры отчётности, исключения служебных каталогов, битый YAML → `invalid_reason` без падения обхода |
| CLI | `services_08/reports_hub/cli.py` + `__main__.py` | `generate/serve/list/diff`; `list` рабочий (автообход), остальные — честная заглушка exit 2 (H3–H5) |
| Заглушки H2/H3 | `extract/`, `design/`, `templates/` (`__init__.py`) | Пустые пакеты с пометкой этапа реализации |
| Тесты спеки | `tests_09/test_reports_hub_model.py` (тест 3) + `tests_09/test_reports_hub_discovery.py` (тест 5) | 12 тестов: round-trip/гвард версии; docs/no-data/битый yaml/excluded/title/служебные/нет корня |
| Реестр | `data_13/missing_registry.yaml` (серверно-локально, в .gitignore) | `reports_hub` registered → prompt_written (`reports-hub-spec.md`) |

## 2. Контракты (сохранены)

- **Additive:** сервис только читает проекты, ничего не переписывает; новые файлы — только `services_08/reports_hub/` + `tests_09/test_reports_hub_*`.
- **Contract First:** `ReportModel` — dataclass-контракт, `schema_version` версионирует; сайт H3 = детерминированный рендер модели.
- **Без зависимостей:** парсер owner-YAML — stdlib (PyYAML не требуется); серверный venv печатника (`yaml` отсутствует) — учтено фактом, не предположением.
- **Не молча:** битый `reports_hub.yaml` → `invalid_reason` в профиле + диагностика главной (H3), не падение.

## 3. DoD §7 (H1)

Каркас + ReportModel + автообход готовы; тесты спеки 3 и 5 зелёные; живой `list` на whimco: 31 проект, печатник `has-docs`, 17 `has-docs` / 14 `no-data`, служебные исключены.

## 4. Верификация

- pytest: **12 passed** (`test_reports_hub_model` 5 + `test_reports_hub_discovery` 7, venv печатника `.venv`, 0.25с).
- mypy: **clean, 6 файлов** (`__init__/config/cli/__main__/build+model`, `--explicit-package-bases`).
- CLI: `python -m services_08.reports_hub list` → 31 строка, печатник `has-docs`.

## 5. Что НЕ входит (следующие этапы)

- H2: extract-слой (markdown/metrics/gitstats) + тесты 1, 2.
- H3: рендер + Apple-токены + главная + отчёт печатника + тесты 6, 9 (golden).
- H4: diff + summaries.json + тесты 4, 8. H5: сервер + отчёт платформы + тест 7. H6: systemd `reports-hub.service` :8310 + деплой.
