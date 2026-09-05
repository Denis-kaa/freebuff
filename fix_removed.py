#!/usr/bin/env python3
"""Fix ***REMOVED*** corruption across Python files.

The corruption pattern: a previous AI session read files through a tool that
displays ***REMOVED*** for redacted content, then wrote those corrupted
tokens back to disk.

This script analyzes bracket nesting context to determine what each
***REMOVED*** token should be replaced with.

Usage:
    python3 fix_removed.py [--dry-run] [--verbose]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# The REMOVED token pattern (various star counts)
REMOVED_RE = re.compile(r'\*+REMOVED\*+')


def count_unmatched_openers(line_before_token: str) -> dict[str, int]:
    """Count unmatched opening brackets/parens/braces in text before the token."""
    depth = {'(': 0, '[': 0, '{': 0}
    close_map = {')': '(', ']': '[', '}': '{'}
    in_string = False
    string_char = None
    escape_next = False

    for ch in line_before_token:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\':
            escape_next = True
            continue
        if in_string:
            if ch == string_char:
                in_string = False
            continue
        if ch in ('"', "'"):
            in_string = True
            string_char = ch
            continue
        if ch in ('#',):
            break  # rest is comment
        if ch in depth:
            depth[ch] += 1
        elif ch in close_map:
            opener = close_map[ch]
            if depth[opener] > 0:
                depth[opener] -= 1

    return depth


def determine_closing(line_before: str, after_token: str) -> str:
    """Determine what closing bracket(s) the REMOVED token should be."""
    depth = count_unmatched_openers(line_before)

    # Priority: close the deepest nesting first
    closers = []
    if depth['{'] > 0:
        closers.append('}')
    if depth['['] > 0:
        closers.append(']')
    if depth['('] > 0:
        closers.append(')')

    if not closers:
        # No unmatched openers - figure out from context
        # Check if after_token starts with something
        after_stripped = after_token.lstrip()
        if after_stripped.startswith(')'):
            # Could be closing a set/dict literal used as function arg
            # Check what's before on the line
            stripped = line_before.rstrip()
            if stripped.endswith(','):
                return '}'
            return ']'
        elif after_stripped.startswith(']'):
            return '}'
        elif after_stripped.startswith('}'):
            return ']'
        else:
            # Default to closing bracket
            return ']'

    return ''.join(closers)


def fix_line(line: str) -> Tuple[str, int]:
    """Fix REMOVED tokens in a single line. Returns (fixed_line, num_replacements)."""
    if 'REMOVED' not in line:
        return line, 0

    result = []
    count = 0
    pos = 0

    for m in REMOVED_RE.finditer(line):
        before = line[pos:m.start()]
        after = line[m.end():]
        closing = determine_closing(before, after)
        result.append(before)
        result.append(closing)
        pos = m.end()
        count += 1

    if count:
        result.append(line[pos:])
        return ''.join(result), count

    return line, 0


def fix_file(filepath: str, dry_run: bool = False, verbose: bool = False) -> int:
    """Fix REMOVED corruption in a single file. Returns number of replacements."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (UnicodeDecodeError, PermissionError) as e:
        if verbose:
            print(f"  SKIP {filepath}: {e}")
        return 0

    total = 0
    new_lines = []
    for i, line in enumerate(lines, 1):
        fixed, n = fix_line(line)
        new_lines.append(fixed)
        total += n
        if n and verbose:
            print(f"  {filepath}:{i}: {n} replacement(s)")

    if total and not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    return total


def find_python_files(root_dirs: List[str]) -> List[str]:
    """Find all Python files in given directories."""
    files = []
    for root_dir in root_dirs:
        for dirpath, dirs, fnames in os.walk(root_dir):
            # Skip venvs, __pycache__, .git
            dirs[:] = [d for d in dirs if d not in ('venv', '.venv', '__pycache__', '.git', 'node_modules', '.next')]
            for fn in fnames:
                if fn.endswith('.py'):
                    files.append(os.path.join(dirpath, fn))
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description="Fix ***REMOVED*** corruption in Python files")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files, just report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-line replacements")
    parser.add_argument("--dirs", nargs="+", default=["core_02", "tests_09", "scripts_01", "freebuff_plugin_03", "plugins_04"],
                        help="Directories to scan")
    args = parser.parse_args()

    files = find_python_files(args.dirs)
    print(f"Scanning {len(files)} Python files...")

    total_files = 0
    total_replacements = 0

    for fp in files:
        # Quick check if file contains REMOVED
        try:
            with open(fp) as f:
                content = f.read(4096)  # Read first 4KB for quick check
            if 'REMOVED' not in content:
                continue
        except:
            continue

        n = fix_file(fp, dry_run=args.dry_run, verbose=args.verbose)
        if n:
            total_files += 1
            total_replacements += n
            action = "would fix" if args.dry_run else "fixed"
            print(f"  {action} {fp}: {n} replacements")

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Summary:")
    print(f"  Files affected: {total_files}")
    print(f"  Total replacements: {total_replacements}")

    return 0 if not args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
