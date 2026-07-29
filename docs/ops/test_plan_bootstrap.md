# TEST PLAN — Bootstrap Engine

> **Версия:** 1.0.0  
> **Дата:** 2026-07-29  
> **Компонент:** `freebuff_plugin/bootstrap/` (8 файлов)  
> **Существующие тесты:** 53 (в `tests/test_bootstrap_engine.py`)  
> **Основание:** [BOOTSTRAP_SPECIFICATION.md***REMOVED***(BOOTSTRAP_SPECIFICATION.md), [PROMPT_BASE.md***REMOVED***(PROMPT_BASE.md) §6.3  

---

## 1. Цель нагрузочного тестирования

Проверить Bootstrap Engine под нагрузкой:
- **50 RPS** на `check()` / `check_quick()` — быстрые проверки окружения
- **10 concurrent** запросов к `get_status()` / `list_profiles()` — read-only операции
- **Максимальная латентность:** 500ms на `check_quick()`, 2000ms на `run()`
- **Память:** < 50MB на инстанс Engine, < 100MB на `run()`

---

## 2. Профиль нагрузки

| Сценарий | RPS | Concurrency | Длительность | Метрики |
|----------|-----|-------------|--------------|---------|
| **A: Быстрые проверки** | 50 | 5 | 30s | check_quick() latency, error rate |
| **B: Полный цикл** | 5 | 3 | 30s | run() latency, error rate |
| **C: Read-only API** | 30 | 10 | 20s | get_status(), list_profiles() |
| **D: Смешанная** | 50 | 10 | 60s | все операции, долговременная стабильность |

---

## 3. Инструменты

### Python: `locust` (рекомендуемый)

```python
# locustfile.py — файл для locust
from locust import HttpUser, task, between
import json

class BootstrapUser(HttpUser):
    wait_time = between(0.02, 0.1)  # ~10-50 RPS

    @task(3)
    def check_quick(self):
        """Быстрая проверка — самый частый сценарий"""
        self.client.post("/api/v1/bootstrap/check", json={"mode": "quick"***REMOVED***)

    @task(1)
    def full_bootstrap(self):
        """Полный bootstrap — редкий, тяжёлый"""
        self.client.post("/api/v1/bootstrap/run", json={"profile": "minimal"***REMOVED***)

    @task(2)
    def get_status(self):
        """Статус — частый read-only запрос"""
        self.client.get("/api/v1/bootstrap/status")

    @task(2)
    def list_profiles(self):
        """Список профилей — лёгкий read-only"""
        self.client.get("/api/v1/bootstrap/profiles")
```

### CLI: `hey` (альтернатива)

```bash
# Быстрая проверка (50 RPS, 30s)
hey -n 1500 -c 5 -q 50 -m POST \
  -H "Content-Type: application/json" \
  -d '{"mode": "quick"***REMOVED***' \
  http://localhost:8000/api/v1/bootstrap/check

# Статус (30 RPS, 20s)
hey -n 600 -c 10 -q 30 \
  http://localhost:8000/api/v1/bootstrap/status
```

---

## 4. Сценарии тестирования

### Сценарий 1: Быстрые проверки (30s, 50 RPS)

| Шаг | Действие | Ожидаемый результат |
|-----|----------|---------------------|
| 1 | Вызвать `check_quick()` 1500 раз | < 500ms p95, 0 errors |
| 2 | Проверить `os_type` | Должен быть определён |
| 3 | Проверить `python_version` | Должна быть непустая |
| 4 | Проверить `git_available` | Должен быть булев |

### Сценарий 2: Полный bootstrap (30s, 5 RPS)

| Шаг | Действие | Ожидаемый результат |
|-----|----------|---------------------|
| 1 | Вызвать `run(profile="minimal")` 150 раз | < 2000ms p95, 0 errors |
| 2 | Проверить `success == True` | Bootstrap завершён |
| 3 | Проверить `profile == "minimal"` | Профиль применён |
| 4 | Проверить `environment.python_version` | Версия определена |

### Сценарий 3: Read-only API (20s, 30 RPS)

| Шаг | Действие | Ожидаемый результат |
|-----|----------|---------------------|
| 1 | Вызвать `get_status()` 600 раз | < 100ms p95, 0 errors |
| 2 | Вызвать `list_profiles()` 600 раз | < 100ms p95, 0 errors |

### Сценарий 4: Смешанная нагрузка (60s, 50 RPS)

| Шаг | Действие | Ожидаемый результат |
|-----|----------|---------------------|
| 1 | Смешанный сценарий (пропорции из locustfile) | < 500ms p95, < 1% errors |
| 2 | Мониторинг памяти | < 100MB |

---

## 5. Критерии успеха

| Метрика | Цель | Предел |
|---------|------|--------|
| **`check_quick()` p95 latency** | < 200ms | < 500ms |
| **`check()` p95 latency** | < 500ms | < 1000ms |
| **`run()` p95 latency** | < 1000ms | < 2000ms |
| **`get_status()` p95 latency** | < 50ms | < 100ms |
| **Error rate** | 0% | < 1% |
| **Memory per Engine instance** | < 50MB | < 100MB |
| **Memory during `run()`** | < 100MB | < 200MB |

---

## 6. Условия тестирования

### Среда
- Python 3.11+
- Linux / Termux
- CPU: минимум 2 cores
- RAM: минимум 1 GB свободной
- Disk: минимум 100 MB свободных

### Подготовка

> ⚠️ Bootstrap Engine — библиотечный класс без встроенного HTTP API. Перед нагрузочным тестированием необходимо обернуть Engine в FastAPI эндпоинты.

```bash
# 1. Установка инструментов
pip install locust fastapi uvicorn  # для нагрузочного теста
# или: apt install hey  # для CLI теста

# 2. Создать HTTP обёртку для BootstrapEngine
# Примерный файл test_server.py:
#
# from fastapi import FastAPI
# from freebuff_plugin.bootstrap.engine import BootstrapEngine
#
# app = FastAPI()
# engine = BootstrapEngine()
#
# @app.post("/api/v1/bootstrap/check")
# def check(data: dict):
#     if data.get("mode") == "quick":
#         return engine._checker.check_quick().__dict__
#     return engine.check().__dict__
#
# @app.get("/api/v1/bootstrap/status")
# def status():
#     return engine.get_status()
#
# @app.get("/api/v1/bootstrap/profiles")
# def profiles():
#     return {"profiles": engine.list_profiles()***REMOVED***
#
# @app.post("/api/v1/bootstrap/run")
# def run(data: dict):
#     eng = BootstrapEngine(profile=data.get("profile", "minimal"))
#     return eng.run().__dict__

# 3. Запуск HTTP сервера
uvicorn test_server:app --host 0.0.0.0 --port 8000 &

# 4. Unit тесты сначала
python -m pytest tests/test_bootstrap_engine.py -v --tb=short

# 5. Убедиться что все 53 unit-теста проходят
```

### Очистка
```bash
# Удалить временные файлы bootstrap_state.json
find /tmp -name "bootstrap_state.json" -delete
```

---

## 7. Формат отчёта

### Шаблон результата

```
# Отчёт нагрузочного тестирования Bootstrap Engine

Дата: {date***REMOVED***
Версия: {version***REMOVED***
Окружение: {os***REMOVED*** / Python {python_version***REMOVED*** / RAM {ram_gb***REMOVED***GB

## Сводка
| Сценарий | RPS | Concurrency | Среднее | P95 | P99 | Max | Errors |
|----------|-----|-------------|---------|-----|-----|-----|--------|
| Быстрые проверки | 50 | 5 | {ms***REMOVED*** | {ms***REMOVED*** | {ms***REMOVED*** | {ms***REMOVED*** | {n***REMOVED*** |
| Полный bootstrap | 5 | 3 | {ms***REMOVED*** | {ms***REMOVED*** | {ms***REMOVED*** | {ms***REMOVED*** | {n***REMOVED*** |
| Read-only API | 30 | 10 | {ms***REMOVED*** | {ms***REMOVED*** | {ms***REMOVED*** | {ms***REMOVED*** | {n***REMOVED*** |
| Смешанная | 50 | 10 | {ms***REMOVED*** | {ms***REMOVED*** | {ms***REMOVED*** | {ms***REMOVED*** | {n***REMOVED*** |

## Память
| Сценарий | До (MB) | После (MB) | Diff |
|----------|---------|-----------|------|
| Полный bootstrap | {mb***REMOVED*** | {mb***REMOVED*** | {mb***REMOVED*** |

## Вердикт
✅/❌ Все метрики в пределах нормы
```

---

*Связанные документы: [BOOTSTRAP_SPECIFICATION.md***REMOVED***(BOOTSTRAP_SPECIFICATION.md), [AUDIT_BOOTSTRAP.md***REMOVED***(AUDIT_BOOTSTRAP.md), [tests/test_bootstrap_engine.py***REMOVED***(../tests/test_bootstrap_engine.py)*
