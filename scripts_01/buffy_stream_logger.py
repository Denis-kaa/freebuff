#!/usr/bin/env python3
"""
buffy_stream_logger.py — Логирование ответов Buffy в стрим-сессию.

Позволяет Buffy (или любому внешнему агенту) записывать свои ответы
в текущую стрим-сессию. Если активной сессии нет — создаёт новую.

Использование из кода:
    from scripts_01.buffy_stream_logger import log_assistant, log_user
    log_assistant("Рассказал пользователю о StreamBridge.")

CLI:
    python scripts_01/buffy_stream_logger.py "Текст ответа ассистента"
    python scripts_01/buffy_stream_logger.py --role user "Текст запроса"
    echo "Текст ответа" | python scripts_01/buffy_stream_logger.py --role assistant
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from scripts_01.stream_bridge import StreamBridge


def _ensure_stream(bridge: StreamBridge, topic: str = "Buffy chat") -> None:
    """Если нет активной сессии — создать новую."""
    if bridge.session_id is None:
        bridge.start_session(topic=topic)


def log_user(text: str) -> None:
    """Залогировать сообщение пользователя в текущую стрим-сессию."""
    bridge = StreamBridge(auto_bootstrap=True, run_gc=False)
    _ensure_stream(bridge)
    bridge.log_user(text)


def log_assistant(text: str) -> None:
    """Залогировать ответ ассистента (Buffy) в текущую стрим-сессию."""
    bridge = StreamBridge(auto_bootstrap=True, run_gc=False)
    _ensure_stream(bridge)
    bridge.log_assistant(text)


def log_system(text: str) -> None:
    """Залогировать системное сообщение в текущую стрим-сессию."""
    bridge = StreamBridge(auto_bootstrap=True, run_gc=False)
    _ensure_stream(bridge)
    bridge.log_system(text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Log Buffy messages into the active streaming session",
    )
    parser.add_argument("text", nargs="?", help="Message text (or read from stdin)")
    parser.add_argument(
        "--role",
        choices=["user", "assistant", "system"],
        default="assistant",
        help="Role of the message (default: assistant)",
    )
    parser.add_argument(
        "--topic",
        default="Buffy chat",
        help="Topic for a new session if no active session exists",
    )

    args = parser.parse_args()

    if args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(1)

    if not text:
        print("❌ Message text is empty")
        sys.exit(1)

    bridge = StreamBridge(auto_bootstrap=True, run_gc=False)
    _ensure_stream(bridge, topic=args.topic)

    if args.role == "user":
        bridge.log_user(text)
    elif args.role == "system":
        bridge.log_system(text)
    else:
        bridge.log_assistant(text)

    print(f"✅ Logged {args.role} message ({len(text)} chars)")


if __name__ == "__main__":
    main()
