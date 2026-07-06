# -*- coding: utf-8 -*-
"""Quick smoke-test for daily_ai_news scoring logic."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import daily_ai_news as dan
items = [
    {'title': 'OpenAI launches GPT-5 with new reasoning', 'summary': 'Major release', 'source': 'OpenAI'},
    {'title': 'Random cat video goes viral', 'summary': 'Cute cats', 'source': 'Twitter'},
    {'title': 'Anthropic Claude 4 Opus released', 'summary': 'New model launch', 'source': 'Anthropic'},
    {'title': 'EU AI Act passed', 'summary': 'Regulation approved', 'source': 'EU'},
    {'title': 'Mistral releases new open-weight model', 'summary': 'Open weights launch', 'source': 'Mistral'},
    {'title': 'Some blog post about productivity', 'summary': 'Tips and tricks', 'source': 'Blog'},
]
print('Score  Big?    Title')
print('-' * 70)
for it in items:
    score = dan.score_item(it)
    big = dan.is_big_news(it)
    print(f'{score:3d}   {str(big):5s}   {it["title"]}')
print()
today = dan._today()
slug = dan._slugify('OpenAI launches GPT-5 with reasoning')
print(f'today={today}  slug={slug}')
print('expected: OpenAI->big, Anthropic->big, EU->maybe, Mistral->big, cat->no')
print('OK' if dan.is_big_news(items[0]) else 'FAIL')
