"""Workspace-aware onboarding state machine for scripts_01/telegram_bot.py.

5-state FSM per PLATFORM.md §3 (closes OQ26-Q31):
  NONE → ASKING_PROJECT
       → (если «да, есть проект») → ASKING_PICK_PROJECT → ASKING_WORKSPACE_NAME → DONE
       → (если «нет проекта»)    → ASKING_IDEA          → ASKING_WORKSPACE_NAME → DONE
  /cancel сбрасывает state в NONE.

Persistence:
  - State:         data_13/telegram_onboarding.json (chat_id → state dict)
  - Workspaces:    data_13/telegram_workspaces.json (chat_id → [workspace, ...])
  Оба JSON-файла flat + human-readable; error-tolerant: пустой/невалидный →
  default значение (CAN-14 fail-loud на уровне logger, recoverable на уровне runtime).

Reuse:
  - pompts_11/*.md как existing-project corpus (top 5 by mtime desc, +title +snippet)
  - chat_id константы — из core_02/telegram_contract (CON-19 single-source-of-truth)
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
}
from typing import Any

logger = logging.getLogger(__name__)

ONBOARDING_FILENAME = "telegram_onboarding.json"
WORKSPACES_FILENAME = "telegram_workspaces.json"

# ── States ─────────────────────────────────────────────────────

STATE_NONE = "NONE"
STATE_ASKING_PROJECT = "ASKING_PROJECT"
STATE_ASKING_PICK_PROJECT = "ASKING_PICK_PROJECT"
STATE_ASKING_IDEA = "ASKING_IDEA"
STATE_ASKING_WORKSPACE_NAME = "ASKING_WORKSPACE_NAME"
STATE_CONFIRM_WORKSPACE = "CONFIRM_WORKSPACE"
STATE_DONE = "DONE"


@dataclass
class OnboardingState:
    state: str = STATE_NONE
    source: str = ""  # откуда workspace: "pompts_11/047_06_*" или "idea:<user_text>"
    candidates: list[str] = field(default_factory=list)  # stem pompts_11 файлов для ASKING_PICK_PROJECT
    workspace_name: str = ""

    def reset(self) -> None:
        self.state = STATE_NONE
        self.source = ""
        self.candidates = []
        self.workspace_name = ""


def default_state() -> OnboardingState:
    return OnboardingState(state=STATE_NONE)


# ── Persistence ────────────────────────────────────────────────


def load_state(workspace: Path, chat_id: int) -> OnboardingState:
    """Load OnboardingState for chat_id; default_state() if missing/corrupt."""
    path = workspace / "data_13" / ONBOARDING_FILENAME
    if not path.exists():
        return default_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        st_dict = data.get(str(chat_id))
        if not st_dict or not isinstance(st_dict, dict):
            return default_state()
        return OnboardingState(**st_dict)
    except Exception as exc:
        logger.exception("load_state failed for chat_id=%s: %s", chat_id, exc)
        return default_state()


def save_state(workspace: Path, chat_id: int, state: OnboardingState) -> None:
    """Persist OnboardingState for chat_id (durable across bot restarts)."""
    path = workspace / "data_13" / ONBOARDING_FILENAME
    try:
        payload: dict[str, Any] = {}
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    payload = {}
            except Exception:
                payload = {}
        payload[str(chat_id)] = asdict(state)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.exception("save_state failed for chat_id=%s: %s", chat_id, exc)


def clear_state(workspace: Path, chat_id: int) -> None:
    """Remove per-chat state entry. Idempotent: missing key OK."""
    path = workspace / "data_13" / ONBOARDING_FILENAME
    try:
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return
        payload.pop(str(chat_id), None)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.exception("clear_state failed for chat_id=%s: %s", chat_id, exc)


# ── Pompts_11 corpus scan ─────────────────────────────────────


def list_pompts_11_corpus(
    workspace: Path, top_n: int = 5
) -> list[dict[str, Any]]:
    """Scan pompts_11/*.md как existing-project corpus; top-N by mtime desc.

    Возвращает [{filename, stem, title, snippet, mtime}, ...].
    Анти-OOM: только первые top_n файлов и только первые 200 символов каждого.
    """
    corpus_dir = workspace / "pompts_11"
    if not corpus_dir.is_dir():
        logger.warning("pompts_11/ not found at %s", corpus_dir)
        return []
    results: list[dict[str, Any]] = []
    try:
        candidates = [p for p in corpus_dir.glob("*.md")]
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for path in candidates[:top_n]:
            title, snippet = _read_title_snippet(path)
            results.append(
                {
                    "filename": path.name,
                    "stem": path.stem,
                    "title": title,
                    "snippet": snippet,
                    "mtime": path.stat().st_mtime,
                }
            )
    except Exception as exc:
        logger.exception("list_pompts_11_corpus failed: %s", exc)
    return results


def _read_title_snippet(path: Path, snippet_chars: int = 200) -> tuple[str, str]:
    """Извлечь title (первый H1) и snippet (первая непустая строка prose).

    Анти-OOM: читаем только первые 50 строк файла (≈10 KB cap, не больше).
    """
    title = path.stem
    snippet = ""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= 50:
                    break
                s = line.strip()
                if not s:
                    continue
                if s.startswith("# "):
                    title = s[2:].strip() or path.stem
                    continue
                if s.startswith("#") or s.startswith(">"):
                    continue
                snippet = s[:snippet_chars]
                break
    except Exception:
        return path.stem, ""
    return title, snippet


# ── Workspace registry ─────────────────────────────────────────


def register_workspace(
    workspace: Path,
    chat_id: int,
    name: str,
    source: str,
) -> dict[str, Any]:
    """Persist new workspace record for chat_id. Returns the record."""
    path = workspace / "data_13" / WORKSPACES_FILENAME
    record = {
        "name": name,
        "source": source,
        "created_at": time.time(),
        "status": "active",
    }
    try:
        payload: dict[str, Any] = {}
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    payload = {}
            except Exception:
                payload = {}
        chat_workspaces = payload.setdefault(str(chat_id), [])
        if not isinstance(chat_workspaces, list):
            chat_workspaces = []
            payload[str(chat_id)] = chat_workspaces
        chat_workspaces.append(record)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return record
    except Exception as exc:
        logger.exception("register_workspace failed for chat_id=%s: %s", chat_id, exc)
        raise


def list_workspaces_for_chat(
    workspace: Path, chat_id: int
) -> list[dict[str, Any]]:
    """Return list of workspaces registered for chat_id; [] if none."""
    path = workspace / "data_13" / WORKSPACES_FILENAME
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get(str(chat_id), []) if isinstance(payload, dict) else []
    except Exception:
        return []


# ── State machine ──────────────────────────────────────────────


def can_cancel(state_name: str) -> bool:
    """True если пользователь может /cancel из этого состояния."""
    return state_name not in (STATE_NONE, STATE_DONE)


# Тексты для UI (русский) — централизованные константы, чтобы тесты работали стабильно

TXT_GREETING = (
    "👋 Привет! Я — Buffy, твоё рабочее пространство для проектов.\n\n"
    "Помогу вести проекты, не терять контекст и вспоминать важные мысли.\n"
    "С чего начнём?"
)

TXT_ASKING_PROJECT = (
    "📋 **У тебя уже есть готовый или начатый проект,** "
    "который хочешь принести сюда?\n\n"
    "Например, что-то из `pompts_11/`, из заметок, из другого инструмента.\n\n"
    "Ответь одной фразой:\n"
    "  • `да` (или «yes») — покажу кандидатов\n"
    "  • `нет` (или «no») — спрошу про идею\n"
    "  • `/cancel` — выйти из онбординга"
)

TXT_ASKING_PICK_HEADER = "📂 Кандидаты из `pompts_11/` (топ-{n] по свежести):\n\n"
TXT_ASKING_PICK_SEPARATOR = "\n\nВыбери номер (например: `1`) или `/cancel`."

TXT_ASKING_IDEA = (
    "💡 Опиши свою идею одним-двумя предложениями — я потом оформлю её в проект.\n\n"
    "Пример: «приложение, чтобы вести список ремонтов в квартире».\n"
    "Или `/cancel`."
)

TXT_ASKING_WORKSPACE_NAME = (
    "🗂 Как назовём **workspace** (твою «жизнь»), в котором будут жить проекты?\n\n"
    "Примеры: `Работа`, `Дом`, `Учёба`, `Хобби`.\n"
    "Или `/cancel`."
)

TXT_WORKSPACE_CREATED = (
    "✅ Готово!\n\n"
    "📁 **Workspace:** `{name]`\n"
    "📦 **Source:** {source]\n"
    "🆔 **chat_id:** {chat_id]\n\n"
    "Я уже запомнил контекст этого workspace. "
    "Отправляй задачи — каждый раз буду держать в голове, "
    "что мы делали раньше в этой «жизни».\n\n"
    "Команды: `/start` (повторить онбординг), `/cancel` (прервать)."
)


def render_pick_list(candidates: list[dict[str, Any]]) -> str:
    """Render pompts_11 candidates as numbered pick list for Telegram."""
    if not candidates:
        return "📂 В `pompts_11/` пока нет кандидатов.\n\nОтветь `нет` — спрошу про идею. Или `/cancel`."
    lines = [TXT_ASKING_PICK_HEADER.format(n=len(candidates))]
    for i, c in enumerate(candidates, 1):
        title = c.get("title") or c.get("stem")
        snippet = c.get("snippet", "")
        if snippet:
            lines.append(f"**{i}.** {title}\n    _{snippet}_")
        else:
            lines.append(f"**{i}.** {title}")
    lines.append(TXT_ASKING_PICK_SEPARATOR.lstrip("\n"))
    return "\n".join(lines)
