# ADR-004 — License gate: approved/pending/rejected; unknown никогда → live

> **Статус:** 🟢 Accepted (2026-08-23)
> **Источник:** blueprint v0.1 §2/§11, prompt1 §11–§13, prompt.md Этап 0, prompt3 §8–9

## Context

Банк упражнений строится из внешних источников (Exercism, freeCodeCamp, Google Python Class, MIT 6.0001, Python Docs). Каждый источник имеет разные лицензии, а внутри источника — разные типы контента (условия, тесты, эталонные решения, support-файлы, metadata). Ошибка лицензирования = юридический риск навсегда.

## Options

1. «Скачать и использовать» — запрещено policy проекта (prompt.md: «что под закрытой лицензией — не трогать, даже если легко скачать»).
2. **Гейт на уровне каждой записи:** `exercise_source.status`: pending → license validation → approved/rejected; `approved` — только с license evidence; **никогда `unknown → live`**.
3. Принятие «по названию лицензии» без пофайлового audit.

## Decision

Принят вариант 2: ни одно упражнение не попадает в live corpus, пока `exercise_source.status != approved`; approval — ручной шаг с evidence (файл/лицензия/источник). Для Exercism — пофайловый audit реально импортируемых частей (подсказки/тесты/метаданные отдельно), без автоматического вывода «Exercism = MIT ⇒ всё можно». Reference solution — non-обязательный и импортируется только если разрешён; иначе — ссылка.

## Rationale

- Фундамент должен быть «качественным, воспроизводимым и юридически чистым» (prompt1 §40).
- Со временем corpus — юридическая база всей платформы; исправить после интеграции — дорого.
- Модель provenance + content_hash позволяет отслеживать upstream-изменения.

## Consequences

- В B+C: упражнения по умолчанию `pending`; после проверки — `approved` (с evidence) или `rejected`.
- Low confidence mapping — НЕ основание для auto-approve лицензии (разные вещи).
- gap-report может честно показывать «мало легального контента по компетенции X» — это фича, не скрываемый дефект (prompt.md Этап 0 п.4).

## Links

- [blueprint §2/§11***REMOVED***(../python_ai_tutor_blueprint_v0.1.md) · [prompt1 §11–§13/§16***REMOVED***(../prompt1.md) · [prompt3 §8–§9***REMOVED***(../prompt3.md) · [ROADMAP §3/§9***REMOVED***(../ROADMAP.md)