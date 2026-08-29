# Localization v0.1 — English source and Russian learner projection

> Current state: extraction/status workflow and optional Gemini draft provider with a three-key failover pool are implemented; drafts are not published automatically.

## Current language state

The approved Exercism Python clone is the canonical English source. The project
itself contains Russian engineering documentation, but the learner-facing
Exercism corpus is not translated yet.

The deterministic extractor currently finds **432 learner-facing Markdown
documents** and approximately **1,022,490 characters** in the pinned clone.
Included files are `instructions.md`, `introduction.md`, `hints.md`, and
concept `about.md` documents below `exercises/` or `concepts/`. Code, tests,
reference solutions, metadata and license evidence remain English/source data.

The count is generated, not hand-authored:

```bash
python3 -m app localize scan \
  --source data/exercism_src \
  --manifest data/localization/source_manifest.json \
  --target-locale ru
```

## Projection layout

The English clone remains untouched. Russian reviewed files are written under a separate
locale root with the same relative paths; provider drafts use a separate ignored root:

```text
data/localization/
  source_manifest.json
  drafts/ru/        # ignored provider output (*.draft.md + *.draft.json)
  ru/               # reviewed projection only
    concepts/.../*.md
    exercises/.../*.md
    *.source_hash
    *.provenance.json
```

`source_manifest.json` records `document_id`, relative path, content kind and
SHA-256 source hash. A Russian file is current only when its `.source_hash`
sidecar equals the current English source hash.

## Status and update workflow

```bash
# Rebuild the English source manifest after an upstream refresh.
python3 -m app localize scan

# Show missing, reviewed and stale Russian documents.
python3 -m app localize status

# Fail-closed provider boundary (no credentials required).
python3 -m app localize update --provider external_llm

# Use the local three-key Gemini pool; default is one draft, never publication.
python3 -m app localize update --provider gemini --limit 1
# Explicit form:
python3 -m app localize update --provider gemini \\
  --keys /storage/emulated/0/PROJECTS/workstation/freebuff/.keys/gemini_active.keys \\
  --model gemini-2.5-flash --limit 1
```

The intended update cycle is:

1. Refresh/pin the approved upstream clone and rerun the license/change audit.
2. Run `localize scan`.
3. Run `localize status` and select missing/stale documents.
4. Ask the configured external LLM provider for `TranslationDraft` objects; Gemini rotates the local key pool on retryable API failures.
5. Validate Markdown structure and source hash; invalid drafts remain drafts with validation errors in metadata. A current draft is not regenerated on repeat runs; upstream hash drift permits regeneration.
6. Review the draft and publish only `reviewed` translations.
7. Store source-hash and provider/model provenance sidecars.

## Translation boundary

LLM is optional and external. It may draft translations, but it may not:

- overwrite the English source;
- change exercise IDs, code, tests or reference solutions;
- change license/provenance evidence;
- mutate curriculum, evidence, competency state or grading rules;
- publish directly without review.

Publication validates code fences, inline-code tokens, Markdown link targets and
heading structure. Changed upstream content becomes `stale`; it is never
silently overwritten with an old translation.

See [ADR-006***REMOVED***(../decisions/ADR-006_localization_and_llm_content_updates.md)
and [prompt_localization.md***REMOVED***(../prompt_localization.md).
