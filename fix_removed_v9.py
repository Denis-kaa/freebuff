#!/usr/bin/env python3
"""Fix ***REMOVED*** corruption — v9 (AST-guided iterative fix).

Strategy: Replace REMOVED with '?', then use Python's ast.parse to find
syntax errors and iteratively fix them.

For each SyntaxError:
- If it says "closing X doesn't match opening Y on line N",
  look at line N to find what the correct closing should be.
- If it says "unexpected EOF" or similar, the REMOVED was a closer that
  we need to insert.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def strip_all_removed(content: str) -> str:
    """Replace all REMOVED variants with '?' (one per REMOVED keyword)."""
    positions = [m.start() for m in re.finditer('REMOVED', content)]
    if not positions:
        return content
    
    result = []
    last_end = 0
    for i, pos in enumerate(positions):
        start = pos
        prev_end = positions[i-1] + 7 if i > 0 else 0
        while start > prev_end and content[start-1] == '*':
            start -= 1
        next_pos = positions[i+1] if i+1 < len(positions) else len(content)
        end = pos + 7
        while end < next_pos and content[end] == '*':
            end += 1
        result.append(content[last_end:start])
        result.append('?')
        last_end = end
    result.append(content[last_end:])
    return ''.join(result)


def try_parse(content: str) -> Optional[Tuple[int, int, str]]:
    """Try to parse. Return (line, col, msg) of first error, or None."""
    try:
        ast.parse(content)
        return None
    except SyntaxError as e:
        return (e.lineno or 0, e.offset or 0, e.msg)


def fix_by_line_context(lines: List[str], error_line: int, error_col: int, error_msg: str) -> List[str]:
    """Fix the '?' on the error line based on the error message."""
    if error_line < 1 or error_line > len(lines):
        return lines
    
    line = lines[error_line - 1]
    
    # Find the ? on this line
    if '?' not in line:
        return lines
    
    # Determine what the ? should be based on error message
    closer = None
    
    if "closing parenthesis ')'" in error_msg and "does not match opening" in error_msg:
        # ')' doesn't match something — need to figure out what
        # Look at the context: what opener is on the error line?
        opener_match = re.search(r"opening parenthesis '(\w)'", error_msg)
        if opener_match:
            opener = opener_match.group(1)
            closer_map = {'(': ')', '[': ']', '{': '}'}
            closer = closer_map.get(opener, '}')
    
    elif "closing parenthesis ']'" in error_msg and "does not match opening" in error_msg:
        opener_match = re.search(r"opening parenthesis '(\w)'", error_msg)
        if opener_match:
            opener = opener_match.group(1)
            closer_map = {'(': ')', '[': ']', '{': '}'}
            closer = closer_map.get(opener, ']')
    
    elif "closing parenthesis '}'" in error_msg and "does not match opening" in error_msg:
        opener_match = re.search(r"opening parenthesis '(\w)'", error_msg)
        if opener_match:
            opener = opener_match.group(1)
            closer_map = {'(': ')', '[': ']', '{': '}'}
            closer = closer_map.get(opener, '}')
    
    elif "unexpected EOF" in error_msg or "unexpected end" in error_msg:
        # Need to close something — use bracket tracking
        closer = '}'
    
    elif "expected ':'" in error_msg or "invalid syntax" in error_msg:
        # Could be f-string issue — replace ? with }
        closer = '}'
    
    if closer is None:
        closer = '}'  # default
    
    # Replace the first ? on the error line with the closer
    new_line = line.replace('?', closer, 1)
    lines[error_line - 1] = new_line
    
    return lines


def fix_iterative(content: str, max_iterations: int = 200, verbose: bool = False) -> Tuple[str, int]:
    """Iteratively fix '?' placeholders using AST errors."""
    lines = content.split('\n')
    iterations = 0
    fixes = 0
    
    while iterations < max_iterations:
        test_content = '\n'.join(lines)
        error = try_parse(test_content)
        
        if error is None:
            break
        
        line_num, col, msg = error
        if verbose and iterations < 10:
            print(f"    iter {iterations}: L{line_num}:{col}: {msg}")
        
        old_lines = lines[:]
        lines = fix_by_line_context(lines, line_num, col, msg)
        
        if lines == old_lines:
            # No change made — try a different strategy
            # Look for ? on nearby lines
            found = False
            for offset in range(-5, 6):
                check_line = line_num + offset
                if 1 <= check_line <= len(lines) and '?' in lines[check_line - 1]:
                    lines = fix_by_line_context(lines, check_line, 0, msg)
                    found = True
                    break
            if not found:
                if verbose:
                    print(f"    STUCK at iter {iterations}: L{line_num}: {msg}")
                break
        
        iterations += 1
        fixes += 1
    
    return '\n'.join(lines), fixes


def fix_file(filepath: str, dry_run: bool = False, verbose: bool = False) -> int:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError) as e:
        if verbose:
            print(f"  SKIP {filepath}: {e}")
        return 0
    
    if 'REMOVED' not in content:
        return 0
    
    count = content.count('REMOVED')
    
    # Strip all REMOVED to ?
    normalized = strip_all_removed(content)
    
    # Iteratively fix
    fixed, fixes = fix_iterative(normalized, verbose=verbose)
    
    # Final AST check
    remaining = fixed.count('REMOVED')
    ast_ok = True
    try:
        ast.parse(fixed)
    except SyntaxError as e:
        ast_ok = False
        if verbose:
            print(f"  ❌ AST ERROR: {filepath}:{e.lineno}:{e.offset}: {e.msg}")
    
    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed)
    
    return count


def find_python_files(root_dirs):
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--dirs", nargs="+",
                        default=["core_02", "tests_09", "scripts_01", "freebuff_plugin_03", "plugins_04"])
    args = parser.parse_args()
    
    files = find_python_files(args.dirs)
    print(f"Scanning {len(files)} Python files...")
    
    total_files = 0
    total_replacements = 0
    ast_errors = 0
    ast_ok = 0
    
    for fp in files:
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
            print(f"  {'would fix' if args.dry_run else 'fixed'} {fp}: {n} replacements")
            
            if not args.dry_run:
                try:
                    with open(fp) as f:
                        ast.parse(f.read())
                    ast_ok += 1
                except SyntaxError:
                    ast_errors += 1
    
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Summary:")
    print(f"  Files affected: {total_files}")
    print(f"  Total replacements: {total_replacements}")
    if not args.dry_run:
        print(f"  ✅ AST OK: {ast_ok}")
        if ast_errors:
            print(f"  ⚠️  AST errors: {ast_errors}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
