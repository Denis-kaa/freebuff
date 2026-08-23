# ADR-005 — Deterministic matcher and intent gate (P5)

> **Статус:** Accepted
> **Дата:** 2026-08-23
> **Связано:** `MATCHING_ENGINE.md`, `ROADMAP.md` P5, `decisions/DECISIONS.md`

## Контекст

P3 зафиксировал контракт `SearchProfile` (required/optional/synonyms/
excluded/intent terms + thresholds) и `MatchDecision` (explainable, с
`rules_snapshot`). Для P5 нужно выбрать, как именно сопоставлять текст
публикации с профилем, не прибегая к LLM и не утверждая live source.

## Решение

1. **Детерминированный rule-based matcher** (`app/matcher/engine.py`):
   термальные правила, префиксный word-form доступ (>= 4 символа), точные
   фразы скользящим окном, пороги из профиля.
2. **Жёсткие отказы со score 0:** excluded term match, missing required term,
   offer-wording без intent-сигнала, пустой профиль.
3. **Intent gate:** если в тексте есть offer-маркеры (`OFFER_MARKERS`) и нет
   совпавших `intent_terms` — REJECT. Это различает «ищет услугу» и
   «предлагает услугу» без внешних классификаторов.
4. **Score:** среднее по ratio присутствующих компонентов (required/optional/
   synonyms) × 0.9 + 0.1 за intent, cap 1.0. Формула воспроизводима и
   документирована; stopwords в optional не участвуют в знаменателе.
5. **Каждый decision** несёт `profile_version`, `rules_snapshot`,
   matched/rejected terms и строковые reasons.

## Альтернативы

- **LLM scoring:** сильнее и гибче, но недетерминирован, дорог и требует
  отдельного допустимого основания для обработки контента. Отложен до
  evidence-фазы P14.
- **Полный stemming/морфология (pymorphy/stemmer):** выше точность форм, но
  новая зависимость и больше поверхность для дефектов; префикс-доступ покрывает
  основные инварианты MVP и остаётся заменяемым.
- **Numeric keyword scoring без жёстких правил:** проще, но не объясняет why
  и не различает спрос/предложение.

## Последствия

- P4-публикации можно сразу прогонять через matcher на fixtures;
- пороги и словари остаются в профиле (`SearchProfile`) и не зашиты в matcher;
- calibration на реальных данных — задача P10/P14;
- G2 (approved live source) не затрагивается: matcher работает offline.