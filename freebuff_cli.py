#!/usr/bin/env python3
"""
freebuff — CLI для управления системой Freebuff.
v1.0.0: 7 команд для работы с сессиями, контекстом и мониторингом.

Использование:
    python freebuff_cli.py start termux-ai-agent "v4.0 architecture"
    python freebuff_cli.py status
    python freebuff_cli.py resume
    python freebuff_cli.py conspect
    python freebuff_cli.py list
    python freebuff_cli.py checkpoint "Обсудили архитектуру"
    python freebuff_cli.py restore
    python freebuff_cli.py qwen-resume <session_id>
    python freebuff_cli.py task start "Название задачи" "Описание"
    python freebuff_cli.py task archive
    python freebuff_cli.py project-book
    python freebuff_cli.py project-book "Workspace OS"
    python freebuff_cli.py project-context "July 31 Crisis"
    python freebuff_cli.py resource link "CRM" "Telegram"
    python freebuff_cli.py resource projects "Telegram"   # Work Area as View
    python freebuff_cli.py policy list                    # User Preferences (правило 11)
    python freebuff_cli.py policy set coding "deepseek-v4-flash"
    python freebuff_cli.py policy get coding
    python freebuff_cli.py policy unset coding
    python freebuff_cli.py policy resolve research         # какой Runtime выберет система
    python freebuff_cli.py policy override "use deepseek instead of claude for coding"

Архитектура по Kwork Arbitr v3:
    Explainer → LISA (TC=5 Medium) → Decomposer → Architect → Developer → Tester → Acceptance
"""
import os
import shutil
import sys
from datetime import datetime, timezone
}

WORKSPACE = os.environ.get("FREEBUFF_ROOT", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE)

PROJECT_BOOK_PATH = Path(WORKSPACE) / "docs_10" / "engineering-memory" / "PROJECT_BOOK.md"

from scripts_01.context_manager import ContextManager, SessionStatus, CheckpointType
from scripts_01.system_monitor import health_check
from scripts_01.context_builder import ContextBuilder
from scripts_01.event_bus import get_default_event_bus
from scripts_01.seed_knowledge import seed as seed_knowledge
from scripts_01.session_utils ]solve_session_id

# MANDATORY RUNTIME CONTRACT (v5.24.0): системные уведомления о завершении CLI-задач.
# Graceful degradation: если notification-модуль недоступен (FREEBUFF_NO_NOTIFY=1
# или ImportError) — CLI работает как раньше, без уведомлений.
# Все вызовы ниже защищены флагом _HAS_NOTIFICATION, поэтому отдельные
# no-op фолбэки не нужны (dead code исключён).
try:
    from scripts_01.notification import notify_error, notify_task_complete

    _HAS_NOTIFICATION = True
except ImportError:
    _HAS_NOTIFICATION = False
    notify_task_complete = None
    notify_error = None


# ── TASK.md helpers ────────────────────────────────────────────

def _task_path() -> Path:
    return Path(WORKSPACE) / "TASK.md"


def _archive_task_path() -> Path:
    archive_dir = Path(WORKSPACE) / "docs_10" / "task_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    return archive_dir / f"TASK_{ts}.md"


def _archive_current_task() -> Path | None:
    """Archive current TASK.md if it exists. Returns archive path or None."""
    current = _task_path()
    if not current.exists():
        return None
    archive = _archive_task_path()
    shutil.copy2(current, archive)
    return archive


# ── Project Book helpers ─────────────────────────────────────

def _load_project_book() -> str:
    """Возвращает содержимое Project Book или пустую строку, если файл отсутствует."""
    try:
        return PROJECT_BOOK_PATH.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def _project_book_headings(text: str) -> list[str]:
    """Извлекает список заголовков второго уровня (##) из Project Book."""
    return [line.strip()[3:].strip() for line in text.splitlines() if line.strip().startswith("## ")]


def _project_book_chapter(text: str, chapter_query: str) -> str:
    """Извлекает главу по номеру или подстроке заголовка.

    Args:
        text: содержимое Project Book.
        chapter_query: номер главы ("3") или подстрока заголовка ("Workspace OS").

    Returns:
        Текст главы с заголовком или пустая строка, если не найдена.
    """
    if not text:
        return ""

    lines = text.splitlines()
    query_lower = chapter_query.lower()

    # Если запрос — число, ищем "Глава N."
    is_number = query_lower.isdigit()

    start_idx = -1
    for i, line in enumerate(lines):
        heading = line.strip()
        if not heading.startswith("## "):
            continue
        title = heading[3:].strip().lower()
        if is_number and f"глава {query_lower}" in title:
            start_idx = i
            break
        if query_lower in title:
            start_idx = i
            break

    if start_idx < 0:
        return ""

    # Идём до следующего заголовка второго уровня
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if lines[j].strip().startswith("## "):
            end_idx = j
            break

    return "\n".join(lines[start_idx:end_idx]).strip()


def _project_book_context(text: str, query: str, limit: int = 10) -> str:
    """Находит абзацы, содержащие запрос, с небольшим контекстом.

    Args:
        text: содержимое Project Book.
        query: поисковый запрос.
        limit: максимальное количество абзацев.

    Returns:
        Строка с найденными абзацами или пустая строка.
    """
    if not text or not query:
        return ""

    query_lower = query.lower()
    # Разбиваем на абзацы по пустым строкам, сохраняя позицию в тексте
    paragraphs = []
    current = []
    for line in text.splitlines():
        if line.strip():
            current.append(line)
        else:
            if current:
                paragraphs.append("\n".join(current))
                current = []
    if current:
        paragraphs.append("\n".join(current))

    matches = [p for p in paragraphs if query_lower in p.lower()]
    if not matches:
        return ""

    return "\n\n".join(matches[:limit])


def cmd_task_start(title: str, description: str = "") -> None:
    """Создаёт новую TASK.md, архивируя предыдущую."""
    if not title:
        print("❌ Укажи заголовок задачи: python freebuff_cli.py task start 'Название задачи'")
        return

    archive = _archive_current_task()

    task_md = f"""# TASK: {title}

**Статус:** активна  
**Создана:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}  
**Описание:** {description or '(нет)'}  

## Цель

<!-- Опиши цель задачи -->

## Шаги

- [ ] Шаг 1

## Связанные файлы

- `README.md`
- `TASK.md`

## Контекст

<!-- Дополнительный контекст, конспекты, ссылки -->
"""
    _task_path().write_text(task_md, encoding="utf-8")

    if archive:
        print(f"📦 Предыдущая TASK.md архивирована: {archive}")
    print(f"📝 Новая TASK.md создана: {title}")


def cmd_task_archive() -> None:
    """Вручную архивирует текущую TASK.md."""
    archive = _archive_current_task()
    if archive is None:
        print("⚠️ TASK.md не найден, нечего архивировать.")
        return
    print(f"📦 TASK.md архивирована: {archive}")


def cmd_start(project: str, topic: str = "") -> str:
    """Начинает новую сессию. Возвращает session_id."""
    cm = ContextManager(WORKSPACE)
    snap = cm.start_session(project=project, topic=topic)
    print(f"🟢 Сессия начата: {snap.session_id[:8]}")
    print(f"   Проект: {snap.project}")
    print(f"   Тема: {snap.topic or '(без темы)'}")
    return snap.session_id


def cmd_status() -> dict:
    """Статус системы: активные сессии, здоровье, последний конспект."""
    cm = ContextManager(WORKSPACE)

    # Активные сессии
    active = cm.list_sessions(SessionStatus.ACTIVE)
    paused = cm.list_sessions(SessionStatus.PAUSED)

    print("📊 СТАТУС FREEBUFF")
    print(f"   Активных сессий: {len(active)}")
    for s in active[:5]:
        print(f"   • {s['session_id'][:8]} | {s['project']} | {s['topic']} | {s['message_count']} msgs")

    if paused:
        print(f"   Приостановлено: {len(paused)}")

    # Последний конспект
    summaries_dir = os.path.join(WORKSPACE, "context_12", "summaries")
    if os.path.isdir(summaries_dir):
        files = sorted(
            [f for f in os.listdir(summaries_dir) if f.endswith(".md")],
            reverse=True,
        )
        if files:
            print(f"   Последний конспект: {files[0]}")

    # Здоровье системы
    health = health_check()
    print(f"\n💚 Здоровье: {'OK' if all(health.values()) else '⚠️ ПРОБЛЕМЫ'}")
    for k, v in health.items():
        icon = "✅" if v else "❌"
        print(f"   {icon} {k}")

    return {"active_sessions": len(active), "health": health}


def cmd_resume() -> str | None:
    """Восстанавливает последнюю активную сессию."""
    cm = ContextManager(WORKSPACE)

    # Ищем последнюю ACTIVE или CHECKPOINT сессию
    for status in [SessionStatus.ACTIVE, SessionStatus.CHECKPOINT]:
        sessions = cm.list_sessions(status)
        if sessions:
            s = sessions[0]
            print(f"🔄 Восстановлена сессия: {s['session_id'][:8]}")
            print(f"   Проект: {s['project']}")
            print(f"   Тема: {s['topic']}")
            print(f"   Сообщений: {s['message_count']}")

            # Показываем последний конспект
            summary = cm.get_last_summary(s['session_id'])
            if summary:
                print(f"   Последнее: {summary[:100]}")

            return str(s['session_id'])

    print("⚠️ Нет активных сессий для восстановления.")
    return None


def cmd_conspect(session_id: str | None = None) -> str:
    """Создаёт конспект сессии для инжекта в новый контекст."""
    cm = ContextManager(WORKSPACE)

    if session_id is None:
        active = cm.list_sessions(SessionStatus.ACTIVE)
        if not active:
            print("⚠️ Нет активных сессий.")
            return ""
        session_id = active[0]['session_id']

    full_id = resolve_session_id(cm, session_id)
    if full_id is None:
        print(f"❌ Сессия не найдена: {session_id[:8] if session_id else '?'}")
        return ""
    session_id = full_id

    conspect = cm.export_checkpoint_summary(session_id)
    if not conspect:
        print(f"❌ Конспект пуст для сессии {session_id[:8]}.")
        return ""

    print(conspect)
    return conspect


def cmd_list(status: str | None = None) -> list[dict]:
    """Список сессий с фильтром по статусу."""
    cm = ContextManager(WORKSPACE)
    status_enum = SessionStatus(status) if status else None
    sessions = cm.list_sessions(status_enum)

    if not sessions:
        print("📭 Сессий нет.")
        return []

    print(f"📋 Сессии ({len(sessions)}):")
    for s in sessions:
        icon = {"active": "🟢", "completed": "✅", "paused": "⏸️", "abandoned": "💤"}.get(
            s['status'], "❓"
        )
        print(
            f"   {icon} {s['session_id'][:8]} | {s['status']:10} | "
            f"{s['project']:20} | {s['topic'][:30]} | {s['message_count']} msgs"
        )
    return sessions


def cmd_checkpoint(session_id: str | None, summary: str) -> None:
    """Ручной чекпоинт. session_id может быть частичным (первые 8 символов)."""
    cm = ContextManager(WORKSPACE)

    if session_id is not None:
        full_id = resolve_session_id(cm, session_id)
        if full_id is None:
            print(f"❌ Сессия не найдена: {session_id[:8]}")
            return
        session_id = full_id

    if session_id is None:
        active = cm.list_sessions(SessionStatus.ACTIVE)
        if not active:
            print("⚠️ Нет активных сессий. Создайте сессию: python freebuff_cli.py start <project>")
            return
        session_id = active[0]['session_id']

    cm.save_checkpoint(session_id, summary, ctype=CheckpointType.MANUAL)
    print(f"📌 Чекпоинт сохранён: {summary[:80]}")


def cmd_seed() -> None:
    """Заполняет Knowledge Memory проектными документами и best practices.

    Повторный запуск безопасен: уже загруженные и неизменённые документы
    пропускаются.
    """
    try:
        bus = get_default_event_bus(WORKSPACE)
        count = seed_knowledge(workspace_root=WORKSPACE, event_bus=bus, rebuild=False)
        print(f"✅ Knowledge Memory синхронизирована: {count} записей.")
    except Exception as e:
        print(f"❌ Ошибка при заполнении Knowledge Memory: {e}")


def cmd_project_book(chapter: str | None = None) -> str:
    """Выводит Project Book: либо оглавление, либо конкретную главу.

    Args:
        chapter: номер главы или подстрока её заголовка. Если None —
                 выводится оглавление.

    Returns:
        Выведенный текст (для тестов).
    """
    text = _load_project_book()
    if not text:
        print("⚠️ Project Book не найден.")
        return ""

    if chapter:
        chapter_text = _project_book_chapter(text, chapter)
        if not chapter_text:
            print(f"❌ Глава не найдена: {chapter}")
            print("Доступные главы:")
            for h in _project_book_headings(text):
                print(f"  • {h}")
            return ""
        print(chapter_text)
        return chapter_text

    # По умолчанию — оглавление + введение
    headings = _project_book_headings(text)
    print("\n".join(headings))
    return "\n".join(headings)


def _project_book_summary() -> str:
    """Возвращает краткую сводку Project Book для включения в стартовый контекст."""
    text = _load_project_book()
    if not text:
        return ""
    headings = _project_book_headings(text)
    if not headings:
        return ""
    summary = "\n".join(f"  • {h}" for h in headings[:12])
    return f"""Книга проекта ({PROJECT_BOOK_PATH}):
{summary}
Запросить главу: python freebuff_cli.py project-book '<глава>'
Запросить контекст: python freebuff_cli.py project-context '<запрос>'"""


def cmd_project_context(query: str, limit: int = 10) -> str:
    """Ищет и выводит фрагменты Project Book, релевантные запросу.

    Args:
        query: поисковый запрос.
        limit: максимальное количество абзацев.

    Returns:
        Найденный текст или пустая строка.
    """
    text = _load_project_book()
    if not text:
        print("⚠️ Project Book не найден.")
        return ""

    if not query:
        print("❌ Укажи запрос: python freebuff_cli.py project-context '<query>'")
        return ""

    result = _project_book_context(text, query, limit=limit)
    if not result:
        print(f"🔍 По запросу '{query}' ничего не найдено.")
        return ""

    print(f"🔍 Результаты для '{query}':\n")
    print(result)
    return result


def cmd_buffy() -> None:
    """Генерирует Unified Context для старта диалога с Buffy.

    Автоматически собирает:
      - Memory Engine (Working + Project + Knowledge + Personal)
      - TASK.md — текущая задача
      - CHANGELOG.md — последние изменения
      - StreamBridge — последний конспект сессии
      - Project Book — ключевые главы и контекст проекта

    Выводит готовый промпт для вставки в начало диалога.
    """
    print("🔄 Building Unified Context...")

    # Собираем Unified Context
    builder = ContextBuilder(max_tokens=6000)
    unified_ctx = builder.build(
        include_task=True,
        include_changelog=True,
        include_session=True,
    )

    # Статус системы
    cm = ContextManager(WORKSPACE)
    active = cm.list_sessions(SessionStatus.ACTIVE)
    paused = cm.list_sessions(SessionStatus.PAUSED)
    health = health_check()

    system_status = f"""📊 СИСТЕМА FREEBUFF
   Активных сессий: {len(active)}
   Приостановлено: {len(paused)}
   Здоровье: {'✅ OK' if all(health.values()) else '⚠️ ПРОБЛЕМЫ'}
"""

    # Сохраняем Unified Context в файл
    ctx_path = os.path.join(WORKSPACE, "context_12", "unified_context.md")
    if unified_ctx:
        os.makedirs(os.path.dirname(ctx_path), exist_ok=True)
        with open(ctx_path, "w", encoding="utf-8") as f:
            f.write(unified_ctx)

    # Project Book summary для стартового контекста
    project_book_summary = _project_book_summary()

    # Формируем итоговый промпт
    if unified_ctx:
        print("╔══════════════════════════════════════════════════════╗")
        print("║      UNIFIED CONTEXT — СТАРТ ДИАЛОГА С BUFFY       ║")
        print("╚══════════════════════════════════════════════════════╝")
        print()
        print("📋 СКОПИРУЙ ЭТО В НАЧАЛО ДИАЛОГА:")
        print()
        print("=" * 60)
        print(unified_ctx)
        print("=" * 60)
        print()
        print(system_status)
        print(f"💾 Контекст сохранён: {ctx_path}")
        print(f"   Размер: {len(unified_ctx)} chars, ~{len(unified_ctx) // 4} токенов")
        if project_book_summary:
            print()
            print(project_book_summary)
    else:
        print("⚠️ Unified Context пуст (нет данных в памяти).")
        print()
        print("📋 Стартовый промпт для Buffy:")
        print("=" * 60)
        print("Я начинаю новую сессию. Расскажи кратко что было в прошлой сессии")
        print("и что мы продолжаем.")
        print("=" * 60)
        if project_book_summary:
            print()
            print(project_book_summary)


# ── Policy Engine helpers (правило 11: User-Choice Override) ──

def _get_policy_engine():
    """Lazy-инстанцирует PolicyEngine с реальными Runtime-реестрами.

    Правило 11 (User-Choice Override): пользователь назначает Runtime
    (модель/агента) на capability; система рекомендует, но не навязывает.

    Returns:
        PolicyEngine или None при ошибке инициализации (graceful degradation).
    """
    try:
        from freebuff_plugin_03.policy import PolicyEngine
        from freebuff_plugin_03.runtime.registry import (
            RuntimeCapabilityRegistry,
            RuntimeRegistry,
        )

        storage = Path(WORKSPACE) / "data_13" / "runtime_registry.json"
        registry = RuntimeRegistry(storage_path=storage)
        registry.load()
        cap_reg = RuntimeCapabilityRegistry(registry)
        return PolicyEngine(registry, cap_reg)
    except Exception as e:
        print(f"❌ PolicyEngine недоступен: {e}")
        return None


def cmd_policy(action: str | None, arg1: str | None = None, arg2: str | None = None) -> None:
    """User Preferences (правило 11, User-Choice Override): назначение Runtime на capabilities.

    Пользователь выбирает исполнителя (модель/агента) для каждого вида задач;
    система рекомендует автоматически, но пользователь может переопределить
    (см. promt37, ADR-009). Предпочтения хранятся в runtime_05/policies.json.

    Подкоманды:
        policy list                          — все назначенные предпочтения
        policy set <capability> <runtime>    — назначить Runtime на capability
        policy get <capability>              — показать предпочтение для capability
        policy unset <capability>            — сбросить предпочтение (вернуть авто-выбор)
        policy resolve <capability>          — какой Runtime выберет система (с учётом override)
        policy override <фраза>              — диалог: «use deepseek instead of claude for coding»
    """
    engine = _get_policy_engine()
    if engine is None:
        return

    if action == "list":
        policies = engine.list_policies()
        print(f"🎯 User Preferences ({len(policies)}):")
        if not policies:
            print("   (нет назначенных предпочтений — система выбирает автоматически)")
            return
        for cap, p in sorted(policies.items()):
            fb = ", ".join(p.fallback_chain) if p.fallback_chain else "—"
            print(f"   • {cap}: preferred={p.preferred_runtime or '—'} | fallback=[{fb}]")

    elif action == "set":
        if not arg1 or not arg2:
            print("❌ Укажи capability и runtime: python freebuff_cli.py policy set <capability> <runtime>")
            return
        engine.set_preference(arg1, arg2)
        print(f"✅ Назначено: {arg1} → {arg2} (сохранено в runtime_05/policies.json)")

    elif action == "get":
        if not arg1:
            print("❌ Укажи capability: python freebuff_cli.py policy get <capability>")
            return
        p = engine.get_policy(arg1)
        if p is None:
            print(f"ℹ️ Для '{arg1}' предпочтение не назначено (система выберет автоматически).")
            return
        fb = ", ".join(p.fallback_chain) if p.fallback_chain else "—"
        print(f"🎯 Политика '{arg1}':")
        print(f"   preferred = {p.preferred_runtime or '—'}")
        print(f"   fallback  = [{fb}]")
        print(f"   constraints = {len(p.constraints)}")

    elif action == "unset":
        if not arg1:
            print("❌ Укажи capability: python freebuff_cli.py policy unset <capability>")
            return
        cleared = engine.unset_preference(arg1)
        if cleared:
            print(f"🗑  Предпочтение сброшено: {arg1} (вернётся авто-выбор системы)")
        else:
            print(f"ℹ️ Для '{arg1}' предпочтение не было назначено.")

    elif action == "resolve":
        if not arg1:
            print("❌ Укажи capability: python freebuff_cli.py policy resolve <capability>")
            return
        runtime = engine.select_runtime(arg1)
        if runtime:
            print(f"🎯 Для '{arg1}' система выберет: {runtime}")
        else:
            print(f"⚠️ Для '{arg1}' подходящий Runtime не найден.")

    elif action == "override":
        # Conversational User-Choice Override (правило 11): «используй X вместо Y»
        if not arg1:
            print("❌ Укажи фразу: python freebuff_cli.py policy override \"use deepseek instead of claude for coding\"")
            return
        from freebuff_plugin_03.policy.conversational import apply_override
        result = apply_override(arg1, engine)
        if result and result.get("applied"):
            prev = result.get("previous_runtime") or "авто-выбор системы"
            print(f"✅ User-Choice Override: {result['capability']} → {result['runtime']} "
                  f"(было: {prev}, сохранено в runtime_05/policies.json)")
        else:
            print(f"⚠️ Не удалось распознать переопределение в: \"{arg1}\"")
            print("   Примеры: \"use deepseek instead of claude for coding\",")
            print("            \"используй freebuff для research\", \"switch coding to claude-code\"")

    else:
        print("Использование:")
        print("  python freebuff_cli.py policy list")
        print("  python freebuff_cli.py policy set <capability> <runtime>")
        print("  python freebuff_cli.py policy get <capability>")
        print("  python freebuff_cli.py policy unset <capability>")
        print("  python freebuff_cli.py policy resolve <capability>")
        print('  python freebuff_cli.py policy override "use deepseek instead of claude for coding"')


def cmd_resource(action: str | None, arg1: str | None = None, arg2: str | None = None) -> None:
    """Work Area as View (канон promt36/37, правило 2): проекты, связанные с ресурсом.

    Work Area — НЕ папка и НЕ сущность, а динамический список проектов,
    связанных с конкретным Resource (таблица `project_resources` в data_13/context.db).

    Подкоманды:
        resource link <project> <resource>        — связать проект с ресурсом
        resource unlink <project> <resource>      — удалить связь
        resource projects <resource>              — список проектов для ресурса (View)
        resource resources <project>              — список ресурсов для проекта
        resource list                             — все связи
    """
    from scripts_01.work_area_view import (
        link as wav_link,
        unlink as wav_unlink,
        print_projects,
        resources_for_project,
        list_links,
    )

    if action == "link":
        if not arg1 or not arg2:
            print("❌ Укажи проект и ресурс: python freebuff_cli.py resource link <project> <resource>")
            return
        created = wav_link(arg1, arg2)
        print(f"🔗 {'Связь создана' if created else 'Связь уже существует'}: {arg1} ↔ {arg2}")

    elif action == "unlink":
        if not arg1 or not arg2:
            print("❌ Укажи проект и ресурс: python freebuff_cli.py resource unlink <project> <resource>")
            return
        removed = wav_unlink(arg1, arg2)
        print(f"🗑 {'Связь удалена' if removed else 'Связь не найдена'}: {arg1} ↔ {arg2}")

    elif action == "projects":
        if not arg1:
            print("❌ Укажи ресурс: python freebuff_cli.py resource projects <resource_name>")
            return
        print_projects(arg1)

    elif action == "resources":
        if not arg1:
            print("❌ Укажи проект: python freebuff_cli.py resource resources <project_name>")
            return
        resources = resources_for_project(arg1)
        print(f"Ресурсы, связанные с {arg1}:")
        if not resources:
            print("  (нет связей)")
            return
        for r in resources:
            print(f"  - {r['resource_id']}")

    elif action == "list":
        links = list_links()
        print(f"Связи проект ↔ ресурс ({len(links)}):")
        if not links:
            print("  (нет связей)")
            return
        for l in links:
            print(f"  - {l['project_id']} ↔ {l['resource_id']}")

    else:
        print("Использование:")
        print("  python freebuff_cli.py resource link <project> <resource>")
        print("  python freebuff_cli.py resource unlink <project> <resource>")
        print("  python freebuff_cli.py resource projects <resource_name>")
        print("  python freebuff_cli.py resource resources <project_name>")
        print("  python freebuff_cli.py resource list")


def cmd_qwen_resume(session_id: str) -> None:
    """Читает Qwen file-history напрямую и выводит контекст сессии.
    
    Аналог: qwen --resume <session_id>
    """
    qwen_history = Path.home() / ".qwen" / "file-history"
    session_dir = os.path.join(qwen_history, session_id)

    if not os.path.isdir(session_dir):
        # Пробуем найти по префиксу
        if os.path.isdir(qwen_history):
            for d in os.listdir(qwen_history):
                if d.startswith(session_id):
                    session_dir = os.path.join(qwen_history, d)
                    session_id = d
                    break
        if not os.path.isdir(session_dir):
            print(f"❌ Qwen-сессия не найдена: {session_id[:8]}")
            return

    files = sorted(os.listdir(session_dir))
    print(f"📂 Qwen Session: {session_id}")
    print(f"   Файлов: {len(files)}")
    print()

    for fname in files[:20]:  # лимит на вывод
        fpath = os.path.join(session_dir, fname)
        try:
            with open(fpath, encoding='utf-8') as f:
                content = f.read()[:2000]
            if len(content) == 2000:
                content += "\n... [truncated]"
            version = ""
            if "@v" in fname:
                base, ver = fname.rsplit("@", 1)
                version = f" ({ver})"
                fname = base
            print(f"### {fname}{version}")
            print(f"```")
            print(content)
            print(f"```")
            print()
        except Exception as e:
            print(f"   ⚠️ Ошибка чтения {fname}: {e}")

    if len(files) > 20:
        print(f"   ... и ещё {len(files) - 20} файлов")


# ── CLI Entry Point ────────────────────────────────────────────


def _main_with_notification() -> int:
    """Обёртка main(): отправляет системное уведомление о завершении CLI-задачи.

    MANDATORY RUNTIME CONTRACT (v5.24.0): каждая завершённая задача ОБЯЗАНА
    отправить уведомление пользователю. Эта обёртка гарантирует это для всех
    команд freebuff_cli.py.

    Returns:
        Exit code (0 — успех, иначе код ошибки).
    """
    import time as _time

    started = _time.monotonic()
    exit_code = 0
    try:
        main()
    except SystemExit as e:
        # main() использует sys.exit(code) для ошибок — перехватываем код.
        # sys.exit(None) по спецификации Python эквивалентен exit 0.
        if e.code is None:
            exit_code = 0
        elif isinstance(e.code, int):
            exit_code = e.code
        else:
            exit_code = 1
        if exit_code != 0 and _HAS_NOTIFICATION:
            notify_error(
                "Freebuff CLI",
                error=f"Команда завершилась с кодом {exit_code}: {' '.join(sys.argv[1:])}",
                stage=sys.argv[1] if len(sys.argv) > 1 else "",
            )
    except Exception as e:  # noqa: BLE001
        print(f"❌ Ошибка: {e}")
        exit_code = 1
        if _HAS_NOTIFICATION:
            notify_error(
                "Freebuff CLI",
                error=str(e),
                stage=sys.argv[1] if len(sys.argv) > 1 else "",
            )
    finally:
        # Успешное завершение (нормальное или SystemExit(0)):
        # отправляем уведомление о завершении задачи.
        if exit_code == 0 and _HAS_NOTIFICATION:
            duration = f"{_time.monotonic() - started:.0f}s"
            try:
                notify_task_complete(
                    task_name="Freebuff CLI",
                    status="Успешно",
                    duration=duration,
                    details=" ".join(sys.argv[1:]) or "(без аргументов)",
                )
            except Exception:  # noqa: BLE001
                pass

    return exit_code


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    try:
        if cmd == "start":
            project = sys.argv[2] if len(sys.argv) > 2 else "freebuff"
            topic = sys.argv[3] if len(sys.argv) > 3 else ""
            cmd_start(project, topic)

        elif cmd == "status":
            cmd_status()

        elif cmd == "resume":
            cmd_resume()

        elif cmd == "conspect":
            sid = sys.argv[2] if len(sys.argv) > 2 else None
            cmd_conspect(sid)

        elif cmd == "list":
            status_filter = sys.argv[2] if len(sys.argv) > 2 else None
            cmd_list(status_filter)

        elif cmd == "checkpoint":
            summary = sys.argv[2] if len(sys.argv) > 2 else "Manual checkpoint"
            sid = sys.argv[3] if len(sys.argv) > 3 else None
            cmd_checkpoint(sid, summary)

        elif cmd == "restore":
            sid = sys.argv[2] if len(sys.argv) > 2 else None
            conspect = cmd_conspect(sid)
            if conspect:
                print("\n📋 Для инжекта в контекст — скопируй вывод выше.")

        elif cmd == "qwen-resume":
            sid = sys.argv[2] if len(sys.argv) > 2 else None
            if sid is None:
                print("❌ Укажи ID сессии: python freebuff_cli.py qwen-resume 9667a0ca")
                sys.exit(1)
            cmd_qwen_resume(sid)

        elif cmd == "seed":
            cmd_seed()

        elif cmd == "task":
            sub = sys.argv[2] if len(sys.argv) > 2 else None
            if sub == "start":
                title = sys.argv[3] if len(sys.argv) > 3 else ""
                description = sys.argv[4] if len(sys.argv) > 4 else ""
                cmd_task_start(title, description)
            elif sub == "archive":
                cmd_task_archive()
            else:
                print("Использование:")
                print("  python freebuff_cli.py task start 'Название задачи' ['Описание')")
                print("  python freebuff_cli.py task archive")
                sys.exit(1)

        elif cmd == "project-book":
            chapter = sys.argv[2] if len(sys.argv) > 2 else None
            cmd_project_book(chapter)

        elif cmd == "project-context":
            query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
            cmd_project_context(query)

        elif cmd == "resource":
            action = sys.argv[2] if len(sys.argv) > 2 else None
            arg1 = sys.argv[3] if len(sys.argv) > 3 else None
            arg2 = sys.argv[4] if len(sys.argv) > 4 else None
            cmd_resource(action, arg1, arg2)

        elif cmd == "policy":
            action = sys.argv[2] if len(sys.argv) > 2 else None
            arg1 = sys.argv[3] if len(sys.argv) > 3 else None
            arg2 = sys.argv[4] if len(sys.argv) > 4 else None
            cmd_policy(action, arg1, arg2)

        elif cmd == "buffy":
            # Запуск коммуникации с Buffy — собирает Unified Context.
            # Перед сборкой синхронизируем Knowledge Memory.
            try:
                bus = get_default_event_bus(WORKSPACE)
                seed_knowledge(workspace_root=WORKSPACE, event_bus=bus, rebuild=False)
            except Exception:
                pass
            cmd_buffy()

        else:
            print(f"❌ Неизвестная команда: {cmd}")
            print("Доступные: start, status, resume, conspect, list, checkpoint, restore, qwen-resume, task, buffy, seed, project-book, project-context, resource, policy")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(_main_with_notification())
