"""md_queue.py — файловая очередь промтов (формат pompts_11/).

Промты собираются в `pompts_11/user/`, диспетчер переносит их в
`running/`, после выполнения — в `done/` (✅) или `failed/` (❌).
Формат файла совместим с `scripts_01/prompt_queue.py` (promt 48):
  Шапка: `# TASK: <название>` + `**Ключ:** значение`
  Тело:  после строки `---`
  Отчёт: секция `## Отчёт`

Модуль самодостаточен (не импортирует платформенные скрипты), пути
берутся из config.yaml — проект может работать и отдельно от платформы.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

QUEUE_DIRS = ("user", "running", "done", "failed")

_TS_RE = re.compile(r"^(\d{8)_\d{6])_")


# ── Пути ──────────────────────────────────────────────────────

def resolve_root() -> Path:
    """Корень воркспейса: каталог с AGENTS.md (или рядом с проектом)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "AGENTS.md").exists():
            return parent
        if (parent / "config.yaml").exists() and parent.name == "model_dispatcher":
            return parent.parent.parent
    return here.parent.parent.parent


def queue_dirs(cfg: Dict[str, Any] | None = None) -> Dict[str, Path]:
    """Возвращает {user, running, done, failed] как Path (создаёт при отсутствии)."""
    root = resolve_root()
    cfg = cfg or {}
    q = cfg.get("queue", {})
    names = {
        "user": str(q.get("user_dir", "pompts_11/user")),
        "running": str(q.get("running_dir", "pompts_11/running")),
        "done": str(q.get("done_dir", "pompts_11/done")),
        "failed": str(q.get("failed_dir", "pompts_11/failed")),
    }
    result = {}
    for status, rel in names.items():
        p = (root / rel).resolve()
        p.mkdir(parents=True, exist_ok=True)
        result[status] = p
    return result


# ── Метаданные файла промта ───────────────────────────────────

@dataclass
class PromptMeta:
    """Метаданные промта из шапки файла."""

    path: Path
    task_id: str
    title: str
    body: str
    status: str = "pending"
    model: str = "auto"
    chat_id: str = ""
    created_at: str = ""
    headers: Dict[str, str] = field(default_factory=dict)


def parse_prompt(path: Path) -> Optional[PromptMeta]:
    """Разбирает файл промта в PromptMeta.

    Шапка: `# TASK: <title>` + `**Ключ:** value`. Тело — после `---`.
    Возвращает None для невалидного файла (без # TASK).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    lines = text.splitlines()
    title = ""
    headers: Dict[str, str] = {}
    body_lines: List[str] = []
    in_body = False
    for ln in lines:
        if in_body:
            body_lines.append(ln)
            continue
        if ln.startswith("# TASK:"):
            title = ln[len("# TASK:"):].strip()
        m = re.match(r"^\*\*([^*)+):\*\*\s*(.*)$", ln.strip())
        if m:
            headers[m.group(1).strip()] = m.group(2).strip()
        if ln.strip() == "---":
            in_body = True
    if not title:
        return None
    task_id = headers.get("Task ID") or _derive_task_id(path)
    return PromptMeta(
        path=path,
        task_id=task_id,
        title=title,
        body="\n".join(body_lines).strip(),
        status=headers.get("Status", "pending"),
        model=headers.get("Model", "auto"),
        chat_id=headers.get("Chat ID", ""),
        created_at=headers.get("Created At", ""),
        headers=headers,
    )


def _derive_task_id(path: Path) -> str:
    m = _TS_RE.search(path.name)
    if m:
        return m.group(1)
    return uuid.uuid4().hex[:12]


def new_prompt_file(
    text: str,
    title: str = "Task",
    model: str = "auto",
    status: str = "pending",
    queue_status: str = "user",
    cfg: Dict[str, Any] | None = None,
) -> Path:
    """Создаёт файл промта в папке очереди. Возвращает путь.

    Имя: task_<YYYYmmdd_HHMMSS>_<taskid>.md
    """
    dirs = queue_dirs(cfg)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    tid = uuid.uuid4().hex[:6]
    path = dirs[queue_status] / f"task_{ts}_{tid}.md"
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    content = (
        f"# TASK: {title}\n"
        f"**Task ID:** {tid}\n"
        f"**Status:** {status}\n"
        f"**Model:** {model}\n"
        f"**Created At:** {stamp}\n"
        f"---\n"
        f"{text}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def scan(status: str = "user", cfg: Dict[str, Any] | None = None) -> List[PromptMeta]:
    """Сканирует папку очереди (user/running/done/failed), сортирует по имени."""
    dirs = queue_dirs(cfg)
    folder = dirs.get(status, dirs["user"])
    metas = []
    for p in sorted(folder.glob("*.md")):
        if p.name.startswith("."):
            continue
        meta = parse_prompt(p)
        if meta:
            metas.append(meta)
    return metas


def move_to_status(path: Path, status: str, cfg: Dict[str, Any] | None = None) -> Path:
    """Перемещает файл промта в папку статуса (atomic rename)."""
    dirs = queue_dirs(cfg)
    target = dirs.get(status, dirs["user"]) / path.name
    path.rename(target)
    return target


def set_report(
    path: Path,
    status: str,
    report_text: str,
    cfg: Dict[str, Any] | None = None,
) -> Path:
    """Дописывает `## Отчёт` в файл и перемещает его в папку статуса."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    if "## Отчёт" in text:
        head, _, _ = text.partition("## Отчёт")
        text = head.rstrip() + "\n\n## Отчёт\n" + report_text + "\n"
    else:
        text = text.rstrip() + "\n\n## Отчёт\n" + report_text + "\n"
    path.write_text(text, encoding="utf-8")
    return move_to_status(path, status, cfg)


def queue_counts(cfg: Dict[str, Any] | None = None) -> Dict[str, int]:
    """Счётчик файлов по папкам очереди."""
    dirs = queue_dirs(cfg)
    counts = {}
    for status, folder in dirs.items():
        counts[status] = sum(1 for p in folder.glob("*.md") if not p.name.startswith("."))
    return counts
