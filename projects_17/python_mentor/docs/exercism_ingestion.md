# Exercism Ingestion — операционное руководство (python_mentor)

> **Версия:** 0.1.0 · **Дата:** 2026-08-23 · **Фаза:** B+C (Шаги 2, 5–8) · prompt1 §24–§30

## 1. Получение источника (однократно)

```bash
git clone --depth 1 https://github.com/exercism/python data/exercism_src
```

- Коммит фиксируется (сейчас `1f6aab8…`); аудит лицензий — `docs/exercism_research.md` §3.
- При изменении upstream: обновляем клон, сравниваем commit; при изменении **повторяем license audit** (правило change→update, Шаг 6).
- Клон и corpus — вне git (`.gitignore` проекта).

## 2. Первый импорт

```bash
python3 -m app ingest exercism --dry-run
# ожидаемо: discovered=161, parsed=161, approved_live=161, errors=0

python3 -m app ingest exercism            # создаст data/corpus/corpus_v0.1.db
python3 -m app ingest exercism --report   # тот же импорт + отчёты
```

Флаги:
| Флаг | Значение |
|---|---|
| `--source DIR` | другой source-клона (полезно для тестов с фикстурами) |
| `--db PATH` | путь к corpus (по умолчанию в `data/corpus/`) |
| `--dry-run` | ничего не пишет, показывает счётчики |
| `--with-refs` | импортировать reference solutions (`example.py`/`exemplar.py`) |
| `--report` | после импорта вывести coverage/gaps/low-confidence/license |

## 3. Отчёты

```bash
python3 -m app report coverage            # по компетенциям: n/concept/practice/difficulty
python3 -m app report gaps                # компетенции с 0–1 упражнением, rung-пробелы
python3 -m app report low-confidence      # упражнения с low/medium маппингом — для ревью
python3 -m app report license             # статус источников (approved/pending/rejected)
```

**Как читать gap-отчёт:** v0.1 честно показывает, что 13 компетенций покрыты слабо (0–1 упражнение). Это НЕ баг пайплайна — сигнал для Phase D+ (второй источник после license gate, дополнение контента).

## 4. Как добавить override (ручной маппинг)

1. Открыть `configs/exercise_overrides.yaml`;
2. Добавить запись:
   ```yaml
   - exercise_id: my-exercise
     competency_id: functions
     confidence: high        # high — ручное подтверждение; low — попадает в low-confidence-ревью
   ```
3. `python3 -m app ingest exercism` — override применится идемпотентно.

Правила: один override на упражнение (двойной — ошибка); ссылка на несуществующую компетенцию — ошибка.

## 5. Как одобрить новый источник

1. Research + **пофайловый license audit** (как для exercism: `docs/exercism_research.md`);
2. Запись в `configs/sources.yaml` со `status: approved` и НЕПУСТЫМ `license_evidence`;
3. `ingest` применит реестр (upsert); pending/rejected упражнения не попадут в corpus.

## 6. Hermetic/тесты

```bash
python3 -m pytest tests/ -q                     # 37 unit (без сети, на фикстурах)
python3 -m pytest tests/ -q -m integration      # canary на реальном клоне
```

Unit-сюит не использует сеть и не требует клона (fixture-мини-трек в `tests/fixtures/exercism/`).

## 7. Ограничения

- Runtime офлайн: ingestion читает только локальный клон (`--source`), никаких API;
- Контент хранится локально (approved) — в SQLite сохраняются пути/метаданные/hash, не содержимое файлов (S0-6);
- Reference solutions — только с `--with-refs` (S0-7);
- foregone (3 упражнения) не импортируются никогда.

## Cross-links

- `PHASE_BC_PLAN.md` · `docs/exercism_research.md` · `docs/curriculum_v0.1.md`
- `configs/sources.yaml` (реестр источников) · `configs/exercise_overrides.yaml`
- Код: `app/ingestion/{parser,pipeline,license,mapping,reports***REMOVED***.py`, `app/__main__.py`