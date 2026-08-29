# Capability Gap Audit Report

> Сгенерировано `CapabilityGapAuditorExecutor` (ADR-016, deterministic v1).
> Вердикт основан на keyword/regex-матче секций задачи против курируемой таксономии.
> LLM-вариант (более точный вывод, дополнительная стоимость) — `CapabilityGapLlmExecutor`, следующая итерация.

**Всего секций проанализировано:** 69 [observation***REMOVED***
**Уникальных требуемых capabilities:** 7 [observation***REMOVED***
**Блокеров (first-slice):** 6 [observation***REMOVED***
**Режим registry:** injected (DI) [observation***REMOVED***

## 1. Сводная таблица

| Capability | В MissingRegistry? | Статус | kind | factory | Описание |
|------------|--------------------|--------|------|---------|----------|
| `anti_pattern_miner` | да | `registered` | `tool` | `research` | Anti-pattern mining (закрытые курсы/школы/заброшенные продукты) |
| `business_model_constructor` | да | `registered` | `module` | `doc` | Конструктор бизнес-моделей (14 полей, валидированный шаблон) |
| `devil_advocate_pass` | да | `registered` | `module` | `thinker` | Adversarial review (3 kill-questions в конце, anti-confirmation-bias) |
| `lisa_estimator` | да | `implemented` | `tool` | `research` | Estimation / Unit-economics для creator-economy (Teacher Time/$, калибровка) |
| `mvp_design_wizard` | да | `registered` | `module` | `doc` | MVP-механики (предпродажа, пилот, диагностическая воронка) |
| `pricing_enumerator` | да | `registered` | `tool` | `research` | Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») |
| `qualitative_review_analyzer` | да | `registered` | `tool` | `research` | Качественный анализ отзывов (pain-points / churn / praise кластеризация) |

## 2. Детализация по секциям

### Что уже продаётся на рынке — форматы, цены, программы, преподаватели, отзывы, результаты.
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***

### Есть ли вообще жизнеспособная модель именно для твоей подруги — учитывая её репутацию и аудиторию в StarMaker, но главны
- ⚠ `business_model_constructor` (kind=`module`, factory=`doc`) — Конструктор бизнес-моделей (14 полей, валидированный шаблон) → в реестре, статус отличен от implemented [registered***REMOVED***

### КОНТЕКСТ
- Не требует новой capability (preamble/quality/conf/Q&A).

### Пойдут ли люди вообще учиться к ней?
- Не требует новой capability (preamble/quality/conf/Q&A).

### Будет ли аудитория StarMaker готова платить?
- Не требует новой capability (preamble/quality/conf/Q&A).

### Какой формат обучения им нужен?
- Не требует новой capability (preamble/quality/conf/Q&A).

### Какая цена психологически приемлема?
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***

### Как избежать модели, где преподаватель получает деньги только за часы своего личного времени?
- Не требует новой capability (preamble/quality/conf/Q&A).

### Как избежать выгорания?
- Не требует новой capability (preamble/quality/conf/Q&A).

### Можно ли сделать продукт, который продаётся многим людям одновременно?
- Не требует новой capability (preamble/quality/conf/Q&A).

### Можно ли начать с небольшого MVP и проверить спрос до создания полноценной школы/курса?
- Не требует новой capability (preamble/quality/conf/Q&A).

### Как использовать её существующую репутацию и социальный капитал в StarMaker?
- Не требует новой capability (preamble/quality/conf/Q&A).

### Есть ли смысл вообще делать курс или более рационален другой продукт?
- Не требует новой capability (preamble/quality/conf/Q&A).

### ИЗУЧИТЬ STARMAKER КАК КАНАЛ ПРИВЛЕЧЕНИЯ
- Не требует новой capability (preamble/quality/conf/Q&A).

### НАЙТИ РЕАЛЬНЫЕ КУРСЫ ВОКАЛА
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***

### ОБЯЗАТЕЛЬНО РАЗДЕЛИТЬ МОДЕЛИ
- Не требует новой capability (preamble/quality/conf/Q&A).

### Интенсив
- Не требует новой capability (preamble/quality/conf/Q&A).

### ГЛАВНЫЙ АНАЛИЗ: ЭКОНОМИКА ВРЕМЕНИ ПРЕПОДАВАТЕЛЯ
- ✅ `lisa_estimator` (kind=`tool`, factory=`research`) — Estimation / Unit-economics для creator-economy (Teacher Time/$, калибровка) → уже реализован [implemented***REMOVED***

### ПОСТРОИТЬ ЭКОНОМИЧЕСКИЕ СЦЕНАРИИ
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***

### ИССЛЕДОВАТЬ СПРОС
- Не требует новой capability (preamble/quality/conf/Q&A).

### ОСОБО ИССЛЕДОВАТЬ АУДИТОРИЮ STARMAKER
- Не требует новой capability (preamble/quality/conf/Q&A).

### КОНКУРЕНТНЫЙ АНАЛИЗ
- Не требует новой capability (preamble/quality/conf/Q&A).

### АНАЛИЗ ОТЗЫВОВ
- ⚠ `qualitative_review_analyzer` (kind=`tool`, factory=`research`) — Качественный анализ отзывов (pain-points / churn / praise кластеризация) → в реестре, статус отличен от implemented [registered***REMOVED***

### ПРОВЕРИТЬ ГИПОТЕЗУ «ЗАПИСАННЫЙ КУРС НЕ НУЖЕН»
- Не требует новой capability (preamble/quality/conf/Q&A).

### ПРОВЕРИТЬ МОДЕЛЬ «РАЗБОР ПЕСНИ»
- Не требует новой capability (preamble/quality/conf/Q&A).

### ПРОВЕРИТЬ МОДЕЛЬ «STARMAKER VOCAL COACH»
- Не требует новой capability (preamble/quality/conf/Q&A).

### НАЙТИ РЕАЛЬНЫЕ ЦЕНЫ
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***

### ПОИСК НЕУДАЧНЫХ ПРОЕКТОВ
- ⚠ `anti_pattern_miner` (kind=`tool`, factory=`research`) — Anti-pattern mining (закрытые курсы/школы/заброшенные продукты) → в реестре, статус отличен от implemented [registered***REMOVED***

### ОПРЕДЕЛИТЬ UNIT ECONOMICS
- ✅ `lisa_estimator` (kind=`tool`, factory=`research`) — Estimation / Unit-economics для creator-economy (Teacher Time/$, калибровка) → уже реализован [implemented***REMOVED***
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***

### СОЗДАТЬ РЕЙТИНГ МОДЕЛЕЙ
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***

### НЕОБХОДИМО РАССМОТРЕТЬ СЦЕНАРИЙ «НЕ ДЕЛАТЬ КУРС»
- Не требует новой capability (preamble/quality/conf/Q&A).

### СФОРМИРОВАТЬ 5–7 КОНКРЕТНЫХ БИЗНЕС-МОДЕЛЕЙ
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***
- ⚠ `business_model_constructor` (kind=`module`, factory=`doc`) — Конструктор бизнес-моделей (14 полей, валидированный шаблон) → в реестре, статус отличен от implemented [registered***REMOVED***

### ОСОБО ИССЛЕДОВАТЬ MVP
- ⚠ `mvp_design_wizard` (kind=`module`, factory=`doc`) — MVP-механики (предпродажа, пилот, диагностическая воронка) → в реестре, статус отличен от implemented [registered***REMOVED***

### КРИТЕРИЙ УСПЕХА
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***

### ФИНАЛЬНЫЙ ОТЧЁТ
- Не требует новой capability (preamble/quality/conf/Q&A).

### Рынок вокального обучения
- Не требует новой capability (preamble/quality/conf/Q&A).

### StarMaker как потенциальный источник аудитории
- Не требует новой capability (preamble/quality/conf/Q&A).

### Карта конкурентов
- Не требует новой capability (preamble/quality/conf/Q&A).

### Таблица 15–25 реальных продуктов
- Не требует новой capability (preamble/quality/conf/Q&A).

### Сравнение бизнес-моделей
- ⚠ `business_model_constructor` (kind=`module`, factory=`doc`) — Конструктор бизнес-моделей (14 полей, валидированный шаблон) → в реестре, статус отличен от implemented [registered***REMOVED***

### Анализ цен
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***

### Анализ отзывов
- Не требует новой capability (preamble/quality/conf/Q&A).

### Боли и потребности учеников
- Не требует новой capability (preamble/quality/conf/Q&A).

### Экономика моделей
- Не требует новой capability (preamble/quality/conf/Q&A).

### Риск выгорания преподавателя
- Не требует новой capability (preamble/quality/conf/Q&A).

### Возможности использования репутации в StarMaker
- Не требует новой capability (preamble/quality/conf/Q&A).

### Что работает у конкурентов
- Не требует новой capability (preamble/quality/conf/Q&A).

### Что не работает
- Не требует новой capability (preamble/quality/conf/Q&A).

### 5–7 потенциальных моделей продукта
- Не требует новой capability (preamble/quality/conf/Q&A).

### Рейтинг моделей
- Не требует новой capability (preamble/quality/conf/Q&A).

### Рекомендуемая модель
- Не требует новой capability (preamble/quality/conf/Q&A).

### MVP
- Не требует новой capability (preamble/quality/conf/Q&A).

### Эксперимент по проверке спроса
- Не требует новой capability (preamble/quality/conf/Q&A).

### Критерии успеха/провала
- Не требует новой capability (preamble/quality/conf/Q&A).

### План действий на первые 30 дней
- Не требует новой capability (preamble/quality/conf/Q&A).

### ГЛАВНЫЙ ВОПРОС ИССЛЕДОВАНИЯ
- ⚠ `devil_advocate_pass` (kind=`module`, factory=`thinker`) — Adversarial review (3 kill-questions в конце, anti-confirmation-bias) → в реестре, статус отличен от implemented [registered***REMOVED***

### ТРЕБОВАНИЯ К КАЧЕСТВУ ИССЛЕДОВАНИЯ
- Не требует новой capability (preamble/quality/conf/Q&A).

### Использовать актуальные данные на 2026 год.
- Не требует новой capability (preamble/quality/conf/Q&A).

### Не ограничиваться первой страницей Google.
- Не требует новой capability (preamble/quality/conf/Q&A).

### Использовать разные типы источников.
- Не требует новой capability (preamble/quality/conf/Q&A).

### Приоритет
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***

### Каждое существенное утверждение подкреплять источником.
- Не требует новой capability (preamble/quality/conf/Q&A).

### Разделять
- Не требует новой capability (preamble/quality/conf/Q&A).

### Не выдавать предположение за факт.
- Не требует новой capability (preamble/quality/conf/Q&A).

### Не использовать маркетинговые заявления продавцов как доказательство эффективности.
- Не требует новой capability (preamble/quality/conf/Q&A).

### Искать негативные отзывы и противоположные мнения.
- Не требует новой capability (preamble/quality/conf/Q&A).

### Не делать вывод о спросе только на основании количества подписчиков.
- Не требует новой capability (preamble/quality/conf/Q&A).

### Если данных недостаточно — прямо написать «данных недостаточно».
- Не требует новой capability (preamble/quality/conf/Q&A).

### Не подгонять результаты под заранее выбранную бизнес-модель.
- ⚠ `pricing_enumerator` (kind=`tool`, factory=`research`) — Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.») → в реестре, статус отличен от implemented [registered***REMOVED***
- ⚠ `business_model_constructor` (kind=`module`, factory=`doc`) — Конструктор бизнес-моделей (14 полей, валидированный шаблон) → в реестре, статус отличен от implemented [registered***REMOVED***

## 3. Рекомендуемые register-команды

Скопируйте блок → выполните в `core_02/` → затем сделайте
`mark-prompt-written` и `mark-implemented` согласно AGENTS.md §5 REGISTER-FIRST.

```bash
python -m core_02.missing_registry register anti_pattern_miner --kind tool --factory research --description 'Anti-pattern mining (закрытые курсы/школы/заброшенные продукты)'
python -m core_02.missing_registry register business_model_constructor --kind module --factory doc --description 'Конструктор бизнес-моделей (14 полей, валидированный шаблон)'
python -m core_02.missing_registry register devil_advocate_pass --kind module --factory thinker --description 'Adversarial review (3 kill-questions в конце, anti-confirmation-bias)'
python -m core_02.missing_registry register mvp_design_wizard --kind module --factory doc --description 'MVP-механики (предпродажа, пилот, диагностическая воронка)'
python -m core_02.missing_registry register pricing_enumerator --kind tool --factory research --description 'Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.»)'
python -m core_02.missing_registry register qualitative_review_analyzer --kind tool --factory research --description 'Качественный анализ отзывов (pain-points / churn / praise кластеризация)'
```

## 4. First-slice (блокеры исполнения)

- [conclusion***REMOVED*** Ниже — рекомендуемый порядок реализации недостающих сущностей.
- Правило: сначала absent (0) → registered (1) → design_ready (2) → prompt_written (3).
- Первые 3 — **минимально необходимый** набор для запуска исходной задачи.
- Если среди блокеров есть `corpus_persistence` или `claim_source_tracker` → это особенно критично.

1. `anti_pattern_miner` (kind=`tool`, factory=`research`) — статус: `registered`
2. `business_model_constructor` (kind=`module`, factory=`doc`) — статус: `registered`
3. `devil_advocate_pass` (kind=`module`, factory=`thinker`) — статус: `registered`

После реализации блокеров в порядке 1→2→3, вернитесь к исходному промту.

## 5. Дисклеймеры (per Code Quality Standard §24)

- **Детермин vs LLM:** это детерминированный keyword-анализ по курируемой таксономии. [methodology***REMOVED***
  LLM-вариант может извлечь больше неочевидных зависимостей, но требует подключённой модели и стоимости.
- **Tagging:** каждое утверждение явно отмечено `[observation***REMOVED***`/`[conclusion***REMOVED***`/`[methodology***REMOVED***`
  (закрывает ANTI-6b/vocabulary defense + §24 «факт/наблюдение/вывод/гипотеза»).
- **No side-effects:** этот executor НЕ вызывает `MissingRegistry.register_missing()` напрямую.
  Все команды — paste-friendly для оператора; регистрация остаётся человеку или supervised-агенту.
- **Audit trail:** отчёт — `capability_gap_report.md` в `project.root` (logged via `execute() -> List[str***REMOVED***`).
- **Testability:** таксономия детерминирована, тесты инжектят `MissingRegistry` через конструктор — без сети и диска.

