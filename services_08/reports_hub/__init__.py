"""Reports Hub — сервис отчётов платформы Workspace OS.

Генерирует красивые Apple-style отчёты (mobile-first, light+dark) из
Markdown-документации проектов: хронология этапов + метрики +
roadmap/что дальше + проблемы/блокеры + библиотека документов.

Спека: ``reports-hub-spec.md`` (корень репозитория).
Поток B (H1–H6) роадмапа v7 печатника.

Архитектура (спека §4):
- Additive: только читает проекты через их owner-файлы, ничего не переписывает.
- Contract First: внутренняя модель — ``report.model.ReportModel``
  (dataclass-контракт, JSON-сериализуемый, версионируется ``schema_version``).
- Single Source of Truth: факты из исходных доков; правки резюме только
  через override-файлы (``summaries.json``), переживающие перегенерацию.
- Observability: каждая генерация пишет ``site/manifest.json``.
- Graceful degradation: нет git-истории → раздел скрывается, не падает.

Использование:
    python -m services_08.reports_hub generate --all
    python -m services_08.reports_hub serve --port 8310
"""

from __future__ import annotations

__all__ = ["SCHEMA_VERSION"]

#: Версия контракта ReportModel. Поднимается при несовместимом изменении модели.
SCHEMA_VERSION = 1
