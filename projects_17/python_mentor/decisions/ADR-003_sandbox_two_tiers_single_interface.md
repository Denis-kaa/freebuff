# ADR-003 — Sandbox: два tier'а с единым интерфейсом (MVP сейчас, hardened потом)

> **Статус:** 🟢 Accepted (2026-08-23)
> **Источник:** blueprint v0.1 §0/§9, prompt2 Phase E
> **Уточнение:** [ADR-005***REMOVED***(ADR-005_rlimit_as_termux_proot_mvp_hardened_boundary.md) фиксирует поведение `RLIMIT_AS` в Termux/proot и критерии границы hardened tier.

## Context

Система исполняет студенческий код. Строгие изоляторы (nsjail/Docker) в текущей среде обычно недоступны: Termux (нерутованный Android), без user namespaces по умолчанию. Публичного multi-tenant сценария нет — пользователь один, код свой.

## Options

1. Один «настоящий» sandbox (nsjail/Docker) — блокирует прогресс: инфраструктура недоступна.
2. Голый subprocess без ограничений — небезопасно даже для MVP.
3. **Два tier'а с единым интерфейсом:** `SANDBOX_TIER = "mvp_untrusted_single_user"` (сейчас): subprocess + timeout + RLIMIT_CPU/AS + output limit + temp dir + cleanup + sanitized env; `"hardened"` (future): nsjail/Docker с network/filesystem isolation, тот же контракт Job → Worker → Sandbox → Result.

## Decision

Принят вариант 3. Интерфейс единый независимо от tier'а — смена tier'а не требует переписать остальную систему. Перед реализацией MVP обязательно проверить `unshare --user echo ok`; если user namespaces доступны — сделать MVP чуть безопаснее; не обещать того, чего нет.

## Rationale

- Честность ограничений (blueprint §0): никаких `network_isolation = true` без OS-механизма.
- Нулевая блокировка разработки: Phase E реализуется в Termux, hardened — интерфейс-заглушка.
- Один пользователь и localhost делают subprocess+limits приемлемым компромиссом.

## Consequences

- В коде обязательный флаг `SANDBOX_TIER`; security tests по списку prompt2 Phase E §7.
- Hardened-бэкенд — будущий (интерфейс `ExecutionBackend`), публичный запуск вне scope (ROADMAP §3).
- Никаких обещаний безопасного исполнения произвольного чужого кода.

## Links

- [blueprint §0/§9***REMOVED***(../python_ai_tutor_blueprint_v0.1.md) · [prompt2 Phase E***REMOVED***(../prompt2.md) · [ROADMAP §3/§9***REMOVED***(../ROADMAP.md)