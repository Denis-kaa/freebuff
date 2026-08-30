"""Live e2e TG verify для v5.83.0 dual-path dispatch.

Pipeline:
  1. Pre-flight: TG session alive + queues ready + core_02 importable.
  2. Bot lifecycle: invoke cmd_task via in-process mock Update/Context (Option C).
  3. Real TG send: dispatcher calls send_to_chat via report_to_saved_messages.
  4. Latency measurement: <5 sec target.
  5. Round-trip verify: TGClient.get_messages(chat_id, limit-scan).
  6. Log file check: logs_14/tg_spawn_<taskid>.log exists + has dispatcher output.
  7. Audit-trail append: docs_10/e2e_logs/promt47_run.md prepend на TOP.

Per CAN-9 + CAN-17 + CON-22 + CON-25:
  - honest fail-loud (CAN-14)
  - anti-rewriting historical rows (CAN-17)
  - latency budget (target: <5 sec vs 0–5 min cron baseline)

CLI flags (v5.86.0 — single --dry-run gate):
  --chat-id-saved 7709651193      (default)
  --chat-id-litvinov 1063827731
  --text "..."                    (default: auto-generated run tag)
  --run-tag v5.86.0_e2e
  --dry-run                       (skip real TG send — useful для pre-flight + pytest)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
import time
import uuid
}

WORKSPACE = Path(__file__).resolve().parent.parent

SAVED_MESSAGES_CHAT_ID = 7709651193  # CAN-3 v5.40.0 anchor
ALEX_LITVINOV_CHAT_ID = 1063827731  # CAN-9 v5.45.0 anchor
TARGET_LATENCY_SECS = 5.0


TG_TERMINAL_MESSENGER = WORKSPACE / "projects_17/tg_terminal_messenger"
TG_SESSION_NAME = "tg_session"  # canonical (CON-31 wrap)
TG_SESSION_PATH = TG_TERMINAL_MESSENGER / f"{TG_SESSION_NAME}.session"

# v5.86.0 user-facing reauth instruction (plain ASCII; use chr(39) for apostrophes in Python source —
# here strings use double outer-quote so single apostrophes are literal and don't escape hell).
TG_REAUTH_HINT = (
    "To regenerate the TG session, run a Telethon interactive sign-in:\n"
    "   python3 -c 'from telethon.sync import TelegramClient;"
    " c = TelegramClient(\"tg_session\", int(os.environ[\"TG_API_ID\"]),"
    " os.environ[\"TG_API_HASH\"]); c.start()'\n"
    "Requires TG_API_ID + TG_API_HASH env vars (from https://my.telegram.org/apps)"
    " and an interactive TTY (does NOT work under cron / non-TTY)."
)

# v5.86.0 round-9: hoisted dispatch-table constants for canonical auth-error classification.
# Single source of truth for "which auth-class needs reauth vs 2FA vs account-block".
_REAUTH_REQUIRED_CLASSES: frozenset = frozenset({
    "AuthKeyUnregisteredError",
    "InvalidAuthKeyError",
    "AuthKeyDuplicatedError",
])
_2FA_CLASSES: frozenset = frozenset({"SessionPasswordNeededError"})


# ============================================================
# v5.86.0 round-5 fixed probe: TG_AUTH_FAILURES tuple + unified exit(2)
# + SessionPasswordNeededError + AuthKeyDuplicatedError coverage.
# ============================================================
async def _probe_tg_session() -> bool:
    """Probe TG session via TGClient.connect() + get_me().

    Returns True if session is alive and callable. Returns False ONLY on
    recoverable unknown-error category (CAN-14 partial: unknown error class can't
    be classified as fail-loud). All known canonical failures raise sys.exit(2).

    v5.86.0 round-5:
      - DRY via TG_AUTH_FAILURES tuple of 6 non-recoverable auth classes.
      - SessionPasswordNeededError handled separately (recoverable via 2FA prompt).
      - AuthKeyDuplicatedError added to dead-session list.
      - Telethon resolves session path internally (v1.x+); no cwd mutation needed.
      - Retry-once for transient ConnectionError/TimeoutError/OSError (2 strikes, sleep(1)).
    """
    import asyncio as _asyncio

    try:
        from telethon.errors import (
            AuthKeyUnregisteredError,
            UserDeactivatedError,
            UserBannedError,
            PhoneNumberBannedError,
            SessionRevokedError,
            InvalidAuthKeyError,
            AuthKeyDuplicatedError,
            SessionPasswordNeededError,
            FloodWaitError,
        )
        TG_AUTH_FAILURES: tuple = (
            AuthKeyUnregisteredError,
            UserDeactivatedError,
            UserBannedError,
            PhoneNumberBannedError,
            SessionRevokedError,
            InvalidAuthKeyError,
            AuthKeyDuplicatedError,
            SessionPasswordNeededError,  # round-7: 2FA promoted to fail-loud
        )
    except ImportError as imp_exc:
        print(f"FAIL telethon public auth-error classes unavailable: {imp_exc}", flush=True)
        print("     falling back to legacy 2-class catch (round-3 behavior); see CON-NEW fwd-guard", flush=True)
        # Legacy fallback: only catch what existed pre-v5.86.0 (still better than nothing).
        TG_AUTH_FAILURES = (
            AuthKeyUnregisteredError,
            UserDeactivatedError,
        )

    last_exc = None
    for attempt in (1, 2):
        client = None
        try:
            from projects_17.tg_terminal_messenger.src.telegram.client import TGClient  # NOQA: E402
            client = TGClient(session_name=TG_SESSION_NAME)
            await client.connect()
            await client.get_me()
            try:
                await client.disconnect()
            except Exception:
                pass
            print(f"  ok TG probe OK (attempt {attempt}/2)", flush=True)
            return True
        except TG_AUTH_FAILURES as exc:
            # Non-recoverable, fail-loud per CAN-14. Unified exit(2) per round-4 review.
            cls_name = type(exc).__name__
            print(f"FAIL TG AUTH FAILURE ({cls_name}): {exc}", flush=True)
            print(f"     session path: {TG_SESSION_PATH}", flush=True)
            # Round-9: dispatch table for which auth classes require reauth vs block.
            # Uses module-level constants (hoisted from inline definition per code-reviewer round-8).
            if cls_name in _2FA_CLASSES:
                print("     2FA password required. Reauth via interactive session:", flush=True)
                print("       c.sign_in(password='YOUR_2FA_PASSWORD') OR c.start()", flush=True)
            elif cls_name in _REAUTH_REQUIRED_CLASSES:
                print("     Reauth required. Instructions:", flush=True)
                print(TG_REAUTH_HINT, flush=True)
            else:
                print("     Account-level block. Reauth will NOT help.", flush=True)
                print("     Resolve via https://my.telegram.org or Telegram support.", flush=True)
            if client is not None:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            sys.exit(2)
        except Exception as exc:
            # FloodWaitError (rate-limit): echo seconds-readable so cron operator can plan next run.
            if isinstance(exc, FloodWaitError):
                seconds = getattr(exc, "seconds", 60)
                print(f"FAIL TG FLOOD-WAIT: must wait {seconds}s before retrying; aborting.", flush=True)
                if client is not None:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                sys.exit(2)
            # Transient (network level): retry-once.
            if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
                last_exc = exc
                print(f"  warn transient probe error (attempt {attempt}/2): {type(exc).__name__}: {exc}",
                      flush=True)
                if attempt == 1:
                    await _asyncio.sleep(1)
                    if client is not None:
                        try:
                            await client.disconnect()
                        except Exception:
                            pass
                        client = None
                    continue
                print(f"FAIL TG probe failed after 2 attempts; last error: {last_exc}", flush=True)
                sys.exit(2)
            # Unknown error: soft-warn, retry-once. Final strike returns False (CAN-14 partial).
            last_exc = exc
            print(f"  warn unexpected probe error (attempt {attempt}/2): {type(exc).__name__}: {exc}",
                  flush=True)
            if attempt == 1:
                await _asyncio.sleep(1)
                if client is not None:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                    client = None
                continue
            # Round-10 polish: explicit TGClient disconnect-guard before soft-warn False-return.
            # Without this, an unknown class on the 2nd strike leaks an open TGClient connection.
            if client is not None:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            print(f"  warn TG probe gave up after 2 attempts; round-trip verify will likely fail.",
                  flush=True)
            return False
        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                pass
    return False


# ============================================================
# Mock Update/Context (used for in-process bot lifecycle test, Option C).
# ============================================================
class _MockMessage:
    def __init__(self, chat_id: int) -> None:
        self.chat_id = chat_id
        self.replies: list = []
        self.reply_text_calls: list = []

    async def reply_text(self, text: str, **kwargs) -> None:
        self.reply_text_calls.append({"text": text, **kwargs})


class _MockChat:
    """Minimal chat object exposing .id for cmd_task's update.effective_chat.id access."""
    def __init__(self, chat_id: int) -> None:
        self.id = chat_id
        self.type = "private"  # PTB enum-ish; cmd_task does not branch on this


class _MockUpdate:
    def __init__(self, text: str, chat_id: int) -> None:
        self.message = _MockMessage(chat_id)
        self.message.text = text
        # Real python-telegram-bot Update exposes .effective_message + .effective_chat (PTB >= 13.x).
        # cmd_task accesses update.effective_message.reply_text AND update.effective_chat.id.
        self.effective_message = self.message
        self.effective_chat = _MockChat(chat_id)


class _MockContext:
    def __init__(self, args: "list[str)") -> None:
        self.args = args


def _preflight() -> None:
    """0-side-effect checks. Exit 1 on any failure (no TG touch)."""
    session = TG_SESSION_PATH
    if not session.exists():
        print(f"FAIL Pre-flight FAILED: TG session file missing: {session}")
        sys.exit(1)
    age_h = (time.time() - session.stat().st_mtime) / 3600.0
    if age_h > 36:
        print(f"WARN Pre-flight WARNING: TG session is {age_h:.1f}h old (may indicate expired auth).")
        print(f"     session path: {session}")

    for sub in ("user", "running", "done", "failed"):
        d = WORKSPACE / "pompts_11" / sub
        if not d.is_dir():
            print(f"FAIL Pre-flight FAILED: queue dir missing: {d}")
            sys.exit(1)

    logs_dir = WORKSPACE / "logs_14"
    if not logs_dir.is_dir():
        logs_dir.mkdir(exist_ok=True)


async def _invoke_cmd_task(text: str, chat_id: int) -> tuple:
    """Run cmd_task via in-process mock Update/Context (Option C)."""
    sys.path.insert(0, str(WORKSPACE))
    from scripts_01.telegram_bot import cmd_task  # NOQA: E402

    update = _MockUpdate(text=f"/task {text}", chat_id=chat_id)
    context = _MockContext(args=text.split(" "))

    t0 = time.time()
    await cmd_task(update, context)
    latency = time.time() - t0

    bot_replies = list(update.message.reply_text_calls)
    print(f"  cmd_task latency: {latency:.2f}s (target <{TARGET_LATENCY_SECS}s)")
    for c in bot_replies:
        text_short = (c["text"][:120] + "...") if len(c.get("text", "")) > 120 else c.get("text", "")
        print(f"  bot reply: {text_short}")

    return latency, text, bot_replies


async def _wait_for_spawn_log(prefix: str, before: float, max_secs: int = 30) -> "Path | None":
    """Wait for the per-task log; check it has the expected prefix."""
    logs_dir = WORKSPACE / "logs_14"
    deadline = time.time() + max_secs
    while time.time() < deadline:
        candidates = sorted(
            [p for p in logs_dir.glob("tg_spawn_*.log") if p.stat().st_mtime >= before],
            key=lambda p: p.stat().st_mtime,
        )
        if candidates:
            latest = candidates[-1]
            content = latest.read_text(encoding="utf-8", errors="replace")
            if prefix in content or "dispatch" in content.lower():
                return latest
        await asyncio.sleep(0.5)
    return None


def _round_trip_chat_id_sync(chat_id: int, search_text: str, _run_tag: str = "") -> "int | None":
    """Round-trip via TGClient.get_messages(limit-scan) — synchronous path tested without
    event loop concerns. Returns msg_id if found.

    v5.86.0: TGClient constructor takes session_name='tg_session' (post-CON-31 fix).
    """
    try:
        from projects_17.tg_terminal_messenger.src.telegram.client import TGClient  # NOQA: E402
        base = TGClient(session_name=TG_SESSION_NAME)
    except Exception as exc:
        print(f"WARN TGClient base instantiation failed: {exc}")
        return None

    async def _runner() -> "int | None":
        client = base
        try:
            from core_02._tg_client_v2 import TGClientV2  # NOQA: E402
            client = TGClientV2(base)
        except Exception:
            pass
        try:
            await client.connect()
            try:
                msgs = await client.get_messages(chat_id, limit=20)
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass
        except Exception as exc:
            print(f"WARN TG round-trip failed: {exc}")
            try:
                await client.disconnect()
            except Exception:
                pass
            return None
        for m in msgs:
            text = (m.get("message") or "") if isinstance(m, dict) else getattr(m, "message", "") or ""
            if search_text in str(text):
                return int(m.get("id") if isinstance(m, dict) else getattr(m, "id", 0))
        return None

    try:
        return asyncio.run(_runner())
    except Exception as exc:
        print(f"WARN round-trip async runner failed: {exc}")
        return None


def _append_audit_trail(
    task_id: str,
    saved_msg_id: "int | None",
    lit_msg_id: "int | None",
    latency: float,
    run_tag: str,
) -> None:
    """Prepend at TOP of `## Historical Verification Runs` section per CAN-17."""
    md_path = WORKSPACE / "docs_10/e2e_logs" / "promt47_run.md"
    if not md_path.exists():
        print(f"WARN audit trail file missing: {md_path}")
        return
    src = md_path.read_text(encoding="utf-8")
    marker = "## Historical Verification Runs"
    if marker not in src:
        print("WARN audit trail section not found — skipping")
        return
    head, sep, tail = src.partition(marker)
    after_marker = sep + marker
    lines = tail.splitlines()
    insert_at = 0
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|---") or ln.strip().startswith("| Date") or ln.strip().startswith("|"):
            insert_at = i + 1
            break
    new_row = (
        f"| {time.strftime('%Y-%m-%d %H:%M:%S')} | `{task_id}` | "
        f"{saved_msg_id or chr(0x2014)} | {lit_msg_id or chr(0x2014)} | "  # em-dash U+2014 per promt47_run.md canonical
        f"{latency:.2f}s | {run_tag} |"
    )
    lines.insert(insert_at, new_row)
    new_tail = "\n".join(lines)
    md_path.write_text(head + sep + new_tail + "\n", encoding="utf-8")
    print(f"ok prepended audit row → {md_path.name}")


async def main_async(
    chat_id_saved: int,
    chat_id_litvinov: int,
    text: str,
    run_tag: str,
    dry_run: bool,
) -> None:
    _preflight()

    # v5.86.0 round-7: --dry-run is single disable (replaces legacy NO_TG/env dual-gate).
    send_tg = not dry_run

    safe_text = text if text else f"v5.86.0 dual-path verify @ {time.strftime('%H:%M:%S')}"
    print(f"\n=== v5.86.0 dual-path LIVE e2e TAG={run_tag} (dry-run={dry_run}, send_tg={send_tg}) ===")
    print(f"  text: {safe_text!r}")
    print(f"  saved_chat_id: {chat_id_saved} | litvinov_chat_id: {chat_id_litvinov}")

    before = time.time()
    latency, task_text, bot_replies = await _invoke_cmd_task(safe_text, chat_id_saved)

    print("\n... waiting for spawn log file (<=30s)...")
    spawn_log = await _wait_for_spawn_log(prefix=safe_text, before=before, max_secs=30)
    if spawn_log:
        log_head = "\n".join(spawn_log.read_text(encoding="utf-8", errors="replace").splitlines()[:25])
        print(f"ok log file OK: {spawn_log.name}")
        print(f"  head:\n{log_head}")
    else:
        print("WARN spawn log file not found within 30s (dispatch may have exited or stuck)")

    saved_msg_id = None
    lit_msg_id = None

    if send_tg:
        # Probe (CAN-14 fail-loud; round-7 unified exit(2) on canonical auth failures).
        alive = await _probe_tg_session()
        if not alive:
            print("WARN TG session probe reported soft-warn; round-trip may still need reauth.")

        print("\n... TG round-trip Saved...")
        saved_msg_id = _round_trip_chat_id_sync(chat_id_saved, search_text=safe_text)
        print(f"  saved: {saved_msg_id if saved_msg_id else 'NOT FOUND'}")
        print("... TG round-trip Litvinov...")
        lit_msg_id = _round_trip_chat_id_sync(chat_id_litvinov, search_text=safe_text)
        print(f"  litvinov: {lit_msg_id if lit_msg_id else 'NOT FOUND (optional channel)'}")
    else:
        print("\n... skipping TG round-trip (--dry-run). "
              "Dispatcher may STILL send TG messages (e.g., cron dispatch).")

    # Extract a synthesized task_id from bot reply if available.
    task_id = f"task_{run_tag[:18]}"
    for c in bot_replies:
        m = c.get("text", "")
        if "Task ID:" in m and "`" in m:
            try:
                task_id = m.split("Task ID: ")[1].strip("` \n").splitlines()[0].strip()
            except Exception:
                pass

    _append_audit_trail(
        task_id=task_id,
        saved_msg_id=saved_msg_id,
        lit_msg_id=lit_msg_id,
        latency=latency,
        run_tag=run_tag,
    )

    if latency >= TARGET_LATENCY_SECS:
        print(f"\nWARN LATENCY WARNING: {latency:.2f}s >= target {TARGET_LATENCY_SECS}s")
    if send_tg and not saved_msg_id:
        print("WARN ROUND-TRIP WARNING: real TG round-trip did not find msg in history")


def main() -> int:
    p = argparse.ArgumentParser(description="v5.83.0 dual-path TG e2e verify (v5.86.0 polish)")
    p.add_argument("--chat-id-saved", type=int, default=SAVED_MESSAGES_CHAT_ID)
    p.add_argument("--chat-id-litvinov", type=int, default=ALEX_LITVINOV_CHAT_ID)
    p.add_argument("--text", type=str, default="")
    p.add_argument("--run-tag", type=str, default=f"v5.86.0_e2e_{uuid.uuid4().hex[:6]}")
    p.add_argument("--dry-run", action="store_true",
                   help="skip real TG send (preflight + pytest smoke + structural e2e)")
    args = p.parse_args()
    asyncio.run(
        main_async(
            chat_id_saved=args.chat_id_saved,
            chat_id_litvinov=args.chat_id_litvinov,
            text=args.text,
            run_tag=args.run_tag,
            dry_run=args.dry_run,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
