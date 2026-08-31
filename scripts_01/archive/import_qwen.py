#!/usr/bin/env python3
"""
Импорт Qwen IDE данных в ContextManager freebuff.
- Memories (MEMORY.md, user/*.md, feedback/*.md, reference/*.md) → сессия "qwen-memories"
- File-history (19 сессий) → отдельные сессии с сообщениями
- Projects (meta.json) → метаданные проектов

Использование:
    python scripts_01/import_qwen.py
    python scripts_01/import_qwen.py --memories-only
    python scripts_01/import_qwen.py --history-only
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Добавляем freebuff в путь
FREEBUFF_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FREEBUFF_ROOT))

from scripts_01.context_manager import ContextManager

QWEN_HOME = Path(os.environ.get("QWEN_HOME", str(Path.home() / ".qwen")))


def import_memories(cm: ContextManager) -> Optional[str]:
    """Импортирует Qwen memories как одну сессию с чекпоинтами."""
    memories_dir = QWEN_HOME / "memories"
    if not memories_dir.exists():
        print("⚠️ Qwen memories не найдены")
        return None

    snap = cm.start_session(project="qwen", topic="Qwen Memories Import")

    # MEMORY.md — главный индекс
    mem_file = memories_dir / "MEMORY.md"
    if mem_file.exists():
        content = mem_file.read_text()
        cm.add_message(snap.session_id, "system", f"# Qwen MEMORY.md\n\n{content}", token_count=len(content.split()))

    # User memories
    for md_file in sorted(memories_dir.rglob("*.md")):
        if md_file.name == "MEMORY.md":
            continue
        rel = md_file.relative_to(memories_dir)
        content = md_file.read_text()
        cm.add_message(
            snap.session_id, "system",
            f"# {rel}\n\n{content}",
            token_count=len(content.split()),
        )

    cm.save_checkpoint(snap.session_id, f"Импортировано {len(list(memories_dir.rglob('*.md')))} memory-файлов")
    cm.complete_session(snap.session_id)

    print(f"✅ Memories: сессия {snap.session_id[:8]} ({len(list(memories_dir.rglob('*.md')))} файлов)")
    return snap.session_id


def import_file_history(cm: ContextManager, max_sessions: int = 10) -> List[str]:
    """Импортирует Qwen file-history как сессии."""
    history_dir = QWEN_HOME / "file-history"
    if not history_dir.exists():
        print("⚠️ Qwen file-history не найден")
        return []

    session_ids = []
    imported = 0

    for session_dir in sorted(history_dir.iterdir()):
        if not session_dir.is_dir():
            continue
        if imported >= max_sessions:
            break

        snap = cm.start_session(project="qwen", topic=f"File-History: {session_dir.name[:8]}")

        file_count = 0
        for f in sorted(session_dir.iterdir()):
            if f.is_file():
                try:
                    content = f.read_text()[:8000]  # обрезаем
                    cm.add_message(
                        snap.session_id, "system",
                        f"# {f.name}\n\n```\n{content}\n```",
                        token_count=len(content.split()),
                    )
                    file_count += 1
                except Exception:
                    pass

        cm.save_checkpoint(snap.session_id, f"Импортировано {file_count} версий файлов из Qwen file-history")
        cm.complete_session(snap.session_id)
        session_ids.append(snap.session_id)
        imported += 1
        print(f"✅ History {session_dir.name[:8]}: {file_count} файлов → сессия {snap.session_id[:8]}")

    print(f"📊 Импортировано {imported} file-history сессий (из {len(list(history_dir.iterdir()))})")
    return session_ids


def import_projects(cm: ContextManager) -> List[str]:
    """Импортирует метаданные Qwen-проектов."""
    projects_dir = QWEN_HOME / "projects_17"
    if not projects_dir.exists():
        return []

    session_ids = []
    for proj_dir in projects_dir.iterdir():
        if not proj_dir.is_dir():
            continue
        meta_file = proj_dir / "meta.json"
        if not meta_file.exists():
            continue

        try:
            meta = json.loads(meta_file.read_text())
        except Exception:
            continue

        name = meta.get("name", proj_dir.name.replace("-", "/"))
        snap = cm.start_session(project="qwen", topic=f"Project: {name}")

        cm.add_message(
            snap.session_id, "system",
            f"# Qwen Project Metadata: {name}\n\n```json\n{json.dumps(meta, indent=2, ensure_ascii=False)}\n```",
        )
        cm.save_checkpoint(snap.session_id, f"Метаданные проекта Qwen: {name}")
        cm.complete_session(snap.session_id)
        session_ids.append(snap.session_id)
        print(f"✅ Project {name}: сессия {snap.session_id[:8]}")

    return session_ids


def main():
    cm = ContextManager(str(FREEBUFF_ROOT))
    args = sys.argv[1:]

    do_memories = "--history-only" not in args
    do_history = "--memories-only" not in args
    do_projects = True

    print("📥 Импорт Qwen → ContextManager")
    print(f"   QWEN_HOME: {QWEN_HOME}")
    print()

    total = 0
    if do_memories:
        total += 1 if import_memories(cm) else 0
    if do_history:
        total += len(import_file_history(cm))
    if do_projects:
        total += len(import_projects(cm))

    print(f"\n🎉 Импортировано: {total} сессий в context.db")


if __name__ == "__main__":
    main()
