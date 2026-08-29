# Test Suite Runbook — запуск полного тестирования платформы

> **Скрипт:** `scripts_01/run_test_suite.sh`
> **Версия:** v5.189.79+
> **Окружение:** Termux на Android (ARM64/aarch64)

---

## Быстрый старт

```bash
# Из корня репозитория:
bash scripts_01/run_test_suite.sh --all
```

Скрипт сам всё запустит и сохранит структурированный MD-отчёт.  
Вам останется только **прислать сгенерированный MD-файл агенту**.

---

## Режимы запуска

| Команда | Что делает | Примерное время |
|---------|-----------|----------------|
| `bash scripts_01/run_test_suite.sh --quick` | Router smoke + Artifact + ADR-018 + реестры + AST-счётчик | ~30 секунд |
| `bash scripts_01/run_test_suite.sh --full` | Всё из quick + полный `pytest tests_09/` (до 15 мин) | ~10–15 минут |
| `bash scripts_01/run_test_suite.sh --all` | **Всё:** quick + full + mypy factory_base + artifact + реестры | ~15–20 минут |
| `bash scripts_01/run_test_suite.sh --all --skip-mypy` | Всё кроме mypy | ~15 минут |
| `bash scripts_01/run_test_suite.sh --all --skip-full` | Всё кроме полного pytest | ~2 минуты |

---

## Что делает скрипт

Скрипт последовательно запускает:

1. **Quick smoke** (~30 сек)
   - `pytest tests_09/core/test_router.py::TestSmartRouterAvailability -q`
   - `pytest tests_09/test_artifact.py tests_09/test_adr018_factory_forge_bridge.py -q`

2. **Full suite** (~10–15 мин, опционально)
   - `pytest tests_09/ -q`
   - Таймаут: 15 минут

3. **mypy type-check** (~2–5 мин, опционально)
   - `mypy core_02/factory_base.py --ignore-missing-imports`
   - `mypy core_02/artifact.py --ignore-missing-imports`

4. **Registry + consistency** (~15 сек)
   - `python -m core_02.missing_registry check`
   - `python -m scripts_01.consistency_check --report`

5. **AST test counter** (~3 сек)
   - Подсчёт тестовых функций через AST

### Результат

Каждый этап записывается в структурированный MD-файл с:
- выводом команды,
- exit code,
- временем выполнения,
- статус-иконкой (`✅` PASS / `❌` FAIL / `⏱️` TIMEOUT).

---

## Где искать результат

```bash
# Автоматический путь (с timestamp):
docs_10/runbook/TEST_RESULT_20260822_161958.md

# Или задать свой путь:
bash scripts_01/run_test_suite.sh --all --out /tmp/my_test_result.md
```

После выполнения скрипт выводит:

```
════════════════════════════════════════════
  Test suite complete
  Report: docs_10/runbook/TEST_RESULT_20260822_161958.md
════════════════════════════════════════════
```

---

## Что прислать агенту

Достаточно **пути к сгенерированному MD-файлу**:

```
тесты готовы, результат в docs_10/runbook/TEST_RESULT_20260822_161958.md
```

Или скопировать содержимое файла в чат.

Агент сам прочитает MD, извлечёт статусы фаз и сверит с ожидаемыми.

---

## Алиасы (Termux / bash)

Зарегистрированы в `~/.bash_aliases` (подхватываются `~/.bashrc` автоматически):

```bash
alias fulltest='cd /storage/emulated/0/PROJECTS/workstation/freebuff && bash scripts_01/run_test_suite.sh --all'
alias quicktest='cd /storage/emulated/0/PROJECTS/workstation/freebuff && bash scripts_01/run_test_suite.sh --quick'
```

- `fulltest` — полный прогон (~15-20 мин, все фазы + mypy).
- `quicktest` — быстрый smoke (~30 сек: Router + Artifact + реестры).

Чтобы активировать в текущем терминале: `source ~/.bash_aliases` (или переоткрыть сессию).
Если путь репозитория на устройстве другой — поправить `cd` внутри алиаса.

---

## Примечания

- **Таймауты:** full-suite (15 мин), mypy factory_base (5 мин), mypy artifact (2 мин). Если этап не уложился — в отчёте будет `⏱️ TIMEOUT`, скрипт продолжит.
- **Несовместимости окружения:** тест `test_route_filters_unavailable_local_provider` может падать из-за differences в доступных провайдерах (SmartRouter). Это **expected** для некоторых окружений, не регрессия кода.
- **Python 3.12+:** скрипт совместим с Python 3.12–3.14 (Termux).

---

## Troubleshooting

| Симптом | Действие |
|---------|----------|
| `ModuleNotFoundError: No module named 'yaml'` | `pip install pyyaml` |
| `permission denied: scripts_01/run_test_suite.sh` | `chmod +x scripts_01/run_test_suite.sh` |
| Тесты висят на network-related test | Дождаться таймаута или `Ctrl+C` — фаза будет помечена `TIMEOUT` |
| mypy не завершается | Дождаться таймаута (5 мин) — фаза будет `TIMEOUT`, скрипт продолжит |