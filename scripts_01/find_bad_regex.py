#!/usr/bin/env python3
"""Найти .py файлы, где re.compile/re.match/re.search падают с PatternError.
Ищет повреждённые regex-паттерны (последствие ***REMOVED*** коррупции).
"""
import ast, re, subprocess, sys
from pathlib import Path

# extract all string literals that look like regex patterns
REGEX_FUNCS = {'compile', 'match', 'search', 'findall', 'sub', 'finditer', 'split', 'fullmatch'}

def find_regex_calls(src: str):
    """Извлекает все вызовы re.X(...) и их строковые аргументы."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in REGEX_FUNCS:
                # Check if first arg is a string literal
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    pattern = node.args[0].value
                    try:
                        re.compile(pattern)
                    except re.error as e:
                        results.append((node.lineno, pattern, str(e)))
    return results

def main():
    r = subprocess.run(['git','ls-files','*.py'], capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent)
    files = [f for f in r.stdout.strip().split('\n') if f]
    bad = 0
    for p in files:
        try:
            src = open(p, 'r', encoding='utf-8', errors='replace').read()
            ast.parse(src)
        except SyntaxError:
            continue
        issues = find_regex_calls(src)
        if issues:
            bad += 1
            for ln, pat, err in issues[:3]:
                print(f"{p}:{ln} PATTERN={pat!r} ERR={err}")
    print(f"--- files with bad regex: {bad} ---")

if __name__ == '__main__':
    main()
