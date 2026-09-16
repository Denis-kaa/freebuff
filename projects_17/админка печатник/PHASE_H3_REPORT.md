# PHASE_H3_REPORT.md — H3: рендер + Apple-токены + главная + отчёт печатника

> **Статус:** COMPLETE · **Дата:** 2026-09-16
> **Этап:** H3 потока B (Reports Hub) · РОАДМАП_v7 §7 · reports-hub-spec.md §14.3
> **Верификация:** 40 passed (H1+H2+H3 тесты спеки) · mypy clean (21 файл) · живая генерация: 13 проектов / 228 страниц доков / 1.3с

---

## 1. Что сделано

| Артефакт | Файл | Суть |
|---|---|---|
| Сборка проектного отчёта | `report/project_report.py` | `build_project_report` → ReportModel по §7.1: метрики из статус-дока (249 passed / mypy clean 50 файлов), timeline из таблицы «этап/коммит/дата/результат» (13 этапов печатника), roadmap из роадмапа (чекбоксы + строки с эмодзи), blockers из указанного дока + `*OPEN_QUESTIONS*`, LOC по `loc_paths`, git-коммиты; отсутствующие источники → diagnostics |
| Библиотека документов | `report/doclibrary.py` | Карточки (тип, статус-цитата, дата, размер, резюме), `*исключения*` (worktree/.venv/node_modules/README), `doc_slug` — слаг с сохранением подкаталогов |
| Резюме | `report/summaries.py` | `SummaryProvider` (Protocol) + `DeterministicProvider` + `OverrideProvider` (`summaries.json`, приоритет override, осиротевшие ключи в диагностику), `slugify` (транслит кириллицы, хеш при пустоте) |
| Дизайн | `design/tokens.py`, `design/accent.py` | Apple-токены light/dark (`prefers-color-scheme` + переключатель), mobile-first сетка, `extract_accent` (логотип → конфиг → дефолт, Pillow опционален) |
| Рендер | `report/render.py` | Самодостаточные страницы (inline CSS/JS, только относительные ссылки, file://-совместимо): главная-галерея, статус-отчёт проекта, полный рендер дока, `manifest.json` (observability) |
| Генерация | `report/generate.py` | `generate_site`: профили → модели → страницы → сайт; `no_data`-карточки, диагностика, осиротевшие ключи |
| Профиль печатника | `projects_17/админка печатник/reports_hub.yaml` | Первый профиль сервиса (§2, §4.3): docs/timeline_sources/metrics.loc_paths/roadmap/blockers |
| CLI | `cli.py` | `generate` рабочий (`--project/--all/--site/--projects-root/--summaries`); `serve/diff` — заглушки H5/H4 |
| Тесты спеки 6 и 9 | `tests_09/test_reports_hub_render.py` + `test_reports_hub_golden_pechatnik.py` | 13 тестов: файлы сайта, `<title>`/токены темы, отсутствие абсолютных ссылок, manifest-контракт, no-data карточки, HTML-экранирование; golden печатника (13 этапов, 249 passed, mypy 50 файлов, 26 доков) |

## 2. Живая генерация (FACT, whimco)

```
python -m services_08.reports_hub generate --all
→ 13 проектов с отчётами · 17 без данных · 228 страниц доков · 1.28с
```

- `site/index.html` — галерея (карточки + секция «Без отчётных данных»);
- `site/projects/adminka-pechatnik/index.html` — 21 КБ, метрики 249 passed / mypy clean (50 файлов), timeline 13 этапов, roadmap H1–H6, библиотека 26 доков;
- `site/manifest.json` — счётчики по каждому проекту.

Выход сайта в `.gitignore` (`services_08/reports_hub/site/`): сайт — производный артефакт, источник истины — доки; H6 перегенерирует его при деплое.

## 3. Решения по ходу (и почему)

1. **`report/` вместо `build/`** — `build/` в `.gitignore` платформы (паттерн `build/`); переименование вместо добавления исключений.
2. **Метрики — из статус-дока**, не из суммы доков: иначе поздние PHASE-отчёты перетирали бы канонические числа («249 passed» → «385 passed»). Цифры всегда с источником `файл:строка`.
3. **`doc_slug` без расширения** (`project-status-report.html`) + сохранение подкаталогов: спека §11 (доки с одинаковым именем в разных подкаталогах не конфликтуют).
4. **Отчёт платформы — H5**: в H3 `--platform` возвращает честную диагностику, а не пустую страницу.
5. **`site/` не коммитится** (кроме решения о manifest): сайт перегенерируется за 1.3с, дубль в git не нужен.

## 4. Что НЕ входит (следующие этапы)

- H4: diff между генерациями (`site/data/history/*.json`, бейджи NEW/±N) + `summaries.json` агента + тесты 4, 8.
- H5: сервер (token-гейт, raw/zip) + отчёт платформы + тест 7.
- H6: systemd `reports-hub.service` (:8310) + деплой + смоук.