# ADR-006: Lightpanda Headless Browser Integration

**Дата:** 2026-07-28
**Статус:** ✅ Принято
**Контекст:** Phase 4, веб-автоматизация для Buffy

## Проблема

Для веб-автоматизации (скрапинг, поиск, тестирование) нужен headless-браузер. Chrome/Chromium слишком тяжёлые для Termux ARM64.

## Альтернативы

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A. Playwright/Chromium** | Зрелый API | >1 GB RAM, OOM-kill, сложная установка |
| **B. requests + BeautifulSoup** | Лёгкий | Не работает с JS-сайтами |
| **C. Lightpanda** | Лёгкий (123 MB), быстрый, Agent Mode, CDP, MCP | Beta, требует glibc/proot |

## Решение

Выбран **вариант C**: Lightpanda через `proot-distro Ubuntu`.

## Ключевые решения

1. **proot-distro Ubuntu** — предоставляет glibc без root на Android.
2. **Wrapper `.tools/lightpanda`** — делегирует вызовы в proot.
3. **Python-класс `LightpandaWorker`** — унифицированный API для скриптов и агента.
4. **Stateless subprocess** — каждый запрос = новый процесс, устойчив к OOM.
5. **CDP-сервер** — background `Popen` для Puppeteer/Playwright.

## Документация

- [docs_10/projects_meta/LIGHTPANDA_INTEGRATION.md***REMOVED***(../../../docs_10/projects_meta/LIGHTPANDA_INTEGRATION.md)
- [src_06/workers/lightpanda_worker.py***REMOVED***(../../../src_06/workers/lightpanda_worker.py)
- [scripts_01/install_lightpanda.sh***REMOVED***(../../../scripts_01/install_lightpanda.sh)
- [tests_09/test_lightpanda_worker.py***REMOVED***(../../../tests_09/test_lightpanda_worker.py)

## Связанные ADR

- [ADR-007***REMOVED***(ADR_001_Vision_3.0_AI_Infrastructure_Layer.md) — Vision 3.0: AI Infrastructure Layer
- Индекс всех ADR: [DECISIONS.md***REMOVED***(../../decisions/DECISIONS.md)
