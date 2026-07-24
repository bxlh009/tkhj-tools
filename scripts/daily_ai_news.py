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
Requires: AGNES_API_KEY. Empty responses and low-quality drafts are rejected.
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

from content_quality import evaluate_article
from publish_article import publish

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
    ("Hacker News AI",               "https://hnrss.org/newest?q=AI+OR+GPT+OR+Claude+OR+Gemini+OR+DeepSeek+OR+Llama" + "&count=30"),
    ("Hacker News Prompt Eng",       "https://hnrss.org/newest?q=prompt+engineering+OR+LLM+OR+coding+agent" + "&count=20"),
    ("Ars Technica AI",              "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ("Google Research Blog",         "https://blog.research.google/feeds/posts/default"),
    ("Google News AI",               "https://news.google.com/rss/search?q=AI+artificial+intelligence+model+release" + "&hl=en-US&gl=US&ceid=US:en"),
    ("Google News AI Tools",         "https://news.google.com/rss/search?q=AI+tool+prompt+engineering+workflow" + "&hl=en-US&gl=US&ceid=US:en"),
    ("Hugging Face Blog",            "https://huggingface.co/blog/feed.xml"),
    ("MarkTechPost",                 "https://www.marktechpost.com/feed/"),
    ("ScienceDaily AI",              "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml"),
    ("Neowin AI",                    "https://www.neowin.net/news/tag/artificial-intelligence/rss"),
    ("Reddit MachineLearning",       "https://www.reddit.com/r/MachineLearning/.rss"),
    ("Reddit LocalLLaMA",            "https://www.reddit.com/r/LocalLLaMA/.rss"),
    ("The Decoder",                  "https://the-decoder.com/feed/"),
    ("Analytics Vidhya",             "https://www.analyticsvidhya.com/feed/"),
    ("AI Business",                  "https://aibusiness.com/feed"),
    ("MIT AI News",                  "https://news.mit.edu/topic/artificial-intelligence2/rss"),
    ("Prompt Engineering Guide",     "https://www.promptingguide.ai/rss.xml"),
]

EVERGREEN_TOPICS = [
    {
        "title": "Debug an AI Prompt with a Small Test Set",
        "source": "Google AI for Developers",
        "link": "https://ai.google.dev/gemini-api/docs/prompting-strategies",
        "summary": "Turn prompt iteration into a repeatable test process using clear instructions, varied examples, and observed failures.",
        "kind": "evergreen",
    },
    {
        "title": "Verify an AI Answer Before It Enters Your Notes",
        "source": "NIST AI Resource Center",
        "link": "https://airc.nist.gov/",
        "summary": "A practical verification workflow inspired by testing, evaluation, verification, and validation practices.",
        "kind": "evergreen",
    },
    {
        "title": "When Few-Shot Examples Improve an AI Workflow",
        "source": "Google AI for Developers",
        "link": "https://ai.google.dev/gemini-api/docs/prompting-strategies",
        "summary": "A decision guide for adding specific and varied examples without overfitting a prompt to one case.",
        "kind": "evergreen",
    },
    {
        "title": "Run a Reversible Pilot Before Automating Work with AI",
        "source": "NIST AI Risk Management Framework",
        "link": "https://www.nist.gov/itl/ai-risk-management-framework",
        "summary": "Define scope, human checks, failure criteria, and rollback before expanding an AI-assisted workflow.",
        "kind": "evergreen",
    },
    {
        "title": "Break a Complex AI Task into Verifiable Steps",
        "source": "Google AI for Developers",
        "link": "https://ai.google.dev/gemini-api/docs/prompting-strategies",
        "summary": "Use task decomposition and prompt chaining when one large instruction produces outputs that are hard to inspect.",
        "kind": "evergreen",
    },
    {
        "title": "Document Uncertainty in AI-Assisted Decisions",
        "source": "NIST Generative AI Profile",
        "link": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
        "summary": "Separate source evidence, model output, reviewer judgment, and unresolved uncertainty in a decision record.",
        "kind": "evergreen",
    },
    {
        "title": "Write Clear Output Constraints for an AI Prompt",
        "source": "Google AI for Developers",
        "link": "https://ai.google.dev/gemini-api/docs/prompting-strategies",
        "summary": "Specify audience, fields, length, and completion format so an AI response can be checked automatically.",
        "kind": "evergreen",
    },
    {
        "title": "Create a Human Review Checkpoint for AI Content",
        "source": "NIST AI Resource Center",
        "link": "https://airc.nist.gov/",
        "summary": "Place human review where an error becomes costly instead of adding vague approval to every step.",
        "kind": "evergreen",
    },
]


# Safety: blocklist for dangerous/skip domains
BLOCKED_DOMAINS = [
    "xxx", "porn", "sex", "gambling", "casino", "pharmacy",
    "ransomware", "malware", "darknet", "tor.", "onion.",
]
BLOCKED_TLDS = [".xxx", ".sex", ".porn", ".adult", ".gambling"]

def _is_safe_url(url):
    u = url.lower()
    for d in BLOCKED_DOMAINS:
        if d in u:
            return False
    for tld in BLOCKED_TLDS:
        if tld in u:
            return False
    return True

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

def pull_feeds(max_per_feed=10):
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
            if not _is_safe_url(link):
                print(f"  [skip blocked] {name}: {link[:60]}")
                continue
            items.append({"source": name, "title": title_s, "link": link.strip(),
                          "summary": desc_s, "pubDate": pubDate})
            seen_links.add(link)
            count += 1
    return items

def score_item(item):
    text = (item["title"] + " " + item["summary"]).lower()
    return sum(w for k, w in KEYWORD_WEIGHTS.items() if k in text)

def is_big_news(item, threshold=5):
    return score_item(item) >= threshold

def is_today(item):
    """Check if the RSS item was published today."""
    pub = item.get("pubDate", "")
    if not pub:
        return True
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            from datetime import datetime as _dt2
            parsed = _dt2.strptime(pub.strip(), fmt)
            today = _dt.datetime.now(parsed.tzinfo if parsed.tzinfo else _dt.timezone.utc)
            return (parsed.date() == today.date())
        except ValueError:
            continue
    return True

def _fingerprint(item):
    return _hashlib.sha1((item["title"] + "|" + item["link"]).encode("utf-8")).hexdigest()[:14]

def already_seen(item, db):
    return _fingerprint(item) in db

def mark_seen(item, db):
    db[_fingerprint(item)] = {"title": item["title"], "link": item["link"], "date": _today()}

def make_prompt(item, style_rules):
    sys_path = ENGINE_DIR / "prompts" / "system_prompt_editorial.md"
    system = sys_path.read_text("utf-8").replace("{rules}", style_rules)
    user_msg = (
        f"TITLE: {item['title']}\n"
        f"SOURCE: {item['source']}\n"
        f"LINK:   {item['link']}\n"
        f"SUMMARY:\n{item['summary']}\n\n"
        "Write only an 800-1500 word article body in Markdown; do not add YAML.\n"
        "Required sections: ## What the source establishes; ## What this means; "
        "## A practical next step; ## Limits and uncertainty; ## When to use or skip it.\n"
        "Use the supplied source as the factual boundary. Attribute announcement "
        "claims, distinguish interpretation, and omit unsupported details.\n"
        "Do not claim hands-on testing, invent metrics, quotes, people, prices, "
        "benchmarks, reactions, or links. Do not write a generic news recap. Add "
        "original value through a decision framework or reproducible workflow.\n"
    )
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
        "temperature": CONFIG["api"].get("temperature", 0.65),
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

def article_text(item, body):
    today = _today()
    slug = _slugify(item["title"]) or "ai-news"
    source_url = item.get("link", "")
    refs_section = f"\n## Sources\n\n- {source_url}\n" if source_url else ""
    frontmatter = (
        "---\n"
        f'title: "{item["title"]}"\n'
        f'slug: "{today}-{slug}"\n'
        f'date: "{today}"\n'
        'domain: "ai"\n'
        'category: "AI"\n'
        f'description: "{item.get("summary", "").replace(chr(34), chr(39))[:220]}"\n'
        f'primary_keyword: "{slug}"\n'
        f'word_count: {len(body.split())}\n'
        "---\n\n"
    )
    return frontmatter + body + refs_section + "\n"


def save_article(item, body):
    today = _today()
    slug = _slugify(item["title"]) or "ai-news"
    out_path = OUTPUT_AI / f"{today}-{slug}.md"
    n = 1
    while out_path.exists():
        n += 1
        out_path = OUTPUT_AI / f"{today}-{slug}-{n}.md"
    article = article_text(item, body)
    if n > 1:
        article = _re.sub(
            r'^slug:\s*".*"$',
            f'slug: "{today}-{slug}-{n}"',
            article,
            count=1,
            flags=_re.MULTILINE,
        )
    out_path.write_text(article, encoding="utf-8")
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

def _is_recent(item, cutoff):
    """Check if an RSS item was published after the cutoff datetime."""
    pub = item.get("pubDate", "")
    if not pub:
        return True
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            from datetime import datetime as _dt2
            parsed = _dt2.strptime(pub.strip(), fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=_dt.timezone.utc)
            return parsed >= cutoff
        except ValueError:
            continue
    return True

def last_ai_article_date():
    """Return YYYY-MM-DD of the most recent AI article in output/ai/, or None."""
    dates = []
    for f in OUTPUT_AI.glob("*.md"):
        m = _re.match(r"(\d{4}-\d{2}-\d{2})", f.name)
        if m:
            dates.append(m.group(1))
    return max(dates) if dates else None

def days_since(date_str):
    if not date_str:
        return 999
    from datetime import datetime as _dt2, timezone as _tz2
    last = _dt2.strptime(date_str, "%Y-%m-%d").replace(tzinfo=_tz2.utc)
    now = _dt2.now(_tz2.utc)
    return (now - last).days

def main():
    print(f"=== daily_ai_news.py — {_today()} ===")
    if last_ai_article_date() == _today():
        print("[ai] already published today, skipping")
        return 0
    style_rules_path = ENGINE_DIR / "rules" / "WRITING_RULES.md"
    style_rules = style_rules_path.read_text("utf-8") if style_rules_path.exists() else ""
    db = _load_seen()
    print("[1/5] Pulling RSS feeds...")
    items = pull_feeds()
    print(f"  pulled {len(items)} candidate items")

    print("[2/5] Building evidence-backed candidate queue...")
    news = [
        item
        for item in sorted(items, key=score_item, reverse=True)
        if is_today(item) and is_big_news(item) and not already_seen(item, db)
    ]
    daily_updates = [
        item
        for item in sorted(items, key=score_item, reverse=True)
        if is_today(item)
        and item not in news
        and not already_seen(item, db)
    ]
    offset = _dt.date.today().toordinal() % len(EVERGREEN_TOPICS)
    evergreen = EVERGREEN_TOPICS[offset:] + EVERGREEN_TOPICS[:offset]
    evergreen = [item for item in evergreen if not already_seen(item, db)]
    # Important news wins. Official evergreen guides are the preferred fallback;
    # other same-day updates keep the daily queue renewable after evergreen topics
    # have been used, while the quality gate still blocks thin recaps.
    candidates = news + evergreen + daily_updates
    print(
        f"  major news={len(news)} evergreen={len(evergreen)} "
        f"other daily updates={len(daily_updates)}"
    )
    if not candidates:
        print("[ERROR] no unused AI topic is available; extend EVERGREEN_TOPICS")
        return 1

    minimum = int(CONFIG.get("defaults", {}).get("ai_news_min_words", 800))
    maximum = int(CONFIG.get("defaults", {}).get("ai_news_max_words", 1500))
    for attempt, target in enumerate(candidates[:3], start=1):
        print(f"[3/5] Quality attempt {attempt}/3: {target['title']} ({target['source']})")
        system, user_msg = make_prompt(target, style_rules)
        body = call_llm(system, user_msg).strip()
        if not body or (body.startswith("{") and body.endswith("}")):
            print("  [reject] empty or metadata-only model response")
            continue
        try:
            import importlib as _il

            body = _il.import_module("_clean_body").clean_body(body)
        except Exception:
            pass

        preview = article_text(target, body)
        report = evaluate_article(
            preview,
            domain="ai",
            min_words=minimum,
            max_words=maximum,
            source_urls=[target["link"]],
            existing_dir=OUTPUT_AI,
        )
        print(f"  [gate] {report.summary()} | {report.metrics}")
        if not report.passed:
            log_event(
                {
                    "date": _today(),
                    "action": "rejected",
                    "title": target["title"],
                    "errors": report.errors,
                }
            )
            continue

        print("[5/5] Saving, publishing, and rebuilding...")
        out_path = save_article(target, body)
        destination = publish(out_path)
        mark_seen(target, db)
        _save_seen(db)
        log_event(
            {
                "date": _today(),
                "action": "published",
                "file": str(out_path),
                "site_file": str(destination),
                "title": target["title"],
                "source": target["source"],
                "score": score_item(target),
            }
        )
        print(f"  saved: {out_path}")
        print(f"  published: {destination}")
        return 0 if rebuild_site() else 1

    print("[ERROR] three AI candidates failed the quality gate")
    return 1

if __name__ == "__main__":
    _sys.exit(main())
