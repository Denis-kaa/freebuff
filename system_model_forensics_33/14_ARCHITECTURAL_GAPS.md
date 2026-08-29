# 14_ARCHITECTURAL_GAPS.md — Реестр gap'ов

> **Статус:** FORENSIC FACT (по 05 + 06 + 07 + 08)

---

## Gap-реестр

| ID | Gap | Тип | Severity | Evidence | Рекомендация |
|----|-----|-----|----------|----------|--------------|
| GAP-001 | Слой Opportunity отсутствует в целевой модели | модель↔код | HIGH | EV-002 | зафиксировать в целевой модели (glossary) |
| GAP-002 | Skill описан в целевой модели, отсутствует в коде | модель↔код | MEDIUM | EV-018 | признать capability-токены = Skill; завести skill_registry (шаг 5) |
| GAP-003 | Agent — нет единой stateful абстракции | архитектура | HIGH | EV-017 | развести Role (stateless) vs Agent (stateful, будущее) |
| GAP-004 | Forge перегружен 4 смыслами | терминология | HIGH | EV-011..015 | glossary + docstrings (шаг 1) |
| GAP-005 | Scenario перегружен 2 смыслами | терминология | HIGH | EV-005/006 | glossary (шаг 1) |
| GAP-006 | Две execution-парадигмы (chain vs DAG) не связаны | архитектура | HIGH | EV-027/028 | решить: унифицировать или задокументировать (шаг 4) |
| GAP-007 | Дубль db (scripts_01/data vs data_13) | source-of-truth | MEDIUM | EV-033 | канонизировать data_13 (шаг 2) |
| GAP-008 | Tool runtime изолирован от Forge chain | архитектура | MEDIUM | EV-019 | соединить Tool ↔ Role (будущее) |
| GAP-009 | Runtime — реестр, не слой | архитектура | LOW | EV-020 | расширить runtime-слой |
| GAP-010 | Project → Platform импорты (нарушение изоляции) | boundary | MEDIUM | promt105 R | consistency_check warning (шаг 3) |
| GAP-011 | Workspace «разговор/обсуждения» живут вне Workspace | модель | LOW | EV-003 | задокументировать (ContextManager/Memory) |
| GAP-012 | Factory только 4 (target: 8+) | охват | LOW | EV-031 | не создавать автоматически; по demand |
| GAP-013 | Traceability разрознена (нет сквозного component_id) | traceability | MEDIUM | 11 | data_13/traceability.yaml |
| GAP-014 | NN-нумерация историческая, не отражает слой | filesystem | LOW | promt105 | целевая структура (09), позже |

---

## Приоритет закрытия

1. GAP-001 + GAP-004 + GAP-005 (glossary, нулевой риск) — сразу.
2. GAP-007 (source-of-truth db) — средний риск, высокий эффект.
3. GAP-006 (две парадигмы) — решить явно.
4. GAP-002 + GAP-003 (Skill/Agent) — аддитивно.
5. Остальное — по demand.
