"""Build the curated TKHJ Tools site.

Bulk drafts in ``output/`` are intentionally excluded. Only guides explicitly
listed in ``site/content/guides.json`` can become public pages.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import shutil
from datetime import datetime


HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "_site"
STATIC = HERE / "static"
CONTENT = HERE / "content"
TRANSLATIONS = CONTENT / "zh"
DOMAIN = "tkhjtools.top"
NAME = "TKHJ Tools"
TAGLINE = "Evidence-first guides for learning better and using AI with judgment."
ADSENSE = (
    '<script async src="https://pagead2.googlesyndication.com/pagead/js/'
    'adsbygoogle.js?client=ca-pub-8913718352251239" crossorigin="anonymous"></script>'
)
ANALYTICS = (
    '<script async src="https://www.googletagmanager.com/gtag/js?id=G-QFNJLMGDXL"></script>'
    "<script>window.dataLayer=window.dataLayer||[];"
    "function gtag(){dataLayer.push(arguments)}"
    'gtag("js",new Date());gtag("config","G-QFNJLMGDXL");</script>'
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def slugify(value: str) -> str:
    plain = re.sub(r"<[^>]+>", "", value).casefold()
    return re.sub(r"[\W_]+", "-", plain, flags=re.UNICODE).strip("-") or "section"


def inline(value: str) -> str:
    value = esc(value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    return re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", value)


def markdown_to_html(markdown: str) -> tuple[str, list[tuple[int, str, str]]]:
    lines = markdown.replace("\r\n", "\n").split("\n")
    output: list[str] = []
    headings: list[tuple[int, str, str]] = []
    paragraph: list[str] = []
    index = 0

    def flush() -> None:
        if paragraph:
            value = " ".join(line.strip() for line in paragraph if line.strip())
            if value:
                output.append(f"<p>{inline(value)}</p>")
            paragraph.clear()

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            flush()
            index += 1
            continue

        heading = re.match(r"^(#{2,3})\s+(.+)$", stripped)
        if heading:
            flush()
            level = len(heading.group(1))
            label = heading.group(2).strip()
            anchor = slugify(label)
            headings.append((level, label, anchor))
            output.append(f'<h{level} id="{anchor}">{inline(label)}</h{level}>')
            index += 1
            continue

        if stripped.startswith("> "):
            flush()
            output.append(f"<blockquote><p>{inline(stripped[2:])}</p></blockquote>")
            index += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush()
            raw_rows: list[str] = []
            while index < len(lines):
                candidate = lines[index].strip()
                if not (candidate.startswith("|") and candidate.endswith("|")):
                    break
                raw_rows.append(candidate)
                index += 1
            rows = [[cell.strip() for cell in row.strip("|").split("|")] for row in raw_rows]
            if len(rows) > 1 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in rows[1]):
                header = "".join(f"<th>{inline(cell)}</th>" for cell in rows[0])
                body = "".join(
                    "<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>"
                    for row in rows[2:]
                )
                output.append(
                    f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead>'
                    f"<tbody>{body}</tbody></table></div>"
                )
            continue

        ordered = re.match(r"^\d+\.\s+(.+)$", stripped)
        unordered = re.match(r"^[-*]\s+(.+)$", stripped)
        if ordered or unordered:
            flush()
            tag = "ol" if ordered else "ul"
            pattern = r"^\d+\.\s+(.+)$" if ordered else r"^[-*]\s+(.+)$"
            items: list[str] = []
            while index < len(lines):
                match = re.match(pattern, lines[index].strip())
                if not match:
                    break
                items.append(f"<li>{inline(match.group(1))}</li>")
                index += 1
            output.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue

        paragraph.append(stripped)
        index += 1
    flush()
    return "\n".join(output), headings


def load_guides() -> list[dict]:
    manifest = json.loads((CONTENT / "guides.json").read_text("utf-8"))
    guides: list[dict] = []
    seen: set[str] = set()
    for item in manifest:
        if item["slug"] in seen:
            raise ValueError(f"Duplicate slug: {item['slug']}")
        seen.add(item["slug"])
        source = CONTENT / item["file"]
        markdown = source.read_text("utf-8")
        body_html, headings = markdown_to_html(markdown)
        guide = dict(item)
        guide.setdefault("track", "learning")
        guide.update(
            body_html=body_html,
            headings=headings,
            word_count=len(re.findall(r"\b[\w’'-]+\b", markdown)),
        )
        translation = TRANSLATIONS / f"{item['slug']}.md"
        if translation.exists():
            translated = translation.read_text("utf-8")
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", translated, re.DOTALL)
            if not match:
                raise ValueError(f"Invalid Chinese sidecar frontmatter: {translation.name}")
            metadata: dict[str, str] = {}
            for line in match.group(1).splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                try:
                    metadata[key.strip()] = str(json.loads(value.strip()))
                except json.JSONDecodeError:
                    metadata[key.strip()] = value.strip().strip("\"'")
            if metadata.get("source_slug") != item["slug"]:
                raise ValueError(f"Chinese sidecar slug mismatch: {translation.name}")
            zh_markdown = match.group(2).strip()
            zh_body_html, zh_headings = markdown_to_html(zh_markdown)
            guide.update(
                zh_title=metadata["title"],
                zh_description=metadata["description"],
                zh_body_html=zh_body_html,
                zh_headings=zh_headings,
                zh_word_count=len(re.findall(r"[\w’'-]+", zh_markdown)),
            )
        guides.append(guide)
    return guides


def nav(active: str = "", language: str = "en") -> str:
    prefix = "/zh" if language == "zh" else ""
    items = [("Home", f"{prefix}/", "home", "nav-home"),
             ("Learning", f"{prefix}/learning/", "learning", "nav-learning"),
             ("AI", f"{prefix}/ai/", "ai", "nav-ai"),
             ("Library", f"{prefix}/guides/", "guides", "nav-library"),
             ("About", f"{prefix}/about.html", "about", "nav-about"),
             ("Contact", f"{prefix}/contact.html", "contact", "nav-contact")]
    links = "".join(
        f'<a href="{url}" data-i18n="{i18n}"'
        f'{" aria-current=\"page\"" if active == key else ""}>{label}</a>'
        for label, url, key, i18n in items
    )
    return (
        '<header class="site-header"><div class="container nav-row">'
        f'<a class="brand" href="{prefix}/" aria-label="TKHJ Tools home">'
        '<img class="brand-logo" src="/static/logo.png" alt="" width="88" height="30"></a>'
        f'<nav class="nav-links" aria-label="Primary navigation">{links}</nav>'
        '<form class="nav-search" action="/search.html" method="get" role="search">'
        '<label class="sr-only" for="site-search" data-i18n="search-label">Search guides</label>'
        '<input class="nav-search-input" id="site-search" name="q" type="search" data-search '
        'placeholder="Search" data-i18n-placeholder="search-placeholder" autocomplete="off" '
        'required pattern=".*\\S.*"><span class="search-caret" aria-hidden="true"></span></form>'
        '<button class="language-toggle" type="button" data-language-toggle '
        'aria-label="切换到中文"><span data-language-label>中文</span></button>'
        '<button class="theme-toggle" type="button" data-theme-toggle aria-label="Switch color theme">'
        '<svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"/></svg>'
        '<svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/>'
        '<path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2'
        'M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></button></div></header>'
    )


def footer(language: str = "en") -> str:
    prefix = "/zh" if language == "zh" else ""
    return (
        '<footer class="site-footer"><div class="container footer-grid"><div><strong>TKHJ Tools</strong>'
        '<p data-i18n="footer-summary">Source-grounded Learning and AI guides with visible reasoning, '
        'practical examples, and explicit limits.</p></div><nav aria-label="Footer navigation">'
        f'<a href="{prefix}/learning/" data-i18n="nav-learning">Learning</a>'
        f'<a href="{prefix}/ai/" data-i18n="nav-ai">AI</a>'
        f'<a href="{prefix}/guides/" data-i18n="nav-library">Library</a>'
        f'<a href="{prefix}/about.html" data-i18n="footer-editorial">Editorial process</a>'
        f'<a href="{prefix}/contact.html" data-i18n="footer-corrections">Corrections</a>'
        f'<a href="{prefix}/disclaimer.html" data-i18n="footer-legal">Copyright &amp; disclaimer</a>'
        '<a href="/privacy.html" data-i18n="footer-privacy">Privacy</a></nav></div>'
        f'<div class="container footer-base">&copy; {datetime.now().year} {DOMAIN}. '
        '<span data-i18n="footer-disclaimer">Independent editorial site; no provider endorsement '
        "is implied.</span></div></footer>"
    )


def page(title: str, description: str, body: str, *, active: str = "", path: str = "/",
         page_type: str = "website", schema: dict | None = None, language: str = "en",
         alternate_path: str = "") -> str:
    canonical = f"https://{DOMAIN}{path}"
    html_language = "zh-CN" if language == "zh" else "en"
    alternate = ""
    if alternate_path:
        alternate_language = "en" if language == "zh" else "zh-CN"
        alternate = (
            f'<link rel="alternate" hreflang="{alternate_language}" '
            f'href="https://{DOMAIN}{esc(alternate_path)}">'
        )
    structured = ""
    if schema:
        safe_schema = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
        structured = f'<script type="application/ld+json">{safe_schema}</script>'
    return (
        f'<!doctype html><html lang="{html_language}" data-theme="light" '
        f'data-page-language="{language}" data-language-url="{esc(alternate_path)}">'
        '<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)} | {NAME}</title>"
        f'<meta name="description" content="{esc(description[:160])}">'
        f'<link rel="canonical" href="{canonical}">{alternate}<link rel="icon" href="/favicon.png">'
        '<meta name="theme-color" content="#0f766e">'
        f'<meta property="og:title" content="{esc(title)} | {NAME}">'
        f'<meta property="og:description" content="{esc(description[:160])}">'
        f'<meta property="og:type" content="{page_type}"><meta property="og:url" content="{canonical}">'
        '<meta name="twitter:card" content="summary"><link rel="stylesheet" href="/static/style.css">'
        + ADSENSE + ANALYTICS + structured + "</head><body>"
        '<script>try{var t=localStorage.getItem("tkhj-theme");'
        'if(t)document.documentElement.dataset.theme=t;'
        'var l=localStorage.getItem("tkhj-language");'
        'if(!document.documentElement.dataset.languageUrl&&l==="zh-CN")'
        'document.documentElement.lang=l}catch(e){}</script>'
        '<a class="skip-link" href="#main-content" data-i18n="skip-link">Skip to main content</a>'
        + nav(active, language) + f'<main id="main-content" tabindex="-1">{body}</main>'
        + footer(language) + '<script src="/static/nav.js"></script></body></html>'
    )


def guide_card(guide: dict, language: str = "en") -> str:
    chinese = language == "zh" and "zh_title" in guide
    title = guide["zh_title"] if chinese else guide["title"]
    description = guide["zh_description"] if chinese else guide["description"]
    prefix = "/zh" if chinese else ""
    minutes = max(3, round(guide["word_count"] / 220))
    meta = f"{minutes} 分钟阅读 · 更新于 {guide['updated']}" if chinese else (
        f"{minutes} min read · Updated {guide['updated']}"
    )
    return (
        f'<article class="guide-card"><a href="{prefix}/guides/{guide["slug"]}.html">'
        f'<span class="eyebrow">{esc(guide["category"])}</span><h3>{esc(title)}</h3>'
        f'<p>{esc(description)}</p><span class="card-meta">{esc(meta)}</span>'
        "</a></article>"
    )


def toc(guide: dict, language: str = "en") -> str:
    headings = guide["zh_headings"] if language == "zh" else guide["headings"]
    items = "".join(
        f'<li class="toc-level-{level}"><a href="#{anchor}">{inline(label)}</a></li>'
        for level, label, anchor in headings
    )
    label = "本页目录" if language == "zh" else "On this page"
    return f'<nav class="article-toc" aria-label="{label}"><strong>{label}</strong><ol>{items}</ol></nav>'


def sources(guide: dict, language: str = "en") -> str:
    chinese = language == "zh"
    links = "".join(
        f'<li><a href="{esc(url)}">{esc("来源" if chinese else label)}</a> '
        f'<span>— {"核对日期" if chinese else "checked"} {esc(guide["updated"])}</span></li>'
        for label, url in guide["sources"]
    )
    heading = "来源说明" if chinese else "Source notes"
    explanation = (
        "这些链接界定了本指南所依据的事实范围。TKHJ Tools 在此基础上提供解释、流程、"
        "决策框架或原创练习。"
        if chinese else
        "These links define the factual boundary used for this guide. TKHJ Tools adds the "
        "explanation, workflow, decision framework, or original practice."
    )
    return (
        '<aside class="source-notes" aria-labelledby="source-notes-title"><h2 id="source-notes-title">'
        f"{heading}</h2><p>{explanation}</p><ul>{links}</ul></aside>"
    )


def article_page(guide: dict, guides: list[dict], language: str = "en") -> str:
    chinese = language == "zh"
    eligible = [g for g in guides if not chinese or "zh_title" in g]
    related = [g for g in eligible if g["slug"] != guide["slug"] and g["track"] == guide["track"]][:2]
    if not related:
        related = [g for g in eligible if g["slug"] != guide["slug"]][:2]
    related_html = "".join(guide_card(item, language) for item in related)
    prefix = "/zh" if chinese else ""
    track_path = f"{prefix}/ai/" if guide["track"] == "ai" else f"{prefix}/learning/"
    track_label = (
        ("AI 指南" if guide["track"] == "ai" else "学习指南")
        if chinese else
        ("AI guides" if guide["track"] == "ai" else "Learning guides")
    )
    if chinese:
        note = (
            "本指南由 AI 辅助准备，并对照所列来源进行核查；编辑还检查了无依据的测试主张、"
            "虚构权威和对读者是否具有可执行价值。"
            if guide["track"] == "ai" else
            "本指南由 AI 辅助准备，围绕一个明确的学习任务编辑，并对照官方来源核查；"
            "编辑还检查了原创练习和推理说明。"
        )
    else:
        note = (
            "Prepared with AI assistance, checked against the listed sources, and reviewed for "
            "unsupported testing claims, invented authority, and actionable reader value."
            if guide["track"] == "ai" else
            "Prepared with AI assistance, edited around one learner task, checked against the "
            "listed official sources, and reviewed for original practice and explained reasoning."
        )
    title = guide["zh_title"] if chinese else guide["title"]
    description = guide["zh_description"] if chinese else guide["description"]
    body_html = guide["zh_body_html"] if chinese else guide["body_html"]
    byline = "作者" if chinese else "By"
    published = "发布于" if chinese else "Published"
    updated = "更新于" if chinese else "Updated"
    made = "本指南如何制作" if chinese else "How this guide was made"
    about_url = "/zh/about.html#editorial-team" if chinese else "/about.html#editorial-team"
    disclaimer = (
        "独立编辑内容。产品和考试名称归其各自所有者所有，不代表任何认可或背书。"
        if chinese else
        "Independent editorial content. Product and exam names belong to their respective owners. "
        "No endorsement is implied."
    )
    continue_label = "继续探索" if chinese else "Continue exploring"
    article = (
        f'<div class="article-shell"><article class="article-body"><a class="back-link" href="{track_path}">{track_label}</a>'
        f'<span class="eyebrow">{esc(guide["category"])}</span><h1>{esc(title)}</h1>'
        f'<p class="dek">{esc(description)}</p><div class="byline">{byline} '
        f'<a href="{about_url}">TKHJ Tools Editorial Team</a>'
        f' · {published} <time datetime="{guide["published"]}">{guide["published"]}</time>'
        f' · {updated} <time datetime="{guide["updated"]}">{guide["updated"]}</time></div>'
        f'<aside class="editorial-note"><strong>{made}</strong><p>{note}</p></aside>'
        + toc(guide, language) + body_html + sources(guide, language)
        + f'<div class="article-disclaimer">{disclaimer}</div></article>'
        + f'<aside class="related"><h2>{continue_label}</h2><div class="guide-grid compact">'
        + related_html + "</div></aside></div>"
    )
    path = f"{prefix}/guides/{guide['slug']}.html"
    alternate_path = (
        f"/guides/{guide['slug']}.html" if chinese else f"/zh/guides/{guide['slug']}.html"
    )
    schema = {
        "@context": "https://schema.org", "@type": "Article", "headline": title,
        "description": description, "datePublished": guide["published"],
        "dateModified": guide["updated"],
        "inLanguage": "zh-CN" if chinese else "en",
        "mainEntityOfPage": f"https://{DOMAIN}{path}",
        "author": {"@type": "Organization", "name": "TKHJ Tools Editorial Team",
                   "url": f"https://{DOMAIN}/about.html#editorial-team"},
        "publisher": {"@type": "Organization", "name": NAME},
    }
    return page(title, description, article, active=guide["track"], path=path,
                page_type="article", schema=schema, language=language,
                alternate_path=alternate_path)


def home_page(guides: list[dict], language: str = "en") -> str:
    prefix = "/zh" if language == "zh" else ""
    learning = [g for g in guides if g["track"] == "learning"]
    ai = [g for g in guides if g["track"] == "ai"]
    learning_cards = "".join(guide_card(g, language) for g in reversed(learning[-3:]))
    ai_cards = "".join(guide_card(g, language) for g in reversed(ai[-3:]))
    body = (
        '<section class="hero"><div class="container hero-grid"><div><span class="eyebrow">'
        'Learning × AI</span><h1 data-i18n="home-title">Use evidence. Make a better next move.</h1>'
        f'<p class="hero-lead" data-i18n="home-lead">{TAGLINE} Learning guides turn mistakes into practice; AI guides '
        "turn announcements and documentation into decisions.</p><div class=\"hero-actions\">"
        f'<a class="button primary" href="{prefix}/learning/" data-i18n="explore-learning">Explore Learning</a>'
        f'<a class="button secondary" href="{prefix}/ai/" data-i18n="explore-ai">Explore AI</a>'
        f'<a class="button secondary" href="{prefix}/about.html" data-i18n="see-editorial">See the editorial process</a></div></div>'
        '<aside class="method-card"><span class="method-number">01</span>'
        '<h2 data-i18n="method-evidence">Find the evidence</h2>'
        "<p>Locate the phrase, rule, or descriptor that controls the decision.</p>"
        '<span class="method-number">02</span><h2 data-i18n="method-judgment">Separate claim from judgment</h2>'
        "<p>Mark what the source establishes and what still needs verification.</p>"
        '<span class="method-number">03</span><h2 data-i18n="method-next-step">Run a small next step</h2>'
        "<p>Use an original practice item or reversible workflow before scaling up.</p></aside></div></section>"
        '<section class="section"><div class="container section-heading"><div><span class="eyebrow">'
        f'Learning</span><h2 data-i18n="learning-heading">Improve one study decision</h2><p>{len(learning)} focused guides with '
        f'original practice and official source notes.</p></div><a class="text-link" href="{prefix}/learning/">'
        f'<span data-i18n="view-learning">View Learning</span></a></div>'
        f'<div class="container guide-grid">{learning_cards}</div></section>'
        '<section class="section"><div class="container section-heading"><div><span class="eyebrow">'
        f'AI</span><h2 data-i18n="ai-heading">Use AI with judgment</h2><p>{len(ai)} source-grounded guides with explicit '
        f'limits and concrete next steps.</p></div><a class="text-link" href="{prefix}/ai/">'
        '<span data-i18n="view-ai">View AI</span></a></div>'
        f'<div class="container guide-grid">{ai_cards}</div></section>'
        '<section class="trust-band"><div class="container trust-grid">'
        "<div><strong>Two clear tracks</strong><p>Learning and AI have different evidence and "
        "usefulness checks.</p></div><div><strong>Visible sources</strong><p>Time-sensitive and "
        "format-dependent claims link to their factual anchors.</p></div><div><strong>Daily gate</strong>"
        "<p>Automation can publish only after structure, source, originality, and honesty checks.</p>"
        "</div></div></section>"
    )
    path = f"{prefix}/"
    title = "循证学习与 AI 指南" if language == "zh" else "Evidence-first Learning and AI guides"
    description = (
        "帮助你更有效学习、更有判断地使用 AI 的循证指南。"
        if language == "zh" else TAGLINE
    )
    schema = {"@context": "https://schema.org", "@type": "WebSite", "name": NAME,
              "url": f"https://{DOMAIN}{path}", "description": description,
              "inLanguage": "zh-CN" if language == "zh" else "en"}
    alternate = "/" if language == "zh" else "/zh/"
    return page(title, description, body, active="home", path=path, schema=schema,
                language=language, alternate_path=alternate)


def guides_page(guides: list[dict], language: str = "en") -> str:
    prefix = "/zh" if language == "zh" else ""
    selected = [g for g in guides if language == "en" or "zh_title" in g]
    cards = "".join(guide_card(g, language) for g in selected)
    heading = (
        "学习与 AI，汇集于一个循证文章库"
        if language == "zh" else
        "Learning and AI, in one evidence-first library"
    )
    description = (
        "选择一个明确的阅读任务。每篇文章均包含来源、清晰推理和具体的下一步。"
        if language == "zh" else
        "Choose a focused reader task. Each page includes sources, explicit reasoning, and a concrete next step."
    )
    body = (
        '<section class="page-hero"><div class="container narrow"><span class="eyebrow">Guide library</span>'
        f"<h1>{heading}</h1><p>{description}"
        '</p></div></section><section class="section"><div class="container guide-grid">'
        + cards + "</div></section>"
    )
    path = f"{prefix}/guides/"
    alternate = "/guides/" if language == "zh" else "/zh/guides/"
    title = "全部指南" if language == "zh" else "All guides"
    return page(title, description, body, active="guides", path=path, language=language,
                alternate_path=alternate)


def track_page(guides: list[dict], track: str, language: str = "en") -> str:
    prefix = "/zh" if language == "zh" else ""
    selected = [
        guide for guide in guides
        if guide["track"] == track and (language == "en" or "zh_title" in guide)
    ]
    label = "AI" if track == "ai" else ("学习" if language == "zh" else "Learning")
    if language == "zh":
        description = (
            "将产品变化、提示方法和 AI 工作流拆分为事实主张、限制与决策。"
            if track == "ai" else
            "包含原创练习与推理说明的考试方法和学习系统。"
        )
    else:
        description = (
            "Product changes, prompt methods, and AI workflows separated into claims, limits, and decisions."
            if track == "ai" else
            "Exam methods and study systems with original practice and explained reasoning."
        )
    cards = "".join(guide_card(guide, language) for guide in reversed(selected))
    heading = f"{label}指南" if language == "zh" else f"{label} guides"
    body = (
        f'<section class="page-hero"><div class="container narrow"><span class="eyebrow">{label}</span>'
        f"<h1>{heading}</h1><p>{description}</p></div></section>"
        f'<section class="section"><div class="container guide-grid">{cards}</div></section>'
    )
    path = f"{prefix}/{track}/"
    alternate = f"/{track}/" if language == "zh" else f"/zh/{track}/"
    return page(heading, description, body, active=track, path=path, language=language,
                alternate_path=alternate)


def about_page(language: str = "en") -> str:
    if language == "zh":
        body = (
            '<section class="page-hero"><div class="container narrow"><span class="eyebrow">关于</span>'
            "<h1>两个领域，同一套证据标准</h1><p>TKHJ Tools 发布学习与 AI 指南。我们可以使用自动化，"
            "但不发布虚构经历、无来源主张或为凑数量而写的内容。</p></div></section>"
            '<section class="prose-page"><div class="container narrow"><h2>什么样的指南可以发布</h2>'
            "<p>每篇指南必须解决一个明确的读者任务，展示推理过程，提供原创示例或可复用流程，"
            "为重要事实链接可靠来源，并通过对应领域的质量检查。</p>"
            '<h2 id="editorial-team">编辑团队与署名</h2><p>文章统一署名为 TKHJ Tools 编辑团队。'
            "我们不会虚构教师身份，也不会声称无法核实的学生数量、提分效果、产品实测经历或专业资质。</p>"
            "<h2>AI 的使用</h2><p>AI 可以协助列提纲、起草和翻译，每篇指南都会披露这种协助。发布前还要"
            "聚焦真实问题、删除无依据的经验性说法、用官方页面核对时效性信息，并加入原创练习或具体决策框架。</p>"
            "<h2>每日发布</h2><p>自动流程每天计划发布一篇学习文章和一篇 AI 文章。未通过检查的草稿会换题重写，"
            "不会用短小占位内容替代。</p><h2>更正与更新</h2><p>每篇指南都显示更新日期和来源核对日期。"
            '如果考试或产品规则发生变化，我们会更新或撤下相关指南。<a href="/zh/contact.html">提交更正</a>。</p>'
            "<h2>独立性</h2><p>TKHJ Tools 与 ETS、IELTS、British Council、IDP、"
            "Cambridge University Press &amp; Assessment 均无隶属或背书关系。"
            "这些指南不接受赞助文章，也不使用联盟推广链接。</p></div></section>"
        )
        return page("关于与编辑流程", "了解 TKHJ Tools 如何选择主题、核对来源、更新及更正指南。",
                    body, active="about", path="/zh/about.html", language="zh",
                    alternate_path="/about.html")

    body = (
        '<section class="page-hero"><div class="container narrow"><span class="eyebrow">About</span>'
        "<h1>Two tracks with one evidence standard</h1><p>TKHJ Tools publishes Learning and AI "
        "guides. Automation is allowed, but invented experience, source-free claims, and quota "
        "fillers are not.</p></div></section>"
        '<section class="prose-page"><div class="container narrow"><h2>What makes a guide publishable</h2>'
        "<p>A guide must solve one identifiable reader task, show its reasoning, include an original "
        "example or reusable workflow, link important claims to sources, and pass the track-specific "
        "quality gate before automated publication.</p>"
        '<h2 id="editorial-team">Editorial team and authorship</h2><p>Published pages are attributed '
        "to the TKHJ Tools Editorial Team. We do not use a fictional teacher identity or claim "
        "student counts, score improvements, hands-on product tests, or credentials readers cannot verify.</p>"
        "<h2>Use of AI</h2><p>AI may assist with outlining and drafting. That assistance is stated on "
        "every guide. Publication requires narrowing the page to a real learner decision, removing "
        "unsupported experience claims, checking current format statements against official pages, "
        "and adding original practice or a concrete AI decision framework.</p>"
        "<h2>Daily publishing</h2><p>The automation targets one Learning and one AI article each day. "
        "A failed draft is replaced with another sourced topic; it is never replaced with a short "
        "placeholder.</p><h2>Corrections and freshness</h2><p>Every guide "
        "shows an updated date and a source-checked date. If a provider changes its format, we update "
        'or withdraw the affected guide. <a href="/contact.html">Report a correction</a>.</p>'
        "<h2>Independence</h2><p>TKHJ Tools is not affiliated with or endorsed by ETS, IELTS, the "
        "British Council, IDP, or Cambridge University Press &amp; Assessment. We do not accept "
        "sponsored posts or use affiliate links in these guides.</p></div></section>"
    )
    return page("About and editorial process", "How TKHJ Tools selects, sources, updates, and corrects guides.",
                body, active="about", path="/about.html", alternate_path="/zh/about.html")


def contact_page(language: str = "en") -> str:
    if language == "zh":
        body = (
            '<section class="page-hero"><div class="container narrow"><span class="eyebrow">联系</span>'
            "<h1>报告事实或使用问题</h1><p>请提供页面网址、有问题的原句，并尽可能附上可靠来源。</p>"
            "</div></section>"
            '<section class="prose-page"><div class="container narrow"><h2>内容更正</h2>'
            "<p>请在项目仓库创建公开 Issue，方便记录问题和后续修改。</p>"
            '<p><a class="button primary" href="https://github.com/bxlh009/tkhj-tools/issues">'
            "创建 GitHub Issue</a></p><h2>请提供这些信息</h2><ol><li>具体的指南网址。</li>"
            "<li>需要处理的主张、失效链接或交互问题。</li><li>你原本预期看到的结果。</li>"
            "<li>如涉及事实更正，请尽可能提供官方来源。</li></ol>"
            "<h2>处理范围</h2><p>TKHJ Tools 可以更正本站内容和界面。报名、评分、便利安排或账户问题，"
            "请直接联系相应考试或产品服务商。</p><h2>版权问题</h2>"
            '<p>如果你认为本站内容侵犯了你的权利，请提供相关页面、作品或商标说明，以及你有权提出请求的证明。'
            '我们会核查并在适当情况下更正或移除内容。详情参阅<a href="/zh/disclaimer.html">版权与免责声明</a>。</p>'
            "</div></section>"
        )
        return page("联系与内容更正", "报告错误、过时信息、版权问题或使用问题。",
                    body, active="contact", path="/zh/contact.html", language="zh",
                    alternate_path="/contact.html")

    body = (
        '<section class="page-hero"><div class="container narrow"><span class="eyebrow">Contact</span>'
        "<h1>Report a factual or usability problem</h1><p>Include the page URL, the sentence at issue, "
        "and a reliable source when available.</p></div></section>"
        '<section class="prose-page"><div class="container narrow"><h2>Corrections</h2>'
        "<p>Open a public issue in the project repository so changes remain traceable.</p>"
        '<p><a class="button primary" href="https://github.com/bxlh009/tkhj-tools/issues">'
        "Open a GitHub issue</a></p><h2>What to include</h2><ol><li>The exact guide URL.</li>"
        "<li>The claim, broken link, or interaction that needs attention.</li><li>What you expected "
        "to see.</li><li>An official source for factual corrections, when possible.</li></ol>"
        "<h2>Response scope</h2><p>TKHJ Tools can correct its own content and interface. Contact the "
        "exam provider for registration, scoring, accommodations, or account questions.</p>"
        "<h2>Copyright concerns</h2><p>If you believe material on this site infringes your rights, "
        "include the page, the protected work or mark, and evidence that you are authorized to report it. "
        'We will review the request and correct or remove material when appropriate. See the '
        '<a href="/disclaimer.html">copyright and disclaimer page</a>.</p></div></section>'
    )
    return page("Contact and corrections", "Report errors, outdated information, or usability problems.",
                body, active="contact", path="/contact.html", alternate_path="/zh/contact.html")


def disclaimer_page(language: str = "en") -> str:
    if language == "zh":
        body = (
            '<section class="page-hero"><div class="container narrow"><span class="eyebrow">法律说明</span>'
            "<h1>版权与免责声明</h1><p>最后更新：2026 年 7 月 24 日。</p></div></section>"
            '<section class="prose-page"><div class="container narrow"><h2>内容与版权</h2>'
            "<p>除非另有标注，本站的编辑文字、原创示例和工作流程由 TKHJ Tools 制作。引用、商标、"
            "产品名称、考试名称及外部资料仍归各自权利人所有。来源链接不表示本站拥有相关资料。</p>"
            "<h2>引用与转载</h2><p>我们尽量只使用说明问题所必需的有限引用，并链接来源。未经许可，"
            "请勿完整复制本站文章。法律允许的引用仍应注明 TKHJ Tools 和原页面链接，并以适用法律为准。</p>"
            "<h2>非官方信息</h2><p>本站提供一般学习和技术信息，不是考试机构、产品厂商或专业顾问。"
            "内容不构成法律、财务、医疗或其他专业意见，也不保证特定分数、结果或产品表现。</p>"
            "<h2>商标与独立性</h2><p>ETS、TOEFL、IELTS、British Council、IDP、Cambridge 以及"
            "其他名称和标志可能是其各自所有者的商标。提及这些名称仅用于识别讨论对象，"
            "不表示合作、授权、认可或背书。</p><h2>外部链接</h2><p>外部网站由第三方控制。"
            "我们提供链接是为了核对来源，不对其内容、可用性或隐私做法作保证。</p>"
            '<h2>权利通知</h2><p>如你认为本站侵犯版权、商标或其他合法权利，请通过'
            '<a href="/zh/contact.html">联系与内容更正页面</a>提交具体网址、权利说明和授权证明。'
            "我们会核查，并在适当情况下更正或移除相关内容。</p></div></section>"
        )
        return page("版权与免责声明", "TKHJ Tools 的版权、引用、商标、独立性和权利通知说明。",
                    body, path="/zh/disclaimer.html", language="zh",
                    alternate_path="/disclaimer.html")

    body = (
        '<section class="page-hero"><div class="container narrow"><span class="eyebrow">Legal</span>'
        "<h1>Copyright and disclaimer</h1><p>Last updated July 24, 2026.</p></div></section>"
        '<section class="prose-page"><div class="container narrow"><h2>Content and copyright</h2>'
        "<p>Unless stated otherwise, TKHJ Tools creates the editorial text, original examples, and "
        "workflows on this site. Quotations, trademarks, product names, exam names, and linked material "
        "remain the property of their respective rights holders. Linking a source does not claim ownership.</p>"
        "<h2>Quotation and reuse</h2><p>We aim to use only limited quotations needed to explain a point "
        "and link to the source. Do not reproduce complete articles without permission. Where quotation "
        "is permitted by law, attribute TKHJ Tools and link to the original page; applicable law controls.</p>"
        "<h2>Not official or professional advice</h2><p>This site provides general learning and technical "
        "information. It is not an exam provider, product vendor, or professional adviser. Content is not "
        "legal, financial, medical, or other professional advice and does not guarantee scores, outcomes, "
        "or product performance.</p><h2>Trademarks and independence</h2><p>ETS, TOEFL, IELTS, the British "
        "Council, IDP, Cambridge, and other names or logos may be trademarks of their respective owners. "
        "Their mention identifies the subject being discussed and does not imply affiliation, permission, "
        "approval, or endorsement.</p><h2>External links</h2><p>Third parties control external sites. "
        "Links are provided for source checking; TKHJ Tools does not guarantee their content, availability, "
        "or privacy practices.</p><h2>Rights notices</h2><p>If you believe this site infringes copyright, "
        'trademark, or another legal right, use the <a href="/contact.html">contact and corrections page</a> '
        "and provide the exact URL, a description of the right, and evidence that you are authorized to "
        "submit the notice. We will review it and correct or remove material when appropriate.</p></div></section>"
    )
    return page("Copyright and disclaimer", "Copyright, quotation, trademark, independence, and rights-notice information.",
                body, path="/disclaimer.html", alternate_path="/zh/disclaimer.html")


def privacy_page() -> str:
    body = (
        '<section class="page-hero"><div class="container narrow"><span class="eyebrow">Privacy</span>'
        "<h1>Privacy policy</h1><p>Last updated July 24, 2026.</p></div></section>"
        '<section class="prose-page"><div class="container narrow"><h2>Information collected</h2>'
        "<p>This site has no user accounts or contact form. Standard hosting logs may contain an IP "
        "address, browser information, requested URL, and timestamp for security and reliability.</p>"
        "<h2>Analytics</h2><p>Google Analytics is used to understand aggregate page use. Google may "
        "set or read cookies and process device or usage data under its own privacy terms.</p>"
        "<h2>Advertising</h2><p>The site includes the Google AdSense site-verification script. Google "
        "may use cookies or local storage when advertising services are enabled. No manual ad units "
        "are inserted between guide text during the approval build.</p><h2>Local preferences</h2>"
        "<p>The color-theme choice is stored in local browser storage and is not sent to TKHJ Tools.</p>"
        "<h2>External links</h2><p>Guides link to official providers and GitHub. Their privacy practices "
        'apply after you leave this site.</p><h2>Questions</h2><p>Use the <a href="/contact.html">'
        "corrections page</a> for privacy or content questions.</p></div></section>"
    )
    return page("Privacy policy", "Privacy information for analytics, advertising verification, and logs.",
                body, path="/privacy.html")


def search_page() -> str:
    body = (
        '<section class="page-hero"><div class="container narrow">'
        '<span class="eyebrow" data-i18n="search-eyebrow">Guide search</span>'
        '<h1 data-i18n="search-title">Search the library</h1>'
        '<form class="search-page-form" action="/search.html" method="get" role="search">'
        '<label class="sr-only" for="search-page-input" data-i18n="search-label">Search guides</label>'
        '<input id="search-page-input" name="q" type="search" data-search-page '
        'placeholder="Search titles, topics, or exams" data-i18n-placeholder="search-page-placeholder" '
        'autocomplete="off"><button class="button primary" type="submit" '
        'data-i18n="search-button">Search</button></form></div></section>'
        '<section class="section"><div class="container"><div id="results" '
        'class="search-results" aria-live="polite"></div></div></section>'
        '<script src="/static/search.js"></script>'
    )
    return page("Search", "Search TKHJ Tools Learning and AI guides.", body, active="search",
                path="/search.html")


def search_index(guides: list[dict]) -> str:
    rows = []
    for guide in guides:
        rows.append(
            {
                "title": guide["title"],
                "description": guide["description"],
                "category": guide["category"],
                "track": guide["track"],
                "date": guide["published"],
                "url": f"/guides/{guide['slug']}.html",
                "zh_title": guide.get("zh_title", ""),
                "zh_description": guide.get("zh_description", ""),
                "zh_url": f"/zh/guides/{guide['slug']}.html" if "zh_title" in guide else "",
            }
        )
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))


def write(path: str, content: str) -> None:
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, "utf-8")


def sitemap(guides: list[dict]) -> str:
    entries = [("/", None), ("/guides/", None), ("/learning/", None), ("/ai/", None), ("/about.html", None),
               ("/contact.html", None), ("/disclaimer.html", None), ("/privacy.html", None),
               ("/search.html", None), ("/zh/", None), ("/zh/guides/", None), ("/zh/learning/", None),
               ("/zh/ai/", None), ("/zh/about.html", None), ("/zh/contact.html", None),
               ("/zh/disclaimer.html", None)]
    entries += [(f"/guides/{g['slug']}.html", g["updated"]) for g in guides]
    entries += [
        (f"/zh/guides/{g['slug']}.html", g["updated"])
        for g in guides if "zh_title" in g
    ]
    rows = "".join(
        f"<url><loc>https://{DOMAIN}{path}</loc>"
        + (f"<lastmod>{modified}</lastmod>" if modified else "") + "</url>"
        for path, modified in entries
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + rows + "</urlset>")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "static").mkdir(parents=True)
    for name in ("style.css", "nav.js", "search.js", "logo.png", "favicon.png"):
        shutil.copy2(STATIC / name, OUT / "static" / name)
    shutil.copy2(STATIC / "favicon.png", OUT / "favicon.png")
    guides = load_guides()
    write("index.html", home_page(guides))
    write("guides/index.html", guides_page(guides))
    write("learning/index.html", track_page(guides, "learning"))
    write("ai/index.html", track_page(guides, "ai"))
    write("about.html", about_page())
    write("contact.html", contact_page())
    write("disclaimer.html", disclaimer_page())
    write("privacy.html", privacy_page())
    write("search.html", search_page())
    write("search_index.json", search_index(guides))
    for guide in guides:
        write(f"guides/{guide['slug']}.html", article_page(guide, guides))
        if "zh_title" in guide:
            write(f"zh/guides/{guide['slug']}.html", article_page(guide, guides, "zh"))
    write("zh/index.html", home_page(guides, "zh"))
    write("zh/guides/index.html", guides_page(guides, "zh"))
    write("zh/learning/index.html", track_page(guides, "learning", "zh"))
    write("zh/ai/index.html", track_page(guides, "ai", "zh"))
    write("zh/about.html", about_page("zh"))
    write("zh/contact.html", contact_page("zh"))
    write("zh/disclaimer.html", disclaimer_page("zh"))
    write("sitemap.xml", sitemap(guides))
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: https://{DOMAIN}/sitemap.xml\n")
    write("ads.txt", "google.com, pub-8913718352251239, DIRECT, f08c47fec0942fa0\n")
    print(f"Built {len(guides)} curated guides; bulk drafts excluded.")


if __name__ == "__main__":
    main()
