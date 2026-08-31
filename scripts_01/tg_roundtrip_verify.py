"""Live TG round-trip verifier (v5.87.0) — positive Saved + Литвинов round-trip confirm.

WHY this exists (OOM lesson CON-27):
  The full e2e_dual_path_tg_verify.py real-run spawns cmd_task → dispatcher →
  wrapper.launch → Buffy/proot = RAM-heavy (~GB-class). On phone-class RAM this
  dies with signal 9 (OOM) BEFORE the TG round-trip can complete. The round-trip
  confirm itself needs NO Buffy — just a TG send + TGClient.get_messages read-back.
  This lean verifier covers exactly that (CAN-9 discipline without the heavy chain).

Pipeline:
  1. Send to Saved Messages (report_to_saved_messages) → msg_id_saved
  2. Send to Литвинов (report_to_alex_litvinov) → msg_id_litvinov
  3. Round-trip read-back via TGClient.get_messages(chat_id, limit=100) + filter
     (CON-31 pivot: TGClient wrapper has no ids= kwarg).
  4. Append audit row to docs_10/e2e_logs/promt47_run.md `## Historical
     Verification Runs` at TOP per CAN-17 (anti-rewriting).
  Exit 0 = both round-trips positive; Exit 1 = mismatch / not-connected.

Usage:
  python3 scripts_01/tg_roundtrip_verify.py --run-tag v5.87.0_live --text "optional"
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
import uuid
from pathlib import Path

FB_ROOT = Path(__file__).resolve().parent.parent
if str(FB_ROOT) not in sys.path:
    sys.path.insert(0, str(FB_ROOT))

import core_02.telegram_contract as tc  # noqa: E402

MESSAGE_TEXT = (
    "🧪 v5.87.0 live TG round-trip {run_tag]\n\n"
    "Лёгкий путь без Buffy-spawn (OOM-safe): Telegram-contract send + "
    "TGClient.get_messages read-back. Run-tag: {run_tag]"
)


def _unique_search_head(text: str, run_tag: str) -> str:
    """Unique-per-run search substring — run_tag is in the FIRST LINE so
    read-back cannot false-positive on an older run with the same prefix."""
    return text.splitlines()[0][:60] if run_tag in text.splitlines()[0] else run_tag


def _round_trip(chat_id: int, search_text: str, client_factory=None) -> "int | None":
    """Read-back via TGClient.get_messages limit-scan + client-side filter (CON-31).

    client_factory: injectable TGClient factory (test seam per code-reviewer
    v5.87.0 round-4). Default None → real TGClient from sibling project.
    """
    if client_factory is None:
        from projects_17.tg_terminal_messenger.src.telegram.client import TGClient

        client_factory = lambda: TGClient()  # noqa: E731  (simple default factory)

    async def _run() -> "int | None":
        client = client_factory()
        try:
            ok = await client.connect()
            if not ok:
                print(f"  warn not authorized for chat {chat_id}")
                return None
            msgs = await client.get_messages(chat_id, limit=100)
            for m in msgs:
                text = (m.get("message") or "") if isinstance(m, dict) else getattr(m, "message", "") or ""
                if search_text in str(text):
                    return int(m.get("id") if isinstance(m, dict) else getattr(m, "id", 0))
            return None
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    return asyncio.run(_run())


def _append_audit_trail(
    run_tag: str,
    task_id: str,
    saved_msg_id: "int | None",
    lit_msg_id: "int | None",
    latency: float,
    md_path: "Path | None" = None,
) -> None:
    """Prepend at TOP of `## Historical Verification Runs` per CAN-17.

    md_path: injectable target file (test seam per code-reviewer v5.87.0 round-4).
    Default None → canonical docs_10/e2e_logs/promt47_run.md.
    """
    if md_path is None:
        md_path = FB_ROOT / "docs_10/e2e_logs" / "promt47_run.md"
    if not md_path.exists():
        print(f"  warn audit trail file missing: {md_path}")
        return
    src = md_path.read_text(encoding="utf-8")
    marker = "## Historical Verification Runs"
    if marker not in src:
        print("  warn audit trail section not found — skipping")
        return
    head, sep, tail = src.partition(marker)
    lines = tail.splitlines()
    insert_at = 0
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|---") or ln.strip().startswith("| Date") or ln.strip().startswith("|"):
            insert_at = i + 1
            break
    new_row = (
        f"| {time.strftime('%Y-%m-%d %H:%M:%S')} | `{task_id}` | "
        f"{saved_msg_id or chr(0x2014)} | {lit_msg_id or chr(0x2014)} | "
        f"{latency:.2f}s | {run_tag} |"
    )
    lines.insert(insert_at, new_row)
    new_tail = "\n".join(lines)
    md_path.write_text(head + sep + new_tail + "\n", encoding="utf-8")
    print(f"  ok audit row prepended → {md_path.name}")


def main() -> int:
    p = argparse.ArgumentParser(description="v5.87.0 live TG round-trip verifier (OOM-safe)")
    p.add_argument("--run-tag", type=str, default=f"v5.87.0_rt_{uuid.uuid4().hex[:6]}")
    p.add_argument("--text", type=str, default="")
    args = p.parse_args()

    text = args.text or MESSAGE_TEXT.format(run_tag=args.run_tag)
    # Round-3 edge-case fix (code-reviewer): custom --text may omit the run-tag,
    # which would make _unique_search_head fall back to run_tag and the read-back
    # always miss (false negative) even on successful send. Force-append if absent.
    if args.run_tag not in text:
        text = f"{text}\nRun-tag: {args.run_tag}"
    print(f"=== v5.87.0 live TG round-trip TAG={args.run_tag} ===")
    print(f"  text head: {text.splitlines()[0]}")

    t0 = time.time()
    saved_id = asyncio.run(tc.report_to_saved_messages(text))
    print(f"  Saved Messages msg_id = {saved_id}")
    lit_id = asyncio.run(tc.report_to_alex_litvinov(text))
    print(f"  Литвинов msg_id = {lit_id}")
    latency = time.time() - t0

    print("\n--- round-trip read-back ---")
    search_head = _unique_search_head(text, args.run_tag)
    saved_rt = _round_trip(tc.SAVED_MESSAGES_CHAT_ID, search_head) if saved_id else None
    print(f"  saved round-trip msg_id = {saved_rt}")
    lit_rt = _round_trip(tc.LITVINOV_CHAT_ID, search_head) if lit_id else None
    print(f"  litvinov round-trip msg_id = {lit_rt}")

    # CAN-9 honesty (code-reviewer v5.87.0): audit row records ROUND-TRIP-CONFIRMED
    # ids only — never the raw send return (which would claim verification it lacks).
    # Em-dash cells = unverified (process already exits 1 on failure).
    task_id = f"task_{args.run_tag[:18]}"
    _append_audit_trail(
        run_tag=args.run_tag,
        task_id=task_id,
        saved_msg_id=saved_rt,
        lit_msg_id=lit_rt,
        latency=latency,
    )

    if saved_rt and lit_rt:
        print(f"\n=== TG round-trip POSITIVE: Saved={saved_rt}, Литвинов={lit_rt} (latency {latency:.2f}s) ===")
        return 0
    print("\n=== TG round-trip INCOMPLETE — see warnings above ===")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
