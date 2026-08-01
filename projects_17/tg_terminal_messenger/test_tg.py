#!/usr/bin/env python3
"""
Тест Telegram-подключения для tg-terminal-toolkit.

Запуск:
    cd projects/tg_terminal_messenger
    python test_tg.py

Проверяет:
  1. Подключение к Telegram
  2. Информацию о пользователе
  3. Последние 5 диалогов
"""

import asyncio
import os
import sys
***REMOVED***

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telethon.errors.rpcerrorlist import AuthKeyUnregisteredError

from src_06.telegram.client import TGClient


async def _show_profile_and_dialogs(client: TGClient) -> bool:
    """Показать профиль и диалоги. Возвращает False если ключ протух."""
    try:
        me = await client.get_me()
        print(f"\n👤 {me.first_name***REMOVED*** {me.last_name or ''***REMOVED***" if me else "\n👤 ???")
        if me:
            print(f"   Username: @{me.username or 'нет'***REMOVED***")
            print(f"   Phone: {me.phone or 'скрыт'***REMOVED***")

        print(f"\n💬 Последние 5 диалогов:")
        dialogs = await client.get_dialogs(limit=5)
        for d in dialogs:
            unread = f"[{d.unread_count***REMOVED******REMOVED***" if d.unread_count else ""
            print(f"   {unread***REMOVED*** {d.name***REMOVED***")
        return True
    except AuthKeyUnregisteredError:
        return False


async def main():
    client = TGClient(session_name="tg_session")

    print("📡 Подключаюсь к Telegram...")
    is_authorized = await client.connect()

    if not is_authorized:
        print("🔐 Нужна авторизация. На номер +79223919054 придёт код.")
        authorized = await client.start()
        if not authorized:
            print("❌ Не удалось авторизоваться.")
            await client.disconnect()
            return
    else:
        print("✅ Сессия активна!")

    # Загружаем профиль и диалоги (с обработкой протухшего ключа)
    if not await _show_profile_and_dialogs(client):
        # Ключ протух — пересоздаём сессию
        print("🗑️ Ключ протух — удаляю сессию и пересоздаю...")
        await client.disconnect()
        client.session_file.unlink(missing_ok=True)
        client = TGClient(session_name="tg_session")
        await client.connect()
        print("🔐 Нужна авторизация. На номер +79223919054 придёт код.")
        authorized = await client.start()
        if not authorized:
            print("❌ Не удалось авторизоваться.")
            await client.disconnect()
            return
        if not await _show_profile_and_dialogs(client):
            print("❌ Ключ снова протух — попробуй позже.")
            await client.disconnect()
            return

    print(f"\n✅ Тест пройден!")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
