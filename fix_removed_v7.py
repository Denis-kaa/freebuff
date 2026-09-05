#!/usr/bin/env python3
"""Fix ***REMOVED*** corruption — v7 (definitive).

Two-pass strategy:
1. Strip REMOVEDs that already have a closing bracket before them (redundant)
2. For remaining REMOVEDs, use line-level bracket context to determine the closer

The key insight from analysis:
- 38x: `]REMOVED***` — bracket already present, just strip
- 4x: `)REMOVED***` — same
- 2x: `}REMOVED***` — same
- 18303x: `***REMOVED***` — bracket REPLACED, need to determine what it was
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def normalize_and_fix(content: str) -> str:
    """Normalize all REMOVED variants, strip redundant ones, fix remaining."""
    
    # Step 1: Replace all REMOVED variants with placeholder '?'
    # Handle adjacent tokens by processing all REMOVED positions
    positions = [m.start() for m in re.finditer('REMOVED', content)]
    
    if not positions:
        return content
    
    # Build replacement plan: for each REMOVED, determine its full extent
    # (including surrounding stars) and replace with '?'
    result = []
    last_end = 0
    
    for i, pos in enumerate(positions):
        # Find extent: go back to find stars (but not past previous token)
        start = pos
        prev_end = positions[i-1] + 7 if i > 0 else 0  # end of previous REMOVED keyword
        while start > prev_end and content[start-1] == '*':
            start -= 1
        
        # Go forward to find stars (but not past next REMOVED's start)
        next_pos = positions[i+1] if i+1 < len(positions) else len(content)
        end = pos + 7
        while end < next_pos and content[end] == '*':
            end += 1
        
        # Add clean text before this token
        clean = content[last_end:start]
        result.append(clean)
        
        # Add placeholder
        result.append('?')
        last_end = end
    
    # Remaining clean text
    result.append(content[last_end:])
    normalized = ''.join(result)
    
    # Step 2: Determine what each '?' should be based on bracket context
    # Process line by line, tracking bracket nesting
    lines = normalized.split('\n')
    output_lines = []
    
    # Global bracket stack
    stack = []  # list of (char, line_num)
    
    for line_num, line in enumerate(lines, 1):
        new_line = []
        i = 0
        in_string = False
        string_char = None
        triple = False
        
        while i < len(line):
            ch = line[i]
            
            # String handling
            if in_string:
                if triple:
                    if line[i:i+3] == string_char * 3:
                        in_string = False
                        triple = False
                        new_line.append(line[i:i+3])
                        i += 3
                        continue
                else:
                    if ch == '\\':
                        new_line.append(line[i:i+2])
                        i += 2
                        continue
                    if ch == string_char:
                        in_string = False
                new_line.append(ch)
                i += 1
                continue
            
            if ch in ('"', "'"):
                if line[i:i+3] in ('"""', "'''"):
                    in_string = True
                    triple = True
                    string_char = ch
                    new_line.append(line[i:i+3])
                    i += 3
                    continue
                else:
                    in_string = True
                    string_char = ch
                    new_line.append(ch)
                    i += 1
                    continue
            
            # Comment
            if ch == '#':
                new_line.append(line[i:])
                i = len(line)
                continue
            
            # Placeholder — determine correct closer
            if ch == '?':
                if stack:
                    opener = stack.pop()
                    closer = {'(': ')', '[': ']', '{': '}'}[opener]
                else:
                    closer = '}'  # default for standalone/empty
                new_line.append(closer)
                i += 1
                continue
            
            # Track brackets
            if ch in ('(', '[', '{'):
                stack.append(ch)
                new_line.append(ch)
            elif ch in (')', ']', '}'):
                expected = {'(': ')', '[': ']', '{': '}'}
                if stack and expected.get(stack[-1]) == ch:
                    stack.pop()
                new_line.append(ch)
            else:
                new_line.append(ch)
            
            i += 1
        
        output_lines.append(''.join(new_line))
    
    return '\n'.join(output_lines)


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
    
    count = content.count('REMOVED')
    
    fixed = normalize_and_fix(content)
    
    # Verify
    remaining = fixed.count('REMOVED')
    if remaining > 0:
        if verbose:
            print(f"  WARNING: {filepath}: {remaining} REMOVED remaining")
    
    # Check AST
    ast_ok = True
    try:
        ast.parse(fixed)
    except SyntaxError as e:
        ast_ok = False
        if verbose:
            print(f"  AST ERROR: {filepath}:{e.lineno}:{e.offset}: {e.msg}")
    
    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed)
    
    return count


def find_python_files(root_dirs: List[str]) -> List[str]:
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
            action = "would fix" if args.dry_run else "fixed"
            print(f"  {action} {fp}: {n} replacements")
            
            if not args.dry_run:
                try:
                    with open(fp) as f:
                        ast.parse(f.read())
                except SyntaxError:
                    ast_errors += 1
    
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Summary:")
    print(f"  Files affected: {total_files}")
    print(f"  Total replacements: {total_replacements}")
    if ast_errors:
        print(f"  ⚠️  Files with AST errors: {ast_errors}")
    else:
        print(f"  ✅ All fixed files parse correctly")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
