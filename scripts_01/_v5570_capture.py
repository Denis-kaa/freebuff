"""v5.57.0 atomic capture (single Python orchestration, ASCII-safe OUTPUT).

Pipeline:
  1. BACKUP - copy 3 doc files to /tmp/v55x_backup/
  2. SURGERY - revert v5.58.0 + v5.59.0 sections from 3 doc files
  3. COMMIT - git add 3 docs + tg_send_v5570.py + apply/restore scripts
  4. TAG    - annotated git tag v5.57.0
  5. RESTORE - copy backup files back over working tree

Idempotency: refuses to run if tag v5.57.0 already exists in git.

NOTE: print() outputs are intentionally ASCII-only (no emoji, no \u2705 etc) to
sidestep UnicodeEncodeError on surrogate-containing output in restricted
stdout environments. The bash-side `echo OK` afterward still works fine.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import os
from pathlib import Path


REPO = Path("/storage/emulated/0/PROJECTS/workstation/freebuff")
BACKUP_DIR = Path("/tmp/v55x_backup")
TRASH = REPO / "trash_21"

CHANGELOG = REPO / "CHANGELOG.md"
ARCH_DEBT = REPO / "docs_10/core/ARCHITECTURAL_DEBT.md"
LESSONS = REPO / "core_02/LESSONS.md"
TG_SEND = REPO / "scripts_01/tg_send_v5570.py"


def banner(t: str) -> None:
    print(f"\n=== {t} ===")


def ok(s: str) -> None:
    print(f"  [OK]   {s}")


def warn(s: str) -> None:
    print(f"  [WARN] {s}")


def fail(s: str) -> None:
    print(f"  [FAIL] {s}")


def run(cmd):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


# -- 1. BACKUP --
def backup():
    banner("STEP 1: BACKUP")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for src in (CHANGELOG, ARCH_DEBT, LESSONS):
        dst = BACKUP_DIR / src.name
        shutil.copy2(src, dst)
        ok(f"{src.name} -> {dst} (size={dst.stat().st_size}B)")
    return 0


# -- 2. SURGERY --
def surgery():
    banner("STEP 2: SURGERY (revert v5.58.0 + v5.59.0 sections)")

    # ---- CHANGELOG ----
    text = CHANGELOG.read_text()
    m_557 = text.find("## [5.57.0)")
    m_558 = text.find("## [5.58.0)")
    m_559 = text.find("## [5.59.0)")
    if m_557 == -1 or m_558 == -1 or m_559 == -1:
        fail(f"CHANGELOG missing expected headers (m_557={m_557}, m_558={m_558}, m_559={m_559})")
        return 1
    if not (m_559 < m_558 < m_557):
        fail(f"CHANGELOG ordering unexpected (m_559={m_559}, m_558={m_558}, m_557={m_557})")
        return 1
    new_text = text[m_557:]
    CHANGELOG.write_text(new_text)
    ok(f"CHANGELOG.md cut-off: -{m_557}B; new size={len(new_text)}B")
    ok(f"  v5.57.0 at offset 0; v5.58.0/v5.59.0 stripped")

    # ---- ARCHITECTURAL_DEBT - remove section 5.19 + 5.18 latest-run row ----
    text = ARCH_DEBT.read_text()
    m_519 = text.find("### 5.19 Block-A Recovery")
    if m_519 == -1:
        fail("ARCH_DEBT: section 5.19 header not found")
        return 1
    m_next = text.find("\n## 6. Recommended Next Steps", m_519)
    if m_next == -1:
        fail("ARCH_DEBT: section 6 boundary not found after 5.19")
        return 1
    text = text[:m_519] + text[m_next:]
    target_row = "| **Latest verified run (v5.59.0, locator-based)** | **2026-08-03**"
    idx = text.find(target_row)
    if idx == -1:
        fail("ARCH_DEBT: section 5.18 'Latest verified run' row not found")
        return 1
    end = text.find("\n", idx)
    text = text[:idx] + text[end + 1:]
    ARCH_DEBT.write_text(text)
    ok(f"ARCH_DEBT cut-off section 5.19 + removed 5.18 Latest-run row; new size={len(text)}B")

    # ---- LESSONS - remove Block-A closure + CAN-9 closure sections ----
    text = LESSONS.read_text()
    # Section anchors use ASCII-only fragments (emoji fade-safe). The Begin markers
    # we wrote are "## Scenario: Block-A Recovery" and "## Scenario: CAN-9 Final Closure"
    # but the file has "## <emoji> Scenario: ..." form. Search for "Scenario: Block-A Recovery"
    # which appears later with leading space/letters around emoji.
    m_ba = text.find("Scenario: Block-A Recovery")
    if m_ba == -1:
        fail("LESSONS: 'Scenario: Block-A Recovery' anchor not found")
        # diagnostic: dump last 100 chars
        warn(f"LESSONS tail 200 chars: {text[-200:]!r}")
        return 1
    # Walk back to find the "##" of its section header
    pre = text[:m_ba]
    m_hdr = pre.rfind("## ")
    if m_hdr == -1:
        fail("LESSONS: cannot locate '## ' before Block-A closure anchor")
        return 1
    m_cn9 = text.find("Scenario: CAN-9 Final Closure")
    if m_cn9 != -1 and m_cn9 > m_ba:
        ok("LESSONS: Block-A and CAN-9 Final Closure both present; cut at Block-A start")
    else:
        ok(f"LESSONS: Block-A present; CAN-9 anchor m_cn9={m_cn9} (may be missing or before)")
    new_text = text[:m_hdr].rstrip() + "\n"
    LESSONS.write_text(new_text)
    ok(f"LESSONS cut to v5.57.0-only state; was {len(text)}B, now {len(new_text)}B")
    return 0


# -- 3. COMMIT --
def commit_and_tag():
    banner("STEP 3: git add + commit + tag v5.57.0")
    rc, tags_out, _ = run(["git", "tag", "--list", "v5.57.0"])
    if rc != 0:
        fail(f"git tag --list rc={rc}")
        return 1
    if tags_out.strip():
        fail("tag v5.57.0 already exists; refuse to double-tag")
        return 1
    ok("no pre-existing v5.57.0 tag")

    files = [
        str(CHANGELOG.relative_to(REPO)),
        str(ARCH_DEBT.relative_to(REPO)),
        str(LESSONS.relative_to(REPO)),
        str(TG_SEND.relative_to(REPO)),
        str((TRASH / "_apply_can8_v5570.py").relative_to(REPO)),
        str((TRASH / "_restore_can8_v5570.py").relative_to(REPO)),
    ]
    for f in files:
        rc, out, err = run(["git", "add", "--", f])
        if rc != 0:
            fail(f"git add {f}: {err}")
            return 1
        ok(f"git add {f}")

    msg = (
        "fix(scripts): body-level /tmp hardcode elimination (CAN-8, v5.57.0)\n\n"
        "- Resolution chain: $INTERIOR_PLANNER_HOME > canonical hardcode (inline duplicated resolver)\n"
        "- Helper _interior_planner_home.py + _marker.txt removed (anti-fragile per v5.56.0 lesson)\n"
        "- Sys.path block restored (Option A: parents[1] form kept; Block-A deferred as Known Limitation)\n"
        "- Holistic docstring pass (ANTI-11): help-strings now match actual behavior\n"
        "- Tools: scripts_01/_apply_can8_v5570.py + _restore_can8_v5570.py archived to trash_21/\n"
        "- Notify: scripts_01/tg_send_v5570.py added for human-format TG broadcast\n\n"
        "Known limitations (deferred to future releases, closed later):\n"
        "- Block-A recovery (closed in v5.58.0 via _freebuff_locator)\n"
        "- DEFAULT_CANONICAL_ROOT hardcode (NIT-1 wires through core_02/wizard_lib)\n\n"
        "Verify gates (4/4 green):\n"
        "- py_compile cold-import: OK\n"
        "- cold-import DEFAULT_SEED/DEFAULT_ARTIFACT not /tmp: PASS\n"
        "- business gate e2e_promt47.py --skip-tg --silent: exit 0\n"
        "- grep audit /tmp/interior in canonical scripts: 0 hits"
    )
    rc, out, err = run(["git", "commit", "-m", msg])
    if rc != 0:
        fail(f"git commit rc={rc}: {err}")
        warn(f"stdout: {out[:300]}")
        return 1
    ok(f"git commit: {out.splitlines()[0] if out else '(no summary)'}")

    tag_msg = (
        "v5.57.0 - CAN-8 closure (body-level /tmp hardcode elimination)\n\n"
        "Resolver pattern: $INTERIOR_PLANNER_HOME env > inline def in both scripts.\n"
        "_interior_planner_home.py + _marker.txt removed (single-source-of-truth).\n"
        "See CHANGELOG.md v5.57.0 entry for full Verify Gate evidence."
    )
    rc, out, err = run(["git", "tag", "-a", "v5.57.0", "-m", tag_msg])
    if rc != 0:
        fail(f"git tag rc={rc}: {err}")
        return 1
    ok("git tag v5.57.0 created (annotated)")
    return 0


# -- 4. RESTORE --
def restore():
    banner("STEP 4: RESTORE working tree (pre-surgery state)")
    mapping = {
        "CHANGELOG.md": REPO / "CHANGELOG.md",
        "ARCHITECTURAL_DEBT.md": REPO / "docs_10/core/ARCHITECTURAL_DEBT.md",
        "LESSONS.md": REPO / "core_02/LESSONS.md",
    }
    for name, dst in mapping.items():
        src = BACKUP_DIR / name
        if not src.exists():
            warn(f"backup missing: {src}")
            continue
        shutil.copy2(src, dst)
        ok(f"{name} <- {src} (size={dst.stat().st_size}B)")
    rc, status, err = run(["git", "status", "--porcelain"])
    if rc != 0:
        warn(f"git status rc={rc}: {err}")
    ok("git status after restore:")
    for line in (status or "").splitlines()[:15]:
        ok(f"  {line}")
    return 0


def restore_after_failure(prev_rc: int) -> int:
    print()
    banner("FAILURE RECOVERY: restore from backup")
    mapping = {
        "CHANGELOG.md": REPO / "CHANGELOG.md",
        "ARCHITECTURAL_DEBT.md": REPO / "docs_10/core/ARCHITECTURAL_DEBT.md",
        "LESSONS.md": REPO / "core_02/LESSONS.md",
    }
    for name, dst in mapping.items():
        src = BACKUP_DIR / name
        if not src.exists():
            warn(f"backup missing: {src}")
            continue
        shutil.copy2(src, dst)
        ok(f"restored {name}")
    warn(f"prior rc={prev_rc}")
    return prev_rc


def main() -> int:
    print("=== v5.57.0 atomic capture ===")
    if backup() != 0:
        return 1
    if surgery() != 0:
        return restore_after_failure(1)
    if commit_and_tag() != 0:
        return restore_after_failure(1)
    if restore() != 0:
        warn("restore phase had warnings but proceeded")
    print()
    banner("v5.57.0 capture complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
