#!/usr/bin/env python3
"""CAN-8 corrective script v5.57.0 — restore sys.path block in register.py.

First-pass apply at `scripts_01/_apply_can8_v5570.py` succeeded in register.py
edits but REMOVED the sys.path block (`parents[1]` form) without a replacement.
That silent regression breaks cold-import of `core_02.blueprint_v3` needed by
`BlueprintCorpus(root=local_seed)` (register.py Stage 2).

Fix strategy — **Option A** (chosen per code-reviewer feedback):
- Re-insert `parents[1]` sys.path block BEFORE the `# --- Workspace locator ---`
  comment, restoring pre-apply state for that block.
- OUT OF SCOPE: Block-A recovery (= replace `parents[1]` with
  `from _freebuff_locator ]solve_freebuff_root` import for hot-freebuff
  root discovery). Block-A is a separate debt (see ARCHITECTURAL_DEBT §5.10);
  rolling it into the CAN-8 closure would expand scope without resolution.

Also drops `_interior_planner_home.py` helper (anti-fragile: _inline_ resolver
now defined identically in register.py + e2e_promt47.py; the file was a
vestigial `v5.53.0` artifact that introduced brittle dependency on a sibling
script that can be lost across relocations).

Idempotent: re-running on already-restored state is a no-op.
"""
from __future__ import annotations



SCRIPTS_DIR = Path(
    "/storage/emulated/0/PROJECTS/workstation/interior_planner_e2e/interior_planner/scripts"
)
REG = SCRIPTS_DIR / "interior_consultant_register.py"
HELPER = SCRIPTS_DIR / "_interior_planner_home.py"

ANCHOR = "# --- Workspace locator (CAN-8 closure, v5.57.0) ---\n"
RESTORED_MARK = "ROOT = Path(__file__).resolve().parents[1]\n"

# Block to insert before the canonical Workspace-locator anchor. Includes a
# lead-in comment explaining why we're keeping the `parents[1]` form (so future
# devs don't "fix" it without context).
PRE_INLINER_BLOCK = (
    "# --- Restore CON-17 sys.path block (Option A: keep parents[1] form for CAN-8 closure) ---\n"
    "# NOTE: `parents[1]` (= parent of scripts/ = interior_planner/) does NOT contain\n"
    "# core_02/, so this block alone does NOT enable core_02 import. Real core_02\n"
    "# discovery requires Block-A recovery (`from _freebuff_locator import ...`)\n"
    "# which is a SEPARATE debt; CAN-8 closure kept parents[1] form per scope.\n"
    "ROOT = Path(__file__).resolve().parents[1]\n"
    "if str(ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(ROOT))\n"
    "\n"
    "\n"
    "# --- Workspace locator (CAN-8 closure, v5.57.0) ---\n"
)


def main() -> int:
    print("=== Corrective restore: register.py sys.path block (Option A) ===\n")

    txt = REG.read_text()

    # === Validate anchor ===
    if ANCHOR not in txt:
        print(f"  ✗ {REG.name}: anchor '{ANCHOR.strip()}' not found — manual review")
        return 1
    if txt.count(ANCHOR) > 1:
        print(f"  ✗ {REG.name}: anchor appears {txt.count(ANCHOR)} times — ambiguous")
        return 1

    # === Idempotent insertion ===
    if RESTORED_MARK in txt:
        print(f"  - {REG.name}: sys.path block already restored (idempotent no-op)")
    else:
        new_txt = txt.replace(ANCHOR, PRE_INLINER_BLOCK, 1)
        REG.write_text(new_txt)
        print(f"  ✓ {REG.name}: inserted 5-line sys.path block before Workspace locator")

    # === Drop helper (idempotent) ===
    print()
    if HELPER.exists():
        HELPER.unlink()
        print(f"  ✓ dropped helper: {HELPER.name}")
    else:
        print(f"  - helper already absent: {HELPER.name}")

    print("\n=== Corrective restore complete ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
