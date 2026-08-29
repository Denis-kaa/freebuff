# DECISIONS.md — Индекс решений проекта Lead Aggregator (Attract-модуль)

> **Scope:** PROJECT-LOCAL — решения, принадлежащие проекту, а не платформе.
> **Конвенция:** [`docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md`***REMOVED***(../../../docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md) §4.
> **Создан:** 2026-08-10 (v5.147.0) · **Агент:** Buffy

| # | Решение | Статус | Дата | Related |
|---|---------|--------|------|---------|
| ADR-001 | Pull-модель + порядок источников (Kwork → TG-каналы) | ✅ Accepted | 2026-08-10 | PHASE2, ADR-014 (platform) |
| ADR-002 | Юридический гейт: read-only, без outbound, без приватных данных | ✅ Accepted | 2026-08-10 | PHASE1 W-7 |
| ADR-003 | Контракты-адаптеры (TLSClient/ProxyRotator/CheckpointStore) — встраивание вместо платформенных импортов | ✅ Accepted | 2026-08-10 | PHASE2, W-2/W-3/W-5 |

---

## Как добавлять ADR

1. Копия шаблона из `docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md` §4 (секции: Context / Decision / Альтернативы / Consequences).
2. Файл: `ADR-NNN_<slug>.md` (NNN — следующий свободный номер).
3. Строка в эту таблицу.
4. Cross-link в `MANIFEST.md` (секция «Документация проекта»).

## Принципы

- **Scope-граница:** решения о платформе — в `docs_10/engineering-memory/decisions/` (ADR_013/014); решения проекта — здесь.
- **Provenance:** если решение дублирует платформенное — пометка «self-contained копия с provenance».
- **Ничего не удаляется** (как IDEAS.md): изменённый ADR получает статус `Superseded`, а не удаление.
