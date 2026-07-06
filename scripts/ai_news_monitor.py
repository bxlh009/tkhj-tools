# -*- coding: utf-8 -*-
"""
AI 新闻监控脚本

用途：
每天美国东部时间 9:00 自动跑，从 8 个 RSS 源抓取最新 AI 新闻。
过滤大事件（OpenAI / Anthropic / Google / Meta），
自动调用 generate.py 生成评测文章草稿。

用法（单次）：
  python scripts/ai_news_monitor.py

用法（带生成）：
  python scripts/ai_news_monitor.py --auto-generate

用法（指定日期）：
  python scripts/ai_news_monitor.py --max-items 3

Windows 定时任务：
  控制面板 → 任务计划程序 → 创建任务
    - 每天 09:00（美东时间 / 根据你所在时区调整）
    - 操作: python.exe scripts/ai_news_monitor.py --auto-generate 2>&1
    - 工作目录: D:\codex\content-engine
    - 只在网络可用时运行
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET

# ------------------------------------------------------------
# 配置
# ------------------------------------------------------------
SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
ENGINE_DIR  = SCRIPTS_DIR.parent
VARS_DIR    = ENGINE_DIR / "vars"
PROMPTS_DIR = ENGINE_DIR / "prompts"
OUTPUT_DIR  = ENGINE_DIR / "output"
SEEN_DB     = ENGINE_DIR / ".seen_articles.json"
MONITOR_LOG = ENGINE_DIR / "monitor_log.txt"

RSS_FEEDS = [
    # OpenAI 官方
    "https://openai.com/blog/rss.xml",
    # Anthropic 官方
    "https://www.anthropic.com/news/rss.xml",
    # The Verge / AI
    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    # TechCrunch / AI
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    # VentureBeat / AI
    "https://venturebeat.com/category/ai/feed/",
    # Ars Technica / AI
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    # MIT Tech Review / AI
    "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    # Hacker News AI 高赞
    "https://hnrss.org/newest?q=AI+OR+GPT+OR+Claude+OR+Llama&count=20",
]

AI_KEYWORDS = [
    "openai", "gpt", "chatgpt", "dall-e", "sora", "o1", "o3",
    "anthropic", "claude", "gemini", "google deepmind", "llama",
    "meta ai", "mistral", "ai agent", "ai model", "release",
    "launch", "announce", "breakthrough", "benchmark",
]

MIN_KEYWORD_HITS = 2  # 标题+摘要中至少含多少个 AI 关键词才处理

# ------------------------------------------------------------
# 去重数据库
# ------------------------------------------------------------
def load_seen() -> dict:
    if SEEN_DB.exists():
        try:
            return json.loads(SEEN_DB.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}

def save_seen(seen: dict):
    SEEN_DB.write_text(json.dumps(seen, indent=2, ensure_ascii=False), encoding="utf-8")

def article_hash(url: str, title: str) -> str:
    raw = (url + "|" + title).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]

# ------------------------------------------------------------
# RSS 抓取
# ------------------------------------------------------------
def fetch_rss(url: str, timeout: int = 15) -> bytes | None:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; AINewsBot/1.0)",
        "Accept": "application/rss+xml, application/xml, text/xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        log(f"[WARN] fetch failed: {url[:50]}... -> {e}")
        return None

def parse_rss(xml: bytes, source: str) -> list[dict]:
    items = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return items

    # RSS 2.0
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        desc  = (item.findtext("description") or "").strip()
        date  = (item.findtext("pubDate") or "").strip()
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "description": re.sub(r"<[^>]+>", "", desc)[:300],
                "pub_date": date,
                "source": source,
            })

    # Atom feed
    ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(f".//{ns}entry"):
        title = (entry.findtext(f"{ns}title") or "").strip()
        link_el = entry.find(f"{ns}link")
        link = (link_el.get("href") or "").strip() if link_el is not None else ""
        summary = (entry.findtext(f"{ns}summary") or "").strip()
        date = (entry.findtext(f"{ns}updated") or "").strip()
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "description": re.sub(r"<[^>]+>", "", summary)[:300],
                "pub_date": date,
                "source": source,
            })
    return items

# ------------------------------------------------------------
# 过滤与关键词评分
# ------------------------------------------------------------
def is_relevant(article: dict) -> bool:
    text = (article["title"] + " " + article["description"]).lower()
    hits = sum(1 for kw in AI_KEYWORDS if kw.lower() in text)
    return hits >= MIN_KEYWORD_HITS

# ------------------------------------------------------------
# 日志
# ------------------------------------------------------------
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(MONITOR_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ------------------------------------------------------------
# 自动调用 generate.py
------------------------------------------------------------
def build_vars_from_article(article: dict) -> dict:
    """把 RSS 文章转成 generate.py --vars JSON。"""
    title_clean = article["title"][:120]
    slug_raw = re.sub(r"[^a-zA-Z0-9]+", "-", title_clean.lower())[:50].strip("-")
    desc_preview = article["description"][:200]

    return {
        "source_title": title_clean,
        "source_link": article["link"],
        "source_summary": desc_preview,
        "source_date": article["pub_date"],
        "source_publication": article["source"],
        "min_words": 1800,
        "max_words": 2800,
        "target_audience": "busy professionals evaluating AI tools",
        "primary_keyword": title_clean,
        "long_tail_keywords": [f"{title_clean} review", "ai news today"],
        "slug": f"ai-news-{slug_raw}",
        "category": "ai-news",
    }

def auto_generate(article: dict):
    vars_data = build_vars_from_article(article)
    vars_path = VARS_DIR / f"_auto_{article_hash(article['link'], article['title'])}.json"
    vars_path.write_text(json.dumps(vars_data, indent=2, ensure_ascii=False), encoding="utf-8")

    log(f"[GEN ] calling generate.py for: {article['title'][:60]}")
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "generate.py"),
             "--type", "ai",
             "--vars", str(vars_path)],
            cwd=str(ENGINE_DIR),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0:
            log(f"[OK  ] article drafted -> {result.stdout.strip().splitlines()[-1]}")
        else:
            log(f"[FAIL] generate.py rc={result.returncode}: {result.stderr[:200]}")
    except Exception as e:
        log(f"[FAIL] generate.py threw: {e}")
    finally:
        # vars 文件保留，标记为已用
        vars_path.rename(vars_path.with_suffix(".json.used"))

# ------------------------------------------------------------
# 主流程
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AI 新闻监控")
    parser.add_argument("--auto-generate", action="store_true",
                        help="找到新文章后自动调用 generate.py 生成草稿")
    parser.add_argument("--max-items", type=int, default=5,
                        help="最多处理几篇文章后停止（默认 5，防 API 烧钱）")
    parser.add_argument("--list-only", action="store_true",
                        help="仅列出匹配文章，不调用 generate")
    args = parser.parse_args()

    log(f"=== 开始扫描 {len(RSS_FEEDS)} 个 RSS 源 ===")
    seen = load_seen()
    new_articles = []

    for url in RSS_FEEDS:
        xml = fetch_rss(url)
        if xml is None:
            continue
        articles = parse_rss(xml, source=url.split("//")[-1].split("/")[0])
        for art in articles:
            h = article_hash(art["link"], art["title"])
            if h in seen:
                continue
            if not is_relevant(art):
                continue
            art["_hash"] = h
            new_articles.append(art)
            seen[h] = {"title": art["title"][:80], "date": datetime.now().isoformat()}
        time.sleep(0.5)  # 礼貌延迟

    log(f"新文章: {len(new_articles)} 篇相关 AI 新闻")

    if not new_articles:
        log("无新文章。收工。")
        save_seen(seen)
        return

    for i, art in enumerate(new_articles[:args.max_items], 1):
        print(f"\n[{i}] {art['title'][:80]}")
        print(f"    来源: {art['source']}")
        print(f"    摘要: {art['description'][:120]}...")

        if args.list_only:
            continue
        if args.auto_generate:
            auto_generate(art)

    if not args.list_only and args.auto_generate:
        log(f"已生成 {min(len(new_articles), args.max_items)} 篇草稿到 output/\n"
            + "请人工润色后发布。")

    save_seen(seen)

if __name__ == "__main__":
    main()
