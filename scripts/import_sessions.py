"""
Import sessions: миграция истории из OpenClaw и Aider в freebuff context.db.

Источники:
- OpenClaw: ~/.openclaw/logs/config-audit.jsonl
- Aider: leviathan/root/.aider.chat.history.md
- Last context: ARCHIVE_REMNENTS/.../last_context.txt

Использование:
    python scripts/import_sessions.py --all
    python scripts/import_sessions.py --source openclaw
    python scripts/import_sessions.py --source aider
"""

import json
import os
import sys
from datetime import datetime, timezone

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE)

from scripts.context_manager import ContextManager, CheckpointType

HOME = "/data/data/com.termux/files/home"

SOURCES = {
    "openclaw": {
        "audit_log": f"{HOME***REMOVED***/.openclaw/logs/config-audit.jsonl",
        "health": f"{HOME***REMOVED***/.openclaw/logs/config-health.json",
    ***REMOVED***,
    "aider": {
        "history": f"{HOME***REMOVED***/leviathan/root/.aider.chat.history.md",
    ***REMOVED***,
    "last_context": {
        "file": f"{HOME***REMOVED***/ARCHIVE_REMNANTS/Denis_and_Lina/checkpoints/last_context.txt",
    ***REMOVED***,
***REMOVED***


def import_openclaw(cm: ContextManager) -> int:
    """Импортирует историю OpenClaw."""
    audit_path = SOURCES["openclaw"***REMOVED***["audit_log"***REMOVED***
    if not os.path.isfile(audit_path):
        print(f"⚠️ OpenClaw audit log not found: {audit_path***REMOVED***")
        return 0

    snap = cm.start_session(project="openclaw", topic="Imported from OpenClaw")
    count = 0

    with open(audit_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    timestamp = entry.get("timestamp", datetime.now(timezone.utc).isoformat())
                    status = entry.get("status", "unknown")
                    cm.add_message(
                        session_id=snap.session_id,
                        role="system",
                        content=f"[OpenClaw audit***REMOVED*** {status***REMOVED***: {json.dumps(entry, ensure_ascii=False)[:500***REMOVED******REMOVED***",
                        token_count=20,
                    )
                    count += 1
                except (json.JSONDecodeError, KeyError):
                    continue

    cm.save_checkpoint(
        snap.session_id,
        f"Imported {count***REMOVED*** OpenClaw audit entries",
        ctype=CheckpointType.MANUAL,
    )
    cm.complete_session(snap.session_id)
    return count


def import_aider(cm: ContextManager) -> int:
    """Импортирует историю Aider."""
    history_path = SOURCES["aider"***REMOVED***["history"***REMOVED***
    if not os.path.isfile(history_path):
        print(f"⚠️ Aider history not found: {history_path***REMOVED***")
        return 0

    snap = cm.start_session(project="aider", topic="Imported from Aider")
    count = 0

    with open(history_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Aider формат: ## Заголовок ... текст между заголовками
    sections = content.split("\n## ")
    for section in sections[1:***REMOVED***:  # пропускаем первый пустой
        lines = section.strip().split("\n", 1)
        title = lines[0***REMOVED*** if lines else "Untitled"
        body = lines[1***REMOVED*** if len(lines) > 1 else ""

        cm.add_message(
            session_id=snap.session_id,
            role="system",
            content=f"[Aider***REMOVED*** {title***REMOVED***: {body[:500***REMOVED******REMOVED***",
            token_count=len(body.split()),
        )
        count += 1

    cm.save_checkpoint(
        snap.session_id,
        f"Imported {count***REMOVED*** Aider entries",
        ctype=CheckpointType.MANUAL,
    )
    cm.complete_session(snap.session_id)
    return count


def import_last_context(cm: ContextManager) -> int:
    """Импортирует последний чекпоинт."""
    ctx_path = SOURCES["last_context"***REMOVED***["file"***REMOVED***
    if not os.path.isfile(ctx_path):
        print(f"⚠️ Last context not found: {ctx_path***REMOVED***")
        return 0

    with open(ctx_path, "r", encoding="utf-8") as f:
        content = f.read()

    snap = cm.start_session(project="archive", topic="Imported from last_context.txt")
    cm.save_checkpoint(
        snap.session_id,
        f"Imported last context: {content[:500***REMOVED******REMOVED***",
        ctype=CheckpointType.MANUAL,
    )
    cm.complete_session(snap.session_id)
    return 1


def import_all() -> dict:
    """Импортирует всё."""
    cm = ContextManager(WORKSPACE)
    results = {
        "openclaw": import_openclaw(cm),
        "aider": import_aider(cm),
        "last_context": import_last_context(cm),
    ***REMOVED***
    print(f"\n📥 Импорт завершён: {results***REMOVED***")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["openclaw", "aider", "last_context", "all"***REMOVED***, default="all")
    args = parser.parse_args()

    cm = ContextManager(WORKSPACE)

    if args.source == "all":
        import_all()
    elif args.source == "openclaw":
        print(f"📥 OpenClaw: {import_openclaw(cm)***REMOVED*** entries")
    elif args.source == "aider":
        print(f"📥 Aider: {import_aider(cm)***REMOVED*** entries")
    elif args.source == "last_context":
        print(f"📥 Last context: {import_last_context(cm)***REMOVED*** entries")
