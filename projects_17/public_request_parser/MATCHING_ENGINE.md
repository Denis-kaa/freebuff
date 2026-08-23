# MATCHING_ENGINE — P5

> **Статус:** implemented locally, deterministic
> **Версия:** 0.1.0
> **Ограничение:** детерминированный rule-based matcher; LLM/scoring модели не используются.

## Назначение

P5 сопоставляет нормализованные `Publication` с версионированными `SearchProfile`
и возвращает explainable `MatchDecision`: outcome (`accept`/`pending`/`reject`),
score 0..1, matched/rejected terms, reasons и snapshot правил профиля.

Matcher не выполняет сетевых операций, не импортирует платформенный код и
полностью воспроизводим: одинаковый профиль + публикация + `decided_at` дают
одинаковый decision.

## API

### `RuleMatcher`

```python
matcher = RuleMatcher(profile)          # profile: SearchProfile
decision = matcher.match(publication)   # -> MatchDecision
decision = matcher.match(publication, decided_at=when)  # детерминированные тесты
```

### Вспомогательные функции

- `normalize_text(value)` — lowercase + схлопывание пробелов;
- `tokenize(value)` — токенизация с поддержкой кириллицы;
- `is_stopword(term)` — проверка служебного слова;
- `STOPWORDS` / `OFFER_MARKERS` — константы, используемые в scoring/gate.

## Правила сопоставления

### Термины и word forms

- **Слово:** совпадение токена с термином или префиксный доступ для терминов
  длины >= 4 символов (`юрист` → `юриста`, `юристов`). Короткие термины (`go`)
  совпадают только точно, чтобы не давать ложных срабатываний.
- **Фраза:** точное скользящее окно по токенам; `data engineer` не совпадает
  с `data analysis for engineers`.

### Категории правил

| Категория | Поведение |
|---|---|
| `required_terms` | Должны совпасть все. Отсутствие любого — жёсткий `REJECT`, score 0. |
| `optional_terms` | Влияют на score; stopwords из этой группы игнорируются с reason. |
| `synonyms` | Совпадение любого алиаса засчитывает canonical; если canonical в required/optional — он считается совпавшим. |
| `excluded_terms` | Любое совпадение — жёсткий `REJECT` (сильнее required). |
| `intent_terms` | Demand-сигнал («ищу», «нужен», «требуется»); +0.1 к score. |

### Intent gate (спрос vs предложение)

Если в тексте обнаружены offer-маркеры (`предлага`, `оказыва`, `помог`,
`выполн`, `сделаю`, `прода`, `предостав`, `готов `/`готова `) и **нет** ни одного
совпавшего intent-термина — жёсткий `REJECT` с reason
`offer wording detected without intent signal`. Это отличает «ищет услугу»
от «предлагает услугу». Ambiguous-случай (offer + intent) не отклоняется.

## Формула score (детерминированная)

Для каждого присутствующего в профиле компонента считается ratio 0..1:

- required: `matched / total`;
- optional: `matched / total` (стоп-слова исключены из знаменателя);
- synonyms: `matched групп / всего групп`.

`score = min(1.0, mean(компоненты) * 0.9 + (0.1 если intent matched))`.

Решение: `score >= accept_threshold` → `ACCEPT`; `score >= pending_threshold` →
`PENDING`; иначе `REJECT`. Жёсткие отказы (exclusion, missing required,
offer-without-intent, пустой профиль) всегда возвращают score 0.

## Explainability

Каждый decision содержит:

- `profile_version` и `rules_snapshot` (неизменяемый снимок правил профиля);
- `matched_terms`, `matched_synonyms`, `rejected_terms`;
- `reasons` строки с человекочитаемым объяснением каждого шага;
- `publication_key`, `score`, `decided_at`.

ACCEPT никогда не возвращается без reasons (инвариант контракта P3).

## Fixtures и тесты

`tests/test_matcher.py` — 14 hermetic tests:

- нормализация и stopwords;
- required accept + explainability;
- missing required → hard reject;
- excluded → hard reject;
- синонимальная алия удовлетворяет required;
- частичное optional → PENDING;
- offer без intent → REJECT;
- intent boost меняет score и outcome;
- границы фраз (нет ложных совпадений);
- word forms и безопасность коротких терминов;
- stopword-optional не загрязняет score;
- пустой профиль → REJECT с причиной;
- детерминизм прогона;
- константа `OFFER_MARKERS` документирована.

## Проверки

```bash
cd projects_17/public_request_parser
PYTHONPATH=. python -m pytest tests/test_matcher.py -q
python -m mypy app tests --strict
```

## Не закрыто P5

- SQLite checkpoint/storage связь (P6);
- калибровка порогов на реальных данных (P10/P14);
- расширенная морфология / полноценный stemming (optional, P14);
- per-profile feedback calibration (P14);
- G2: production `allowed` source remains open.