#!/usr/bin/env python3
"""Демонизированный запуск uvicorn (для окружений без systemd/supervisord).

Использование:  python run_server.py
Останавливает предыдущий инстанс и поднимает новый на 127.0.0.1:8000.
"""
import os
import sys
import time

HOST = "127.0.0.1"
PORT = "8000"
LOG = "/tmp/uvicorn.log"


def daemonize() -> None:
    """Двойной форк + setsid: процесс переживает завершение родителя."""
    pid = os.fork()
    if pid > 0:
        os.waitpid(pid, 0)  # ждём первый форк
        return
    os.setsid()
    pid2 = os.fork()
    if pid2 > 0:
        os._exit(0)
    # второй ребёнок — демон
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open(LOG, "w") as log, open(os.devnull) as devnull:
        os.dup2(log.fileno(), 1)
        os.dup2(log.fileno(), 2)
        os.dup2(devnull.fileno(), 0)


if __name__ == "__main__":
    # Останавливаем старый инстанс (если есть)
    os.system("pkill -9 -f 'uvicorn app.main' 2>/dev/null || true")
    time.sleep(1)
    daemonize()
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            HOST,
            "--port",
            PORT,
            "--log-level",
            "warning",
        ],
    )
