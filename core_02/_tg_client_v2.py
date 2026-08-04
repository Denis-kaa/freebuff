"""TGClient extension fork (Phase 5.3-D, DEBT-5.21 closure).

Wraps an existing TGClient (from projects_17/tg_terminal_messenger) to expose
Telethon event subscription API + `ids=` kwarg on `get_messages`.

Architecture (per ADR-011 Option 3):
  - WRAP, not extend — preserves upstream boundary (projects_17 untouched).
  - Bootstrap via injection: caller creates TGClient via _get_tg_client_factory(),
    then wraps it with TGClientV2.
  - The 3 new methods (add_event_handler, remove_event_handler, get_messages
    with ids=) delegate to the underlying telethon TelegramClient stored as
    TGClient._client (private attribute; acceptable for a core fork).

CON-31 resolution: the `ids=` kwarg on get_messages() eliminates the need for
the limit-scan + client-side filter pattern that e2e_remote_sync.py stage3 used.
"""

from __future__ import annotations

***REMOVED***
from typing import Any, Callable, List, Optional, Union


class TGClientV2:
    """Thin wrapper around an existing TGClient, adding event subscription + ids= kwarg.

    Usage::

        from core_02.telegram_contract import _get_tg_client_factory
        from core_02._tg_client_v2 import TGClientV2

        base = _get_tg_client_factory()(session_path)
        client = TGClientV2(base)
        await client.connect()
        client.add_event_handler(my_callback, events.NewMessage(chats=[chat_id***REMOVED***))
        msgs = await client.get_messages(chat_id, ids=[123, 456***REMOVED***)
    """

    def __init__(self, base_client: Any) -> None:
        """Wrap an existing TGClient instance.

        Args:
            base_client: An instance of ``projects_17.tg_terminal_messenger.src.telegram.client.TGClient``
                (or any object with a ``_client`` attribute that is a telethon ``TelegramClient``).

        Raises:
            TypeError: If ``base_client`` does not have a ``_client`` attribute
                (expected from TGClient's private telethon reference).
        """
        if not hasattr(base_client, "_client"):
            raise TypeError(
                f"TGClientV2 requires a base_client with a '_client' attribute "
                f"(telethon TelegramClient). Got {type(base_client).__name__!r***REMOVED***: "
                f"{base_client!r***REMOVED***. Pass a valid TGClient instance from "
                f"projects_17.tg_terminal_messenger.src.telegram.client.TGClient."
            )
        self._base = base_client
        # Telethon TelegramClient instance (private attribute of TGClient)
        self._telethon: Any = base_client._client

    # ── Lifecycle delegation ──────────────────────────────────────────────────

    async def connect(self) -> None:
        """Delegate to TGClient.connect()."""
        await self._base.connect()

    async def disconnect(self) -> None:
        """Delegate to TGClient.disconnect()."""
        await self._base.disconnect()

    async def send_message(self, entity: Any, text: str, **kwargs: Any) -> Any:
        """Delegate to TGClient.send_message()."""
        return await self._base.send_message(entity, text, **kwargs)

    async def get_me(self) -> Any:
        """Delegate to TGClient.get_me()."""
        return await self._base.get_me()

    # ── CON-31 resolution: get_messages with optional ids= kwarg ───────────────

    async def get_messages(
        self,
        entity: Any,
        limit: int = 5,
        ids: Optional[Union[int, List[int***REMOVED******REMOVED******REMOVED*** = None,
    ) -> List[Any***REMOVED***:
        """Fetch messages by ID (via telethon's native ids= kwarg) or via limit-scan.

        This is the CON-31 resolution: previously e2e_remote_sync.py stage3 had to
        use ``client.get_messages(chat_id, limit=100)`` + client-side ``id`` filter
        because the upstream TGClient wrapper did not expose ``ids=``. Now the fork
        delegates directly to telethon's ``get_messages(entity, ids=ids)`` when
        ``ids`` is provided, falling back to the original limit-scan behaviour when
        ``ids`` is None.

        Args:
            entity: Target chat/peer (int chat_id or telethon entity).
            limit: Max messages to fetch (used only when ``ids`` is None).
            ids: Optional message ID(s) to fetch directly. Can be int or list of ints.

        Returns:
            List of telethon ``Message`` objects (or ``_FakeMessage`` in tests).
        """
        if ids is not None:
            return await self._telethon.get_messages(entity, ids=ids)
        return await self._base.get_messages(entity, limit=limit)

    # ── ADR-011: event subscription API ───────────────────────────────────────

    def add_event_handler(self, callback: Callable, event: Any) -> None:
        """Register a callback for a Telethon event (e.g. ``events.NewMessage``).

        Args:
            callback: Sync function ``(event) -> None``. **Must not be async** —
                Telethon does NOT await coroutines returned by ``add_event_handler``.
                Use ``RemoteSyncListener._on_new_message`` (sync N-1 fix).
            event: A Telethon event filter, e.g. ``events.NewMessage(chats=[chat_id***REMOVED***)``.
        """
        self._telethon.add_event_handler(callback, event)

    def remove_event_handler(self, callback: Callable, event: Any) -> None:
        """Deregister a previously registered event handler.

        Args:
            callback: The same function reference passed to ``add_event_handler``.
            event: The same event filter.
        """
        self._telethon.remove_event_handler(callback, event)