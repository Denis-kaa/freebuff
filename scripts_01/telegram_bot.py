"""Telegram bot frontend for Freebuff.

Routes incoming Telegram messages to a ContextManager session so the user can
interact with the project from Telegram.  To start the bot:

    TELEGRAM_BOT_TOKEN=xxx python scripts_01/telegram_bot.py

The bot stores every chat as a ContextManager session, supports a few slash
commands, and answers via the configured LLM through ModelGateway.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
}
import sys
import uuid
}
from typing import Any

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from scripts_01.context_manager import ContextManager
from scripts_01.tgbot_base import BaseTGBot, load_dotenv
from scripts_01._workspace_onboarding import (
    OnboardingState,
    STATE_DONE,
    STATE_ASKING_PROJECT,
    STATE_ASKING_PICK_PROJECT,
    STATE_ASKING_IDEA,
    STATE_ASKING_WORKSPACE_NAME,
    STATE_CONFIRM_WORKSPACE,
    STATE_NONE,
    TXT_GREETING,
    TXT_ASKING_PROJECT,
    TXT_ASKING_IDEA,
    TXT_ASKING_WORKSPACE_NAME,
    TXT_WORKSPACE_CREATED,
    can_cancel,
    clear_state as clear_onboarding_state,
    default_state as default_onboarding_state,
    list_pompts_11_corpus,
    list_workspaces_for_chat,
    load_state as load_onboarding_state,
    register_workspace as register_onboarding_workspace,
    render_pick_list,
    save_state as save_onboarding_state,
)
from core_02.workspace_registry import (
    PrivacyViolationError,
    WorkspaceRegistry,
)
from datetime import datetime
from core_02.telegram_contract import (
    SAVED_MESSAGES_CHAT_ID,
    LITVINOV_CHAT_ID,
    report_to_saved_messages,
    report_to_alex_litvinov,
)

# Make project root importable
WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

try:
    from scripts_01.model_gateway import ModelGateway
except ImportError:
    ModelGateway = None  # type: ignore[misc, assignment]


load_dotenv(WORKSPACE / ".env")

# In production, restrict this to your own chat IDs.
ALLOWED_CHAT_IDS: set[int] = set()
if os.environ.get("ALLOWED_CHAT_IDS"):
    ALLOWED_CHAT_IDS = {
        int(cid.strip())
        for cid in os.environ["ALLOWED_CHAT_IDS"].split(",")
        if cid.strip()
    }


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("freebuff.telegram_bot")


class TelegramFreebuffBot(BaseTGBot):
    """Simple Telegram frontend backed by ContextManager.

    Наследует общую Telegram-инфраструктуру (BaseTGBot): .env-загрузку,
    токен, ApplicationBuilder, polling-цикл и error handler (DEBT-007).
    """

    logger = logging.getLogger("freebuff.telegram_bot")

    def __init__(self, workspace: str | Path) -> None:
        super().__init__(workspace)
        self.cm = ContextManager(str(self.workspace))
        self._active_session: dict[int, str] = {}
        self._model_gateway: Any | None = None
        # CON-19 single-source-of-truth: registry shared с scan_projects.py — additive
        # таблицы в data_13/context.db. Per-bot-instance lifetime (testable via tmp_path
        # в bot fixture с автоматической DB isolation).
        self.registry = WorkspaceRegistry(self.workspace / "data_13" / "context.db")
        self._load_active_sessions()

    # ── Onboarding helpers (Phase 5.4, closes OQ26-Q31 from PLATFORM.md §12) ──

    def onboarding_state(self, chat_id: int) -> OnboardingState:
        """Lazy load + cache per-chat onboarding state from data_13/telegram_onboarding.json."""
        return load_onboarding_state(self.workspace, chat_id)

    def save_onboarding(self, chat_id: int, state: OnboardingState) -> None:
        save_onboarding_state(self.workspace, chat_id, state)

    def reset_onboarding(self, chat_id: int) -> None:
        clear_onboarding_state(self.workspace, chat_id)

    @property
    def model_gateway(self) -> Any | None:
        """Lazy, cached ModelGateway instance."""
        if self._model_gateway is None and ModelGateway is not None:
            self._model_gateway = ModelGateway()
        return self._model_gateway

    def _session_id(self, chat_id: int) -> str:
        # Deterministic but stable mapping from chat to session.
        return f"telegram-{chat_id}"

    def _get_or_create_session(self, chat_id: int) -> str:
        if chat_id in self._active_session:
            return self._active_session[chat_id]
        session_id = self._session_id(chat_id)
        if self.cm.get_session(session_id) is None:
            self.cm.start_session(
                session_id=session_id,
                project="telegram_bot",
                topic=f"telegram chat {chat_id}",
            )
        self._active_session[chat_id] = session_id
        return session_id

    def _record_message(self, chat_id: int, role: str, text: str) -> None:
        session_id = self._get_or_create_session(chat_id)
        self.cm.add_message(
            session_id=session_id,
            role=role,
            content=text,
            auto_checkpoint_interval=0,
        )

    def _persist_active_sessions(self) -> None:
        """Persist the active session mapping to a small JSON file."""
        path = self.workspace / "data_13" / "telegram_bot_sessions.json"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({str(k): v for k, v in self._active_session.items()}),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to persist active sessions")

    def _load_active_sessions(self) -> None:
        """Load the active session mapping from disk."""
        path = self.workspace / "data_13" / "telegram_bot_sessions.json"
        try:
            if not path.exists():
                return
            data = json.loads(path.read_text(encoding="utf-8"))
            self._active_session = {int(k): v for k, v in data.items()}
        except Exception:
            logger.exception("Failed to load active sessions")

    def _active_session_id(self, chat_id: int) -> str:
        """Return the currently active session ID for a chat, falling back to DB."""
        if chat_id in self._active_session:
            return self._active_session[chat_id]
        # Fallback to the deterministic legacy session ID.
        return self._session_id(chat_id)

    def _session_status_text(self, chat_id: int) -> str:
        session_id = self._active_session_id(chat_id)
        session = self.cm.get_session(session_id)
        if session is None:
            return "Сессия ещё не создана. Отправь любое сообщение."
        return (
            f"🆔 Session: `{session.session_id[:8]}`\n"
            f"📁 Project: {session.project}\n"
            f"💬 Messages: {session.message_count}\n"
            f" Tokens (est): {session.token_estimate}\n"
            f" Updated: {session.updated_at[:19]}"
        )

    def _agent_reply(self, chat_id: int, text: str) -> str:
        """Generate an LLM reply using the project ModelGateway (if available).

        Falls back to a helpful local response when no API keys/models are
        configured, so the bot is never completely silent.
        """
        session_id = self._get_or_create_session(chat_id)
        messages = self._build_messages(session_id, text)

        gw = self.model_gateway
        if gw is None:
            return self._fallback_reply()

        try:
            response = gw.generate(
                model=os.environ.get("TELEGRAM_BOT_MODEL", "deepseek-v4-flash"),
                messages=messages,
                fallback=os.environ.get("TELEGRAM_BOT_FALLBACK_MODEL"),
                temperature=float(os.environ.get("TELEGRAM_BOT_TEMPERATURE", "0.7")),
            )
            return str(response.content or "").strip() or self._fallback_reply()
        except Exception as exc:
            logger.exception("ModelGateway failed for chat %s", chat_id)
            return (
                "🤖 Buffy (Telegram mode)\n\n"
                f"⚠️ ModelGateway error: {exc}\n\n"
                "Check TELEGRAM_BOT_TOKEN / model env vars, or run local Ollama."
            )

    def _build_messages(self, session_id: str, text: str) -> list[dict[str, str]]:
        """Build OpenAI-style message history for the current session."""
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are Buffy, the strategic coding assistant for the Freebuff "
                    "AI Engineering Workspace. You are chatting with the user via Telegram. "
                    "Be concise, helpful, and action-oriented. If the user asks about code, "
                    "files, or architecture, reason step by step and offer concrete next steps."
                ),
            }
        ]
        for msg in self.cm.get_messages(session_id, limit=20):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role not in ("user", "assistant", "system"):
                continue
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": text})
        return messages

    def _fallback_reply(self) -> str:
        return (
            " Buffy (Telegram mode)\n\n"
            "Я получил твоё сообщение и сохранил в сессию.\n"
            "ModelGateway недоступен (нет ключей или не установлены зависимости).\n\n"
            "Доступные команды:\n"
            "/status — статус сессии\n"
            "/new — начать новую сессию\n"
            "/session — ID текущей сессии\n"
            "/task — поставить задачу в очередь промтов\n"
            "/queue — список задач в очереди (user/running/done/failed)\n"
            "/workspace — список workspace-ов (per chat_id)"
        )


# ── Handlers ───────────────────────────────────────────────────

_bot = TelegramFreebuffBot(WORKSPACE)


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/start` начинает workspace-aware onboarding (опрос из 5 шагов по PLATFORM.md §3).

    FSM: NONE → ASKING_PROJECT → (ASKING_PICK_PROJECT | ASKING_IDEA)
        → ASKING_WORKSPACE_NAME → CONFIRM_WORKSPACE → DONE.
    /cancel на любом шаге → reset state в NONE (не теряет user data).
    """
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    if chat_id is None:
        return
    _bot._record_message(chat_id, "system", "/start")
    state = OnboardingState(state=STATE_ASKING_PROJECT)
    _bot.save_onboarding(chat_id, state)

    workspaces = list_workspaces_for_chat(_bot.workspace, chat_id)
    msg = TXT_GREETING
    if workspaces:
        ws_names = ", ".join(f"`{w.get('name', '?')}`" for w in workspaces)
        msg += f"\n\n📁 У тебя уже есть workspace-ы: {ws_names}. Можно добавить ещё."
    await update.effective_message.reply_text(  # type: ignore[union-attr]
        msg + "\n\n" + TXT_ASKING_PROJECT
    )


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/cancel` — прервать онбординг на любом шаге (кроме NONE/DONE)."""
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    if chat_id is None:
        return
    state = _bot.onboarding_state(chat_id)
    if state.state == STATE_NONE or state.state == STATE_DONE:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            "ℹ️ Ты сейчас не в онбординге — можно отправить задачу в свободной форме."
        )
        return
    _bot.reset_onboarding(chat_id)
    await update.effective_message.reply_text(  # type: ignore[union-attr]
        "❌ Онбординг прерван. Отправляй обычные задачи — они пойдут в свободную сессию."
    )


async def _status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    text = _bot._session_status_text(chat_id)
    await update.effective_message.reply_text(text)  # type: ignore[union-attr]


async def cmd_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin /notify — репортует сообщение в Избранное (Saved Messages) через TGClient.

    Wire‑in для LESSONS §10 TG‑contract: реально использует SAVED_MESSAGES_CHAT_ID + report_to_saved_messages
    из core_02/telegram_contract.py (post CAN‑3 closure v5.40.0).
    Usage: /notify <message>
    """
    text = " ".join(context.args or []).strip()
    if not text:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            "Usage: /notify <message>\n"
            "(сообщение попадёт в Избранное через TGClient send_message)"
        )
        return

    wrapped = f"📨 [Freebuff admin notify] (от chat_id={update.effective_chat.id})\n\n{text}"
    try:
        msg_id = await report_to_saved_messages(wrapped)
        if msg_id is None:
            await update.effective_message.reply_text(  # type: ignore[union-attr]
                "⚠️ Не доставлено в Избранное — TGClient недоступен или сессия не авторизована. "
                "Проверь `python scripts_01/tg_smoke.py` для diagnostics."
            )
            return
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            f"✅ Доставлено в Избранное (chat_id={SAVED_MESSAGES_CHAT_ID}). "  # type: ignore[union-attr]
            f"msg_id={msg_id}"
        )
    except Exception as exc:
        logger.exception("/notify failed")
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            f"❌ Ошибка notify: {exc}"
        )


async def cmd_notify_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin /notify_client — репортует сообщение клиенту (Александру Литвинову) через TGClient.

    Закрывает wire‑in задачу: connects к LESSONS §10 TG‑contract. Использует
    report_to_alex_litvinov из core_02/telegram_contract. Используйте cautiously —
    сообщение уходит реальному клиенту @alexlitvinov.
    Usage: /notify_client <message>
    """
    text = " ".join(context.args or []).strip()
    if not text:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            "Usage: /notify_client <message>\n"
            "(сообщение попадёт к клиенту — Александру Литвинову, chat_id=1063827731)"
        )
        return

    wrapped = f"📨 [Freebuff notify → клиент] (от admin chat_id={update.effective_chat.id})\n\n{text}"
    try:
        msg_id = await report_to_alex_litvinov(wrapped)
        if msg_id is None:
            await update.effective_message.reply_text(  # type: ignore[union-attr]
                "⚠️ Не доставлено клиенту — TGClient недоступен или сессия не авторизована."
            )
            return
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            f"✅ Доставлено клиенту (chat_id={LITVINOV_CHAT_ID}). msg_id={msg_id}"
        )
    except Exception as exc:
        logger.exception("/notify_client failed")
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            f"❌ Ошибка notify_client: {exc}"
        )


# ── Module-level registry для fire-and-forget BG tasks (anti-GC, v5.83.0) ──
# `asyncio.create_task()` создания без strong reference рискуют GC'нуться
# до завершения. Anchorнг в `_pending_reapers` keeps the reaper alive.
_pending_reapers: "set[asyncio.Task[None]]" = set()


async def _reap_subprocess_safe(proc: "asyncio.subprocess.Process") -> None:
    """Safely wait on subprocess; auto-unregister from `_pending_reapers`.

    Companion for dual-path TG → Buffy dispatch (v5.83.0). Fire-and-forget
    waiter; written + registered at call-site via `_pending_reapers.add(...)`.
    Output routing handled at spawn-site (per-task log file in `logs_14/`).
    Catch is narrow: ONLY swallow `Exception`, NOT `CancelledError` / `KeyboardInterrupt`
    (those must propagate so the asyncio reactor can shut down cleanly).
    """
    try:
        await proc.wait()
    except Exception:
        # Anti-zombie: never let subprocess leak; surface catastrophic errors via logger.
        logger.warning(
            "_reap_subprocess_safe: subprocess.wait() raised for pid=%s",
            getattr(proc, "pid", "?"),
        )
    finally:
        current = asyncio.current_task()
        if current is not None:
            _pending_reapers.discard(current)




async def cmd_answer(update, context) -> None:
    """Task 1 (promt 61): TG `/answer <task_id> <text>` — резюм running-resumable задачи.

    Usage: `/answer task_<timestamp>_<uuid> the missing context is X`.
    Reply — статус (успех / `not found in running/` / `not awaiting answer (status=...)`).
    """
    if update is None or update.message is None:
        return

    chat = update.effective_chat
    if chat is None:
        return

    # Парсим args: /answer <task_id> <text...>
    args = context.args if context and getattr(context, "args", None) else []
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Использование: /answer <task_id> <текст ответа>\n"
            "Task 1 (promt 61): отвечает на clarification Buffered-on-resumable задачи.",
        )
        return

    task_id = args[0]
    answer_text = " ".join(args[1:])

    # Lazy import (avoid cyclic / slow startup)
    try:
        from scripts_01.prompt_dispatcher import process_answer
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка импорта: {e}")
        return

    result = process_answer(task_id, answer_text)
    if result.get("ok"):
        await update.message.reply_text(
            f"✅ Answer принят: task_id `{result['task_id']}`\n"
            f"**{result['old_status']} → {result['new_status']}**\n"
            f"Iteration: {result['old_iteration']} → {result['new_iteration']}\n"
            f"Следующий cron-тик возмёт задачу и передаст answer в Buffalo.",
        )
    else:
        await update.message.reply_text(
            f"❌ {result.get('error', 'unknown error')}\n"
            f"Task id: `{result.get('task_id', '?')}`",
        )


async def cmd_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/task <текст>` — real-time задача Баффи (dual-path, v5.83.0).

    Пишет файл в `pompts_11/user/` и СРАЗУ spawn'ит `prompt_dispatcher.py --once`
    в фоновом asyncio subprocess (fire-and-forget — НЕ блокирует TG reactor).
    Cron остаётся safety-net: подхватывает (a) если spawn упал, (b) каждые ≤5 минут
    в любом случае. Output dispatcher'а routed в `logs_14/tg_spawn_<taskid>.log`.

    Anti-OOM: dispatcher использует `wrapper.launch_and_wait` phase-based.
    Race-safe: атомарный rename lock внутри `move_to_status` — параллельный cron
    spawn получит FileNotFoundError → корректный `skipped_locked` (см. dispatch_one).

    Note (Fix 1 from review v5.83.0): сообщение "📥 Задача добавлена" — НЕ "Запущена".
    Если cron подхватит раньше (race window <=~0.1s), финальный отчёт всё равно
    придёт в TG через dispatcher'ский `_send_tg_report` → пользователь видит итог
    независимо от того, кто именно обработал.

    Usage: /task <текст задачи>
           /task model:2: <текст> — выбор модели по позиции в стартовом списке
           freebuff (0/auto = DeepSeek V4 Flash · free безлимит; 1..5 = другие)
    """
    text = " ".join(context.args or []).strip()
    if not text:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            "Usage: /task <текст задачи>\n"
            "/task model:0: <текст> — модель по позиции в списке выбора freebuff\n"
            "  · 0 / auto — DeepSeek V4 Flash (free, безлимит, рекомендованная)\n"
            "  · 1..5 — позиция в списке (premium-модели, лимит сессий)\n"
            "(задача попадёт в pompts_11/user/ и обработается в real-time)"
        )
        return

    # Выбор модели из префикса "model:<позиция|алиас>:" (v5.88.0)
    model = "auto"
    m_model = re.match(
        r"^\s*model\s*:\s*([A-Za-z0-9_.-]+)\s*:\s*(.+)$", text, re.DOTALL | re.IGNORECASE
    )
    if m_model:
        model = m_model.group(1).strip().lower()
        text = m_model.group(2).strip()

    try:
        from scripts_01.prompt_queue import write_user_prompt

        path = write_user_prompt(
            text,
            chat_id=update.effective_chat.id,  # type: ignore[union-attr]
            source="telegram",
            model=model,
        )

        # ── DUAL-PATH real-time spawn ───────────────────────────────
        # If spawn failed → cron safety-net (`*/5 * * * *` prompt_dispatch.sh)
        # подхватит ≤5 минут. Output routed в per-task log для диагностики.
        spawn_status = "spawned (real-time)"
        log_path: "Path | None" = None
        try:
            freebuff_root = Path(__file__).resolve().parent.parent
            dispatcher_script = freebuff_root / "scripts_01" / "prompt_dispatcher.py"
            logs_dir = freebuff_root / "logs_14"
            logs_dir.mkdir(exist_ok=True)
            log_path = logs_dir / f"tg_spawn_{path.stem}.log"
            log_fd = open(log_path, "w", encoding="utf-8")  # routing diagnostic per-task
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(dispatcher_script),
                    "--once",
                    cwd=str(freebuff_root),
                    stdout=log_fd,
                    stderr=log_fd,
                )
            except Exception:
                # Anti-leak: if fork fails before inheriting fd, parent MUST close.
                log_fd.close()
                raise
            log_fd.close()  # SUCCESS-PATH CLOSE ONLY -- exception branch above already closed; do NOT add another close here on success path (v5.84.0 polish: explicit comment prevents future double-close)
            # Anchor reaper in module-level `_pending_reapers` (anti-GC).
            reaper = asyncio.create_task(_reap_subprocess_safe(proc))
            _pending_reapers.add(reaper)
        except Exception as spawn_exc:
            # spawn-failure → cron safety-net подхватит ≤5 минут (никогда не fail full).
            spawn_status = f"deferred → cron safety-net (≤5 минут): {spawn_exc}"

        log_note = f"\nДиагностика: `logs_14/{log_path.name}`" if log_path else ""

        await update.effective_message.reply_text(  # type: ignore[union-attr]
            f"📥 Задача добавлена в очередь (dual-path v5.83.0).\n"
            f"Task ID: `{path.stem}`\n"
            f"Model: `{model}`\n"
            f"Spawn: {spawn_status}\n"
            f"Файл: `{path.name}`\n"
            f"Отчёт придёт в TG (от Баффи) после `wrapper.launch_and_wait`.{log_note}"
        )
    except Exception as exc:
        logger.exception("/task failed")
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            f"❌ Ошибка при постановке в очередь: {exc}"
        )


async def _new_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    old_session_id = _bot._active_session.pop(chat_id, _bot._session_id(chat_id))
    try:
        _bot.cm.complete_session(old_session_id)
    except Exception:
        pass
    # Start a fresh session with a new unique ID.
    new_session_id = f"telegram-{chat_id}-{uuid.uuid4().hex[:8]}"
    _bot.cm.start_session(
        session_id=new_session_id,
        project="telegram_bot",
        topic=f"telegram chat {chat_id}",
    )
    _bot._active_session[chat_id] = new_session_id
    _bot._persist_active_sessions()
    await update.effective_message.reply_text(  # type: ignore[union-attr]
        "🆕 Новая сессия создана.\n" + _bot._session_status_text(chat_id)
    )


async def _session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    session_id = _bot._active_session_id(chat_id)
    await update.effective_message.reply_text(  # type: ignore[union-attr]
        f"Текущая сессия: `{session_id}`"
    )


async def _notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Модульный wrapper — вызов cmd_notify (module‑level, после fix ship‑blocker)."""
    await cmd_notify(update, context)


async def _notify_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Модульный wrapper — вызов cmd_notify_client (module‑level, после fix ship‑blocker)."""
    await cmd_notify_client(update, context)


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    user_text = (update.message.text or "") if update.message else ""
    if chat_id is None:
        return
    if not user_text:
        if update.effective_message:
            await update.effective_message.reply_text(
                "Отправь текстовое сообщение, и я отвечу."
            )
        return

    # ── Onboarding routing (Phase 5.4): если state != NONE/DONE, ведём FSM ──
    state = _bot.onboarding_state(chat_id)
    if state.state not in (STATE_NONE, STATE_DONE):
        await _route_onboarding_text(update, context, chat_id, user_text, state)
        return

    try:
        await context.bot.send_chat_action(chat_id, action="typing")
    except Exception:
        pass

    _bot._record_message(chat_id, "user", user_text)
    reply = _bot._agent_reply(chat_id, user_text)
    _bot._record_message(chat_id, "assistant", reply)

    await update.effective_message.reply_text(reply)  # type: ignore[union-attr]


async def _route_onboarding_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_text: str,
    state: OnboardingState,
) -> None:
    """Route user text into the onboarding FSM (per PLATFORM.md §3).

    FSM:
      ASKING_PROJECT          → «да» → ASKING_PICK_PROJECT (list pompts_11)
                              → «нет» → ASKING_IDEA
      ASKING_PICK_PROJECT     → номер 1..N → ASKING_WORKSPACE_NAME
      ASKING_IDEA             → 1-2 предложения → ASKING_WORKSPACE_NAME
      ASKING_WORKSPACE_NAME   → имя (1-64) → register + DONE
    """
    text = user_text.strip().lower()
    reply = ""
    next_state = state.state
    new_source = state.source
    new_candidates = list(state.candidates)
    new_workspace_name = state.workspace_name

    if next_state == STATE_ASKING_PROJECT:
        if text in ("да", "yes", "y", "есть", "есть проект"):
            candidates = list_pompts_11_corpus(_bot.workspace, top_n=5)
            if not candidates:
                reply = (
                    "📂 В `pompts_11/` пока нет кандидатов.\n"
                    "Переходим к идее — опиши её одним предложением:"
                )
                next_state = STATE_ASKING_IDEA
            else:
                reply = render_pick_list(candidates)
                new_candidates = [c["stem"] for c in candidates]
                next_state = STATE_ASKING_PICK_PROJECT
        elif text in ("нет", "no", "n", "не", "нету", "неа"):
            reply = TXT_ASKING_IDEA
            next_state = STATE_ASKING_IDEA
        else:
            reply = (
                "⚠️ Ответь «да» или «нет» (или `/cancel` для выхода).\n\n"
                + TXT_ASKING_PROJECT
            )

    elif next_state == STATE_ASKING_PICK_PROJECT:
        error_msg = ""
        try:
            idx = int(text) - 1
            if 0 <= idx < len(new_candidates):
                chosen_stem = new_candidates[idx]
                new_source = f"pompts_11/{chosen_stem}"
                reply = TXT_ASKING_WORKSPACE_NAME
                next_state = STATE_ASKING_WORKSPACE_NAME
            else:
                error_msg = f"Номер должен быть от 1 до {len(new_candidates)}."
        except ValueError:
            error_msg = "Введи номер кандидата (например, `1`)."
        if error_msg:
            reply = f"⚠️ {error_msg}\n" + render_pick_list(
                list_pompts_11_corpus(_bot.workspace, top_n=5)
            )

    elif next_state == STATE_ASKING_IDEA:
        if 1 <= len(user_text.strip()) <= 200:
            new_source = f"idea:{user_text.strip()[:120]}"
            reply = TXT_ASKING_WORKSPACE_NAME
            next_state = STATE_ASKING_WORKSPACE_NAME
        else:
            reply = (
                "⚠️ Опиши идею в 1-2 предложениях (до 200 символов).\n"
                + TXT_ASKING_IDEA
            )

    elif next_state == STATE_ASKING_WORKSPACE_NAME:
        name = user_text.strip()
        if not name or len(name) > 64:
            reply = (
                "⚠️ Имя workspace должно быть 1-64 символа.\n"
                + TXT_ASKING_WORKSPACE_NAME
            )
        else:
            # Дубль-имён dedup: если workspace с таким именем уже есть
            # для chat_id, добавляем суффикс " (N)" — UX safeguard
            # против случайных дублей.
            existing_names = {
                w.get("name", "")
                for w in list_workspaces_for_chat(_bot.workspace, chat_id)
            }
            final_name = name
            counter = 2
            while final_name in existing_names and counter <= 99:
                suffix = f" ({counter})"
                base = name if len(name) + len(suffix) <= 64 else name[: 64 - len(suffix)]
                candidate = f"{base}{suffix}"
                # Жёсткий clamp: даже при счётчике 99+ держим ≤ 64 символа
                if len(candidate) > 64:
                    candidate = candidate[:64]
                final_name = candidate
                counter += 1
            new_workspace_name = final_name
            try:
                register_onboarding_workspace(
                    _bot.workspace,
                    chat_id=chat_id,
                    name=final_name,
                    source=new_source,
                )
                # Дополнительно регистрируем в core_02/workspace_registry (SQLite
                # в data_13/context.db) — для cross-system queries и MCP tools.
                # Failure mode: try/except + logger; НЕ rollback JSON успех
                # (CON-21: Telegram UX не должна падать на registry issues).
                project_paths = []
                if new_source.startswith("pompts_11/"):
                    target = (_bot.workspace / new_source).resolve()
                    if target.exists():
                        project_paths = [str(target)]
                    else:
                        logger.warning(
                            "WorkspaceRegistry integration: pompts_11/<stem> %s "
                            "не найден на FS; workspace будет зарегистрирован "
                            "без project_paths (создадим новую corpus-папку позже)",
                            new_source,
                        )
                try:
                    _bot.registry.create_workspace(
                        name=final_name,
                        project_paths=project_paths,
                        description=(
                            f"Onboarded via /start в TG; source={new_source}"
                        ),
                        owner_chat_id=chat_id,
                    )
                except ValueError as exc:
                    # slug collision — create_workspace raises ValueError (NOT PrivacyViolationError)
                    # dedup in _workspace_onboarding guarantees uniqueness within session
                    logger.warning(
                        "WorkspaceRegistry slug collision for chat_id=%s name=%s: %s",
                        chat_id, final_name, exc,
                    )
                except Exception as exc:
                    logger.exception(
                        "WorkspaceRegistry integration failed for chat_id=%s: %s",
                        chat_id, exc,
                    )
                _bot._record_message(
                    chat_id, "system", f"workspace_created:{final_name}"
                )
                reply = TXT_WORKSPACE_CREATED.format(
                    name=final_name,
                    source=new_source,
                    chat_id=chat_id,
                )
                next_state = STATE_DONE
            except Exception as exc:
                logger.exception("register workspace failed")
                reply = (
                    f"❌ Ошибка регистрации workspace: {exc}\n"
                    "Ответь ещё раз, или `/cancel`."
                )

    new_state = OnboardingState(
        state=next_state,
        source=new_source,
        candidates=new_candidates,
        workspace_name=new_workspace_name,
    )
    _bot.save_onboarding(chat_id, new_state)

    if update.effective_message:
        await update.effective_message.reply_text(reply)


async def cmd_workspace(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/workspace [list]` — список workspace-ов пользователя (filter by owner_chat_id).

    Формат ответа (canonical):
        📂 У тебя пока нет зарегистрированных workspace-ов.
    или
        📁 Твои workspace-ы (N):

        🏷 **Name** (slug: slug)
           Source: source_or_path
           Статус: status
           Создан: YYYY-MM-DD HH:MM
           (повтор для следующего workspace)
    """
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    if chat_id is None:
        return
    try:
        workspaces = [
            ws for ws in _bot.registry.list_workspaces()
            if ws.owner_chat_id == chat_id
        ]
    except Exception as exc:
        logger.exception("WorkspaceRegistry.list_workspaces failed")
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            f"❌ Ошибка чтения registry: {exc}"
        )
        return

    if not workspaces:
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            "📂 У тебя пока нет зарегистрированных workspace-ов."
        )
        return

    lines = [f"📁 Твои workspace-ы ({len(workspaces)}):\n"]
    for ws in workspaces:
        try:
            created_dt = datetime.fromtimestamp(ws.created_at).strftime("%Y-%m-%d %H:%M")
        except Exception:
            created_dt = "n/a"
        # Source display: лучший display-name based on project_paths
        source_display = "—"
        if ws.project_paths:
            try:
                rel = Path(ws.project_paths[0]).relative_to(_bot.workspace)
                source_display = str(rel)
            except ValueError:
                source_display = Path(ws.project_paths[0]).name
        lines.append(f"🏷 **{ws.name}** (slug: {ws.slug})")
        lines.append(f"   Source: {source_display}")
        lines.append(f"   Статус: {ws.status}")
        lines.append(f"   Создан: {created_dt}\n")
    await update.effective_message.reply_text("\n".join(lines).strip())  # type: ignore[union-attr]


async def cmd_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/queue [state]` — список промтов в pompts_11/{user,running,done,failed].

    Показывает все каталоги с таймстемпами (mtime файла) и статусом (из
    `**Status:**` header). Аргумент `[state]` (опциональный) — фильтр на
    один каталог: `user|running|done|failed`. Пример:
        /queue          → все 4 каталога сводно
        /queue running  → только running/ (multi-turn resumable)
    Reuse: scripts_01/prompt_queue.{prompts_dir, parse_prompt, queue_counts}.
    TG сообщение truncate до 3800 символов (= safety margin от 4096 TG-limit).
    """
    from scripts_01.prompt_queue import (
        ensure_queue_dirs,
        parse_prompt,
        prompts_dir,
        queue_counts,
    )

    args = context.args or []
    state_filter: str | None = None
    if args:
        candidate = args[0].strip().lower()
        allowed = ("user", "running", "done", "failed")
        if candidate not in allowed:
            await update.effective_message.reply_text(  # type: ignore[union-attr]
                f"Usage: /queue или /queue {('|').join(allowed)}"
            )
            return
        state_filter = candidate

    try:
        ensure_queue_dirs()
        counts = queue_counts()
    except Exception as exc:
        logger.exception("/queue failed at counts")
        await update.effective_message.reply_text(  # type: ignore[union-attr]
            f"❌ Ошибка чтения очереди: {exc}"
        )
        return

    dir_labels = [
        ("user", "📥 user (ожидают)"),
        ("running", "⚙️ running (в работе / resumable)"),
        ("done", "✅ done (выполнено)"),
        ("failed", "❌ failed (ошибка)"),
    ]

    sections: list[str] = [
        f"📊 Очередь задач (promt 48, multi-turn v5.79.0)",
        (
            "{u] user • {r] running • {d] done • {f] failed"
        ).format(
            u=counts.get("pending", 0),
            r=counts.get("running", 0),
            d=counts.get("done", 0),
            f=counts.get("failed", 0),
        ),
    ]

    for subdir_key, label in dir_labels:
        if state_filter and subdir_key != state_filter:
            continue
        sub_dir = prompts_dir() / subdir_key
        try:
            files = sorted(sub_dir.glob("*.md"))
        except OSError as exc:
            sections.append(f"\n{label}: (не удалось прочитать — {exc})")
            continue
        if not files:
            sections.append(f"\n{label}: (пусто)")
            continue
        sections.append(f"\n{label}: {len(files)} файл(ов)")
        for p in files:
            meta = parse_prompt(p)
            # Status badge (multi-turn aware).
            if meta is None:
                sections.append(f"  • `{p.name}` (unparseable)")
                continue
            badge = meta.status or "?"
            if meta.iteration > 1:
                badge = f"{meta.status} iter {meta.iteration}/{meta.max_iterations}"
            # mtime (last filesystem touch) + Created from header.
            try:
                mtime_dt = datetime.fromtimestamp(p.stat().st_mtime).strftime(
                    "%Y-%m-%d %H:%M"
                )
            except OSError:
                mtime_dt = "n/a"
            created = meta.created[:19] if meta.created else "n/a"
            task_short = meta.task_id[:14] if meta.task_id else p.stem
            title_preview = (meta.title or "")[:48]
            sections.append(
                f"  • `{task_short}` [{badge}]\n"
                f"    {title_preview}\n"
                f"    Created: {created} · mtime: {mtime_dt}"
            )

    full = "\n".join(sections)
    # TG message limit 4096; truncate at 3800 with marker.
    if len(full) > 3800:
        full = (
            full[:3800]
            + "\n\n[… truncated — используй `/queue <state>` для фильтра …]"
        )
    await update.effective_message.reply_text(full)  # type: ignore[union-attr]


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Делегирует общему обработчику BaseTGBot (DEBT-007)."""
    await _bot.error_handler(update, context)


# ── Entry point ────────────────────────────────────────────────

def main() -> int:
    if not _bot.token:
        print(
            "❌ TELEGRAM_BOT_TOKEN не задан.\n"
            "Получи токен у @BotFather и запусти:\n"
            "    TELEGRAM_BOT_TOKEN=xxx python scripts_01/telegram_bot.py\n"
            "Или добавь TELEGRAM_BOT_TOKEN в .env файл."
        )
        return 1

    app = _bot.build_application()

    app.add_handler(CommandHandler("start", _start))
    app.add_handler(CommandHandler("status", _status))
    app.add_handler(CommandHandler("new", _new_session))
    app.add_handler(CommandHandler("session", _session))
    app.add_handler(CommandHandler("notify", _notify))
    app.add_handler(CommandHandler("notify_client", _notify_client))
    app.add_handler(CommandHandler("task", cmd_task))
    app.add_handler(CommandHandler("answer", cmd_answer))  # Task 1 (promt 61)
    app.add_handler(CommandHandler("cancel", _cancel))
    app.add_handler(CommandHandler("workspace", cmd_workspace))
    app.add_handler(CommandHandler("queue", cmd_queue))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))
    app.add_error_handler(_error_handler)

    logger.info("Starting Freebuff Telegram bot...")
    return _bot.run_polling(app)


if __name__ == "__main__":
    sys.exit(main())
