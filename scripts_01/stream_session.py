#!/usr/bin/env python3
"""
stream_session.py — Непрерывная запись сессии в лог-файл + ContextManager.

Каждое сообщение автоматически сохраняется в:
  context_12/streams/<topic_YYYY-MM-DD_HHMMSS>/
    ├── conversation.log    # полный лог в реальном времени
    ├── summary.md          # чекпоинты и конспект
    └── raw.jsonl           # полные JSON-строки (для восстановления)

А также в SQLite через ContextManager (context.db) — для freebuff_cli.py

Фичи:
  - BackgroundWriter: асинхронная запись (не блокирует ответ)
  - Адаптивный чекпоинт-интервал: 20 → 30 → 40 → 50
  - CONTEXT_FULL триггер при превышении порога токенов
  - Авто-GC стрим-директорий (хранит последние 10)
  - Очистка ABANDONED сессий старше 1 дня

Использование:
    python scripts_01/stream_session.py start <topic>        # новая сессия
    python scripts_01/stream_session.py resume <session_id>  # продолжить старую
    python scripts_01/stream_session.py log <role> <text>    # добавить сообщение
    python scripts_01/stream_session.py checkpoint <msg>     # чекпоинт
    python scripts_01/stream_session.py tail                 # последние 20 строк
    python scripts_01/stream_session.py status               # статус
    python scripts_01/stream_session.py list                 # все сессии
    python scripts_01/stream_session.py prune                # GC: старые стримы + abandoned
"""

import argparse
import json
import os
import sys
import threading
from collections import deque
from datetime import datetime, timezone
}
from queue import Queue, Empty
from typing import Optional, Any

# ── Пути ──────────────────────────────────────────────────────

WORKSPACE = Path(__file__).resolve().parent.parent
STREAMS_DIR = WORKSPACE / "context_12" / "streams"
STREAMS_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_FILE = STREAMS_DIR / ".current"  # содержит имя активной директории

# ── Конфигурация ──────────────────────────────────────────────

AUTO_CHECKPOINT_INTERVAL_START = 20   # начальный интервал
AUTO_CHECKPOINT_INTERVAL_MAX = 50     # максимальный интервал
AUTO_CHECKPOINT_INTERVAL_STEP = 10    # шаг увеличения
MAX_STREAM_DIRS = 10                   # сколько стрим-директорий хранить
ABANDONED_CLEANUP_DAYS = 1            # удалять ABANDONED старше N дней
CONTEXT_FULL_THRESHOLD = 28000        # триггер CONTEXT_FULL (DeepSeek ~32K)

# ── ContextManager ────────────────────────────────────────────

sys.path.insert(0, str(WORKSPACE))
try:
    from scripts_01.context_manager import (
        ContextManager, CheckpointType, SessionStatus, DEFAULT_CONTEXT_THRESHOLD
    )
    cm = ContextManager(str(WORKSPACE), context_threshold=CONTEXT_FULL_THRESHOLD)
except ImportError:
    cm = None
    print("⚠️ ContextManager не загружен (сессия только в файлы)", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════
# BackgroundWriter — асинхронная запись
# ═══════════════════════════════════════════════════════════════

class BackgroundWriter:
    """
    Фоновый писатель: все I/O операции выполняются в отдельном потоке.

    Потокобезопасен — использует Queue.
    Авто-старт при первом enqueue.
    """

    def __init__(self) -> None:
        self._queue: Queue[dict[str, Any]] = Queue()
        self._thread: threading.Thread | None = None
        self._started = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Запускает фоновый поток."""
        with self._lock:
            if self._started:
                return
            self._started = True
            self._thread = threading.Thread(
                target=self._worker,
                daemon=True,
                name="stream-bg-writer",
            )
            self._thread.start()

    def enqueue(self, operation: str, **kwargs: Any) -> None:
        """Добавляет операцию в очередь (неблокирующая)."""
        if not self._started:
            self.start()
        self._queue.put({"op": operation, **kwargs})

    def flush(self, timeout: float = 5.0) -> int:
        """Ожидает опустошения очереди. Возвращает сколько осталось."""
        deadline = datetime.now(timezone.utc).timestamp() + timeout
        while self._queue.qsize() > 0 and datetime.now(timezone.utc).timestamp() < deadline:
            import time
            time.sleep(0.05)
        return self._queue.qsize()

    def _worker(self) -> None:
        """Фоновый поток: читает из очереди и выполняет I/O."""
        while True:
            try:
                item = self._queue.get(timeout=1.0)
            except Empty:
                # Проверяем, не пора ли завершиться (main thread умер)
                if not threading.main_thread().is_alive():
                    break
                continue

            try:
                op = item.pop("op")
                handler = getattr(self, f"_handle_{op}", None)
                if handler:
                    handler(**item)
                else:
                    print(f"⚠️ Unknown BG operation: {op}", file=sys.stderr)
            except Exception as e:
                # traceback в stderr — иначе ошибка фонового потока невидима
                import traceback
                traceback.print_exc(file=sys.stderr)
                print(f"⚠️ BG writer error: {e}", file=sys.stderr)
            finally:
                self._queue.task_done()

    # ── Handlers ─────────────────────────────────────────────

    @staticmethod
    def _handle_log(**kw: Any) -> None:
        """Запись в файлы (синхронно, но в фоновом потоке)."""
        session_dir = kw.get("session_dir")
        role = kw.get("role", "?")
        content = kw.get("content", "")
        count = kw.get("count", 0)
        ts = kw.get("ts", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

        if not session_dir:
            return
        # Defensive: Path-коэрция (str / str → TypeError терял сообщение молча)
        session_dir = Path(session_dir)

        icon = {"user": "🧑", "assistant": "🤖", "system": "⚙️"}.get(role, "❓")

        # conversation.log (читаемый)
        log_file = session_dir / "conversation.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {icon} [{role}] msg#{count}\n")
            for line in content.strip().split("\n"):
                f.write(f"  │ {line}\n")
            f.write(f"  └─ ({len(content)} chars)\n\n")

        # raw.jsonl (полный машинный формат)
        jsonl_file = session_dir / "raw.jsonl"
        entry: dict[str, Any] = {
            "ts": ts,
            "role": role,
            "msg_num": count,
            "chars": len(content),
            "content": content,
            "preview": content[:200],
        }
        with open(jsonl_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @staticmethod
    def _handle_checkpoint(**kw: Any) -> None:
        """Запись чекпоинта в summary.md."""
        session_dir = kw.get("session_dir")
        summary = kw.get("summary", "")
        count = kw.get("count", 0)
        ts = kw.get("ts", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        if session_dir:
            # Defensive: Path-коэрция (см. _handle_log)
            session_dir = Path(session_dir)
            summary_file = session_dir / "summary.md"
            preview = summary[:120].replace("\n", " ")
            with open(summary_file, "a", encoding="utf-8") as f:
                f.write(f"- [{ts}] msg#{count}: {preview}\n")


# Глобальный экземпляр BackgroundWriter
BG_WRITER = BackgroundWriter()


# ═══════════════════════════════════════════════════════════════
# Управление сессией
# ═══════════════════════════════════════════════════════════════

def _safe_topic(topic: str) -> str:
    """Очищает тему для имени директории."""
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in topic)[:40]
    return safe.strip().replace(" ", "_")


def _current_session_path() -> Optional[Path]:
    """Читает .current файл и возвращает путь к сессии."""
    if CURRENT_FILE.exists():
        name = CURRENT_FILE.read_text().strip()
        target = STREAMS_DIR / name
        if target.exists():
            return target
    return None


def _set_current_session(name: str) -> None:
    """Записывает имя активной сессии в .current."""
    CURRENT_FILE.write_text(name)


# ── Счётчик (in-memory cache) ────────────────────────────────

_counter_cache: dict[str, int] = {}

def _get_counter(session_dir: Path) -> int:
    name = session_dir.name
    if name not in _counter_cache:
        cf = session_dir / ".counter"
        _counter_cache[name] = int(cf.read_text()) if cf.exists() else 0
    return _counter_cache[name]


def _inc_counter(session_dir: Path) -> int:
    name = session_dir.name
    count = _get_counter(session_dir) + 1
    _counter_cache[name] = count
    cf = session_dir / ".counter"
    cf.write_text(str(count))
    return count


# ── Адаптивный чекпоинт-интервал ─────────────────────────────

_checkpoint_interval_current: int = AUTO_CHECKPOINT_INTERVAL_START

def _get_adaptive_interval(msg_count: int) -> int:
    """
    Адаптивный чекпоинт-интервал.

    - msg_count < 20: 20 (каждое 20-е)
    - msg_count < 100: 30
    - msg_count < 500: 40
    - msg_count >= 500: 50
    """
    if msg_count < 20:
        return AUTO_CHECKPOINT_INTERVAL_START
    elif msg_count < 100:
        return 30
    elif msg_count < 500:
        return 40
    else:
        return AUTO_CHECKPOINT_INTERVAL_MAX


# ═══════════════════════════════════════════════════════════════
# Основные операции
# ═══════════════════════════════════════════════════════════════

def start_session(topic: str, session_id: str | None = None) -> Path:
    """Создаёт новую сессию."""
    name = f"{_safe_topic(topic)}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
    session_dir = STREAMS_DIR / name
    session_dir.mkdir(parents=True, exist_ok=True)
    _set_current_session(name)

    # Cброс кэша счётчика
    _counter_cache.pop(name, None)

    # ContextManager
    if cm is not None:
        sid = session_id or name
        snap = cm.start_session(project="tg_terminal_messenger", topic=topic, session_id=sid)
        (session_dir / ".session_id").write_text(snap.session_id)
        print(f"   SQLite: {snap.session_id[:8]}")
    else:
        (session_dir / ".session_id").write_text(name)

    log_file = session_dir / "conversation.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"{'='*60}\n")
        f.write(f" Сессия: {topic}\n")
        f.write(f" Начата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")

    # Запускаем фоновый писатель
    BG_WRITER.start()

    print(f"▶ Сессия начата: {name}")
    print(f"   Лог: {log_file}")
    return session_dir


def resume_session(session_id: str) -> Optional[Path]:
    """Найти и продолжить существующую сессию по session_id или префиксу."""
    # Поиск среди стрим-директорий
    for d in sorted(STREAMS_DIR.iterdir(), reverse=True):
        if d.is_dir():
            sid_file = d / ".session_id"
            if sid_file.exists() and sid_file.read_text().strip().startswith(session_id):
                _set_current_session(d.name)
                print(f"▶ Продолжена сессия: {d.name}")
                print(f"   Лог: {d / 'conversation.log'}")
                return d

    # Поиск в ContextManager
    if cm is not None:
        sessions = cm.list_sessions()
        for s in sessions:
            sid = s["session_id"]
            if sid.startswith(session_id):
                print(f"  📌 Найдено в SQLite: {sid[:8]}, создаю стрим-директорию...")
                return attach_session(sid)

    print(f"❌ Сессия не найдена: {session_id}")
    return None


def attach_session(session_id: str) -> Optional[Path]:
    """Привязать стрим-сессию к существующей SQLite-сессии."""
    if cm is None:
        print("❌ ContextManager не загружен, attach недоступен")
        return None

    sessions = cm.list_sessions()
    target = None
    for s in sessions:
        sid = s["session_id"]
        if sid.startswith(session_id):
            target = s
            break

    if target is None:
        print(f"❌ Сессия не найдена в SQLite: {session_id}")
        print("   Список сессий: python freebuff_cli.py list")
        return None

    sid = target["session_id"]

    # Проверить, не привязана ли уже
    for d in sorted(STREAMS_DIR.iterdir(), reverse=True):
        if d.is_dir():
            sf = d / ".session_id"
            if sf.exists() and sf.read_text().strip() == sid:
                _set_current_session(d.name)
                print(f"▶ Уже привязана: {d.name}")
                return d

    topic = target.get("topic", "untitled")
    name = f"attached_{_safe_topic(topic)}_{sid[:8]}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
    session_dir = STREAMS_DIR / name
    session_dir.mkdir(parents=True, exist_ok=True)
    _set_current_session(name)

    (session_dir / ".session_id").write_text(sid)

    log_file = session_dir / "conversation.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"{'='*60}\n")
        f.write(f" Сессия: {topic} (attached to {sid[:8]})\n")
        f.write(f" Начата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")

    print(f"▶ Привязана стрим-сессия: {name}")
    print(f"   SQLite ID: {sid[:8]}")
    print(f"   Лог: {log_file}")
    return session_dir


# ═══════════════════════════════════════════════════════════════
# Логирование
# ═══════════════════════════════════════════════════════════════

def log_message(role: str, content: str) -> Optional[int]:
    """
    Добавить сообщение в лог текущей сессии (асинхронно + синхронно в SQLite).

    Запись в файлы (conversation.log + raw.jsonl) через BackgroundWriter.
    Запись в SQLite через ContextManager (синхронно, с блокировкой).
    Авточекпоинт с адаптивным интервалом.
    """
    session_dir = _current_session_path()
    if session_dir is None:
        print("❌ Нет активной сессии. Сначала: python scripts_01/stream_session.py start <topic>", file=sys.stderr)
        return None

    count = _inc_counter(session_dir)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Асинхронная запись в файлы (не блокирует ответ)
    BG_WRITER.enqueue(
        "log",
        session_dir=session_dir,
        role=role,
        content=content,
        count=count,
        ts=ts,
    )

    # 2. Синхронная запись в SQLite (ContextManager)
    cp_result = None
    if cm is not None:
        sid_file = session_dir / ".session_id"
        if sid_file.exists():
            sid = sid_file.read_text().strip()
            adaptive_interval = _get_adaptive_interval(count)

            cp_result = cm.add_message(
                session_id=sid,
                role=role,
                content=content,
                token_count=None,  # auto-estimate
                auto_checkpoint_interval=adaptive_interval,
            )

    # 3. Локальный авточекпоинт (в файл summary.md) — если ContextManager создал
    if cp_result:
        summary = cp_result.get("summary", f"Auto-checkpoint at msg#{count}")
        ctype = cp_result.get("checkpoint_type", "auto_interval")
        rollup_path = cp_result.get("rollup_path")

        BG_WRITER.enqueue(
            "checkpoint",
            session_dir=session_dir,
            summary=summary,
            count=count,
            ts=ts,
        )

        small = summary[:60]
        print(f"  📌 Чекпоинт msg#{count} [{ctype}]: {small}...")

        # Если CONTEXT_FULL — показываем путь к rollup
        if ctype == "context_full" and rollup_path:
            print(f"  🔄 Rollup-конспект: {rollup_path}")
            print(f"  💡 Инжектни в новый контекст для непрерывности")

    return count


# ═══════════════════════════════════════════════════════════════
# GC: очистка старых стрим-директорий и ABANDONED сессий
# ═══════════════════════════════════════════════════════════════

def prune_streams(keep: int = MAX_STREAM_DIRS, dry_run: bool = False) -> int:
    """
    Удаляет старые стрим-директории, оставляя только последние `keep`.

    Returns:
        Количество удалённых директорий.
    """
    dirs = sorted(
        [d for d in STREAMS_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )

    to_delete = dirs[keep:]
    current = _current_session_path()

    deleted = 0
    for d in to_delete:
        if current and d.resolve() == current.resolve():
            continue  # не удаляем активную

        if dry_run:
            print(f"  [DRY RUN] Буду удалён: {d.name} "
                  f"({_get_counter(d)} msgs, "
                  f"{sum(f.stat().st_size for f in d.glob('*') if f.is_file()) // 1024} KB)")
            continue

        import shutil
        try:
            shutil.rmtree(str(d))
            _counter_cache.pop(d.name, None)
            deleted += 1
        except OSError as e:
            print(f"  ⚠️ Не удалось удалить {d.name}: {e}", file=sys.stderr)

    if deleted:
        print(f"  🗑 Удалено старых стрим-директорий: {deleted}")
    elif not dry_run:
        print(f"  ✓ Всё чисто: {len(dirs)} директорий, лимит {keep}")

    return deleted


def prune_all(dry_run: bool = False) -> dict[str, int]:
    """
    Полная очистка: ABANDONED сессии + старые стрим-директории.

    Returns:
        dict с количеством удалённого: {abandoned, streams, stale_active}
    """
    result: dict[str, int] = {"abandoned": 0, "streams": 0, "stale_active": 0}

    # 1. Очистка ABANDONED в SQLite
    if cm is not None:
        if dry_run:
            # Показываем, что будет удалено
            sessions = cm.list_sessions(SessionStatus.ABANDONED)
            stale_count = 0
            for s in sessions:
                updated = s.get("updated_at", "")
                if updated:
                    from datetime import datetime, timezone
                    try:
                        updated_dt = datetime.fromisoformat(updated)
                        age = (datetime.now(timezone.utc) - updated_dt).days
                        if age >= ABANDONED_CLEANUP_DAYS:
                            stale_count += 1
                    except (ValueError, TypeError):
                        pass
            if stale_count:
                print(f"  [DRY RUN] Будут удалены ABANDONED сессии: {stale_count}")
        else:
            # Переводим пустые ACTIVE в ABANDONED
            result["stale_active"] = cm.auto_abandon_stale(days=ABANDONED_CLEANUP_DAYS)
            if result["stale_active"]:
                print(f"  💤 Переведено ACTIVE→ABANDONED: {result['stale_active']}")

            # Удаляем ABANDONED
            result["abandoned"] = cm.prune_abandoned(days=ABANDONED_CLEANUP_DAYS)
            if result["abandoned"]:
                print(f"  🗑 Удалено ABANDONED сессий: {result['abandoned']}")

    # 2. Очистка стрим-директорий
    result["streams"] = prune_streams(keep=MAX_STREAM_DIRS, dry_run=dry_run)

    return result


# ═══════════════════════════════════════════════════════════════
# Просмотр
# ═══════════════════════════════════════════════════════════════

def print_status() -> None:
    """Статус текущей сессии."""
    session_dir = _current_session_path()
    if session_dir is None:
        print("⏸ Нет активной сессии")
        print("   Начни: python scripts_01/stream_session.py start \"тема\"")
        return
    log_file = session_dir / "conversation.log"
    count = _get_counter(session_dir)
    sz = log_file.stat().st_size if log_file.exists() else 0
    print(f"▶ Активная сессия: {session_dir.name}")
    print(f"   Сообщений: {count}")
    print(f"   Размер лога: {sz // 1024} KB")
    print(f"   Лог: {log_file}")

    # Статус контекста из ContextManager
    if cm is not None:
        sid_file = session_dir / ".session_id"
        if sid_file.exists():
            sid = sid_file.read_text().strip()
            status = cm.get_context_status(sid)
            if "error" not in status:
                print(f"   Контекст: {status['token_estimate']} / {status['threshold']} tokens "
                      f"({status['usage_percent']}%) "
                      f"{'⚠️ FULL' if status['is_full'] else '✅ OK'}")


def print_tail(n: int = 20) -> None:
    """Последние строки лога."""
    session_dir = _current_session_path()
    if session_dir is None:
        print("❌ Нет активной сессии")
        return
    log_file = session_dir / "conversation.log"
    if not log_file.exists():
        print("📭 Лог пуст")
        return
    lines = log_file.read_text().splitlines()
    tail = lines[-n:]
    print(f"📋 Последние {len(tail)} строк:")
    for line in tail:
        print(line)


def list_sessions() -> None:
    """Список всех стрим-сессий."""
    dirs = sorted(
        [d for d in STREAMS_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime, reverse=True
    )
    if not dirs:
        print("📭 Нет стрим-сессий")
        return
    print(f"📋 Всего стрим-сессий: {len(dirs)}")
    print("")
    for d in dirs[:10]:
        count = _get_counter(d)
        sz = sum(f.stat().st_size for f in d.glob("*") if f.is_file()) // 1024
        sid_file = d / ".session_id"
        sid = sid_file.read_text()[:8] if sid_file.exists() else "?"
        active = " ◀" if _current_session_path() == d else ""
        print(f"  {d.name}")
        print(f"    msgs={count}, {sz}KB, id={sid}{active}")

    if len(dirs) > 10:
        print(f"   ... и ещё {len(dirs) - 10}")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="stream_session — непрерывная запись сессии",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts_01/stream_session.py start "Редизайн TUI"
  python scripts_01/stream_session.py resume 26275a79
  python scripts_01/stream_session.py attach 26275a79
  python scripts_01/stream_session.py log user "Привет"
  python scripts_01/stream_session.py log assistant --file response.txt
  python scripts_01/stream_session.py checkpoint "Закончил этап A"
  python scripts_01/stream_session.py tail
  python scripts_01/stream_session.py status
  python scripts_01/stream_session.py list
  python scripts_01/stream_session.py prune
  python scripts_01/stream_session.py prune --dry-run
        """,
    )
    sub = parser.add_subparsers(dest="command")

    p_start = sub.add_parser("start", help="Начать новую сессию")
    p_start.add_argument("topic", help="Тема сессии")

    p_resume = sub.add_parser("resume", help="Продолжить сессию")
    p_resume.add_argument("session_id", help="ID сессии (первые 8 символов)")

    p_attach = sub.add_parser("attach", help="Привязать стрим к существующей SQLite-сессии")
    p_attach.add_argument("session_id", help="ID сессии из ContextManager (первые 8 символов)")

    p_log = sub.add_parser("log", help="Добавить сообщение")
    p_log.add_argument("role", choices=["user", "assistant", "system"])
    p_log.add_argument("text", nargs="?", help="Текст (или --file / stdin)")
    p_log.add_argument("--file", "-f", help="Читать текст из файла")

    p_cp = sub.add_parser("checkpoint", help="Ручной чекпоинт")
    p_cp.add_argument("message", help="Описание")

    sub.add_parser("tail", help="Последние строки лога")
    sub.add_parser("status", help="Статус сессии")
    sub.add_parser("list", help="Список сессий")

    p_prune = sub.add_parser("prune", help="Очистка старых сессий и стримов")
    p_prune.add_argument("--dry-run", action="store_true", help="Показать что будет удалено без удаления")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "start":
        start_session(args.topic)

    elif args.command == "resume":
        resume_session(args.session_id)

    elif args.command == "attach":
        attach_session(args.session_id)

    elif args.command == "log":
        text = args.text
        if text is None and args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        if text is None and not sys.stdin.isatty():
            text = sys.stdin.read()
        if text is None or not text.strip():
            print("❌ Нет текста. Укажи text, --file, или передай через пайп: echo \"текст\" | stream_session.py log user")
            return
        log_message(args.role, text.strip())

    elif args.command == "checkpoint":
        session_dir = _current_session_path()
        if session_dir is None:
            print("❌ Нет активной сессии")
            return
        count = _get_counter(session_dir)
        summary_file = session_dir / "summary.md"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] [MANUAL] msg#{count}: {args.message}\n")
        print(f"📌 Чекпоинт msg#{count}: {args.message}")

    elif args.command == "tail":
        print_tail()

    elif args.command == "status":
        print_status()

    elif args.command == "list":
        list_sessions()

    elif args.command == "prune":
        print("🧹 GC: очистка старых сессий и стримов")
        if args.dry_run:
            print("   Режим: DRY RUN (ничего не удаляется)\n")
        prune_all(dry_run=args.dry_run)
        if args.dry_run:
            print("\n   Запусти без --dry-run для реального удаления")


if __name__ == "__main__":
    main()
