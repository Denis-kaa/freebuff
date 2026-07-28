#!/usr/bin/env python3
"""
auto_save.py — Автоматическое сохранение диалога Buffy в стрим-сессию.

Использование (из Buffy):

  1. При старте сессии (один раз):
     python scripts/auto_save.py --start "Тема сессии"
     → сохраняет session_id в /tmp/buffy_stream.sid

  2. При каждом сообщении:
     echo "текст пользователя" | python scripts/auto_save.py --save-user
     echo "текст ответа" | python scripts/auto_save.py --save-assistant

  3. При завершении:
     python scripts/auto_save.py --end

  Или напрямую:
     python scripts/auto_save.py --save-user "текст"
     python scripts/auto_save.py --save-assistant "текст"
"""

import argparse
import json
import os
import sys
***REMOVED***

WORKSPACE = Path(__file__).resolve().parent.parent
SID_FILE = Path("/tmp/buffy_stream.sid")

# Сентинел для stdin-режима: отличает "--save-user" от "--save-user текст" и от "не указано"
_STDIN = object()

# Добавляем freebuff в путь
sys.path.insert(0, str(WORKSPACE))


def _get_bridge():
    """Ленивое создание StreamBridge (не на уровне модуля)."""
    try:
        from scripts.stream_bridge import StreamBridge
        return StreamBridge(auto_bootstrap=True, run_gc=True)
    except ImportError as e:
        print(f"❌ StreamBridge не загружен: {e***REMOVED***", file=sys.stderr)
        return None


# Глобальный инстанс (инициализируется при первом вызове)
_bridge_instance = None


def get_bridge():
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = _get_bridge()
    return _bridge_instance


def cmd_start(topic: str, project: str = "freebuff") -> str:
    """Начать новую стрим-сессию."""
    b = get_bridge()
    if b is None:
        return ""

    # Проверяем, может уже есть активная (bootstrap)
    if b.session_id:
        sid = b.session_id[:8***REMOVED***
        print(f"🔄 Уже активна сессия: {sid***REMOVED***")
        return sid

    # Стартуем новую
    b.start_session(topic=topic)
    sid_file = SID_FILE
    if b.session_id:
        sid_file.write_text(b.session_id)
        sid = b.session_id[:8***REMOVED***
        print(f"✅ Сессия начата: {sid***REMOVED*** | тема: {topic***REMOVED***")
        print(f"   Для остановки: python scripts/auto_save.py --end")
        return sid
    else:
        print("❌ Не удалось начать сессию")
        return ""


def cmd_save(role: str, text: str | None = None) -> bool:
    """Сохранить сообщение (user/assistant/system)."""
    b = get_bridge()
    if b is None:
        return False

    # Читаем из stdin если нет текста в аргументе
    if text is None or not text.strip():
        if not sys.stdin.isatty():
            text = sys.stdin.read()
        if not text or not text.strip():
            print("❌ Нет текста. Передай аргументом или через stdin (echo | ...)", file=sys.stderr)
            return False

    text = text.strip()
    if not text:
        return False

    # Сохраняем
    if role == "user":
        result = b.log_user(text)
    elif role == "assistant":
        result = b.log_assistant(text)
    elif role == "system":
        result = b.log_system(text)
    else:
        print(f"❌ Неизвестная роль: {role***REMOVED***", file=sys.stderr)
        return False

    if result is not None:
        # Выводим JSON со статусом (для парсинга другими скриптами)
        if not sys.stdout.isatty():
            print(json.dumps({
                "status": "ok",
                "msg_num": result,
                "role": role,
                "chars": len(text),
            ***REMOVED***))
        return True
    else:
        print("❌ Нет активной сессии. Сначала: --start", file=sys.stderr)
        return False


def cmd_end(do_conspect: bool = True) -> str:
    """Завершить сессию."""
    b = get_bridge()
    if b is None:
        return ""

    path = b.end_session(do_conspect=do_conspect)
    if SID_FILE.exists():
        SID_FILE.unlink()
    if path:
        print(f"✅ Сессия завершена. Конспект: {path***REMOVED***")
    else:
        print("✅ Сессия завершена.")
    return path


def cmd_status() -> dict:
    """Статус текущей сессии."""
    b = get_bridge()
    if b is None:
        return {"status": "no_bridge"***REMOVED***

    status = b.get_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return status


def main():
    parser = argparse.ArgumentParser(
        description="auto_save — автоматическое сохранение диалога Buffy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts/auto_save.py --start "Рефакторинг TUI"
  python scripts/auto_save.py --save-user "Привет, сделай рефакторинг"
  python scripts/auto_save.py --save-assistant "Начинаю рефакторинг..."
  echo "короткий текст" | python scripts/auto_save.py --save-assistant
  python scripts/auto_save.py --end
  python scripts/auto_save.py --status
        """,
    )

    parser.add_argument("--start", metavar="TOPIC", nargs="?", const="", help="Начать сессию")
    parser.add_argument("--save-user", metavar="TEXT", nargs="?", const=_STDIN, default=None, help="Сохранить сообщение пользователя")
    parser.add_argument("--save-assistant", metavar="TEXT", nargs="?", const=_STDIN, default=None, help="Сохранить ответ ассистента")
    parser.add_argument("--save-system", metavar="TEXT", nargs="?", const=_STDIN, default=None, help="Сохранить системное сообщение")
    parser.add_argument("--end", action="store_true", help="Завершить сессию")
    parser.add_argument("--no-conspect", action="store_true", help="Не создавать конспект при завершении")
    parser.add_argument("--status", action="store_true", help="Статус сессии")
    parser.add_argument("--project", default="freebuff", help="Название проекта")

    args = parser.parse_args()

    if args.start is not None:
        topic = args.start if args.start else "Buffy session"
        cmd_start(topic, project=args.project)
    elif args.save_user is not None:
        cmd_save("user", None if args.save_user is _STDIN else args.save_user)
    elif args.save_assistant is not None:
        cmd_save("assistant", None if args.save_assistant is _STDIN else args.save_assistant)
    elif args.save_system is not None:
        cmd_save("system", None if args.save_system is _STDIN else args.save_system)
    elif args.end:
        cmd_end(do_conspect=not args.no_conspect)
    elif args.status:
        cmd_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
