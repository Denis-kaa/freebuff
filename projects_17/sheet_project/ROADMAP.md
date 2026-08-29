# ROADMAP.md — Этапы

> **Дизайн-фаза (Blueprint v3 LIGHT-роли) — ЗАВЕРШЕНА** (2026-08-18):
> explainer → lisa → risk → decomposer → architect → auditor. Итог: `architecture.md` + `contracts.yaml` + `adr/ADR-002` + `consistency_report.md` (D1–D7 закрыты).
> Таблица ниже отслеживает только **реализацию кода** (дизайн уже есть, код не начат).
> **Аудит-замечания закрыты (2026-08-19):** H1 (якорение → `Anchor`) + H2 (DATA→sheet → `DataSource.source`) + G1–G5 (lifecycle / L1–L4 / generation_id+template_version / atomic publish / input snapshot). Архитектура = **READY**, код не начат.

| Этап | Название | Статус | Результат |
|------|----------|--------|-----------|
| 0 | Каркас проекта + план | 🟢 | MANIFEST/STEPS/decisions/README/RUNNABLE/CHECKLIST |
| 1 | Доменная модель конфигурации | ⚪ | config/schema.py |
| 2 | Разделение неизменяемое/изменяемое | ⚪ | контракты модулей |
| 3 | Структура проекта | ⚪ | папки generator/styles/validator/... |
| 4 | CONFIG первого шаблона | ⚪ | config/project_dashboard.py |
| 5 | Контракт DATA | ⚪ | data/models.py + sample_data.py |
| 6 | GENERATOR | ⚪ | generator/*.py |
| 7 | VALIDATOR | ⚪ | validator/validator.py |
| 8 | Эталонный XLSX | ⚪ | output/project_dashboard.xlsx |
| 9 | Архитектурный тест | ⚪ | тест изменения CONFIG без правки ядра |
| 10 | Финальная проверка | ⚪ | полный прогон + отчёт |

> Статусы: 🟢 готово · 🟡 в работе · ⚪ не начато · 🔴 блокировано

---

## Forge chain status (Blueprint v3) — прогон 2026-08-18

`python scripts_01/forge.py chain projects_17/sheet_project` (read-only, `project_read_only=True`).

**Overall: `partial`** · registry=`loaded` (локальная копия `blueprints_v3/registry.yaml` — fix 2026-08-18; ранее `missing`→`degraded`) · base_check=`ok`.

### LIGHT-роли планирования (check_only)

| Роль | Статус | Артефакты (нет) |
|------|--------|-----------------|
| explainer | ✅ ok | brief.md, parsed_requirements.md созданы |
| lisa | ✅ ok | lisa_report.md (LISA-3, COND — с калибровкой lisa_calibration.yaml) |
| risk | ✅ ok | risk_matrix.md (CONDITIONAL GO) |
| decomposer | ✅ ok | decomposition.md, module_list.md, integration_topology.md |
| architect | ✅ ok | architecture.md, adr/ADR-002.md, contracts.yaml созданы |
| auditor | ✅ ok | audit_report.md (READY WITH FIXES) |

→ Все 6 LIGHT-ролей планирования закрыты: explainer (brief.md + parsed_requirements.md) · lisa (lisa_report.md) · risk (risk_matrix.md) · decomposer (decomposition/module_list/integration_topology) · architect (architecture.md + contracts.yaml + adr/ADR-002) · auditor (audit_report.md). Калибровка `lisa_calibration.yaml` (XLSX-домен, `ai_suitability×7.0`) подняла вердикт NO-GO → COND; честная граница остаётся — openpyxl не считает формулы (calculation validation = отдельный слой LibreOffice), поэтому GO не заявлен. Аудитор вынес READY WITH FIXES: 2 High-недоопределённости контрактов (якорение формул/ссылок к диапазонам данных; привязка DATA→sheet) — закрыть в начале реализации. **→ (2026-08-19) оба High (H1+H2) и G1–G5 закрыты в `contracts.yaml`/`architecture.md` — архитектура READY (см. шапку).**

### HEAVY-роли (full_cycle) — pipeline прошёл, артефактов кода нет

| Роль | Статус | Примечание |
|------|--------|-----------|
| developer | run_ok | src/**/*.py, tests/**/*.py, migrations/*.py — пусто |
| devops | run_ok | Dockerfile, docker-compose.yml и т.д. — пусто |
| tester | run_ok | tests/**/*.py — пусто |
| fixer | run_ok | bug_fixes.md, regression_tests.py — пусто |
| acceptance | run_ok | acceptance_report.md, validation.md — пусто |
| frontend | skipped | project.type != "web" |

→ `run_ok` = статус ForgePipeline-стадий, НЕ существование кода: в read-only режиме Forge не создаёт код. Реальных артефактов кода ещё нет (код не начат).

### documenter / retrospective — partial

| Роль | Статус | Есть | Нет |
|------|--------|------|-----|
| documenter | partial | README.md | PORTFOLIO_CASE.md, TG_POST.md, API_DOCS.md, ARCHITECTURE.md |
| retrospective | partial | LESSONS.md | retrospective_report.md, lisa_calibration.yaml |

### Вывод

Покрыто: каркас проекта = этап 0 + ВСЕ 6 LIGHT-ролей планирования (explainer/lisa/risk/decomposer/architect/auditor). Пусто: весь код (HEAVY) + documenter/retrospective недобиты (частичные артефакты). Следующий шаг — этап 1 (доменная модель `config/schema.py`) по `contracts.yaml`. Аудит-замечания H1 + H2 + G1–G5 закрыты — архитектура READY.
