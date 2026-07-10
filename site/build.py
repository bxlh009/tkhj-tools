import pathlib, re, shutil
from datetime import datetime
import os, json

DATA = os.path.dirname(os.path.abspath(__file__))
HERE = pathlib.Path(DATA)
OUT  = HERE / "_site"
EXAM = HERE.parent / "output" / "exams"
AI   = HERE.parent / "output" / "ai"
STA  = HERE / "static"

DOM  = "tkhjtools.top"
NAME = "TKHJ Tools"
TAG  = "Free study guides for every level, and honest AI news coverage."
CSL  = "static/style.css"
JSL  = "static/nav.js"

AD_HEAD = ""
AD_UNIT = ""

EXAM_TABS = ["All Exams","IELTS","TOEFL","GRE","SAT","More"]
AI_TABS   = ["All","AI","Tools","Prompts","Workflows","Productivity"]

EXAM_ICON = {"IELTS":"","TOEFL":"","GRE":"","SAT":"","More":""}
AI_ICON   = {"AI":"","Tools":"\xf0\x9f\x94\xa7","Prompts":"\xf0\x9f\x93\x9c","Workflows":"\xe2\x9a\x99\xef\xb8\x8f","Productivity":"\xf0\x9f\x9a\x80"}

if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir(parents=True, exist_ok=True)
for d in ["static","exam","exam/article","exam/tools","ai","ai/article","ai/tools"]:
    (OUT / d).mkdir(parents=True, exist_ok=True)
for f in STA.iterdir():
    if f.is_file(): shutil.copy2(str(f), str(OUT / "static" / f.name))

_fav_src = HERE / "static" / "favicon.png"
if _fav_src.exists():
    shutil.copy2(str(_fav_src), str(OUT / "favicon.png"))

NL = chr(10)
def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace('"',"&quot;")

def read(p): return pathlib.Path(p).read_text("utf-8")
def fm(md):
    md = md.lstrip("\ufeff")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", md, re.S)
    if not m: return {}, md
    meta = {}
    for line in m.group(1).splitlines():
        if ":" not in line: continue
        k,v = line.split(":",1)
        v = v.strip().strip("'").strip('"')
        if v.startswith("["):
            inner = v.strip("[]")
            v = [x.strip().strip("'").strip('"') for x in inner.split(",") if x.strip()]
        meta[k.strip()] = v
    return meta, m.group(2)

def clean_md(text):
    out = []
    for line in text.split(chr(10)):
        if re.match(r"^\s*\|", line): continue
        line = re.sub(r"^#{1,6}\s+", "", line)
        if re.match(r"^\s*[-*]\s+", line):
            line = re.sub(r"^\s*[-*]\s+", "", line)
        out.append(line)
    return chr(10).join(out)

def md2html(text):
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    text = clean_md(text)
    out = []
    for line in text.split(chr(10)):
        t = line.strip()
        if not t: continue
        if t.startswith("> "):
            out.append("<blockquote><p>" + esc(t[2:]) + "</p></blockquote>")
            continue
        out.append("<p>" + esc(t) + "</p>")
    body = chr(10).join(out)
    body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
    body = re.sub(r"\*(.+?)\*", r"<em>\1</em>", body)
    body = body.replace("*", "")
    return body

def ctag(tag):
    t = (tag or "").lower()
    for k,v in [("ielts","cat-ielts"),("toefl","cat-toefl"),("gre","cat-gre"),("sat","cat-sat"),("chatgpt","cat-chatgpt"),("notion","cat-notion"),("gemini","cat-gemini"),("prompt","cat-prompt"),("workflow","cat-workflow")]:
        if k in t: return v
    return "cat-ai"

def card(a, is_exam=True):
    slug = a["_slug"]
    section = "exam" if is_exam else "ai"
    url = "/" + section + "/article/" + slug + ".html"
    cat = a.get("_display_cat", "Article")
    cls = ctag(cat)
    m = max(1, a["_wc"] // 220)
    title = esc(a.get("title", "Untitled"))
    kw = esc(a.get("primary_keyword", ""))
    date = a.get("date", "")[:10]
    keywords = a.get("_keywords", [])
    keywords_json = esc(json.dumps(keywords, ensure_ascii=False) if keywords else "[]")
    cover = '<div class="card-cover">' + esc(cat) + " &middot; " + esc(m) + " min</div>"
    data_kw = ' data-keywords="' + keywords_json + '"'
    body = '<div class="card-body">'
    body += '<span class="card-cat ' + cls + '">' + esc(cat) + "</span>"
    body += '<h3 class="card-title">' + title + "</h3>"
    body += '<p class="card-desc">' + kw + "</p>"
    body += '<div class="card-foot"><span>TKHJ Tools</span><span>' + date + "</span></div>"
    body += "</div>"
    return '<a class="card" href="' + url + '" data-card ' + data_kw + '>' + cover + body + "</a>"

def load_articles(folder, is_exam=True):
    arts = []
    if not folder.exists(): return arts
    for f in folder.glob("*.md"):
        if re.search(r"-\d{1,2}$", f.stem) and not re.search(r"20\d{2}$", f.stem): continue
        body = read(f)
        meta, _ = fm(body)
        slug = f.stem
        title = meta.get("title", slug.replace("-"," ").title())
        keywords = meta.get("long_tail", [])
        if isinstance(keywords, str): keywords = [keywords]
        raw_exam = meta.get("exam","")
        raw_cat  = meta.get("category","")
        if is_exam:
            if "ielts" in raw_exam.lower() or "ielts" in slug.lower():
                sec = (meta.get("section","").strip() or "Academic").split(" ")[0]
                display = "IELTS " + sec
            elif "toefl" in raw_exam.lower() or "toefl" in slug.lower():
                sec = (meta.get("section","").strip() or "iBT").split(" ")[0]
                display = "TOEFL " + sec
            elif "gre" in raw_exam.lower() or "gre" in slug.lower():
                sec = (meta.get("section","").strip() or "Verbal").split(" ")[0]
                display = "GRE " + sec
            elif "sat" in raw_exam.lower() or "sat" in slug.lower():
                sec = (meta.get("section","").strip() or "Math").split(" ")[0]
                display = "SAT " + sec
            else:
                display = raw_exam.strip() or "Exam"
        else:
            cat_map = {"comparison":"AI Comparison","tools":"AI Tools","prompts":"Prompts","workflow":"Workflows","productivity":"Productivity"}
            display = cat_map.get(raw_cat.lower().strip(), "AI")
        arts.append({
            "_slug":slug, "_body":body, "_wc":len(body.split()),
            "title":title, "_keywords":keywords,
            "_display_cat":display,
            "exam":raw_exam or "Exam",
            "category":raw_cat or "AI",
            "date":meta.get("date",""),
            "primary_keyword":meta.get("primary_keyword",""),
        })
    arts.sort(key=lambda a: a.get("date",""), reverse=True)
    return arts

def section_hero(title, desc, tag=None):
    out = '<section class="section-hero" style="padding:48px 0 32px;border-bottom:1px solid var(--line);background:var(--surface)">'
    out += '<div class="container">'
    if tag: out += '<span style="font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--brand);margin-bottom:8px;display:inline-block">' + esc(tag) + '</span>'
    out += '<h1 style="font-size:clamp(1.6rem,3.5vw,2.4rem);line-height:1.2;margin:0 0 12px;color:var(--text-1);letter-spacing:-.02em;font-weight:800">' + esc(title) + '</h1>'
    out += '<p style="margin:0;color:var(--text-2);max-width:640px">' + esc(desc) + '</p>'
    out += '</div></section>'
    return out

def tabs_html(name, items, selected_idx=0, icons=None):
    out = []
    for i,label in enumerate(items):
        cls = "tab active" if i == selected_idx else "tab"
        icon = icons.get(label, "") if icons else ""
        prefix = icon + " " if icon else ""
        out.append('<button class="' + cls + '" data-tab="' + name + '" data-val="' + esc(label) + '">' + prefix + '<span>' + esc(label) + "</span></button>")
    return '<div class="tabs" data-tabs="' + name + '">' + NL.join(out) + "</div>"

def footer():
    y = str(datetime.now().year)
    cols = [
        '<h4 style="margin:0 0 8px;font-size:1.05rem;color:var(--text-1)">' + NAME + '</h4><p>Student-first study guides for English exams and AI tools. Most articles are AI-assisted and reviewed by human editor.</p>',
        '<h4>Articles</h4><a href="/exam/">All Exam Articles</a><a href="/exam/tools/">Exam Tools</a><a href="/ai/">All AI Articles</a><a href="/ai/tools/">AI Tools</a>',
        '<h4>Popular Guides</h4><a href="/exam/article/ielts-writing-band-7-strategy.html">IELTS Writing Band 7</a><a href="/exam/article/toefl-reading-inference-strategy.html">TOEFL Reading</a><a href="/exam/article/gre-text-completion-master-plan.html">GRE Text</a><a href="/ai/article/gpt-5-vs-claude-4-comparison.html">GPT-5 vs Claude 4</a>',
    ]
    grid = ""
    for c in cols:
        grid += '<div class="foot-col">' + c + "</div>"
    return '<footer class="site-footer"><div class="container"><div class="foot-grid">' + grid + '</div><p class="foot-copy">&copy; ' + y + " " + DOM + " \xb7 Independent study guides \xb7 Some content is AI-assisted and reviewed by human editors.</p></div></footer>"

def nav(active="home"):
    out = ['<header class="site-header">']
    out.append('<div class="container nav-row">')
    out.append('<a href="/" class="brand"><img src="/static/logo.png" alt="TKHJ Tools" height="28"></a>')
    out.append('<nav class="nav-links">')
    for label, url,is_active in [["Home","/",active=="home"],["Exam","/exam/",active=="exam"],["AI","/ai/",active=="ai"],["About","/about.html",active=="about"]]:
        cls = "active" if is_active else ""
        out.append('<a href="' + url + '" class="' + cls + '">' + label + "</a>")
    out.append('</nav><div class="nav-right">')
    out.append('<button class="theme-toggle" aria-label="Toggle dark mode" data-theme-toggle><svg class="icon-sun" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg><svg class="icon-moon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg></button>')
    out.append('<form class="nav-search" onsubmit="return false;"><input type="search" placeholder="Search..." data-search></form>')
    out.append('</div></div></header>')
    return NL.join(out)

def page(title, body_str, active="home"):
    meta = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<link rel="icon" href="/favicon.png">',
        '<meta name="theme-color" content="#3B82F6" media="(prefers-color-scheme:light)">',
        '<link rel="stylesheet" href="/' + CSL + '">',
    ]
    return "<!doctype html><html lang=\"en\" data-theme=\"light\"><head>" + NL.join(meta) + "</head><body><script>try{var t=localStorage.getItem('tkhj-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}</script>" + nav(active) + "<main>" + body_str + "</main>" + footer() + '<script src="/' + JSL + '"></script></body></html>'

def wp(path, content):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

# ---- SEO: sitemap + robots ----
def gen_sitemap(articles):
    urls = []
    for path, prio, changefreq in [
        ("/", "1.0", "daily"),
        ("/exam/", "0.9", "daily"),
        ("/ai/", "0.9", "daily"),
        ("/about.html", "0.3", "monthly"),
        ("/search.html", "0.3", "monthly"),
    ]:
        urls.append(f"""  <url>
    <loc>https://{DOM}{path}</loc>
    <priority>{prio}</priority>
    <changefreq>{changefreq}</changefreq>
  </url>""")
    for a in articles:
        section = "exam" if a.get("exam") else "ai"
        url = f"https://{DOM}/{section}/article/{a['_slug']}.html"
        d = (a.get("date") or "").strip()[:10]
        prio = "0.8" if section == "exam" else "0.7"
        if d:
            urls.append(f"""  <url>
    <loc>{url}</loc>
    <lastmod>{d}</lastmod>
    <priority>{prio}</priority>
    <changefreq>weekly</changefreq>
  </url>""")
        else:
            urls.append(f"""  <url>
    <loc>{url}</loc>
    <priority>{prio}</priority>
    <changefreq>weekly</changefreq>
  </url>""")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls)
    xml += "\n</urlset>"
    wp("sitemap.xml", xml)
    wp("robots.txt", f"User-agent: *\nAllow: /\nSitemap: https://{DOM}/sitemap.xml\n")

# ---- SEO: related articles ----
def related_html(current_slug, all_articles, n=4):
    related = [a for a in all_articles if a["_slug"] != current_slug]
    related = related[:n]
    if not related:
        return ""
    items = []
    for a in related:
        section = "exam" if a.get("exam") else "ai"
        url = f"/{section}/article/{a['_slug']}.html"
        items.append('<li><a href="' + url + '">' + esc(a["title"]) + "</a></li>")
    return '<section class="related-articles"><h2>Related Articles</h2><ul>' + "\n".join(items) + "</ul></section>"

def about_page():
    hero = '<section class="section-hero" style="padding:64px 0 48px;text-align:left">'
    hero += '<div class="container">'
    hero += '<h1 style="font-size:clamp(1.8rem,4vw,2.6rem);line-height:1.2;margin:0 0 16px;color:var(--text-1);font-weight:800">About TKHJ Tools</h1>'
    hero += '<p style="margin:0;color:var(--text-2);max-width:640px;font-size:1.05rem">Independent study guides and honest AI tool comparisons. Built for students who deserve clarity.</p>'
    hero += '</div></section>'
    body = '<section class="section"><div class="container"><div style="max-width:680px;margin:0 auto">'
    body += '<h2 style="font-weight:800;margin:0 0 16px">Our Mission</h2>'
    body += '<p>TKHJ Tools exists because most student-focused content is either written by marketers trying to sell courses, or buried under search-engine junk.</p>'
    body += '<p><strong>How this site works:</strong> All articles start as AI drafts, then the editor personally reviews, fact-checks, and edits every piece. Exam strategies come from real classroom experience. AI tool reviews come from hands-on testing. If a claim cannot be verified, it is removed or rewritten.</p>'
    body += '<h2 style="font-weight:800;margin:40px 0 16px">FAQ</h2>'
    body += '<h3 style="font-weight:700;margin:0 0 8px">Who writes these guides?</h3>'
    body += '<p>A small team of educators and AI researchers. No freelancers, no AI-only spin. Every article is fact-checked by a human before publication.</p>'
    body += '</div></div></section>'
    return page("About", hero + body, "about")

def search_page():
    body = '<section class="section-hero" style="padding:64px 0 48px;text-align:left">'
    body += '<div class="container">'
    body += '<h1 style="font-size:clamp(1.8rem,4vw,2.6rem);line-height:1.2;margin:0 0 16px;color:var(--text-1);font-weight:800">Search</h1>'
    body += '</div></section>'
    body += '<section class="section"><div class="container"><div id="results" style="min-height:200px"><p id="search-status">Loading...</p></div></div></section>'
    body += '<script src="/static/search.js"></script>'
    return page("Search", body, "search")

def main():
    exam_arts = load_articles(EXAM, True)
    ai_arts = load_articles(AI, False)
    all_arts = exam_arts + ai_arts
    exam_html = NL.join(card(a, True) for a in exam_arts)
    ai_html = NL.join(card(a, False) for a in ai_arts)

    hero = '<section class="hero"><div style="max-width:720px;margin:0 auto">'
    hero += '<h1>Smarter learning, <span style="color:var(--brand)">powered by clarity</span>.</h1>'
    hero += '<p class="lead">' + TAG + '</p>'
    hero += '</div></section>'

    exam_tabs = tabs_html("exam", EXAM_TABS, 0, EXAM_ICON)
    exam_sect = '<section class="section" data-section="exam">'
    exam_sect += '<div class="container">'
    exam_sect += '<div class="section-head"><div class="title-wrap"><h2>Exam Prep Articles</h2></div><a href="/exam/" class="view-all">View all &rarr;</a></div>'
    exam_sect += exam_tabs
    exam_sect += '<div class="grid-4">' + exam_html + "</div>"
    exam_sect += '</div></section>'

    ai_tabs = tabs_html("ai", AI_TABS, 0, AI_ICON)
    ai_sect = '<section class="section-ai" data-section="ai">'
    ai_sect += '<div class="container">'
    ai_sect += '<div class="section-head"><div class="title-wrap"><h2>AI Tools &amp; Guides</h2></div><a href="/ai/" class="view-all">Explore all &rarr;</a></div>'
    ai_sect += ai_tabs
    ai_sect += '<div class="grid-4">' + ai_html + "</div>"
    ai_sect += '</div></section>'

    wp("index.html", page("Study guides & AI coverage", hero + exam_sect + ai_sect))
    wp("about.html", about_page())
    wp("search.html", search_page())

    idx = [{"title": a["title"], "url": ("/exam/" if a.get("exam") else "/ai/") + "article/" + a["_slug"] + ".html", "cat": a["_display_cat"], "kw": a["_keywords"], "date": a.get("date","")[:10]} for a in all_arts]
    wp("search_index.json", json.dumps(idx, ensure_ascii=False))

    exam_listing = section_hero("Exam Prep Articles","IELTS, TOEFL, GRE, SAT study guides.","Exam")
    exam_listing += '<section class="section" data-section="exam"><div class="container">'
    exam_listing += '<div class="grid-4">' + exam_html + "</div></div></section>"
    wp("exam/index.html", page("Exam Prep Articles", exam_listing, "exam"))

    ai_listing = section_hero("AI Tools & Guides","Workflows, prompts, and honest comparisons.","AI")
    ai_listing += '<section class="section-ai" data-section="ai"><div class="container">'
    ai_listing += '<div class="grid-4">' + ai_html + "</div></div></section>"
    wp("ai/index.html", page("AI Tools & Guides", ai_listing, "ai"))

    for a in exam_arts:
        slug = a["_slug"]
        meta, body = fm(a["_body"])
        rel = related_html(slug, all_arts)
        html = page(a["title"], '<article class="article-body"><h1>' + esc(a["title"]) + '</h1>' + md2html(body) + '</article>' + rel, "exam")
        wp("exam/article/" + slug + ".html", html)

    for a in ai_arts:
        slug = a["_slug"]
        meta, body = fm(a["_body"])
        rel = related_html(slug, all_arts)
        html = page(a["title"], '<article class="article-body"><h1>' + esc(a["title"]) + '</h1>' + md2html(body) + '</article>' + rel, "ai")
        wp("ai/article/" + slug + ".html", html)

    gen_sitemap(all_arts)

    print("Built:", len(exam_arts), "exams +", len(ai_arts), "ai")
    print("Ready for deployment.")

if __name__ == "__main__":
    main()
