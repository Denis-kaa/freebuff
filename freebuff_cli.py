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

Архитектура по Kwork Arbitr v3:
    Explainer → LISA (TC=5 Medium) → Decomposer → Architect → Developer → Tester → Acceptance
"""
import os
import shutil
import sys
from datetime import datetime, timezone
***REMOVED***

WORKSPACE = os.environ.get("FREEBUFF_ROOT", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE)

from scripts.context_manager import ContextManager, SessionStatus, CheckpointType
from scripts.system_monitor import health_check
from scripts.context_builder import ContextBuilder
from scripts.event_bus import get_default_event_bus
from scripts.seed_knowledge import seed as seed_knowledge
from scripts.session_utils ***REMOVED***solve_session_id

# MANDATORY RUNTIME CONTRACT (v5.24.0): системные уведомления о завершении CLI-задач.
# Graceful degradation: если notification-модуль недоступен (FREEBUFF_NO_NOTIFY=1
# или ImportError) — CLI работает как раньше, без уведомлений.
# Все вызовы ниже защищены флагом _HAS_NOTIFICATION, поэтому отдельные
# no-op фолбэки не нужны (dead code исключён).
try:
    from scripts.notification import notify_error, notify_task_complete

    _HAS_NOTIFICATION = True
except ImportError:
    _HAS_NOTIFICATION = False
    notify_task_complete = None
    notify_error = None


# ── TASK.md helpers ────────────────────────────────────────────

def _task_path() -> Path:
    return Path(WORKSPACE) / "TASK.md"


def _archive_task_path() -> Path:
    archive_dir = Path(WORKSPACE) / "docs" / "task_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    return archive_dir / f"TASK_{ts***REMOVED***.md"


def _archive_current_task() -> Path | None:
    """Archive current TASK.md if it exists. Returns archive path or None."""
    current = _task_path()
    if not current.exists():
        return None
    archive = _archive_task_path()
    shutil.copy2(current, archive)
    return archive


def cmd_task_start(title: str, description: str = "") -> None:
    """Создаёт новую TASK.md, архивируя предыдущую."""
    if not title:
        print("❌ Укажи заголовок задачи: python freebuff_cli.py task start 'Название задачи'")
        return

    archive = _archive_current_task()

    task_md = f"""# TASK: {title***REMOVED***

**Статус:** активна  
**Создана:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")***REMOVED***  
**Описание:** {description or '(нет)'***REMOVED***  

## Цель

<!-- Опиши цель задачи -->

## Шаги

- [ ***REMOVED*** Шаг 1

## Связанные файлы

- `README.md`
- `TASK.md`

## Контекст

<!-- Дополнительный контекст, конспекты, ссылки -->
"""
    _task_path().write_text(task_md, encoding="utf-8")

    if archive:
        print(f"📦 Предыдущая TASK.md архивирована: {archive***REMOVED***")
    print(f"📝 Новая TASK.md создана: {title***REMOVED***")


def cmd_task_archive() -> None:
    """Вручную архивирует текущую TASK.md."""
    archive = _archive_current_task()
    if archive is None:
        print("⚠️ TASK.md не найден, нечего архивировать.")
        return
    print(f"📦 TASK.md архивирована: {archive***REMOVED***")


def cmd_start(project: str, topic: str = "") -> str:
    """Начинает новую сессию. Возвращает session_id."""
    cm = ContextManager(WORKSPACE)
    snap = cm.start_session(project=project, topic=topic)
    print(f"🟢 Сессия начата: {snap.session_id[:8***REMOVED******REMOVED***")
    print(f"   Проект: {snap.project***REMOVED***")
    print(f"   Тема: {snap.topic or '(без темы)'***REMOVED***")
    return snap.session_id


def cmd_status() -> dict:
    """Статус системы: активные сессии, здоровье, последний конспект."""
    cm = ContextManager(WORKSPACE)

    # Активные сессии
    active = cm.list_sessions(SessionStatus.ACTIVE)
    paused = cm.list_sessions(SessionStatus.PAUSED)

    print("📊 СТАТУС FREEBUFF")
    print(f"   Активных сессий: {len(active)***REMOVED***")
    for s in active[:5***REMOVED***:
        print(f"   • {s['session_id'***REMOVED***[:8***REMOVED******REMOVED*** | {s['project'***REMOVED******REMOVED*** | {s['topic'***REMOVED******REMOVED*** | {s['message_count'***REMOVED******REMOVED*** msgs")

    if paused:
        print(f"   Приостановлено: {len(paused)***REMOVED***")

    # Последний конспект
    summaries_dir = os.path.join(WORKSPACE, "context", "summaries")
    if os.path.isdir(summaries_dir):
        files = sorted(
            [f for f in os.listdir(summaries_dir) if f.endswith(".md")***REMOVED***,
            reverse=True,
        )
        if files:
            print(f"   Последний конспект: {files[0***REMOVED******REMOVED***")

    # Здоровье системы
    health = health_check()
    print(f"\n💚 Здоровье: {'OK' if all(health.values()) else '⚠️ ПРОБЛЕМЫ'***REMOVED***")
    for k, v in health.items():
        icon = "✅" if v else "❌"
        print(f"   {icon***REMOVED*** {k***REMOVED***")

    return {"active_sessions": len(active), "health": health***REMOVED***


def cmd_resume() -> str | None:
    """Восстанавливает последнюю активную сессию."""
    cm = ContextManager(WORKSPACE)

    # Ищем последнюю ACTIVE или CHECKPOINT сессию
    for status in [SessionStatus.ACTIVE, SessionStatus.CHECKPOINT***REMOVED***:
        sessions = cm.list_sessions(status)
        if sessions:
            s = sessions[0***REMOVED***
            print(f"🔄 Восстановлена сессия: {s['session_id'***REMOVED***[:8***REMOVED******REMOVED***")
            print(f"   Проект: {s['project'***REMOVED******REMOVED***")
            print(f"   Тема: {s['topic'***REMOVED******REMOVED***")
            print(f"   Сообщений: {s['message_count'***REMOVED******REMOVED***")

            # Показываем последний конспект
            summary = cm.get_last_summary(s['session_id'***REMOVED***)
            if summary:
                print(f"   Последнее: {summary[:100***REMOVED******REMOVED***")

            return str(s['session_id'***REMOVED***)

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
        session_id = active[0***REMOVED***['session_id'***REMOVED***

    full_id = resolve_session_id(cm, session_id)
    if full_id is None:
        print(f"❌ Сессия не найдена: {session_id[:8***REMOVED*** if session_id else '?'***REMOVED***")
        return ""
    session_id = full_id

    conspect = cm.export_checkpoint_summary(session_id)
    if not conspect:
        print(f"❌ Конспект пуст для сессии {session_id[:8***REMOVED******REMOVED***.")
        return ""

    print(conspect)
    return conspect


def cmd_list(status: str | None = None) -> list[dict***REMOVED***:
    """Список сессий с фильтром по статусу."""
    cm = ContextManager(WORKSPACE)
    status_enum = SessionStatus(status) if status else None
    sessions = cm.list_sessions(status_enum)

    if not sessions:
        print("📭 Сессий нет.")
        return [***REMOVED***

    print(f"📋 Сессии ({len(sessions)***REMOVED***):")
    for s in sessions:
        icon = {"active": "🟢", "completed": "✅", "paused": "⏸️", "abandoned": "💤"***REMOVED***.get(
            s['status'***REMOVED***, "❓"
        )
        print(
            f"   {icon***REMOVED*** {s['session_id'***REMOVED***[:8***REMOVED******REMOVED*** | {s['status'***REMOVED***:10***REMOVED*** | "
            f"{s['project'***REMOVED***:20***REMOVED*** | {s['topic'***REMOVED***[:30***REMOVED******REMOVED*** | {s['message_count'***REMOVED******REMOVED*** msgs"
        )
    return sessions


def cmd_checkpoint(session_id: str | None, summary: str) -> None:
    """Ручной чекпоинт. session_id может быть частичным (первые 8 символов)."""
    cm = ContextManager(WORKSPACE)

    if session_id is not None:
        full_id = resolve_session_id(cm, session_id)
        if full_id is None:
            print(f"❌ Сессия не найдена: {session_id[:8***REMOVED******REMOVED***")
            return
        session_id = full_id

    if session_id is None:
        active = cm.list_sessions(SessionStatus.ACTIVE)
        if not active:
            print("⚠️ Нет активных сессий. Создайте сессию: python freebuff_cli.py start <project>")
            return
        session_id = active[0***REMOVED***['session_id'***REMOVED***

    cm.save_checkpoint(session_id, summary, ctype=CheckpointType.MANUAL)
    print(f"📌 Чекпоинт сохранён: {summary[:80***REMOVED******REMOVED***")


def cmd_seed() -> None:
    """Заполняет Knowledge Memory проектными документами и best practices.

    Повторный запуск безопасен: уже загруженные и неизменённые документы
    пропускаются.
    """
    try:
        bus = get_default_event_bus(WORKSPACE)
        count = seed_knowledge(workspace_root=WORKSPACE, event_bus=bus, rebuild=False)
        print(f"✅ Knowledge Memory синхронизирована: {count***REMOVED*** записей.")
    except Exception as e:
        print(f"❌ Ошибка при заполнении Knowledge Memory: {e***REMOVED***")


def cmd_buffy() -> None:
    """Генерирует Unified Context для старта диалога с Buffy.

    Автоматически собирает:
      - Memory Engine (Working + Project + Knowledge + Personal)
      - TASK.md — текущая задача
      - CHANGELOG.md — последние изменения
      - StreamBridge — последний конспект сессии

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
   Активных сессий: {len(active)***REMOVED***
   Приостановлено: {len(paused)***REMOVED***
   Здоровье: {'✅ OK' if all(health.values()) else '⚠️ ПРОБЛЕМЫ'***REMOVED***
"""

    # Формируем итоговый промпт
    if unified_ctx:
        # Сохраняем в файл для удобства
        ctx_path = os.path.join(WORKSPACE, "context", "unified_context.md")
        os.makedirs(os.path.dirname(ctx_path), exist_ok=True)
        with open(ctx_path, "w", encoding="utf-8") as f:
            f.write(unified_ctx)

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
        print(f"💾 Контекст сохранён: {ctx_path***REMOVED***")
        print(f"   Размер: {len(unified_ctx)***REMOVED*** chars, ~{len(unified_ctx) // 4***REMOVED*** токенов")
    else:
        print("⚠️ Unified Context пуст (нет данных в памяти).")
        print()
        print("📋 Стартовый промпт для Buffy:")
        print("=" * 60)
        print("Я начинаю новую сессию. Расскажи кратко что было в прошлой сессии")
        print("и что мы продолжаем.")
        print("=" * 60)


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
            print(f"❌ Qwen-сессия не найдена: {session_id[:8***REMOVED******REMOVED***")
            return

    files = sorted(os.listdir(session_dir))
    print(f"📂 Qwen Session: {session_id***REMOVED***")
    print(f"   Файлов: {len(files)***REMOVED***")
    print()

    for fname in files[:20***REMOVED***:  # лимит на вывод
        fpath = os.path.join(session_dir, fname)
        try:
            with open(fpath, encoding='utf-8') as f:
                content = f.read()[:2000***REMOVED***
            if len(content) == 2000:
                content += "\n... [truncated***REMOVED***"
            version = ""
            if "@v" in fname:
                base, ver = fname.rsplit("@", 1)
                version = f" ({ver***REMOVED***)"
                fname = base
            print(f"### {fname***REMOVED***{version***REMOVED***")
            print(f"```")
            print(content)
            print(f"```")
            print()
        except Exception as e:
            print(f"   ⚠️ Ошибка чтения {fname***REMOVED***: {e***REMOVED***")

    if len(files) > 20:
        print(f"   ... и ещё {len(files) - 20***REMOVED*** файлов")


# ── CLI Entry Point ────────────────────────────────────────────


def _main_with_notification() -> int:
    """Обёртка main(): отправляет системное уведомление о завершении CLI-задачи.

    MANDATORY RUNTIME CONTRACT (v5.24.0): каждая завершённая задача ОБЯЗАНА
    отправить уведомление пользователю. Эта обёртка гарантирует это для всех
    команд freebuff_cli.py через try/finally.

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
        exit_code = e.code if isinstance(e.code, int) else 1
        if exit_code == 0:
            return 0
        # Ошибка: уведомляем и пробрасываем код дальше.
        if _HAS_NOTIFICATION:
            notify_error(
                "Freebuff CLI",
                error=f"Команда завершилась с кодом {exit_code***REMOVED***: {' '.join(sys.argv[1:***REMOVED***)***REMOVED***",
                stage=sys.argv[1***REMOVED*** if len(sys.argv) > 1 else "",
            )
        return exit_code
    except Exception as e:  # noqa: BLE001
        print(f"❌ Ошибка: {e***REMOVED***")
        exit_code = 1
        if _HAS_NOTIFICATION:
            notify_error(
                "Freebuff CLI",
                error=str(e),
                stage=sys.argv[1***REMOVED*** if len(sys.argv) > 1 else "",
            )
        return 1
    finally:
        # Успех (или SystemExit(0)): уведомляем о завершении задачи.
        if exit_code == 0 and _HAS_NOTIFICATION:
            duration = f"{_time.monotonic() - started:.0f***REMOVED***s"
            try:
                notify_task_complete(
                    task_name="Freebuff CLI",
                    status="Успешно",
                    duration=duration,
                    details=" ".join(sys.argv[1:***REMOVED***) or "(без аргументов)",
                )
            except Exception:  # noqa: BLE001
                pass


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1***REMOVED***

    try:
        if cmd == "start":
            project = sys.argv[2***REMOVED*** if len(sys.argv) > 2 else "freebuff"
            topic = sys.argv[3***REMOVED*** if len(sys.argv) > 3 else ""
            cmd_start(project, topic)

        elif cmd == "status":
            cmd_status()

        elif cmd == "resume":
            cmd_resume()

        elif cmd == "conspect":
            sid = sys.argv[2***REMOVED*** if len(sys.argv) > 2 else None
            cmd_conspect(sid)

        elif cmd == "list":
            status_filter = sys.argv[2***REMOVED*** if len(sys.argv) > 2 else None
            cmd_list(status_filter)

        elif cmd == "checkpoint":
            summary = sys.argv[2***REMOVED*** if len(sys.argv) > 2 else "Manual checkpoint"
            sid = sys.argv[3***REMOVED*** if len(sys.argv) > 3 else None
            cmd_checkpoint(sid, summary)

        elif cmd == "restore":
            sid = sys.argv[2***REMOVED*** if len(sys.argv) > 2 else None
            conspect = cmd_conspect(sid)
            if conspect:
                print("\n📋 Для инжекта в контекст — скопируй вывод выше.")

        elif cmd == "qwen-resume":
            sid = sys.argv[2***REMOVED*** if len(sys.argv) > 2 else None
            if sid is None:
                print("❌ Укажи ID сессии: python freebuff_cli.py qwen-resume 9667a0ca")
                sys.exit(1)
            cmd_qwen_resume(sid)

        elif cmd == "seed":
            cmd_seed()

        elif cmd == "task":
            sub = sys.argv[2***REMOVED*** if len(sys.argv) > 2 else None
            if sub == "start":
                title = sys.argv[3***REMOVED*** if len(sys.argv) > 3 else ""
                description = sys.argv[4***REMOVED*** if len(sys.argv) > 4 else ""
                cmd_task_start(title, description)
            elif sub == "archive":
                cmd_task_archive()
            else:
                print("Использование:")
                print("  python freebuff_cli.py task start 'Название задачи' ['Описание'***REMOVED***")
                print("  python freebuff_cli.py task archive")
                sys.exit(1)

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
            print(f"❌ Неизвестная команда: {cmd***REMOVED***")
            print("Доступные: start, status, resume, conspect, list, checkpoint, restore, qwen-resume, task, buffy, seed")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Ошибка: {e***REMOVED***")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(_main_with_notification())
