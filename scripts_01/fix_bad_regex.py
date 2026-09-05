#!/usr/bin/env python3
"""Ремонт битых regex-паттернов (последствие ***REMOVED*** коррупции).

Паттерны повреждений:
  - `)+` → `]+` (char class closer был заменён на `)`)
  - `{N)` → `{N}` (quantifier brace)
  - `(\d+)` → `(\d+)` (capturing group)
  - и т.д.

Проверяет каждый regex через re.compile, пишет только при успехе.
"""
import ast, re, subprocess
from pathlib import Path

REGEX_FUNCS = {'compile', 'match', 'search', 'findall', 'sub', 'finditer', 'split', 'fullmatch'}

def fix_regex(pattern: str) -> str:
    """Простой эвристический ремонт regex-паттерна."""
    # Replace `)+` with `]+` (most common: char class closer replaced by `)`)
    # But careful: `)+` could also be a valid group repetition
    # Heuristic: if regex fails to compile, try swapping `)` → `]` near `)+`
    
    # Strategy: try multiple swaps, validate with re.compile
    candidates = [pattern]
    
    # Swap `)+` → `]+` (char class closer)
    if ')+(' in pattern or ')+$' in pattern or ')+\\' in pattern:
        candidates.append(pattern.replace(')+', ']+'))
    
    # Swap `{N)` → `{N}` (quantifier)
    if re.search(r'\{\d+\)', pattern):
        candidates.append(re.sub(r'\{(\d+)\)', r'{\1}', pattern))
    
    # Swap `\d{3))` → `\d{3})` (double close paren)
    if '))' in pattern and '\\d{' in pattern:
        candidates.append(pattern.replace('))', '})'))
    
    # Swap `\d{2]` → `\d{2}` (brace replaced by bracket)
    if re.search(r'\{\d+\]', pattern):
        candidates.append(re.sub(r'\{(\d+)\]', r'{\1}', pattern))
    
    # Swap `(\d{4)` → `(\d{4})` 
    if re.search(r'\(\d+\{', pattern):
        candidates.append(pattern)  # keep
    
    # Try each candidate, return first that compiles
    for c in candidates:
        try:
            re.compile(c)
            return c
        except re.error:
            continue
    
    return pattern  # no fix found

def process_file(p: str) -> int:
    """Process a single .py file, fix broken regex patterns in-place. Return count of fixes."""
    try:
        src = open(p, 'r', encoding='utf-8', errors='replace').read()
        tree = ast.parse(src)
    except SyntaxError:
        return 0
    
    # Collect all (lineno, col_offset, end_col_offset, new_value) fixes
    fixes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in REGEX_FUNCS:
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                pattern = node.args[0].value
                try:
                    re.compile(pattern)
                except re.error:
                    fixed = fix_regex(pattern)
                    if fixed != pattern:
                        try:
                            re.compile(fixed)
                            fixes.append((node.args[0].lineno, node.args[0].col_offset, node.args[0].end_col_offset, fixed))
                        except re.error:
                            pass
    
    if not fixes:
        return 0
    
    # Apply fixes (sort by lineno desc so offsets don't shift)
    lines = src.split('\n')
    # Build per-line fixes
    fixes.sort(key=lambda x: (x[0], -x[1]))  # last first
    for lineno, col_off, end_col_off, new_val in fixes:
        # lineno is 1-based
        line_idx = lineno - 1
        if line_idx >= len(lines):
            continue
        line = lines[line_idx]
        # col_off is 0-based char offset within the line
        # ast uses UTF-8 byte offsets in some Python versions, but Python 3.8+ uses unicode char offsets
        # Replace by line slicing
        # Need to be careful — ast offsets may not match if file has tabs or weird whitespace
        # Just do a substring replacement of the old pattern value instead
        pass  # we'll use direct replacement below
    
    # Simpler approach: for each broken pattern, find and replace the exact string in source
    for lineno, col_off, end_col_off, new_val in fixes:
        line_idx = lineno - 1
        if line_idx >= len(lines):
            continue
        # Read line, find the pattern string and replace
        old_val_repr = None
        # We don't have old pattern value easily, but we can extract from the AST node
        # Actually, let's just do a direct string replacement by finding the raw repr
    
    return len(fixes)

def main():
    r = subprocess.run(['git','ls-files','*.py'], capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent)
    files = [f for f in r.stdout.strip().split('\n') if f]
    total_fixes = 0
    files_fixed = 0
    
    for p in files:
        try:
            src = open(p, 'r', encoding='utf-8', errors='replace').read()
            tree = ast.parse(src)
        except SyntaxError:
            continue
        
        # Find broken regex patterns and fix them
        # We need to find the original pattern strings and their replacements
        fixes = []  # (old_pattern_str, new_pattern_str, node)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in REGEX_FUNCS:
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    pattern = node.args[0].value
                    try:
                        re.compile(pattern)
                    except re.error:
                        fixed = fix_regex(pattern)
                        if fixed != pattern:
                            try:
                                re.compile(fixed)
                                fixes.append((pattern, fixed))
                            except re.error:
                                pass
        
        if not fixes:
            continue
        
        # Apply fixes: for each (old, new), find the raw repr of `old` in source and replace with repr of `new`
        # The pattern is stored as a string literal; we need to find `r"old"` or `"old"` or `r'old'` etc.
        new_src = src
        for old_pat, new_pat in fixes:
            # Try various quote styles
            for prefix in ('r"', 'r\'', '"', '\''):
                old_str = prefix + old_pat
                # Find the matching close quote
                # This is tricky; just do a direct find/replace of the exact `old_pat` substring
                pass
            # Simplest: replace old_pat → new_pat directly (they're unique enough)
            if old_pat in new_src:
                new_src = new_src.replace(old_pat, new_pat, 1)
        
        if new_src != src:
            try:
                ast.parse(new_src)
                open(p, 'w', encoding='utf-8').write(new_src)
                files_fixed += 1
                total_fixes += len(fixes)
                print(f"FIXED {p}: {len(fixes)} regex patterns")
            except SyntaxError as e:
                print(f"STILL {p}:{e.lineno} {e.msg}")
    
    print(f"--- files fixed: {files_fixed}, patterns: {total_fixes} ---")

if __name__ == '__main__':
    main()
