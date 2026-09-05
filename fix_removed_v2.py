#!/usr/bin/env python3
"""Fix ***REMOVED*** corruption across Python files — v2.

Strategy: For each line with REMOVED tokens, count the unmatched opening
brackets BEFORE the first REMOVED token. This tells us how many ']' closings
are needed. Then each consecutive REMOVED on the same line gets one ']'.

For special cases (f-strings, standalone lines), use additional context clues.

Usage:
    python3 fix_removed_v2.py [--dry-run] [--verbose] [--dirs DIR1 DIR2 ...]
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


def fix_line(line: str) -> Tuple[str, int]:
    """Fix REMOVED tokens in a single line. Returns (fixed_line, num_replacements)."""
    if 'REMOVED' not in line:
        return line, 0

    # Find all REMOVED positions
    matches = list(REMOVED_RE.finditer(line))
    if not matches:
        return line, 0

    # Count unmatched opening brackets BEFORE the first REMOVED
    before_first = line[:matches[0].start()]
    open_square = before_first.count('[') - before_first.count(']')
    open_paren = before_first.count('(') - before_first.count(')')
    open_curly = before_first.count('{') - before_first.count('}')

    # Also check what comes AFTER the last REMOVED
    after_last = line[matches[-1].end():]

    # Determine closing bracket sequence needed
    # Priority: first close { then [ then ( — matching Python's inside-out closing
    closers_needed = []
    if open_curly > 0:
        closers_needed.append('}' * open_curly)
    if open_square > 0:
        closers_needed.append(']' * open_square)
    if open_paren > 0:
        closers_needed.append(')' * open_paren)
    closers = ''.join(closers_needed)

    # Build result
    result = []
    count = 0
    pos = 0
    num_removes = len(matches)

    for i, m in enumerate(matches):
        # Add text before this REMOVED token
        result.append(line[pos:m.start()])

        if num_removes == 1:
            # Single REMOVED on line — use the full closers string
            result.append(closers if closers else ']')
        else:
            # Multiple REMOVEDs on line — distribute closers
            # Each REMOVED gets one closing bracket
            if i < len(closers):
                result.append(closers[i])
            else:
                # Extra REMOVED tokens beyond what brackets need
                # Check context: if we're in a type hint context, use ']'
                result.append(']')

        count += 1
        pos = m.end()

    # Add remaining text
    result.append(line[pos:])

    return ''.join(result), count


def fix_standalone_lines(lines: List[str]) -> List[str]:
    """Fix standalone ***REMOVED*** lines that appear on their own.

    These are closing brackets that were on separate lines in the original.
    We need to look at surrounding context to determine what to close.
    """
    result = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == '***REMOVED***' or stripped == '***REMOVED***':
            # Standalone REMOVED — determine from context
            # Look backward for the last unclosed bracket
            context_before = ''.join(result[-5:]) if len(result) >= 5 else ''.join(result)
            open_c = context_before.count('{') - context_before.count('}')
            open_b = context_before.count('[') - context_before.count(']')
            open_p = context_before.count('(') - context_before.count(')')

            if open_c > 0:
                closer = '}'
            elif open_b > 0:
                closer = ']'
            elif open_p > 0:
                closer = ')'
            else:
                closer = '}'

            # Preserve indentation
            indent = line[:len(line) - len(line.lstrip())]
            result.append(f"{indent}{closer}\n")
        else:
            # Regular line — fix inline REMOVED tokens
            fixed, _ = fix_line(line)
            result.append(fixed)
    return result


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

    # First pass: fix inline REMOVED tokens
    for i, line in enumerate(lines, 1):
        if 'REMOVED' in line:
            fixed, n = fix_line(line)
            new_lines.append(fixed)
            total += n
        else:
            new_lines.append(line)

    # Second pass: fix standalone REMOVED lines (need context from surrounding lines)
    new_lines = fix_standalone_lines(new_lines)

    if total and not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    return total


def find_python_files(root_dirs: List[str]) -> List[str]:
    """Find all Python files in given directories."""
    files = []
    for root_dir in root_dirs:
        if not os.path.isdir(root_dir):
            continue
        for dirpath, dirs, fnames in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in (
                'venv', '.venv', '__pycache__', '.git', 'node_modules', '.next'
            )]
            for fn in fnames:
                if fn.endswith('.py'):
                    files.append(os.path.join(dirpath, fn))
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description="Fix ***REMOVED*** corruption in Python files")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files, just report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-line replacements")
    parser.add_argument("--dirs", nargs="+",
                        default=["core_02", "tests_09", "scripts_01", "freebuff_plugin_03", "plugins_04"],
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
                content = f.read(8192)
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
