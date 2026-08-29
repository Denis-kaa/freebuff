# Local Test Request — v5.189.79 platform validation

> Запускать команды **из корня репозитория** на телефоне/в Termux.
> Этот файл предназначен для локального запуска пользователем; не вставляйте в отчёт секреты, API-ключи и токены.

## Цель

Проверить после исправления SmartRouter flaky-теста:

1. что availability-тесты роутера hermetic;
2. что Artifact и ADR-018 не получили регрессий;
3. что полный `tests_09` проходит в пользовательском окружении;
4. что долгий mypy-прогон `factory_base.py` завершается или явно фиксируется как timeout.

## Окружение

- Python из текущего Termux-окружения;
- зависимости проекта уже установлены из `requirements.txt`;
- для hermetic-тестов внешняя сеть и API-ключи не нужны;
- полный suite может затрагивать environment-dependent проверки.

## 1. Быстрый smoke-тест роутера

```bash
python3 -m pytest tests_09/core/test_router.py::TestSmartRouterAvailability -q
```

Ожидаемый результат: **4 passed, 0 failed**.

## 2. Регрессия Artifact + ADR-018

```bash
python3 -m pytest tests_09/test_artifact.py tests_09/test_adr018_factory_forge_bridge.py -q
```

Ожидаемый результат: **19 passed, 0 failed**.

## 3. Полный suite

```bash
python3 -m pytest tests_09/ -q
```

Допустимый timeout: **15 минут**.

Ожидаемый результат: все собранные тесты `passed`, `0 failed`, `0 errors`. Число passed прислать фактическое, не подставлять из документации.

Если прогон слишком долго не завершается, остановите его по timeout и пришлите последние 30–50 строк вывода.

## 4. Длинная type-check проверка

```bash
python3 -m mypy core_02/factory_base.py --ignore-missing-imports
```

Допустимый timeout: **5 минут**.

Успех: `Success: no issues found` либо фактический список диагностик. Если команда не завершилась — указать `TIMEOUT` и время остановки.

## 5. Реестры и consistency

```bash
python3 -m core_02.missing_registry check
python3 -m scripts_01.consistency_check --report
```

Ожидается:

- MissingRegistry: `46 записей валиден` / эквивалентное сообщение с exit code 0;
- consistency: `exit 0`, `All canonical registries agree with the codebase`.

## Формат отчёта

```text
### Local validation result

Environment: <Python version / Termux, если известно>

1. Router smoke:
   Exit code: <0/other>
   Result: <N passed / failures>

2. Artifact + ADR-018:
   Exit code: <0/other>
   Result: <N passed / failures>

3. Full tests_09:
   Exit code: <0/other/timeout>
   Result: <N passed, N failed, N errors, N xpassed>
   Last output:
   <последние строки>

4. mypy factory_base:
   Exit code: <0/other/timeout>
   Result: <clean / diagnostics / timeout>

5. Registry + consistency:
   MissingRegistry: <результат>
   consistency_check: <результат>

Unexpected failures:
<команды и traceback, если есть>
```
