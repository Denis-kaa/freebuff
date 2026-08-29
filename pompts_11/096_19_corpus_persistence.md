# pompts_11/096_19_corpus_persistence.md
## Corpus Persistence — Persistent URL corpus for research_* tools

**Версия:** 1.0 · **Дата:** 2026-08-20 · **Зарегистрирован:** `corpus_persistence` (kind=tool, factory=nil, status=implemented v5.189.54)

---

## Цель

Реализовать **persistent URL corpus** для research-задач: чтобы `research_web`,
`research_factory`, `capability_gap_auditor` могли **сохранять URL между
сессиями** и не терять уже найденные источники при перезапуске runtime.

**AGENTS.md §5 REGISTER-FIRST:** зарегистрирован в `core_02/missing_registry`,
lifecycle: registered → prompt_written → implemented (этот промт — реализация).

**Аддитивность (CAN-16):** модуль НЕ переписывает существующие
`scripts_01/research_web.py` / `scripts_01/opportunity_engine.py` — только
добавляет новый tool, который они могут вызывать когда будут готовы (см. §H
дизайн-валидации).

---

## 1. Семантика хранения (canonical)

Per-(url, source) **idempotent** (Option C из дизайн-валидации):

- Файл: `data_13/corpus/<sha256(url.encode('utf-8'))>.jsonl`
- Одна строка = один record (JSON).
- Для одного URL можно иметь несколько строк (разные `source`).
- Вызов `persist(url, source)` с тем же `(url, source)` ПЕРЕЗАПИСЫВАЕТ
  существующую строку (атомарная write-temp-then-rename).
- Вызов с новым `source` для уже-сохранённого URL ДОБАВЛЯЕТ новую строку.

Жизненный цикл record: `persist() → файл → lookup() / lookup_by_source() /
list_all() / stats()`. Append-only на уровне источника, last-write-wins на
уровне (url, source).

---

## 2. Schema record

```json
{
  "url": "https://example.com/article",
  "source": "research_web",
  "timestamp": "2026-08-20T12:00:00Z",
  "title": "Article title (optional)",
  "metadata": {"status": 200, "lang": "en"***REMOVED***
***REMOVED***
```

Поля:
- `url` (str, required): валидный http(s) URL
- `source` (str, required): имя источника (`research_web`, `manual`,
  `research_factory`, etc.)
- `timestamp` (str, required): ISO 8601 UTC, всегда с суффиксом `Z`
- `title` (str | null, optional)
- `metadata` (dict[str, Any***REMOVED***, default `{***REMOVED***`)

Robustness: парсинг должен быть `from_dict(...)` устойчив к лишним ключам
(паттерн `MissingItem.from_dict`).

---

## 3. Филенaming + безопасность

- Filename = `<sha256_hex>` (64 hex chars). Никаких user-controlled paths
  → path-traversal исключён по построению.
- Reject `file://`, `javascript:`, `data:`, прочие не-http(s) URL (security
  per design risk).
- Hardcap `len(url) ≤ MAX_URL_LEN = 2048` (DoS protection per design risk #3).

---

## 4. Concurrency / Atomicity

- `threading.Lock` на module level + append mode (per option C semantics):
  каждый `persist()` берёт lock → читает существующий JSONL → удаляет старую
  запись для этого `source` (если есть) → пишет новую запись → отпускает lock.
- Атомарность записи: write-temp-then-rename + `os.fsync` (per LisaEstimator
  style). На ошибке tmp удаляется.
- Корректность при corrupt jsonl: `_read_jsonl_safely()` пропускает битые
  строки с `sys.stderr` warning (не роняет lookup).

---

## 5. API (canonical)

```python
from scripts_01.corpus_persistence import (
    CorpusEntry, PersistResult,
    persist, lookup, lookup_by_source, list_all, stats,
)

@dataclass
class CorpusEntry:
    url: str
    source: str
    timestamp: str
    title: str | None = None
    metadata: dict = field(default_factory=dict)

@dataclass
class PersistResult:
    entry: CorpusEntry
    is_duplicate: bool  # True если существующая (url, source) перезаписана

def persist(url: str, source: str, *, title: str | None = None,
            metadata: dict | None = None) -> PersistResult: ...
def lookup(url: str) -> list[CorpusEntry***REMOVED***: ...
def lookup_by_source(source: str) -> list[CorpusEntry***REMOVED***: ...
def list_all() -> list[CorpusEntry***REMOVED***: ...
def stats() -> dict[str, int***REMOVED***: ...   # {source: count***REMOVED***
```

---

## 6. CLI (python -m scripts_01.corpus_persistence)

```bash
# Add
python -m scripts_01.corpus_persistence add <URL> --source <SRC> [--title T***REMOVED*** [--metadata k=v ...***REMOVED*** [--json***REMOVED***

# Lookup by URL
python -m scripts_01.corpus_persistence lookup <URL> [--json***REMOVED***

# List (all or filter by source)
python -m scripts_01.corpus_persistence list [--source <S>***REMOVED*** [--json***REMOVED***

# Stats
python -m scripts_01.corpus_persistence stats [--json***REMOVED***

# Version (per CODE_QUALITY_STANDARD §9.5)
python -m scripts_01.corpus_persistence --version
```

Exit codes: 0 = OK, 1 = lookup/list внутренний сбой, 2 = usage/invalid URL.

---

## 7. Quality gates

- ✅ ROUND-2 tests (≥8): persist (new + idempotent overwrite), lookup (found,
  empty, validate reject), lookup_by_source, list_all, stats, corrupt jsonl
  recovery, CLI add/lookup/list/stats smoke.
- ✅ Atomic file write (tmp + fsync + rename).
- ✅ Thread-safety (FILE_LOCK контекст).
- ✅ mypy strict, 0 errors в new files.
- ✅ CODE_QUALITY_STANDARD §5.1 (Termux-compatible), §9.5 (--version), §4.7
  (no hardcoded paths).

---

## 8. Integration roadmap (out-of-scope для v1, first-slice cap)

- `scripts_01/research_web.py:254` — после `extract()` добавить
  `corpus_persistence.persist(src.url, "research_web", title=src.title)`.
- `core_02/capability_gap_auditor` — boot-time `lookup_by_source("research_web")`
  для injection в context агента.
- `scripts_01/research_factory.py` — чистая интеграция через registry.

Roadmap documented в `core_02/LESSONS.md` после имплементации.
