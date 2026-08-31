#!/usr/bin/env python3
"""Простой ремонт скобок: построчно, трекинг строк через простые
правила. Если закрывающий не совпадает с вершиной стека — меняем.
"""
import ast, subprocess, sys
from pathlib import Path

def repair_line_by_line(src: str):
    lines = src.split('\n')
    out = []
    notes = []
    for ln, line in enumerate(lines, 1):
        stack = []
        result = []
        in_str = None  # ' " f" f'
        in_triple = False
        i = 0
        L = len(line)
        while i < L:
            ch = line[i]
            # triple quotes
            if not in_str and not in_triple:
                for tq in ('"""', "'''", 'r"""', "r'''"):
                    if line[i:i+len(tq)] == tq:
                        in_triple = True
                        result.append(tq)
                        i += len(tq)
                        break
                else:
                    # f-string
                    if line[i:i+2] in ('f"', "f'") or line[i:i+3] in ('rf"', "rf'"):
                        prefix_len = 2 if line[i] == 'f' and line[i+1] in '"\'' else 3
                        in_str = line[i + prefix_len - 1]
                        result.append(line[i:i+prefix_len])
                        i += prefix_len
                        continue
                    if ch in ('"', "'"):
                        in_str = ch
                        result.append(ch)
                        i += 1
                        continue
                    if ch in '([{':
                        stack.append(ch)
                        result.append(ch)
                        i += 1
                        continue
                    if ch in ')]}':
                        pairs = {')':'(', ']':'[', '}':'{'}
                        if stack and stack[-1] == pairs[ch]:
                            stack.pop()
                            result.append(ch)
                        elif stack:
                            correct = {v:k for k,v in pairs.items()}[stack[-1]]
                            stack.pop()
                            result.append(correct)
                            notes.append(f"L{ln}: {ch}->{correct}")
                        else:
                            # stray — remove
                            notes.append(f"L{ln}: stray {ch}")
                        i += 1
                        continue
                    result.append(ch)
                    i += 1
                    continue
                continue
            if in_triple:
                # check for closing triple
                close_tq = '"""' if ('"""' in ''.join(result[-3:])) else "'''"
                if line[i:i+3] == close_tq:
                    result.append(close_tq)
                    in_triple = False
                    i += 3
                    continue
                result.append(ch)
                i += 1
                continue
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
                # f-string { }
                if line[i-1:i] == '{' or (i>=1 and line[i-1]=='{' and ch != '}'):
                    # wait — we need to track { in f-string
                    pass
                result.append(ch)
                i += 1
                continue
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
        repaired, notes = repair_line_by_line(src)
        if not notes:
            continue
        try:
            ast.parse(repaired)
            open(p, 'w', encoding='utf-8').write(repaired)
            fixed += 1
            if fixed <= 10:
                print(f"FIXED {p}: {len(notes)}")
        except SyntaxError as e:
            still += 1
            if still <= 10:
                print(f"STILL {p}:{e.lineno} {e.msg}")
    print(f"--- fixed={fixed} still={still} ---")

if __name__ == '__main__':
    main()
