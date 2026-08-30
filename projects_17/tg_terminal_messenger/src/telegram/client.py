"""
Telegram-клиент для tg-terminal-toolkit.
Обёртка над Telethon: авторизация, диалоги, сообщения.

Два варианта:
  - TGClient: прямой async-клиент (для standalone скриптов)
  - ThreadedTGClient: клиент в отдельном потоке (для TUI на Textual)
    Обходит проблему Python 3.14 + Textual: Telethon.connect() виснет
    внутри event loop Textual.

Использование:
    from src.telegram.client import TGClient
    client = TGClient()
    await client.connect()
    dialogs = await client.get_dialogs(limit=10)

    # Для TUI:
    from src.telegram.client import ThreadedTGClient
    tg = ThreadedTGClient()
    future = tg.connect_async()
    result = await asyncio.wrap_future(future)
"""

from __future__ import annotations

import asyncio
import threading
}
from typing import List, Optional

from telethon import TelegramClient as TelethonClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import Dialog, Message, User


# ── Credentials ──────────────────────────────────────────────

API_ID = 37035907
API_HASH = "383bbe0942526db1133edc23d8ba8023"
PHONE = "+79223919054"

SESSION_DIR = Path(__file__).resolve().parent.parent.parent


def _is_animated(path) -> bool:
    """Реально ли анимированный GIF/WebP (PIL, >1 кадра).

    DocumentAttributeAnimated нельзя вешать на статичный файл — Telegram
    отклоняет такой запрос. Если PIL недоступен — доверяем расширению.
    """
    try:
        from PIL import Image, ImageSequence
        img = Image.open(path)
        return sum(1 for _ in ImageSequence.Iterator(img)) > 1
    except ImportError:
        return True
    except Exception:
        return False


class TGClient:
    """Асинхронный Telegram-клиент с авто-авторизацией."""

    def __init__(self, session_name: str = "tg_session"):
        self._session_path = str(SESSION_DIR / session_name)
        self._client = TelethonClient(self._session_path, API_ID, API_HASH)
        self._connected = False

    @property
    def client(self) -> TelethonClient:
        return self._client

    @property
    def session_file(self) -> Path:
        """Путь к файлу .session."""
        return Path(self._session_path + ".session")

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """Подключиться к Telegram. Если сессия есть — использует её.
        
        При AuthKeyUnregisteredError удаляет старую сессию и требует новую авторизацию.
        """
        from telethon.errors.rpcerrorlist import AuthKeyUnregisteredError
        try:
            await self._client.connect()
        except AuthKeyUnregisteredError:
            await self._client.disconnect()
            session_file = Path(self._session_path + ".session")
            if session_file.exists():
                session_file.unlink()
            self._client = TelethonClient(self._session_path, API_ID, API_HASH)
            await self._client.connect()
        self._connected = True
        return await self._client.is_user_authorized()  # type: ignore[no-any-return]  # Telethon без stubs

    async def start(self, phone: str = PHONE, code_callback=None) -> bool:
        """Авторизоваться (интерактивно запросит код если нужно)."""
        if not self._connected:
            await self.connect()

        if await self._client.is_user_authorized():
            return True

        await self._client.send_code_request(phone)

        if code_callback:
            code = await code_callback()
        else:
            code = input("📱 Telegram-код: ").strip()

        try:
            await self._client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input("🔐 2FA пароль: ").strip()
            await self._client.sign_in(password=password)

        return await self._client.is_user_authorized()  # type: ignore[no-any-return]  # Telethon без stubs

    async def get_me(self) -> Optional[User]:
        """Информация о текущем пользователе."""
        if not self._connected:
            await self.connect()
        return await self._client.get_me()

    async def get_dialogs(self, limit: int = 10) -> List[Dialog]:
        """Последние диалоги."""
        dialogs = await self._client.get_dialogs(limit=limit)
        return list(dialogs)  # type: ignore[no-any-return]  # Telethon без stubs

    async def get_messages(self, entity, limit: int = 5, offset_id: int = 0) -> List[Message]:
        """Сообщения из диалога. offset_id — подгрузить более старые (строго раньше этого id)."""
        return await self._client.get_messages(entity, limit=limit, offset_id=offset_id)  # type: ignore[no-any-return]  # Telethon без stubs

    async def send_message(self, entity, text: str) -> Message:
        """Отправить сообщение."""
        return await self._client.send_message(entity, text)

    async def send_file(self, entity, path: str, caption: str = "", progress_callback=None) -> Message:
        """Отправить файл как медиа. Тип определяется по расширению:
        .jpg/.png → фото, .mp4 → видео, .gif/.webp → анимированная гифка,
        .mp3 → музыка. progress_callback(done, total) вызывается из TG-потока."""
        from telethon.tl.types import DocumentAttributeAnimated, DocumentAttributeFilename

        kwargs: dict = {}
        if str(path).lower().endswith((".gif", ".webp")) and _is_animated(path):
            # Явно помечаем файл как анимированную гифку (DocumentAttributeAnimated),
            # иначе Telegram может показать его простым документом. WebP тоже
            # поддерживается: Telegram транскодирует анимированный webp в гифку.
            # Проверка анимации через PIL: статичный файл не помечаем, иначе
            # Telegram отклонит запрос (атрибут только для анимированных).
            kwargs["attributes"] = [
                DocumentAttributeAnimated(),
                DocumentAttributeFilename(Path(str(path)).name),
            ]
        return await self._client.send_file(
            entity, path, caption=caption or None, progress_callback=progress_callback, **kwargs
        )

    async def download_media(self, message, dest: str, progress_callback=None) -> Optional[str]:
        """Скачать медиа из сообщения в dest. Возвращает путь или None.
        progress_callback(done, total) вызывается из TG-потока."""
        return await self._client.download_media(message, file=dest, progress_callback=progress_callback)

    async def disconnect(self) -> None:
        await self._client.disconnect()
        self._connected = False


# ── Threaded client (workaround for Python 3.14 + Textual) ──

class ThreadedTGClient:
    """TGClient в отдельном потоке со своим event loop.

    Workaround: Telethon.connect() виснет внутри event loop Textual на Python 3.14.
    Изолируем TG-операции в отдельном asyncio-потоке, общаясь через
    asyncio.run_coroutine_threadsafe + asyncio.wrap_future.

    Использование в TUI:
        tg = ThreadedTGClient()
        future = tg.connect_async()
        ok = await asyncio.wrap_future(future)
        ...
        tg.shutdown()
    """

    def __init__(self, session_name: str = "tg_session"):
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._client: Optional[TGClient] = None
        self._ready = threading.Event()
        self._started = False

        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="tg-thread")
        self._thread.start()

        if not self._ready.wait(timeout=5):
            raise RuntimeError("TG thread failed to start")

    # ── потоковый event loop ─────────────────────────────────

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    # ── async → sync мост ────────────────────────────────────

    def _submit(self, coro):
        """Запустить корутину в TG-потоке, вернуть concurrent.futures.Future.

        Вызывающий код делает:  await asyncio.wrap_future(future)
        """
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    # ── публичные async-методы (возвращают Future) ───────────

    def connect_async(self):
        """Подключиться к Telegram. Возвращает Future[bool]."""
        if self._started:
            async def _recheck():
                if self._client is None:
                    return False
                return await self._client.client.is_user_authorized()
            return self._submit(_recheck())
        self._started = True

        async def _connect():
            self._client = TGClient()
            return await self._client.connect()
        return self._submit(_connect())

    def get_me_async(self):
        """Информация о пользователе. Возвращает Future[Optional[User]]."""
        async def _get_me():
            if self._client is None:
                return None
            return await self._client.get_me()
        return self._submit(_get_me())

    def get_dialogs_async(self, limit: int = 10):
        """Список диалогов. Возвращает Future[List[Dialog]]."""
        async def _get_dialogs():
            if self._client is None:
                return []
            return await self._client.get_dialogs(limit)
        return self._submit(_get_dialogs())

    def get_messages_async(self, entity, limit: int = 5, offset_id: int = 0):
        """Сообщения из диалога. Возвращает Future[List[Message]]."""
        async def _get_messages():
            if self._client is None:
                return []
            return await self._client.get_messages(entity, limit, offset_id=offset_id)
        return self._submit(_get_messages())

    def send_message_async(self, entity, text: str):
        """Отправить сообщение. Возвращает Future[Message]."""
        async def _send():
            if self._client is None:
                raise RuntimeError("Not connected")
            return await self._client.send_message(entity, text)
        return self._submit(_send())

    def send_file_async(self, entity, path: str, caption: str = "", progress_callback=None, voice_note: bool = False):
        """Отправить файл как медиа. Возвращает Future[Message].

        voice_note=True — отправить как голосовое сообщение (Telethon сам
        добавит DocumentAttributeAudio(voice=True); поддерживается для
        записей termux-microphone-recorder: .m4a/.ogg/.opus).
        """
        async def _send():
            if self._client is None:
                raise RuntimeError("Not connected")
            kwargs = {"caption": caption, "progress_callback": progress_callback}
            if voice_note:
                kwargs["voice_note"] = True
            return await self._client.send_file(entity, path, **kwargs)
        return self._submit(_send())

    def download_media_async(self, message, dest: str, progress_callback=None):
        """Скачать медиа из сообщения. Возвращает Future[str | None]."""
        async def _download():
            if self._client is None:
                return None
            return await self._client.download_media(
                message, dest, progress_callback=progress_callback
            )
        return self._submit(_download())

    @property
    def telethon_client(self) -> Optional[TelethonClient]:
        """Прямой доступ к TelethonClient (если нужен is_user_authorized)."""
        if self._client is None:
            return None
        return self._client.client

    def is_authorized_async(self):
        """Проверить авторизацию. Возвращает Future[bool]."""
        async def _check():
            if self._client is None:
                return False
            return await self._client.client.is_user_authorized()
        return self._submit(_check())

    # ── shutdown ─────────────────────────────────────────────

    def shutdown(self) -> None:
        """Отключиться и остановить поток."""
        async def _disconnect():
            if self._client is not None:
                try:
                    await self._client.disconnect()
                except Exception:
                    pass

        try:
            future = self._submit(_disconnect())
            future.result(timeout=5)
        except Exception:
            pass

        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=3)
