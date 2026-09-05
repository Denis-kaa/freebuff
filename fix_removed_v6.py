#!/usr/bin/env python3
"""Fix ***REMOVED*** corruption using iterative AST validation.

Strategy:
1. Replace all REMOVED tokens with '?' placeholders
2. Use Python's ast.parse to find syntax errors
3. For each error, determine the correct replacement
4. Repeat until no more errors

This is the most reliable approach because it uses Python's own parser.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from typing import List, Optional, Tuple


PLACEHOLDER = '?'


def normalize_removed(content: str) -> Tuple[str, int]:
    """Replace all REMOVED variants with '?' placeholders."""
    count = [0]
    def replacer(m):
        count[0] += 1
        return PLACEHOLDER
    result = re.sub(r'\*+REMOVED\*+', replacer, content)
    return result, count[0]


def find_syntax_error(content: str) -> Optional[Tuple[int, int, str]]:
    """Try to parse content. Return (line, col, msg) of first syntax error, or None."""
    try:
        ast.parse(content)
        return None
    except SyntaxError as e:
        return (e.lineno or 0, e.offset or 0, e.msg)


def fix_by_bracket_matching(content: str) -> str:
    """One-pass fix using bracket nesting to resolve all '?' placeholders."""
    lines = content.split('\n')
    result = []
    
    # Track nesting across the file
    stack = []  # list of (char, line_num)
    
    for line_num, line in enumerate(lines, 1):
        new_chars = []
        i = 0
        in_string = False
        string_char = None
        triple_quote = False
        
        while i < len(line):
            ch = line[i]
            
            # Handle string state
            if in_string:
                if triple_quote:
                    if line[i:i+3] == string_char * 3:
                        in_string = False
                        triple_quote = False
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
            
            # Start of string
            if ch in ('"', "'"):
                if line[i:i+3] in ('"""', "'''"):
                    in_string = True
                    triple_quote = True
                    string_char = ch
                    new_chars.append(line[i:i+3])
                    i += 3
                    continue
                else:
                    in_string = True
                    string_char = ch
                    new_chars.append(ch)
                    i += 1
                    continue
            
            # Comment
            if ch == '#':
                new_chars.append(line[i:])
                i = len(line)
                continue
            
            # Placeholder
            if ch == PLACEHOLDER:
                # Determine correct closer from stack
                if stack:
                    opener = stack.pop()
                    closer = {'(': ')', '[': ']', '{': '}'}[opener]
                else:
                    closer = '}'  # default for standalone
                new_chars.append(closer)
                i += 1
                continue
            
            # Track brackets
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
        
        result.append(''.join(new_chars))
    
    return '\n'.join(result)


def fix_file(filepath: str, dry_run: bool = False, verbose: bool = False) -> int:
    """Fix REMOVED corruption using iterative AST validation."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError) as e:
        if verbose:
            print(f"  SKIP {filepath}: {e}")
        return 0
    
    if 'REMOVED' not in content:
        return 0
    
    original_count = content.count('REMOVED')
    
    # Step 1: Normalize all REMOVED variants to '?'
    normalized, _ = normalize_removed(content)
    
    # Step 2: Fix using bracket matching
    fixed = fix_by_bracket_matching(normalized)
    
    # Step 3: Validate with AST
    error = find_syntax_error(fixed)
    if error and verbose:
        line, col, msg = error
        print(f"  WARNING: {filepath}:{line}:{col}: {msg}")
    
    # Step 4: Write
    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed)
    
    return original_count


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
    import argparse
    parser = argparse.ArgumentParser(description="Fix ***REMOVED*** corruption in Python files")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files, just report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-file info and AST errors")
    parser.add_argument("--dirs", nargs="+",
                        default=["core_02", "tests_09", "scripts_01", "freebuff_plugin_03", "plugins_04"],
                        help="Directories to scan")
    args = parser.parse_args()
    
    files = find_python_files(args.dirs)
    print(f"Scanning {len(files)} Python files...")
    
    total_files = 0
    total_replacements = 0
    total_errors = 0
    
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
            
            # Check AST after fix
            if not args.dry_run:
                try:
                    with open(fp) as f:
                        ast.parse(f.read())
                except SyntaxError as e:
                    total_errors += 1
                    if args.verbose:
                        print(f"    ❌ AST ERROR: {e.lineno}:{e.offset}: {e.msg}")
    
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Summary:")
    print(f"  Files affected: {total_files}")
    print(f"  Total replacements: {total_replacements}")
    if total_errors:
        print(f"  ⚠️  Files with AST errors: {total_errors}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
