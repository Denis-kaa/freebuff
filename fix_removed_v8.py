#!/usr/bin/env python3
"""Fix ***REMOVED*** corruption — v8 (handles f-strings correctly).

Two-pass strategy:
1. Replace all REMOVED variants with '?' placeholder
2. Process line by line tracking bracket nesting, handling f-strings specially

Key improvement: f-string expressions use {expr} but these are NOT
Python brackets for nesting purposes. We need to track f-string depth
separately.
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
    """Normalize all REMOVED variants and fix with bracket tracking."""
    
    # Step 1: Replace all REMOVED variants with '?'
    positions = [m.start() for m in re.finditer('REMOVED', content)]
    
    if not positions:
        return content
    
    result = []
    last_end = 0
    
    for i, pos in enumerate(positions):
        # Find extent
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
    normalized = ''.join(result)
    
    # Step 2: Process with bracket tracking, handling f-strings
    lines = normalized.split('\n')
    output_lines = []
    
    # Python bracket stack (for [], (), and non-f-string {})
    stack = []
    
    for line_num, line in enumerate(lines, 1):
        new_line = []
        i = 0
        in_string = False
        string_char = None
        triple = False
        in_fstring = False
        fstring_depth = 0  # nesting of { } inside f-string
        fstring_quote = None
        
        while i < len(line):
            ch = line[i]
            
            # Handle f-string
            if in_fstring:
                if ch == '{':
                    if i + 1 < len(line) and line[i+1] == '{':
                        # Escaped {{ 
                        new_line.append('{{')
                        i += 2
                        continue
                    fstring_depth += 1
                    new_line.append(ch)
                    i += 1
                    continue
                elif ch == '}':
                    if i + 1 < len(line) and line[i+1] == '}':
                        # Escaped }}
                        new_line.append('}}')
                        i += 2
                        continue
                    if fstring_depth > 0:
                        fstring_depth -= 1
                        new_line.append(ch)
                        i += 1
                        continue
                    else:
                        # End of f-string expression
                        in_fstring = False
                        new_line.append(ch)
                        i += 1
                        continue
                elif ch == fstring_quote:
                    in_fstring = False
                    fstring_quote = None
                    new_line.append(ch)
                    i += 1
                    continue
                elif ch == '?':
                    # Placeholder inside f-string expression — should be '}'
                    if fstring_depth > 0:
                        fstring_depth -= 1
                    else:
                        in_fstring = False
                    new_line.append('}')
                    i += 1
                    continue
                else:
                    new_line.append(ch)
                    i += 1
                    continue
            
            # Handle regular strings
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
            
            # Start of string
            if ch in ('"', "'"):
                # Check if it's an f-string
                if i > 0 and line[i-1] in ('f', 'F', 'r', 'R', 'b', 'B'):
                    prefix = ''
                    j = i - 1
                    while j >= 0 and line[j].lower() in ('f', 'r', 'b', 'u'):
                        prefix = line[j] + prefix
                        j -= 1
                    if 'f' in prefix.lower():
                        in_fstring = True
                        fstring_quote = ch
                        fstring_depth = 0
                        in_string = True
                        string_char = ch
                        if line[i:i+3] in ('"""', "'''"):
                            triple = True
                        new_line.append(ch)
                        i += 1
                        continue
                
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
            
            # Placeholder
            if ch == '?':
                if stack:
                    opener = stack.pop()
                    closer = {'(': ')', '[': ']', '{': '}'}[opener]
                else:
                    closer = '}'
                new_line.append(closer)
                i += 1
                continue
            
            # Track brackets
            if ch in ('(', '['):
                stack.append(ch)
                new_line.append(ch)
            elif ch == '{':
                # Only track { if not in f-string context
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
    
    remaining = fixed.count('REMOVED')
    
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
