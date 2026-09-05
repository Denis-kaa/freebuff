"""One-shot helper to apply v5.86.0 round-4+5 holistic fix to e2e_dual_path_tg_verify.py.

Avoids heredoc quote hell: writes Python source for _probe_tg_session via plain
string concatenation (chr(39) for literal apostrophes where needed).

Usage: python3 scripts_01/_v5_86_0_holistic_fix.py
"""
***REMOVED***
import os
import shutil

# ============================================================
# Constants — anchored to current file content (round-2 layout)
# ============================================================
SRC = Path("scripts_01/e2e_dual_path_tg_verify.py")
BAK = Path("scripts_01/e2e_dual_path_tg_verify.py.bak_v5.86.0_holistic")

# New probe function — DRY tuple + unified exit(2) + FloodWait seconds + retry-once
# All single-quotes inside are literal text for user-facing messages (not Python strings).
NEW_PROBE = '''async def _probe_tg_session() -> bool:
    """v5.86.0 probe (round-5 holistic): DRY via TG_AUTH_FAILURES tuple, unified
    exit(2) for all probe failures, retry-once for transient, FloodWait echoes
    its seconds-remaining so cron operators know when to retry.

    Returns True on success, False on soft-warn (only via unknown error category).
    """
    import asyncio as _asyncio

    # DRY forward-looking guard (round-4 code-reviewer): tuple of all non-recoverable
    # TG auth errors. Adding new ones = add to tuple, no code change.
    try:
        from telethon.errors import (
            AuthKeyUnregisteredError,
            UserDeactivatedError,
            UserBannedError,
            PhoneNumberBannedError,
            SessionRevokedError,
            InvalidAuthKeyError,
            FloodWaitError,
        )
        TG_AUTH_FAILURES = (
            AuthKeyUnregisteredError,
            UserDeactivatedError,
            UserBannedError,
            PhoneNumberBannedError,
            SessionRevokedError,
            InvalidAuthKeyError,
        )
    except ImportError:
        # Some telethon versions may not export all — fallback
        TG_AUTH_FAILURES = (Exception,)
        FloodWaitError = None  # type: ignore

    orig_cwd = os.getcwd()
    last_exc = None
    try:
        os.chdir(_TG_CWD)
        for attempt in (1, 2):
            client = None
            try:
                client = TGClient(session_name=TG_SESSION_NAME)
                await client.connect()
                try:
                    await client.get_me()
                finally:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                print(f"  ok TG probe OK (attempt {attempt***REMOVED***/2)", flush=True)
                return True
            except TG_AUTH_FAILURES as exc:
                # Non-recoverable, fail-loud per CAN-14. Unified exit(2).
                cls = type(exc).__name__
                print(f"FAIL TG AUTH FAILURE ({cls***REMOVED***): {exc***REMOVED***", flush=True)
                print(f"     session path: {TG_SESSION_PATH***REMOVED***", flush=True)
                if cls in ("AuthKeyUnregisteredError", "InvalidAuthKeyError"):
                    print("     Reauth required. Regenerate with:", flush=True)
                    print("       python3 -c 'from telethon.sync import TelegramClient;'", flush=True)
                    print("         c = TelegramClient(\"tg_session\", int(os.environ[\"TG_API_ID\"***REMOVED***), os.environ[\"TG_API_HASH\"***REMOVED***);", flush=True)
                    print("         c.start()'", flush=True)
                    print("     Requires TG_API_ID/TG_API_HASH env vars + interactive phone+code.", flush=True)
                    print("     Get creds at: https://my.telegram.org/apps", flush=True)
                elif cls in ("UserDeactivatedError", "UserBannedError", "PhoneNumberBannedError", "SessionRevokedError"):
                    print("     Account-level block. Reauth will NOT help.", flush=True)
                    print("     Resolve via https://my.telegram.org or Telegram support.", flush=True)
                try:
                    if client is not None:
                        await client.disconnect()
                except Exception:
                    pass
                sys.exit(2)
            except Exception as exc:
                # FloodWaitError (if available) is rate-limit; echo seconds
                if FloodWaitError is not None and isinstance(exc, FloodWaitError):
                    seconds = getattr(exc, "seconds", 60)
                    print(f"FAIL TG FLOOD-WAIT: must wait {seconds***REMOVED***s before retrying", flush=True)
                    try:
                        if client is not None:
                            await client.disconnect()
                    except Exception:
                        pass
                    sys.exit(2)
                if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
                    last_exc = exc
                    print(f"  warn transient probe error (attempt {attempt***REMOVED***/2): {type(exc).__name__***REMOVED***: {exc***REMOVED***", flush=True)
                    if attempt == 1:
                        await _asyncio.sleep(1)
                        continue
                    print(f"FAIL TG probe failed after 2 attempts; last error: {last_exc***REMOVED***", flush=True)
                    if client is not None:
                        try:
                            await client.disconnect()
                        except Exception:
                            pass
                    sys.exit(2)
                # Unknown — soft-warn, retry-once
                last_exc = exc
                print(f"  warn unexpected probe error (attempt {attempt***REMOVED***/2): {type(exc).__name__***REMOVED***: {exc***REMOVED***", flush=True)
                if attempt == 1:
                    await _asyncio.sleep(1)
                    continue
                print(f"  warn TG probe gave up after 2 attempts; round-trip verify will likely fail.", flush=True)
                if client is not None:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                return False
        return False
    finally:
        try:
            os.chdir(orig_cwd)
        except Exception:
            pass


'''


def main() -> None:
    if BAK.exists():
        print(f"backup already exists at {BAK***REMOVED***; remove it first if you want to re-run")
        return
    shutil.copy2(SRC, BAK)
    print(f"backup created: {BAK***REMOVED***")

    src = SRC.read_text(encoding="utf-8")

    # Locate probe function bounds and replace.
    ***REMOVED***

    probe_start_re = re.compile(r"^async def _probe_tg_session", re.M)
    next_def_re = re.compile(r"^async def _round_trip_chat_id|^def _", re.M)

    m_start = probe_start_re.search(src)
    if not m_start:
        print("ERROR: _probe_tg_session not found")
        return
    m_end = next_def_re.search(src, m_start.end() + 1)
    if not m_end:
        print("ERROR: next def after probe not found")
        return
    end_idx = m_end.start()

    new_src = src[: m_start.start()***REMOVED*** + NEW_PROBE + src[end_idx:***REMOVED***
    SRC.write_text(new_src, encoding="utf-8")
    print(f"probe function replaced (old {end_idx - m_start.start()***REMOVED*** bytes -> new {len(NEW_PROBE)***REMOVED*** bytes)")
    print(f"file size: {BAK.stat().st_size***REMOVED*** -> {SRC.stat().st_size***REMOVED*** bytes")


if __name__ == "__main__":
    main()
