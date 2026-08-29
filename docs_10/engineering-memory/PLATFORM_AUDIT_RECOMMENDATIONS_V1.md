# PLATFORM_AUDIT_RECOMMENDATIONS_V1.md — Аудит платформы: 25 рекомендаций

| Поле | Значение |
|------|----------|
| **Документ** | PLATFORM_AUDIT_RECOMMENDATIONS_V1.md |
| **Статус** | 📋 АУДИТ (read-only, 2026-08-12) — рекомендации, реализация по register-first |
| **Версия** | 1.0 |
| **Дата** | 2026-08-12 |
| **Метод** | Полный аудит кода (core_02: 25 py · scripts_01: 68 py · tests_09: 98 py) + документации (docs_10: 181 md · pompts_11: 76 md) + реестров (DOCUMENT_REGISTRY, missing_registry, forge_registry) + проверок (consistency_check, pytest collect, drift) |
| **Ключевые факты** | 2694 теста собрано · consistency_check TOTAL 0 CONSISTENT True · missing_registry ok (9 записей) · CHANGELOG v5.187.3 vs TASK.md v5.110.0 · DOCUMENT_REGISTRY: 18 путей из 181 md |
| **Главное правило** | Каждая рекомендация — с evidence (path + факт). Реализация — аддитивная (CAN-16) + register-first (AGENTS.md §5), без переписывания истории (CAN-17). |

---

## 1. Сводка аудита

Платформа архитектурно здорова (consistency_check: **TOTAL 0, CONSISTENT True**; 2694 теста коллектируется; реестр missing valid). Выявленные проблемы — **гигиенические и процессные**, не архитектурные: дрейф версий в доках (77 релизов отставания), неполный DOCUMENT_REGISTRY (164 md вне реестра по comm; 181−18=163 без self-reference DOCUMENT_REGISTRY.md), устаревшая таблица тест-счётчиков (2181 vs фактических 2694), битые ссылки в DRIFT_REPORT, дубли директорий, незакрытый register-first бэклог (7 из 9 записей не `implemented`).

Ниже — **25 рекомендаций** по 7 областям: A. Версии и счётчики · B. Реестры документов · C. Ссылки и naming · D. Код · E. Структура каталогов · F. Register-first бэклог · G. Процессы и git.

---

## 2. Рекомендации

### A. Версии и счётчики

**R1 — [CRITICAL***REMOVED*** Синхронизировать версию проекта в TASK.md/BUFFY_PROJECT.md с CHANGELOG.**
*Evidence:* CHANGELOG.md top = `[5.187.3***REMOVED*** — 2026-08-11`; TASK.md = «Версия проекта: v5.110.0 (2026-08-09)»; BUFFY_PROJECT.md = «v5.110.0 (latest shipped)». Отставание ≈ 77 релизов.
*Рекомендация:* единый источник версии (CHANGELOG); TASK.md/BUFFY_PROJECT.md обновлять при каждом release (или вынести версию в один файл `VERSION` и ссылаться).
*Эффект:* исключает путаницу «какая версия актуальна».

**R2 — [HIGH***REMOVED*** Убрать stale-версии из BUFFY.md (v5.59.0, v5.74.0).**
*Evidence:* BUFFY.md:367 «Что уже есть (v5.59.0)»; BUFFY.md:18 «(2026-08-04, v5.74.0)» — проект давно на v5.187.x.
*Рекомендация:* заменить «на момент vX» на «по состоянию на 2026-08-12» без версии, либо проставить актуальную.
*Эффект:* доки перестают противоречить CHANGELOG.

**R3 — [HIGH***REMOVED*** Обновить таблицу test counters в CODE_QUALITY_STANDARD.md (2181 → 2694).**
*Evidence:* последняя запись таблицы «2026-08-04 | 2181»; фактический `pytest --collect-only` = **2694 теста**.
*Рекомендация:* добавить строку `2026-08-12 | 2694 | CI-slice + forensics + audits | pytest collect` с provenance; старые строки не трогать (CAN-17).
*Эффект:* счётчик снова single source of truth.

**R4 — [MEDIUM***REMOVED*** Автоматизировать сверку счётчиков (consistency_check `check_test_counter`).**
*Evidence:* счётчик расходится вручную (2181→2694 без записи). В `scripts_01/consistency_check.py` уже есть `check_test_counter` (CODE_QUALITY_STANDARD:781).
*Рекомендация:* расширить проверку на свежесть (последняя запись ≥ дата последнего релиза), добавить тест.
*Эффект:* дрейф счётчиков ловится автоматически, не вручную.

### B. Реестры документов

**R5 — [CRITICAL***REMOVED*** Закрыть разрыв DOCUMENT_REGISTRY: 164 md на диске вне реестра.**
*Evidence:* `find docs_10 -name '*.md'` = 181; уникальных путей в DOCUMENT_REGISTRY = 18; `comm -13` = 164 вне реестра (1 из них — сам DOCUMENT_REGISTRY.md, self-reference). Вне реестра: audits/ (22 файла), core/ (многие), engineering-memory/ (41 на диске, 18 в реестре), vision/, decisions/, runbook/ и др.
*Рекомендация:* инвентаризация по каталогам; каждый ACTIVE/ARCHIVE документ — запись + bump-трейл по конвенции. Одноразовая операция (промт-сессия), затем поддерживать автоматически.
*Эффект:* реестр снова отражает реальность; consistency_check может валидировать полноту.

**R6 — [HIGH***REMOVED*** Валидировать полноту реестра в consistency_check.**
*Evidence:* реестр покрывает 18/181 — проверка полноты отсутствует (TOTAL 0 при неполном реестре).
*Рекомендация:* добавить rule «каждый .md в docs_10/engineering-memory и docs_10/core — в реестре (ACTIVE|ARCHIVE|LEGACY)»; исключения — INDEX/реестр-файлы.
*Эффект:* реестр перестаёт расходиться.

**R7 — [MEDIUM***REMOVED*** Разделить «реестровые» и «архивные» аудиты в реестре.**
*Evidence:* docs_10/audits/ — 22 файла, почти все вне реестра (исторические AUDIT_*).
*Рекомендация:* пометить исторические аудиты ARCHIVE одним блоком (не 22 отдельными bump), зарегистрировать активные.
*Эффект:* история сохранена (CAN-17), реестр чистый.

### C. Ссылки и naming

**R8 — [HIGH***REMOVED*** Починить битые ссылки в DRIFT_REPORT.md.**
*Evidence:* DRIFT_REPORT.md содержит: `pompts_11/promt48.md` (файл = `048_11_platform_rewrite_directive.md`), `prompts_11/promt47.md` (опечатка каталога, реально `pompts_11/`), `tmp/interior_planner_e2e/...` (tmp/ отсутствует), `scripts_01/interior_consultant_register.py`, `scripts_01/e2e_promt47.py` (нужно проверить существование), ADR_012 → `pompts_11/promt48.md`.
*Рекомендация:* перегенерировать DRIFT_REPORT (drift_check), исправить или перевести битые ссылки в «historical, файл удалён».
*Эффект:* отчёт перестаёт показывать ложный дрейф.

**R9 — [HIGH***REMOVED*** Унифицировать naming промтов: `promt` vs `pompts`, `0NN_XX` vs `promtNN`.**
*Evidence:* каталог `pompts_11/` (pompts), но внутри ссылки `promt48.md`, `promt70.md.bak`, `promt47.md`; конвенция `NNN_XX_*.md` (048_11_platform_rewrite_directive.md) нарушается в ссылках.
*Рекомендация:* канонический формат `pompts_11/NNN_XX_slug.md`; ссылки вести только на реальные файлы; `.bak` удалить/архивировать.
*Эффект:* нет двух правописаний одного каталога.

**R10 — [WONTFIX***REMOVED*** [MEDIUM→DONE***REMOVED*** Привести ADR-имена к единому формату — Superseded by CON-59.**
*Решение 2026-08-12 (R8 fix):* **CON-59** (см. `core_02/LESSONS.md`) установил канон: **`ADR_NNN_*.md` (underscore)** как единственно правильный формат. Рекомендация R10 выбрать `ADR-NNN_*.md` (hyphen) **отменена**. Текущее состояние:
*Evidence:* `docs_10/engineering-memory/decisions/`: `ADR_001_Vision...` (underscore) и `ADR_012_buffy...`; BUFFY.md и ADR_012_buffy_swappable_brain.md теперь соглашаются на underscore (R8 fix "BUFFY.md:21 ADR-012→ADR_012" + cite в LESSONS CON-59).
*Effect:* ADR-ссылки перестали биться (R8 fix v5.187.5), канон зафиксирован в CON-59, миграция historical hyphen-ссылок не требуется — их не было.

### D. Код

**R11 — [MEDIUM***REMOVED*** Убрать/залогировать print-отладку в core_02 (8 файлов).**
*Evidence:* `grep -rln 'print(' core_02/*.py` = 8 файлов; в scripts_01 — 44 упоминания. Пример: scripts_01/buffy_autodoc.py:179.
*Рекомендация:* перевести отладочный вывод на `logging`/`DEBUG/QUIET` (стандарт CODE_QUALITY_STANDARD UX), print оставить только в CLI-точках входа.
*Эффект:* предсказуемый stdout, пригодный для JSON-интерфейсов.

**R12 — [MEDIUM***REMOVED*** Инвентаризировать TODO/FIXME/XXX (5 в коде).**
*Evidence:* core_02/blueprint_v3.py:516 (auto-stub TODO), scripts_01/orchestrator.py:431 (TODO-команда), mcp_server.py:1870 (TODO-текст) и др.
*Рекомендация:* каждому TODO — issue/промт или явный статус (wontfix с обоснованием); завести трекинг в missing_registry (kind=tool/module).
*Эффект:* незакрытые долги видны, не теряются.

**R13 — [LOW***REMOVED*** mypy для core_02/scripts_01 в CI-проверке.**
*Evidence:* протокол AGENTS.md §6 требует `mypy scripts_01/ core_02/`, но в run_checks не подтверждён как обязательный гейт.
*Рекомендация:* добавить mypy-гейт в `run_checks.py` / pre-commit.
*Эффект:* типобезопасность — автоматический барьер.

### E. Структура каталогов

**R14 — [HIGH***REMOVED*** Разрешить дубль плагинов `freebuff_plugin/` vs `freebuff_plugin_03/`.**
*Evidence:* на диске оба каталога; `freebuff_plugin/` содержит только `monitor.sh`, `freebuff_plugin_03/` — полный плагин (12 py). Оба в git.
*Рекомендация:* подтвердить, какой каноничен (03), `freebuff_plugin/` — LEGACY → ARCHIVE/удалить из git, ссылки обновить.
*Эффект:* один источник плагина.

**R15 — [HIGH***REMOVED*** Прибрать корень: служебные файлы в каталоги.**
*Evidence:* в корне: `SESSION_UNDERSTANDING_2026-08-02.md`, `steps.md`, `status_report_20260801_205122.txt`, `promt70.md.bak`, `qwen-table-1785806850126.csv`, `verify_archive.sh`, `setup_canonical.sh`, `generate_project_dump.sh`, `promts_59_67_complete_work_*.sha256`.
*Рекомендация:* служебное → `docs_10/history/` / `scripts_01/` / `.archive/`; корень — только канонические манифесты (AGENTS/BUFFY/README/CHANGELOG/TASK/SPEC/PLATFORM).
*Эффект:* корень = точка входа, не склад.

**R16 — [MEDIUM***REMOVED*** Удалить/архивировать пустой `books_out/`.**
*Evidence:* `ls books_out/` пуст; каталог в git (untracked).
*Рекомендация:* удалить или добавить .gitkeep с README; не держать пустые каталоги.
*Эффект:* чистая структура.

**R17 — [MEDIUM***REMOVED*** Легализовать `prototype_22/` (ренейм `prototype/`).**
*Evidence:* ранее `prototype/` переименован в `prototype_22/`; forge_api.py mount указывает на `prototype/` и использует PROTOTYPE_DIR guard. На диске — только `prototype_22/`.
*Рекомендация:* зафиксировать каноническое имя (prototype_22) в forge_api.py + доке, убрать fallback-двусмысленность.
*Эффект:* код и диск совпадают.

### F. Register-first бэклог

**R18 — [HIGH***REMOVED*** Закрыть бэклог missing_registry: 7 из 9 записей не `implemented`.**
*Evidence:* `missing_registry list`: implemented = lisa_estimator, research_web; остальные: conformance_checker (registered), decision_registry (registered), factory_registry (design_ready), model_diagram_autogen (registered), opportunity_engine (prompt_written), scenario_engine (design_ready), whim_capture (registered).
*Рекомендация:* по каждой записи — следующее действие (промт → реализация → mark-implemented) по плану ФАЗ 1–3 (RECONCILIATION); конformance/decision_registry/model_diagram_autogen — написать промты.
*Эффект:* реестр отражает реальный прогресс, не висит.

**R19 — [HIGH***REMOVED*** Исправить рассинхрон factory_registry (промт есть, статус design_ready).**
*Evidence:* промт `pompts_11/078_19_factory_registry.md` на диске; в реестре `factory_registry` = design_ready (не prompt_written) — O1 RECONCILIATION.
*Рекомендация:* `python -m core_02.missing_registry mark-prompt-written factory_registry --prompt pompts_11/078_19_factory_registry.md`.
*Эффект:* реестр догоняет диск.

**R20 — [MEDIUM***REMOVED*** Добавить `opportunities.yaml`/`whims.yaml` схему в reестр до реализации Фазы 1.**
*Evidence:* opportunity_engine (prompt_written), whim_capture (registered) — данные-схемы (data_13/opportunities.yaml, whims.yaml) ещё не специфицированы в реестре.
*Рекомендация:* при реализации по контракту §E зарегистрировать kind=engine + файл-манифест.
*Эффект:* персистентность CI-слоя продумана до кода.

### G. Процессы и git

**R21 — [HIGH***REMOVED*** Уменьшить незакоммиченный объём (281 файл в git status).**
*Evidence:* `git status --short` = 281; много modified + untracked (реестры, доки, новое ядро core_02).
*Рекомендация:* регулярные осмысленные коммиты (по release-вехам); untracked разделить на «в проект» и «не в проект» (.gitignore).
*Эффект:* история воспроизводима, recovery не зависит от рабочей директории.

**R22 — [MEDIUM***REMOVED*** Разделить .gitignore: сгенерированное vs артефакты.**
*Evidence:* в корне служебные файлы (sha256, CSV, .bak) трекаются/видны в status.
*Рекомендация:* добавить паттерны для *.bak, *.sha256, временных отчётов, books_out/.
*Эффект:* status показывает только осмысленные изменения.

**R23 — [MEDIUM***REMOVED*** Возродить drift_check как регулярный гейт.**
*Evidence:* DRIFT_REPORT.md существует и содержит битые ссылки — проверка либо не гоняется, либо не блокирует.
*Рекомендация:* drift_check в run_checks + pre-commit; битые ссылки — fail.
*Эффект:* ссылки всегда валидны.

**R24 — [LOW***REMOVED*** Устранить mixed-language в CODE_QUALITY_STANDARD.**
*Evidence:* раздел «cited test counters» на украинском («Ціль цього розділу», «Правило оновлення») внутри русскоязычного документа.
*Рекомендация:* привести к одному языку (RU/EN), сохранив смысл; CAN-17 не трогать историю — только пояснительную часть.
*Эффект:* единый стиль доков.

**R25 — [LOW***REMOVED*** Ввести CHANGELOG-entry для каждого релиза с обязательным bump реестра.**
*Evidence:* DOCUMENT_REGISTRY bump-трейл ведётся вручную и расходится (18/181); CHANGELOG v5.187.3 без следов реестрового bump.
*Рекомендация:* чек-лист release: CHANGELOG entry → test counter → DOCUMENT_REGISTRY bump → consistency_check; автоматизировать в run_checks.
*Эффект:* релиз = атомарная согласованная операция.

---

## 3. Приоритеты

| Приоритет | Рекомендации | Сумма |
|-----------|--------------|-------|
| 🔴 CRITICAL | R1, R5 | 2 |
| 🟠 HIGH | R2, R3, R6, R8, R9, R14, R15, R18, R19, R21 | 10 |
| 🟡 MEDIUM | R4, R7, R10, R11, R12, R16, R17, R20, R22, R23 | 10 |
| 🟢 LOW | R13, R24, R25 | 3 |

**Быстрый старт (первые 5):** R1 (версия TASK), R3 (счётчик тестов), R5 (реестр доков), R19 (mark-prompt-written factory_registry), R8 (битые ссылки).

---

## 4. Методология и evidence

- Структура: `ls`, `find` по core_02/scripts_01/tests_09/docs_10/pompts_11/runtime_05/projects_17.
- Проверки: `python -c build_report` (TOTAL 0 CONSISTENT True), `pytest --collect-only` (2694), `missing_registry check/list` (9 записей), `grep` (TODO/print/дубли/версии), `git status` (281).
- Реестр vs диск: `grep -o 'docs_10/...' DOCUMENT_REGISTRY.md | sort -u` (18) vs `find docs_10 -name '*.md'` (181).
- Дрейф ссылок: содержимое `docs_10/DRIFT_REPORT.md` (битые пути promt48/prompts_11/tmp/ADR-012).
- Ограничения: полный pytest-прогон (2694 теста) не выполнялся в этой сессии (время ~15 мин); проверены collect-only + точечные тесты. R-позиции — рекомендации, не факты дефектов.

---

## 5. Связные документы

- `docs_10/DOCUMENT_REGISTRY.md` — реестр документов (R5–R7);
- `docs_10/core/CODE_QUALITY_STANDARD.md` — test counters, UX-стандарт (R3, R4, R11, R24);
- `docs_10/core/PROJECT_RULES.md` — канон ведения проектов (R21, R25);
- `core_02/missing_registry.py` + `data_13/missing_registry.yaml` — register-first (R18–R20);
- `docs_10/engineering-memory/INTELLIGENCE_FACTORY_CONTRACT_RECONCILIATION_V1.md` — план Фаз 1–3 (R18–R20);
- `AGENTS.md` §5/§6 — register-first, протокол сессии (R12, R13, R23).

---

*Аудит выполнен 2026-08-12 (read-only). Платформа архитектурно согласована; рекомендации направлены на гигиену реестров, версий, ссылок и процессов. Реализация — по register-first, аддитивно, без переписывания истории (CAN-16/CAN-17).*
