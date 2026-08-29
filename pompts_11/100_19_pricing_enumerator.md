# 100_19_pricing_enumerator.md — verified course pricing scraper (canonical промт)

> **Status:** 🏗 ПРОМТ НА РЕАЛИЗАЦИЮ (Missing Capability `pricing_enumerator`, registered в `data_13/missing_registry.yaml`)
> **Source:** `data_13/missing_registry.yaml` entry `pricing_enumerator` (kind=`tool`, factory=`research`, status=`registered`)
> **Lifecycle:** registered → **prompt_written** (этот файл) → `mark-implemented scripts_01/pricing_enumerator.py`

---

## 1. Цель

Скрапер **верифицированных** цен курсов (а не «примерно 10-20 тыс. ₽» из интервью).
Ключевая добавка: качество данных цены = **точная цифра с источника**, сохраняемая между сессиями в `corpus_persistence`.

## 2. Use case

`projects_17/vocal/задача.md` («цена курса как конкретная цифра, не диапазон»).
Pipeline: `pricing_enumerator.enumerate(urls)` → `List[CoursePrice***REMOVED***` JSON-ready + persisted в corpus.

## 3. Scope

**В scope:**
- Web-scrape одного URL → `ScrapeResult(data={course, price_raw, teacher, format?***REMOVED***, status)`.
- Простые HTML-парсеры: schema.org microdata (Course / Product) + fallback `<h1>` + `.price` CSS-class.
- Per-URL write через `corpus_persistence.persist()` (ADR-016 lazy import + try/except).
- Batch enumeration (≤1000 URLs per call) с survival-of-partial-failure.
- CLI `enumerate URL1 URL2 …` с `--json`, `--no-corpus`, `--source`, `--timeout`, `--root`.

**Out of scope:**
- Авторизация, JavaScript-only страницы (нет headless browser).
- Anti-bot bypass (нет прокси/captcha-resolver).
- Ценовые сравнения (downstream consumer задача).
- ML-извлечение из произвольных layouts (только schema.org + simple fallback).

## 4. Schema invariants

`CoursePrice`:
- Required: `course: str`, `price_raw: str` (verbatim), `source_url: str` (URL), `scrape_timestamp: str` (ISO 8601 UTC 'Z').
- Optional: `teacher`, `price_amount: Optional[float***REMOVED***`, `price_currency: Optional[str***REMOVED***`, `format: FormatType`.

`FormatType` enum: `RECORDED | COHORT | MICRO | LIVE | HYBRID | MEMBERSHIP | COMMUNITY | CHALLENGE | INTENSIVE | UNKNOWN`.

`ScrapeStatus` enum: `OK | HTTP_ERROR | PARSE_ERROR | MISSING_FIELDS`.

## 5. Cross-module contracts

| Module | Interface | Mirror pattern |
|--------|-----------|----------------|
| `scripts_01/corpus_persistence.py` | `persist(url, source, title, metadata)` | Per-URL atomic JSONL append |
| `scripts_01/research_web.py` | Scraper dataclass + `--no-corpus` + lazy import + ADR-016 try/except | Sibling pattern |
| `core_02/missing_registry.py` | lifecycle CLI: `mark-prompt-written` → `mark-implemented` | Register-first |

## 6. Test surface (10 hermetic + ADR-016)

1. `test_successful_scrape_yields_course_price` — happy path.
2. `test_missing_required_fields_warns_and_skips` — soft error.
3. `test_http_error_warns_and_skips` — soft error.
4. `test_parse_error_warns_and_skips` — soft error.
5. `test_network_unavailable_raises_fatal_exception` — hard error.
6. `test_valid_scrape_triggers_corpus_persist` — persistence integration.
7. `test_no_corpus_flag_bypasses_persistence` — `enabled=False`.
8. `test_corpus_exception_caught_safely_adr016` — fail-safe persist.
9. `test_batch_processing_survives_partial_failures` — partial survival.
10. `test_price_raw_preserved_when_amount_unparseable` — verbatim guarantee.
11. `test_invalid_url_summary_skipped_but_other_urls_continue` — input validation.

## 7. Closed decisions (validated 6/6, thinker v5.189.60)

| # | Decision | Implementation |
|---|----------|----------------|
| 1 | Verbatim `price_raw` + optional parsed numerics | `CoursePrice` has `price_raw + price_amount + price_currency` |
| 2 | ScraperProtocol for hermetic tests | `class ScraperProtocol(Protocol)` + `FakeScraper` |
| 3 | Per-URL persist + ADR-016 try/except | `_persist_to_corpus` lazy import + except |
| 4 | Write-forward append-only (WORM) | Each scrape = new event; consumer-side dedup |
| 5 | Soft errors skip-with-warn, network fatal → exception | 4 `ScrapeStatus` + 1 `PricingEnumeratorNetworkError` |
| 6 | CLI subcommand with positional `nargs='+'` | `enumerate URL1 URL2 ...` |

## 8. Quality gates (must pass before close)

- [ ***REMOVED*** `python -c "import ast; ast.parse(...)"` clean (syntax).
- [ ***REMOVED*** `python -m pytest tests_09/test_pricing_enumerator.py -v` — ≥10 passed.
- [ ***REMOVED*** `python -m mypy scripts_01/pricing_enumerator.py --ignore-missing-imports` — 0 errors.
- [ ***REMOVED*** `python -m core_02.missing_registry check` — exit 0 (46 entries).
- [ ***REMOVED*** `python -m core_02.missing_registry mark-implemented pricing_enumerator --implementation scripts_01/pricing_enumerator.py` — closes lifecycle.
- [ ***REMOVED*** code-reviewer-minimax-m3 — "Production-ready: yes".

## 9. Diff summary (target manifests)

- `scripts_01/pricing_enumerator.py` — NEW (~280 LOC).
- `tests_09/test_pricing_enumerator.py` — NEW (~200 LOC, 10 tests).
- `data_13/missing_registry.yaml` — `pricing_enumerator` lifecycle CLOSED (status=`implemented`, implementation=`scripts_01/pricing_enumerator.py`).
- `CHANGELOG.md` — v5.189.60 entry prepended (str_replace-only per v5.184.0 wipe lesson).
