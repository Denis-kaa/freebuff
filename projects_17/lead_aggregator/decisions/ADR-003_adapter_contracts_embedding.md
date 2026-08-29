# ADR-003: Контракты-адаптеры (TLSClient/ProxyRotator/CheckpointStore) — встраивание вместо платформенных импортов

**Status:** Accepted (2026-08-10)
**Component:** Attract-модуль — интеграционные абстракции
**Scope:** PROJECT-LOCAL
**Related:** [MANIFEST.md***REMOVED***(../MANIFEST.md) · [PHASE2_ARCHITECTURE.md***REMOVED***(../PHASE2_ARCHITECTURE.md) · [ROADMAP.md***REMOVED***(../ROADMAP.md) §2 (capability-check) · Platform: [PROJECT_MIGRATION_TEMPLATE.md***REMOVED***(../../../docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md) §2 (самодостаточность)

---

## 1. Context

Ограничения среды (W-2/W-3/W-5 из PHASE1): Termux/ARM64, Python 3.14.6, SQLite-only; отсутствуют curl_cffi/playwright/PG/Redis. Промт 69 требует TLS-impersonation, прокси, PostgreSQL/Redis, async. Прямые платформенные импорты (`scripts_01/model_gateway.py` и др.) связали бы проект с платформой — против аддитивности и портируемости.

## 2. Decision

- **Абстракции живут ВНУТРИ проекта** (`app/`):
  - `TLSClient` — интерфейс TLS-impersonation; **v1 на httpx** (уже в среде), curl_cffi — optional install (W-2).
  - `ProxyRotator` — интерфейс ротации прокси; **stub v1**, реализация после выбора провайдера.
  - `CheckpointStore` — чекпоинты/дедупликация; **SQLite v1** (W-3), контракт позволяет PG/Redis позже.
- **Reuse платформы — по контракту, не по импорту:** L3-скоринг через `scripts_01/model_gateway.py` — вызов через интерфейс (fallback на L2-only при недоступности), не прямой импорт из кода адаптеров.
- **Цель:** `grep freebuff_plugin|core_02|scripts_01` в `app/` → 0 (проверяемо, тестируемо, мигрируемо).

## 3. Альтернативы, которые рассматривались

- **Прямые импорты платформы** — **rejected**: нарушает аддитивность (ANTI-5), блокирует миграцию (протокол §2), связывает версии.
- **Установка полного стека промта 69** (curl_cffi/playwright/PG/Redis) — **rejected**: риск несовместимости с Python 3.14.6/Termux (W-2), избыточно для v1.
- **Контракты-адаптеры (принято)** — интерфейс + v1-реализация + контракт будущего расширения.

## 4. Consequences

- ✅ Проект автономен и переносим (миграция — копирование каталога + контракты).
- ✅ Проверяемо: grep-инвариант «0 платформенных ИМПОРТОВ в app/» закреплён тестами (26+).
- ⚠️ L3-скоринг зависит от внешней ModelGateway → fallback L2-only при недоступности.
- ⚠️ TLS-impersonation v1 (httpx) слабее curl_cffi — компромисс за портируемость, зафиксирован.

## 5. Live-верификация (2026-08-10, v5.147.0)

```bash
$ grep -rnE 'freebuff_plugin|core_02|scripts_01' app/ config/ | grep -v .pyc
# 4 совпадения — ВСЕ docstring/комментарии (provenance), НЕ import-операторы:
#   app/core/retry_policy.py:4       «Паттерн переиспользован из scripts_01/notification.py»
#   app/storage/checkpoint_store.py:5 «core_02/workspace_registry.py … контракт расширяем»
#   app/processors/scorer.py:5,24    «переиспользуется scripts_01/model_gateway.py … опциональный gateway»

$ grep -rnE '^(import|from)\s+(freebuff_plugin|core_02|scripts_01)' app/  → 0 hits ✅
```

**Вывод:** проект мигрируем по протоколу §2/§5: 0 реальных импортов; docstring-упоминания платформы — допустимый provenance (разъяснение паттерна reuse), не зависимость.
