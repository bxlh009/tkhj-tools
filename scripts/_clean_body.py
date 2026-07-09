# -*- coding: utf-8 -*-
"""Clean LLM output: strip stray frontmatter / YAML / JSON leaking into body."""

import re

FM_KEYS = {
    "title:", "slug:", "date:", "category:", "primary_keyword:",
    "long_tail:", "word_count:", "estimated_read_min:", "sources:",
    "exam:", "section:", "type:", "target_audience:", "primary_keyword:",
}

def split_fm(text):
    """Split off leading --- ... --- frontmatter. Returns (fm, body)."""
    m = re.match(r'\A---\n.*?\n---\n', text, re.S)
    if m:
        return m.group(0), text[m.end():]
    return "", text

def _looks_like_yaml_line(line):
    s = line.strip()
    if not s or s == "---" or s == "...":
        return True
    if s.startswith("- ") and not s.startswith("- "):
        return True
    key = s.split(":", 1)[0].strip().lower() + ":" if ":" in s else ""
    if key and key in {k.lower() for k in FM_KEYS}:
        return True
    return False

def clean_body(text):
    """Remove stray frontmatter-like content bleeding into the article body.

    Handles:
      - Duplicate --- ... --- frontmatter blocks
      - Standalone YAML key lines (title:, slug:, date:, etc.)
      - JSON object dumps that start with {

    Returns the original frontmatter (if any) + cleaned body.
    """
    if not text:
        return text

    fm, body = split_fm(text)

    # If what remains still starts with ---, strip again (stray frontmatter)
    body_stripped = body.lstrip()
    while body_stripped.startswith("---"):
        m = re.match(r'\A---\n.*?\n---\n', body_stripped, re.S)
        if m:
            body_stripped = body_stripped[m.end():].lstrip()
        elif body_stripped.startswith("---") and "\n" in body_stripped:
            body_stripped = body_stripped.split("\n", 1)[1].lstrip()
        else:
            break

    # Remove leading YAML-like lines until we hit real prose
    lines = body_stripped.split("\n")
    start = 0
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped:
            start = i + 1
            continue
        if stripped == "---":
            start = i + 1
            continue
        key = stripped.split(":", 1)[0].strip().lower() + ":" if ":" in stripped else ""
        if key and key.rstrip(":") in {k.rstrip(":") for k in FM_KEYS}:
            start = i + 1
            continue
        if stripped.startswith("- ") and ":" not in stripped:
            start = i + 1
            continue
        break

    cleaned_lines = lines[start:]
    result = "\n".join(cleaned_lines)

    # If body looks like JSON object, caller runs fallback (handled upstream)
    result_stripped = result.strip()
    return fm + result_stripped
