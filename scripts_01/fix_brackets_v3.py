#!/usr/bin/env python3
"""Ремонт скобок v3: корректный трекинг тройных кавычек и f-strings.

Идея: токенизируем строку, отслеживая строковые литералы. Вне строк
ведём стек скобок. Если закрывающий символ не совпадает с вершиной —
меняем на правильный.
"""
import ast, subprocess, sys
from pathlib import Path

PAIRS = {')': '(', ']': '[', '}': '{'}
OPENS = set(PAIRS.values())
CLOSES = set(PAIRS.keys())
INV = {v: k for k, v in PAIRS.items()}

def repair(src: str):
    lines = src.split('\n')
    out = []
    notes = []

    in_triple = None  # '"""' or "'''"
    stack = []  # persist across lines!
    # simple per-line char scan, but in_triple persists across lines
    for ln_no, line in enumerate(lines, 1):
        result = []
        i = 0
        L = len(line)
        in_str = None  # ' " (simple single-quoted string)

        while i < L:
            ch = line[i]

            # Inside triple-quoted string
            if in_triple:
                if line[i:i+3] == in_triple:
                    result.append(in_triple)
                    in_triple = None
                    i += 3
                    continue
                result.append(ch)
                i += 1
                continue

            # Check triple-quote start (must check before single)
            if not in_str:
                if line[i:i+3] == '"""':
                    result.append('"""')
                    in_triple = '"""'
                    i += 3
                    continue
                if line[i:i+3] == "'''":
                    result.append("'''")
                    in_triple = "'''"
                    i += 3
                    continue

            # Inside simple string
            if in_str:
                if ch == '\\':
                    result.append(ch)
                    if i+1 < L:
                        result.append(line[i+1])
                        i += 2
                    else:
                        i += 1
                    continue
                if ch == in_str:
                    result.append(ch)
                    in_str = None
                    i += 1
                    continue
                result.append(ch)
                i += 1
                continue

            # Not in any string
            # Check string start (simple quote)
            if ch in ('"', "'"):
                # could be f-string prefix — check back
                result.append(ch)
                in_str = ch
                i += 1
                continue

            if ch in OPENS:
                stack.append(ch)
                result.append(ch)
                i += 1
                continue

            if ch in CLOSES:
                if stack and stack[-1] == PAIRS[ch]:
                    stack.pop()
                    result.append(ch)
                elif stack:
                    correct = INV[stack[-1]]
                    stack.pop()
                    result.append(correct)
                    notes.append(f"L{ln_no}: {ch}->{correct}")
                else:
                    # stray closer — remove (don't append)
                    notes.append(f"L{ln_no}: stray {ch}")
                i += 1
                continue

            result.append(ch)
            i += 1

        # End of line
        if in_str and not in_triple:
            # single-line string ended by newline — close it implicitly
            in_str = None

        out.append(''.join(result))

    return '\n'.join(out), notes

def main():
    r = subprocess.run(['git','ls-files','*.py'], capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent)
    files = [f for f in r.stdout.strip().split('\n') if f]
    fixed = 0
    still = 0
    for p in files:
        try:
            src = open(p, 'r', encoding='utf-8', errors='replace').read()
            ast.parse(src)
            continue
        except SyntaxError:
            pass
        repaired, notes = repair(src)
        if not notes:
            continue
        try:
            ast.parse(repaired)
            open(p, 'w', encoding='utf-8').write(repaired)
            fixed += 1
            if fixed <= 10:
                print(f"FIXED {p}: {len(notes)} fixes")
        except SyntaxError as e:
            still += 1
            if still <= 15:
                print(f"STILL {p}:{e.lineno} {e.msg}")
    print(f"--- fixed={fixed} still={still} ---")

if __name__ == '__main__':
    main()
