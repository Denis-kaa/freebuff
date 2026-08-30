"""E2E smoke test v2 for Freebuff v5.41.0 — corrected TGClient API.

Changes from v1:
- TGClient has NO `is_user_authorized` method on the wrapper. Use
  `await client.connect()` which RETURNS bool (already does internal check).
- `send_message(entity, text)` accepts int (chat_id) as entity — kept.
- Wizard --selftest isolated: if PB-2 (`No module named 'yaml'`) blocks wizard,
  fall through with raw scenario summary stub via `runtime_05/scenarios/` ls.

Stages:
1. wizard --selftest (or stub if PB-2).
2. TGClient bootstrap (returns bool from connect()).
3. send_message to Saved Messages (chat_id=7709651193) with wizard summary.
4. send_message to Litvinov (chat_id=1063827731) with hello.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
}
from typing import Any, Optional

FREEBUFF_ROOT = Path("/storage/emulated/0/PROJECTS/workstation/freebuff")
WIZARD = FREEBUFF_ROOT / "scripts_01/wizard.py"
TG_CLIENT_DIR = FREEBUFF_ROOT / "projects_17/tg_terminal_messenger"
SCENARIOS_DIR = FREEBUFF_ROOT / "runtime_05" / "scenarios"

SAVED_MESSAGES_CHAT_ID = 7709651193
LITVINOV_CHAT_ID = 1063827731


def stage1_wizard_selftest() -> dict[str, Any]:
    """Stage 1 — wizard --selftest. Isolated; PB-2 yaml documented."""
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(WIZARD), "--selftest"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(FREEBUFF_ROOT),
        )
        elapsed = time.monotonic() - t0
        summary = proc.stdout.strip()[-1500:]
        # If wizard failed due to missing yaml — known PB-2; provide stub.
        if proc.returncode != 0 and "No module named 'yaml'" in proc.stderr + proc.stdout:
            return {
                "stage": "wizard_selftest",
                "ok": False,
                "fallback_used": True,
                "pb": "PB-2 (No module named 'yaml')",
                "elapsed_seconds": round(elapsed, 2),
                "stub_summary": _list_scenarios_stub(),
                "stderr_tail": proc.stderr.strip()[-300:],
            }
        return {
            "stage": "wizard_selftest",
            "ok": proc.returncode == 0,
            "elapsed_seconds": round(elapsed, 2),
            "stdout_tail": summary,
            "stderr_tail": proc.stderr.strip()[-300:] if proc.returncode != 0 else "",
        }
    except subprocess.TimeoutExpired:
        return {"stage": "wizard_selftest", "ok": False, "error": "timeout 60s"}
    except Exception as e:
        return {"stage": "wizard_selftest", "ok": False, "error": f"{type(e).__name__}: {e}"}


def _list_scenarios_stub() -> str:
    """Fallback summary if wizard is blocked by PB-2 yaml."""
    if not SCENARIOS_DIR.exists():
        return f"scenarios_dir not found: {SCENARIOS_DIR}"
    lines = [
        f"scenarios_dir: {SCENARIOS_DIR}",
        f"scenarios discovered:",
    ]
    for p in sorted(SCENARIOS_DIR.glob("*.yaml")):
        lines.append(f"  - {p.name}")
    return "\n".join(lines)


async def stage2_tg_bootstrap() -> tuple[Any, dict[str, Any]]:
    """Stage 2 — TGClient.connect() returns bool; if False abort."""
    sys.path.insert(0, str(TG_CLIENT_DIR))
    try:
        from src.telegram.client import TGClient  # type: ignore
    except Exception as e:
        return None, {"ok": False, "error": f"import TGClient: {type(e).__name__}: {e}"}

    client = TGClient()
    try:
        t0 = time.monotonic()
        authorized = await client.connect()  # returns bool directly
        elapsed = time.monotonic() - t0
        if not authorized:
            await client.disconnect()
            return None, {
                "ok": False,
                "elapsed_seconds": round(elapsed, 2),
                "error": "not_authorized (session invalid)",
            }
        me = await client.get_me()
        return client, {
            "ok": True,
            "elapsed_seconds": round(elapsed, 2),
            "self_id": me.id,
            "self_username": f"@{me.username}" if me.username else None,
            "self_name": f"{me.first_name} {me.last_name}".strip(),
        }
    except Exception as e:
        return None, {"ok": False, "error": f"{type(e).__name__}: {e}"}


async def stage_send(client: Any, chat_id: int, text: str) -> dict[str, Any]:
    """Helper — send via TGClient.send_message."""
    t0 = time.monotonic()
    try:
        msg = await client.send_message(chat_id, text)
        elapsed = time.monotonic() - t0
        return {
            "ok": True,
            "chat_id": chat_id,
            "msg_id": getattr(msg, "id", None),
            "elapsed_seconds": round(elapsed, 2),
        }
    except Exception as e:
        elapsed = time.monotonic() - t0
        return {
            "ok": False,
            "chat_id": chat_id,
            "elapsed_seconds": round(elapsed, 2),
            "error": f"{type(e).__name__}: {e}",
        }


async def main() -> int:
    print("=" * 60)
    print("E2E SMOKE TEST v2 — Freebuff v5.41.0 (post CAN-3 closure)")
    print("=" * 60)

    # Stage 1
    print("\n[Stage 1) wizard --selftest")
    print("-" * 40)
    wizard = stage1_wizard_selftest()
    print(f"  ok={wizard.get('ok')}  elapsed={wizard.get('elapsed_seconds')}s")
    if wizard.get("fallback_used"):
        print(f"  PB-2: {wizard.get('pb')} → using scenarios stub")
        print(f"  stub_summary:\n{_list_scenarios_stub()}")

    # Stage 2
    print("\n[Stage 2) TGClient bootstrap")
    print("-" * 40)
    client, bootstrap = await stage2_tg_bootstrap()
    if not bootstrap.get("ok"):
        print(f"  ERROR: {bootstrap}")
        return 3
    print(f"  ok={True}  elapsed={bootstrap['elapsed_seconds']}s")
    print(f"  self_id={bootstrap['self_id']}  username={bootstrap['self_username']}")
    print(f"  name={bootstrap['self_name']}")

    # Stage 3 — Saved Messages (wizard-summary block)
    print("\n[Stage 3) send to Saved Messages (7709651193)")
    print("-" * 40)
    summary_text = (
        "📚 Freebuff E2E smoke test v5.41.0\n\n"
        f"stage1 (wizard --selftest):\n"
        f"  ok={wizard.get('ok')}\n"
        f"  elapsed={wizard.get('elapsed_seconds')}s\n"
        f"  fallback={wizard.get('fallback_used', False)} (PB-2 if True)\n\n"
        f"stage2 (TGClient bootstrap):\n"
        f"  self_id={bootstrap['self_id']}  name={bootstrap['self_name']}\n\n"
        f"chat_id=SAVED_MESSAGES, smoke harness v2 (2026-08-02)."
    )
    saved = await stage_send(client, SAVED_MESSAGES_CHAT_ID, summary_text)
    print(f"  {saved}")

    # Stage 4 — Litvinov hello
    print("\n[Stage 4) send to Александр Литвинов (1063827731)")
    print("-" * 40)
    litvinov_text = (
        "Привет от Freebuff smoke test (v5.41.0). "
        "E2E проверка после CAN-3 closure: TGClient → Saved Messages + Litvinov. "
        "Если ты это читаешь — TG-интеграция в Freebuff работает."
    )
    litvinov = await stage_send(client, LITVINOV_CHAT_ID, litvinov_text)
    print(f"  {litvinov}")

    # Disconnect
    try:
        await client.disconnect()
    except Exception:
        pass

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    summary = {
        "wizard_selftest": {
            "ok": wizard.get("ok"),
            "elapsed": wizard.get("elapsed_seconds"),
            "fallback_used": wizard.get("fallback_used", False),
        },
        "tg_bootstrap": {
            "ok": bootstrap.get("ok"),
            "elapsed": bootstrap.get("elapsed_seconds"),
            "self_id": bootstrap.get("self_id"),
        },
        "saved_messages": saved,
        "litvinov": litvinov,
    }
    summary["both_tg_ok"] = saved.get("ok") and litvinov.get("ok")
    summary["full_e2e_ok"] = (
        wizard.get("ok") and summary["both_tg_ok"]
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["both_tg_ok"] else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
