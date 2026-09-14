# PHASE_H1_REPORT.md — H1: каркас Reports Hub (ReportModel + автообход projects_17)

> **Статус:** COMPLETE · **Дата:** 2026-09-14
> **Этап:** H1 потока B (Reports Hub) · РОАДМАП_v7 §7 · reports-hub-spec.md §4.2/§14.1 (тесты №3, №5)
> **Верификация:** 16 passed (новые H1-тесты) · mypy clean (7 файлов пакета) · CLI list/generate на реальном projects_17

---

## 1. Что сделано

| Артефакт | Файл | Суть |
|---|---|---|
| Пакет | `services_08/reports_hub/__init__.py` | Каркас сервиса (решение №1: services_08, не projects_17) |
| Модель | `services_08/reports_hub/model.py` | `ReportModel`/`ProjectReport`/`Section`/`SourceRef` — dataclass-контракт, `schema_version=1`, JSON round-trip (тест №3). Закрытый словарь статусов `SECTION_STATUSES` (ANTI-6b). `status='missing'` + note вместо пустышек (§5.2 анти-галлюцинация) |
| Реэкспорт | `services_08/reports_hub/build/model.py` | Спеченный путь импорта без дублирования контракта (Single Source of Truth) |
| Обходчик | `services_08/reports_hub/config.py` | `discover_projects(projects_17)`: сигнатуры (PROJECT_STATUS_REPORT/FINAL_REPORT/MANIFEST + globs PHASE_*/РОАДМАП*/AUDIT*), `EXCLUDED_DIRS`, per-project `exclude: true`, битый yaml → причина в диагностике (не молча, §11), конфликт slug → `DiscoveryError` (B-Rule 5), кириллица → детерминированный хеш-слаг (§11 open question №1 v1) |
| CLI | `services_08/reports_hub/cli.py` + `__main__.py` | `list` (рабочий), `generate` (каркас модели, extract — H2), `serve`/`diff` — честные заглушки «этап H5/H4» (§10.1) |

## 2. REGISTER-FIRST (AGENTS.md §6)

- `reports_hub` зарегистрирован: `python -m core_02.missing_registry register reports_hub --kind module --factory platform …` → 51 запись, `check` exit 0. Статус `registered` (реализация закроется `mark-implemented` после H6-деплоя — каркас ≠ готовый сервис).

## 3. Проверка на реальных данных

`python -m services_08.reports_hub list` по живому `projects_17/`: **30 каталогов**, 15 с данными (в т.ч. `админка печатник → p-7f82735b6bdf`), 15 «нет данных» с причиной. Слаг кириллицы детерминирован. `generate` строит каркас модели без ошибок.

## 4. Верификация

- **Новые тесты:** `tests_09/test_reports_hub_model_contract.py` (6) + `tests_09/test_reports_hub_discovery.py` (10) = **16 passed** — спека №3 и №5 закрыты.
- **mypy:** `services_08/reports_hub/` — clean (7 файлов).
- **Полный tests_09/ (честная фиксация, вне скоупа H1):** 371 failed / 105 errors / 2617 passed / 3077 collected / 22 collection errors. Все сбои — **pre-existing**: маркеры восстановления (`***REMOVED***`) в `core_02/` от коммитов bd1b4fe/1862fbd ломают `re.compile`/импорты (22 файла НЕ собираются, `test_scenario_engine` — 64 FAILED и т.д.). Проверено на чистом worktree `origin/master` — та же порча в conftest/исходниках. **Ни одного FAILED/ERROR по `test_reports_hub_*`** в полном прогоне нет.
- Полный прогон тестов платформы — отдельный ремонтный этап (РЕКОМЕНДАЦИЯ: dedicated session «marker-repair round 2», см. §6).

## 5. Контракты (сохранены)

- Модель — единственный источник истины; сайт (H3) = детерминированный рендер модели.
- Ничего не пишется в projects_17 (только чтение) — не-цель §3 соблюдена.
- Ошибки не молчат: битый профиль/нет данных/конфликт slug — видимые причины.
- Идемпотентность закладывается: слаги детерминированы, модель сериализуема сортированно.

## 6. Что дальше (поток B, спека §14)

- **H2:** extract-слой (markdown.py, metrics.py, gitstats.py) + тесты №1, №2.
- **H3:** рендер + Apple-токены + главная + отчёт печатника + тесты №6, №9.
- **H4:** diff + summaries.json (тесты №4, №8) · **H5:** сервер + token-гейт + платформа (тест №7) · **H6:** systemd на whimco, порт 8310.
- **Вне потока B (рекомендация):** ремонтная сессия по маркерам восстановления core_02/tests_09 (371 failing — прежде всего мешает канонической метрике «3342+ passed» из CODE_QUALITY_STANDARD §11.6).
