# manifest.md — Blueprints v3 Pipeline Manifest

> **Проект:** tg-terminal-toolkit
> **LISA:** 4.86 (MEDIUM)
> **Дата старта:** 2026-07-27

---

## Pipeline State

```yaml
project: tg-terminal-toolkit
version: 1.0.0
status: in_progress
current_stage: decomposer
total_stages: 10
completed_stages: 4
```

## Stages

```yaml
stages:
  - id: explainer
    role: 02_explainer.md
    status: done
    output: doc/brief.md, doc/parsed_requirements.md

  - id: lisa
    role: 03_lisa_estimator.md
    status: done
    output: doc/lisa_report.md
    score: 4.86
    complexity: MEDIUM

  - id: risk
    role: 04_risk_manager.md
    status: done
    output: doc/risk_manager_report.md

  - id: architect
    role: 06_architect.md
    status: done
    output: doc/architect/report_v1.md

  - id: decomposer
    role: 05_decomposer.md
    status: pending
    output: bounded_contexts.md

  - id: developer
    role: 07_developer.md
    status: pending
    depends_on: [decomposer, architect***REMOVED***

  - id: tester
    role: 12_tester.md
    status: pending
    depends_on: [developer***REMOVED***

  - id: fixer
    role: 13_fixer.md
    status: pending
    depends_on: [tester***REMOVED***

  - id: acceptance
    role: 14_acceptance_agent.md
    status: pending
    depends_on: [fixer***REMOVED***

  - id: documenter
    role: 15_documenter.md
    status: pending
    depends_on: [acceptance***REMOVED***
```

## Context Snapshots

```yaml
context:
  last_checkpoint: null
  compression_count: 0
```
