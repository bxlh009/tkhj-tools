# Task

Write an evidence-first AI article in English for TKHJ Tools.

Primary topic: {primary_keyword}
Supporting search phrases: {long_tail_keywords}
Requested slug: {slug}
Date: {current_date}
Length: {min_words}-{max_words} words

# Supplied sources

{source_urls}

# Required result

1. Separate confirmed source claims from editorial interpretation.
2. Explain what changed and who is affected.
3. Give a concrete decision, workflow, or small reversible test.
4. Include `## Limits and uncertainty`.
5. Include `## When to use it` or `## When to skip it`.
6. End with `## Sources` and reproduce only the supplied URLs.

# Truth constraints

- Do not claim hands-on testing, benchmarks, time savings, prices, user reactions,
  quotes, or product experience unless supplied source material contains them.
- Never invent an interview, persona, screenshot, metric, or URL.
- Do not turn one announcement into a broad industry prediction.
- If evidence is insufficient, explicitly narrow the article.
- Do not add YAML frontmatter; the pipeline creates it.
- Use normal Markdown headings and lists.
- Do not use hype, forced emotion, deliberate typos, or filler FAQs.
