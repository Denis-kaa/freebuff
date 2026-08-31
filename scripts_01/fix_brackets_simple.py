#!/usr/bin/env python3
"""Однопроходный ремонт скобок: заменяет неверный закрывающий
на тот, что соответствует вершине стека.

Например:  {... value]  →  {... value}
            (func(x)]   →  (func(x))

Работает построчно с трекингом строк (f-strings, тройные кавычки,
кавычки). Файл записывается только если ast.parse проходит.
"""
import ast, re, sys, subprocess
from pathlib import Path

MARKER = re.compile(r'\*{2,3}REMOVED\*{2,3}')

def repair_text(src: str) -> tuple[str, list[str]]:
    lines = src.split('\n')
    out_lines = []
    notes = []
    stack = []  # (char, line_no)

    in_triple = None  # tracking """ or '''
    in_line_str = None  # ' or "
    in_fstring = False  # inside f"..."

    for li, line in enumerate(lines, 1):
        result = []
        i = 0
        while i < len(line):
            ch = line[i]

            # Check triple quotes
            if not in_line_str and not in_triple:
                for tq in ('"""', "'''"):
                    if line[i:i+3] == tq:
                        in_triple = tq
                        result.append(tq)
                        i += 3
                        break
                else:
                    # Check f-string start
                    if not in_line_str and line[i:i+2] == 'f"' or line[i:i+2] == "f'" or line[i:i+3] == 'rf"' or line[i:i+3] == "rf'":
                        q = line[i+1] if line[i] == 'f' else line[i+2]
                        in_line_str = q
                        in_fstring = True
                        result.append(line[i:i+2] if line[i] == 'f' else line[i:i+3])
                        i += 2 if line[i] == 'f' else 3
                        continue
                    # Check normal string start
                    if ch in ('"', "'"):
                        in_line_str = ch
                        result.append(ch)
                        i += 1
                        continue
                    result.append(ch)
                    i += 1
                    continue
                continue

            # Inside triple quote
            if in_triple:
                if line[i:i+3] == in_triple:
                    result.append(in_triple)
                    in_triple = None
                    i += 3
                else:
                    result.append(ch)
                    i += 1
                continue

            # Inside line string
            if in_line_str:
                if ch == '\\':
                    result.append(ch)
                    if i+1 < len(line):
                        result.append(line[i+1])
                        i += 2
                    else:
                        i += 1
                    continue
                # f-string { opens nested expression
                if in_fstring and ch == '{':
                    stack.append(('{', li, True))  # fstring brace
                    result.append(ch)
                    i += 1
                    continue
                if in_fstring and ch == '}':
                    # pop to matching {
                    while stack and stack[-1][0] != '{':
                        stack.pop()
                        notes.append(f"L{li}: closed stray {stack[-1][0] if stack else '?'} via }}")
                    if stack:
                        stack.pop()
                    result.append(ch)
                    i += 1
                    continue
                if ch == in_line_str:
                    result.append(ch)
                    in_line_str = None
                    in_fstring = False
                    i += 1
                    continue
                result.append(ch)
                i += 1
                continue

            # Outside strings
            if ch in ('(', '[', '{'):
                stack.append((ch, li, False))
                result.append(ch)
            elif ch in (')', ']', '}'):
                expected = {')': '(', ']': '[', '}': '{'}
                if stack and stack[-1][0] == expected[ch]:
                    stack.pop()
                    result.append(ch)
                elif stack and stack[-1][0] != expected[ch]:
                    # Wrong closer — replace with correct one
                    correct = {v: k for k, v in expected.items()}[stack[-1][0]]
                    stack.pop()
                    result.append(correct)
                    notes.append(f"L{li}: {ch} -> {correct}")
                else:
                    # Stray closer — remove it
                    notes.append(f"L{li}: stray {ch} removed")
                    # don't append
            else:
                result.append(ch)
            i += 1

        # End of line: close line string if still open (newline ends it)
        if in_line_str and not in_triple:
            in_line_str = None
            in_fstring = False

        out_lines.append(''.join(result))

    return '\n'.join(out_lines), notes

def main():
    r = subprocess.run(['git','ls-files','*.py'], capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent)
    files = [f for f in r.stdout.strip().split('\n') if f]
    fixed = 0
    failed = 0
    for p in files:
        try:
            src = open(p, 'r', encoding='utf-8', errors='replace').read()
            ast.parse(src)
            continue  # already ok
        except SyntaxError:
            pass
        repaired, notes = repair_text(src)
        if not notes:
            continue
        try:
            ast.parse(repaired)
            open(p, 'w', encoding='utf-8').write(repaired)
            fixed += 1
            if fixed <= 5:
                print(f"FIXED {p}: {len(notes)} fixes")
        except SyntaxError as e:
            failed += 1
            if failed <= 10:
                print(f"STILL BROKEN {p}:{e.lineno} {e.msg}")
    print(f"--- DONE --- fixed={fixed} still_broken={failed}")

if __name__ == '__main__':
    main()
