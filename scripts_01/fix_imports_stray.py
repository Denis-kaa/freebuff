#!/usr/bin/env python3
"""Финальный ремонт: 'from X ]Y' -> 'from X import Y' и stray } .
"""
import ast, subprocess, re
from pathlib import Path

# Pattern: "from X ]Y" where ] should be "import"
FROM_REMOVED = re.compile(r'^(\s*from\s+\S+)\s+\](\w)')
# stray } on its own line (was an import that became })
STRAY_BRACE = re.compile(r'^(\s*)\}\s*$')

def repair_imports(src: str):
    lines = src.split('\n')
    notes = []
    for i, line in enumerate(lines):
        m = FROM_REMOVED.match(line)
        if m:
            indent_module, first_char = m.group(1), m.group(2)
            # restore "import" before the captured word
            rest = line[m.end():]
            lines[i] = f"{indent_module} import {first_char}{rest}"
            notes.append('L{}: ] -> import'.format(i+1))
            continue
        # stray } on a line that used to be an import
        if STRAY_BRACE.match(line):
            # check if prev/next are imports — if so, this was a removed import
            prev = lines[i-1] if i > 0 else ''
            nxt = lines[i+1] if i < len(lines)-1 else ''
            if 'import' in prev or 'import' in nxt:
                # delete this line (it was a stray })
                lines[i] = ''
                notes.append('L{}: stray }} (import context) removed'.format(i+1))
    return '\n'.join(lines), notes

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
        repaired, notes = repair_imports(src)
        if not notes:
            continue
        try:
            ast.parse(repaired)
            open(p, 'w', encoding='utf-8').write(repaired)
            fixed += 1
            print(f"FIXED {p}: {len(notes)}")
        except SyntaxError as e:
            still += 1
            if still <= 15:
                print(f"STILL {p}:{e.lineno} {e.msg}")
    print(f"--- fixed={fixed} still={still} ---")

if __name__ == '__main__':
    main()
