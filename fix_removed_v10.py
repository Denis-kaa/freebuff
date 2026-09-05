#!/usr/bin/env python3
"""Fix ***REMOVED*** corruption — v10 (lazy regex + bracket matching).

Uses lazy regex to group adjacent REMOVED tokens, then applies bracket
matching with proper f-string handling.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


# Lazy regex: matches one or more adjacent REMOVED tokens as a group
GROUP_RE = re.compile(r'(\*+?)REMOVED(\*+?)(?:\*+REMOVED\*+)*')


def normalize(content: str) -> Tuple[str, int]:
    """Replace all REMOVED groups with N placeholders (N = number of REMOVEDs in group)."""
    total = [0]
    def replacer(m):
        n = m.group(0).count('REMOVED')
        total[0] += n
        return '?' * n
    result = GROUP_RE.sub(replacer, content)
    return result, total[0]


def fix_brackets(content: str) -> str:
    """Process content tracking bracket nesting to resolve '?' placeholders.
    
    Handles:
    - Regular brackets: [], (), {}
    - f-string expressions: {expr} inside f"..."
    - Regular strings: '...', "..."
    - Triple-quoted strings: '''...''', \"\"\"...\"\"\"
    - Comments: #...
    """
    lines = content.split('\n')
    output = []
    stack = []  # list of ('[' | '(' | '{')
    
    for line in lines:
        new_chars = []
        i = 0
        n = len(line)
        
        # String state
        in_string = False
        string_char = None
        is_triple = False
        is_fstring = False
        fstring_depth = 0
        
        while i < n:
            ch = line[i]
            
            # ── Inside f-string expression ──
            if is_fstring and fstring_depth > 0:
                if ch == '{':
                    fstring_depth += 1
                    new_chars.append(ch)
                elif ch == '}':
                    fstring_depth -= 1
                    new_chars.append(ch)
                elif ch == '?':
                    # Inside f-string expr — should close the expression
                    fstring_depth -= 1
                    new_chars.append('}')
                elif ch in ('"', "'"):
                    # String inside f-string expression — track it
                    if line[i:i+3] in ('"""', "'''"):
                        q = line[i:i+3]
                        end_q = line.find(q, i + 3)
                        if end_q == -1:
                            new_chars.append(line[i:])
                            i = n
                            continue
                        new_chars.append(line[i:end_q + 3])
                        i = end_q + 3
                        continue
                    else:
                        j = i + 1
                        while j < n:
                            if line[j] == '\\':
                                j += 2
                                continue
                            if line[j] == ch:
                                j += 1
                                break
                            j += 1
                        new_chars.append(line[i:j])
                        i = j
                        continue
                elif ch == '#':
                    new_chars.append(line[i:])
                    i = n
                    continue
                else:
                    new_chars.append(ch)
                i += 1
                continue
            
            # ── Inside f-string but not in expression (literal part) ──
            if is_fstring and fstring_depth == 0:
                if ch == '{':
                    if i + 1 < n and line[i + 1] == '{':
                        new_chars.append('{{')
                        i += 2
                        continue
                    # Start of f-string expression
                    fstring_depth = 1
                    new_chars.append(ch)
                elif ch == '}':
                    if i + 1 < n and line[i + 1] == '}':
                        new_chars.append('}}')
                        i += 2
                        continue
                    # End of f-string
                    is_fstring = False
                    new_chars.append(ch)
                elif ch == string_char:
                    is_fstring = False
                    in_string = False
                    new_chars.append(ch)
                elif ch == '?':
                    # ? in f-string literal part — replace with }
                    is_fstring = False
                    new_chars.append('}')
                else:
                    new_chars.append(ch)
                i += 1
                continue
            
            # ── Inside regular string ──
            if in_string:
                if is_triple:
                    if line[i:i+3] == string_char * 3:
                        in_string = False
                        is_triple = False
                        new_chars.append(line[i:i+3])
                        i += 3
                        continue
                else:
                    if ch == '\\':
                        new_chars.append(line[i:i+2])
                        i += 2
                        continue
                    if ch == string_char:
                        in_string = False
                new_chars.append(ch)
                i += 1
                continue
            
            # ── Start of string / f-string ──
            if ch in ('"', "'"):
                # Check for f-string prefix
                prefix_chars = set()
                j = i - 1
                while j >= 0 and line[j].isalpha():
                    prefix_chars.add(line[j].lower())
                    j -= 1
                
                if 'f' in prefix_chars:
                    is_fstring = True
                    fstring_depth = 0
                    in_string = True
                    string_char = ch
                else:
                    in_string = True
                    string_char = ch
                
                if line[i:i+3] in ('"""', "'''"):
                    is_triple = True
                    new_chars.append(line[i:i+3])
                    i += 3
                else:
                    new_chars.append(ch)
                    i += 1
                continue
            
            # ── Comment ──
            if ch == '#':
                new_chars.append(line[i:])
                i = n
                continue
            
            # ── Placeholder ──
            if ch == '?':
                if stack:
                    opener = stack.pop()
                    closer = {'(': ')', '[': ']', '{': '}'}[opener]
                else:
                    closer = '}'
                new_chars.append(closer)
                i += 1
                continue
            
            # ── Bracket tracking ──
            if ch in ('(', '[', '{'):
                stack.append(ch)
                new_chars.append(ch)
            elif ch in (')', ']', '}'):
                expected = {'(': ')', '[': ']', '{': '}'}
                if stack and expected.get(stack[-1]) == ch:
                    stack.pop()
                new_chars.append(ch)
            else:
                new_chars.append(ch)
            
            i += 1
        
        output.append(''.join(new_chars))
    
    return '\n'.join(output)


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
    
    # Step 1: Normalize
    normalized, n_placeholders = normalize(content)
    
    # Step 2: Fix brackets
    fixed = fix_brackets(normalized)
    
    # Verify
    remaining = fixed.count('REMOVED')
    remaining_q = fixed.count('?')
    
    # AST check
    ast_ok = True
    try:
        ast.parse(fixed)
    except SyntaxError as e:
        ast_ok = False
        if verbose:
            print(f"  ❌ AST: {filepath}:{e.lineno}:{e.offset}: {e.msg}")
    
    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed)
    
    if verbose and remaining_q > 0:
        print(f"  ⚠️  {filepath}: {remaining_q} unresolved '?' remaining")
    
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
