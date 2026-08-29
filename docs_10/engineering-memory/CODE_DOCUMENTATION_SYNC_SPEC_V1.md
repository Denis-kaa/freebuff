# CODE-DOCUMENTATION SYNC SPEC (Artifact J — Phase J Specification)

> **Source of Truth:** repository (Freebuff / Workspace OS codebase, 2026-08-12).
> **Conforms to:** `projects_17/content_factory/promts/4.md` §17 (ДОКУМЕНТАЦИЯ ДОЛЖНА СТАТЬ ЖИВОЙ — document claim → anchor → code symbol → verification), §19-J (CODE_DOCUMENTATION_SYNC_SPEC.md), §20 PHASE G (Consistency validation).
> **Anchor inheritance:** this is **the spec of the spec** — it defines the operational CI rules that consume the 19-namespace anchor system of Artifact I `SEMANTIC_ANCHOR_SPEC_V1.md` and the §A code map of Artifact A `PLATFORM_CODE_MAP_V1.md`.
> **REPOSITORY = SOURCE OF TRUTH:** механизм УЖЕ реализован как код — `core_02/doc_code_verify.py` (register-first cycle closed, Missing Capability `doc_code_verify`, 30 тестов). Эта спека — нормативное описание работающего механизма, НЕ проектный документ «на будущее».
> **Counterparts required:** Artifact I (anchor namespaces/regex), Artifact A (§A code map), Artifact H (consistency report = выход), `scripts_01/consistency_check.py` (Stage 9 — старший sibling).

---

## §J.1 — Purpose

Спека задаёт **операционные правила живой документации**: каждый `@entity`/`@contract`/`@symbol`/`@test`/`@event`-анкор в `docs_10/engineering-memory/*.md` должен резолвиться до конкретного кода (file::symbol, AST-подтверждённого, без импорта) либо классифицироваться как STALE / DOC_ONLY. Цель — исключить вопрос «что автор документа имел в виду?»: анкор → код → проверяемый ответ.

---

## §J.2 — Normative contract (что реализует `core_02/doc_code_verify.py`)

### J.2.1 — Пайплайн (5 шагов)

| Шаг | Функция | Вход → Выход | Правило |
|-----|---------|--------------|---------|
| 1 | `extract_claims(doc)` | `.md` файл → `list[Claim***REMOVED***` | Regex `@(entity\|contract\|symbol\|test\|event\|module\|component) <target>`; **пропускает code fences** (```...```); отсутствующий/битый файл → `[***REMOVED***` |
| 2 | `load_code_map(workspace)` | `PLATFORM_CODE_MAP_V1.md §A` → `dict[entity_id***REMOVED*** -> {type, file, symbol***REMOVED***` | State machine по секциям `### @entity <id>` + bullets `- **type/file/symbol/public_api:**`; first-wins на дубли (ANTI-6b) |
| 3 | `check_symbol_exists(workspace, file, symbol)` | `file_rel::symbol` → bool | **AST-парсинг** (`ast.parse`), без `import`; поддерживает `Class.method`; отсутствующий файл / SyntaxError → False |
| 4 | `verify_claim(claim, code_map, workspace)` | Claim → `VerificationResult` | Классификация: CONFIRMED / STALE / DOC_ONLY / UNKNOWN |
| 5 | `run_verification(target, workspace, strict)` | путь (файл/дир) → JSON-агрегат | Считает по классификациям; `strict=True` → exit 1 при любом STALE/DOC_ONLY |

### J.2.2 — Classification semantics (закрытое множество, ANTI-6b)

| Класс | Условие | Смысл промт-4 |
|-------|---------|---------------|
| `CONFIRMED` | анкор в Map §A + file::symbol AST-подтверждён | «код реализует утверждение» |
| `STALE` | анкор в Map, но файл/символ отсутствует (или запись без file/symbol) | «symbol исчез → STALE» (§17) |
| `DOC_ONLY` | анкор в доке, но отсутствует в Map §A | «документ описывает неизвестный код» |
| `UNKNOWN` | классификация не удалась (catch-all, defensive) | fail-safe, никогда не fallthrough в CURRENT |

**Анти-галлюцинация:** если разрешение невозможно по любой причине → `UNKNOWN`, никогда не «CONFIRMED по умолчанию» (зеркалит §I.5 Artifact I).

### J.2.3 — CLI contract

```bash
python -m core_02.doc_code_verify docs_10/engineering-memory/PLATFORM_CODE_MAP_V1.md   # файл
python -m core_02.doc_code_verify docs_10/engineering-memory/ --json                   # все *.md, JSON
python -m core_02.doc_code_verify docs_10/engineering-memory/ --strict                 # exit 1 при STALE/DOC_ONLY
python -m core_02.doc_code_verify <path> --workspace <root>                            # workspace override
```

Exit codes: `0` — ок (или WARN без strict) · `1` — strict: найдены STALE/DOC_ONLY · `2` — target/error.

Scope-правило: обрабатываются только файлы с `engineering-memory` в пути (не весь репозиторий).

---

## §J.3 — Status integration (как статусы живут)

| Класс verifier | Статус Artifact A (§A.6) | Действие в живом цикле |
|----------------|--------------------------|------------------------|
| CONFIRMED | CURRENT | ок; анкор остаётся валидным |
| STALE | STALE | пометить; чинить (код или Map) |
| DOC_ONLY | CODE_ONLY / DESIGN_ONLY | добавить в Map §A (если код есть) или в MissingRegistry (register-first) |
| UNKNOWN | UNVERIFIED | диагностика; не молчать |

Жизненный цикл живого документа (промт-4 §17):

```
document claim → anchor → code symbol → verification
   ├── symbol исчез                 → STALE
   ├── implementation изменился     → REVIEW_REQUIRED
   └── документ противоречит коду   → CONTRADICTION
```

---

## §J.4 — CI integration (место в конвейере качества)

```
repo change (commit/push)
    ↓
scripts_01/drift_check.py        (link checker + структура)        — существующий CI
scripts_01/consistency_check.py  (Stage 9: реестры как данные)     — существующий CI
core_02/doc_code_verify.py       (анкоры → код, WARN по умолчанию) — Artifact J
    └── --strict → exit 1 на STALE/DOC_ONLY (gate в pre-merge)
```

**Режим по умолчанию: WARN** (exit 0, findings в stdout/JSON) — не блокирует разработку, но делает drift видимым. **`--strict` — опциональный gate** для ревью/merge. Это осознанное решение: жёсткий gate на всю docs_10/engineering-memory сразу заблокирует 100% мерджей (анкоры добавляются артефакт за артефактом).

---

## §J.5 — Extension path (что дальше, НЕ в scope текущего кода)

| Возможность | Статус | Связь |
|-------------|--------|-------|
| `@module`/`@component` резолвер (сейчас в ANCHOR_RE, но verify_claim работает по `@entity`) | расширение | §I.3 AnchorResolver |
| `@event` → `event_bus.py` registered_events cross-check | расширение | §I.7 anti-hallucination #3 |
| AnchorsResolver (`core_02/anchors_resolver.py`) — полный 19-namespace резолвер | DESIGN_ONLY | Artifact I §I.3 (планируется) |
| Hook в `consistency_check.py` как check #11 | предложение | через `--strict` |

---

*Artifact J closed. Механизм реализован и проверен: `core_02/doc_code_verify.py` + `tests_09/test_doc_code_verify.py` (30 тестов) + register-first `doc_code_verify` (status=prompt_written, промт `pompts_11/082_19_doc_code_sync.md` — канон v5.189.3). Эта спека — нормативное описание: classification §J.2.2, CLI §J.2.3, CI §J.4. Связано: Artifact A, I, H; `consistency_check.py`.*
