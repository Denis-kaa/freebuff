#!/usr/bin/env python3
"""Fix ***REMOVED*** corruption across Python files — v4 (tokenize-by-keyword).

Strategy:
1. Split content on 'REMOVED' keyword boundaries
2. Each segment between REMOVEDs is "clean" Python
3. For each REMOVED occurrence, determine the correct closing bracket
   by tracking bracket nesting in the clean segments

Usage:
    python3 fix_removed_v4.py [--dry-run] [--verbose] [--dirs DIR1 DIR2 ...]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def tokenize(content: str):
    """Split content into alternating clean_segments and removed_positions.
    
    Returns list of (type, value) tuples:
    - ('clean', text) - regular Python code
    - ('removed', position_in_content, before_stars, after_stars) - REMOVED token
    """
    tokens = []
    pos = 0
    
    for m in re.finditer(r'REMOVED', content):
        # Clean segment before this REMOVED
        if m.start() > pos:
            tokens.append(('clean', content[pos:m.start()]))
        
        # Count stars before REMOVED
        before_start = m.start()
        while before_start > 0 and content[before_start - 1] == '*':
            before_start -= 1
        before_stars = m.start() - before_start
        
        # Count stars after REMOVED
        after_end = m.end()
        while after_end < len(content) and content[after_end] == '*':
            after_end += 1
        after_stars = after_end - m.end()
        
        tokens.append(('removed', m.start(), before_stars, after_stars))
        pos = after_end
    
    # Remaining clean segment
    if pos < len(content):
        tokens.append(('clean', content[pos:]))
    
    return tokens


def fix_content(content: str) -> str:
    """Fix all REMOVED tokens in content using bracket nesting context."""
    tokens = tokenize(content)
    
    # Track bracket nesting state
    stack = []  # list of (char, position)
    
    # First, process all clean segments to build the nesting state
    # Then resolve REMOVED tokens
    
    result = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        if token[0] == 'clean':
            text = token[1]
            # Track brackets in clean text, skip strings and comments
            j = 0
            while j < len(text):
                ch = text[j]
                
                # Skip strings
                if ch in ('"', "'"):
                    if text[j:j+3] in ('"""', "'''"):
                        quote = text[j:j+3]
                        end = text.find(quote, j + 3)
                        if end == -1:
                            j = len(text)
                        else:
                            j = end + 3
                        continue
                    else:
                        j += 1
                        while j < len(text):
                            if text[j] == '\\':
                                j += 2
                                continue
                            if text[j] == ch:
                                j += 1
                                break
                            j += 1
                        continue
                
                # Skip comments
                if ch == '#':
                    break
                
                if ch in ('(', '[', '{'):
                    stack.append((ch, len(result)))
                elif ch in (')', ']', '}'):
                    expected = {'(': ')', '[': ']', '{': '}'}
                    if stack and expected.get(stack[-1][0]) == ch:
                        stack.pop()
                
                j += 1
            
            result.append(text)
        
        elif token[0] == 'removed':
            pos, before_stars, after_stars = token[1], token[2], token[3]
            
            # Determine what closer this REMOVED should be
            if stack:
                opener_char, _ = stack[-1]
                closer = {'(': ')', '[': ']', '{': '}'}[opener_char]
                stack.pop()
            else:
                # No unmatched openers - use context clues
                closer = ']'  # default
            
            result.append(closer)
        
        i += 1
    
    return ''.join(result)


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
    
    # Count REMOVED occurrences
    count = content.count('REMOVED')
    
    # Fix
    fixed = fix_content(content)
    
    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed)
    
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
