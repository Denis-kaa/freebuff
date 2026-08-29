# PHASE9 Traceability — Capability → Factory → Registry → Forge (§16)

**Domain-neutral contract verified across THREE clients in Phase 11.**

## Path 1 — Capability `article_generation` (CONTENT DOMAIN — production)

```
Capability `article_generation`
  → runtime_05/factories/content/factory.yaml    (factory_id=content)
  → runtime_05/factories/content/writing.yaml   (forge_id=writing)
  → core_02/factory_registry.py::FactoryRegistry.select_forge("article_generation")
  → scripts_01/content_factory.py::ContentFactory.resolve()
  → core_02/forge_facade.py::ForgeFacade.run_chain(project, role_ids=CONTENT_ROLE_IDS, project_read_only=True)
  → artifact: content_report
  → MemoryStore(kind=candidate, tag=content_factory)
```

## Path 2 — Capability `research` (RESEARCH DOMAIN — production)

```
Capability `research`
  → runtime_05/factories/research/factory.yaml    (factory_id=research)
  → runtime_05/factories/research/analysis.yaml   (forge_id=analysis)
  → core_02/factory_registry.py::FactoryRegistry.select_forge("research")
  → scripts_01/research_factory.py::ResearchFactory.resolve()
  → core_02/forge_facade.py::ForgeFacade.run_chain(project, role_ids=RESEARCH_ROLE_IDS, project_read_only=True)
  → artifact: research_report
  → MemoryStore(kind=candidate, tag=research_factory)
```

## Path 3 — Capability `code` (TEST DOMAIN — material, NOT PRODUCTION per §11 Variant B)

```
Capability `code`
  → runtime_05/factories/test/factory.yaml   (factory_id=test)
  → runtime_05/factories/test/verifier.yaml  (forge_id=verifier)
  → core_02/factory_registry.py::FactoryRegistry.select_forge("code")
  → scripts_01/test_factory.py::TestFactory.resolve()
  → core_02/forge_facade.py::ForgeFacade.run_chain(project, role_ids=TEST_ROLE_IDS, project_read_only=True)
  → artifact: verifier_report
  → MemoryStore(kind=candidate, tag=test_factory)
```

## Universal Boundary Proof (test_15 META-TEST)

ONE `FactoryRegistry(runtime_05/factories/)` resolves ALL THREE capability tokens (article_generation, research, code) → 3 distinct factory_ids (`content`, `research`, `test`) with ZERO edits to FactoryRegistry or ForgeFacade code.

**CAN-16 ADDITIVE invariant preserved:** No upstream module modifications — only NEW capability nodes inserted under `runtime_05/factories/`.
