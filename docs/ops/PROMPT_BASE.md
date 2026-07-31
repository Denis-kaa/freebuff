# PROMPT BASE — Библиотека промтов для Buffy

> **Версия:** 1.0.0  
> **Дата:** 2026-07-29  
> **Назначение:** Универсальная библиотека промтов для аудита, создания сценариев, ревью, анализа, тестирования, рефакторинга, документации и отладки  

---

## Содержание

1. [Аудит***REMOVED***(#1-аудит)
2. [Создание сценариев***REMOVED***(#2-создание-сценариев)
3. [Рекомендации***REMOVED***(#3-рекомендации)
4. [Code Review***REMOVED***(#4-code-review)
5. [Архитектурный анализ***REMOVED***(#5-архитектурный-анализ)
6. [Тестирование***REMOVED***(#6-тестирование)
7. [Рефакторинг***REMOVED***(#7-рефакторинг)
8. [Документация***REMOVED***(#8-документация)
9. [Отладка***REMOVED***(#9-отладка)
10. [Безопасность***REMOVED***(#10-безопасность)
11. [План / Roadmap***REMOVED***(#11-план--roadmap)
12. [Миграция данных***REMOVED***(#12-миграция-данных)
13. [Онбординг / Начало работы***REMOVED***(#13-онбординг--начало-работы)
14. [DevOps / CI-CD / Инфраструктура***REMOVED***(#14-devops--ci-cd--инфраструктура)
15. [API Дизайн и Спецификация***REMOVED***(#15-api-дизайн-и-спецификация)
16. [Управление знаниями / Knowledge Base***REMOVED***(#16-управление-знаниями--knowledge-base)
17. [Релизный процесс / Versioning***REMOVED***(#17-релизный-процесс--versioning)
18. [Генерация кода / Прототипирование***REMOVED***(#18-генерация-кода--прототипирование)

---

## 1. Аудит

### 1.1 Аудит кода

```
Проведи аудит кода в файле {file_path***REMOVED***.

Анализируй:
1. Качество кода (чистота, читаемость, сложность)
2. Ошибки (баги, race conditions, утечки памяти)
3. Безопасность (инъекции, XSS, авторизация)
4. Производительность (узкие места, N+1 запросы)
5. Тестируемость (покрытие, моки)
6. Соответствие конвенциям проекта ({conventions***REMOVED***)

Формат вывода:
```json
{
  "severity": "critical|high|medium|low",
  "file": "путь к файлу",
  "line": "строка",
  "issue": "описание проблемы",
  "suggestion": "как исправить"
***REMOVED***
```

Приоритет: сначала критические, потом высокие, потом средние.
```

### 1.2 Аудит архитектуры

```
Проведи архитектурный аудит модуля {module_name***REMOVED***.

Критерии:
1. Связность (cohesion) — насколько модуль сфокусирован
2. Зацепление (coupling) — насколько модуль зависит от других
3. Тестируемость — можно ли протестировать изолированно
4. Расширяемость — легко ли добавить новую функциональность
5. Соответствие SOLID принципам
6. Управление зависимостями (Dependency Injection / Service Locator)
7. Обработка ошибок (try/except, logging, fallback)

Файлы модуля: {file_list***REMOVED***

Формат:
| Аспект | Оценка (1-10) | Проблемы | Рекомендации |
|--------|--------------|----------|--------------|
```

### 1.3 Аудит документации

```
Проведи аудит документации проекта.

Проверь:
1. README.md — актуальность, полнота, инструкции по установке
2. CHANGELOG.md — все ли изменения зафиксированы
3. docs/*.md — консистентность, устаревшие разделы
4. Комментарии в коде — не расходятся ли с реальностью
5. Отсутствующие документы (спецификации, ADR, TROUBLESHOOTING)

Формат:
| Документ | Статус | Проблема | Необходимое действие |
|----------|--------|----------|---------------------|
```

### 1.4 Аудит зависимостей

```
Проведи аудит зависимостей проекта.

Файл: {requirements_file***REMOVED***

Проверь:
1. Устаревшие пакеты (версии >1 года)
2. Неиспользуемые пакеты (dead weight)
3. Конфликты версий
4. Уязвимости (CVE)
5. Лицензии (совместимость с проектом)

Формат:
| Пакет | Текущая версия | Последняя | Статус | Риск |
|-------|---------------|-----------|--------|------|
```

### 1.5 Drift-аудит (расхождение кода и документации)

```
Проведи drift-аудит проекта в {project_path***REMOVED***.

Сравни:
1. Файловую структуру с описанием в BUFFY.md / README.md
2. Фактические API с документированными API
3. Наличие тестов в tests/ с тестами, описанными в спецификациях
4. Актуальность CHANGELOG.md (все ли значимые изменения зафиксированы)

Формат:
| Ожидание | Реальность | Расхождение | Severity |
|----------|-----------|-------------|----------|
```

### 1.6 Аудит тестового покрытия

```
Проведи аудит тестового покрытия для модулей: {modules***REMOVED***.

Проверь:
1. Какие функции/классы не покрыты тестами
2. Какие тесты тестируют не то, что нужно (false positive)
3. Какие тесты слишком хрупкие (завязаны на имплементацию)
4. Какие граничные случаи не покрыты
5. Есть ли интеграционные тесты для критических путей

Файлы: {test_files***REMOVED***
Исходники: {source_files***REMOVED***

Формат:
| Модуль | Покрытие | Пропущенные кейсы | Рекомендации |
|--------|----------|-------------------|--------------|
```

---

## 2. Создание сценариев

### 2.1 Новый сценарий (YAML front matter + Markdown)

```
Создай новый сценарий для Scenario Engine.

Категория: {category***REMOVED*** (freelancing / ai / tool / templates / agent / automation)
Сложность: {complexity***REMOVED*** (низкая / средняя / высокая)
Название: {title***REMOVED***
Описание: {description***REMOVED***

Формат файла (YAML front matter + Markdown тело):
```markdown
---
category: {category***REMOVED***
complexity: {complexity***REMOVED***
description: {description***REMOVED***
tags:
  - {tag1***REMOVED***
  - {tag2***REMOVED***
---

# Сценарий: {title***REMOVED***

## Описание задачи

{detailed_description***REMOVED***

## Технические требования

```yaml
стек:
  {tech_stack***REMOVED***
```

## Промт для freebuff

```
{prompt_template***REMOVED***
```

## Варианты

| Вариант | Описание | Сложность |
|---------|----------|-----------|
```

### 2.2 Сценарий для парсера данных

```
Создай сценарий парсера для сайта {url***REMOVED***.

Что парсить:
- {field1***REMOVED***: {description1***REMOVED***
- {field2***REMOVED***: {description2***REMOVED***
- {field3***REMOVED***: {description3***REMOVED***

Тип сайта: {site_type***REMOVED*** (статический / SPA / API / авторизация)
Формат вывода: {format***REMOVED*** (JSON / CSV / SQLite)
Частота: {frequency***REMOVED*** (разово / ежедневно / в реальном времени)

Сгенерируй:
1. Полный код парсера (Python 3.11+)
2. requirements.txt
3. Инструкцию по запуску
4. Обработку ошибок (timeout, retry, логирование)
```

### 2.3 Сценарий для Telegram бота

```
Создай сценарий Telegram бота для задачи: {task***REMOVED***.

Требования:
- Функционал: {features***REMOVED***
- База данных: {database***REMOVED*** (SQLite / PostgreSQL)
- Deploy: {deploy***REMOVED*** (VPS / serverless / Termux)
- Язык: {language***REMOVED*** (Python / JS / Go)

Сгенерируй:
1. Структуру проекта
2. Основные файлы с кодом
3. requirements.txt
4. Команды для deploy
```

### 2.4 Сценарий для AI агента

```
Создай сценарий настройки AI агента {agent_type***REMOVED***.

Параметры:
- Имя агента: {name***REMOVED***
- Проект: {project***REMOVED***
- Роль: {role***REMOVED*** (coding / reviewing / architect / devops)
- Дополнительные инструкции: {instructions***REMOVED***

Сгенерируй:
1. Конфигурационный файл агента
2. Правила и конвенции
3. Контекст из документации проекта
4. Тестовые команды для проверки
```

### 2.5 Пакетный импорт сценариев

```
Импортируй несколько сценариев из шаблона.

Шаблон: {template_name***REMOVED***
Количество: {count***REMOVED***
Категория: {category***REMOVED***
Базовое имя: {base_name***REMOVED***
Параметры:
- Параметр 1: вариации {variations1***REMOVED***
- Параметр 2: вариации {variations2***REMOVED***

Сгенерируй {count***REMOVED*** файлов сценариев с YAML front matter.
```

---

## 3. Рекомендации

### 3.1 Технические рекомендации

```
Проанализируй текущее состояние компонента {component***REMOVED***.

Контекст:
- Текущая реализация: {current_implementation***REMOVED***
- Проблемы: {issues***REMOVED***
- Цель: {goal***REMOVED***

Дай рекомендации по улучшению в формате:
| # | Рекомендация | Обоснование | Сложность | Эффект | Приоритет |
|---|-------------|-------------|-----------|--------|-----------|
```

### 3.2 Рекомендации по оптимизации

```
Найди узкие места в {module***REMOVED***.

Метрики:
- Время выполнения: {execution_time***REMOVED***
- Использование памяти: {memory_usage***REMOVED***
- Количество запросов: {query_count***REMOVED***

Предложи оптимизации:
1. Какие участки кода можно ускорить
2. Какие запросы можно кэшировать
3. Какие структуры данных можно оптимизировать
4. Какие алгоритмы заменить

Формат: рекомендация → ожидаемый эффект → сложность внедрения
```

### 3.3 Рекомендации по архитектуре

```
Проанализируй архитектуру {system***REMOVED*** и предложи улучшения.

Текущая архитектура:
{current_architecture_description***REMOVED***

Проблемы:
{known_issues***REMOVED***

Будущие требования:
{future_requirements***REMOVED***

Предложи:
1. Изменения в структуре модулей
2. Новые абстракции/интерфейсы
3. Паттерны для внедрения
4. План миграции (по шагам)
```

### 3.4 Рекомендации по выбору технологии

```
Выбери оптимальную технологию для задачи: {task***REMOVED***.

Требования:
- Функциональные: {functional_requirements***REMOVED***
- Нефункциональные: {non_functional_requirements***REMOVED***
- Ограничения: {constraints***REMOVED*** (бюджет, время, стек)

Сравни:
| Критерий | Вариант A | Вариант B | Вариант C |
|----------|-----------|-----------|-----------|
| {criterion1***REMOVED*** | | | |
| {criterion2***REMOVED*** | | | |

Итоговая рекомендация: {recommendation_with_justification***REMOVED***
```

---

## 4. Code Review

### 4.1 Стандартный Code Review

```
Проверь изменения в PR.

Файлы изменены: {files***REMOVED***
Описание изменений: {description***REMOVED***

Проверь:
1. Логика — корректность, граничные случаи
2. Безопасность — инъекции, утечки данных
3. Производительность — лишние запросы, аллокации
4. Читаемость — naming, структура, комментарии
5. Тесты — покрытие, качество ассертов
6. Обработка ошибок — try/except, fallback, логи

Формат:
- ❌ CRITICAL: {issue***REMOVED*** → {fix***REMOVED***
- ⚠️ HIGH: {issue***REMOVED*** → {suggestion***REMOVED***
- 💡 MEDIUM: {issue***REMOVED*** → {suggestion***REMOVED***
- 📝 LOW: {note***REMOVED***
```

### 4.2 Code Review безопасности

```
Проверь код на уязвимости.

Файлы: {files***REMOVED***

Ищи:
1. SQL инъекции (f-strings в запросах, конкатенация)
2. Command инъекции (os.system, subprocess shell=True, eval/exec)
3. Path traversal (os.path.join с пользовательским вводом)
4. XSS (неэкранированный вывод в HTML/JS)
5. Утечки данных (API ключи в логах, отладка в production)
6. SSRF (запросы к URL из пользовательского ввода)
7. Race conditions (threading без lock, временные файлы)

Формат:
| Уязвимость | Файл:Строка | Риск | Фикс |
|-----------|-------------|------|------|
```

### 4.3 Code Review производительности

```
Проверь производительность изменений.

Файлы: {files***REMOVED***
Бенчмарки (если есть): {benchmarks***REMOVED***

Ищи:
1. N+1 запросы в циклах
2. Лишние аллокации (создание объектов в циклах)
3. Неэффективные структуры данных (list вместо set для поиска)
4. Блокирующие вызовы в async коде
5. Утечки памяти (незакрытые файлы, циклические ссылки)
6. Лишние импорты (замедляют загрузку)

Формат:
| Проблема | Файл:Строка | Влияние | Оптимизация |
|----------|-------------|---------|-------------|
```

---

## 5. Архитектурный анализ

### 5.1 Анализ модуля

```
Проведи глубокий анализ модуля {module***REMOVED***.

Файлы модуля: {files***REMOVED***

Проанализируй:
1. **Назначение** — какую проблему решает
2. **API** — публичные функции/классы, их стабильность
3. **Зависимости** — от каких модулей зависит, какие от него
4. **Состояние** — есть ли мутабельное состояние, как управляется
5. **Потоки** — thread-safe? async? блокирующие вызовы?
6. **Ошибки** — какие исключения выбрасывает, как обрабатывает
7. **Тесты** — покрытие, качество, интеграционные тесты

Формат вывода: аналитическая записка с выводами и рекомендациями.
```

### 5.2 Диаграмма зависимостей

```
Построй диаграмму зависимостей для модуля {module***REMOVED***.

Файлы: {files***REMOVED***

Формат:
{module***REMOVED***
  ├── {dependency1***REMOVED*** ({type: core/extension/lab***REMOVED***)
  │     ├── {sub_dep1***REMOVED***
  │     └── {sub_dep2***REMOVED***
  ├── {dependency2***REMOVED***
  └── {dependency3***REMOVED***

Оцени:
- Циклические зависимости
- Неоправданные зависимости (модуль знает слишком много)
- Отсутствующие абстракции (прямые вызовы вместо интерфейсов)
```

### 5.3 Анализ data flow

```
Проанализируй поток данных в {module***REMOVED***.

Входные точки: {entry_points***REMOVED***
Выходные точки: {exit_points***REMOVED***
Хранилища: {storage***REMOVED***

Построй:
1. **Data Flow Diagram** — как данные проходят через модуль
2. **Transformations** — какие преобразования происходят
3. **Validation** — где и как валидируются данные
4. **Error paths** — что происходит при ошибках валидации/обработки

Найди:
- Избыточные преобразования
- Потеря данных (silent truncation)
- Отсутствие валидации на границах модуля
```

---

## 6. Тестирование

### 6.1 Написание тестов для модуля

```
Напиши unit-тесты для модуля {module***REMOVED***.

Исходный код: {source_files***REMOVED***
Существующие тесты: {test_files***REMOVED***
Требуемое покрытие: 80%+ строк кода

Что тестировать:
1. Основной функционал (happy path)
2. Граничные случаи (пустые значения, None, максимумы)
3. Ошибки (неверные аргументы, исключения)
4. Состояние (изменение состояния, идемпотентность)
5. Интеграция (взаимодействие с зависимостями)

Конвенции:
- Fixtures в conftest.py или freebuff
- Mock внешних зависимостей
- Один тест — один assert (или группа связанных)
- Имена тестов: test_{function***REMOVED***_{scenario***REMOVED***
```

### 6.2 Интеграционные тесты

```
Напиши интеграционные тесты для {feature***REMOVED***.

Компоненты: {components***REMOVED***
Точки интеграции: {integration_points***REMOVED***

Что тестировать:
1. Полный цикл: вход → обработка → выход
2. Состояние между компонентами (передача данных)
3. Ошибки на стыках компонентов
4. Производительность (время ответа)
5. Идемпотентность (повторный вызов)

Тестовые данные: {test_data***REMOVED***
```

### 6.3 Нагрузочное тестирование

```
Создай сценарий нагрузочного тестирования для {component***REMOVED***.

Метрики:
- RPS: {target_rps***REMOVED***
- Латентность: {max_latency_ms***REMOVED***
- Параллельность: {concurrency***REMOVED***

Инструменты:
- Python: {python_tool***REMOVED*** (locust / aiohttp benchmark)
- CLI: {cli_tool***REMOVED*** (wrk / ab / hey)

Сценарии:
1. {scenario1***REMOVED*** — {duration***REMOVED***
2. {scenario2***REMOVED*** — {duration***REMOVED***

Формат отчёта:
| Метрика | Среднее | P95 | P99 | Max |
|---------|---------|-----|-----|-----|
```

---

## 7. Рефакторинг

### 7.1 Рефакторинг модуля

```
Проведи рефакторинг модуля {module***REMOVED***.

Текущие проблемы: {issues***REMOVED***
Цель рефакторинга: {goal***REMOVED***

Требования:
1. Сохранить обратную совместимость API
2. Не сломать существующие тесты (добавить новые)
3. Разделить на логические подмодули при необходимости
4. Улучшить читаемость (naming, структура, комментарии)
5. Добавить typing (type hints)

План:
1. {step1***REMOVED*** — {expected_result***REMOVED***
2. {step2***REMOVED*** — {expected_result***REMOVED***
3. {step3***REMOVED*** — {expected_result***REMOVED***
```

### 7.2 Выделение модуля

```
Выдели функциональность {functionality***REMOVED*** из {source_module***REMOVED*** в новый модуль {target_module***REMOVED***.

Причина: {reason***REMOVED***

Шаги:
1. Создать {target_module***REMOVED*** с интерфейсом
2. Перенести функции/классы
3. Обновить импорты в {source_module***REMOVED***
4. Создать тесты для {target_module***REMOVED***
5. Проверить что все старые тесты проходят

Код для переноса:
{code_to_extract***REMOVED***
```

### 7.3 Упрощение сложного кода

```
Упрости сложный код в {file***REMOVED***:{line_start***REMOVED***-{line_end***REMOVED***.

Текущий код:
```python
{complex_code***REMOVED***
```

Проблемы:
- {issue1***REMOVED***
- {issue2***REMOVED***

Предложи:
1. Разбитие на меньшие функции
2. Использование более простых конструкций
3. Выделение повторяющегося кода
4. Упрощение логики (early return, guard clauses)
```

---

## 8. Документация

### 8.1 Написание README

```
Напиши README.md для модуля/проекта {name***REMOVED***.

Описание: {description***REMOVED***
Ключевые особенности: {features***REMOVED***
Стек: {tech_stack***REMOVED***
Аудитория: {audience***REMOVED*** (разработчики / пользователи / DevOps)

Структура:
1. **Заголовок** — название и краткое описание (1 предложение)
2. **Зачем** — проблема, которую решает
3. **Установка** — pip / git clone / docker
4. **Быстрый старт** — минимальный пример использования
5. **API** — основные функции/классы с примерами
6. **Конфигурация** — переменные окружения, .env
7. **Тестирование** — как запустить тесты
8. **Contributing** — как внести вклад
```

### 8.2 Написание CHANGELOG

```
Обнови CHANGELOG.md.

Новая версия: {version***REMOVED***
Дата: {date***REMOVED***
Изменения:
- Добавлено: {added_features***REMOVED***
- Изменено: {changed_features***REMOVED***
- Исправлено: {fixed_bugs***REMOVED***
- Удалено: {removed_features***REMOVED***

Формат (Keep a Changelog):
## [{version***REMOVED******REMOVED*** — {date***REMOVED***

### Добавлено
- {feature1***REMOVED*** — {description***REMOVED***

### Изменено
- {change1***REMOVED*** — {reason***REMOVED***

### Исправлено
- {fix1***REMOVED*** — {description***REMOVED***

### Удалено
- {removal1***REMOVED*** — {reason***REMOVED***
```

### 8.3 Написание ADR (Architecture Decision Record)

```
Создай ADR для решения: {decision_title***REMOVED***.

Контекст:
- Проблема: {problem***REMOVED***
- Альтернативы: {alternatives***REMOVED***
- Критерии: {criteria***REMOVED***

Формат:
# ADR-{number***REMOVED***: {title***REMOVED***

## Статус
{status***REMOVED*** (Proposed / Accepted / Deprecated / Superseded)

## Контекст
{context***REMOVED***

## Решение
{decision***REMOVED***

## Альтернативы
| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| {option1***REMOVED*** | | |
| {option2***REMOVED*** | | |

## Последствия
{consequences***REMOVED***

## Связанные ADR
{related***REMOVED***
```

---

## 9. Отладка

### 9.1 Диагностика ошибки

```
Проведи диагностику ошибки.

Ошибка: {error_message***REMOVED***
Трейс: {traceback***REMOVED***
Контекст: {context***REMOVED***
Версия: {version***REMOVED***
Окружение: {environment***REMOVED***

Проанализируй:
1. Причина — что вызывает ошибку
2. Условия — при каких условиях воспроизводится
3. Влияние — кого/что затрагивает
4. Workaround — временное решение
5. Фикс — постоянное решение

Формат:
## Диагностика
{analysis***REMOVED***

## Воспроизведение
{steps_to_reproduce***REMOVED***

## Решение
{fix_description***REMOVED***
```

### 9.2 Анализ OOM / Signal 9

```
Проведи анализ OOM (Out of Memory / Signal 9 / SIGKILL).

Контекст: {context***REMOVED***
Логи: {logs***REMOVED***
Использование памяти: {memory_stats***REMOVED***
Окружение: {environment***REMOVED*** (Termux / Linux / Docker)

Проанализируй:
1. Какой процесс был убит
2. Сколько памяти использовал
3. Какие процессы конкурировали за память
4. Есть ли утечки памяти
5. Swap настроен? Есть ли swap-файл?

Рекомендации:
1. Оптимизация памяти (ленивая загрузка, stream вместо загрузки в RAM)
2. Swap-файл (dd если нужно)
3. OOM Priority (echo -17 > /proc/pid/oom_adj)
4. Мониторинг (free -m, /proc/meminfo)
```

### 9.3 Анализ производительности

```
Проведи профилирование {module***REMOVED***.

Метод: {method***REMOVED*** (cProfile / py-spy / timeit)
Данные профилирования: {profiling_data***REMOVED***

Найди:
1. Функции с наибольшим временем выполнения
2. Функции с наибольшим количеством вызовов
3. Неожиданно медленные участки
4. Лишние аллокации

Формат:
| Функция | Calls | Total time | Per call | % времени |
|---------|-------|------------|----------|-----------|
```

---

## 10. Безопасность

### 10.1 Аудит безопасности

```
Проведи аудит безопасности проекта {project***REMOVED***.

Сканируй:
1. Твёрдые API ключи в коде (regex: [A-Za-z0-9_***REMOVED***{20,***REMOVED***)
2. Открытые эндпоинты без авторизации
3. Устаревшие зависимости с CVE
4. Небезопасные конфигурации (debug=True, CORS *)
5. Права доступа к файлам (минимальные привилегии)
6. Логирование чувствительных данных

Файлы: {files***REMOVED***
Исключения: {exclusions***REMOVED***

Формат:
| Уязвимость | Файл | Риск | Фикс |
|-----------|------|------|------|
```

### 10.2 Проверка на инъекции

```
Проверь код на уязвимости инъекций.

Типы:
1. SQL: f-strings/format в SQL запросах, конкатенация
2. Command: os.system, os.popen, subprocess shell=True, eval
3. Path: os.path.join с пользовательскими данными
4. Template: SSTI в Jinja2/Mako

Файлы: {files***REMOVED***

Формат:
| Тип | Файл:Строка | Код | Уязвимость | Фикс |
|-----|-------------|-----|------------|------|
```

---

## 11. План / Roadmap

### 11.1 Составление плана

```
Составь план реализации для {feature***REMOVED***.

Требования: {requirements***REMOVED***
Ограничения: {constraints***REMOVED*** (время, ресурсы, зависимости)
Приоритет: {priority***REMOVED*** (P0 / P1 / P2 / P3)

Формат:
## Фаза 1: {name***REMOVED***
- [ ***REMOVED*** {task1***REMOVED*** — {estimate***REMOVED***
- [ ***REMOVED*** {task2***REMOVED*** — {estimate***REMOVED***

## Фаза 2: {name***REMOVED***
- [ ***REMOVED*** {task3***REMOVED*** — {estimate***REMOVED***

### Легенда
- P0: критично (блокер)
- P1: важно (основной функционал)
- P2: желательно (улучшения)
- P3: нишево (когда будет время)
```

### 11.2 Оценка сложности

```
Оцени сложность реализации {feature***REMOVED***.

Критерии:
1. Объём кода: {estimated_lines***REMOVED*** LOC
2. Новые концепции: {new_concepts***REMOVED*** (0-5)
3. Зависимости от других модулей: {dependencies***REMOVED***
4. Риски: {risks***REMOVED***
5. Тестирование: {testing_effort***REMOVED*** unit / integration / e2e

Итоговая оценка:
- Сложность: {complexity***REMOVED*** (низкая / средняя / высокая / критическая)
- Время: {estimated_time***REMOVED*** (часы / дни / недели)
- Тестов: {estimated_tests***REMOVED***
```

---

## 12. Миграция данных

### 12.1 Создание скрипта миграции

```
Создай скрипт миграции данных из {source***REMOVED*** в {target***REMOVED***.

Исходный формат: {source_format***REMOVED***
Целевой формат: {target_format***REMOVED***
Объём данных: {data_volume***REMOVED***
Требования к идемпотентности: {idempotent***REMOVED*** (да / нет)

Скрипт должен:
1. Читать данные из {source***REMOVED***
2. Трансформировать их
3. Сохранять в {target***REMOVED***
4. Обрабатывать ошибки (пропускать битые записи, логировать)
5. Быть идемпотентным (повторный запуск не создаёт дубликатов)

Тестовые данные: {test_data***REMOVED***
```

### 12.2 Валидация после миграции

```
Проверь корректность миграции данных.

Данные до: {source_sample***REMOVED***
Данные после: {target_sample***REMOVED***
Количество записей: {source_count***REMOVED*** → {target_count***REMOVED***

Проверь:
1. Количество записей совпадает (или учитывая intentional drops)
2. Формат данных соответствует ожидаемому
3. Ключевые поля не потеряны
4. Нет дубликатов
5. Нет битых записей (null в обязательных полях)

Формат:
| Проверка | Статус | Детали |
|----------|--------|--------|
| Количество | ✅/❌ | source={n***REMOVED*** target={m***REMOVED*** |
| Формат | ✅/❌ | {details***REMOVED*** |
```

---

## 13. Онбординг / Начало работы

### 13.1 Онбординг нового разработчика

```
Проведи онбординг нового разработчика в проект {project***REMOVED***.

Роль: {role***REMOVED*** (backend / frontend / AI / fullstack)
Уровень: {level***REMOVED*** (junior / middle / senior)
Стек: {tech_stack***REMOVED***

Сгенерируй:
1. **Карту проекта** — какие директории за что отвечают
2. **Quick Start** — 5 шагов для запуска freebuff
3. **Список конвенций** — naming, стиль кода, коммиты, PR
4. **Глоссарий** — термины проекта (аббревиатуры, внутренние названия)
5. **Связанные документы** — ссылки на README, SPEC, ADR, архитектуру
6. **Чеклист первого PR**:
   - [ ***REMOVED*** Установил зависимости
   - [ ***REMOVED*** Запустил тесты (они проходят)
   - [ ***REMOVED*** Прочитал CONTRIBUTING.md
   - [ ***REMOVED*** Создал ветку от main
   - [ ***REMOVED*** Добавил тесты на новый код
   - [ ***REMOVED*** Обновил CHANGELOG.md

Формат: Markdown документ с секциями и чеклистами.
```

### 13.2 Assessment кодовой базы

```
Проведи assessment кодовой базы для нового участника.

Проект: {project***REMOVED***
Директории: {directories***REMOVED***

Оцени по шкале 1-10:
1. **Читаемость** — понятны ли названия, структура файлов?
2. **Документированность** — есть ли README, комментарии, ADR?
3. **Тестируемость** — легко ли написать/запустить тесты?
4. **Входной порог** — сколько времени нужно чтобы сделать первый PR?
5. **Консистентность** — единый стиль или "лоскутное одеяло"?

Вывод: топ-3 проблемы для нового разработчика и рекомендации по их устранению.
```

### 13.3 Создание CONTRIBUTING.md

```
Создай CONTRIBUTING.md для проекта {project***REMOVED***.

Тип проекта: {type***REMOVED*** (open-source / internal / commercial)
Стек: {tech_stack***REMOVED***
Требования к PR: {pr_requirements***REMOVED***

Разделы:
1. **Как начать** — fork, clone, branch naming
2. **Установка** — зависимости, виртуальное окружение, переменные
3. **Запуск тестов** — pytest / npm test / make test
4. **Code Style** — линтеры, форматтеры, pre-commit hooks
5. **Правила коммитов** — Conventional Commits (feat/fix/docs/refactor)
6. **Процесс PR** — шаблон, ревью, CI checks, merge strategy
7. **Code Review** — что проверять, checklist
8. **Релизный процесс** — versioning, CHANGELOG, tags
```

---

## 14. DevOps / CI-CD / Инфраструктура

### 14.1 Настройка CI/CD пайплайна

```
Настрой CI/CD пайплайн для проекта {project***REMOVED***.

Платформа: {platform***REMOVED*** (GitHub Actions / GitLab CI / Jenkins / Drone)
Язык: {language***REMOVED***
Тесты: {test_command***REMOVED***
Deploy: {deploy_target***REMOVED*** (VPS / Docker / Serverless)

Сгенерируй конфигурацию:
1. **Линтинг + форматирование** — ruff / black / eslint / prettier
2. **Type checking** — mypy / ts-check / pyright
3. **Unit тесты** — pytest / vitest / go test
4. **Интеграционные тесты** — docker-compose / testcontainers
5. **Билд** — сборка артефакта
6. **Deploy** — staging → production (с approval gate)
7. **Уведомления** — Telegram / Slack / Email при падении

Формат: файл .github/workflows/{name***REMOVED***.yml или эквивалент.
```

### 14.2 Docker-контейнеризация

```
Создай Docker-инфраструктуру для проекта {project***REMOVED***.

Стек: {tech_stack***REMOVED***
База данных: {database***REMOVED***
Дополнительные сервисы: {services***REMOVED*** (Redis / Nginx / очередь)

Сгенерируй:
1. **Dockerfile** — multi-stage build для production
2. **docker-compose.yml** — dev окружение со всеми сервисами
3. **.dockerignore** — исключения (__pycache__, .git, venv)
4. **healthcheck** — эндпоинт /health или скрипт
5. **docker-compose.override.yml** — для freebuff разработки (volume mount, debug)

Требования:
- Минимальный размер образа (alpine / slim)
- Non-root user
- Healthcheck каждые 30s
- Логирование в stdout/stderr
```

### 14.3 Настройка мониторинга

```
Настрой мониторинг для сервиса {service***REMOVED***.

Метрики:
- Системные: CPU, RAM, Disk, Network
- Приложения: RPS, latency, error rate
- Бизнес: {business_metrics***REMOVED***

Инструменты: {tools***REMOVED*** (Prometheus + Grafana / Datadog / Sentry)

Сгенерируй:
1. **Метрики** — список экспортируемых метрик с описанием
2. **Алерты** — правила оповещения (critical/warning/info)
3. **Дашборд** — Grafana dashboard (JSON model)
4. **Логирование** — structured logging (JSON), retention policy
5. **Healthchecks** — эндпоинты /health, /ready, /metrics

Формат: документация + конфигурационные файлы.
```

---

## 15. API Дизайн и Спецификация

### 15.1 REST API дизайн

```
Спроектируй REST API для {domain***REMOVED***.

Ресурсы: {resources***REMOVED***
Операции: {operations***REMOVED*** (CRUD / поиск / фильтрация)
Аутентификация: {auth***REMOVED*** (JWT / API Key / OAuth2)
Аудитория: {audience***REMOVED*** (публичное / внутреннее / партнёрское)

Сгенерируй:
1. **Endpoint map** — таблица методов, URL, параметров
2. **Request/Response схемы** — JSON Schema или Pydantic модели
3. **Error handling** — структура ошибок, HTTP статусы
4. **Pagination** — cursor-based или offset-based
5. **Rate limiting** — политики, заголовки (X-RateLimit-*)
6. **Versioning** — URL (/v1/) или заголовок (Accept: vnd.api.v1+json)

Формат: OpenAPI 3.0 спецификация (YAML) или таблица Markdown.
```

### 15.2 WebSocket / Event API дизайн

```
Спроектируй Event-Driven API для {domain***REMOVED***.

События: {events***REMOVED***
Транспорт: {transport***REMOVED*** (WebSocket / SSE / Webhook / Message Queue)
Формат: {format***REMOVED*** (JSON / Protobuf / Avro)

Сгенерируй:
1. **Event catalog** — таблица событий, их структура, триггеры
2. **Subscription model** — как клиенты подписываются
3. **Delivery гарантии** — at-most-once / at-least-once / exactly-once
4. **Retry policy** — exponential backoff, dead letter queue
5. **Schema registry** — где хранятся схемы, версионирование
6. **Примеры** — publish/subscribe, consumer code

Формат:
```
Event: order.created
Schema: { id: str, total: float, items: [...***REMOVED*** ***REMOVED***
When: пользователь оформляет заказ
Guarantee: at-least-once
```
```

### 15.3 API Review Checklist

```
Проведи ревью API спецификации {spec_file***REMOVED***.

Проверь:
1. **RESTful** — соблюдение REST конвенций (ресурсы, методы, статусы)
2. **Консистентность** — единый стиль именования (camelCase / snake_case)
3. **Безопасность** — аутентификация, авторизация, validation
4. **Ошибки** — все ли ошибки покрыты, понятные сообщения
5. **Idempotency** — идемпотентны ли POST на создание?
6. **Pagination** — есть ли у списков, default/page size limit
7. **Deprecation** — есть ли план устаревания полей/эндпоинтов
8. **Документация** — понятно ли consumer'у как использовать?

Формат: review by категориям с примерами проблемных мест.
```

---

## 16. Управление знаниями / Knowledge Base

### 16.1 Извлечение знаний из кода

```
Извлеки знания из модуля {module***REMOVED*** для Knowledge Base.

Файлы: {files***REMOVED***

Сгенерируй:
1. **Архитектурный обзор** — как устроен модуль (2-3 абзаца)
2. **Ключевые концепции** — таблица терминов и определений
3. **Паттерны** — какие паттерны используются (с примерами кода)
4. **Правила** — неочевидные правила и ограничения
5. **Почему так** — решения, которые могут показаться странными (с обоснованием)
6. **WTF moments** — частые ошибки и как их избежать

Формат: Markdown документ в docs/knowledge/{module***REMOVED***.md

Пример вывода:
| Концепция | Описание |
|-----------|----------|
| Session | Единица контекста в системе, содержит messages + metadata |
| Checkpoint | Snapshot состояния сессии в определённый момент времени |
```

### 16.2 Создание FAQ

```
Создай FAQ для модуля {module***REMOVED***.

Контекст:
- Типовые вопросы пользователей: {questions***REMOVED***
- Типовые ошибки: {common_errors***REMOVED***
- Частые баги: {common_bugs***REMOVED***

Формат:
## Q: {вопрос***REMOVED***
**A:** {ответ***REMOVED*** с примером кода/команды.
**Когда:** {когда это актуально***REMOVED***
**Если не работает:** {что проверить***REMOVED***
```

### 16.3 Knowledge Graph update

```
Обнови Knowledge Graph новыми связями.

Новый компонент: {component***REMOVED***
Связи:
- Зависит от: {dependencies***REMOVED***
- Используется в: {used_in***REMOVED***
- Связанные ADR: {adr_list***REMOVED***
- Связанные сценарии: {scenarios***REMOVED***

Формат обновления:
```
{component***REMOVED***:
  depends_on: [{dependencies***REMOVED******REMOVED***
  used_by: [{used_in***REMOVED******REMOVED***
  adrs: [{adrs***REMOVED******REMOVED***
  scenarios: [{scenarios***REMOVED******REMOVED***
  description: "{brief_description***REMOVED***"
```

Добавь связи в Knowledge Engine и проверь что нет циклов.
```

---

## 17. Релизный процесс / Versioning

### 17.1 Подготовка релиза

```
Подготовь релиз версии {version***REMOVED***.

Текущая версия: {current_version***REMOVED***
Изменения: {changes_list***REMOVED***
Тип релиза: {release_type***REMOVED*** (patch / minor / major)

Шаги:
1. [ ***REMOVED*** Обновить CHANGELOG.md — перенести unreleased → version
2. [ ***REMOVED*** Обновить версию в __init__.py / package.json / Cargo.toml
3. [ ***REMOVED*** Проверить что все тесты проходят
4. [ ***REMOVED*** Создать git tag "v{version***REMOVED***"
5. [ ***REMOVED*** Собрать артефакты (wheel / binary / Docker image)
6. [ ***REMOVED*** Опубликовать (PyPI / npm / GitHub Releases / Docker Hub)
7. [ ***REMOVED*** Уведомить команду

Для каждого шага: команда / скрипт / ожидаемый результат.
```

### 17.2 Semantic Versioning Audit

```
Проверь корректность версионирования изменений.

Текущая версия: {current_version***REMOVED***
Предыдущая версия: {previous_version***REMOVED***
Изменения с предыдущей версии:
{changes***REMOVED***

Проверь:
1. **Major** (1.x → 2.0): breaking changes, удаление API
2. **Minor** (1.1 → 1.2): новые фичи, deprecation без удаления
3. **Patch** (1.1.1 → 1.1.2): bug fixes, performance, docs

Нарушения:
- Если есть breaking changes: bump major
- Если есть новые фичи: bump minor
- Если только багфиксы: bump patch

Формат:
| Изменение | Тип | Версия | Корректно? |
|-----------|-----|--------|------------|
| {change***REMOVED*** | {type***REMOVED*** | {version***REMOVED*** | ✅/❌ |
```

### 17.3 Changelog generation

```
Сгенерируй CHANGELOG на основе git log.

Диапазон: {from_ref***REMOVED*** → {to_ref***REMOVED*** (main branch)
Формат: Keep a Changelog (https://keepachangelog.com)
Категории: Added / Changed / Deprecated / Removed / Fixed / Security

Правила группировки:
- feat: → Added
- fix: → Fixed
- refactor: → Changed
- docs: → Changed (если значительные)
- security: → Security
- chore/deps: → опустить (не significant)

Сгенерируй Markdown с группировкой по категориям и ссылками на PR.
```

---

## 18. Генерация кода / Прототипирование

### 18.1 Быстрый прототип

```
Создай прототип для {feature***REMOVED***.

Язык: {language***REMOVED***
Время: {time_limit***REMOVED*** (30 мин / 1 час / 1 день)
Ключевые функции: {core_functions***REMOVED***
Что НЕ нужно: {out_of_scope***REMOVED*** (auth, persistence, UI polish)

Генерация:
1. Single-file прототип (всё в одном файле для скорости)
2. Тестовые данные для демонстрации
3. CLI команда или curl пример для тестирования

Пометки:
- TODO: {что нужно доработать для production***REMOVED***
- FIXME: {известные проблемы***REMOVED***
```

### 18.2 Скрипт автоматизации

```
Напиши скрипт для автоматизации {task***REMOVED***.

Входные данные: {input***REMOVED***
Выходные данные: {output***REMOVED***
Частота запуска: {frequency***REMOVED*** (разово / cron / on-demand)
Окружение: {environment***REMOVED*** (Linux / Termux / macOS)

Требования:
1. Идемпотентность (повторный запуск безопасен)
2. Логирование (stdout + файл)
3. Обработка ошибок (try/except, retry, fallback)
4. Progress bar (если долгий)
5. Exit code (0 = success, 1 = error)

Формат: Python 3.11+ скрипт с argparse.
```

### 18.3 Шаблон модуля

```
Создай шаблон нового модуля {module_name***REMOVED***.

Категория: {category***REMOVED*** (core / extension / lab)
Зависимости: {dependencies***REMOVED***
API: {api_description***REMOVED***

Структура:
```
freebuff_plugin/{category***REMOVED***/{module***REMOVED***/
  __init__.py       # публичный API, dataclasses, типы
  engine.py         # основная логика
  config.py         # настройки, defaults
  errors.py         # кастомные исключения
  # ...

Файлы должны содержать:
- __init__.py: docstring модуля, все публичные импорты
- engine.py: класс {ModuleName***REMOVED***Engine с run() методом
- config.py: @dataclass Config с полями и defaults
- errors.py: {ModuleName***REMOVED***Error(Exception), {ModuleName***REMOVED***Warning
```

---

*Связанные документы: [BOOTSTRAP_SPECIFICATION.md***REMOVED***(../core/BOOTSTRAP_SPECIFICATION.md), [EVENT_PLATFORM_SPECIFICATION.md***REMOVED***(../core/EVENT_PLATFORM_SPECIFICATION.md), [freebuff_plugin/scenarios/***REMOVED***(../../freebuff_plugin/scenarios), [PROMPT_BASE.md***REMOVED***(PROMPT_BASE.md)*
