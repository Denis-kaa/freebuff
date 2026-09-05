#!/usr/bin/env python3
"""Fix ***REMOVED*** corruption across Python files — v5.

Key insight: each REMOVED keyword represents exactly ONE closing bracket.
Stars between adjacent REMOVEDs are artifacts from the corruption process.

Algorithm:
1. Find all REMOVED keyword positions
2. Strip stars from between adjacent REMOVEDs (they're noise)
3. Process the file tracking bracket nesting in clean segments
4. Each REMOVED gets the appropriate closing bracket from the stack

Usage:
    python3 fix_removed_v5.py [--dry-run] [--verbose] [--dirs DIR1 DIR2 ...]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def fix_content(content: str) -> str:
    """Fix all REMOVED tokens using full-file bracket tracking."""
    
    # Step 1: Find all REMOVED keyword positions
    removed_positions = [m.start() for m in re.finditer('REMOVED', content)]
    
    if not removed_positions:
        return content
    
    # Step 2: Build replacement plan
    # For each REMOVED, we need to:
    # a) Strip the stars around it (replace with standard marker)
    # b) Strip star-only segments between adjacent REMOVEDs
    # c) Track bracket nesting to determine the correct closer
    
    # Build segments: alternating clean_text and removed_markers
    segments = []
    last_end = 0
    
    for i, pos in enumerate(removed_positions):
        # Find the extent of this REMOVED token (including surrounding stars)
        # But don't consume stars that belong to the next REMOVED
        
        # Start: go back to find stars, but stop before previous token's end
        start = pos
        prev_end = segments[-1][2] if segments and segments[-1][0] == 'removed' else last_end
        while start > prev_end and content[start - 1] == '*':
            start -= 1
        
        # End: go forward to find stars, but stop before next REMOVED's start
        next_pos = removed_positions[i + 1] if i + 1 < len(removed_positions) else len(content)
        end = pos + 7  # len('REMOVED')
        while end < next_pos and content[end] == '*':
            end += 1
        
        # Clean segment before this REMOVED
        clean_before = content[last_end:start]
        
        # Strip star-only content from clean_before (artifacts between adjacent REMOVEDs)
        # But only if the entire clean segment is stars
        if clean_before and not clean_before.strip('*'):
            clean_before = ''  # Star-only artifact — remove
        
        if clean_before:
            segments.append(('clean', clean_before, last_end, start))
        
        segments.append(('removed', '', start, end))
        last_end = end
    
    # Remaining clean segment
    if last_end < len(content):
        segments.append(('clean', content[last_end:], last_end, len(content)))
    
    # Step 3: Process segments, tracking bracket nesting
    stack = []  # list of (char, segment_index)
    result = []
    
    for seg in segments:
        if seg[0] == 'clean':
            text = seg[1]
            # Track brackets in clean text, skip strings and comments
            j = 0
            while j < len(text):
                ch = text[j]
                
                # Skip strings
                if ch in ('"', "'"):
                    if text[j:j+3] in ('"""', "'''"):
                        quote = text[j:j+3]
                        end_q = text.find(quote, j + 3)
                        if end_q == -1:
                            j = len(text)
                        else:
                            j = end_q + 3
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
                    stack.append(ch)
                elif ch in (')', ']', '}'):
                    expected = {'(': ')', '[': ']', '{': '}'}
                    if stack and expected.get(stack[-1]) == ch:
                        stack.pop()
                
                j += 1
            
            result.append(text)
        
        elif seg[0] == 'removed':
            # Determine what closer this REMOVED should be
            if stack:
                opener = stack.pop()
                closer = {'(': ')', '[': ']', '{': '}'}[opener]
            else:
                # No unmatched openers — use context
                # Look at what's in the result so far
                context = ''.join(result[-3:]) if len(result) >= 3 else ''.join(result)
                last_openers = []
                for ch in reversed(context):
                    if ch in (')', ']', '}'):
                        # This is a closer, skip
                        pass
                    elif ch in ('(', '[', '{'):
                        last_openers.append(ch)
                        break
                    elif ch == ',' or ch == ' ':
                        continue
                    else:
                        break
                
                if last_openers:
                    opener = last_openers[0]
                    closer = {'(': ')', '[': ']', '{': '}'}[opener]
                else:
                    closer = '}'  # default for standalone
            
            result.append(closer)
    
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
    
    count = content.count('REMOVED')
    
    fixed = fix_content(content)
    
    # Verify: no REMOVED should remain
    remaining = fixed.count('REMOVED')
    if remaining > 0:
        if verbose:
            print(f"  WARNING: {filepath}: {remaining} REMOVED tokens remaining after fix")
    
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
