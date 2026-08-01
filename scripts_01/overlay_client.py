#!/usr/bin/env python3
"""
FreeBuff Overlay Client — отправка статуса агента в оверлей.

Использование в коде агента:
    from scripts_01.overlay_client import OverlayClient

    client = OverlayClient()
    client.status(task="Code review", progress=0.3, agent="Buffy")
    client.status(task="Code review", progress=0.7, status="running")
    client.done(task="Code review", message="2 issues found")

    # Проверить команды от сервера:
    cmd = client.check_command()
    if cmd == "pause":
        ...
    elif cmd == "resume":
        ...
    elif cmd == "stop":
        ...

Также работает как CLI:
    python scripts_01/overlay_client.py status --task "Code review" --progress 0.5
    python scripts_01/overlay_client.py done --task "Deploy" --message "OK"
"""

import json
import os
import socket
import sys
from typing import Optional

SOCKET_PATH = "/data/data/com.termux/files/usr/var/run/freebuff_overlay.sock"


class OverlayClient:
    """Клиент для отправки статуса в оверлей-сервер."""

    _TIMEOUT = 2  # секунды на ответ сервера

    def __init__(self):
        self._last_command: Optional[str***REMOVED*** = None

    def _send(self, payload: dict) -> Optional[dict***REMOVED***:
        """Отправить JSON и получить ответ."""
        if not os.path.exists(SOCKET_PATH):
            return None

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self._TIMEOUT)
            sock.connect(SOCKET_PATH)

            data = json.dumps(payload).encode("utf-8")
            sock.sendall(data)

            response = sock.recv(4096)
            sock.close()

            return json.loads(response.decode("utf-8"))
        except (socket.timeout, ConnectionRefusedError, FileNotFoundError,
                json.JSONDecodeError, OSError):
            return None

    # ── публичные методы ──────────────────────────────────

    def status(self, task: str = "", progress: float = -1,
               agent: str = "", status: str = "running",
               message: str = "") -> None:
        """Отправить обновление статуса.

        Команды от сервера проверяются через check_command().
        """
        payload: dict = {"type": "status"***REMOVED***
        if task:
            payload["task"***REMOVED*** = task
        if progress >= 0:
            payload["progress"***REMOVED*** = progress
        if agent:
            payload["agent"***REMOVED*** = agent
        if status:
            payload["status"***REMOVED*** = status
        if message:
            payload["message"***REMOVED*** = message

        resp = self._send(payload)
        if resp and resp.get("type") == "command":
            self._last_command = resp["action"***REMOVED***

    def done(self, task: str = "", message: str = "") -> None:
        """Пометить задачу выполненной."""
        self.status(task=task, progress=1.0, status="done", message=message)

    def error(self, task: str = "", message: str = "") -> None:
        """Сообщить об ошибке."""
        self.status(task=task, status="error", message=message)

    def check_command(self) -> Optional[str***REMOVED***:
        """Проверить, есть ли ожидающая команда (после последнего status).

        Возвращает 'pause', 'resume', 'stop' или None.
        """
        cmd = self._last_command
        self._last_command = None
        return cmd


# ── CLI ───────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="FreeBuff Overlay Client")
    sub = parser.add_subparsers(dest="action")

    p_status = sub.add_parser("status", help="Отправить обновление статуса")
    p_status.add_argument("--task", default="")
    p_status.add_argument("--progress", type=float, default=-1)
    p_status.add_argument("--agent", default="")
    p_status.add_argument("--status", default="running")
    p_status.add_argument("--message", default="")

    p_done = sub.add_parser("done", help="Пометить задачу выполненной")
    p_done.add_argument("--task", default="")
    p_done.add_argument("--message", default="")

    p_err = sub.add_parser("error", help="Сообщить об ошибке")
    p_err.add_argument("--task", default="")
    p_err.add_argument("--message", default="")

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(1)

    client = OverlayClient()

    if args.action == "status":
        client.status(
            task=args.task, progress=args.progress,
            agent=args.agent, status=args.status, message=args.message
        )
        cmd = client.check_command()
        print(f"Status sent. Command: {cmd***REMOVED***" if cmd else "Status sent.")
    elif args.action == "done":
        client.done(task=args.task, message=args.message)
        print("Done.")
    elif args.action == "error":
        client.error(task=args.task, message=args.message)
        print("Error reported.")


if __name__ == "__main__":
    main()
