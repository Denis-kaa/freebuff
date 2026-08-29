# AUDIT_DELTA_v5.189.82.md — Изменения после v5.189.75 (P1-закрытие Agent + Integration)

> **Назначение:** внешнему аудитору мог быть передан архив `FORENSICS_104_105_106_107_v5.189.75.tar.gz`
> ДО того, как были реализованы ADR-019 (Agent) и ADR-020 (Integration). Этот файл — явный перечень
> **каких файлов коснулись изменения, что именно изменилось и почему.**
> Файлы, НЕ перечисленные здесь, в архиве v5.189.82 идентичны v5.189.75.

---

## Изменённые файлы (vs v5.189.75)

| # | Файл | Что изменилось | Почему | Дата |
|---|------|----------------|--------|------|
| 1 | `FORENSICS_104_105_106_107/_consolidated/UNIFIED_CONCLUSIONS.md` | Заголовок: 4→6 проходов; §3: Agent и Integration убраны из DOCUMENTED ONLY (добавлен блок «Закрыто → IMPLEMENTED»); §4: P1-контракты ВСЕ ЗАКРЫТЫ с evidence (Agent — ADR-019, Integration — ADR-020); §5: Agent и Integration сняты с «только предполагаем»; §6: итоговый вердикт обновлён (все P1 закрыты, остались P0+P2) | Agent (v5.189.80) и Integration (v5.189.81) реализованы — forensic-документы должны отражать фактическое состояние кода | 2026-08-22 |
| 2 | `FORENSICS_104_105_106_107/_consolidated/EVIDENCE_LEDGER_MERGED.md` | Добавлено 2 строки в секцию «Integration / Security»: Agent base class + lifecycle (ADR-019, core_02/agent_base.py, 29 тестов) и Integration adapter boundary (ADR-020, core_02/integration_base.py, 33 теста) — оба с пометкой «РЕАЛИЗОВАН» | Журнал доказательств должен содержать все значимые claims | 2026-08-22 |
| 3 | `FORENSICS_104_105_106_107/_consolidated/INDEX.md` | Временная линия: добавлены шаги 5 (ADR-019, v5.189.80) и 6 (ADR-020, v5.189.81); пометка «Все P1-контракты ЗАКРЫТЫ» | Полнота временной линии | 2026-08-22 |
| 4 | `FORENSICS_104_105_106_107/README.md` | Версия v5.189.75→v5.189.82; описание обновлено (добавлены ADR-019/020 результаты); счётчик 49→50 файлов; ссылка на новый AUDIT_DELTA_v5.189.82.md | Новый релиз архива | 2026-08-22 |
| 5 | `FORENSICS_104_105_106_107/_consolidated/AUDIT_DELTA_v5.189.82.md` | **НОВЫЙ файл** (этот документ) | Явная маркировка изменений для аудитора | 2026-08-22 |

## Что НЕ менялось

- `architecture_forensics_v2/` (промт 104) — все 13 файлов **идентичны** v5.189.75.
- `repository_organization_forensics_32/` (промт 105) — все 3 файла **идентичны** v5.189.75.
- `system_model_forensics_33/` (промт 106) — все 17 файлов **идентичны** v5.189.75.
- `platform_architectural_inventory_34/` (промт 107) — все 11 файлов **идентичны** v5.189.75.
- `FORENSICS_104_105_106_107/_consolidated/AUDIT_DELTA.md` — идентичен v5.189.75 (исторический документ).
- `core_02/agent_base.py`, `core_02/integration_base.py`, `tests_09/test_agent_base.py`, `tests_09/test_integration_base.py` — НЕ входят в forensic-архив (это production-код, не forensic).

## Ключевой содержательный сдвиг (кратко)

**Было (v5.189.75):** DOCUMENTED ONLY включал AGENT как класс с lifecycle и Integration/Connector/Adapter слой; P1-отсутствующие контракты: Agent base class + Integration adapter boundary.

**Стало (v5.189.82):** оба контракта ЗАКРЫТЫ:
- **ADR-019 Agent:** `core_02/agent_base.py::Agent` (ABC) + `AgentLifecycle` (forward-only DAG CREATED→ACTIVE→PAUSED→DONE/FAILED) + `route_model`/`run_forge` сервисы + `AgentResult` + 29 hermetic тестов.
- **ADR-020 Integration:** `core_02/integration_base.py::IntegrationAdapter` (ABC) + `AuthSpec` (5 методов: none/bearer/vault/chat_id_scope/phone_scope) + `INTENT_CAPABILITY_MAP` (закрытый словарь intent→capability, ANTI-6b) + `call_platform` (SmartRouter, §7.3) + `log_event` + 33 hermetic теста.

**Все P1-контракты ЗАКРЫТЫ (v5.189.81):**

| ADR | Суть | Статус |
|-----|------|--------|
| ADR-018 | Factory→Forge мост (6 тестов, v5.189.77) | ✅ Accepted |
| ADR-019 | Agent base class + lifecycle (29 тестов, v5.189.80) | ✅ Accepted/Implemented |
| ADR-020 | Integration adapter boundary (33 теста, v5.189.81) | ✅ Accepted/Implemented |

**Открытыми остаются:** P0 (единая Workspace модель — design: ADR-017, реализации нет; sandbox/tool-ACL), P2 (дубли task/tool/memory), P3 (репозиторий), P4 (enhancements).