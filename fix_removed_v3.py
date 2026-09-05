#!/usr/bin/env python3
"""Fix ***REMOVED*** corruption across Python files — v3.

Strategy: Two-pass approach.
Pass 1: Replace each ***REMOVED*** with a PLACEHOLDER marker (e.g., «REMOVED_N»)
Pass 2: Walk the file tracking bracket nesting state (only counting real brackets,
         not placeholders), and replace each placeholder with the correct closer.

This handles cross-line context correctly.

Usage:
    python3 fix_removed_v3.py [--dry-run] [--verbose] [--dirs DIR1 DIR2 ...]
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

# PLACEHOLDER pattern for pass 1
PLACEHOLDER_RE = re.compile(r'«REMOVED_(\d+)»')


def pass1_replace_with_placeholders(content: str) -> Tuple[str, int]:
    """Replace all REMOVED tokens with numbered placeholders."""
    count = [0]
    def replacer(m):
        count[0] += 1
        return f'«REMOVED_{count[0]}»'
    result = REMOVED_RE.sub(replacer, content)
    return result, count[0]


def pass2_resolve_placeholders(content: str) -> str:
    """Walk the file tracking bracket state and resolve each placeholder."""
    lines = content.split('\n')
    result_lines = []

    # Track bracket nesting across the file
    stack = []  # list of (char, line_num) for unmatched openers

    for line_num, line in enumerate(lines, 1):
        new_line = []
        i = 0
        while i < len(line):
            # Check for placeholder
            m = PLACEHOLDER_RE.match(line, i)
            if m:
                placeholder_id = m.group(1)
                # Determine what closer we need based on the stack
                if stack:
                    opener_char, opener_line = stack[-1]
                    closer = {'(': ')', '[': ']', '{': '}'}[opener_char]
                    stack.pop()
                    new_line.append(closer)
                else:
                    # No unmatched openers — default to '}'
                    new_line.append('}')
                i = m.end()
                continue

            ch = line[i]

            # Skip strings
            if ch in ('"', "'"):
                # Check for triple-quote
                if line[i:i+3] in ('"""', "'''"):
                    quote = line[i:i+3]
                    end = line.find(quote, i + 3)
                    if end == -1:
                        # Multi-line string — skip to end of line
                        new_line.append(line[i:])
                        i = len(line)
                        continue
                    else:
                        new_line.append(line[i:end + 3])
                        i = end + 3
                        continue
                else:
                    # Single-char string
                    j = i + 1
                    while j < len(line):
                        if line[j] == '\\':
                            j += 2
                            continue
                        if line[j] == ch:
                            j += 1
                            break
                        j += 1
                    new_line.append(line[i:j])
                    i = j
                    continue

            # Skip comments
            if ch == '#':
                new_line.append(line[i:])
                i = len(line)
                continue

            # Track brackets
            if ch in ('(', '[', '{'):
                stack.append((ch, line_num))
                new_line.append(ch)
            elif ch in (')', ']', '}'):
                expected = {'(': ')', '[': ']', '{': '}'}
                if stack and expected.get(stack[-1][0]) == ch:
                    stack.pop()
                # If stack is empty or mismatch, still append (keep the char)
                new_line.append(ch)
            else:
                new_line.append(ch)

            i += 1

        result_lines.append(''.join(new_line))

    return '\n'.join(result_lines)


def fix_file(filepath: str, dry_run: bool = False, verbose: bool = False) -> int:
    """Fix REMOVED corruption in a single file. Returns number of replacements."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError) as e:
        if verbose:
            print(f"  SKIP {filepath}: {e}")
        return 0

    if 'REMOVED' not in content:
        return 0

    # Pass 1: Replace with placeholders
    content, count = pass1_replace_with_placeholders(content)
    if count == 0:
        return 0

    # Pass 2: Resolve placeholders using bracket context
    content = pass2_resolve_placeholders(content)

    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    return count


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
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-file info")
    parser.add_argument("--dirs", nargs="+",
                        default=["core_02", "tests_09", "scripts_01", "freebuff_plugin_03", "plugins_04"],
                        help="Directories to scan")
    args = parser.parse_args()

    files = find_python_files(args.dirs)
    print(f"Scanning {len(files)} Python files...")

    total_files = 0
    total_replacements = 0

    for fp in files:
        # Quick check
        try:
            with open(fp) as f:
                if 'REMOVED' not in f.read(8192):
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
