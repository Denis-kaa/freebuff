# ADR-005 — RLIMIT_AS в Termux/proot и граница MVP execution / hardened sandbox

> **Статус:** Accepted (2026-08-24)
> **Область:** Phase E execution runtime
> **Связанные решения:** [ADR-003***REMOVED***(ADR-003_sandbox_two_tiers_single_interface.md)
> **Источники:** `prompt2.md` Phase E · `python_ai_tutor_blueprint_v0.1.md` §0/§9

## Context

Phase E должна ограничивать выполнение student code, но текущий runtime работает в Termux на Android внутри proot-distro. В такой среде `resource.setrlimit()` доступен, однако `RLIMIT_AS` ограничивает виртуальное адресное пространство процесса, включая bootstrap самого Python/pytest и унаследованные proot-структуры. Поэтому числовой лимит, который выглядит умеренным на обычном Linux, может преждевременно завершить корректный pytest child process.

Наблюдение воспроизводимо в текущем окружении: включение `RLIMIT_AS` вокруг pytest grader вызывало ложный `TIMEOUT` даже при лимите 1 GiB. При этом прямой execution job может применить address-space policy и проверить факт её установки на пороге, совместимом с данным runtime. Это различие нельзя скрывать за общим названием «sandbox».

## Decision

1. `RLIMIT_AS` остаётся частью общего `ExecutionPolicy` и поддерживается `TermuxSubprocessBackend` как **опциональная policy для прямых execution jobs**.
2. `PytestGrader` в `mvp_untrusted_single_user` **не включает `RLIMIT_AS` вокруг pytest bootstrap** в Termux/proot. Для grader применяются wall-clock timeout, process-group cleanup, bounded output и `RLIMIT_CPU`.
3. Такое выполнение классифицируется только как локальный MVP execution boundary. Оно **не является hardened sandbox** и не обещает:
   - изоляцию сети;
   - изоляцию произвольной файловой системы от текущего пользователя;
   - user switching, namespaces, seccomp, Docker или nsjail;
   - безопасное публичное или multi-user выполнение чужого кода.
4. `SandboxTier.HARDENED` остаётся отдельным будущим backend tier’ом. Его нельзя объявлять доступным только потому, что `RLIMIT_AS` или `unshare` присутствуют в окружении.
5. Переход к hardened tier требует отдельного backend, сохраняющего `ExecutionJob → ExecutionPolicy → ExecutionResult`, и положительных проверок его заявленных свойств на целевой ОС. До этого `hardened` должен быть явно отклонён контрактом как не реализованный.

## Rationale

- `RLIMIT_AS` ограничивает память процесса, но не создаёт границу доверия и не изолирует сеть или файловую систему.
- Применение лимита, которое ломает bootstrap тестового runner’а, снижает корректность и даёт ложные student/grader outcomes.
- Сохранение policy в заменяемом backend-контракте не блокирует дальнейшее hardening и позволяет отдельно тестировать прямой execution path.
- Явный tier предотвращает ошибочное представление локального single-user режима как production security boundary.

## Consequences

- Phase E G-E закрывает только MVP execution contract; hardened sandbox остаётся открытым требованием.
- Тесты должны разделять direct-job policy checks и grader acceptance. Нельзя считать успешный `setrlimit()` доказательством sandbox isolation.
- Документация и интерфейс обязаны использовать формулировку `mvp_untrusted_single_user`, пока hardened backend не реализован и не проверен.
- Числовой `RLIMIT_AS` не является переносимым SLA: его допустимое значение зависит от runtime, Python bootstrap и proot overhead.
- При смене окружения требуется повторить capability check и acceptance tests; нельзя автоматически переносить текущий порог на обычный Linux, Android host или другой container runtime.

## Acceptance evidence

- `tests/unit/test_execution.py` проверяет direct-job address-space policy и явный MVP tier.
- `tests/unit/test_grading.py` проверяет grader path без `RLIMIT_AS` bootstrap failure и с сохранением нормализации grading contract.
- `docs/execution_v0.1.md` описывает текущую policy и security limitations.
- `ROADMAP.md` и `STEPS.md` фиксируют G-E как MVP-only и следующий незакрытый трек hardening.

## Revisit triggers

Пересмотреть ADR перед public или multi-user execution, при смене Termux/proot на обычный Linux/container runtime, при появлении подтверждённого namespace/seccomp/nsjail/Docker backend, либо если acceptance-тесты покажут воспроизводимое применение `RLIMIT_AS` без ложных bootstrap failures.
