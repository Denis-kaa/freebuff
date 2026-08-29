# Localization Contract v0.1 — English source, Russian projection, optional LLM updates

## Goal

Provide a learner-facing Russian locale for approved Exercism content without
replacing the canonical English upstream or weakening provenance and update
safety.

## Scope

Translate and version learner-facing Markdown only:

- exercise `instructions.md`, `introduction.md`, `hints.md`;
- concept `about.md`, `introduction.md`;
- later, learner-facing `blurb` and curriculum text through the same locale contract.

Do not translate or mutate Python code, tests, reference solutions, source
metadata, license evidence, hashes, or exercise identifiers.

## Contracts

```text
English upstream clone
  -> deterministic extractor
  -> source manifest (document_id, path, content_kind, source_hash)
  -> translation provider (optional external LLM or human)
  -> TranslationDraft
  -> structural/hash validation
  -> reviewed publication to locale projection
```

A translation is current only when its sidecar source hash equals the current
English source hash. Upstream changes produce `stale`, never silent overwrite.

## LLM boundary

The deterministic core does not call an LLM. A provider implements
`TranslationProvider.translate()` and returns drafts only. The provider must
carry provider/model provenance. It cannot publish files, alter curriculum,
create evidence, update competency state, or change grading rules.

The publication boundary requires explicit reviewed status and validates:

- source document identity and source hash;
- code fences;
- inline-code tokens;
- Markdown link targets;
- heading structure.

## Update policy

1. `localize scan` records the current English source manifest.
2. `localize status` identifies missing, reviewed, and stale Russian documents.
3. An external provider generates drafts only for missing/stale documents.
4. Drafts are validated and reviewed.
5. Only reviewed drafts are published with source-hash and provider provenance sidecars.
6. The next scan after an upstream update marks affected translations stale.

No automatic live update is allowed merely because an LLM returned text.
