# -*- coding: utf-8 -*-
import pathlib, re
base = pathlib.Path(r'D:\codex/content-engine/site/_site')
print('=== Per-article body audit ===')
articles = [
    'exam/article/ielts-writing-band-7-strategy.html',
    'exam/article/gre-text-completion-master-plan.html',
    'exam/article/toefl-reading-inference-strategy.html',
    'ai/article/gpt-5-vs-gpt-4o-comparison.html',
]
for fn in articles:
    p = base / fn
    if not p.exists():
        print(f'{fn}: MISSING')
        continue
    html = p.read_text('utf-8')
    body_start = html.find('<div class="article-body">')
    body_end = html.find('</article>')
    body = html[body_start:body_end] if body_start >= 0 and body_end >= 0 else ''
    heads = len(re.findall(r'<h[1-6]>', body))
    tables = body.count('<table') + body.count('<td') + body.count('<th')
    bullets = body.count('<li')
    print(f'{pathlib.Path(fn).name:45} headings={heads} tables={tables} bullets={bullets}')
# Global checks
index_html = (base / 'index.html').read_text('utf-8')
print()
print('=== Global checks ===')
print('flagged emoji 🎓 absent:', '🎓' not in index_html)
print('flagged emoji 🤖 absent:', '🤖' not in index_html)
print('icons.js ref absent   :', 'icons.js' not in index_html)
print('data-lucide absent    :', 'data-lucide=' not in index_html)
print('SUN_SVG / MOON_SVG absent:', 'SUN_SVG' not in index_html and 'MOON_SVG' not in index_html)
