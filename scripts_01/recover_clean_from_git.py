#!/usr/bin/env python3
"""Recover last-known-clean (marker-free) versions of corrupted files from git history.

Reads-only for the working tree and git objects; writes results ONLY into
.recovery_git_clean/ (files/ + meta/index.json + progress.log).

Strategy (single-pass, FUSE-friendly):
  1. Find affected tracked files (working tree contains the marker).
  2. One `git log --all --raw` pass maps path -> newest (date, commit, blob) candidates.
  3. One `git cat-file --batch` pass checks candidate blobs for the marker and
     dumps the newest clean blob per path.
"""
import subprocess
import pathlib
import json
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKER = b"***REMOVED***"
OUT = ROOT / ".recovery_git_clean"
FILES_DIR = OUT / "files"
META_DIR = OUT / "meta"
MAX_CANDIDATES_PER_PATH = 200


def log(msg: str, fh) -> None:
    print(msg, file=fh, flush=True)


def main() -> int:
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)
    fh = (OUT / "progress.log").open("w")

    t0 = time.time()
    # ── 1. affected files ──────────────────────────────────────────────
    affected = []
    for f in subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0"):
        if not f:
            continue
        p = ROOT / f
        if not p.is_file():
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        if MARKER in data:
            affected.append(f)
    log(f"[{time.time()-t0:7.1f}s] affected files: {len(affected)}", fh)
    affected_set = set(affected)

    # ── 2. single raw-history pass: path -> candidates ─────────────────
    # candidates: path -> list of (date, commit, blob); newest appended last
    hist: dict = {}
    proc = subprocess.Popen(
        ["git", "-c", "core.quotepath=false", "log", "--all", "--raw",
         "--no-abbrev", "--format=%H %ct", "--diff-filter=AM"],
        stdout=subprocess.PIPE,
    )
    cur_commit, cur_date = None, None
    for raw in proc.stdout:
        line = raw.decode("utf-8", "replace").rstrip("\n")
        if not line:
            continue
        if "\t" not in line:
            header = line.split()
            if len(header) == 2 and len(header[0]) == 40:
                cur_commit, cur_date = header[0], int(header[1])
            continue
        meta_part, _, rest = line.partition("\t")
        parts = meta_part.split()
        if len(parts) < 5 or cur_commit is None:
            continue
        blob = parts[3]
        status = parts[4]
        new_path = rest.split("\t")[-1]  # renames: old\tpath -> take last
        if new_path not in affected_set:
            continue
        cand = hist.setdefault(new_path, [])
        if len(cand) < 4000:  # hard cap for pathological paths
            cand.append((cur_date, cur_commit, blob))
    proc.wait()
    log(f"[{time.time()-t0:7.1f}s] raw pass done, paths with history: {len(hist)}", fh)

    # keep only newest K candidates per path, newest first for checking
    check_plan = []  # (path, [(date, commit, blob), ...] newest first)
    for path, cand in hist.items():
        cand.sort(key=lambda x: -x[0])
        check_plan.append((path, cand[:MAX_CANDIDATES_PER_PATH]))

    # ── 3. batch-check candidate blobs, dump newest clean per path ─────
    results = {}
    blob_to_paths = {}
    for path, cand in check_plan:
        for date, commit, blob in cand:
            blob_to_paths.setdefault(blob, []).append((path, date, commit))

    proc = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    pending = dict(blob_to_paths)  # blob -> [(path, date, commit)]
    found: dict = {}  # path -> (date, commit, blob)

    def write_out(blob: str, data: bytes) -> None:
        for path, date, commit in pending.pop(blob, []):
            if path in found:
                continue  # already have a newer clean version
            found[path] = (date, commit, blob)
            out = FILES_DIR / path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)

    stdin = proc.stdin
    stdout = proc.stdout
    asked = set()
    for path, cand in check_plan:
        for date, commit, blob in cand:
            if blob in asked:
                continue
            asked.add(blob)
            stdin.write(blob.encode() + b"\n")
            stdin.flush()
            header = stdout.readline().decode().split()
            if len(header) < 3 or header[1] != "blob":
                # missing object: read possible error payload line
                continue
            size = int(header[2])
            data = stdout.read(size)
            stdout.read(1)  # trailing LF
            if MARKER not in data:
                write_out(blob, data)
        done = len(found)
        if done and done % 100 == 0:
            log(f"[{time.time()-t0:7.1f}s] clean found so far: {done}", fh)
    stdin.close()
    proc.wait()

    # ── 4. index + summary ─────────────────────────────────────────────
    entries = []
    for path in affected:
        if path in found:
            date, commit, blob = found[path]
            entries.append({"path": path, "status": "clean_found",
                            "commit": commit, "blob": blob[:12], "date": date})
        else:
            entries.append({"path": path, "status": "no_clean_in_history"})
    index = {
        "marker": MARKER.decode(),
        "affected_scanned": len(affected),
        "clean_found": sum(1 for e in entries if e["status"] == "clean_found"),
        "no_clean_in_history": sum(1 for e in entries if e["status"] == "no_clean_in_history"),
        "entries": entries,
    }
    (META_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    log(f"[{time.time()-t0:7.1f}s] DONE clean={index['clean_found']} "
        f"no_clean={index['no_clean_in_history']}", fh)
    fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
