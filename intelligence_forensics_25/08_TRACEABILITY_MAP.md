# 08 — TRACEABILITY MAP

> Исследование существующего механизма anchors/tags/traceability (промт §20–§21).

## T1. Существующее состояние

**FACT:** Механизм traceability УЖЕ существует и работает:
- `core_02/anchors_resolver.py::AnchorResolver` — резолвер семантических анкоров (в коде `ANCHOR_RE` = 17 @-namespace паттернов + `doc.*` extension; термин «19» из spec §I.3 — известный counting-drift, см. 07 D-4).
- `core_02/doc_code_verify.py` — верификация doc↔code (mark-implemented в MissingRegistry).
- `scripts_01/consistency_check.py` check #11 (ANCHORS) — CI-интеграция.

## T2. AnchorResolver namespaces (17 @-patterns + doc.* extension)

| Namespace | Regex | Резолв-цель | Статус при отсутствии |
|-----------|-------|-------------|----------------------|
| `@entity` | `[a-z***REMOVED***[a-z0-9_***REMOVED****(\.[a-z***REMOVED***[a-z0-9_***REMOVED****)+` | Artifact A → module-file → MissingRegistry | UNVERIFIED |
| `@component` | … | parent @entity | UNVERIFIED |
| `@module` | … | scripts_01/core_02/freebuff_plugin_03/<name>.py | UNVERIFIED |
| `@symbol` | `[A-Z***REMOVED***[A-Za-z0-9_***REMOVED***+(\.[a-zA-Z_***REMOVED***\w*)+` | AST class/method lookup | **STALE** (§I.7) |
| `@contract` | … | CONTRACT_REGISTRY_V1.md | UNVERIFIED |
| `@event` | … | event_bus.py / Artifact A | UNVERIFIED |
| `@storage` | `[a-z***REMOVED***[a-z0-9_***REMOVED***+(_...)*` | data_13/<name>.{yaml,json,jsonl***REMOVED*** / shorthand | UNVERIFIED |
| `@test` | `test_[a-z***REMOVED***\w*` | tests_09/<name>.py / AST | UNVERIFIED |
| `@decision` | `ADR_\d{3***REMOVED***` | docs_10/**/decisions/ADR_NNN_*.md | UNVERIFIED |
| `@requirement` | `REQ-…` | REQ_REGISTRY_V1.md | DESIGN_ONLY |
| `@scenario` | … | runtime_05/scenarios/<name>.yaml | DESIGN_ONLY |
| `@factory` | `[a-z***REMOVED***\w*_factory` | CANONICAL_FACTORIES enum | UNVERIFIED |
| `@forge` | `forge_[a-z***REMOVED***\w*` | CANONICAL_FORGES enum | UNVERIFIED |
| `@opportunity` | `opp-[a-z0-9***REMOVED***+` | data_13/opportunities.yaml | UNVERIFIED |
| `@whim` | `whim-[a-z0-9***REMOVED***+` | data_13/whims.yaml | UNVERIFIED |
| `@lesson` | `(CON\|ANTI\|CAN\|R)[-_***REMOVED***\d{1,3***REMOVED***[a-z***REMOVED***?` | core_02/LESSONS.md | UNVERIFIED |
| `doc.*` | `doc.<name>#<section>[.cN***REMOVED***` | DOCUMENTATION_CODE_MAP_V1.md | UNVERIFIED |

## T3. Статусная таксономия (§I.5)

`CURRENT` (резолвится) · `LESSON` (в LESSONS.md) · `DESIGN_ONLY` (planned namespace) · `UNVERIFIED` (не резолвится, флагуется CI) · `STALE` (@symbol class absent).

## T4. Оценка промт §20–§21

**FACT:** Промт §20 («если механизм anchors/tags существует — исследовать его») — **механизм существует и покрывает цепочку DOCUMENT→SECTION→ANCHOR→CODE SYMBOL→TEST**.
**FACT:** `@opportunity`/`@whim` уже резолвятся к YAML-stores → Intelligence TRACE/PROVENANCE готов.
**FACT:** Промт §21 (семантические теги `@concept/@contract/@decision/@requirement/@implementation/@evidence/@invariant/@gap/@runtime/@test`) — частично покрыт: `@contract/@decision/@requirement/@test/@lesson` существуют; `@concept/@implementation/@evidence/@invariant/@gap/@runtime` — НЕТ.

**DECISION (Tagging):**
- НЕ добавлять теги механически (промт §21 предупреждает о semantic noise).
- `@evidence/@runtime/@gap` — полезны для Intelligence PROVENANCE, но добавлять только как extension `_PLANNED_NAMESPACES` → DESIGN_ONLY (не флагует CI), когда появится потребитель.
- Формат уже каноничен (ANCHOR_RE + normalize + skip_fences). Связь с graph — через `@lesson` → LESSONS.md и `doc.*` → DOCUMENTATION_CODE_MAP.

## T5. Минимальный traceability-контракт (для отсутствующей части)

Промт §20 просит «если нет — предложить минимальную модель». Механизм есть, поэтому требуется только **минимальное расширение** (не внедрение):

```
DOCUMENT → SECTION → PARAGRAPH → ANCHOR(@ns value) → CODE SYMBOL / TEST → RUNTIME PATH
```

Единственный недостающий кусок — RUNTIME PATH (резолв «какой код исполняет этот абзац» уже есть через @symbol AST; runtime-path — через `@storage`/`@event` фактически). **INFERENCE:** контракт полон для Intelligence; ничего строить не нужно.
