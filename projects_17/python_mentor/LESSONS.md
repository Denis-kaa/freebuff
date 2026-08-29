# LESSONS.md — Уроки проекта python_mentor

> Journal lessons (project-local). Формат: `CON-<n>` (подтверждено), `CAN-<n>` (гипотеза), `ANTI-<n>` (анти-паттерны), `PB-<n>` (процессный баг). Заполняется по ходу фаз, а не в конце.

## Уроки

- **CON-1 (2026-08-23, B+C):** структура репо exercism/python стабильна для парсинга (config.json + .docs + .meta) — parser работает без правок на 161 упражнении; фикстуры из реального репо (6 упражнений) воспроизводят её hermetic.
- **CON-2 (2026-08-23, B+C):** идемпотентность через content_hash (sha256 дерева) — N→N; change→update (тест подтвердил). Полезно для будущего change-detection upstream.
- **ANTI-1 (2026-08-23, B+C):** вставка FK-зависимых строк в порядке «списка» ломается, когда ссылки идут вперёд → синхронизация карты в БД двухфазная (сначала все узлы, потом рёбра). Аналогично для compiler-задач.
- **ANTI-2 (2026-08-23, B+C):** fixture-директории внутри tests/ собираются pytest как тесты → нужен conftest с collect_ignore (а не только norecursedirs).
- **CAN-1 (2026-08-23, отложено до Phase H):** «pedagogical_rung от difficulty» (1→repetition … 9→independent) — рабочая гипотеза, требует проверки реальным учеником (фаза N) — не факт.
- **PB-1 (2026-08-23, B+C):** при ручном написании длинных YAML-файлов появляются опечатки в ключах — решение: генерация через `tools/gen_competency_map.py` с валидацией схемы ДО записи файла; ключи в data-структурах контролируются программно.
- **CON-3 (2026-08-23, Phase D):** pytest/JUnit нормализация должна работать в child process с временным workspace; preflight синтаксиса тестов и student-кода позволяет отличить malformed exercise от student error, не выдавая ложный timeout.
- **ANTI-3 (2026-08-23, Phase D):** результат grader нельзя собирать только по exit code: одинаковый `returncode=1` означает и assertion failure, и collection/import error; contract обязан хранить counts и отдельный `failure_kind`.
- **CON-4 (2026-08-24, Phase E):** execution boundary должен принимать абсолютный interpreter path; sanitized `PATH` может быть минимальным и не содержать `python3`, поэтому команда через имя бинарника ломает корректный backend start.
- **CON-5 (2026-08-24, Phase E):** `RLIMIT_AS` применим как backend policy, но в Termux/proot его нельзя безусловно включать вокруг pytest bootstrap: даже 1 GiB вызывает ложные timeout; grader использует CPU/wall-clock/output limits, direct jobs проверяют AS отдельно.
- **ANTI-4 (2026-08-24, Phase E):** `ExecutionStatus.OUTPUT_LIMIT` нельзя определять только после завершения процесса — writer может продолжать печать; backend должен poll-ить размер файла и завершать process group при превышении.
- **CON-6 (2026-08-24, Phase E):** CPU exhaustion нужно нормализовать отдельно от wall-clock timeout (`RESOURCE_ERROR`/`cpu_limit`), иначе инфраструктурный лимит ошибочно выглядит как зависший student process.
- **CON-7 (2026-08-24, Phase F):** Pylint возвращает bitmask exit code, а не простой `0/1`; adapter принимает валидный JSON при кодах `0..31`, иначе корректные diagnostics ошибочно классифицируются как tool failure.
- **CON-8 (2026-08-24, Phase F):** bootstrap Pylint/Flake8 в Termux может превышать 10 секунд даже на малом файле; внешний sensor timeout должен быть configurable и default 60s, а timeout не смешивается с malformed output.
- **ANTI-5 (2026-08-24, Phase F):** Radon metrics нельзя парсить «по памяти»: Halstead лежит под `total`, MI имеет отдельную shape; parser tests должны фиксировать реальные JSON-форматы версии инструмента.
- **CON-9 (2026-08-24, localization):** English upstream и translated locale должны быть отдельными projections; source hash обязателен, иначе upstream refresh тихо оставляет устаревший перевод.
- **ANTI-6 (2026-08-24, localization):** LLM нельзя давать прямое право записи в live corpus: только `TranslationDraft` → structural/hash validation → reviewed publication; provider absence должен fail-closed без изменения данных.
- **CON-10 (2026-08-24, localization):** резервный LLM pool должен ротироваться только после retryable API failures; успешный ответ фиксирует текущий slot, а credential values не должны появляться в repr, logs или reports.
- **ANTI-7 (2026-08-24, localization):** batch translation без лимита опасен: даже рабочий provider может вызвать большой сетевой расход; CLI default — один draft, полный batch только через явный `--limit`.

## Связанные заметки

- Если урок окажется тиражируемым (применим ко всем проектам платформы) — продублировать/связать в `core_02/LESSONS.md` (правило «в одну сторону» PROJECT_RULES §2.3).