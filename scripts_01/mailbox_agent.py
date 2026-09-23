#!/usr/bin/env python3
"""
mailbox_agent.py — живой агент buffy-server на whimco (mailbox-канал).

Реализует capability `mailbox_agent` (missing_registry, промт
`pompts_11/promt02_mailbox_agent.md`). Агент живёт на сервере whimco,
для которого mailbox `/opt/freebuff-mailbox/` — локальная файловая система.

Протокол общения (v1.1): `mailbox/PROTOCOL.md`.
  - входящие:  /opt/freebuff-mailbox/to-server/  (письма от phone/desktop)
  - исходящие: to-phone/ | to-desktop/            (отчёты SRV-NNN)
  - архив:     archive/                           (обработанное, не удаляется)

Закрытый словарь интентов (ANTI-6b): ping / status / hello.
Неизвестный интент — письмо-ошибка отправителю (не выдумываем поведение).

Использование:
    python scripts_01/mailbox_agent.py --once          # один проход (cron/тесты)
    python scripts_01/mailbox_agent.py --loop          # демон (default 300s)
    python scripts_01/mailbox_agent.py --loop 60       # демон с интервалом 60s
    python scripts_01/mailbox_agent.py --status        # JSON-статус в stdout

Конфиг (env):
    FREEBUFF_MAILBOX_DIR         (default /opt/freebuff-mailbox)
    FREEBUFF_MAILBOX_AGENT_ID    (default buffy-server)
    FREEBUFF_MAILBOX_INTERVAL_S  (default 300)
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional

# ── Конфигурация (env-driven, без магических строк в коде) ──────────────

WORKSPACE = Path(__file__).resolve().parent.parent

MAILBOX_DIR = Path(os.environ.get("FREEBUFF_MAILBOX_DIR", "/opt/freebuff-mailbox"))
AGENT_ID = os.environ.get("FREEBUFF_MAILBOX_AGENT_ID", "buffy-server")
AGENT_PREFIX = "SRV"
DEFAULT_INTERVAL_S = int(os.environ.get("FREEBUFF_MAILBOX_INTERVAL_S", "300"))

INBOX_SUBDIR = "to-server"
ARCHIVE_SUBDIR = "archive"
OUT_SUBDIRS = ("to-phone", "to-desktop")

# Шапка письма: "# MSG-001 · от: buffy-phone · кому: ... · <date> · статус: NEW"
_HEADER_RE = re.compile(
    r"^#\s*(?P<id>[A-Za-z]+-\d+)\s*·\s*от:\s*(?P<from>\S+)"
    r"(?:\s*·\s*кому:\s*(?P<to>[^·\n]+))?",
    re.MULTILINE,
)
# Интент может быть в шапке или теле: "интент: ping" / "intent: ping"
_INTENT_RE = re.compile(r"^\s*(?:интент|intent)\s*:\s*(?P<intent>\S+)", re.MULTILINE)
_STATUS_RE = re.compile(r"статус\s*:\s*(?P<status>\S+)")

_KNOWN_INTENTS = ("ping", "status", "hello", "wip_report")

# Параметры интента wip_report (промт pompts_11/promt03_mailbox_agent_wip_report.md):
# строго фиксированный allowlist команд, shell=False, read-only.
WIP_REPO_PATH = Path(os.environ.get("FREEBUFF_WIP_REPO", "/opt/freebuff"))
WIP_GIT_TIMEOUT_S = 20
_GIT_STATUS_CMD = ("git", "status", "--porcelain")
_GIT_HEAD_CMD = ("git", "rev-parse", "--short", "HEAD")
_GIT_BEHIND_CMD = ("git", "log", "--oneline", "HEAD..origin/master")

_RUNNING = True


def _request_stop(signum: int, _frame: object) -> None:
    """SIGTERM/SIGINT-handler: мягкая остановка цикла."""
    global _RUNNING
    _RUNNING = False


# ── Модель письма ────────────────────────────────────────────────────────


class MailMessage:
    """Разобранное входящее письмо mailbox.

    Attributes:
        path: путь к файлу письма.
        msg_id: идентификатор из шапки (напр. ``MSG-003``); ``UNKNOWN-<stem>``
            если шапка не распознана.
        sender: отправитель из шапки (напр. ``buffy-phone``).
        intent: интент из тела/шапки; ``unknown`` если не найден/не в словаре.
        status: статус из шапки (``NEW`` по умолчанию).
        body: полный текст письма.
    """

    def __init__(self, path: Path, msg_id: str, sender: str, intent: str,
                 status: str, body: str) -> None:
        self.path = path
        self.msg_id = msg_id
        self.sender = sender
        self.intent = intent
        self.status = status
        self.body = body


def parse_message(path: Path) -> MailMessage:
    """Разобрать письмо: шапка, отправитель, интент, статус.

    Args:
        path: путь к .md файлу письма.

    Returns:
        MailMessage с полями; при нераспознанной шапке msg_id=UNKNOWN-<stem>,
        sender=unknown, intent=unknown (письмо не падает, обработается как unknown).
    """
    body = path.read_text(encoding="utf-8", errors="replace")
    header = _HEADER_RE.search(body)
    msg_id = header.group("id") if header else f"UNKNOWN-{path.stem}"
    sender = header.group("from") if header else "unknown"
    status_m = _STATUS_RE.search(body)
    status = status_m.group("status") if status_m else "NEW"
    intent_m = _INTENT_RE.search(body)
    intent = intent_m.group("intent").lower() if intent_m else "unknown"
    if intent not in _KNOWN_INTENTS:
        intent = "unknown"
    return MailMessage(path, msg_id, sender, intent, status, body)


# ── Исходящие письма (атомарная запись) ─────────────────────────────────


def _next_out_number(mailbox: Path) -> int:
    """Сквозной номер исходящего SRV-NNN: max по всем папкам + 1.

    Args:
        mailbox: корень mailbox.

    Returns:
        Следующий свободный номер (1, если исходящих ещё нет).
    """
    pattern = re.compile(rf"^{AGENT_PREFIX}-(\d+)_")
    nums = [0]
    for sub in (*OUT_SUBDIRS, ARCHIVE_SUBDIR):
        d = mailbox / sub
        if not d.is_dir():
            continue
        for f in d.iterdir():
            m = pattern.match(f.name)
            if m:
                nums.append(int(m.group(1)))
    return max(nums) + 1


def write_reply(mailbox: Path, to_dir: str, sender: str, subject: str,
                body: str) -> Path:
    """Записать ответ SRV-NNN атомарно (.tmp + os.replace).

    Args:
        mailbox: корень mailbox.
        to_dir: подпапка получателя (``to-phone`` / ``to-desktop``).
        sender: кому адресован ответ (строка ``кому:`` в шапке).
        subject: краткая тема (в имя файла).
        body: тело письма (без шапки).

    Returns:
        Путь записанного файла.

    Raises:
        ValueError: если to_dir не из OUT_SUBDIRS.
    """
    if to_dir not in OUT_SUBDIRS:
        raise ValueError(f"Недопустимая папка получателя: {to_dir}")
    n = _next_out_number(mailbox)
    slug = re.sub(r"[^a-z0-9]+", "_", subject.lower()).strip("_")[:40] or "reply"
    date = datetime.now().strftime("%Y-%m-%d")
    name = f"{AGENT_PREFIX}-{n:03d}_{AGENT_ID}_{date}_{slug}.md"
    target = mailbox / to_dir / name
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = (
        f"# {AGENT_PREFIX}-{n:03d} · от: {AGENT_ID} · кому: {sender} · "
        f"{ts} · статус: NEW\n\n{body}\n"
    )
    tmp = target.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, target)
    return target


# ── Обработчики интентов (закрытый словарь) ─────────────────────────────


def _sender_out_dir(sender: str) -> str:
    """Сопоставить отправителя папке ответа.

    Args:
        sender: значение ``от:`` из шапки (напр. ``buffy-phone``).

    Returns:
        Подпапка mailbox (``to-phone``/``to-desktop``); unknown → ``to-phone``
        (письмо-ошибка всё равно доставится и будет видно человеку).
    """
    if "desktop" in sender:
        return "to-desktop"
    return "to-phone"


def _handle_ping(mailbox: Path, msg: MailMessage) -> Path:
    """Интент ping → pong + краткий статус."""
    return write_reply(
        mailbox, _sender_out_dir(msg.sender), msg.sender, "pong",
        f"**pong** · {AGENT_ID} жив · получено {msg.msg_id} от {msg.sender}\n",
    )


def _handle_status(mailbox: Path, msg: MailMessage) -> Path:
    """Интент status → JSON-отчёт о состоянии агента и mailbox."""
    inbox = mailbox / INBOX_SUBDIR
    report = {
        "agent": AGENT_ID,
        "capability": "mailbox_agent",
        "host": os.uname().nodename,
        "python": sys.version.split()[0],
        "mailbox_dir": str(mailbox),
        "known_intents": list(_KNOWN_INTENTS),
        "inbox_pending": sorted(p.name for p in inbox.glob("*.md")) if inbox.is_dir() else [],
        "counts": {
            sub: len(list((mailbox / sub).glob("*.md"))) if (mailbox / sub).is_dir() else 0
            for sub in (*OUT_SUBDIRS, INBOX_SUBDIR, ARCHIVE_SUBDIR)
        },
    }
    return write_reply(
        mailbox, _sender_out_dir(msg.sender), msg.sender, "status",
        "```json\n" + json.dumps(report, ensure_ascii=False, indent=2) + "\n```",
    )


def _handle_hello(mailbox: Path, msg: MailMessage) -> Path:
    """Интент hello (онбординг) → приветствие + готовность + словарь интентов."""
    return write_reply(
        mailbox, _sender_out_dir(msg.sender), msg.sender, "onboard_ready",
        (
            f"**{AGENT_ID} на связи.** Онбординг по протоколу mailbox v1.1 завершён.\n\n"
            f"- Агент: `{AGENT_ID}` (capability `mailbox_agent`, SRV-нумерация)\n"
            f"- Входящие: `{mailbox / INBOX_SUBDIR}/`\n"
            f"- Известные интенты: {', '.join(_KNOWN_INTENTS)}\n"
            f"- Правила: письма не удаляются (archive/), секреты не передаются,\n"
            f"  shell из писем не исполняется (закрытый словарь).\n\n"
            f"Ответ на {msg.msg_id} от {msg.sender}.\n"
        ),
    )


def _run_git_allowlisted(args: tuple) -> tuple[bool, str]:
    """Выполнить одну allowlist-команду git (read-only, shell=False).

    Args:
        args: полный argv-кортеж команды (только из констант _GIT_*_CMD).

    Returns:
        (ok, stdout) — ok=False при ненулевом коде/таймауте/ошибке запуска.
    """
    if args not in (_GIT_STATUS_CMD, _GIT_HEAD_CMD, _GIT_BEHIND_CMD):
        return False, f"команда вне allowlist: {args!r}"
    try:
        proc = subprocess.run(
            list(args), cwd=str(WIP_REPO_PATH), shell=False,
            capture_output=True, text=True, timeout=WIP_GIT_TIMEOUT_S,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, f"git error: {exc}"
    if proc.returncode != 0:
        return False, (proc.stderr or "unknown git error").strip()[:300]
    return True, proc.stdout.strip()


def _handle_wip_report(mailbox: Path, msg: MailMessage) -> Path:
    """Интент wip_report → read-only JSON-отчёт о WIP репозитория.

    Источники (промт promt03): allowlist git-команд + файл refs/remotes.
    Агент ничего не меняет и не исполняет из письма — только докладывает.
    """
    if not WIP_REPO_PATH.is_dir():
        report: Dict[str, object] = {
            "error": f"репозиторий не найден: {WIP_REPO_PATH}", "repo": str(WIP_REPO_PATH),
        }
    else:
        ok_status, status_out = _run_git_allowlisted(_GIT_STATUS_CMD)
        ok_head, head_out = _run_git_allowlisted(_GIT_HEAD_CMD)
        report = {"repo": str(WIP_REPO_PATH)}
        if not ok_status or not ok_head:
            report["error"] = f"status: {status_out[:200]}; head: {head_out[:200]}"
        else:
            tracked_modified = [
                line for line in status_out.splitlines()
                if line.strip() and not line.startswith("??")
            ]
            untracked_top = sorted({
                line[3:].split("/")[0] for line in status_out.splitlines()
                if line.startswith("??")
            })[:15]
            ok_behind, behind_out = _run_git_allowlisted(_GIT_BEHIND_CMD)
            behind = behind_out.splitlines()[:10] if ok_behind else []
            origin_ref = WIP_REPO_PATH / ".git" / "refs" / "remotes" / "origin" / "master"
            origin_master = origin_ref.read_text(encoding="utf-8").strip()[:7] \
                if origin_ref.is_file() else "unknown"
            report.update({
                "head": head_out[:7],
                "origin_master": origin_master,
                "in_sync": head_out[:7] == origin_master,
                "behind_commits": behind,
                "tracked_modified": tracked_modified,
                "untracked_top": untracked_top,
            })
            if not tracked_modified:
                report["suggestion"] = "WIP отсутствует: можно пуллить базу напрямую (auto_deploy снимет SKIP)."
            else:
                report["suggestion"] = (
                    "WIP есть: desktop-агенту — (1) secret-scan изменённых файлов, "
                    "(2) git add <эти пути> + commit wip(server), (3) git fetch origin, "
                    "(4) git merge origin/master --no-edit, (5) git push origin master. "
                    "Checkout -f -B запрещён до коммита WIP (CON-69)."
                )
    return write_reply(
        mailbox, _sender_out_dir(msg.sender), msg.sender, "wip_report",
        "```json\n" + json.dumps(report, ensure_ascii=False, indent=2) + "\n```",
    )


def _handle_unknown(mailbox: Path, msg: MailMessage) -> Path:
    """Неизвестный/отсутствующий интент → письмо-ошибка отправителю."""
    return write_reply(
        mailbox, _sender_out_dir(msg.sender), msg.sender, "unknown_intent",
        (
            f"⚠️ Письмо {msg.msg_id} от {msg.sender}: интент "
            f"`{msg.intent}` отсутствует в закрытом словаре {list(_KNOWN_INTENTS)}.\n"
            f"Письмо заархивировано без исполнения. Для нового интента —\n"
            f"register-first: промт + расширение словаря (см. AGENTS.md §6).\n"
        ),
    )


INTENT_HANDLERS: Dict[str, Callable[[Path, MailMessage], Path]] = {
    "ping": _handle_ping,
    "status": _handle_status,
    "hello": _handle_hello,
    "wip_report": _handle_wip_report,
    "unknown": _handle_unknown,
}


# ── Основной цикл ────────────────────────────────────────────────────────


def process_inbox(mailbox: Path) -> list[str]:
    """Один проход: обработать все NEW-письма в to-server/.

    Письма со статусом не-NEW пропускаются (их уже взял кто-то).
    После успешной обработки письмо перемещается в archive/ (идемпотентность).

    Args:
        mailbox: корень mailbox.

    Returns:
        Список обработанных msg_id (в порядке обработки).
    """
    inbox = mailbox / INBOX_SUBDIR
    if not inbox.is_dir():
        return []
    processed: list[str] = []
    for path in sorted(inbox.glob("*.md")):
        msg = parse_message(path)
        if msg.status != "NEW":
            continue
        handler = INTENT_HANDLERS.get(msg.intent, _handle_unknown)
        reply_path = handler(mailbox, msg)
        print(f"[{AGENT_ID}] {msg.msg_id} ({msg.intent}) → {reply_path.name}",
              file=sys.stderr)
        archived = mailbox / ARCHIVE_SUBDIR / path.name
        os.replace(path, archived)  # атомарно, не удаляем
        processed.append(msg.msg_id)
    return processed


def run_once() -> list[str]:
    """Один проход по inbox (CLI --once)."""
    return process_inbox(MAILBOX_DIR)


def run_loop(interval_s: int) -> None:
    """Демон-цикл (CLI --loop): pass + sleep, выход по SIGTERM.

    Args:
        interval_s: пауза между проходами в секундах.
    """
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    print(f"[{AGENT_ID}] loop started, interval={interval_s}s, "
          f"mailbox={MAILBOX_DIR}", file=sys.stderr)
    while _RUNNING:
        try:
            process_inbox(MAILBOX_DIR)
        except Exception as exc:  # ядро не падает: ошибка в лог, спим дальше
            print(f"[{AGENT_ID}] pass error: {exc}", file=sys.stderr)
        for _ in range(interval_s):
            if not _RUNNING:
                break
            time.sleep(1)
    print(f"[{AGENT_ID}] loop stopped", file=sys.stderr)


def build_status() -> dict:
    """Собрать JSON-статус (CLI --status)."""
    return {
        "agent": AGENT_ID,
        "capability": "mailbox_agent",
        "mailbox_dir": str(MAILBOX_DIR),
        "known_intents": list(_KNOWN_INTENTS),
        "inbox_dir_exists": (MAILBOX_DIR / INBOX_SUBDIR).is_dir(),
        "inbox_pending": len(list((MAILBOX_DIR / INBOX_SUBDIR).glob("*.md")))
        if (MAILBOX_DIR / INBOX_SUBDIR).is_dir() else 0,
    }


def main() -> int:
    """Точка входа CLI: --once | --loop [S] | --status."""
    import argparse

    parser = argparse.ArgumentParser(description="mailbox_agent — buffy-server")
    parser.add_argument("--once", action="store_true", help="один проход")
    parser.add_argument("--loop", nargs="?", const=DEFAULT_INTERVAL_S, type=int,
                        metavar="SECONDS", help=f"демон-цикл (default {DEFAULT_INTERVAL_S}s)")
    parser.add_argument("--status", action="store_true", help="JSON-статус")
    args = parser.parse_args()

    if args.status:
        print(json.dumps(build_status(), ensure_ascii=False, indent=2))
        return 0
    if args.once:
        done = run_once()
        print(json.dumps({"processed": done}, ensure_ascii=False))
        return 0
    run_loop(args.loop if args.loop is not None else DEFAULT_INTERVAL_S)
    return 0


if __name__ == "__main__":
    sys.exit(main())
