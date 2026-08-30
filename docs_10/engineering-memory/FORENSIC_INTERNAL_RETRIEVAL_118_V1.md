# FORENSIC ARCHITECTURE REPORT: Internal Retrieval / Knowledge Fabric

> Executed per `pompts_11/118.md` (mature v2 of `118_19_internal_retrieval_knowledge_audit.md`).
> Mode: READ -> MAP -> CROSS-REFERENCE -> VERIFY -> REPORT. No code written, no migrations run.
> Date: 2026-08-30. Evidence checked against the live workspace, not documentation claims.

---

## A. Executive Summary

The platform does NOT lack retrieval machinery. It has five overlapping retrieval stacks, all implemented. What it lacks is (1) fresh and populated indices, (2) an enforced "consult before act" step in the agent loop, and (3) coverage of the highest-value knowledge sources (LESSONS.md, prompt corpus, fresh CHANGELOG).

**Verdict: Option B (minimal).** Build nothing new at the storage or engine level. Add one thin Retrieval Facade that the agent loop consults before acting, backfill the empty Organizational Memory store, and refresh the stale index with wider doc coverage. No pgvector, no new engine, no new graph engine.

Confidence: HIGH on inventory (verified against live code and live DBs), MEDIUM on root cause of the empty OM store (inferred from data, not from a logged failure).

## B. Evidence Map (CLAIM -> EVIDENCE -> CONFIDENCE)

| # | Claim | Evidence | Confidence |
|---|-------|----------|------------|
| E1 | KnowledgeEngine is IMPLEMENTED and functional | `scripts_01/knowledge_engine.py` (FTS5 `porter unicode61`, TF-IDF, LSA `semantic_ml`, hybrid). Live DB `context_12/knowledge/index.db`: 97 docs in `docs_fts` + `doc_meta` | HIGH |
| E2 | The knowledge index is STALE | index.db last modified Aug 1; repo now has 223 docs under docs_10 and 119 prompts. Index has 97 docs | HIGH |
| E3 | RAGEngine (RAG 2.0, RRF) is IMPLEMENTED and exposed | `scripts_01/rag_engine.py` (RRF, rerank, expand_query); MCP tools `rag_search`, `rag_hybrid`, `rag_rerank` at mcp_server.py:661-679 | HIGH |
| E4 | Organizational Memory store is IMPLEMENTED but EMPTY | `core_02/memory_store.py` (full schema in data_13/context.db). Live counts: knowledge_objects=0, knowledge_links=0, learning_events=86 | HIGH |
| E5 | LearningLoop is a dead end in practice | `core_02/learning_loop.py` analyze() -> `SemanticLayer.find_similar_patterns()` -> filters kinds over knowledge_objects -> store is empty, so analyze always returns "no known pattern". 86 learning_events accumulate but nothing formalizes them into knowledge objects | HIGH |
| E6 | GraphIndex code exists but the graph is UNPOPULATED | `scripts_01/graph_index.py` (nodes/edges schema, related/path/subgraph/traverse). Live `context_12/knowledge/index.db` has NO graph_nodes/graph_edges tables. KnowledgeEngine.graph lazy-inits GraphIndex on the same DB but nothing ever populates it | HIGH |
| E7 | EventStore has working FTS search | `freebuff_plugin_03/event/store.py` `_search_fts` (FTS5 + triggers). Live: 88 events, 88 FTS rows | HIGH |
| E8 | MemoryEngine is a separate silo from MemoryStore | `scripts_01/memory_engine.py` (5 levels: working/project/knowledge/personal/archive, key-value) vs `core_02/memory_store.py` (knowledge objects + graph). Different domains, both called "memory" | HIGH |
| E9 | The agent loop has a "consult before act" step ONLY in Orchestrator | `scripts_01/orchestrator.py:695` `check_existing_context` (rule 8) queries KnowledgeEngine before creating a workflow. But nothing outside orchestrator.py's own CLI instantiates Orchestrator. The agent (TUI/Freebuff sessions) does not pass through it | HIGH |
| E10 | The agent has retrieval tools available but no enforced step to use them | MCP tools: `knowledge_search`, `rag_search`, `rag_hybrid`, `rag_rerank`, `memory_store/retrieve/list`, `context_resume`, `session_status` | HIGH |
| E11 | seed_knowledge covers root manifests + docs_10/**.md, excludes AUDIT_* | `scripts_01/seed_knowledge.py` `_collect_doc_sources`. Index has 97 docs, last built Aug 1 | HIGH |
| E12 | core_02/LESSONS.md is NOT in the seed sources | `_collect_doc_sources` has no core_02 entry. The only "lessons_learned" doc in the index (553 chars) is the EM template artifact from `memory/knowledge/lessons_learned_md`, not LESSONS.md | HIGH |
| E13 | pompts_11 is NOT indexed | no pompts source in seed; no pompts doc in the index | HIGH |
| E14 | CHANGELOG.md IS indexed but stale | `mem_knowledge_changelog_md` exists; index frozen Aug 1, CHANGELOG now at 5.189.85 | HIGH |
| E15 | EventStore FTS search is IMPLEMENTED | `freebuff_plugin_03/event/store.py` `_search_fts` (FTS5 + insert/update/delete triggers). Live: 88 events, 88 FTS rows | HIGH |
| E16 | Six registries exist | scenario_registry, workspace_registry, forge_registry, missing_registry, factory_registry (core_02) + ToolRegistry (scripts_01/tool_runtime.py) + PluginRegistry (plugin_api) + RuntimeRegistry (freebuff_plugin_03/runtime/registry.py) | HIGH |
| E17 | GraphIndex vs MemoryStore.knowledge_links is a real duplication | two graph implementations: `scripts_01/graph_index.py` (nodes/edges, doc-level) and `core_02/memory_store.py` knowledge_links (org rel_types: supports/contradicts/duplicates/supersedes/...) | HIGH |

## C. Current Retrieval Architecture (as built)

```
Agent (TUI / Freebuff / TG)
  |
  |-- MCP tools (opt-in, not enforced):
  |     knowledge_search   -> KnowledgeEngine (FTS5 + TF-IDF + LSA, hybrid)
  |     rag_search/hybrid/rerank -> RAGEngine (RRF + rerank + expansion)
  |     memory_store/retrieve/list -> MemoryEngine (5 levels, key-value)
  |     context_resume     -> last checkpoint conspect (file)
  |
  |-- Orchestrator.check_existing_context (rule 8) -> KnowledgeEngine
  |     (only reachable via orchestrator.py CLI; nothing instantiates it)
  |
  |-- AgentContextBridge -> ContextManager (sessions/messages -> data_13/context.db)
  |
  |-- EventBus (context_12/events.db via default bus)
        |-- auto_index_subscriber: memory.stored -> KnowledgeEngine.index_document
        |-- LearningLoop (AFC) -> MemoryStore (knowledge_objects)  [EMPTY]
        |-- GraphIndex (lazy, same DB as KnowledgeEngine)          [UNPOPULATED]
```

## D. Agent -> Context -> Knowledge Flow (as it actually runs)

1. User message arrives via TUI/Freebuff client.
2. Session and messages persist via ContextManager into data_13/context.db. VERIFIED working (58 sessions, 4141 messages after TUI import).
3. Events flow into context_12/events.db via EventBus -> EventStore (88 events, FTS-searchable).
4. Retrieval happens only if the agent opts in: `knowledge_search`, `rag_search`, `memory_retrieve`, `context_resume` MCP tools exist and work.
5. NO step forces a consult before acting. Orchestrator rule 8 exists but nothing instantiates Orchestrator outside its own CLI. This is the core gap.
6. LearningLoop.analyze is reachable but always returns "no known pattern" because knowledge_objects is empty (0 rows, 86 learning_events unformalized).

## E. Documentation Audit

| Doc | Machine-searchable? | In index? | Fresh? | Notes |
|-----|--------------------:|-----------|--------|-------|
| root manifests (README, TASK, AGENTS, CHANGELOG...) | YES via seed | YES | NO (Aug 1) | CHANGELOG is 5.189.85 now |
| docs_10/**.md (223 files) | YES via seed | 97 indexed (AUDIT_* excluded) | NO (Aug 1) | ~126 newer/never indexed |
| core_02/LESSONS.md | NO | NO | n/a | NOT in seed sources. The only "lessons" doc in the index is the 553-char EM template, not LESSONS.md |
| pompts_11 (119 prompts) | NO | NO | n/a | NOT in seed sources |
| ADRs in docs_10/engineering-memory/decisions | YES via seed | partial | NO | indexed only up to Aug 1 |
| MemoryEngine entries | YES via auto-index subscriber | partial | live | memory.stored -> index_document, works when bus is live |
| EventStore | YES (own FTS) | 88 events | live | separate FTS, not in KnowledgeEngine |

**Key finding:** the single most operationally valuable knowledge source (core_02/LESSONS.md, 1496 lines, 102 CON-N entries) is invisible to machine retrieval. The agent's own hard-won lessons are unsearchable.

## F. LESSONS.md Audit (separate per 118.md)

- Source of truth? YES by convention (AGENTS.md §5, CON-18), but it is a prose Markdown file with no frontmatter, no stable IDs per lesson beyond CON-N headings, no machine-readable links to ADRs/components.
- Semantic search? NO. It is not in seed sources, so KnowledgeEngine never indexes it. `find_similar_patterns` cannot return a lesson because lessons live in an empty knowledge_objects table, not in the file.
- Lesson -> ADR -> Component links? Prose-only ("см. docs_10/..."). No graph edges exist anywhere (graph tables do not even exist).
- Verdict: PARTIAL as human documentation, ABSENT as machine knowledge. Highest-value, lowest-effort fix in the whole report.

## G. CHANGELOG Audit

- It is a projection of Git history + hand-written release notes, not a source of truth for decisions (ADRs hold the "why").
- It IS in seed sources and indexed (`mem_knowledge_changelog_md`), but the index froze Aug 1 while CHANGELOG is at 5.189.85.
- EventStore is the event-level truth (88 events) but is a separate FTS silo, not fused into KnowledgeEngine results.
- Verdict: PARTIAL. Keep CHANGELOG as release narrative; keep EventStore as event truth; fuse both into retrieval results rather than merging the stores.

## H. Memory / Knowledge / Graph / Context / Events Boundary Check

| Component | Domain | Store | Status |
|-----------|--------|-------|--------|
| ContextManager | sessions, messages, checkpoints | data_13/context.db | VERIFIED working |
| MemoryEngine | key-value memory, 5 levels | data_13/context.db (memory tables) | VERIFIED |
| MemoryStore (OM) | knowledge objects + org graph | data_13/context.db (OM tables) | IMPLEMENTED, EMPTY (0 objects, 86 learning_events) |
| KnowledgeEngine | doc search | context_12/knowledge/index.db (FTS+TF-IDF+LSA) | IMPLEMENTED, STALE (97 docs, Aug 1) |
| GraphIndex | doc-level graph | lazy on index.db | IMPLEMENTED, UNPOPULATED (no tables) |
| EventStore | event log + FTS | context_12/events.db | VERIFIED (88 events, FTS works) |
| RAGEngine | ranking layer over KnowledgeEngine | none (stateless) | IMPLEMENTED, exposed via MCP |

No true overlap between ContextManager / MemoryEngine / MemoryStore / KnowledgeEngine domains: sessions vs key-value memory vs knowledge objects vs doc search. The ONE real duplication is GraphIndex vs MemoryStore.knowledge_links (two graph implementations).

## I. Six Registries: would internal retrieval have prevented them?

| Registry | Domain | Duplication? |
|----------|--------|--------------|
| scenario_registry | scenario lifecycle | no, own domain |
| workspace_registry | workspace/project mapping | no, own domain |
| forge_registry | forge instances | no, own domain |
| factory_registry | factory configs | no, own domain |
| missing_registry | meta-registry of missing capabilities | already functions as the meta-registry (B10 lifecycle) |
| ToolRegistry / PluginRegistry / RuntimeRegistry | tools/plugins/runtime capabilities | adjacent but different namespaces |

Verdict: NO. The registries exist because of different owner-files and lifecycles (B-Rules 3-5), not because retrieval failed. Internal retrieval would not have prevented them; missing_registry already serves as their meta-layer. Registry count is by design, not by accident.

## J. Factory -> Forge Check

Factory->Forge bridge is Path B REAL (ADR-018: opportunity_engine.py:941, factory_base.py:361, forge.py:490). Is poor retrieval the cause of any Factory->Forge problem? NO EVIDENCE. The documented Factory->Forge gaps are contract/semantics issues, independent of retrieval. Treating retrieval as the cause would be a wrong root cause. GAPs are independent.

## K. Responsibility Matrix (overlap / gap)

| Pair | Overlap | Gap |
|------|---------|-----|
| KnowledgeEngine vs RAGEngine | RAGEngine wraps KnowledgeEngine (superset: RRF + rerank) | none; RAGEngine is the better entry point |
| SemanticLayer vs KnowledgeEngine | wrapper, by design | none |
| GraphIndex vs MemoryStore.knowledge_links | TWO graph implementations | real duplication; needs an ownership decision |
| MemoryEngine vs MemoryStore | naming only, different domains | naming confusion risk; document, do not merge |
| EventStore FTS vs KnowledgeEngine | two FTS silos | results never fused |
| Orchestrator rule 8 vs agent loop | one consult step, unreachable | the actual gap |

## L. Planner Options (per 118.md)

- **Option A: agent picks tools ad hoc.** Current state. Works when the agent remembers to search; fails silently when it does not. This is today's failure mode.
- **Option B: Retrieval API + planner step.** One facade (`retrieve(query, need) -> evidence`) + one enforced consult step before acting. Reuses KnowledgeEngine/RAGEngine/EventStore underneath.
- **Option C: Information Need -> Retrieval Fabric.** Agent states an information need; a fabric layer routes to SQL/FTS/vector/graph. Over-engineered for a 97-doc corpus with zero vectors and an empty graph. Rejected for now; Option B is a strict subset that C can later grow from.

## M. Storage Options (pgvector question)

1. SQLite as-is (FTS5 + TF-IDF + LSA): current, sufficient at 97-doc scale, zero ops.
2. PostgreSQL + pgvector: real embeddings, but requires a PG instance on Termux + server, migration of two SQLite DBs, and a reason. No evidence of semantic-quality failures at 97 docs.
3. PG + pgvector + FTS + Graph: full fabric. Rejected: no evidence at this corpus size.
4. Dedicated vector DB: rejected outright at this scale.

Verdict: stay on SQLite. Revisit pgvector only when the corpus passes roughly 10k docs or TF-IDF/LSA quality measurably fails.

## N. What NOT to Build

- No pgvector, no new vector DB, no PG migration now.
- No new graph engine. Decide ownership instead: MemoryStore.knowledge_links is canonical for org relations (lesson/ADR/component), GraphIndex stays doc-artifact-level, and only if it ever gets populated.
- No separate "RAG for lessons" system. Lessons flow through the existing SemanticLayer kinds filter once they exist as knowledge objects.
- No rewrite of KnowledgeEngine or RAGEngine.
- No Orchestrator resurrection just to get rule 8; the consult step belongs in the agent bootstrap, which actually runs.

## O. Safe Implementation Sequence (minimal, additive)

1. **Refresh and widen the index (small, pure win).** Run seed_knowledge + rebuild. Add `core_02/LESSONS.md` to seed sources (it is the highest-value missing doc). Add a CHANGELOG freshness rule so the index cannot silently freeze again. Optionally index pompts_11 titles only (prompts are historical artifacts; full-text may add noise).
2. **Enforce consult-before-act in the agent bootstrap.** bootstrap.py already restores context; add one step that pulls top-3 relevant lessons/patterns via SemanticLayer.find_similar_patterns or knowledge_search for the session topic, and surfaces them in the resume block. No Orchestrator needed.
3. **Backfill the OM store.** Convert the 86 learning_events and the 102 CON-N lessons into knowledge_objects (kind=lesson/pattern) with links to their ADRs and components via MemoryStore.link_knowledge. This makes LearningLoop.analyze and find_similar_patterns actually return matches.
4. **Fuse event search into retrieval results.** The facade queries EventStore FTS alongside KnowledgeEngine and merges by score. No store merging.
5. **Defer pgvector.** Revisit only above roughly 10k docs or on measured semantic-quality failure.

## P. Final Verdict (choose one, A-E)

**B (minimal Retrieval API + enforced consult step), with no new storage and no new engine.** Options A ("nothing needed") is falsified by E2/E4/E5/E6/E12: the machinery exists but is stale, empty, or unreachable from the agent loop. Options C and D are unfalsifiable wins at this scale and are deferred with explicit triggers (corpus size, measured quality failure).

**Main rule honored:** the architecture above was stress-tested to be refuted, and it survived in minimal form. The system's problem is not missing machinery; it is an unenforced habit plus three data holes (stale index, empty OM store, absent LESSONS coverage).

## Q. Unknowns

- Whether the 86 learning_events carry enough structure for clean backfill (spot-checked schema, not all 86 rows).
- Whether GraphIndex was ever intended to be populated on index.db or on a separate DB (code supports both; no ADR found either way).
- Exact moment the repo-wide ***REMOVED*** corruption entered history (after v5.189.85's green run; exact commit not bisected).

---

*Report generated per pompts_11/118.md. Evidence-first; every claim above maps to a live file, DB, or code line checked on 2026-08-30.*
