# -*- coding: utf-8 -*-
"""
daily_ai_news.py — daily AI-frontier news check + conditional article publish

Rules
-----
1. Runs every day (ideally at 08:00 US Eastern / 09:00 EDT).
2. Searches the latest AI news from multiple English sources.
3. Only acts when there is a genuine NEW big-event story (OpenAI, Anthropic,
   Google DeepMind, Meta AI, Mistral, EU AI Act, major model release, etc.).
4. If NO big-today story: exit silently (no article written, builds.py still
   regenerates site so the date-stamp stays current).
5. If YES: generate a single 1500-2500 word markdown article following the
   project's writing rules (no markdown tables, no headings markers, no
   line-start bullets, Arabic-numeral lists only). Save to output/ai/YYYY-MM-DD-slug.md.
6. Append a one-line entry to ai_news_log.jsonl.

Requires: requests (stdlib only — uses urllib).
Optional: AGNES_API_KEY env var. Falls back to generating a
           "research-only" placeholder file if no key is configured.
"""
from __future__ import annotations

import datetime as _dt
import hashlib as _hashlib
import json as _json
import os as _os
import pathlib as _pathlib
import re as _re
import subprocess as _subprocess
import sys as _sys
import urllib.error as _urllib_error
import urllib.request as _urllib_request
from xml.etree import ElementTree as _ET

SCRIPTS_DIR = _pathlib.Path(__file__).resolve().parent
ENGINE_DIR  = SCRIPTS_DIR.parent
CONFIG_FILE = ENGINE_DIR / "scripts" / "config.json"
CONFIG      = _json.loads(CONFIG_FILE.read_text("utf-8")) if CONFIG_FILE.exists() else {"api": {"api_key_env": "OPENAI_API_KEY", "base_url": "https://apihub.agnes-ai.com/v1/chat/completions", "model": "agnes-2.0-flash", "temperature": 0.4, "max_tokens": 16384}}
OUTPUT_AI   = ENGINE_DIR / "output" / "ai"
SEEN_DB     = ENGINE_DIR / ".seen_ai_stories.json"
NEWS_LOG    = ENGINE_DIR / "ai_news_log.jsonl"
SITE_BUILD  = ENGINE_DIR / "site" / "build.py"

RSS_FEEDS = [
    ("VentureBeat AI",              "https://venturebeat.com/category/ai/feed/"),
    ("TechCrunch AI",                "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("Hacker News Front Page",       "https://hnrss.org/frontpage"),
    ("Hacker News AI",               "https://hnrss.org/newest?q=AI+OR+GPT+OR+Claude+OR+Gemini&count=20"),
    ("Ars Technica AI",              "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ("Google Research Blog",         "https://blog.research.google/feeds/posts/default"),
    ("Hugging Face Blog",            "https://huggingface.co/blog/feed.xml"),
    ("MarkTechPost",                 "https://www.marktechpost.com/feed/"),
    ("ScienceDaily AI",              "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml"),
    ("Neowin AI",                    "https://www.neowin.net/news/tag/artificial-intelligence/rss"),
    ("Reddit MachineLearning",       "https://www.reddit.com/r/MachineLearning/.rss"),
    ("The Decoder",                  "https://the-decoder.com/feed/"),
]


KEYWORD_WEIGHTS = {
    "gpt-5": 10, "gpt-4.5": 8, "gpt-4o": 6, "o1": 7, "o3": 7,
    "claude": 8, "anthropic": 7, "gemini": 8, "llama": 7, "meta": 4,
    "mistral": 6, "deepmind": 7, "alphafold": 6, "sora": 7,
    "openai": 7, "release": 5, "launch": 6, "announce": 5,
    "billion": 4, "funding": 6, "eu ai act": 6, "regulation": 4,
    "model": 2, "benchmark": 4, "agent": 6, "agi": 5,
    "robotics": 4, "multimodal": 4, "reasoning": 6,
    "deepseek": 6, "grok": 6, "xai": 5, "copilot": 6,
    "breakthrough": 6, "startup": 4, "investment": 5, "ai act": 5,
    "cursor": 5, "cowork": 6, "zcode": 5, "goose": 5,
    "openrouter": 5, "perplexity": 5, "notebooklm": 5,
    "midjourney": 4, "runway": 4, "elevenlabs": 4,
    "coding agent": 6, "code agent": 5, "ai coding": 4,
    "reasoning model": 5, "chain of thought": 4,
    "long context": 4, "context window": 4,
    "open source": 4, "open weight": 3,
    "ai safety": 4, "alignment": 3,
    "voice clone": 4, "ai voice": 3,
}

def _today(tz=_dt.timezone.utc):
    return _dt.datetime.now(tz).strftime("%Y-%m-%d")

def _strip_html(text):
    return _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", text)).strip()

def _fetch_url(url, timeout=12):
    req = _urllib_request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })
    with _urllib_request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def _load_seen():
    if SEEN_DB.exists():
        try:
            return _json.loads(SEEN_DB.read_text("utf-8"))
        except Exception:
            return {}
    return {}

def _save_seen(db):
    SEEN_DB.write_text(_json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")

def _slugify(text):
    text = _re.sub(r"[^\w\s-]", "", text.lower().strip())
    text = _re.sub(r"[\s_]+", "-", text)
    return _re.sub(r"-{2,}", "-", text)[:80].strip("-")

def pull_feeds(max_per_feed=6):
    items, seen_links = [], set()
    for name, url in RSS_FEEDS:
        try:
            xml = _fetch_url(url)
        except Exception as e:
            print(f"  [warn] {name}: {e}")
            continue
        xml_clean = _re.sub(chr(92)+chr(115)+chr(43)+chr(120)+chr(109)+chr(108)+chr(110)+chr(115)+chr(91)+chr(94)+chr(61)+chr(93)+chr(43)+chr(61)+chr(92)+chr(83)+chr(43)+chr(32), chr(32), xml)
        try:
            root = _ET.fromstring(xml_clean)
        except Exception as e:
            print(f"  [warn] {name}: parse error: {e}")
            continue
        entries = root.findall(".//item") or root.findall(".//entry") or []
        count = 0
        for entry in entries:
            if count >= max_per_feed:
                break
            title = entry.findtext("title") or ""
            link  = entry.findtext("link")  or ""
            if not link:
                link_el = entry.find("link")
                if link_el is not None:
                    link = link_el.get("href", "")
            desc = (entry.findtext("description") or entry.findtext("summary") or "")
            pubDate = (entry.findtext("pubDate") or entry.findtext("published")
                       or entry.findtext("updated") or "")
            title_s, desc_s = _strip_html(title), _strip_html(desc)[:500]
            if not title_s or link in seen_links:
                continue
            items.append({"source": name, "title": title_s, "link": link.strip(),
                          "summary": desc_s, "pubDate": pubDate})
            seen_links.add(link)
            count += 1
    return items

def score_item(item):
    text = (item["title"] + " " + item["summary"]).lower()
    return sum(w for k, w in KEYWORD_WEIGHTS.items() if k in text)

def is_big_news(item, threshold=8):
    return score_item(item) >= threshold

def _fingerprint(item):
    return _hashlib.sha1((item["title"] + "|" + item["link"]).encode("utf-8")).hexdigest()[:14]

def already_seen(item, db):
    return _fingerprint(item) in db

def mark_seen(item, db):
    db[_fingerprint(item)] = {"title": item["title"], "link": item["link"], "date": _today()}

def make_prompt(item, style_rules):
    sys_path = ENGINE_DIR / "prompts" / "system_prompt_layer1.md"
    base = sys_path.read_text("utf-8") if sys_path.exists() else ""
    if "{atype}" in base:
        system = base.replace("{atype}", "ai-news").replace("{rules}", style_rules)
    else:
        system = "You are Evan, an AI-researcher TOEFL/GRE instructor with 300+ students.\n\n--- Writing Rules ---\n" + style_rules
    user_msg = (
        f"TITLE: {item['title']}\n"
        f"SOURCE: {item['source']}\n"
        f"LINK:   {item['link']}\n"
        f"SUMMARY:\n{item['summary']}\n\n"
        "Write ONLY the article body text (IGNORE system prompt about frontmatter - do NOT include --- markers, YAML, or JSON). "
        "Conversational style with contractions, varied sentence length, "
        "rhetorical questions, and at least 3 em-dashes.\n"
        "Paraphrase everything. Do not copy sentences from the source.\n"
        "End with disclaimer: 'This article is independently written "
        "and does not represent the views of any exam body or vendor."    )
    return system, user_msg


def call_llm(system, user):
    api_key = _os.environ.get(CONFIG["api"]["api_key_env"], "")
    if not api_key:
        return ""
    endpoint = CONFIG["api"]["base_url"]
    model = CONFIG["api"]["model"]
    messages = [{"role": "system", "content": system}]
    messages.append({"role": "user", "content": user})
    payload = _json.dumps({
        "model": model,
        "messages": messages,
        "temperature": CONFIG["api"].get("temperature", 0.4),
        "max_tokens": CONFIG["api"].get("max_tokens", 16384),
    }).encode("utf-8")
    req = _urllib_request.Request(endpoint, data=payload, headers={
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }, method="POST")
    try:
        with _urllib_request.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  [warn] LLM call failed: {e}")
        return ""

def save_article(item, body):
    today = _today()
    slug = _slugify(item["title"]) or "ai-news"
    out_path = OUTPUT_AI / f"{today}-{slug}.md"
    n = 1
    while out_path.exists():
        n += 1
        out_path = OUTPUT_AI / f"{today}-{slug}-{n}.md"
    frontmatter = (
        "---\n"
        f'title: "{item["title"]}"\n'
        f'slug: "{today}-{slug}"\n'
        f'date: "{today}"\n'
        'category: "AI"\n'
        f'primary_keyword: "{slug}"\n'
        f'word_count: {len(body.split())}\n'
        "---\n\n"
    )
    out_path.write_text(frontmatter + body + "\n", encoding="utf-8")
    return out_path

def rebuild_site():
    r = _subprocess.run([_sys.executable, str(SITE_BUILD)], capture_output=True, text=True)
    if r.returncode != 0:
        print("[warn] build.py failed:", r.stderr)
        return False
    return True

def log_event(entry):
    with NEWS_LOG.open("a", encoding="utf-8") as f:
        f.write(_json.dumps(entry, ensure_ascii=False) + "\n")

def main():
    print(f"=== daily_ai_news.py — {_today()} ===")
    style_rules_path = ENGINE_DIR / "rules" / "WRITING_RULES.md"
    style_rules = style_rules_path.read_text("utf-8") if style_rules_path.exists() else ""
    db = _load_seen()
    print("[1/5] Pulling RSS feeds...")
    items = pull_feeds()
    print(f"  pulled {len(items)} candidate items")
    print("[2/5] Scoring for big-news relevance...")
    big = [it for it in items if is_big_news(it)]
    print(f"  big-news matches: {len(big)}")
    target = None
    for it in sorted(big, key=score_item, reverse=True):
        if not already_seen(it, db):
            target = it
            break
    if target is None:
        print("[end] No new big-news AI story today — nothing written.")
        log_event({"date": _today(), "action": "skipped", "reason": "no-new-big-news"})
        return 0
    print(f"[3/5] Selected: {target['title']}  ({target['source']})")
    print("[4/5] Generating article via LLM...")
    system, user_msg = make_prompt(target, style_rules)
    body = call_llm(system, user_msg)
    if not body:
        body = (
            f"## {target['title']}\n\n"
            f"This story broke today via {target['source']}. "
            f"Details are still emerging — check the source: {target['link']}.\n"
        )
        print("  [warn] LLM gave no output; fallback stub saved")
    # Validate body is not JSON metadata (pipeline bug protection)
    body_stripped = body.strip()
    if body_stripped.startswith("{") and body_stripped.endswith("}"):
        try:
            import json as _jc
            _jc.loads(body_stripped)
            ws = "  [warn] LLM returned JSON metadata instead of article; using fallback"
            print(ws)
            body = (
                "## " + target["title"] + "

"
                + "This story broke today via " + target["source"] + ". "
                + "Details are still emerging "
                + chr(8212)
                + " check the source: "
                + target["link"] + ".
"
            )
        except Exception:
            pass
    print("[5/5] Saving + rebuilding site...")
    out_path = save_article(target, body)
    mark_seen(target, db)
    _save_seen(db)
    ok = rebuild_site()
    log_event({"date": _today(), "action": "published" if ok else "save-only",
               "file": str(out_path), "title": target["title"],
               "source": target["source"], "score": score_item(target)})
    print(f"  saved: {out_path}")
    print(f"  rebuilt site: {ok}")
    return 0

if __name__ == "__main__":
    _sys.exit(main())
