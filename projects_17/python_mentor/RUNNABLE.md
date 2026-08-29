# RUNNABLE.md — Запуск и ограничения (python_mentor)

> **Статус:** 🟢 Phase F выполнена (2026-08-24) — G-BC/G-D/G-E/G-F пройдены. Дальше — Phase G.

## Текущее состояние

- ✅ Каркас + Phase B+C: `app/` (curriculum, ingestion, storage), corpus 161 упражнения.
- ✅ CLI: `python3 -m app ingest|report`.
- ✅ Phase D: `app/grading/` — immutable contract, approved-corpus adapter, isolated pytest runner.
- ✅ Phase E: `app/execution/` — replaceable subprocess backend, timeout, CPU/output limits, direct-job address-space policy, process-group cleanup, sanitized environment.
- ✅ Phase F: `app/diagnostics/` — 7 deterministic AST rules, normalized sensors, Pylint/Radon/Flake8/Bandit adapters, diagnostic-only boundary.
- ✅ Тесты: 91 passed, 2 integration skipped by default (hermetic, без сети).

## Окружение (факты от 2026-08-23)

| Требование | Статус | Как проверить |
|---|---|---|
| Python 3.14.6 | ✅ | `python3 --version` |
| pytest 9.1.1 | ✅ | `python3 -m pytest --version` |
| SQLite 3.53.4 (stdlib) | ✅ | `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"` |
| pip 26.2.1 + PyPI | ✅ | `python3 -m pip index versions fsrs` |
| RLIMIT (CPU/AS) | ✅ понижение работает | `python3 -c "***REMOVED***source; resource.setrlimit(resource.RLIMIT_AS,(268435456,1073741824)); print('ok')"` |
| user namespaces (`unshare --user`) | ⚠️ НЕ подтверждено (proot-окружение; вывод 0 не значит изоляцию; сеть внутри `unshare --net` не изолируется) | `unshare --user --net sh -c 'cat /proc/net/route'` + сравнение интерфейсов |
| pylint / radon / flake8 / bandit | ✅ установлены: pylint 4.0.7, radon 6.0.1, flake8 7.3.0, bandit 1.9.4 | `pylint --version && radon --version` |
| fsrs-библиотека | ✅ установлена `fsrs 6.3.2` (единственный кандидат PyPI) | `python3 -c "import fsrs; print('ok')"` |
| FastAPI | ⏳ не проверено (Phase L) | `python3 -c "import fastapi"` |
| PyYAML | ✅ 6.0.3 (для конфигов B+C и FSRS_NOTE) | `python3 -c "import yaml; print(yaml.__version__)"` |
| Интернет | ✅ есть (для ingestion в B+; runtime ядра — офлайн) | — |

## Команды (Phase B+C, D, E и F)

```bash
# Сюит:
python3 -m pytest tests/ -q                     # 78 passed, 2 integration skipped (hermetic, без сети)
python3 -m pytest tests/ -q -m integration      # 2 canary на реальном клоне
python3 -m mypy app/ --ignore-missing-imports   # 0 errors
python3 -m pytest tests/unit/test_grading.py -q # Phase D contract/runner
python3 -m pytest tests/unit/test_execution.py -q # Phase E execution/resource limits
python3 -m pytest tests/unit/test_diagnostics.py -q # Phase F AST/adapters/normalization

# Phase B+C CLI:
python3 -m app ingest exercism --dry-run          # счётчики без записи
python3 -m app ingest exercism                    # идемпотентный импорт в data/corpus/corpus_v0.1.db
python3 -m app ingest exercism --with-refs        # + reference solutions
python3 -m app report coverage | gaps | low-confidence | license
python3 -m app localize scan --source data/exercism_src --manifest data/localization/source_manifest.json --target-locale ru
python3 -m app localize status --source data/exercism_src --target data/localization/ru
python3 -m app localize update --provider external_llm  # fail-closed boundary
python3 -m app localize update --provider gemini --limit 1  # local 3-key rotation; draft-only
```

## Ограничения (обязательные)

- **Не сервис в публичный доступ** (MVP-tier sandbox, localhost-only) — blueprint §0.
- **LLM-call = 0** в ядре — любой внешний вызов нарушает инвариант детерминизма.
- Сеть допускается только в CLI-инструменте ingestion для получения официального Exercism source; после импорта runtime офлайн (prompt1 §30).
- Content policy: локальное хранение контента только для approved-источников; иначе — ссылки (prompt1 §15).
- Sandbox: `mvp_untrusted_single_user`; без обещаний network isolation и production-безопасности. `RLIMIT_AS` проверен на прямом backend job, но не включён для pytest bootstrap в proot.
- Diagnostics: Pylint/Radon/Flake8/Bandit — внешние sensors; default adapter timeout 60s учитывает Termux bootstrap. MI, counts и severity никогда не являются evidence.
- Localization: English upstream canonical; `ru` projection versioned by source hash; Gemini uses the ignored `.keys/gemini_active.keys` pool with failover and creates drafts only; reviewed publication is required. Code/tests/reference solutions are not translated.

## Популярные операции

| Хочу | Команда |
|---|---|
| Прочитать роадмап фаз | `open ROADMAP.md` |
| Проверить Phase D | `python3 -m pytest tests/unit/test_grading.py -q`; детали — `docs/grading_v0.1.md` |
| Проверить Phase E | `python3 -m pytest tests/unit/test_execution.py -q`; детали — `docs/execution_v0.1.md` |
| Проверить Phase F | `python3 -m pytest tests/unit/test_diagnostics.py -q`; детали — `docs/diagnostics_v0.1.md` |
| Зарегистрировать решение | Новый файл `decisions/ADR-NNN_*.md` + запись в `DECISIONS.md` |
| Зафиксировать урок | Запись в `LESSONS.md` (CON/CAN/ANTI/PB) |