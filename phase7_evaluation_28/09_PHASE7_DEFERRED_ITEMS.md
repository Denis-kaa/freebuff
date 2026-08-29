# 09_PHASE7_DEFERRED_ITEMS.md — Deferred Items

> Phase 7 §3 (ЗАПРЕТ НА SCOPE CREEP): проблемы вне scope регистрируются с
> problem / evidence / severity / recommended phase.

| # | Item | Problem | Evidence | Severity | Recommended phase |
|---|------|---------|----------|----------|-------------------|
| 1 | **Автономный feedback engine** | Phase 7 создаёт только техническую возможность цепочки OPPORTUNITY→EXECUTION→EVENT→MEMORY→INTELLIGENCE (§10). Полноценный автономный контур переоценки/следующей opportunity не реализован. | §10 «НЕ реализовывай полноценный autonomous feedback engine» | Low (by design) | Phase 8 (Scenario Intelligence) |
| 2 | **DOCUMENT_TAGGING foundation** | Минимальный contract-level tagging (DOCUMENT PARAGRAPH → TAG → CONTRACT → CODE SYMBOL → TEST) не строился — вне scope Phase 7. | §11 «Если реализация tagging выходит за scope — зафиксируй deferred» | Medium | Phase 8/9 |
| 3 | **Scenario Intelligence** | Phase 7 использует существующий `ScenarioRegistry.propose_roles` как есть; интеллектуальный выбор сценария (score/ранжирование поверх fuzzy match) — следующий этап. | §28 NEXT PHASE = SCENARIO INTELLIGENCE | Medium | Phase 8 |
| 4 | **Content Factory** | Полноценный Content Factory (после Scenario Intelligence) — вне Phase 7. | §28 | Low | Phase 9 |
| 5 | **LLM-синтез hypothesis/rationale** | Intelligence-оценка v1 детерминированные эвристики; LLM-синтез — позже. | INTELLIGENCE_FACTORY_CONTRACT §N | Medium | Phase 8+ |
| 6 | **FactoryRegistry полная интеграция** | Factory selection подключён к execute(), но полный Factory-путь (паспорта, capabilities, выбор по статусу) — развитие в следующих фазах. | §6/§7 | Low | Phase 8 |
| 7 | **`scenario.selection` PARTIAL** | `ScenarioRegistry.find_role` возвращает None вместо raise `RoleNotFoundError` (CONTRACT_REGISTRY §C.6 #1) — pre-existing, вне Phase 7. | CONTRACT_REGISTRY §C.6 #1 | Low | P1.4 |
| 8 | **`opportunity.execute` mypy gap** | Lazy import forge_facade.run_chain без аннотаций (CONTRACT_REGISTRY §C.6 #2) — pre-existing. | CONTRACT_REGISTRY §C.6 #2 | Low | v1.4 |

---
_Все deferred-пункты зафиксированы с evidence; ни один не является скрытым расширением scope Phase 7._
