# PHASE5 FUTURE GAPS — v5.189.16

> §23: найденные проблемы НЕ исправлялись автоматически — зафиксированы для будущих этапов.
> §3 SCOPE: всё ниже вне разрешённого scope этой фазы.

---

## A. Намеренно НЕ тронуто (scope §3 «НЕ делать»)

| # | Направление | Почему будущий этап |
|---|---|---|
| 1 | **Полноценный FactoryRegistry** (паспорт factory.yaml, capability-каталог) | ✅ **РЕАЛИЗОВАН** (v5.189.21, промт 089): FactoryPassport + capability-каталог (union factory.yaml + forge passports) + `select_forge()` — разблокирует Factory-путь в цикле |
| 2 | **Advanced Opportunity Ranking** (приоритизация кандидатов по score) | ✅ **РЕАЛИЗОВАН** (v5.189.18, промт 086): композитный score (confidence·0.5 + source·0.2 + recency·0.2 + priority·0.1), `rank_candidates()` + `discover --rank`; см. §20 row #18 |
| 3 | **Scenario Intelligence** (автовыбор сценария по контенту кандидата) | сейчас `propose()` через существующий ScenarioRegistry; интеллект выбора — отдельный слой |
| 4 | **Content Intelligence** (анализ содержимого артефактов) | за пределами Intelligence Loop |
| 5 | **Concept Evolution System** | отдельный research-трек |
| 6 | **C-A / C-B / C-C** (эволюционные слои) | отдельные фазы |
| 7 | **Evolution Memory** | отдельная фаза |
| 8 | **Автономный Project Intelligence** (непрерывный фон-цикл) | требует scheduler/agent runtime — отдельная фаза |
| 9 | **Workspace UI** | отдельный трек (Flutter/TUI) |

## B. Наблюдения (не баги текущего slice, кандидаты на след. фазу)

| # | Наблюдение | Куда |
|---|---|---|
| 1 | `_discover_from_whims` обрабатывает только ACTIVE-whims; DEFERRED/REACTIVATED-семантика whim → opportunity (§13) не используется в DISCOVER (комментарий DEFERRED в коде) | Design decision следующей фазы |
| 2 | Dedup по (source, source_id) — детерминированный identity; при появлении новых полей-признаков (title hash) можно усилить | §18 расширение |
| 3 | E2E использует `sys.modules`-мок для ForgeFacade — полный production E2E требует живой chain (роли + ForgePipeline) | integration runner следующей фазы |
| 4 | ProjectPulse/EventBus читаются только в DISCOVER; обратная связь (pulse от результатов accumulate) не построена | замкнуть полнее |
| 5 | LearningLoop.record_feedback вызывается best-effort; консолидированный confidence-анализ по kind=candidate — будущий этап | Learning maturity |
| 6 | CLI `discover`/`run` не имеют `--dry-run` на уровне CLI (execute поддерживает dry_run) | UX-долг |
| 7 | Реальный `data_13/context.db` accumulate в production не прогонялся (тесты герметичны) — нужен ручной smoke на живых данных | ops-проверка |
| 8 | **MissingRegistry schema:** единственное поле `prompt_path` — одна ссылка на промт. При `mark-implemented --prompt` (intelligence_integration, v5.189.16) замена 084→085 стирает machine-readable след forensics-промта (084 остаётся только в free-text `description` реестра + §20-сноске, без структурированного поля) | ✅ **РЕШЕНО** (v5.189.19: `related_prompts: [***REMOVED***` в MissingRegistry + CLI `add-related-prompt`/`--related-prompt`; backfill `intelligence_integration.related_prompts=[084_19_intelligence_integration_forensics.md***REMOVED***`; промт `pompts_11/088_19_missing_registry_multi_prompt.md`) |
| 9 | **Коллизия пользовательской нумерации промтов с каноническими `NNN_19_*.md`:** пользовательский «промт 87» (multi-prompt MissingRegistry) коллизировал с каноническим `087_19_phase6_code_contract_forensics.md` → перенумерован в **088** (`088_19_missing_registry_multi_prompt.md`, v5.189.19, rationale в CHANGELOG). **Future-риск:** пользовательский «промт 88» может коллизировать с `088_19_missing_registry_multi_prompt.md` (и любой «промт N» — с занятым `NNN_19_*.md`). Рекомендация: при «промт N» проверять занятость `pompts_11/NNN_19_*.md`; при коллизии брать следующий свободный NNN + фиксировать rationale в CHANGELOG | naming/ops-дисциплина |

## C. Порядок (рекомендация roadmap)

1. Advanced Opportunity Ranking (быстрый выигрыш поверх provenance confidence).
2. ✅ Полноценный FactoryRegistry (§15 gap) — разблокирует Factory-путь в цикле (РЕАЛИЗОВАН v5.189.21, промт 089).
3. Scenario Intelligence.
4. Evolution Memory / C-* треки — после стабилизации Memory/Learning.

**Правило (§23):** ни один пункт выше НЕ смешивать с текущей задачей; каждый — отдельный промт с register-first циклом.
