#!/usr/bin/env python3
"""
tg-terminal-toolkit — Textual TUI для Telegram.
Экранный подход: список чатов → экран переписки.

Горячие клавиши:
    Enter     — открыть выбранный чат (полный экран)
    Esc       — назад к списку чатов / закрыть поиск
    Ctrl+F    — фокус на строку ввода (в режиме чата)
    Ctrl+S    — поиск по чатам
    Ctrl+R    — обновить диалоги
    Ctrl+Q    — выход
"""

import asyncio
import json
import sys
***REMOVED***

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Container
from textual.message import Message
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Header, Footer, ListView, ListItem, Input, Label
from textual.binding import Binding

from telethon.errors import AuthKeyUnregisteredError

from src.telegram.client import ThreadedTGClient


# ── Константы ──────────────────────────────────────────────────

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"***REMOVED***
FAVORITES_FILE = Path(__file__).resolve().parent.parent / "favorites.json"


# ═══════════════════════════════════════════════════════════════
# ЭКРАН 1: Список чатов
# ═══════════════════════════════════════════════════════════════

class ChatListScreen(Screen):
    """Главный экран: список чатов с поиском."""

    class SearchOpened(Message):
        pass

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("💬 Чаты", id="chat-header")
        yield Label("", id="search-count")
        yield Input(placeholder="🔍 Поиск чатов...", id="search-input")
        yield ListView(id="chat-list")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).display = False
        self.query_one("#search-count", Label).display = False
        self._all_dialogs: list[object***REMOVED*** = [***REMOVED***
        self._visible_dialogs: list[object***REMOVED*** = [***REMOVED***
        self._current_query = ""
        self._favorites: set[int***REMOVED*** = self._load_favorites()

    def _load_favorites(self) -> set[int***REMOVED***:
        try:
            if FAVORITES_FILE.exists():
                data = json.loads(FAVORITES_FILE.read_text())
                return set(data.get("ids", [***REMOVED***))
        except Exception:
            pass
        return set()

    def _save_favorites(self) -> None:
        try:
            FAVORITES_FILE.write_text(json.dumps({"ids": list(self._favorites)***REMOVED***))
        except Exception:
            pass

    def show_dialogs(self, dialogs: list[object***REMOVED***) -> None:
        self._all_dialogs = dialogs
        if self._current_query:
            self.apply_filter(self._current_query)
        else:
            self._visible_dialogs = dialogs
            self._render_list(dialogs)

    def get_dialog(self, idx: int) -> object | None:
        if 0 <= idx < len(self._visible_dialogs):
            return self._visible_dialogs[idx***REMOVED***
        return None

    def _highlight(self, text: str, query: str) -> str:
        if not query:
            return text
        safe = text.replace("[", "\\[").replace("***REMOVED***", "\\***REMOVED***")
        ql = query.lower()
        idx = safe.lower().find(ql)
        if idx < 0:
            return safe
        matched = safe[idx:idx + len(query)***REMOVED***
        return safe[:idx***REMOVED*** + f"[bold yellow***REMOVED***{matched***REMOVED***[/***REMOVED***" + safe[idx + len(query):***REMOVED***

    def _render_list(self, dialogs: list[object***REMOVED***) -> None:
        lst = self.query_one("#chat-list", ListView)
        lst.clear()
        q = self._current_query
        # Избранные сверху
        favs = [d for d in dialogs if d.id in self._favorites***REMOVED***
        rest = [d for d in dialogs if d.id not in self._favorites***REMOVED***
        for d in favs + rest:
            star = "⭐ " if d.id in self._favorites else ""
            unread = f" [bold cyan***REMOVED***{d.unread_count***REMOVED***[/***REMOVED***" if d.unread_count else ""
            name = self._highlight(d.name, q) if q else d.name.replace("[", "\\[").replace("***REMOVED***", "\\***REMOVED***")
            lst.append(ListItem(Label(f"{star***REMOVED***{name***REMOVED***{unread***REMOVED***")))

    def toggle_search(self) -> None:
        si = self.query_one("#search-input", Input)
        sc = self.query_one("#search-count", Label)
        if si.display:
            si.display = False; sc.display = False; si.value = ""
            self._current_query = ""
            self._visible_dialogs = self._all_dialogs
            self._render_list(self._all_dialogs)
            self.query_one("#chat-list", ListView).focus()
        else:
            si.display = True; sc.display = True; si.focus()
            self.post_message(self.SearchOpened())

    def apply_filter(self, query: str) -> None:
        sc = self.query_one("#search-count", Label)
        self._current_query = query.strip()
        if not self._current_query:
            self._visible_dialogs = self._all_dialogs
            self._render_list(self._all_dialogs)
            sc.update(f"🔍 Все: {len(self._all_dialogs)***REMOVED***")
            return
        q = self._current_query.lower()
        filtered = [d for d in self._all_dialogs if q in d.name.lower()***REMOVED***
        self._visible_dialogs = filtered
        self._render_list(filtered)
        sc.update(f"🔍 Найдено: {len(filtered)***REMOVED*** из {len(self._all_dialogs)***REMOVED***")

    def show_error(self, msg: str) -> None:
        lst = self.query_one("#chat-list", ListView)
        lst.clear()
        lst.append(ListItem(Label(f"❌ {msg***REMOVED***")))

    def action_toggle_favorite(self) -> None:
        """Добавить/убрать чат из избранного."""
        lst = self.query_one("#chat-list", ListView)
        idx = lst.index
        if idx is None:
            return
        dialog = self.get_dialog(idx)
        if dialog is None:
            return
        if dialog.id in self._favorites:
            self._favorites.discard(dialog.id)
            self.app.notify(f"❌ Убран из избранного: {dialog.name[:20***REMOVED******REMOVED***", timeout=2)
        else:
            self._favorites.add(dialog.id)
            self.app.notify(f"⭐ Добавлен в избранное: {dialog.name[:20***REMOVED******REMOVED***", timeout=2)
        self._save_favorites()
        self._render_list(self._visible_dialogs)


# ═══════════════════════════════════════════════════════════════
# ЭКРАН 2: Переписка (как в Telegram)
# ═══════════════════════════════════════════════════════════════

class ChatViewScreen(Screen):
    """Экран переписки: сообщения + строка ввода внизу."""

    def __init__(self, dialog, tg_app):
        super().__init__()
        self._dialog = dialog
        self._tg_app = tg_app
        self._saved_subtitle = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            ListView(id="msg-list"),
            id="msg-area",
        )
        with Horizontal(id="input-bar"):
            yield Input(placeholder="Напиши сообщение...", id="msg-input")
        yield Footer()

    def on_mount(self) -> None:
        self._saved_subtitle = self.app.sub_title
        self.app.sub_title = f"💬 {self._dialog.name***REMOVED***"
        self._tg_app.run_worker(self._load_messages())

    async def _load_messages(self) -> None:
        if self._tg_app._tg is None:
            return
        try:
            messages = await self._tg_app._await_tg(
                self._tg_app._tg.get_messages_async(self._dialog.entity, limit=30)
            )
            lst = self.query_one("#msg-list", ListView)
            lst.clear()
            for m in reversed(messages):
                sender = ""
                s = getattr(m, 'sender', None)
                if s is not None:
                    sn = getattr(s, 'first_name', '') or ''
                    if sn:
                        sender = f"[bold green***REMOVED***{sn***REMOVED***[/***REMOVED*** "
                text = m.message or "[italic dim***REMOVED***медиа[/***REMOVED***"
                ts = m.date.strftime("%H:%M") if m.date else ""
                label = Label(f"{sender***REMOVED***[dim***REMOVED***{ts***REMOVED***[/***REMOVED***  {text[:200***REMOVED******REMOVED***")
                lst.append(ListItem(label))
            if messages:
                lst.index = len(lst) - 1
        except Exception as e:
            self.notify(f"❌ {e***REMOVED***", severity="error")

    def action_go_back(self) -> None:
        self.app.sub_title = self._saved_subtitle or self._tg_app.sub_title
        self.dismiss()

    def action_focus_input(self) -> None:
        self.query_one("#msg-input", Input).focus()

    def action_refresh_msgs(self) -> None:
        self._tg_app.run_worker(self._load_messages())

    def action_quit_app(self) -> None:
        self._tg_app.action_quit()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text or self._tg_app._tg is None:
            return
        try:
            await self._tg_app._await_tg(
                self._tg_app._tg.send_message_async(self._dialog.entity, text)
            )
            event.input.value = ""
            self.notify("✅ Отправлено", timeout=1)
            self._tg_app.run_worker(self._load_messages())
        except Exception as e:
            self.notify(f"❌ {e***REMOVED***", severity="error")


# ═══════════════════════════════════════════════════════════════
# ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ═══════════════════════════════════════════════════════════════

class TGApp(App):
    """Главное TUI-приложение с экранной навигацией."""

    CSS = """
    #chat-header {
        background: #1a1a2e;
        color: #e0e0e0;
        padding: 1;
        text-align: center;
        text-style: bold;
    ***REMOVED***
    #chat-list {
        border: solid #333;
        height: 1fr;
    ***REMOVED***
    #search-input {
        border: solid #4fc3f7;
        margin: 0 1;
        background: #1a1a2e;
        color: #e0e0e0;
    ***REMOVED***
    #search-count {
        color: #4fc3f7;
        padding: 0 1;
        text-style: italic;
    ***REMOVED***
    #msg-area {
        height: 1fr;
        border: solid #333;
    ***REMOVED***
    #msg-list {
        height: 1fr;
    ***REMOVED***
    #input-bar {
        height: 3;
        padding: 1;
        background: #1a1a2e;
        border-top: solid #333;
    ***REMOVED***
    #msg-input {
        width: 1fr;
        background: #24283b;
        color: #e0e0e0;
        border: solid #4fc3f7;
    ***REMOVED***
    ListView:focus {
        border: solid #4fc3f7;
    ***REMOVED***
    """

    BINDINGS = [
        Binding("ctrl+s", "toggle_search", "Поиск", show=True),
        Binding("ctrl+e", "toggle_favorite", "⭐ Избр.", show=True),
        Binding("ctrl+r", "refresh", "Обновить", show=True),
        Binding("ctrl+q", "quit", "Выход", show=True),
        Binding("escape", "escape", "", show=False),
        Binding("ctrl+f", "focus_input", "Писать", show=True),
    ***REMOVED***

    def __init__(self):
        super().__init__()
        self._tg: ThreadedTGClient | None = None
        self._tg_connected = False
        self._spinner_idx = 0
        self._spinner_timer: Timer | None = None
        self._refresh_timer: Timer | None = None
        self._search_history: list[str***REMOVED*** = [***REMOVED***
        self._refreshing = False
        self._total_unread = -1

    async def on_mount(self) -> None:
        """Показать главный экран и запустить подключение."""
        await self.push_screen(ChatListScreen())
        self._spinner_timer = self.set_interval(0.12, self._spin)
        self.run_worker(self._connect_bg())

    def _spin(self) -> None:
        self._spinner_idx = (self._spinner_idx + 1) % len(SPINNER)
        self.sub_title = f"{SPINNER[self._spinner_idx***REMOVED******REMOVED*** Подключение..."

    def _stop_spinner(self) -> None:
        if self._spinner_timer is not None:
            self._spinner_timer.stop()
            self._spinner_timer = None

    # ── TG bridge ──────────────────────────────────────────

    async def _await_tg(self, future):
        while not future.done():
            await asyncio.sleep(0.05)
        return future.result()

    async def _connect_bg(self) -> None:
        try:
            self._tg = ThreadedTGClient()
            authorized = await self._await_tg(self._tg.connect_async())
            if not authorized:
                self._stop_spinner()
                self.sub_title = "⚠️ Нужна авторизация"
                return
            me = await self._await_tg(self._tg.get_me_async())
            name = f"{me.first_name***REMOVED*** {me.last_name or ''***REMOVED***" if me else "???"
            self._stop_spinner()
            self.sub_title = f"👤 {name***REMOVED***"
            self._tg_connected = True
            self._refresh_timer = self.set_interval(10, self._auto_refresh)
            await self._load_chats()
        except AuthKeyUnregisteredError:
            self._stop_spinner()
            self.sub_title = "🔑 Ключ протух"
        except Exception as e:
            self._stop_spinner()
            self.sub_title = f"❌ {e***REMOVED***"

    def _auto_refresh(self) -> None:
        if self._tg_connected and not self._refreshing:
            self._refreshing = True
            self.run_worker(self._load_chats())

    async def _load_chats(self) -> None:
        if self._tg is None:
            self._refreshing = False; return
        screen = self.screen
        if not isinstance(screen, ChatListScreen):
            self._refreshing = False; return
        try:
            dialogs = await self._await_tg(self._tg.get_dialogs_async(limit=20))
            screen.show_dialogs(dialogs)
            self._check_unread(dialogs)
        except Exception as e:
            screen.show_error(str(e))
        finally:
            self._refreshing = False

    def _check_unread(self, dialogs: list[object***REMOVED***) -> None:
        if not self._tg_connected:
            return
        total = sum(d.unread_count for d in dialogs)
        if total != self._total_unread:
            prev = self._total_unread
            self._total_unread = total
            if prev >= 0 and total > prev:
                sys.stderr.write("\a"); sys.stderr.flush()
            current = self.sub_title
            if " [" in current:
                current = current.split(" [")[0***REMOVED***
            self.sub_title = f"{current***REMOVED*** [{total***REMOVED*** нов***REMOVED***" if total > 0 else current

    # ── Навигация: Enter на чате → полный экран ────────────

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Enter — открыть полный экран переписки."""
        if event.list_view.id != "chat-list" or not self._tg_connected:
            return
        idx = event.list_view.index
        screen = self.screen
        if not isinstance(screen, ChatListScreen):
            return
        dialog = screen.get_dialog(idx)
        if dialog is None:
            return
        self.run_worker(self.push_screen(ChatViewScreen(dialog, self)))

    # ── Действия ───────────────────────────────────────────

    def action_toggle_search(self) -> None:
        screen = self.screen
        if isinstance(screen, ChatListScreen):
            screen.toggle_search()

    def action_toggle_favorite(self) -> None:
        screen = self.screen
        if isinstance(screen, ChatListScreen):
            screen.action_toggle_favorite()

    def action_refresh(self) -> None:
        screen = self.screen
        if isinstance(screen, ChatListScreen):
            self.run_worker(self._load_chats())
        elif isinstance(screen, ChatViewScreen):
            screen.action_refresh_msgs()

    def action_escape(self) -> None:
        screen = self.screen
        if isinstance(screen, ChatListScreen):
            si = screen.query_one("#search-input", Input)
            if si.display:
                screen.toggle_search()
        elif isinstance(screen, ChatViewScreen):
            screen.action_go_back()

    def action_focus_input(self) -> None:
        screen = self.screen
        if isinstance(screen, ChatViewScreen):
            screen.action_focus_input()

    def action_quit(self) -> None:
        self._stop_spinner()
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
        if self._tg is not None:
            self._tg.shutdown()
        self.exit()

    # ── Поиск: обработчики ─────────────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            screen = self.screen
            if isinstance(screen, ChatListScreen):
                screen.apply_filter(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input" and event.value.strip():
            q = event.value.strip()
            if q not in self._search_history:
                self._search_history.insert(0, q)
                self._search_history = self._search_history[:5***REMOVED***
            screen = self.screen
            if isinstance(screen, ChatListScreen):
                sc = screen.query_one("#search-count", Label)
                sc.update(f"🔍 Сохранено! История: {', '.join(self._search_history[:3***REMOVED***)***REMOVED***")

    def on_chat_list_search_opened(self, event: ChatListScreen.SearchOpened) -> None:
        if self._search_history:
            screen = self.screen
            if isinstance(screen, ChatListScreen):
                sc = screen.query_one("#search-count", Label)
                sc.update(f"🔍 История: {', '.join(self._search_history)***REMOVED***")


if __name__ == "__main__":
    app = TGApp()
    app.run()
