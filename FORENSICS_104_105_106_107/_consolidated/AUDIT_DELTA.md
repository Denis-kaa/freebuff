# AUDIT_DELTA.md — Изменения после v5.189.73 (для внешнего аудита)

> **Назначение:** внешнему аудитору мог быть передан архив `FORENSICS_104_105_106_107_v5.189.73.tar.gz`
> ДО того, как были внесены правки по Path B и ADR-017. Этот файл — явный перечень
> **каких файлов коснулись изменения, что именно изменилось и почему.**
> Файлы, НЕ перечисленные здесь, в архиве v5.189.75 идентичны v5.189.73.

---

## Изменённые файлы (vs v5.189.73)

| # | Файл | Что изменилось | Почему | Дата |
|---|------|----------------|--------|------|
| 1 | `platform_architectural_inventory_34/CONTRACT_GRAPH.md` | Граф 1 + сводная таблица: `Factory → Forge` переклассифицирован **PARTIAL → REAL**; добавлены evidence-строки (`opportunity_engine.py:941`, `factory_base.py:361`, `forge.py:490`); примечание про адвизорный forge_id | Forensic-вывод был завышен: код показал, что execution-мост СШИТ (см. EVIDENCE_LEDGER_MERGED) | 2026-08-22 |
| 2 | `FORENSICS_104_105_106_107/_consolidated/UNIFIED_CONCLUSIONS.md` | §3 (Path B PARTIAL→REAL), §4 (Factory→Forge снят из P1 «отсутствующие контракты» как ЗАКРЫТ), §5 (select_forge → run_chain REAL с evidence) | Синхронизация с исправленным CONTRACT_GRAPH | 2026-08-22 |
| 3 | `FORENSICS_104_105_106_107/_consolidated/EVIDENCE_LEDGER_MERGED.md` | Строка «Factory→Forge execution НЕ сшит (Path B PARTIAL)» заменена на 4 строки REAL-доказательств (opportunity_engine.execute, BaseFactory.execute, forge.py cmd_chain, forge_id адвизорный) | Журнал доказательств должен отражать фактическое состояние кода | 2026-08-22 |
| 4 | `FORENSICS_104_105_106_107/README.md` | Счётчик файлов 47→48 (AUDIT_DELTA.md учитывается) | Новый файл пакета | 2026-08-22 |
| 5 | `docs_10/engineering-memory/decisions/ADR_017_Unified_Workspace_Model.md` | **НОВЫЙ файл** (вне пакета, но ссылается на него): единая Workspace модель (SQLite mapping + YAML конфиг + sync-контракт) | P0-блокер «Workspace ×2» закрыт дизайном | 2026-08-22 |
| 6 | `FORENSICS_104_105_106_107/_consolidated/AUDIT_DELTA.md` | **НОВЫЙ файл** (этот документ) | Явная маркировка изменений для аудитора | 2026-08-22 |

## Что НЕ менялось

- `architecture_forensics_v2/` (промт 104) — все 13 файлов **идентичны** v5.189.73.
- `repository_organization_forensics_32/` (промт 105) — все 3 файла **идентичны** v5.189.73.
- `system_model_forensics_33/` (промт 106) — все 17 файлов **идентичны** v5.189.73.
- `platform_architectural_inventory_34/` — изменён **только** `CONTRACT_GRAPH.md`; остальные 10 файлов идентичны.
- `FORENSICS_104_105_106_107/_consolidated/INDEX.md` — **идентичен** v5.189.73.

## Ключевой содержательный сдвиг (кратко)

**Было (v5.189.73):** Path B `Opportunity → select_forge → (ForgePassport)` — PARTIAL, execution-мост к ForgeFacade «не сшит», Factory→Forge числился в P1-отсутствующих контрактах.

**Стало (v5.189.75):** Path B — **REAL**:
- `scripts_01/opportunity_engine.py:941` — `facade.run_chain(project, role_ids)` внутри `execute()` (после `_select_factory_forge` → `select_forge`)
- `core_02/factory_base.py:361` — `BaseFactory.execute()` вызывает `facade.run_chain(...)`
- `scripts_01/forge.py:490` — chain-CLI тоже идёт через `run_chain`
- `forge_id` из паспорта — адвизорный (traceability в `provenance['factory_selection'***REMOVED***`), исполнение по `role_ids` сценария; в системе единый ForgeFacade/ForgePipeline — дыры нет.

**Практический вывод для аудитора:** «построить Factory→Forge мост» НЕ требуется — мост существует и его контракт зафиксирован ADR-018 (закрыт дизайном, реализация — только тесты маппинга). Открытыми P1-контрактами остаются Agent base class (ADR-019) и Integration boundary (ADR-020).
