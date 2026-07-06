# -*- coding: utf-8 -*-
import pathlib, re
fns = [
    'output/ai/gpt-5-vs-gpt-4o-comparison.md',
    'output/exams/gre-text-completion-master-plan.md',
    'output/exams/ielts-writing-band-7-strategy.md',
    'output/exams/sat-math-no-calculator-700.md',
    'output/exams/toefl-reading-inference-strategy.md',
]
base = pathlib.Path(r'D:\codex\content-engine')
for fn in fns:
    p = base / fn
    t = p.read_text('utf-8')
    heads = re.findall(r'^#{1,6}\s', t, flags=re.M)
    rows = t.split('\n')
    table_cells = [r for r in rows if re.match(r'^\s*\|.*\|\s*$', r)]
    bullets = [r for r in rows if re.match(r'^\s*[-*]\s', r)]
    numbered = [r for r in rows if re.match(r'^\s*\d+[\.\)]\s', r)]
    print(f'{fn}:')
    print(f'  headings={len(heads)}  tableRows={len(table_cells)}  bullets={len(bullets)}  numbered={len(numbered)}')
    for b in bullets[:3]:
        print(f'    BUL: {b.strip()[:80]}')
    for r in numbered[:3]:
        print(f'    NUM: {r.strip()[:80]}')
    for tc in table_cells[:2]:
        print(f'    TBL: {tc.strip()[:120]}')
    print()
