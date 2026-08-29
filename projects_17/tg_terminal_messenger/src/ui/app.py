#!/usr/bin/env python3
"""
tg-terminal-toolkit — Textual TUI для Telegram.
Экранный подход: список чатов → экран переписки.

Горячие клавиши:
    Enter     — открыть чат / скачать и открыть медиа из сообщения
    Esc       — назад / закрыть поиск / отменить отправку файла
    Tab       — переключить фокус: список сообщений → кнопки 📎 Файл → 🎤 Голос → 🎬 Видео → 🎞 GIF → строка ввода
    j / k     — навигация по списку (если нет стрелок)
    Ctrl+F    — поиск по чатам / поиск по сообщениям (в чате)
    Ctrl+E    — добавить/убрать чат из избранного
    Ctrl+R    — обновить диалоги
    Ctrl+O / a — отправить файл/медиа (📎) — без Ctrl работает клавиша 'a'
    кнопка 📎 Файл — то же, что Ctrl+O / a (рядом со строкой ввода)
    кнопка 🎤 Голос — запись голосового (termux-microphone-recorder): нажми ещё раз — стоп;
        длительность записи видна на кнопке ⏹ (живой счётчик мм:сс);
        после стопа — выбор: s/Enter — отправить · p — прослушать (termux-media-player) · d/Esc — удалить;
        без рекордера — выбор аудиофайла (системный пикер / браузер), отправка как голосовое (Esc — отмена записи)
    кнопка 🎬 Видео — есть termux-camera-photo: открывает камеру (📸 фото, превью + подтверждение);
        без termux-api — выбор видеофайла (.mp4/.mkv/.webm/...) (системный пикер / браузер в режиме видео);
        видео-запись termux-api не умеет (только фото через termux-camera-photo)
    кнопка 🎞 GIF — отправить анимированный .gif/.webp из галереи (системный пикер / браузер)
    перед отправкой — превью первого кадра (chafa): y/Enter — отправить, n/Esc — отмена
    Ctrl+G    — переключить режим: лайт (чисто переписка) / адванс (все функции)
    v         — открыть уже скачанное медиа из папки (без повторного скачивания)
    o         — в превью видео: открыть оригинал в системном плеере
    + / −     — в превью: масштабирование (перезапуск chafa); 0 — сброс
    Ctrl+T    — фокус на строку ввода (в режиме чата)
    Ctrl+X    — выход
    Ctrl+Q    — выход (стандарт Textual)

Внимание: Ctrl+I НЕ используется — в терминале Ctrl+I
неотличим от Tab (байт 0x09), поэтому такое сочетание
никогда не срабатывает как биндинг. Вместо него — Ctrl+T.
"""

import asyncio
import json
import os
***REMOVED***
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
***REMOVED***

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Container
from textual.message import Message
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Header, Footer, ListView, ListItem, Input, Label, Static, ProgressBar, Button
from textual.binding import Binding

from rich.text import Text

from telethon.errors import AuthKeyUnregisteredError
from telethon.tl.types import DocumentAttributeAnimated

from src.cache import MessageCache
from src.telegram.client import ThreadedTGClient, _is_animated


# ── Константы ──────────────────────────────────────────────────

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"***REMOVED***
FAVORITES_FILE = Path(__file__).resolve().parent.parent / "favorites.json"
CACHE_DB = PROJECT_ROOT / "tg_cache.db"
MANUAL_PATH = "::manual::"   # sentinel: выбрать «ввести путь вручную» в браузере
SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"

# ── Настройки (settings.json) ───────────────────────────────

_DEFAULT_SETTINGS = {
    "history_limit": 30,   # сколько сообщений показывать при открытии чата
    "mode": "advance",     # light — чисто переписка; advance — все функции
    "cache_cap": 200,      # максимум сообщений на чат в кэше (автоподгрузка останавливается)
    "cache_days": 30,      # срок хранения кэша: старше N дней удаляются при старте
***REMOVED***


def _load_settings() -> dict:
    """Прочитать settings.json (с дефолтами на неизвестные ключи).

    Типы значений тоже валидируются: битое значение от ручного редактирования
    файла (например "history_limit": "abc") не должно ронять загрузку чата.
    """
    try:
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                out = dict(_DEFAULT_SETTINGS)
                for k in _DEFAULT_SETTINGS:
                    if k in data:
                        out[k***REMOVED*** = data[k***REMOVED***
                for num_key in ("history_limit", "cache_cap", "cache_days"):
                    try:
                        hi = 1000 if num_key != "cache_days" else 3650
                        lo = 0 if num_key == "cache_days" else 1   # 0 = очистка выключена
                        out[num_key***REMOVED*** = max(lo, min(int(out[num_key***REMOVED***), hi))
                    except Exception:
                        out[num_key***REMOVED*** = _DEFAULT_SETTINGS[num_key***REMOVED***
                if out["mode"***REMOVED*** not in ("light", "advance"):
                    out["mode"***REMOVED*** = _DEFAULT_SETTINGS["mode"***REMOVED***
                return out
    except Exception:
        pass
    return dict(_DEFAULT_SETTINGS)


def _save_settings(settings: dict) -> None:
    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


_SETTINGS = _load_settings()


def _get_setting(key: str):
    """Значение настройки (без падения на отсутствующий ключ)."""
    return _SETTINGS.get(key, _DEFAULT_SETTINGS[key***REMOVED***)


def _set_setting(key: str, value) -> None:
    """Записать настройку и сохранить в settings.json."""
    _SETTINGS[key***REMOVED*** = value
    _save_settings(_SETTINGS)


def _is_light_mode() -> bool:
    """Режим «лайт» — чисто переписка (без поиска/GIF/файлов)."""
    return _get_setting("mode") == "light"


# ── Медиа: папка скачивания, имена файлов, подсказки ───────────

_MEDIA_DIR: Path | None = None


def media_dir() -> Path:
    """Папка для скачанных медиа (видна в Files/Галерее на Android)."""
    global _MEDIA_DIR
    if _MEDIA_DIR is not None:
        return _MEDIA_DIR
    candidates = [
        Path.home() / "storage" / "downloads" / "tg_terminal",
        Path.home() / ".tg_terminal_media",
        Path(__file__).resolve().parent.parent.parent / "media",
    ***REMOVED***
    for d in candidates:
        try:
            d.mkdir(parents=True, exist_ok=True)
            _MEDIA_DIR = d
            return d
        except Exception:
            continue
    _MEDIA_DIR = candidates[-1***REMOVED***
    return _MEDIA_DIR


def _sanitize(name: str) -> str:
    return re.sub(r"[^\w.\-***REMOVED***+", "_", name).strip("._")[:120***REMOVED*** or "file"


def _ext_for_mime(mime: str) -> str:
    table = {
        "image/jpeg": "jpg", "image/png": "png", "image/gif": "gif",
        "image/webp": "webp", "video/mp4": "mp4", "audio/mpeg": "mp3",
        "audio/mp4": "m4a", "audio/ogg": "ogg", "audio/opus": "opus",
    ***REMOVED***
    return table.get(mime, "bin")


def media_filename(m) -> str:
    """Понятное имя файла для медиа из сообщения."""
    doc = getattr(m, "document", None)
    if doc:
        for a in getattr(doc, "attributes", [***REMOVED***):
            fn = getattr(a, "file_name", None)
            if fn:
                return _sanitize(fn)
        return f"media_{m.id***REMOVED***.{_ext_for_mime(getattr(doc, 'mime_type', '') or '')***REMOVED***"
    if getattr(m, "photo", None):
        return f"photo_{m.id***REMOVED***.jpg"
    if getattr(m, "video", None):
        return f"video_{m.id***REMOVED***.mp4"
    if getattr(m, "audio", None):
        return f"audio_{m.id***REMOVED***.{_ext_for_mime(getattr(m.audio, 'mime_type', '') or '')***REMOVED***"
    return f"media_{m.id***REMOVED***.bin"


_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"***REMOVED***
_ANIM_EXTS = {".gif", ".webp"***REMOVED***
_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".3gp", ".m4v", ".ts", ".mpg", ".mpeg"***REMOVED***
_AUDIO_EXTS = {".mp3", ".ogg", ".opus", ".m4a", ".m4b", ".m4p", ".wav", ".aac", ".flac", ".amr", ".3gp", ".mka", ".oga", ".mid"***REMOVED***
_CSI_FINAL = set("@ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz[\\***REMOVED***^_`{|***REMOVED***~")


def _is_image_path(path) -> bool:
    """Похоже ли это на картинку (для превью через chafa)."""
    return Path(path).suffix.lower() in _IMAGE_EXTS


def _is_video_path(path) -> bool:
    """Похоже ли это на видео (для превью первого кадра через ffmpeg)."""
    return Path(path).suffix.lower() in _VIDEO_EXTS


def _is_audio_path(path) -> bool:
    """Похоже ли это на аудио (для кнопки 🎤 Голос): расширение или магия.

    Магия важна для SAF-пикера: termux-storage-get сохраняет копию как .bin,
    а запись termux-microphone-recorder (m4a) может приехать с любым именем.
    """
    if Path(path).suffix.lower() in _AUDIO_EXTS:
        return True
    try:
        with open(path, "rb") as fh:
            head = fh.read(16)
    except Exception:
        return False
    if head.startswith(b"ID3"):                                  # mp3 с тегами
        return True
    if head.startswith(b"OggS"):                                 # ogg / opus
        return True
    if head.startswith(b"RIFF") and len(head) >= 12 and head[8:12***REMOVED*** == b"WAVE":
        return True                                              # wav
    if head.startswith(b"fLaC"):
        return True                                              # flac
    if len(head) >= 12 and head[4:8***REMOVED*** == b"ftyp":
        return head[8:12***REMOVED*** in (b"M4A ", b"M4B ", b"M4P ")        # m4a / m4b / m4p
    return False


def _file_media_kind(path) -> str:
    """Тип файла по магии (image/video/other) — не по расширению.

    Причина: если JPEG-картинка сохранилась с расширением .bin (документ без
    mime_type в Telegram), Android-просмотрщик показывает «повреждено» — хотя
    содержимое валидно. Для превью важнее содержимое, чем имя файла.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(16)
    except Exception:
        return "other"
    if not head:
        return "other"
    if head.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF87a", b"GIF89a", b"BM")):
        return "image"
    if head.startswith(b"RIFF") and len(head) >= 12 and head[8:12***REMOVED*** == b"WEBP":
        return "image"
    if len(head) >= 12 and head[4:8***REMOVED*** == b"ftyp":        # mp4 / m4v / mov
        return "video"
    if head.startswith((b"\x1aE\xdf\xa3", b"OggS")):
        return "video"                                   # webm/mkv (EBML), ogg
    return "other"


def _magic_ext(path) -> str | None:
    """Расширение по магии файла (.jpg/.png/.gif/.mp4/...). None — не узнали.

    Нужно для SAF-пикера (termux-storage-get): он копирует выбранный файл в
    заранее заданное имя, теряя оригинальное расширение. По содержимому
    определяем настоящее расширение, чтобы фото/видео уходили как фото/видео.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(16)
    except Exception:
        return None
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if head.startswith(b"RIFF") and len(head) >= 12 and head[8:12***REMOVED*** == b"WEBP":
        return ".webp"
    if head.startswith(b"BM"):
        return ".bmp"
    if len(head) >= 12 and head[4:8***REMOVED*** == b"ftyp":
        # m4a/m4b/m4p — аудио-контейнеры MP4 (бренд в bytes 8..12)
        if head[8:12***REMOVED*** in (b"M4A ", b"M4B ", b"M4P "):
            return ".m4a"
        return ".mp4"
    if head.startswith(b"\x1aE\xdf\xa3"):
        return ".mkv"
    if head.startswith(b"OggS"):
        return ".ogg"
    if head.startswith(b"%PDF"):
        return ".pdf"
    if head.startswith(b"PK\x03\x04"):
        return ".zip"
    return None


def _picker_proper_ext(path: str) -> str:
    """Переименовать SAF-копию (.bin) по магии содержимого. Вернуть новый путь."""
    p = Path(path)
    ext = _magic_ext(p)
    if not ext or p.suffix == ext:
        return str(p)
    new = p.with_suffix(ext)
    try:
        p.rename(new)
        return str(new)
    except Exception:
        return str(p)


def _is_animated_media(path) -> bool:
    """Анимированный GIF/WebP ли файл: расширение/магия + реально анимированный.

    Только .gif/.webp: send_file добавляет DocumentAttributeAnimated для этих
    типов (Telegram транскодирует анимированный webp в гифку). Статичный
    .gif/.webp отклоняется: Telegram не принимает DocumentAttributeAnimated
    для неанимированных файлов. PIL-проверка анимации — общий хелпер
    _is_animated из src.telegram.client (тот же, что использует send_file).
    """
    p = Path(path)
    is_anim = p.suffix.lower() in (".gif", ".webp") or _magic_ext(p) in (".gif", ".webp")
    if not is_anim:
        return False
    return _is_animated(p)


def _is_animatable(path) -> bool:
    """GIF/WebP могут быть анимированными (для chafa --animate on)."""
    return Path(path).suffix.lower() in _ANIM_EXTS


def _strip_csi_non_sgr(s: str) -> str:
    """Удалить CSI-последовательности, кроме SGR-цветов (заканчиваются на 'm')."""
    out: list[str***REMOVED*** = [***REMOVED***
    i = 0
    while True:
        j = s.find("\x1b[", i)
        if j < 0:
            out.append(s[i:***REMOVED***)
            break
        out.append(s[i:j***REMOVED***)
        k = j + 2
        while k < len(s) and s[k***REMOVED*** not in _CSI_FINAL:
            k += 1
        if k < len(s):
            if s[k***REMOVED*** == "m":
                out.append(s[j:k + 1***REMOVED***)   # SGR — оставить (цвета)
            i = k + 1
        else:
            i = len(s)
    return "".join(out)


def _gif_durations(path) -> list[float***REMOVED***:
    """Длительности кадров в мс (PIL). Пусто — не удалось прочитать."""
    try:
        from PIL import Image, ImageSequence
        img = Image.open(path)
        return [float(f.info.get("duration") or 100) for f in ImageSequence.Iterator(img)***REMOVED***
    except Exception:
        return [***REMOVED***


def _frame_interval(durations: list[float***REMOVED***) -> float:
    """Средняя длительность кадра в секундах (0.05..0.5; дефолт 0.1)."""
    if not durations:
        return 0.1
    avg = sum(durations) / len(durations) / 1000.0
    return max(0.05, min(0.5, avg))


def _gif_first_frame(path) -> Path | None:
    """Первый кадр GIF/WebP в JPEG (для превью перед отправкой). None — не вышло.

    Временный файл в tempdir — удаляется после рендера превью.
    """
    try:
        from PIL import Image
        img = Image.open(path)
        img.seek(0)
        frame = img.convert("RGB")
        dest = Path(tempfile.gettempdir()) / f"gif_preview_{time.time_ns()***REMOVED***.jpg"
        frame.save(dest, "JPEG", quality=85)
        return dest
    except Exception:
        return None


def media_hint(m) -> str | None:
    """Эмодзи-метка типа медиа (для списка сообщений)."""
    try:
        if getattr(m, "photo", None):
            return "📷 Фото"
        if getattr(m, "video", None):
            return "🟡 Видеосообщение" if getattr(m.video, "round", False) else "🎬 Видео"
        if getattr(m, "voice", None):
            return "🎤 Голосовое"
        if getattr(m, "audio", None):
            return "🎵 Музыка"
        if getattr(m, "sticker", None):
            return "🖼 Стикер"
        doc = getattr(m, "document", None)
        if doc:
            if any(
                isinstance(a, DocumentAttributeAnimated)
                for a in getattr(doc, "attributes", [***REMOVED***)
            ):
                return "🎞 GIF"
            mime = getattr(doc, "mime_type", "") or ""
            if mime.startswith("video"):
                return "🎬 Видео"
            if mime.startswith("audio"):
                return "🎵 Аудио"
            if mime.startswith("image"):
                return "🖼 Картинка"
            size = getattr(doc, "size", 0) or 0
            return f"📄 Файл ({size // 1024***REMOVED*** КБ)" if size else "📄 Файл"
        if getattr(m, "contact", None):
            return "👤 Контакт"
        if getattr(m, "geo", None):
            return "📍 Гео"
        if getattr(m, "poll", None):
            return "📊 Опрос"
    except Exception:
        pass
    return None


class NavListView(ListView):
    """ListView с навигацией j/k — запасной вариант, когда нет стрелок."""

    BINDINGS = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ***REMOVED***


def _throttled_progress(state: dict, done: int, total: int) -> bool:
    """Троттлинг progress-обновлений. True — обновление нужно пробросить.

    - известный total: только когда меняется целый процент
      (финальное done == total пробрасывается всегда);
    - неизвестный/нулевой total: не чаще раза в 100 мс (time.monotonic).
    """
    now = time.monotonic()
    if total and total > 0:
        pct = int(done * 100 / total)
        if pct == state.get("last_pct") and done != total:
            return False
        state["last_pct"***REMOVED*** = pct
    elif now - state.get("last_t", 0.0) < 0.1:
        return False
    state["last_t"***REMOVED*** = now
    return True


@dataclass
class CachedMsg:
    """Офлайн-запись сообщения из кэша (рендер без Telegram-объекта)."""

    msg_id: int
    sender: str
    ts: float
    text: str
    media: str | None


def _highlight_text(text: str, query: str) -> str:
    """Подсветить вхождения query в тексте (для списков)."""
    if not query:
        return text
    safe = text.replace("[", "\\[").replace("***REMOVED***", "\\***REMOVED***")
    ql = query.lower()
    idx = safe.lower().find(ql)
    if idx < 0:
        return safe
    matched = safe[idx:idx + len(query)***REMOVED***
    return safe[:idx***REMOVED*** + f"[bold yellow***REMOVED***{matched***REMOVED***[/***REMOVED***" + safe[idx + len(query):***REMOVED***


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
        yield NavListView(id="chat-list")
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
        return _highlight_text(text, query)

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

    # Стрелки вверх/вниз работают и при фокусе на строке ввода
    # (однострочный Input их не использует, так что конфликта нет),
    # а когда фокус на списке — их обрабатывает сам ListView.
    BINDINGS = [
        Binding("up", "msg_up", show=False),
        Binding("down", "msg_down", show=False),
        Binding("v", "view_cached", "👁 Открыть", show=True),
    ***REMOVED***

    def __init__(self, dialog, tg_app):
        super().__init__()
        self._dialog = dialog
        self._tg_app = tg_app
        self._saved_subtitle = ""
        self._messages: list = [***REMOVED***
        self._attach_mode = False
        self._gif_attach_mode = False   # ручной путь в режиме GIF (валидировать при отправке)
        self._visible_idx: list[int***REMOVED*** | None = None   # поиск: индексы показанных сообщений
        self._search_query = ""
        self._loading_older = False
        self._can_load_older = True
        self._older_timer: Timer | None = None
        self._cap_notified = False   # одноразовый тост о достижении cache_cap
        self._pending_gif: str | None = None   # путь гифки, ожидающей подтверждения
        self._recording = False      # идёт ли запись голосового (кнопка 🎤 — toggle)
        self._rec_proc: subprocess.Popen | None = None
        self._rec_path: str | None = None
        self._rec_started: float | None = None   # старт записи (time.monotonic) — тикер на кнопке ⏹
        self._rec_timer: Timer | None = None     # тикер длительности записи (мм:сс на кнопке)
        self._voice_attach_mode = False   # ручной путь в режиме голосового (валидировать при отправке)
        self._video_attach_mode = False   # ручной путь в режиме видео (валидировать при отправке)
        self._history_end = False    # дошли до начала истории (счётчик в заголовке)
        self._capturing = False      # идёт ли съёмка с камеры (кнопка 🎬)
        self._capture_proc: subprocess.Popen | None = None
        self._capture_path: str | None = None
        self._pending_photo: str | None = None   # фото с камеры, ожидающее подтверждения
        self._pending_voice: str | None = None   # запись, ожидающая выбора (отправить/слушать/удалить)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="🔍 Поиск по сообщениям...", id="chat-search")
        yield Label("", id="chat-search-count")
        yield Container(
            NavListView(id="msg-list"),
            id="msg-area",
        )
        yield ProgressBar(id="transfer-progress", show_percentage=True)
        with Horizontal(id="input-bar"):
            yield Button("📎 Файл", id="btn-attach")
            yield Button("🎤 Голос", id="btn-voice")
            yield Button("🎬 Видео", id="btn-video")
            yield Button("🎞 GIF", id="btn-gif")
            yield Input(placeholder="Напиши сообщение...", id="msg-input")
        yield Footer()

    def on_mount(self) -> None:
        self._saved_subtitle = self.app.sub_title
        self._update_msg_counter()
        self._apply_mode_ui()
        self.query_one("#msg-input", Input).focus()
        self._older_timer = self.set_interval(0.4, self._check_scroll_top)
        self._tg_app.run_worker(self._load_messages())

    def on_unmount(self) -> None:
        if self._older_timer is not None:
            self._older_timer.stop()
            self._older_timer = None
        # Если уходим из чата во время записи/съёмки — не оставляем зомби-процесс
        if self._recording:
            self.cancel_recording()
        if self._capturing:
            self.cancel_capture()

    def _apply_mode_ui(self) -> None:
        """Скрыть/показать элементы по режиму (лайт/адванс) — работает на лету.

        Лайт: чисто переписка — прячем поиск и кнопки 📎 Файл / 🎤 Голос / 🎬 Видео / 🎞 GIF.
        Поиск в адванс-режиме остаётся скрытым до Ctrl+F (как и раньше)."""
        light = _is_light_mode()
        for btn_id in ("#btn-gif", "#btn-attach", "#btn-voice", "#btn-video"):
            try:
                self.query_one(btn_id, Button).display = not light
            except Exception:
                pass
        if light:
            try:
                self.query_one("#chat-search", Input).display = False
                self.query_one("#chat-search-count", Label).display = False
            except Exception:
                pass

    @staticmethod
    def _compose_body(text: str, hint: str | None) -> str:
        """Текст строки сообщения + эмодзи-метка медиа."""
        body = text.strip()
        if hint:
            body = f"{hint***REMOVED***  {body***REMOVED***" if body else hint
        return body[:200***REMOVED*** or "[italic dim***REMOVED***сообщение[/***REMOVED***"

    @staticmethod
    def _msg_label(sender: str, ts: str, body: str) -> Label:
        s = f"[bold green***REMOVED***{sender***REMOVED***[/***REMOVED*** " if sender else ""
        return Label(f"{s***REMOVED***[dim***REMOVED***{ts***REMOVED***[/***REMOVED***  {body***REMOVED***")

    # ── Прогресс-бар передачи файлов ─────────────────────────

    def _progress_cb(self):
        """progress_callback для Telethon. Вызывается из TG-потока:
        троттлинг + переброс обновления в event loop Textual.
        Приложение захватываем один раз здесь (на event loop), чтобы не
        дёргать Widget.app из чужого потока."""
        app = self.app
        state: dict = {***REMOVED***

        def cb(done: int, total: int) -> None:
            try:
                if _throttled_progress(state, done, total):
                    app.call_from_thread(self._set_progress, done, total)
            except Exception:
                pass

        return cb

    def _set_progress(self, done: int, total: int) -> None:
        """Обновить прогресс-бар (вызывается в event loop Textual)."""
        try:
            pb = self.query_one("#transfer-progress", ProgressBar)
            pb.display = True
            if total and total > 0:
                pb.update(total=total, progress=min(done, total))
            else:
                pb.update(total=100, progress=0)
        except Exception:
            pass

    def _hide_progress(self) -> None:
        try:
            self.query_one("#transfer-progress", ProgressBar).display = False
        except Exception:
            pass

    @staticmethod
    def _sender_name(m) -> str:
        s = getattr(m, "sender", None)
        if s is not None:
            sn = getattr(s, "first_name", "") or ""
            if sn:
                return sn
        return ""

    def _row_of(self, m):
        """(sender, ts_str, text, hint) — для Message или CachedMsg."""
        if isinstance(m, CachedMsg):
            ts = datetime.fromtimestamp(m.ts).strftime("%H:%M") if m.ts else ""
            return m.sender, ts, m.text, m.media
        ts = m.date.strftime("%H:%M") if m.date else ""
        return self._sender_name(m), ts, m.message or "", media_hint(m)

    @staticmethod
    def _ts_of(m) -> float:
        if isinstance(m, CachedMsg):
            return m.ts
        return m.date.timestamp() if m.date else 0

    @staticmethod
    def _rows_to_cached(rows: list[dict***REMOVED***) -> list[CachedMsg***REMOVED***:
        """Превратить строки кэша в CachedMsg-записи."""
        return [
            CachedMsg(msg_id=r["msg_id"***REMOVED***, sender=r["sender"***REMOVED***, ts=r["ts"***REMOVED***,
                      text=r["text"***REMOVED***, media=r["media"***REMOVED***)
            for r in rows
        ***REMOVED***

    def _query_match(self, m, q: str) -> bool:
        q = q.lower()
        if isinstance(m, CachedMsg):
            return q in m.text.lower()
        return q in (m.message or "").lower()

    def _render_messages(self, preserve_index: int | None = None) -> None:
        """Перерисовать список сообщений (с учётом поискового фильтра)."""
        lst = self.query_one("#msg-list", ListView)
        lst.clear()
        order = (
            list(range(len(self._messages)))
            if self._visible_idx is None
            else self._visible_idx
        )
        for mi in order:
            m = self._messages[mi***REMOVED***
            sender, ts, text, hint = self._row_of(m)
            body = self._compose_body(text, hint)
            if self._search_query:
                body = _highlight_text(body, self._search_query)
            lst.append(ListItem(self._msg_label(sender, ts, body)))
        if not order:
            return
        if preserve_index is None:
            lst.index = len(order) - 1
        else:
            lst.index = max(0, min(preserve_index, len(order) - 1))

    def _update_msg_counter(self) -> None:
        """Заголовок чата: «💬 Имя — N/cap сообщений» / «N/∞» при лимите.

        Показывает, сколько сообщений загружено в память. Пока не достигнут
        cache_cap — «N/cap»; на лимите — «N/∞» (старее — только скроллом вверх);
        когда история закончилась (_history_end) — просто «N сообщений».
        """
        n = len(self._messages)
        try:
            if self._history_end:
                label = f"{n***REMOVED*** сообщений"
            else:
                cap = _get_setting("cache_cap")
                label = f"{n***REMOVED***/∞" if n >= cap else f"{n***REMOVED***/{cap***REMOVED***"
            self.app.sub_title = f"💬 {self._dialog.name***REMOVED*** — {label***REMOVED***"
        except Exception:
            try:
                self.app.sub_title = f"💬 {self._dialog.name***REMOVED***"
            except Exception:
                pass

    async def _load_messages(self) -> None:
        """Показать историю: сначала кэш (мгновенно), затем фоновая сеть.

        Раньше каждый вход в чат ждал сеть (30 захардкожено), а кэш включался
        только при падении сети — отсюда «грузит всю историю заново». Теперь:
        кэш показывается сразу, сеть обновляет его в фоне. Количество —
        из settings.json (history_limit)."""
        cache = self._tg_app._cache
        limit = _get_setting("history_limit")
        cache_shown = False
        # Свежая загрузка (старт/обновление) — сбрасываем «дошли до начала истории»
        self._history_end = False
        # Кэш показываем СРАЗУ и БЕЗ тоста «офлайн» (notify=False): это не офлайн,
        # а быстрый старт; свежие сообщения подтянет фоновая сеть ниже.
        if cache is not None:
            try:
                if await self._load_messages_from_cache(cache, limit=limit, notify=False):
                    cache_shown = True
            except Exception:
                # Битый кэш/БД — не блокируем сетевую загрузку
                cache_shown = False
        # Пока сеть в полёте — скролл вверх не должен подгружать старые и
        # конфликтовать с перезаписью (гонка). Разрешим после завершения.
        self._can_load_older = False
        if self._dialog.entity is not None and self._tg_app._tg is not None:
            try:
                messages = await self._tg_app._await_tg(
                    self._tg_app._tg.get_messages_async(self._dialog.entity, limit=limit)
                )
                self._messages = list(reversed(messages))
                self._can_load_older = True
                self._visible_idx = None
                self._render_messages()
                self._update_msg_counter()
                if cache is not None and messages:
                    rows = [
                        (m.id, self._sender_name(m), self._ts_of(m), m.message or "", media_hint(m))
                        for m in messages
                    ***REMOVED***
                    await cache.save_messages(
                        self._dialog.id, rows, cap=_get_setting("cache_cap")
                    )
                return
            except Exception as e:
                # Сеть недоступна — кэш уже показан (если был), иначе ошибка
                if cache_shown:
                    self._can_load_older = True
                    self.notify("🌐 Сеть недоступна — показан кэш", timeout=3)
                else:
                    self.notify(f"❌ {e***REMOVED***", severity="error")
                return
        if cache_shown:
            self._can_load_older = True
            return
        self.notify("🕓 Нет истории в кэше", severity="warning")

    async def _load_messages_from_cache(self, cache, limit: int = 30, notify: bool = True) -> bool:
        """Показать историю из кэша. Возвращает False, если кэша нет."""
        rows = await cache.get_messages(self._dialog.id, limit=limit)
        if not rows:
            return False
        self._messages = self._rows_to_cached(rows)
        self._can_load_older = True
        self._visible_idx = None
        self._render_messages()
        self._update_msg_counter()
        if notify:
            self.notify("🕓 Офлайн-история из кэша", timeout=3)
        return True

    # ── Подгрузка более старой истории скроллом вверх ────────

    def _check_scroll_top(self, force: bool = False) -> None:
        """Таймер: на самом верху списка → подгружаем более старые сообщения.

        Авто-подгрузка (таймер) идёт максимум до cache_cap (по умолчанию 200),
        чтобы чат не тащил за собой всю историю без спроса — раньше каскад
        по 30 сообщений каждые 0.4 с вытягивал весь кэш/всю историю Telegram.
        Дальше лимита — только по явному скроллу вверх (force=True)."""
        if self._visible_idx is not None:      # при активном поиске не подгружаем
            return
        if self._loading_older or not self._can_load_older:
            return
        if self.app.screen is not self:        # экран не на переднем плане
            return
        lst = self.query_one("#msg-list", ListView)
        if lst.scroll_offset.y > 0:
            return
        cap = _get_setting("cache_cap")
        if not force and len(self._messages) >= cap:
            # Лимит кэша достигнут — не тащим историю дальше автоматически
            if not self._cap_notified:
                self._cap_notified = True
                self.notify(
                    f"⏹ Кэш: {cap***REMOVED*** сообщений — старее подгружаются скроллом вверх",
                    timeout=3,
                )
            return
        self._loading_older = True
        self._tg_app.run_worker(self._load_older_messages())

    async def _load_older_messages(self) -> None:
        try:
            if not self._messages:
                self._can_load_older = False
                return
            cache = self._tg_app._cache
            oldest = self._messages[0***REMOVED***
            limit = _get_setting("history_limit")
            # Не превышаем cache_cap: грузим не больше, чем не хватает до лимита
            remaining = _get_setting("cache_cap") - len(self._messages)
            if remaining > 0:
                limit = max(1, min(limit, remaining))
            old_index = self.query_one("#msg-list", ListView).index or 0
            # Офлайн-записи или нет сети/entity → только кэш
            if isinstance(oldest, CachedMsg) or self._dialog.entity is None or self._tg_app._tg is None:
                if cache is not None:
                    rows = await cache.get_messages_before(
                        self._dialog.id, before_ts=self._ts_of(oldest), limit=limit
                    )
                    if rows:
                        self._prepend_rows(self._rows_to_cached(rows), old_index)
                        return
                self._can_load_older = False
                self._history_end = True
                self._update_msg_counter()
                return
            try:
                older = await self._tg_app._await_tg(
                    self._tg_app._tg.get_messages_async(
                        self._dialog.entity, limit=limit, offset_id=oldest.id
                    )
                )
            except Exception:
                older = [***REMOVED***
            if not older:
                # История кончилась ИЛИ сеть отвалилась — сначала пробуем кэш,
                # и только если там пусто, объявляем конец истории.
                if cache is not None:
                    rows = await cache.get_messages_before(
                        self._dialog.id, before_ts=self._ts_of(oldest), limit=limit
                    )
                    if rows:
                        self._prepend_rows(self._rows_to_cached(rows), old_index)
                        return
                self._can_load_older = False
                self._history_end = True
                self._update_msg_counter()
                self.notify("🏁 Дошли до начала истории", timeout=2)
                return
            self._prepend_rows(list(reversed(older)), old_index)
            if cache is not None:
                rows = [
                    (m.id, self._sender_name(m), self._ts_of(m), m.message or "", media_hint(m))
                    for m in older
                ***REMOVED***
                await cache.save_messages(
                    self._dialog.id, rows, cap=_get_setting("cache_cap")
                )
        finally:
            self._loading_older = False

    def _prepend_rows(self, older: list, old_index: int) -> None:
        """Добавить более старые сообщения в начало, сохранив позицию просмотра."""
        self._messages = older + self._messages
        self._render_messages(preserve_index=old_index + len(older))
        self._update_msg_counter()

    # ── Поиск по сообщениям внутри чата ──────────────────────

    def action_toggle_msg_search(self) -> None:
        if _is_light_mode():
            self.notify("ℹ️ Поиск — в адванс-режиме (Ctrl+G)", timeout=3)
            return
        si = self.query_one("#chat-search", Input)
        sc = self.query_one("#chat-search-count", Label)
        if si.display:
            si.display = False; sc.display = False; si.value = ""
            self._search_query = ""
            self._visible_idx = None
            self._render_messages()
            self.query_one("#msg-input", Input).focus()
        else:
            si.display = True; sc.display = True
            si.focus()

    def _apply_msg_search(self, query: str) -> None:
        sc = self.query_one("#chat-search-count", Label)
        self._search_query = query.strip().lower()
        if not self._search_query:
            self._visible_idx = None
            self._render_messages()
            sc.update("")
            return
        hits = [i for i, m in enumerate(self._messages) if self._query_match(m, self._search_query)***REMOVED***
        self._visible_idx = hits
        self._render_messages()
        sc.update(f"🔍 Найдено: {len(hits)***REMOVED***")

    @on(Input.Changed, "#chat-search")
    def _on_chat_search_changed(self, event: Input.Changed) -> None:
        self._apply_msg_search(event.value)

    @on(Input.Submitted, "#chat-search")
    def _on_chat_search_submitted(self, event: Input.Submitted) -> None:
        if self._visible_idx:
            self.query_one("#msg-list", ListView).focus()

    def action_go_back(self) -> None:
        self.app.sub_title = self._saved_subtitle or self._tg_app.sub_title
        self.dismiss()

    def action_focus_input(self) -> None:
        self.query_one("#msg-input", Input).focus()

    def action_msg_up(self) -> None:
        self._move_msg_cursor(-1)

    def action_msg_down(self) -> None:
        self._move_msg_cursor(1)

    def _move_msg_cursor(self, delta: int) -> None:
        """Сдвинуть курсор списка сообщений (и при фокусе на вводе)."""
        lst = self.query_one("#msg-list", ListView)
        total = len(lst.children)
        if total == 0:
            return
        cur = lst.index if lst.index is not None else 0
        lst.index = max(0, min(total - 1, cur + delta))
        # Дошли до самого верха → сразу пробуем подгрузить более старые сообщения
        if lst.index == 0 and lst.scroll_offset.y <= 0:
            # Явный скролл/стрелка вверх — разрешаем подгрузку за пределами cache_cap
            self._check_scroll_top(force=True)

    def action_refresh_msgs(self) -> None:
        self._tg_app.run_worker(self._load_messages())

    def get_message(self, idx: int):
        """Сообщение по индексу списка (учитывает поисковый фильтр)."""
        if idx is None or idx < 0:
            return None
        if self._visible_idx is not None:
            if idx >= len(self._visible_idx):
                return None
            idx = self._visible_idx[idx***REMOVED***
        if 0 <= idx < len(self._messages):
            return self._messages[idx***REMOVED***
        return None

    async def download_and_open(self, m) -> None:
        """Скачать медиа и открыть системным просмотрщиком."""
        if self._tg_app._tg is None:
            return
        hint = media_hint(m) or "медиа"
        self.notify(f"⬇️ Скачиваю {hint***REMOVED***...", timeout=2)
        try:
            dest = media_dir() / media_filename(m)
            path = await self._tg_app._await_tg(
                self._tg_app._tg.download_media_async(
                    m, str(dest), progress_callback=self._progress_cb()
                )
            )
            if not path:
                self.notify("❌ Не удалось скачать медиа", severity="error")
                return
            p = Path(path)
            if not p.exists() or p.stat().st_size == 0:
                # Пустой/недописанный файл не должен попадать в системный
                # просмотрщик — Android покажет «повреждено»
                self.notify("⚠️ Файл скачан, но пустой — попробуй ещё раз", severity="warning")
                return
            self.notify(f"✅ Скачано: {p.name***REMOVED***", timeout=3)
            await self._open_local_media(p, hint)
        except Exception as e:
            self.notify(f"❌ {e***REMOVED***", severity="error")
        finally:
            self._hide_progress()

    async def _open_local_media(self, path: Path, hint: str) -> None:
        """Показать локальный файл: ANSI-превью (chafa) или системный просмотрщик.

        Тип определяется по магии файла (не по расширению): JPEG с расширением
        .bin всё равно получит превью, а не «повреждено» от Android-просмотрщика.
        Пустой/битый файл в системный просмотрщик не передаётся.

        Видео: первый кадр извлекается через ffmpeg и показывается chafa-превью
        (в превью доступна клавиша o — открыть оригинал в плеере).
        """
        # Тип определяем по МАГИИ файла, а не по расширению: если JPEG лежит как
        # media_123.bin (документ без mime_type), Android-просмотрщик покажет
        # «повреждено» — а мы всё равно сделаем превью. Битый/пустой файл в
        # системный просмотрщик не отдаём вообще.
        if not path.exists() or path.stat().st_size == 0:
            self.notify("⚠️ Файл пустой или отсутствует", severity="warning")
            return
        kind = _file_media_kind(path)
        if kind == "other":
            # Магию не распознали — фоллбэк на расширение (например .pdf)
            kind = "image" if _is_image_path(str(path)) else (
                "video" if _is_video_path(str(path)) else "other"
            )
        if kind == "image" and shutil.which("chafa"):
            # Превью картинки прямо в терминале (ANSI-арт), без внешнего просмотрщика
            await self.app.push_screen(ImagePreviewScreen(path, hint))
            return
        if kind == "video" and shutil.which("chafa"):
            # chafa проверяем ДО ffmpeg: без chafa кадр показывать нечем
            frame = await self._extract_video_frame(path)
            if frame is not None:
                await self.app.push_screen(
                    ImagePreviewScreen(frame, f"{hint***REMOVED*** (первый кадр)", external=str(path))
                )
                return
        self._tg_app.open_file(str(path))

    async def _extract_video_frame(self, video: Path) -> Path | None:
        """Первый кадр видео через ffmpeg в jpg рядом с файлом. None — не вышло."""
        if not shutil.which("ffmpeg"):
            return None
        dest = media_dir() / f"{_sanitize(video.stem)***REMOVED***_frame.jpg"
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(video),
                "-frames:v", "1", "-q:v", "2",
                str(dest),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=30)
            if dest.exists() and dest.stat().st_size > 0:
                return dest
        except asyncio.TimeoutError:
            if proc is not None:
                try:
                    proc.kill()
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def _find_local_media(self, m) -> Path | None:
        """Путь к уже скачанному файлу медиа. None — файла нет на диске.

        Ограничение: CachedMsg (офлайн) не хранит имя файла, поэтому ищем по id
        (photo_7.jpg / media_7.gif / video_7.mp4...). Если файл был сохранён под
        кастомным file_name документа (например cat.gif) — по id не найдётся;
        это покрывается уведомлением «Файл не скачан».
        """
        if isinstance(m, CachedMsg):
            try:
                hits = sorted(media_dir().glob(f"*_{m.msg_id***REMOVED***.*"))
                if hits:
                    return hits[0***REMOVED***
            except Exception:
                pass
            return None
        dest = media_dir() / media_filename(m)
        return dest if dest.exists() else None

    def action_view_cached(self) -> None:
        """Открыть уже скачанное медиа из media_dir без повторного скачивания."""
        lst = self.query_one("#msg-list", ListView)
        idx = lst.index if lst.index is not None else 0
        m = self.get_message(idx)
        if m is None:
            return
        if isinstance(m, CachedMsg):
            if not m.media:
                self.notify("ℹ️ В сообщении нет медиа", timeout=2)
                return
            hint = m.media
        else:
            hint = media_hint(m)
            if not hint:
                self.notify("ℹ️ В сообщении нет медиа", timeout=2)
                return
        path = self._find_local_media(m)
        if path is None:
            self.notify("ℹ️ Файл не скачан — нажми Enter, чтобы загрузить", timeout=2)
            return
        self.notify(f"👁 Открываю из папки: {path.name***REMOVED***", timeout=2)
        self.run_worker(self._open_local_media(path, hint))

    def action_attach(self) -> None:
        """Отправить файл: системный пикер, встроенный браузер или путь вручную."""
        if _is_light_mode():
            self.notify("ℹ️ Отправка файлов — в адванс-режиме (Ctrl+G)", timeout=3)
            return
        if self._tg_app._tg is None or not self._tg_app._tg_connected:
            self.notify("⚠️ Нет соединения с Telegram", severity="warning")
            return
        picker = self._system_picker_cmd()
        if picker:
            self.notify("📁 Выбери файл (системный пикер)...", timeout=2)
            self._tg_app.run_worker(self._pick_and_send(picker))
            return
        # Нет termux-api → встроенный браузер (j/k), с пунктом «путь вручную»
        self._tg_app.run_worker(
            self.app.push_screen(FileBrowserScreen(), callback=self._on_browser_picked)
        )

    @staticmethod
    def _system_picker_cmd() -> list[str***REMOVED*** | None:
        """Команда системного пикера (termux-api) или None.

        В termux-api НЕТ бинаря termux-file-picker (распространённое заблуждение):
        системный пикер Android — termux-storage-get <выходной_файл>, который
        открывает SAF-пикер и копирует выбранный файл в указанный путь.
        termux-file-picker (если вдруг установлен) держим как запасной вариант.
        """
        if shutil.which("termux-storage-get"):
            return ["termux-storage-get"***REMOVED***
        if shutil.which("termux-file-picker"):
            return ["termux-file-picker"***REMOVED***
        return None

    @on(Button.Pressed, "#btn-attach")
    def _on_btn_attach_pressed(self, event: Button.Pressed) -> None:
        """Кнопка 📎 Файл — то же, что Ctrl+O / a (отправить файл/медиа)."""
        event.stop()
        self.action_attach()

    @on(Button.Pressed, "#btn-gif")
    def _on_btn_gif_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self._send_gif()

    @on(Button.Pressed, "#btn-voice")
    def _on_btn_voice_pressed(self, event: Button.Pressed) -> None:
        """Кнопка 🎤 Голос: toggle запись / выбор аудиофайла."""
        event.stop()
        self._toggle_voice()

    @on(Button.Pressed, "#btn-video")
    def _on_btn_video_pressed(self, event: Button.Pressed) -> None:
        """Кнопка 🎬 Видео: камера (termux-camera-photo) или выбор видеофайла."""
        event.stop()
        self._toggle_video()

    def _toggle_voice(self) -> None:
        """Голосовое: первый клик — запись (termux-microphone-recorder), второй — стоп.

        После стопа появляется выбор: отправить / прослушать / удалить. Если
        рекордера нет — фоллбэк на выбор аудиофайла (системный пикер или браузер
        в режиме audio). Запись поддерживается в адванс-режиме.
        """
        if self._recording:
            # Второй клик — стоп (стоп работает даже если сеть отвалилась или режим
            # сменился на лайт: запись должна остановиться, а решение — потом)
            self._tg_app.run_worker(self._stop_recording())
            return
        if _is_light_mode():
            self.notify("ℹ️ Голосовые — в адванс-режиме (Ctrl+G)", timeout=3)
            return
        if self._tg_app._tg is None or not self._tg_app._tg_connected:
            self.notify("⚠️ Нет соединения с Telegram", severity="warning")
            return
        recorder = shutil.which("termux-microphone-recorder")
        if recorder:
            self._start_recording(recorder)
            return
        # Нет termux-api → выбор аудиофайла
        picker = self._system_picker_cmd()
        if picker:
            self.notify("🎤 Выбери аудиофайл...", timeout=2)
            self._tg_app.run_worker(self._pick_and_send(picker, require_audio=True))
            return
        self._tg_app.run_worker(
            self.app.push_screen(
                FileBrowserScreen(audio_mode=True), callback=self._on_audio_browser_picked
            )
        )

    def _start_recording(self, recorder: str) -> None:
        """Начать запись голосового через termux-microphone-recorder."""
        path = str(media_dir() / f"voice_{time.time_ns()***REMOVED***.m4a")
        try:
            proc = subprocess.Popen(
                [recorder, "-f", path***REMOVED***,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            self.notify(f"❌ Не удалось начать запись: {e***REMOVED***", severity="error")
            return
        self._rec_proc = proc
        self._rec_path = path
        self._recording = True
        self._rec_started = time.monotonic()
        self._update_voice_btn(recording=True)
        self._start_rec_timer()
        self.notify("🔴 Запись... Нажми 🎤 ещё раз — стоп (Esc — отмена)", timeout=5)

    def _update_voice_btn(self, recording: bool) -> None:
        """Подпись кнопки 🎤: при записи — «⏹ 0:00» (дальше тикер секунд), иначе «🎤 Голос»."""
        try:
            btn = self.query_one("#btn-voice", Button)
            btn.label = "⏹ 0:00" if recording else "🎤 Голос"
        except Exception:
            pass

    def _start_rec_timer(self) -> None:
        """Запустить тикер длительности записи (обновление каждые 0.25 с)."""
        self._stop_rec_timer()
        try:
            self._rec_timer = self.set_interval(0.25, self._tick_recording)
        except Exception:
            self._rec_timer = None

    def _stop_rec_timer(self) -> None:
        """Остановить тикер длительности записи."""
        if self._rec_timer is not None:
            try:
                self._rec_timer.stop()
            except Exception:
                pass
            self._rec_timer = None

    def _tick_recording(self) -> None:
        """Обновить подпись кнопки ⏹: текущая длительность записи (мм:сс)."""
        if not self._recording or self._rec_started is None:
            self._stop_rec_timer()
            return
        elapsed = int(time.monotonic() - self._rec_started)
        try:
            self.query_one("#btn-voice", Button).label = f"⏹ {elapsed // 60***REMOVED***:{elapsed % 60:02d***REMOVED***"
        except Exception:
            pass

    async def _stop_recording(self) -> None:
        """Остановить запись и показать выбор: отправить / прослушать / удалить."""
        if self._rec_proc is not None:
            try:
                self._rec_proc.send_signal(signal.SIGINT)
                try:
                    self._rec_proc.wait(timeout=5)
                except Exception:
                    self._rec_proc.kill()
                    self._rec_proc.wait(timeout=3)
            except Exception:
                pass
        self._rec_proc = None
        self._recording = False
        self._update_voice_btn(recording=False)
        self._rec_started = None
        self._stop_rec_timer()
        path = self._rec_path
        self._rec_path = None
        if not path or not Path(path).exists() or Path(path).stat().st_size == 0:
            self.notify("⚠️ Запись пустая — отменена", severity="warning")
            return
        # Не отправляем сразу: спросим — отправить / прослушать / удалить
        self._pending_voice = path
        try:
            await self.app.push_screen(
                VoiceConfirmScreen(Path(path)), callback=self._on_voice_confirm
            )
        except Exception:
            pass

    def _on_voice_confirm(self, result) -> None:
        """Результат VoiceConfirmScreen: «send» — отправить, иначе — удалить.

        «send»: отправка как голосовое (voice_note); файл остаётся в media_dir.
        «delete» / None (Esc/закрытие): запись удаляется.
        """
        path = self._pending_voice
        self._pending_voice = None
        if result == "send":
            if path:
                self._tg_app.run_worker(self._send_file_path(path, voice_note=True))
            else:
                self._refocus_input()
            return
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
            self.notify("🗑 Запись удалена", timeout=2)
        self._refocus_input()

    def cancel_recording(self) -> None:
        """Отменить запись (Esc): убить процесс и удалить файл."""
        if not self._recording:
            return
        if self._rec_proc is not None:
            try:
                self._rec_proc.kill()
                self._rec_proc.wait(timeout=3)
            except Exception:
                pass
        self._rec_proc = None
        self._recording = False
        self._update_voice_btn(recording=False)
        self._rec_started = None
        self._stop_rec_timer()
        path = self._rec_path
        self._rec_path = None
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
        self.notify("🗑 Запись отменена", timeout=2)

    def _on_audio_browser_picked(self, path) -> None:
        """Результат FileBrowserScreen (режим audio): проверить и отправить."""
        if not path:
            return
        if path == MANUAL_PATH:
            self._voice_attach_mode = True
            self._attach_mode = True
            inp = self.query_one("#msg-input", Input)
            inp.placeholder = "🎤 Путь к аудио (Enter — отправить, Esc — отмена)"
            inp.focus()
            return
        if not _is_audio_path(path):
            self.notify("ℹ️ Это не аудиофайл — отправка отменена", severity="warning")
            return
        self._tg_app.run_worker(self._send_file_path(path, voice_note=True))

    def _send_gif(self) -> None:
        """Отправить гифку из галереи: системный пикер или браузер в режиме GIF."""
        if _is_light_mode():
            self.notify("ℹ️ Гифки — в адванс-режиме (Ctrl+G)", timeout=3)
            return
        if self._tg_app._tg is None or not self._tg_app._tg_connected:
            self.notify("⚠️ Нет соединения с Telegram", severity="warning")
            return
        picker = self._system_picker_cmd()
        if picker:
            self.notify("🎞 Выбери GIF в галерее...", timeout=2)
            self._tg_app.run_worker(self._pick_and_send(picker, require_gif=True))
            return
        # Нет termux-api → встроенный браузер, показываются только .gif/.webp
        self._tg_app.run_worker(
            self.app.push_screen(
                FileBrowserScreen(gif_mode=True), callback=self._on_gif_browser_picked
            )
        )

    def _on_gif_browser_picked(self, path) -> None:
        """Результат FileBrowserScreen (режим GIF): проверить и отправить гифку."""
        if not path:
            return
        if path == MANUAL_PATH:
            self._gif_attach_mode = True
            self._attach_mode = True
            inp = self.query_one("#msg-input", Input)
            inp.placeholder = "📎 Путь к GIF (Enter — отправить, Esc — отмена)"
            inp.focus()
            return
        if not _is_animated_media(path):
            self.notify("ℹ️ Это не анимированный GIF/WebP — отправка отменена", severity="warning")
            return
        # Превью первого кадра (chafa) + подтверждение перед отправкой
        self._pending_gif = path
        self._tg_app.run_worker(
            self.app.push_screen(GifConfirmScreen(Path(path)), callback=self._on_gif_confirm)
        )

    def _toggle_video(self) -> None:
        """Кнопка 🎬 Видео: запись через termux-camera-photo ИЛИ выбор видеофайла.

        Видео-запись termux-api не умеет (только termux-camera-photo — фото),
        поэтому при установленной камере кнопка открывает камеру и делает фото
        (превью + подтверждение, отправляется как фото), а без termux-api —
        выбор видеофайла. Повторный клик во время съёмки — отмена.
        """
        if self._capturing:
            self.cancel_capture()
            return
        if _is_light_mode():
            self.notify("ℹ️ Видео/фото — в адванс-режиме (Ctrl+G)", timeout=3)
            return
        if self._tg_app._tg is None or not self._tg_app._tg_connected:
            self.notify("⚠️ Нет соединения с Telegram", severity="warning")
            return
        camera = shutil.which("termux-camera-photo")
        if camera:
            self._camera_photo(camera)
            return
        self._send_video()

    def _camera_photo(self, camera: str) -> None:
        """Открыть камеру (termux-camera-photo) и сделать фото.

        Бинарь блокируется, пока пользователь не сделает/не отменит фото
        в камере Android; файл сохраняется в media_dir (foto_*.jpg).
        """
        path = str(media_dir() / f"foto_{time.time_ns()***REMOVED***.jpg")
        try:
            proc = subprocess.Popen(
                [camera, path***REMOVED***,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            self.notify(f"❌ Не удалось открыть камеру: {e***REMOVED***", severity="error")
            return
        self._capture_proc = proc
        self._capture_path = path
        self._capturing = True
        self._update_video_btn(capturing=True)
        self.notify("📸 Камера открыта — сделай фото (Esc — отмена)", timeout=5)
        self._tg_app.run_worker(self._wait_capture())

    def _update_video_btn(self, capturing: bool) -> None:
        """Подпись кнопки 🎬: при съёмке — «📸 Съёмка...»."""
        try:
            btn = self.query_one("#btn-video", Button)
            btn.label = "📸 Съёмка..." if capturing else "🎬 Видео"
        except Exception:
            pass

    async def _wait_capture(self) -> None:
        """Дождаться termux-camera-photo и показать превью + подтверждение.

        Фото делается в камере Android (TUI ждёт), после завершения —
        GifConfirmScreen (📸): y/Enter — отправить, n/Esc — отмена.
        """
        proc = self._capture_proc
        path = self._capture_path
        try:
            if proc is not None:
                try:
                    await asyncio.to_thread(proc.wait, 120)
                except Exception:
                    # Таймаут (камеру забыли закрыть) — убиваем процесс, иначе
                    # он останется зомби и камера зависнет открытой
                    try:
                        proc.kill()
                        await asyncio.to_thread(proc.wait, 5)
                    except Exception:
                        pass
        finally:
            self._capture_proc = None
            self._capturing = False
            self._update_video_btn(capturing=False)
        if not path or not Path(path).exists() or Path(path).stat().st_size == 0:
            # Отмена через TUI (cancel_capture) уже показала «Съёмка отменена» —
            # не дублируем тост про камеру.
            if self._capture_path is not None:
                self.notify("📷 Фото не сделано (отменено в камере)", timeout=2)
            return
        self._pending_photo = path
        self.notify("📸 Фото готово — подтверди отправку", timeout=2)
        try:
            await self.app.push_screen(
                GifConfirmScreen(Path(path), hint_icon="📸"), callback=self._on_photo_confirm
            )
        except Exception:
            pass

    def cancel_capture(self) -> None:
        """Отменить съёмку (Esc): убить процесс и удалить файл."""
        if not self._capturing:
            return
        if self._capture_proc is not None:
            try:
                self._capture_proc.kill()
                self._capture_proc.wait(timeout=3)
            except Exception:
                pass
        self._capture_proc = None
        self._capturing = False
        self._update_video_btn(capturing=False)
        path = self._capture_path
        self._capture_path = None
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
        self.notify("🗑 Съёмка отменена", timeout=2)

    def _on_photo_confirm(self, confirmed) -> None:
        """Результат GifConfirmScreen для фото с камеры: True — отправить."""
        path = self._pending_photo
        self._pending_photo = None
        if not confirmed:
            self._refocus_input()
            return
        if path and self._tg_app._tg is not None:
            self._tg_app.run_worker(self._send_file_path(path))
        else:
            self._refocus_input()

    def _send_video(self) -> None:
        """Отправить видеофайл: системный пикер или браузер в режиме видео.

        Fallback кнопки 🎬 без termux-api (камеры нет). Записи видео termux-api
        не умеет — только выбор готового видеофайла.
        """
        if _is_light_mode():
            self.notify("ℹ️ Видео — в адванс-режиме (Ctrl+G)", timeout=3)
            return
        if self._tg_app._tg is None or not self._tg_app._tg_connected:
            self.notify("⚠️ Нет соединения с Telegram", severity="warning")
            return
        picker = self._system_picker_cmd()
        if picker:
            self.notify("🎬 Выбери видеофайл...", timeout=2)
            self._tg_app.run_worker(self._pick_and_send(picker, require_video=True))
            return
        # Нет termux-api → встроенный браузер, показываются только видеофайлы
        self._tg_app.run_worker(
            self.app.push_screen(
                FileBrowserScreen(video_mode=True), callback=self._on_video_browser_picked
            )
        )

    def _on_video_browser_picked(self, path) -> None:
        """Результат FileBrowserScreen (режим video): проверить и отправить."""
        if not path:
            return
        if path == MANUAL_PATH:
            self._video_attach_mode = True
            self._attach_mode = True
            inp = self.query_one("#msg-input", Input)
            inp.placeholder = "🎬 Путь к видео (Enter — отправить, Esc — отмена)"
            inp.focus()
            return
        if not _is_video_path(path):
            self.notify("ℹ️ Это не видеофайл — отправка отменена", severity="warning")
            return
        self._tg_app.run_worker(self._send_file_path(path))

    def _on_browser_picked(self, path) -> None:
        """Результат FileBrowserScreen: путь файла или MANUAL_PATH."""
        if not path:
            return
        if path == MANUAL_PATH:
            self._attach_mode = True
            inp = self.query_one("#msg-input", Input)
            inp.placeholder = "📎 Путь к файлу (Enter — отправить, Esc — отмена)"
            inp.focus()
            return
        self._tg_app.run_worker(self._send_file_path(path))

    def cancel_attach(self) -> None:
        self._attach_mode = False
        self._gif_attach_mode = False
        self._voice_attach_mode = False
        self._video_attach_mode = False
        inp = self.query_one("#msg-input", Input)
        inp.placeholder = "Напиши сообщение..."
        inp.value = ""

    async def _pick_and_send(self, picker: list[str***REMOVED***, require_gif: bool = False, require_audio: bool = False, require_video: bool = False) -> None:
        """Системный пикер. termux-storage-get копирует выбранный файл в dest
        (SAF требует имя выходного файла заранее), termux-file-picker печатает
        путь в stdout. Затем файл отправляется в чат. require_gif=True —
        отправлять только анимированные GIF/WebP; require_audio=True —
        отправлять только аудио (как голосовое); require_video=True —
        отправлять только видеофайлы."""
        proc = None
        dest: str | None = None
        try:
            cmd = list(picker)
            if cmd[0***REMOVED*** == "termux-storage-get":
                # time_ns: два быстрых нажатия 'a' не должны получить один dest
                dest = str(media_dir() / f"picker_{time.time_ns()***REMOVED***.bin")
                cmd.append(dest)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            # Таймаут: пикер не должен висеть вечно, если API не отвечает
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
            if dest:
                # SAF-пикер: файл должен появиться в dest (отмена → файла нет)
                path = dest if Path(dest).exists() else ""
            else:
                path = out.decode().strip() if out else ""
            if not path or not Path(path).exists() or Path(path).stat().st_size == 0:
                self.notify("❌ Файл не выбран", severity="warning")
                return
            if dest:
                # SAF-копия всегда .bin — восстановим настоящее расширение по магии,
                # чтобы фото/видео ушли как фото/видео, а не как безымянный документ
                path = _picker_proper_ext(path)
            if require_gif and not _is_animated_media(path):
                self.notify("ℹ️ Это не анимированный GIF/WebP — отправка отменена", severity="warning")
                return
            if require_gif:
                # Превью первого кадра (chafa) + подтверждение перед отправкой
                self._pending_gif = path
                self._tg_app.run_worker(
                    self.app.push_screen(GifConfirmScreen(Path(path)), callback=self._on_gif_confirm)
                )
                return
            if require_audio and not _is_audio_path(path):
                self.notify("ℹ️ Это не аудиофайл — отправка отменена", severity="warning")
                return
            if require_audio:
                await self._send_file_path(path, voice_note=True)
                return
            if require_video and not _is_video_path(path):
                self.notify("ℹ️ Это не видеофайл — отправка отменена", severity="warning")
                return
            await self._send_file_path(path)
        except asyncio.TimeoutError:
            self.notify("⏱️ Пикер не ответил за 60 c", severity="warning")
        except Exception as e:
            self.notify(f"❌ {e***REMOVED***", severity="error")
        finally:
            if proc is not None and proc.returncode is None:
                try:
                    proc.kill()
                except Exception:
                    pass

    async def _send_file_path(self, path: str, voice_note: bool = False) -> None:
        """Отправить файл. voice_note=True — как голосовое сообщение."""
        if (
            self._tg_app._tg is None
            or not self._tg_app._tg_connected
            or self._dialog.input_entity is None
        ):
            msg = "⚠️ Нет соединения — голосовое не отправлено" if voice_note \
                else "⚠️ Нет соединения — файл не отправлен"
            self.notify(msg, severity="warning")
            return
        label = "голосовое" if voice_note else Path(path).name
        self.notify(f"⬆️ Отправляю {label***REMOVED***...", timeout=2)
        try:
            await self._tg_app._await_tg(
                self._tg_app._tg.send_file_async(
                    self._dialog.input_entity, path,
                    progress_callback=self._progress_cb(), voice_note=voice_note,
                )
            )
            self.notify("✅ Голосовое отправлено" if voice_note else "✅ Файл отправлен", timeout=2)
            self._tg_app.run_worker(self._load_messages())
            self._refocus_input()
        except Exception as e:
            self.notify(f"❌ {e***REMOVED***", severity="error")
        finally:
            self._hide_progress()

    def _refocus_input(self) -> None:
        """Вернуть фокус на строку ввода после отправки (кнопка/пикер)."""
        try:
            self.query_one("#msg-input", Input).focus()
        except Exception:
            pass

    def _on_gif_confirm(self, confirmed) -> None:
        """Результат GifConfirmScreen: True — отправить выбранную гифку."""
        if not confirmed:
            self._refocus_input()
            return
        path = self._pending_gif
        if path and self._tg_app._tg is not None:
            self._tg_app.run_worker(self._send_file_path(path))
        else:
            self._refocus_input()

    def action_quit_app(self) -> None:
        self._tg_app.action_quit()

    @on(Input.Submitted, "#msg-input")
    async def _on_msg_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        text = event.value.strip()
        if self._attach_mode:
            self._attach_mode = False
            gif_only = self._gif_attach_mode
            voice_only = self._voice_attach_mode
            video_only = self._video_attach_mode
            self._gif_attach_mode = False
            self._voice_attach_mode = False
            self._video_attach_mode = False
            event.input.placeholder = "Напиши сообщение..."
            if text:
                if gif_only and not _is_animated_media(text):
                    self.notify("ℹ️ Это не анимированный GIF/WebP — не отправлено", severity="warning")
                    return
                if gif_only:
                    # Превью первого кадра (chafa) + подтверждение перед отправкой
                    self._pending_gif = text
                    self._tg_app.run_worker(
                        self.app.push_screen(GifConfirmScreen(Path(text)), callback=self._on_gif_confirm)
                    )
                    return
                if voice_only and not _is_audio_path(text):
                    self.notify("ℹ️ Это не аудиофайл — не отправлено", severity="warning")
                    return
                if voice_only:
                    await self._send_file_path(text, voice_note=True)
                    return
                if video_only and not _is_video_path(text):
                    self.notify("ℹ️ Это не видеофайл — не отправлено", severity="warning")
                    return
                await self._send_file_path(text)
            return
        if not text:
            # Пустой ввод + Enter → открыть выделенное медиа из списка
            lst = self.query_one("#msg-list", ListView)
            idx = lst.index if lst.index is not None else 0
            m = self.get_message(idx)
            if m is not None and media_hint(m):
                await self.download_and_open(m)
            return
        if (
            self._tg_app._tg is None
            or not self._tg_app._tg_connected
            or self._dialog.input_entity is None
        ):
            self.notify("⚠️ Нет соединения — сообщение не отправлено", severity="warning")
            return
        try:
            await self._tg_app._await_tg(
                self._tg_app._tg.send_message_async(self._dialog.input_entity, text)
            )
            event.input.value = ""
            self.notify("✅ Отправлено", timeout=1)
            self._tg_app.run_worker(self._load_messages())
        except Exception as e:
            self.notify(f"❌ {e***REMOVED***", severity="error")


# ═══════════════════════════════════════════════════════════════
# ЭКРАН 3: Превью картинки прямо в терминале (chafa → ANSI-арт)
# ═══════════════════════════════════════════════════════════════

class ImagePreviewScreen(Screen):
    """Полноэкранное ANSI-превью через chafa — без внешнего просмотрщика.

    Анимированные GIF/WebP переигрываются кадр за кадром таймером Textual:
    chafa --animate on выдаёт все кадры подряд (разделитель — form feed \x0c),
    мы разбираем поток на кадры и крутим их циклом. Если chafa-версия не
    разделяет кадры (fallback) — кадры вытаскиваются через PIL и рендерятся
    по одному (chafa --animate off). Пауза — клавиша p.
    """

    BINDINGS = [
        Binding("escape", "close", show=False),
        Binding("enter", "close", show=False),
        Binding("q", "close", show=False),
        Binding("space", "close", show=False),
        Binding("p", "toggle_pause", "Пауза", show=False),
        Binding("o", "open_external", "▶ Плеер", show=False),
        # ВАЖНО: в Textual 8 литеральный '+' в key — разделитель модификаторов
        # (parse_key('+') => ([''***REMOVED***, '')), поэтому используем именованные клавиши:
        # '+'->plus, '='->equals_sign, '-'->minus, '_'->underscore (_character_to_key).
        Binding("plus,equals_sign", "zoom_in", "＋", show=False),
        Binding("minus,underscore", "zoom_out", "−", show=False),
        Binding("0", "zoom_reset", "1×", show=False),
    ***REMOVED***

    CSS = """
    #preview-box {
        width: 100%;
        height: 100%;
        background: #000000;
        align: center middle;
        padding: 1;
    ***REMOVED***
    #preview-label {
        width: auto;
        height: auto;
        color: #e0e0e0;
    ***REMOVED***
    #preview-hint {
        dock: bottom;
        height: 1;
        color: #777777;
        text-align: center;
    ***REMOVED***
    """

    def __init__(self, path: Path, hint: str = "", external: str | None = None):
        super().__init__()
        self._path = path
        self._hint = hint
        self._external = external   # оригинал (видео), если превью — это кадр
        self._frames: list[Text***REMOVED*** = [***REMOVED***
        self._frame_idx = 0
        self._anim_timer: Timer | None = None
        self._paused = False
        self._zoom = 1.0            # масштаб превью (+/−, 0 — сброс)
        self._rendering = False     # идёт ли рендер прямо сейчас
        self._pending_render = False  # быстрые +/−: нужна повторная отрисовка

    def compose(self) -> ComposeResult:
        hint_text = f"{self._hint***REMOVED***  ·  " if self._hint else ""
        yield Container(
            Static("⏳ Рендерю превью...", id="preview-label"),
            Label(f"{hint_text***REMOVED***{self._hint_close()***REMOVED***", id="preview-hint"),
            id="preview-box",
        )

    def _hint_close(self) -> str:
        """Подсказка закрытия/зума внизу превью."""
        extra = " · o — ▶ открыть в плеере" if self._external else ""
        return f"Esc / Enter / q — закрыть{extra***REMOVED*** · +/− масштаб {self._zoom:.2f***REMOVED***× · 0 — сброс"

    def _preview_size(self) -> tuple[int, int***REMOVED***:
        """Размер превью в символах с учётом зума (+/−)."""
        base_cols = self.app.size.width - 4
        base_rows = self.app.size.height - 4
        return max(16, int(base_cols * self._zoom)), max(8, int(base_rows * self._zoom))

    def on_mount(self) -> None:
        self.run_worker(self._render_preview())

    def on_unmount(self) -> None:
        self._stop_anim()

    def _stop_anim(self) -> None:
        if self._anim_timer is not None:
            self._anim_timer.stop()
            self._anim_timer = None

    async def _render_preview(self) -> None:
        """Отрисовать превью. Повторные вызовы во время рендера помечают
        _pending_render — после завершения текущего рендера кадр перерисуется
        с новым масштабом (быстрые нажатия +/- не теряются).

        ВАЖНО: имя не `_render` — Textual 8 вызывает Widget._render() внутри
        композитора, чтобы получить Visual; асинхронный `_render` возвращал
        корутину вместо Visual → AttributeError render_strips (краш превью)."""
        if not self.is_mounted:
            return
        if self._rendering:
            self._pending_render = True
            return
        self._rendering = True
        try:
            await self._render_impl()
        finally:
            self._rendering = False
            if self._pending_render and self.is_mounted:
                self._pending_render = False
                self.run_worker(self._render_preview())

    async def _render_impl(self) -> None:
        st = self.query_one("#preview-label", Static)
        cols, rows = self._preview_size()
        # GIF/WebP — сначала пробуем анимированное превью.
        # try/except: экран могут закрыть, пока chafa рендерит (query_one упадёт
        # на размонтированном экране — это не ошибка, просто закрытие).
        if _is_animatable(self._path):
            try:
                if await self._render_animation(cols, rows):
                    return
            except Exception:
                pass  # редкий сбой анимации — уходим в статический fallback
        if not self.is_mounted:
            return
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                "chafa",
                "--format", "symbols",
                "--colors", "256",
                "--animate", "off",
                "--size", f"{cols***REMOVED***x{rows***REMOVED***",
                str(self._path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            raw = out.decode("utf-8", "replace") if out else ""
            if not raw.strip():
                st.update("⚠️ chafa не смог отрисовать (файл не картинка?)")
                return
            st.update(Text.from_ansi(_strip_csi_non_sgr(raw)))
            prefix = f"{self._hint***REMOVED***  ·  " if self._hint else ""
            self.query_one("#preview-hint", Label).update(prefix + self._hint_close())
        except asyncio.TimeoutError:
            if proc is not None:
                proc.kill()
            st.update("⏱️ Слишком долгий рендер — превью отменено")
        except FileNotFoundError:
            st.update("❌ chafa не установлен — поставь: pkg install chafa")
        except Exception as e:
            st.update(f"❌ {e***REMOVED***")

    # ── Масштабирование (+/−) ──────────────────────────────

    def action_zoom_in(self) -> None:
        self._zoom = min(4.0, self._zoom * 1.25)
        self._zoom_rerender()

    def action_zoom_out(self) -> None:
        self._zoom = max(0.25, self._zoom / 1.25)
        self._zoom_rerender()

    def action_zoom_reset(self) -> None:
        self._zoom = 1.0
        self._zoom_rerender()

    def _zoom_rerender(self) -> None:
        """Остановить анимацию и перезапустить chafa с новым размером."""
        self._stop_anim()
        self._frames = [***REMOVED***
        self._frame_idx = 0
        self._paused = False
        self.run_worker(self._render_preview())

    # ── Анимация: chafa --animate on + таймер Textual ────────

    async def _render_animation(self, cols: int, rows: int) -> bool:
        """Запустить анимацию. True — кадры есть и таймер крутится."""
        durations = _gif_durations(self._path)
        frames = await self._chafa_animate_on_frames(cols, rows)
        if len(frames) < 2:
            frames = await self._chafa_per_frame_frames(cols, rows)
        if len(frames) < 2 or not self.is_mounted:
            return False
        self._frames = [Text.from_ansi(_strip_csi_non_sgr(f)) for f in frames***REMOVED***
        self._frame_idx = 0
        st = self.query_one("#preview-label", Static)
        st.update(self._frames[0***REMOVED***)
        hint = self.query_one("#preview-hint", Label)
        prefix = f"{self._hint***REMOVED***  ·  " if self._hint else ""
        hint.update(
            prefix
            + f"⏵ {len(frames)***REMOVED*** кадров · p — пауза · +/− {self._zoom:.2f***REMOVED***× · Esc — закрыть"
        )
        self._anim_timer = self.set_interval(_frame_interval(durations), self._next_frame)
        return True

    async def _chafa_animate_on_frames(self, cols: int, rows: int) -> list[str***REMOVED***:
        """Один прогон chafa --animate on; кадры разделены form feed (\x0c)."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "chafa",
                "--format", "symbols",
                "--colors", "256",
                "--animate", "on",
                "--duration", "0",
                "--size", f"{cols***REMOVED***x{rows***REMOVED***",
                str(self._path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            if not out:
                return [***REMOVED***
            raw = out.decode("utf-8", "replace")
            # Формат не документирован: пробуем form feed, иначе — одиночный кадр.
            # Лимит кадров — как в fallback (превью, а не плеер).
            if "\x0c" in raw:
                return [f for f in raw.split("\x0c") if f.strip()***REMOVED***[:60***REMOVED***
            return [***REMOVED***
        except Exception:
            return [***REMOVED***

    async def _chafa_per_frame_frames(self, cols: int, rows: int) -> list[str***REMOVED***:
        """Fallback: кадры через PIL (ImageSequence) + chafa --animate off по одному.

        Лимиты: максимум 60 кадров ИЛИ 45 секунд суммарно — чтобы сломанный/hanging
        chafa не превращал превью в многоминутное ожидание.
        """
        frames: list[str***REMOVED*** = [***REMOVED***
        deadline = time.monotonic() + 45.0
        try:
            from PIL import Image, ImageSequence
            img = Image.open(self._path)
            for frame in ImageSequence.Iterator(img):
                if len(frames) >= 60 or time.monotonic() > deadline:
                    break
                rgb = frame.convert("RGB")
                tmp: str | None = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                        rgb.save(tf, format="PNG")
                        tmp = tf.name
                    proc = await asyncio.create_subprocess_exec(
                        "chafa",
                        "--format", "symbols",
                        "--colors", "256",
                        "--animate", "off",
                        "--size", f"{cols***REMOVED***x{rows***REMOVED***",
                        tmp,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    out, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
                    if out:
                        frames.append(out.decode("utf-8", "replace"))
                finally:
                    if tmp is not None:
                        try:
                            Path(tmp).unlink()
                        except Exception:
                            pass
                if len(frames) >= 60:
                    break
        except Exception:
            pass
        return frames

    def _next_frame(self) -> None:
        """Таймер: показать следующий кадр анимации."""
        if self._paused or not self._frames:
            return
        self._frame_idx = (self._frame_idx + 1) % len(self._frames)
        try:
            self.query_one("#preview-label", Static).update(self._frames[self._frame_idx***REMOVED***)
        except Exception:
            pass

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        hint = self.query_one("#preview-hint", Label)
        if len(self._frames) > 1:
            state = "⏸ Пауза" if self._paused else f"⏵ {len(self._frames)***REMOVED*** кадров"
        else:
            state = "⏸ Пауза" if self._paused else "⏳ Рендер..."
        prefix = f"{self._hint***REMOVED***  ·  " if self._hint else ""
        hint.update(
            prefix
            + f"{state***REMOVED*** · p — {'продолжить' if self._paused else 'пауза'***REMOVED*** · +/− {self._zoom:.2f***REMOVED***× · Esc — закрыть"
        )

    def action_open_external(self) -> None:
        """Открыть оригинал (например видео) внешним просмотрщиком."""
        if not self._external:
            self.notify("ℹ️ Внешний файл недоступен для этого превью", timeout=2)
            return
        self._stop_anim()
        self.dismiss()
        self.app.open_file(self._external)   # TGApp.open_file (staticmethod)

    def action_close(self) -> None:
        self._stop_anim()
        self.dismiss()


# ═══════════════════════════════════════════════════════════════
# ЭКРАН 3.5: Превью гифки + подтверждение перед отправкой
# ═══════════════════════════════════════════════════════════════

class GifConfirmScreen(Screen):
    """Превью первого кадра выбранной гифки (chafa) + подтверждение отправки.

    y / Enter — отправить, n / Esc / q — отмена. Результат dismiss(True/False)
    передаётся в callback push_screen(..., callback=...). Первый кадр
    вытаскивается через PIL и рендерится chafa (--animate off); если chafa
    недоступен — показывается подсказка, но отправить (y) всё равно можно.
    """

    BINDINGS = [
        Binding("y,enter", "confirm", "✅ Отправить", show=True),
        Binding("n,escape,q", "cancel", "❌ Отмена", show=True),
    ***REMOVED***

    CSS = """
    #preview-box {
        width: 100%;
        height: 100%;
        background: #000000;
        align: center middle;
        padding: 1;
    ***REMOVED***
    #preview-label {
        width: auto;
        height: auto;
        color: #e0e0e0;
    ***REMOVED***
    #preview-hint {
        dock: bottom;
        height: 1;
        color: #777777;
        text-align: center;
    ***REMOVED***
    """

    def __init__(self, path: Path, hint_icon: str = "🎞"):
        super().__init__()
        self._path = path
        self._hint_icon = hint_icon

    def compose(self) -> ComposeResult:
        yield Container(
            Static("⏳ Рендерю превью...", id="preview-label"),
            Label("", id="preview-hint"),
            id="preview-box",
        )

    def on_mount(self) -> None:
        self.run_worker(self._render_preview())

    async def _render_preview(self) -> None:
        """Первый кадр через chafa (--animate off); без chafa — текст-подсказка.

        ВАЖНО: имя не `_render` — Textual 8 вызывает Widget._render() внутри
        композитора; асинхронный `_render` ломал бы превью (краш render_strips)."""
        if not self.is_mounted:
            return
        st = self.query_one("#preview-label", Static)
        cols = max(16, self.app.size.width - 4)
        rows = max(8, self.app.size.height - 6)
        tmp_frame: Path | None = None
        try:
            if shutil.which("chafa"):
                # Первый кадр вытаскиваем явно через PIL (chafa с --animate off сам
                # показывает первый кадр, но PIL гарантирует это на 100%),
                # и рендерим его. Временный файл удаляем в finally ниже.
                try:
                    # GIF/WebP — первый кадр через PIL; фото (jpg/png) уже кадр
                    tmp_frame = _gif_first_frame(self._path) if _is_animatable(self._path) else None
                except Exception:
                    tmp_frame = None
                source = tmp_frame or self._path
                proc = None
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "chafa",
                        "--format", "symbols",
                        "--colors", "256",
                        "--animate", "off",
                        "--size", f"{cols***REMOVED***x{rows***REMOVED***",
                        str(source),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    out, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                    raw = out.decode("utf-8", "replace") if out else ""
                    if raw.strip():
                        st.update(Text.from_ansi(_strip_csi_non_sgr(raw)))
                except asyncio.TimeoutError:
                    if proc is not None:
                        proc.kill()
                    st.update("⏱️ Слишком долгий рендер — можно отправить без превью (y)")
                except Exception as e:
                    st.update(f"❌ {e***REMOVED***")
            else:
                st.update("❌ chafa не установлен — pkg install chafa (y — отправить всё равно)")
        finally:
            # Удаляем временный кадр в любом случае (в т.ч. при отмене корутины)
            if tmp_frame is not None:
                try:
                    tmp_frame.unlink(missing_ok=True)
                except Exception:
                    pass
        try:
            size = self._path.stat().st_size // 1024
        except Exception:
            size = 0
        name = self._path.name[:60***REMOVED***
        try:
            # Экран могут закрыть, пока chafa рендерит (query_one на размонтированном
            # экране бросит NoMatches — это не ошибка, просто закрытие)
            if self.is_mounted:
                self.query_one("#preview-hint", Label).update(
                    f"{self._hint_icon***REMOVED*** {name***REMOVED*** ({size***REMOVED*** КБ)  ·  y/Enter — отправить · n/Esc — отмена"
                )
        except Exception:
            pass

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class VoiceConfirmScreen(Screen):
    """Выбор после остановки записи: отправить / прослушать / удалить.

    s/Enter — отправить как голосовое, p/l — прослушать (терминал остаётся,
    играет termux-media-player), d/Esc/q — удалить запись.

    ВАЖНО: space НЕ привязан к «слушать» — когда фокус на кнопке, Button сам
    поглощает space/enter (активирует кнопку), поэтому только p/l.
    dismiss("send") / dismiss("delete") → callback _on_voice_confirm.
    """

    BINDINGS = [
        Binding("s,enter", "confirm", "📤 Отправить", show=True),
        Binding("p,l", "listen", "▶️ Слушать", show=True),
        Binding("d,escape,q", "delete", "🗑 Удалить", show=True),
    ***REMOVED***

    CSS = """
    #voice-box {
        width: 64;
        height: 12;
        border: round #35d07f;
        background: #10131c;
        padding: 1;
        align: center middle;
    ***REMOVED***
    #voice-title {
        color: #35d07f;
        text-style: bold;
        text-align: center;
    ***REMOVED***
    #voice-hint {
        color: #e0e0e0;
        text-align: center;
    ***REMOVED***
    #voice-btns {
        align: center middle;
        height: 4;
    ***REMOVED***
    #vc-send, #vc-listen, #vc-delete {
        width: auto;
        min-width: 10;
        height: 3;
        margin: 0 1;
        background: #24283b;
        text-style: bold;
    ***REMOVED***
    #vc-send {
        border: solid #35d07f;
        color: #35d07f;
    ***REMOVED***
    #vc-send:focus {
        border: double #7dffa8;
        color: #7dffa8;
    ***REMOVED***
    #vc-listen {
        border: solid #4fc3f7;
        color: #4fc3f7;
    ***REMOVED***
    #vc-listen:focus {
        border: double #7dc4ff;
        color: #7dc4ff;
    ***REMOVED***
    #vc-delete {
        border: solid #f7768e;
        color: #f7768e;
    ***REMOVED***
    #vc-delete:focus {
        border: double #ff9eac;
        color: #ff9eac;
    ***REMOVED***
    """

    def __init__(self, path: Path):
        super().__init__()
        self._path = path

    def compose(self) -> ComposeResult:
        try:
            size = self._path.stat().st_size // 1024
        except Exception:
            size = 0
        yield Container(
            Label("🎤 Запись готова", id="voice-title"),
            Label(f"[dim***REMOVED***{self._path.name[:44***REMOVED******REMOVED*** ({size***REMOVED*** КБ)[/***REMOVED***", id="voice-hint"),
            Horizontal(
                Button("📤 Отправить", id="vc-send"),
                Button("▶️ Прослушать", id="vc-listen"),
                Button("🗑 Удалить", id="vc-delete"),
                id="voice-btns",
            ),
            Label("s/Enter — отправить · p/l — слушать · d/Esc — удалить", id="voice-hint"),
            id="voice-box",
        )

    def on_mount(self) -> None:
        try:
            self.query_one("#vc-send", Button).focus()
        except Exception:
            pass

    @on(Button.Pressed, "#vc-send")
    def _on_btn_send(self, event: Button.Pressed) -> None:
        event.stop()
        self.action_confirm()

    @on(Button.Pressed, "#vc-listen")
    def _on_btn_listen(self, event: Button.Pressed) -> None:
        event.stop()
        self.action_listen()

    @on(Button.Pressed, "#vc-delete")
    def _on_btn_delete(self, event: Button.Pressed) -> None:
        event.stop()
        self.action_delete()

    def action_confirm(self) -> None:
        self.dismiss("send")

    def action_delete(self) -> None:
        self.dismiss("delete")

    def action_listen(self) -> None:
        """Прослушать запись, не закрывая экран (терминал продолжает работать)."""
        player = shutil.which("termux-media-player")
        try:
            if player:
                subprocess.Popen(
                    [player, "play", str(self._path)***REMOVED***,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.notify("▶️ Слушаю... после прослушивания: s — отправить · d — удалить", timeout=5)
                return
            opener = shutil.which("termux-open") or shutil.which("xdg-open")
            if opener:
                subprocess.Popen(
                    [opener, str(self._path)***REMOVED***,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.notify("▶️ Открыл в плеере — вернись: s — отправить · d — удалить", timeout=5)
                return
        except Exception as e:
            self.notify(f"❌ Не удалось проиграть: {e***REMOVED***", severity="error")
            return
        self.notify("⚠️ Нет плеера (termux-media-player / termux-open)", severity="warning")


# ═══════════════════════════════════════════════════════════════
# ЭКРАН 4: Встроенный файловый браузер (когда нет termux-file-picker)
# ═══════════════════════════════════════════════════════════════

class FileBrowserScreen(Screen):
    """Выбор файла прямо в терминале — fallback без termux-file-picker.

    Навигация j/k (без стрелок), Enter — войти/выбрать, h — на уровень выше.
    Быстрый переход в избранные папки одной клавишей:
    d — Загрузки, i — Картинки, c — DCIM, m — Музыка (~/storage/<name>).
    Первый пункт — «ввести путь вручную» (возвращает MANUAL_PATH).
    При выборе файла экран закрывается со значением пути (dismiss(path)).
    """

    # Избранные папки: клавиша -> (подпапка внутри ~/storage)
    _FAVORITE_DIRS = {
        "downloads": "⬇️ Загрузки",
        "pictures": "🖼 Картинки",
        "dcim": "📷 DCIM",
        "music": "🎵 Музыка",
    ***REMOVED***

    BINDINGS = [
        Binding("escape", "close", show=False),
        Binding("h", "up", "⬆️ Вверх", show=True),
        Binding("backspace", "up", "⬆️ Вверх", show=False),
        Binding("d", "goto_favorite('downloads')", "⬇️ Загрузки", show=True),
        Binding("i", "goto_favorite('pictures')", "🖼 Картинки", show=True),
        Binding("c", "goto_favorite('dcim')", "📷 DCIM", show=True),
        Binding("m", "goto_favorite('music')", "🎵 Музыка", show=True),
    ***REMOVED***

    CSS = """
    #fb-header {
        background: #1a1a2e;
        color: #e0e0e0;
        padding: 1;
        text-align: center;
        text-style: bold;
    ***REMOVED***
    #fb-path {
        color: #4fc3f7;
        padding: 0 1;
        text-style: italic;
    ***REMOVED***
    #fb-list {
        border: solid #333;
        height: 1fr;
    ***REMOVED***
    #fb-hint {
        color: #777777;
        padding: 0 1;
    ***REMOVED***
    """

    def __init__(self, gif_mode: bool = False, audio_mode: bool = False, video_mode: bool = False):
        super().__init__()
        self._dir: Path = Path.home() / "storage"
        self._items: list[tuple[str, object***REMOVED******REMOVED*** = [***REMOVED***
        self._gif_mode = gif_mode   # показывать только .gif/.webp файлы
        self._audio_mode = audio_mode   # показывать только аудиофайлы (🎤)
        self._video_mode = video_mode   # показывать только видеофайлы (🎬)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("📁 Выбери файл для отправки", id="fb-header")
        yield Label("", id="fb-path")
        yield NavListView(id="fb-list")
        hint = (
            "j/k — вниз/вверх · Enter — войти/выбрать · h — наверх · "
            "d — Загрузки · i — Картинки · c — DCIM · m — Музыка · Esc — отмена"
        )
        if self._gif_mode:
            hint = "🎞 Режим GIF: только .gif/.webp · " + hint
        elif self._audio_mode:
            hint = "🎤 Режим голосового: только аудио · " + hint
        elif self._video_mode:
            hint = "🎬 Режим видео: только видеофайлы · " + hint
        yield Label(hint, id="fb-hint")
        yield Footer()

    def on_mount(self) -> None:
        # Стартовая папка: ~/storage (downloads/dcim/pictures/music после termux-setup-storage)
        if not self._dir.exists():
            self._dir = Path("/sdcard") if Path("/sdcard").exists() else Path.home()
        self._load_dir()
        self.query_one("#fb-list", ListView).focus()

    def _load_dir(self) -> None:
        """Перечитать текущую папку в список."""
        lst = self.query_one("#fb-list", ListView)
        lst.clear()
        self.query_one("#fb-path", Label).update(f"📂 {self._dir***REMOVED***")
        self._items = [("manual", None)***REMOVED***
        labels: list[str***REMOVED*** = ["📝 Ввести путь вручную"***REMOVED***
        if self._dir.parent != self._dir and str(self._dir) != "/":
            self._items.append(("up", None))
            labels.append("⬆️ .. (на уровень выше)")
        # Сортировка с защитой от сбоев stat() (права на /sdcard бывают разные)
        entries: list[tuple[bool, Path***REMOVED******REMOVED*** = [***REMOVED***
        try:
            for p in self._dir.iterdir():
                try:
                    entries.append((p.is_file(), p))
                except Exception:
                    continue
        except Exception:
            pass
        entries.sort(key=lambda t: (t[0***REMOVED***, t[1***REMOVED***.name.lower()))
        for is_file, p in entries:
            if p.name.startswith("."):
                continue
            if is_file and self._gif_mode and p.suffix.lower() not in (".gif", ".webp"):
                continue
            if is_file and self._audio_mode and not _is_audio_path(p):
                continue
            if is_file and self._video_mode and not _is_video_path(p):
                continue
            if is_file:
                try:
                    size = p.stat().st_size if p.exists() else 0
                except Exception:
                    size = 0
                self._items.append(("file", p))
                icon = "🎵" if self._audio_mode else ("🎬" if self._video_mode else "📄")
                labels.append(f"{icon***REMOVED*** {p.name***REMOVED***  [dim***REMOVED***({size // 1024***REMOVED*** КБ)[/***REMOVED***")
            else:
                self._items.append(("dir", p))
                labels.append(f"📁 {p.name***REMOVED***/")
        for label in labels:
            lst.append(ListItem(Label(label)))

    @on(ListView.Selected)
    def _on_selected(self, event: ListView.Selected) -> None:
        event.stop()
        lst = self.query_one("#fb-list", ListView)
        idx = lst.index if lst.index is not None else 0
        if idx < 0 or idx >= len(self._items):
            return
        kind, payload = self._items[idx***REMOVED***
        if kind == "manual":
            self.dismiss(MANUAL_PATH)
        elif kind == "up":
            self._dir = self._dir.parent
            self._load_dir()
        elif kind == "dir":
            self._dir = payload
            self._load_dir()
        elif kind == "file":
            self.dismiss(str(payload))

    def action_goto_favorite(self, name: str) -> None:
        """Быстрый переход в избранную папку ~/storage/<name> одной клавишей."""
        target = Path.home() / "storage" / name
        if target.is_dir():
            self._dir = target
            self._load_dir()
            return
        label = self._FAVORITE_DIRS.get(name, name)
        self.notify(
            f"Папки нет: {target***REMOVED*** — сделай termux-setup-storage (доступ к {label***REMOVED***)",
            severity="warning",
            timeout=3,
        )

    def action_up(self) -> None:
        if self._dir.parent != self._dir and str(self._dir) != "/":
            self._dir = self._dir.parent
            self._load_dir()

    def action_close(self) -> None:
        self.dismiss(None)


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
    #chat-search {
        border: solid #4fc3f7;
        margin: 0 1;
        background: #1a1a2e;
        color: #e0e0e0;
    ***REMOVED***
    #chat-search-count {
        color: #4fc3f7;
        padding: 0 1;
        text-style: italic;
    ***REMOVED***
    #transfer-progress {
        display: none;
        margin: 0 1;
        height: 1;
        color: #4fc3f7;
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
    #btn-attach, #btn-gif {
        width: auto;
        min-width: 9;
        height: 3;
        margin-right: 1;
        background: #24283b;
        border: solid #4fc3f7;
        color: #4fc3f7;
        text-style: bold;
    ***REMOVED***
    #btn-attach:focus, #btn-gif:focus {
        border: double #7dc4ff;
        color: #7dc4ff;
    ***REMOVED***
    #btn-voice {
        width: auto;
        min-width: 9;
        height: 3;
        margin-right: 1;
        background: #24283b;
        border: solid #35d07f;
        color: #35d07f;
        text-style: bold;
    ***REMOVED***
    #btn-voice:focus {
        border: double #7dffa8;
        color: #7dffa8;
    ***REMOVED***
    #btn-video {
        width: auto;
        min-width: 9;
        height: 3;
        margin-right: 1;
        background: #24283b;
        border: solid #ff9e64;
        color: #ff9e64;
        text-style: bold;
    ***REMOVED***
    #btn-video:focus {
        border: double #ffc9a0;
        color: #ffc9a0;
    ***REMOVED***
    ListView:focus {
        border: solid #4fc3f7;
    ***REMOVED***
    """

    BINDINGS = [
        Binding("ctrl+f", "toggle_search", "Поиск", show=True),
        Binding("ctrl+e", "toggle_favorite", "⭐ Избр.", show=True),
        Binding("ctrl+r", "refresh", "Обновить", show=True),
        Binding("ctrl+o", "attach", "📎 Файл", show=True),
        Binding("a", "attach", "📎 Файл", show=True),
        Binding("ctrl+g", "toggle_mode", "🔀 Режим", show=True),
        Binding("ctrl+t", "focus_input", "Писать", show=True),
        Binding("ctrl+x", "quit", "Выход", show=True),
        Binding("ctrl+q", "quit", "Выход", show=False),
        Binding("escape", "escape", "", show=False),
    ***REMOVED***

    def __init__(self):
        super().__init__()
        self._tg: ThreadedTGClient | None = None
        self._tg_connected = False
        self._cache: MessageCache | None = None
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
        self.run_worker(self._init_cache())
        self.run_worker(self._connect_bg())

    async def _init_cache(self) -> None:
        """Открыть SQLite-кэш (офлайн-история). Не блокирует подключение."""
        cache = MessageCache(CACHE_DB)
        try:
            await cache.open()
        except Exception:
            self._cache = None
            return
        # Очистка по сроку хранения: сообщения старше cache_days дней удаляются.
        # Поверх cache_cap (лимит на чат) это защищает от вечного копления
        # старых записей в чатах, куда давно не заходили.
        try:
            days = int(_get_setting("cache_days"))
            if days > 0:
                removed = await cache.prune_older_than(days)
                if removed:
                    self.notify(f"🧹 Кэш: удалено {removed***REMOVED*** сообщений старше {days***REMOVED*** дн.", timeout=3)
        except Exception:
            pass
        # Присваиваем ТОЛЬКО после успешного open(): параллельный _load_chats
        # не должен дёргать полуоткрытый кэш (гонка при быстром коннекте TG)
        self._cache = cache

    def _spin(self) -> None:
        self._spinner_idx = (self._spinner_idx + 1) % len(SPINNER)
        self.sub_title = f"{SPINNER[self._spinner_idx***REMOVED******REMOVED*** Подключение..."

    def _stop_spinner(self) -> None:
        if self._spinner_timer is not None:
            self._spinner_timer.stop()
            self._spinner_timer = None

    # ── TG bridge ──────────────────────────────────────────

    async def _await_tg(self, future):
        return await asyncio.wrap_future(future)

    async def _connect_bg(self) -> None:
        try:
            self._tg = ThreadedTGClient()
            authorized = await self._await_tg(self._tg.connect_async())
            if not authorized:
                self._stop_spinner()
                self.sub_title = "⚠️ Нужна авторизация — сначала: python test_tg.py"
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
            msg = str(e)
            if "database is locked" in msg.lower():
                # Типичная причина: второй экземпляр приложения держит
                # SQLite-сессию. Раньше это выглядело как «кнопки не реагируют».
                self.sub_title = "🔒 База занята другим экземпляром — закрой его (Ctrl+Q) и перезапусти"
            else:
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
            if self._cache is not None:
                await self._cache.save_dialogs(dialogs)
        except Exception as e:
            if self._cache is not None:
                cached = await self._load_cached_dialogs()
                if cached:
                    screen.show_dialogs(cached)
                    self.notify("🕓 Офлайн: показаны кэшированные чаты", timeout=3)
                    return
            screen.show_error(str(e))
        finally:
            self._refreshing = False

    async def _load_cached_dialogs(self) -> list:
        """Восстановить список чатов из кэша (офлайн)."""
        from types import SimpleNamespace
        out = [***REMOVED***
        for row in await self._cache.get_dialogs(limit=50):
            out.append(
                SimpleNamespace(
                    id=row["id"***REMOVED***,
                    name=row["name"***REMOVED***,
                    unread_count=row["unread_count"***REMOVED***,
                    entity=None,
                    input_entity=None,
                )
            )
        return out

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
        """Enter — открыть чат или скачать/открыть медиа из сообщения."""
        if event.list_view.id == "chat-list":
            # Открываем чат даже офлайн — история подтянется из кэша
            idx = event.list_view.index
            screen = self.screen
            if not isinstance(screen, ChatListScreen):
                return
            dialog = screen.get_dialog(idx)
            if dialog is None:
                return
            self.run_worker(self.push_screen(ChatViewScreen(dialog, self)))
        elif event.list_view.id == "msg-list":
            if not self._tg_connected:
                return
            screen = self.screen
            if not isinstance(screen, ChatViewScreen):
                return
            m = screen.get_message(event.list_view.index)
            if m is not None and media_hint(m):
                self.run_worker(screen.download_and_open(m))

    # ── Действия ───────────────────────────────────────────

    def action_toggle_search(self) -> None:
        screen = self.screen
        if isinstance(screen, ChatListScreen):
            screen.toggle_search()
        elif isinstance(screen, ChatViewScreen):
            screen.action_toggle_msg_search()

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
            if screen._capturing:
                screen.cancel_capture()
                return
            if screen._recording:
                screen.cancel_recording()
                return
            if screen._attach_mode:
                screen.cancel_attach()
                return
            si = screen.query_one("#chat-search", Input)
            if si.display:
                screen.action_toggle_msg_search()
            else:
                screen.action_go_back()

    def action_focus_input(self) -> None:
        screen = self.screen
        if isinstance(screen, ChatViewScreen):
            screen.action_focus_input()

    def action_attach(self) -> None:
        screen = self.screen
        if isinstance(screen, ChatViewScreen):
            screen.action_attach()
        elif not isinstance(screen, FileBrowserScreen):
            self.notify("Сначала открой чат, чтобы отправить файл", timeout=2)

    def action_toggle_mode(self) -> None:
        """Переключить режим «лайт»/«адванс» на лету (сохраняется в settings.json).

        Лайт — чисто переписка (без поиска, GIF, отправки файлов);
        адванс — все функции."""
        new_mode = "light" if not _is_light_mode() else "advance"
        _set_setting("mode", new_mode)
        label = "лайт (чисто переписка)" if new_mode == "light" else "адванс (все функции)"
        self.notify(f"🔀 Режим: {label***REMOVED***", timeout=3)
        screen = self.screen
        if isinstance(screen, ChatViewScreen):
            screen._apply_mode_ui()

    @staticmethod
    def open_file(path) -> None:
        """Открыть файл внешним просмотрщиком (termux-open / xdg-open).

        Путь резолвится в реальный (/storage/emulated/0/...): системные
        приложения Android часто не открывают файлы через Termux-симлинк
        ~/storage/... и показывают «повреждено».
        """
        try:
            real = os.path.realpath(str(path))
        except Exception:
            real = str(path)
        opener = shutil.which("termux-open") or shutil.which("xdg-open")
        if opener is None:
            return
        try:
            subprocess.Popen(
                [opener, real***REMOVED***,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def action_quit(self) -> None:
        self._stop_spinner()
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
        self.run_worker(self._shutdown_all())

    async def _shutdown_all(self) -> None:
        """Закрыть кэш и TG-поток, затем выйти."""
        if self._cache is not None:
            try:
                await self._cache.close()
            except Exception:
                pass
            self._cache = None
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
