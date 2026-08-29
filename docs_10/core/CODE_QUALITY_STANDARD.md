# CODE QUALITY STANDARD — Buffy AI Infrastructure Layer

> **Версия:** 2.0.0
> **Дата:** 2026-07-29
> **Статус:** Mandatory — применяется ко всем компонентам проекта
> **Основание:** [pompts_11/CODE_QUALITY_STANDARD.md***REMOVED***(../../pompts_11/040_13_code_quality_standard.md) (v1.0), [016_02_arhitektura_reorganizaciya.md***REMOVED***(../../pompts_11/016_02_arhitektura_reorganizaciya.md)
> **Область действия:** `scripts_01/`, `freebuff_plugin_03/`, `projects_17/`, `runtime_05/`, `cli_07/`

---

## Золотое правило

> **Любой созданный код считается production-ready.**
>
> Если есть выбор между коротким и надёжным решением — всегда выбирать надёжное.
>
> Код должен быть безопасным, повторяемым, расширяемым, документированным
> и готовым к использованию без ручных исправлений.

---

## 1. Архитектура

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 1.1 | Модульность — каждый модуль выполняет одну основную задачу (Single Responsibility) | Core / Extensions / Labs жёсткое разделение |
| 1.2 | Минимальная связанность между модулями | Core↔Plugin через `__init__.py` + `bridge.py` ([INTEGRATION_CONTRACT.md***REMOVED***(../../freebuff_plugin_03/INTEGRATION_CONTRACT.md)) |
| 1.3 | Понятная структура каталогов | См. [ARCHITECTURE_PRINCIPLES.md***REMOVED***(ARCHITECTURE_PRINCIPLES.md) |
| 1.4 | Нет дублирования кода (DRY) | Shared helpers через `freebuff_plugin_03/bridge.py` |
| 1.5 | Нет «магических» чисел и строк | Константы в `freebuff_plugin_03/config.py`, `__init__.py` модулей |
| 1.6 | Loosely coupled — компоненты общаются через EventBus | Publish/subscribe, без прямых вызовов ([EVENT_PLATFORM_SPECIFICATION.md***REMOVED***(EVENT_PLATFORM_SPECIFICATION.md)) |
| 1.7 | Infrastructure Plugin — Buffy расширяет Runtime, не заменяет их | Runtime → Adapter → MCP/ACP ([RUNTIME_ABSTRACTION_SPECIFICATION.md***REMOVED***(RUNTIME_ABSTRACTION_SPECIFICATION.md)) |

---

## 2. Читаемость

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 2.1 | Комментарии на русском (docstrings) | Docstrings в стиле Google: описание, Args, Returns, Raises |
| 2.2 | Понятные имена функций и переменных | `_get_bridge_layer()` а не `_gbl()`, `event_bus` а не `eb` |
| 2.3 | Описание каждого модуля (module docstring) | Назначение, использование, пример |
| 2.4 | README или инструкция запуска | Каждый проект/модуль имеет README.md |
| 2.5 | Единый стиль оформления | `from __future__ import annotations`, type hints, snake_case |
| 2.6 | Type hints для всех публичных функций | `def generate(prompt: str, max_tokens: int | None = None) -> str:` |

---

## 3. Надёжность

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 3.1 | Обработка ошибок (try/except) | `try/except ImportError` для Graceful Degradation |
| 3.2 | Логирование действий | EventBus `publish()` для всех значимых операций |
| 3.3 | Корректное завершение при ошибках | Ядро не падает при отсутствии плагина |
| 3.4 | Не оставлять повреждённые файлы | Атомарные операции записи |
| 3.5 | Проверка существования файлов/директорий | `Path.exists()` перед чтением, `mkdir(parents=True)` перед записью |
| 3.6 | Проверка прав доступа | `os.access(path, os.R_OK)` |
| 3.7 | Идемпотентность — повторный запуск не ломает систему | Bootstrap Engine: `install_missing()` не переустанавливает существующее |
| 3.8 | Восстановление после сбоя | OOM Protection, авто-reconnect в Bridge Layer, чекпоинты сессий |
| 3.9 | Graceful Degradation — отсутствие компонента не ломает ядро | `try/except ImportError` для плагина, `return None` для недоступных сервисов |

---

## 4. Безопасность

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 4.1 | Не использовать root | Termux без дополнительных привилегий |
| 4.2 | Не хранить пароли/токены/ключи в коде | `.env` для секретов, `.keys/` для KeyPool |
| 4.3 | Использовать переменные окружения для секретов | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc. из `.env` |
| 4.4 | Валидировать входные данные | JSON Schema в MCP tools, проверка типов в API |
| 4.5 | Не выполнять произвольные shell-команды без проверки | `shlex.quote()` для аргументов, whitelist команд |
| 4.6 | Экранировать пользовательский ввод | `html.escape()`, `json.dumps()` для вывода |
| 4.7 | Никаких хардкодженных путей | Все пути параметризованы (через `__init__`, env, config) |
| 4.8 | Интеграция только через публичные API | CLI → MCP → ACP → API. Нет внутренних/недокументированных API |

---

## 5. Совместимость

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 5.1 | Совместимость с Termux | `IS_TERMUX` проверки, `pkg` вместо `apt` |
| 5.2 | Работа на Android (ARM64) | Нет x86-specific бинарников, ARM64 сборки |
| 5.3 | POSIX-совместимые команды | Bash-скрипты: `#!/bin/bash` с POSIX-подмножеством |
| 5.4 | Избегать платформозависимого поведения | `pathlib.Path` вместо строковых путей, `shutil.which()` вместо `which` |
| 5.5 | Проверка наличия утилит перед запуском | `doctor.py --check-runtime` проверяет git, python, node |
| 5.6 | Python 3.11+ | `from __future__ import annotations`, `X | None` синтаксис |

---

## 6. Производительность

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 6.1 | Минимизировать RAM | Lazy imports (`__getattr__`), генераторы, SQLite вместо in-memory |
| 6.2 | Минимизировать обращения к диску | Кэширование через MemoryEngine, `functools.lru_cache` |
| 6.3 | Избегать лишних процессов | OOM Protection убивает старые процессы, daemon threads |
| 6.4 | Кэширование | `ModelGateway._cache`, `KnowledgeEngine` индекс, `functools.lru_cache` |
| 6.5 | Не выполнять тяжёлые операции повторно | Seed check: `_already_seeded()` по content_hash |
| 6.6 | Lazy loading — загружать только когда нужно | `__getattr__` в `freebuff_plugin_03/__init__.py`, ленивые accessor'ы в `mcp_server.py` |

---

## 7. Логирование

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 7.1 | Логировать начало работы | `Event(type="bootstrap.started", ...)` |
| 7.2 | Логировать завершение | `Event(type="session.ended", ...)` |
| 7.3 | Логировать ошибки | `Event(type="*.error", ...)` через EventBus |
| 7.4 | Логировать предупреждения | `print("⚠ ...", file=sys.stderr)` + EventBus |
| 7.5 | Режим DEBUG | `DEBUG=1` env var, детальный вывод |
| 7.6 | Режим QUIET | `QUIET=1` env var, только ошибки |
| 7.7 | EventBus — все значимые действия публикуются | `mcp.tool.called`, `bootstrap.ran`, `runtime.connected`, etc. |
| 7.8 | Structured logging | Event Store (SQLite + FTS5) + JSON формат |

---

## 8. Конфигурация

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 8.1 | Настройки в конфигурационном файле | `.freebuff/config.json`, `bootstrap/profiles.yaml` |
| 8.2 | Значения по умолчанию | `DEFAULT_DOC_SOURCES`, `DEFAULT_PROFILES_PATH`, `DEFAULT_RUNTIMES` |
| 8.3 | Документировать параметры | `--help` для CLI, docstrings для классов |
| 8.4 | Не изменять конфиг автоматически без разрешения | `BootstrapProfile.auto_update = False` по умолчанию |

---

## 9. UX

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 9.1 | Понятный прогресс | Health score в doctor.py, progress bar в seed |
| 9.2 | Дружелюбные сообщения об ошибках | `"⚠ RuntimeRegistry unavailable (plugin not loaded): {e***REMOVED***"` |
| 9.3 | Не засорять терминал | QUIET режим, `contextlib.redirect_stdout` в bridge.py |
| 9.4 | `--help` | Все CLI-скрипты: argparse с epilog и примерами |
| 9.5 | `--version` | Все CLI-скрипты: `--version` выводит версию |
| 9.6 | Корректные exit-коды | 0 = OK, 1 = ошибка, 2 = критические предупреждения |

---

## 10. Документация

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 10.1 | Инструкция установки | RECIPE.md для каждого Runtime ([runtime_05/recipes/***REMOVED***(../../runtime_05/recipes/)) |
| 10.2 | Инструкция запуска | `python scripts_01/mcp_server.py --http`, `python scripts_01/doctor.py` |
| 10.3 | Примеры использования | Docstrings с примерами, `--help` с `epilog` |
| 10.4 | Описание параметров CLI | argparse: `help=`, `choices=`, `default=` |
| 10.5 | Описание структуры проекта | [INDEX.md***REMOVED***(../INDEX.md), [PROJECT_REGISTRY.md***REMOVED***(PROJECT_REGISTRY.md) |
| 10.6 | Список зависимостей | `requirements.txt` с версиями |
| 10.7 | CHANGELOG.md — все изменения документируются | Каждый релиз: Added/Changed/Fixed/Removed |
| 10.8 | ADR для архитектурных решений | [decisions/DECISIONS.md***REMOVED***(../decisions/DECISIONS.md) (индекс), [engineering-memory/decisions/***REMOVED***(../engineering-memory/decisions/) (ADR) |

---

## 11. Тестируемость

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 11.1 | Легко тестироваться | `pytest tests_09/ -q`, dependency injection (EventBus, workspace_root) |
| 11.2 | Тестовые сценарии | Каждый модуль: unit + integration + boundary tests |
| 11.3 | Примеры входных данных | `tmp_path` фикстуры, `conftest.py` с shared fixtures |
| 11.4 | Ожидаемый результат | `assert result["success"***REMOVED*** is True`, `assert count > 0` |
| 11.5 | Boundary Testing | Тесты для всех интерфейсов (Core↔Plugin, MCP, REST) |
| 11.6 | Регрессионные тесты | Полный прогон перед каждым merge (**цель: 3527+ passed, 0 failures**); full-suite real count = 3527 (AST truth 2026-08-29; +83 vs v5.189.64 baseline 3444, +4 TestCacheLayer на pricing_enumerator + 30 PRD release-cycles); для traceability — см. §11.7 ниже |

---

### 11.7 Counter Milestone Reference — Audit Trail для §3.3 CAN-16 (v5.55.0)

Цель этого раздела: single source-of-truth для cited test counters. Все числа должны иметь file:line provenance — **никогда не выдуманные**. Обновлять при каждом release, который меняет counter (R24 fix: единый язык, R25 discipline).

| Date | Counter | Trigger | Provenance (file:line) |
| --- | --- | --- | --- |
| 2026-07-28 | 586 | v2.8.0 security hardening (exec/shell removal) | [CHANGELOG.md:2086***REMOVED***(../../CHANGELOG.md) |
| 2026-07-29 | 1124 | AUDIT_FULL pre-merge (Stage-8) | [docs_10/audits/AUDIT_FULL_2026-07-29.md:386***REMOVED***(../audits/AUDIT_FULL_2026-07-29.md) |
| 2026-08-01 | 1671 | Stage 9 consolidation + engine recovery | [TASK.md:114***REMOVED***(../../TASK.md) |
| 2026-08-02 | 1891 | drift_check + consistency_check regression | [DAY_SUMMARY_2026-08-02.md:142***REMOVED***(../../docs_10/history/DAY_SUMMARY_2026-08-02.md) |
| 2026-08-02 | 1991 | NIT-3 + negative-tests (v5.39.3) | [CHANGELOG.md v5.39.3 entry***REMOVED***(../../CHANGELOG.md) — anchor |
| 2026-08-04 | 2181 | consistency_check `check_test_counter` alignment — drift closure (1991→2181 `#` shadow tests across v5.50–v5.81 era) | [consistency_check.py:781***REMOVED***(../../scripts_01/consistency_check.py) — drift closure | **current-state goal bumped to 2181+** (not historical rewrite per CAN-17) |
| 2026-08-12 | 2694 | Platform audit batch — CI-slice + forensics + audits + factory/forge expansions (R3 fix) | `pytest tests_09/ --collect-only` → 2694 tests collected in 18.75s | **current-state goal bumped to 2694+** (R25 discipline applied; R4 auto-freshness rule added) |
| 2026-08-18 | 3072 | test_counter drift closure (CHANGELOG anchor 2994 + §11.6 target 3040 → actual 3072) — ADR-016 RoleExecutor/LlmRoleExecutor + LISA calibration + glossary Phase 8-13 | `count_test_functions(tests_09/)` AST → 3072 | **current-state goal bumped to 3072+** (R25 discipline; drift closed without historical rewrite) |
| 2026-08-18 | 3079 | +7 new tests (SmartRouter availability cloud-first + ModelGateway failsafe) — v5.189.48 | `count_test_functions(tests_09/)` AST → 3079 | **current-state goal bumped to 3079+** (cloud-first routing ANTI-6b defense) |
| 2026-08-18 | 3089 | +10 new tests (backfill:bool machine-readable field + B10 invariants) — v5.189.49 | `count_test_functions(tests_09/)` AST → 3089 | **current-state goal bumped to 3089+** (backfill as data, not free-text marker) |
| 2026-08-19 | 3090 | +1 contract test for partial-chain project (smoke) + strict-14 filter + `self.`→module-level clean-up + class rename MockFlag→StageCount — v5.189.50; **full-suite pytest = 3107 passed, 0 failed, 1 xpassed** (tmux 905s); AST count=3090 (consistency_check baseline) | `count_test_functions(tests_09/)` AST → 3090 (+1 contract test) | **current-state AST goal bumped to 3090+ / full-suite goal to 3107+** (partial-chain contract explicit; 0 regression failures) |
| 2026-08-19 | 3096 | +6 `backfill_signature` tests (v5.189.51: retroactive-registration discipline check в `consistency_check.py`); NEW `check_backfill_signatures()` heuristic — `status=implemented AND registered_at==updated_at AND not backfill` → soft WARNING (NOT counted в `total_issues`, per user 'предупреждение' intent); SEED entries exempt via lazy `_SEED` import; standalone `backfill_signature` key в `build_report()` output | `count_test_functions(tests_09/)` AST → 3096 (+6 contract tests in `TestBackfillSignature` class) | **current-state AST goal bumped to 3096+ / full-suite pending tmux re-run (anchor 3107 from v5.189.50 baseline)** (retroactive-registration discipline surfaced; CON-63/64 traceability preserved; soft-signal semantic — 0 hard CI violations) |
| 2026-08-19 | 3104 | +8 тестов (v5.189.52: cross-provider cloud fallback + cloud-first tie-break — TestCrossProviderFallback 6 + TestPolicyRouting 3 cloud-first/negative/tied-score); `SmartRouter.route()` cloud-first tie-break (гейт по `provider_available`) + `_call_with_fallback` hard-error class switch (CON-65) | `count_test_functions(tests_09/)` AST → 3104 | **AST goal bumped to 3104+** (CON-65 ANTI-6b closure; cloud-first availability-aware) |

**Правило обновления:** когда release модифицирует counter — привязать bump к конкретной версии + trigger + файл-ссылка. **Правило анти-rewriting:** не изменять старые numbers ради consistency; audit trail должен выжить intact. CAN-16 closure — 2026-08-03 (v5.55.0) — doc-only patch без модификаций существующих references. R24 fix 2026-08-12: единый русский язык для пояснительной секции.

## 12. Масштабируемость

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 12.1 | Легко расширяться новыми модулями | Plugin API, Adapter Layer, Recipe система |
| 12.2 | Не требовать переписывания существующего кода | Evolution over Revolution, обратная совместимость |
| 12.3 | Поддерживать плагины/инструменты | `freebuff_plugin_03/`, `runtime_05/recipes/`, `runtime_05/adapters/` |
| 12.4 | Marketplace-ready | Добавление Runtime без изменения ядра ([ARCHITECTURE_PRINCIPLES.md***REMOVED***(ARCHITECTURE_PRINCIPLES.md) §2.3) |

---

## 13. Стандарты разработки

| # | Требование | Buffy-специфика |
|---|-----------|-----------------|
| 13.1 | KISS — Keep It Simple, Stupid | Минимум изменений для задачи |
| 13.2 | DRY — Don't Repeat Yourself | Shared helpers, bridge.py, __init__.py exports |
| 13.3 | SOLID (где применимо) | Single Responsibility: Core/Extensions/Labs, Open/Closed: Plugin API |
| 13.4 | Избегать преждевременной оптимизации | Не оптимизировать без измерений (cProfile, memory_profiler) |
| 13.5 | Код, понятный через год | Комментарии «почему», а не «что»; docstrings; ADR |
| 13.6 | Code review обязательно | Каждое изменение → `code-reviewer-deepseek` → исправления → merge |
| 13.7 | mypy type checking | `mypy --strict scripts_01/ freebuff_plugin_03/` (цель) |

---

## 14. Buffy-специфические требования

| # | Требование |
|---|-----------|
| 14.1 | **EventBus first** — все значимые операции публикуют событие |
| 14.2 | **Plugin-safe imports** — ядро импортирует плагин только через `freebuff_plugin_03/__init__.py` |
| 14.3 | **Bridge-only** — плагин импортирует ядро только через `freebuff_plugin_03/bridge.py` |
| 14.4 | **No hardcoded paths** — все пути параметризованы через env/config/параметры |
| 14.5 | **OOM aware** — длительные операции через subprocess (Python не ждёт) |
| 14.6 | **1143+ tests, 0 failures** — стандарт приёмки |
| 14.7 | **Android tested** — все новые функции проверяются на Termux/ARM64 |
| 14.8 | **Runtime validated** — поддержка Runtime заявляется только после практической проверки ([RUNTIME_VALIDATION_FRAMEWORK.md***REMOVED***(RUNTIME_VALIDATION_FRAMEWORK.md)) |

---

## Финальное правило

> Любой созданный код считается **production-ready**.
>
> Если есть выбор между коротким и надёжным решением — всегда выбирать надёжное.
>
> Код должен быть: **безопасным · повторяемым · расширяемым · документированным · готовым к использованию без ручных исправлений.**

---

*Связанные документы:*
- [ARCHITECTURE_PRINCIPLES.md***REMOVED***(ARCHITECTURE_PRINCIPLES.md) — архитектурные принципы
- [INTEGRATION_CONTRACT.md***REMOVED***(../../freebuff_plugin_03/INTEGRATION_CONTRACT.md) — граница ядро↔плагин
- [RUNTIME_VALIDATION_FRAMEWORK.md***REMOVED***(RUNTIME_VALIDATION_FRAMEWORK.md) — валидация Runtime
- [../vision/VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md) — стратегическое видение
- [INDEX.md***REMOVED***(../INDEX.md) — навигация по документации
