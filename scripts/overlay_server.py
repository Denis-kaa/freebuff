#!/usr/bin/env python3
"""
FreeBuff Overlay Server — IPC-сервер статуса агента.

Принимает обновления статуса от агентов через Unix socket,
отображает плавающее окно с прогрессом через Termux:Float.

Протокол (JSON, newline-delimited):
  → {"type":"status","task":"...","progress":0.5,"agent":"Buffy"***REMOVED***
  → {"type":"command","action":"pause|resume|stop"***REMOVED***  (от сервера)
  ← {"type":"ack"***REMOVED***

Запуск:
   python scripts/overlay_server.py
   # или через Termux:Float:
   termux-float python scripts/overlay_server.py

IPC socket: /data/data/com.termux/files/usr/var/run/freebuff_overlay.sock
"""

import json
import os
import select
import signal
import socket
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

# ── Конфигурация ──────────────────────────────────────────────

SOCKET_PATH = "/data/data/com.termux/files/usr/var/run/freebuff_overlay.sock"
FLOAT_WIDTH = 40
REFRESH = 0.2  # интервал перерисовки UI в секундах


class Command(Enum):
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"


@dataclass
class AgentState:
    """Текущее состояние агента."""
    agent: str = "—"
    task: str = "Ожидание..."
    progress: float = 0.0       # 0.0 – 1.0
    status: str = "idle"        # idle | running | paused | done | error
    message: str = ""
    last_update: float = 0.0

    def reset(self) -> None:
        self.agent = "—"
        self.task = "Ожидание..."
        self.progress = 0.0
        self.status = "idle"
        self.message = ""


# ── UI (Termux:Float совместимый вывод) ───────────────────────

def _bar(progress: float, width: int = 20) -> str:
    """Прогресс-бар: ████████░░░░░░░░░░░░ 40%."""
    filled = int(progress * width)
    pct = int(progress * 100)
    return f"▐{'█' * filled***REMOVED***{'░' * (width - filled)***REMOVED***▌ {pct***REMOVED***%"


def _status_icon(status: str) -> str:
    return {"idle": "⏳", "running": "🔄", "paused": "⏸️",
            "done": "✅", "error": "❌"***REMOVED***.get(status, "❓")


def render_frame(state: AgentState, pending_cmd: Optional[Command***REMOVED*** = None) -> str:
    """Отрендерить кадр оверлея."""
    icon = _status_icon(state.status)
    bar = _bar(state.progress)

    lines = [
        "╔" + "═" * (FLOAT_WIDTH - 2) + "╗",
        f"║ {'FreeBuff Overlay':^{FLOAT_WIDTH - 4***REMOVED******REMOVED*** ║",
        "╠" + "═" * (FLOAT_WIDTH - 2) + "╣",
        f"║ {icon***REMOVED*** Агент: {state.agent:<{FLOAT_WIDTH - 11***REMOVED******REMOVED*** ║",
        f"║ 📋 {state.task[:FLOAT_WIDTH - 5***REMOVED***:<{FLOAT_WIDTH - 5***REMOVED******REMOVED*** ║",
        f"║ {bar:<{FLOAT_WIDTH - 4***REMOVED******REMOVED*** ║",
        f"║ Статус: {state.status:<{FLOAT_WIDTH - 10***REMOVED******REMOVED*** ║",
    ***REMOVED***

    if state.message:
        lines.append(f"║ 💬 {state.message[:FLOAT_WIDTH - 5***REMOVED***:<{FLOAT_WIDTH - 5***REMOVED******REMOVED*** ║")

    if pending_cmd:
        lines.append(f"║ ⚡ Команда: {pending_cmd.value:<{FLOAT_WIDTH - 13***REMOVED******REMOVED*** ║")

    lines.append("╠" + "═" * (FLOAT_WIDTH - 2) + "╣")
    lines.append(f"║ [p***REMOVED***ause [r***REMOVED***esume [s***REMOVED***top [q***REMOVED***uit{' ' * (FLOAT_WIDTH - 32)***REMOVED*** ║")
    lines.append("╚" + "═" * (FLOAT_WIDTH - 2) + "╝")

    return "\n".join(lines)


# ── Socket Server ─────────────────────────────────────────────

class OverlayServer:
    """Главный сервер оверлея. Слушает Unix socket, рендерит UI."""

    def __init__(self):
        self._state = AgentState()
        self._running = True
        self._pending_command: Optional[Command***REMOVED*** = None

    # ── socket ────────────────────────────────────────────

    def _setup_socket(self) -> socket.socket:
        """Создать и привязать Unix socket."""
        # Создаём директорию и удаляем старый socket
        sock_dir = os.path.dirname(SOCKET_PATH)
        os.makedirs(sock_dir, exist_ok=True)
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(SOCKET_PATH)
        sock.listen(1)
        sock.setblocking(False)
        os.chmod(SOCKET_PATH, 0o666)
        return sock

    def _handle_client(self, conn: socket.socket) -> None:
        """Обработать входящее сообщение от клиента."""
        try:
            data = conn.recv(4096)
            if not data:
                return
            msg = json.loads(data.decode("utf-8"))

            if msg.get("type") == "status":
                self._state.agent = msg.get("agent", self._state.agent)
                self._state.task = msg.get("task", self._state.task)
                self._state.progress = float(msg.get("progress", self._state.progress))
                self._state.status = msg.get("status", self._state.status)
                self._state.message = msg.get("message", "")
                self._state.last_update = time.time()

                # Отправить pending command
                if self._pending_command:
                    cmd = json.dumps({
                        "type": "command",
                        "action": self._pending_command.value
                    ***REMOVED***)
                    conn.sendall(cmd.encode("utf-8"))
                    self._pending_command = None

                conn.sendall(b'{"type":"ack"***REMOVED***\n')

        except (json.JSONDecodeError, ConnectionError):
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # ── команды ───────────────────────────────────────────

    def _handle_command(self, cmd: Command) -> None:
        """Отправить команду агенту (при следующем status-сообщении)."""
        self._pending_command = cmd
        if cmd == Command.STOP:
            self._state.reset()

    # ── главный цикл ──────────────────────────────────────

    def run(self) -> None:
        """Запустить сервер."""
        sock = self._setup_socket()

        def _cleanup(signum, frame):
            self._running = False

        signal.signal(signal.SIGTERM, _cleanup)
        signal.signal(signal.SIGINT, _cleanup)

        # Настройка stdin для чтения клавиш (p/r/s/q)
        has_termios = False
        old_settings = None
        fd = None
        if sys.stdin.isatty():
            try:
                import termios
                import tty
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                tty.setcbreak(fd)
                has_termios = True
            except (ImportError, OSError):
                pass

        try:
            self._main_loop(sock, has_termios)
        finally:
            if has_termios and old_settings is not None:
                import termios
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sock.close()
            if os.path.exists(SOCKET_PATH):
                os.unlink(SOCKET_PATH)

    def _main_loop(self, sock: socket.socket, has_termios: bool) -> None:
        """Главный цикл: socket + stdin + render."""
        last_render = 0.0

        while self._running:
            now = time.time()

            # Проверяем socket на новые подключения
            try:
                conn, _ = sock.accept()
                self._handle_client(conn)
            except BlockingIOError:
                pass

            # Проверяем stdin на клавиши (p/r/s/q)
            if has_termios:
                r, _, _ = select.select([sys.stdin***REMOVED***, [***REMOVED***, [***REMOVED***, 0)
                if r:
                    ch = sys.stdin.read(1)
                    if ch == 'p':
                        self._handle_command(Command.PAUSE)
                    elif ch == 'r':
                        self._handle_command(Command.RESUME)
                    elif ch == 's':
                        self._handle_command(Command.STOP)
                    elif ch == 'q':
                        self._running = False
                        break

            # Перерисовка
            if now - last_render > REFRESH:
                frame = render_frame(self._state, self._pending_command)
                sys.stdout.write("\033[H\033[J" + frame + "\n")
                sys.stdout.flush()
                last_render = now

            time.sleep(0.05)


# ── Entry Point ────────────────────────────────────────────────

if __name__ == "__main__":
    server = OverlayServer()
    server.run()
