
## 20. Missing Capabilities

| # | Отсутствующая способность | Где нужна | Приоритет / Статус |
|---|---------------------------|-----------|--------------------|
| 1 | **Factory Registry** (`factory_registry`) — реестр фабрик и кузен, статусы, паспорта | Каждая Factory | ✅ реализовано (core_02/factory_registry.py) |
| 2 | **Scenario Engine** (`scenario_engine`) — исполнение сценариев-композиторов поверх Factory | Workspace OS | 📋 дизайн готов (SCENARIO_ENGINE_DESIGN_V1.md) |
| 3 | **Decision Registry** (`decision_registry`) — ADR-реестр как структура данных | Decision Forge | зарегистрировано |
| 4 | **Conformance Checker** (`conformance_checker`) — машиночитаемый конформность-чекер | Governance Forge | зарегистрировано |
| 5 | **Автогенерация моделей/диаграмм** (`model_diagram_autogen`) | Modeling Forge | зарегистрировано |
| 6 | **Web Research** (`research_web`) — веб-исследование | Research Factory | ✅ реализовано (scripts_01/research_web.py) |
| 7 | **Estimation** (`lisa_estimator`) — оценка сложности LISA-3 | Research Factory | ✅ реализовано (scripts_01/lisa_estimator.py) |
| 8 | **Opportunity Engine** (`opportunity_engine`) — ядро Intelligence-слоя | Content Factory | ✅ реализовано (scripts_01/opportunity_engine.py) |
| 9 | **Whim Capture** (`whim_capture`) — лёгкий вход мыслей | Content Factory | ✅ реализовано (scripts_01/whim_capture.py) |
| 10 | **Opportunities store** (`opportunities_yaml`) — persistent lifecycle store | opportunity_engine | ✅ реализовано (data_13/opportunities.yaml) |
| 11 | **Whims store** (`whims_yaml`) — persistent capture store | opportunity_engine | ✅ реализовано (data_13/whims.yaml) |
| 12 | **TODO** (`todo_blueprint_v3_l516`) — blueprint_v3.py:516 auto-stub | blueprint_v3 | зарегистрировано |
| 13 | **TODO** (`todo_orchestrator_l431`) — orchestrator.py:431 | orchestrator | зарегистрировано |
| 14 | **TODO** (`todo_mcp_server_l1870`) — mcp_server.py:1870 | mcp_server | зарегистрировано |
| 15 | **TODO** (`todo_buffy_autodoc_l179`) — buffy_autodoc.py:179 print() | buffy_autodoc | зарегистрировано |
| 16 | **Doc-Code Sync** (`doc_code_verify`) — verifier doc-анкоров | Architecture | ✅ реализовано (core_02/doc_code_verify.py) |
| 17 | **Intelligence Integration** (`intelligence_integration`) — тонкий integration-слой | Content Factory | ✅ реализовано (scripts_01/opportunity_engine.py) |
| 18 | **Opportunity Ranking** (`opportunity_ranking`) — композитный score | Content Factory | ✅ реализовано (scripts_01/opportunity_engine.py) |
| 19 | **Multi-prompt** (`missing_registry_multi_prompt`) — related_prompts поверх prompt_path | Governance | ✅ реализовано (core_02/missing_registry.py) |
| 20 | **FactoryRegistry Full** (`factory_registry_full`) — паспорта + select_forge | Governance | ✅ реализовано (core_02/factory_registry.py) |
| 21 | **Scenario Intelligence** (`scenario_intelligence`) — domain-neutral decision layer | Governance | ✅ реализовано (scripts_01/scenario_intelligence.py) |
| 22 | **Content Factory** (`content_factory`) — первый доменный Factory-adapter | Content | ✅ реализовано (scripts_01/content_factory.py) |
| 23 | **Research Factory** (`research_factory`) — второй доменный Factory-adapter | Research | ✅ реализовано (scripts_01/research_factory.py) |
| 24 | **Test Factory** (`test_factory`) — третий доменный Factory-adapter | Test | ✅ реализовано (scripts_01/test_factory.py) |
| 25 | **BaseFactory** (`factory_base`) — Phase 12 template (ADR-013) | core_02.factory_base | ✅ реализовано (core_02/factory_base.py) |
| 26 | **Capability Resolution Policy** (`capability_resolution_policy`) — CODE_RESOLUTION_POLICY | core_02.factory_registry | ✅ реализовано (core_02/factory_registry.py) |
| 27 | **LISA Calibration Store** (`lisa_calibration_store`) — веса калибровки | Research | ✅ реализовано (data_13/lisa_calibration.yaml) |
| 28 | **RoleExecutorRegistry** (`role_executor`) — автоисполнение LIGHT-ролей (ADR-016) | Forge | ✅ реализовано (core_02/role_executor.py) |
| 29 | **Anti-pattern miner (`anti_pattern_miner`)** — excavate anti-pattern from corpus | Research Factory | 🟡 Medium — зарегистрировано |
| 30 | **Business model constructor (`business_model_constructor`)** — 14-полей конструктор бизнес-моделей | docs_10 | 🟡 Medium — зарегистрировано |
| 31 | **Capability gap auditor (`capability_gap_auditor`)** — детерминистический audit cap-gaps (TAXONOMY-driven) | Governance Forge | 🟢 Low — ✅ **реализовано** (`core_02/capability_gap_auditor.py`) |
| 32 | **Capability gap auditor LLM (`capability_gap_auditor_llm`)** — LLM-вариант с `core_02/missing_registry` DI | Governance Forge | 🟡 Medium — ✅ **реализовано** (`core_02/capability_gap_auditor.py`, v5.189.62) |
| 33 | **Claim-source tracker (`claim_source_tracker`)** — формат факт/наблюдение/гипотеза | docs_10 | 🟡 Medium — зарегистрировано (TAXONOMY Cyrillic trigger в v5.189.61) |
| 34 | **Competitor matrix builder (`competitor_matrix_builder`)** — конкурентная матрица (landscape) | Research Factory | 🟡 Medium — зарегистрировано |
| 35 | **Corpus inspector (`corpus_inspector`)** — read-only stats + dedup + evict (TTL) | docs_10 | 🟡 Medium — ✅ **реализовано** (`scripts_01/corpus_inspector.py`) |
| 36 | **Corpus persistence (`corpus_persistence`)** — URL между сессиями (`data_13/corpus/<sha256>.jsonl`) | docs_10 | 🟡 Medium — ✅ **реализовано** (`scripts_01/corpus_persistence.py`, v5.189.54) |
| 37 | **Devil’s advocate pass (`devil_advocate_pass`)** — first ACTIVE hypothesis_ledger consumer; generates 3 counter-candidates (inversion / boundary / steel-man, deterministic no-LLM), registers via add_hypothesis BEFORE refuting the original (forward-only DAG invariant: fails-open if all candidates fail) | scripts_01 | 🟡 Medium — ✅ **реализовано** (`scripts_01/devil_advocate_pass.py`, v5.189.66) |
| 38 | **Edtech market analyst (`edtech_market_analyst`)** — анализ edtech-рынка | Research Factory | 🟡 Medium — зарегистрировано |
| 39 | **Hypothesis ledger (`hypothesis_ledger`)** — статусы open / supported / refuted | docs_10 | 🟢 Low — ✅ **реализовано** (`scripts_01/hypothesis_ledger.py`) |
| 40 | **MVP design wizard (`mvp_design_wizard`)** — конструктор MVP | docs_10 | 🟡 Medium — зарегистрировано |
| 41 | **Persona funnel analyzer (`persona_funnel_analyzer`)** — воронка персон | Research Factory | 🟡 Medium — зарегистрировано |
| 42 | **Pricing enumerator (`pricing_enumerator`)** — web-scrape курс-цен | Research Factory | 🟡 Medium — ✅ **реализовано** (`scripts_01/pricing_enumerator.py`) |
| 43 | **Qualitative review analyzer (`qualitative_review_analyzer`)** — qualitative scoring | Research Factory | 🟡 Medium — зарегистрировано |
| 44 | **Vanity metric filter (`vanity_metric_filter`)** — что НЕ считать успехом | docs_10 | 🟡 Medium — зарегистрировано |
| 45 | **Weighted scoring engine (`weighted_scoring_engine`)** — Multi-criteria priority scorer (4-factor linear weight: confidence × evidence × recency × tag_match, default sum=1.0) для SUPPORTED гипотез from `hypothesis_ledger` | scripts_01 | 🟠 Medium — ✅ **реализовано** (`scripts_01/weighted_scoring_engine.py`, v5.189.65) |
| 46 | **Artifact contract (`artifact_contract`)** — единый frozen-контракт и адаптеры между файлами, dict и ChainRun; path-traversal-safe файловая проекция | core_02 | 🟡 Medium — ✅ **реализовано** (`core_02/artifact.py`, v5.189.78) |
| 47 | **Content Localization (`content_localization`)** — learner-facing локализация Exercism-контента (locale/source hashes, переведённые ревью) | Content Factory | 🟡 Medium — ✅ **реализовано** (`projects_17/python_mentor/app/localization/`, v5.189.85) |
| 48 | **TUI History Import (`tui_history_import`)** — идемпотентный импорт истории TUI-клиента (manicode) в context.db + events.db | core_02 | ✅ **реализовано** (`scripts_01/tui_history_import.py`, v5.189.85) |

---

## Tail #26 — Phase 12 G-11.6 CAPABILITY ROUTING CONSENSUS

- **Row #26** closes **G-11.6** (capability routing ambiguity) at v5.189.30.
- Authoritative routing doc: `docs_10/engineering-memory/CANONICAL_ENGINE_ROUTING_V1.md`.
- Three orthogonal layers (D-1 MODEL, D-2 FACTORY, D-3 ROLE) — never collapse to a single source of truth (CON-7 invariant).
- `code` capability resolves to `(test_factory, verifier_forge)` at FACTORY layer (D-2); SI applies HARD GATE in `scripts_01/scenario_intelligence.py::evaluate` so opp.capability must equal scenario.capabilities[0***REMOVED*** else feas = 0.0 (DOMAIN_MISMATCH).
- Role layer (D-3) still declares `code` as a capability for developer/frontend/devops/tester/fixer roles; this drives ModelRouter model pick, NOT scenario/factory pick.
- Full participants: Phase 8 ScenarioIntelligence author + Phase 11 TestFactory author + Blueprint v3 author (consensus gated by Phase 12 G-11.6 workshop).


## Tail #27 — Phase 13 G-11.6 capability resolution (set-membership + multi-cap)

- `CapabilityResolutionPolicy` frozen dataclass landed in `core_02/factory_registry.py` (Phase 13 workshop).
- `CODE_RESOLUTION_POLICY` table for `code → (test, verifier)` as the typed single-source-of-truth.
- SI hard-gate refactored: `opp_capability in set(scenario_caps)` (was: `== capability` first-element).
- 2 multi-cap regression tests added: `test_13c_multi_cap_set_membership_positive` + `test_13d_multi_cap_cross_domain_rejected`.
- Defense-in-depth preserved: cross-domain scenarios still INFEASIBLE before ranking (I-4 invariant maintained).
- Participants: Phase 8 SI author + Phase 11 TestFactory author (re-signed D-1/D-2).
