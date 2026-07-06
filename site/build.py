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
AD_UNIT = '<ins class="adsbygoogle" style="display:block; text-align:center;" data-ad-layout="in-article" data-ad-format="fluid" data-ad-client="ca-pub-8913718352251239" data-ad-slot="4470604333"></ins><script>(adsbygoogle=window.adsbygoogle||[]).push({});</script>'
AD_HEAD = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8913718352251239" crossorigin="anonymous"></script>'

EXAM_TABS = ["All Exams","IELTS","TOEFL","GRE","SAT","More"]
AI_TABS   = ["All","AI","Tools","Prompts","Workflows","Productivity"]

EXAM_ICON = {"IELTS":"","TOEFL":"","GRE":"","SAT":"","More":""}
AI_ICON   = {"AI":"","Tools":"&#128295;","Prompts":"&#128220;","Workflows":"&#9881;&#65039;","Productivity":"&#128640;"}


if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir(parents=True, exist_ok=True)
for d in ["static","exam","exam/article","exam/tools","ai","ai/article","ai/tools"]:
    (OUT / d).mkdir(parents=True, exist_ok=True)
for f in STA.iterdir():
    if f.is_file(): shutil.copy2(str(f), str(OUT / "static" / f.name))
for f in HERE.glob("ads.txt"):
    if f.is_file(): shutil.copy2(str(f), str(OUT / f.name))

FAV = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#3B82F6"/><g transform="translate(7,6) scale(0.95)" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"/></g></svg>'
(OUT / "favicon.svg").write_text(FAV, encoding="utf-8")

NL = chr(10); Q = chr(34); SQ = chr(39); AMP = "&"
def esc(s):
    s = str(s)
    s = s.replace("&","&amp;").replace("<","&lt;").replace(Q,"&quot;")
    return s
def read(p): return pathlib.Path(p).read_text("utf-8")
def fm(md):
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
    """Per-project rules:
       - Strip markdown headings; treat them as paragraphs.
       - Remove tables completely (including --- separator rows).
       - Strip bullet markers at the start of a line (keep text).
       - Keep numbered lines as-is.
    """
    out = []
    for line in text.split(chr(10)):
        # skip table delimiter + content rows
        if re.match(r'^\s*\|?[\s:]*-{3,}[\s:]*(?:\|[\s:]*-{3,}[\s:]*)+\|?\s*$', line):
            continue
        if re.match(r'^\s*\|.*\|\s*$', line):
            continue
        # remove heading markers
        line = re.sub(r'^#{1,6}\s+', '', line)
        # remove bullet markers at start of line only
        if re.match(r'^\s*[-*]\s+', line):
            line = re.sub(r'^\s*[-*]\s+', '', line)
        out.append(line)
    return chr(10).join(out)

def esc(s):
    s = str(s).replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')
    return s

def md2html(text):
    text = clean_md(text)
    out = []
    for line in text.split(chr(10)):
        t = line.strip()
        if not t:
            continue
        if t.startswith('> '):
            out.append('<blockquote><p>' + esc(t[2:]) + '</p></blockquote>')
            continue
        out.append('<p>' + esc(t) + '</p>')
    body = chr(10).join(out)
    body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', body)
    body = re.sub(r'\*(.+?)\*', r'<em>\1</em>', body)
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

    cover = '<div class="card-cover">' + esc(cat) + ' &middot; ' + esc(m) + ' min</div>'

    data_kw = ' data-keywords="' + keywords_json + '"'
    body = '<div class="card-body">'
    body += '<span class="card-cat ' + cls + '">' + esc(cat) + "</span>"
    body += '<h3 class="card-title">' + title + "</h3>"
    body += '<p class="card-desc">' + kw + "</p>"
    body += '<div class="card-foot"><span>TKHJ Tools</span><span>' + date + "</span></div>"
    body += "</div>"

    return '<a class="card" href="' + url + '" data-card ' + data_kw + '>' + cover + body + "</a>"

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
        '<h4 style="margin:0 0 8px;font-size:1.05rem;color:var(--text-1)">' + NAME + '</h4><p>Student-first study guides for English exams and AI tools.</p>' +
        '',
        '<h4>Articles</h4><a href="/exam/">All Exam Articles</a><a href="/exam/tools/">Exam Tools</a><a href="/ai/">All AI Articles</a><a href="/ai/tools/">AI Tools</a>',
        '<h4>Popular Guides</h4><a href="/exam/article/ielts-writing-band-7-strategy.html">IELTS Writing Band 7</a><a href="/exam/article/toefl-reading-inference-strategy.html">TOEFL Reading</a><a href="/exam/article/gre-text-completion-master-plan.html">GRE Text</a><a href="/ai/article/gpt-5-vs-gpt-4o-comparison.html">GPT-5 vs GPT-4o</a>',

    ]
    grid = ""
    for c in cols:
        grid += '<div class="foot-col">' + c + "</div>"
    return '<footer class="site-footer"><div class="container"><div class="foot-grid">' + grid + '</div><p class="foot-copy">&copy; ' + y + " " + DOM + " · Independent study guides · All content is educational · Some content is AI-assisted and reviewed by human editors</ · Some content is AI-assisted and reviewed by human editorsp></div></footer>"

def nav(active="home"):
    out = ["<header class=\"site-header\">"]
    out.append("<div class=\"container nav-row\">")
    out.append("<a href=\"/\" class=\"brand\"><img src=\"/static/logo.svg\" alt=\"TKHJ Tools\" height=\"28\"></a>")
    out.append("<nav class=\"nav-links\">")
    for label, url, is_active in [
        ("Home","/",active=="home"),
        ("Exam","/exam/",active=="exam"),
        ("AI","/ai/",active=="ai"),
        ("About","/about.html",active=="about"),
        ("Privacy","/privacy.html",active=="privacy")
    ]:
        cls = "active" if is_active else ""
        out.append("<a href=\"" + url + "\" class=\"" + cls + "\">" + label + "</a>")
    out.append("</nav>")
    out.append("<div class=\"nav-right\">")
    out.append('<button class="theme-toggle" aria-label="Toggle dark mode" data-theme-toggle><svg class="icon-sun" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg><svg class="icon-moon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg></button>')
    out.append('<form class="nav-search" onsubmit="return false;">')
    out.append('<input type="search" placeholder="Search..." aria-label="Search" data-search>')
    out.append('</form>')
    out.append("</div></div></header>")
    return NL.join(out)

def page(title, body_str, active="home"):
    meta = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta name="theme-color" content="#3B82F6" media="(prefers-color-scheme:light)">',
        '<meta name="theme-color" content="#0B0F19" media="(prefers-color-scheme:dark)">',
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg">',
        '<title>' + esc(title) + ' &middot; ' + NAME + '</title>',
        '<meta name="description" content="' + TAG + '">',
        '<link rel="stylesheet" href="/' + CSL + '">',
        AD_HEAD,
    ]
    return "<!doctype html><html lang=\"en\" data-theme=\"light\"><head>" + NL.join(meta) + "</head><body><script>try{var t=localStorage.getItem('tkhj-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}</script>" + nav(active) + "<main>" + body_str + "</main>" + footer() + '<script src="/' + JSL + '"></script></body></html>'

def wp(path, content):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

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
            exams_lower = raw_exam.lower()
            slug_lower = slug.lower()
            if "ielts" in exams_lower or "ielts" in slug_lower:
                sec = (meta.get("section","").strip() or "Academic").split(" ")[0]
                display = "IELTS" + " " + sec
            elif "toefl" in exams_lower or "toefl" in slug_lower:
                sec = (meta.get("section","").strip() or "iBT").split(" ")[0]
                display = "TOEFL" + " " + sec
            elif "gre" in exams_lower or "gre" in slug_lower:
                sec = (meta.get("section","").strip() or "Verbal").split(" ")[0]
                display = "GRE" + " " + sec
            elif "sat" in exams_lower or "sat" in slug_lower:
                sec = (meta.get("section","").strip() or "Math").split(" ")[0]
                display = "SAT" + " " + sec
            else:
                display = raw_exam.strip() or "Exam"
        else:
            cat_map = {"comparison":"AI Comparison","model comparison":"AI Comparison","tools":"AI Tools","prompts":"Prompts","workflow":"Workflows","productivity":"Productivity"}
            display = cat_map.get(raw_cat.lower().strip(), "AI")
        arts.append({
            "_slug":slug, "_body":body, "_wc":len(body.split()),
            "title":title, "_keywords":keywords,
            "_display_cat":display,
            "exam":meta.get("exam","Exam"),
            "category":meta.get("category","AI"),
            "date":meta.get("date",""),
            "primary_keyword":meta.get("primary_keyword",""),
            "section":meta.get("section","General"),
        })
    arts.sort(key=lambda a: a["date"], reverse=True)
    return arts

def section_hero(title, desc, tag=None):
    out = '<section class="section-hero" style="padding:48px 0 32px;border-bottom:1px solid var(--line);background:var(--surface)">'
    out += '<div class="container">'
    if tag: out += '<span style="font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--brand);margin-bottom:8px;display:inline-block">' + esc(tag) + '</span>'
    out += '<h1 style="font-size:clamp(1.6rem,3.5vw,2.4rem);line-height:1.2;margin:0 0 12px;color:var(--text-1);letter-spacing:-.02em;font-weight:800">' + esc(title) + '</h1>'
    out += '<p style="margin:0;color:var(--text-2);max-width:640px">' + esc(desc) + '</p>'
    out += '</div></section>'
    return out

def privacy_page():
    hero = '<section class="section-hero" style="padding:64px 0 48px;text-align:left">'
    hero += '<div class="container">'
    hero += '<span style="font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--brand);margin-bottom:8px;display:inline-block">Legal</span>'
    hero += '<h1 style="font-size:clamp(1.8rem,4vw,2.6rem);line-height:1.2;margin:0 0 16px;color:var(--text-1);letter-spacing:-.02em;font-weight:800">Privacy Policy</h1>'
    hero += '<p style="margin:0;color:var(--text-2);max-width:640px;font-size:1.05rem">Last updated: July 6, 2026</p>'
    hero += '</div></section>'

    body = '<section class="section"><div class="container"><div style="max-width:680px;margin:0 auto">'

    body += '<h2 style="font-weight:800;color:var(--text-1);margin:0 0 16px">What We Collect</h2>'
    body += '<p>We do not collect personal information. We do not use cookies, trackers, or analytics scripts. This site is purely static content — no login, no comments, no forms, no user accounts.</p>'

    body += '<h2 style="font-weight:800;color:var(--text-1);margin:40px 0 16px">Third-Party Content</h2>'
    body += '<p>This site contains links to third-party websites. We are not responsible for their privacy practices. If you click an external link, you leave our domain.</p>'

    body += '<h2 style="font-weight:800;color:var(--text-1);margin:40px 0 16px">Educational Purpose</h2>'
    body += '<p>All content on this site is provided for educational and informational purposes only. It does not constitute professional advice.</p>'

    body += '<h2 style="font-weight:800;color:var(--text-1);margin:40px 0 16px">Contact</h2>'
    body += '<p>If you have questions about this policy, email us at: <a href="mailto:hello@tkhjtools.top" style="color:var(--brand);font-weight:600">hello@tkhjtools.top</a></p>'

    body += '</div></div></section>'
    return page('Privacy Policy', hero + body, 'privacy')


def search_page():
    body = '<section class="section-hero" style="padding:64px 0 48px;text-align:left">'
    body += '<div class="container">'
    body += '<h1 style="font-size:clamp(1.8rem,4vw,2.6rem);line-height:1.2;margin:0 0 16px;color:var(--text-1);letter-spacing:-.02em;font-weight:800">Search Results</h1>'
    body += '<form onsubmit="event.preventDefault();var q=this.querySelector(\'[data-srch]\').value;window.location=\"/search.html?q=\"+encodeURIComponent(q);">'
    body += '<input data-srch type="search" placeholder="Search articles..." style="padding:12px 18px;width:100%%;max-width:480px;border:2px solid var(--line);border-radius:10px;font-size:1rem;background:var(--card);color:var(--text-1);outline:none">'
    body += '</form></div></section>'
    body += '<section class="section"><div class="container"><div id="results" style="min-height:200px"><p style="color:var(--text-3)">Loading...</p></div></div></section>'
    body += '<script src="/static/search.js"></script>'
    return page('Search', body, 'search')

def about_page():
    hero = '<section class="hero" style="padding:64px 0 48px;text-align:left">'
    hero += '<div class="container">'
    hero += '<span style="font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--brand);margin-bottom:8px;display:inline-block">About</span>'
    hero += '<h1 style="font-size:clamp(1.8rem,4vw,2.6rem);line-height:1.2;margin:0 0 16px;color:var(--text-1);letter-spacing:-.02em;font-weight:800">About TKHJ Tools</h1>'
    hero += '<p style="margin:0;color:var(--text-2);max-width:640px;font-size:1.05rem">Independent study guides and honest AI tool comparisons. Built for students who deserve clarity, not clickbait.</p>'
    hero += '</div></section>'

    body = '<section class="section"><div class="container">'
    body += '<div style="max-width:680px;margin:0 auto">'
    body += '<h2 style="font-weight:800;color:var(--text-1);margin:0 0 16px">Our Mission</h2>'
    body += '<p>TKHJ Tools exists because most student-focused content is either written by marketers trying to sell you courses, or buried under search-engine junk. We do neither.</p>'
    body += '<p>Every guide on this site follows one rule: <strong style="color:var(--text-1)">&ldquo;Would this actually help a friend study at 2am?&rdquo;</strong> If not, it does not go live.</p>'
    body += '<p>We cover foreign exams at every level — elementary, middle school, high school, and beyond — and the AI tools (ChatGPT, Claude, Gemini, Notion AI, and whatever comes next) that are changing how students prepare for them.</p>'

    body += '<h2 style="font-weight:800;color:var(--text-1);margin:40px 0 16px">What Makes Us Different</h2>'
    body += '<ul style="padding-left:22px;margin:0 0 24px">'
    body += '<li style="margin-bottom:10px"><strong style="color:var(--text-1)">No paywalls, no course pitching.</strong> Every article is free. We do not upsell you to a paid class at the end.</li>'
    body += '<li style="margin-bottom:10px"><strong style="color:var(--text-1)">Honest AI tool comparisons.</strong> We tell you when a tool is overhyped. We tell you when the free tier is enough. We do not parrot press releases.</li>'
    body += '<li style="margin-bottom:10px"><strong style="color:var(--text-1)">Real exam strategy.</strong> Not generic &ldquo;practice more&rdquo; advice. Specific tactics tested on real practice tests.</li>'
    body += '<li style="margin-bottom:10px"><strong style="color:var(--text-1)">Independent.</strong> We are not affiliated with ETS, the British Council, College Board, or any AI vendor.</li>'
    body += '</ul>'

    body += '<h2 style="font-weight:800;color:var(--text-1);margin:40px 0 16px">FAQ</h2>'
    body += '<h3 style="font-weight:700;color:var(--text-1);font-size:1.05rem;margin:0 0 8px">Who writes these guides?</h3>'
    body += '<p>A small team of educators and AI researchers. No freelancers, no AI-only spin. Every article is fact-checked and edited by a human before it goes live.</p>'

    body += '<h3 style="font-weight:700;color:var(--text-1);font-size:1.05rem;margin:28px 0 8px">How do you make money?</h3>'
    body += '<p>We do not, yet. This is a passion project first. If we ever add affiliate links or sponsored reviews, they will be clearly labeled and never placed above honest recommendations.</p>'

    body += '<h3 style="font-weight:700;color:var(--text-1);font-size:1.05rem;margin:28px 0 8px">I found a mistake. Can I report it?</h3>'
    body += '<p>Please do. Email us at <a href="mailto:hello@tkhjtools.top" style="color:var(--brand);font-weight:600">hello@tkhjtools.top</a>. We fix factual errors within 48 hours.</p>'

    body += '<h3 style="font-weight:700;color:var(--text-1);font-size:1.05rem;margin:28px 0 8px">Can you cover my exam / tool?</h3>'
    body += '<p>Send requests to <a href="mailto:ideas@tkhjtools.top" style="color:var(--brand);font-weight:600">ideas@tkhjtools.top</a>. We read every message and publish the most-requested guides first.</p>'
    body += '</div></div></section>'

    return page("About TKHJ Tools", hero + body, "about")

def main():
    exam_arts = load_articles(EXAM, True)
    ai_arts   = load_articles(AI, False)

    exam_html = NL.join(card(a, True) for a in exam_arts)
    ai_html   = NL.join(card(a, False) for a in ai_arts)

    # HOME HERO
    hero = '<section class="hero"><div style="max-width:720px;margin:0 auto">'
    hero += '<h1>Smarter learning, <span style="color:var(--brand)">powered by clarity</span>.</h1>'
    hero += '<p class="lead">' + TAG + '</p>'
    
    hero += '</div></section>'

    exam_tabs = tabs_html("exam", EXAM_TABS, 0, EXAM_ICON)
    exam_sect = '<section class="section" data-section="exam">'
    exam_sect += '<div class="container">'
    exam_sect += '<div class="section-head"><div class="title-wrap"><h2> Exam Prep Articles</h2><p class="sub">Study guides for foreign exams — from elementary to graduate level.</p></div><a href="/exam/" class="view-all">View all exam articles &rarr;</a></div>'
    exam_sect += exam_tabs
    exam_sect += '<div class="grid-4">' + exam_html + "</div>"
    exam_sect += '</div></section>'

    ai_tabs = tabs_html("ai", AI_TABS, 0, AI_ICON)
    ai_sect = '<section class="section-ai" data-section="ai">'
    ai_sect += '<div class="container">'
    ai_sect += '<div class="section-head"><div class="title-wrap"><h2> AI Tools &amp; Guides</h2><p class="sub">Latest AI breakthroughs, tools, and what they actually mean.</p></div><a href="/ai/" class="view-all">Explore all AI articles &rarr;</a></div>'
    ai_sect += ai_tabs
    ai_sect += '<div class="grid-4">' + ai_html + "</div>"
    ai_sect += '</div></section>'

    wp("index.html", page("Study guides & AI coverage", hero + exam_sect + ai_sect))

    # ABOUT PAGE
    wp("about.html", about_page())
    wp("privacy.html", privacy_page())

    # Generate search index
    idx = [{"title": a["title"], "url": ("/exam/" if a.get("exam") else "/ai/") + "article/" + a["_slug"] + ".html", "cat": a["_display_cat"], "kw": a["_keywords"], "date": a.get("date","")[:10]} for a in exam_arts + ai_arts]
    wp("search_index.json", json.dumps(idx, ensure_ascii=False))
    wp("search.html", search_page())

    # SUBDIR LISTING PAGES
    exam_listing = section_hero("Exam Prep Articles","IELTS, TOEFL, GRE, SAT study guides from real exam questions.","Exam")
    exam_listing += '<section class="section" data-section="exam"><div class="container">'
    exam_listing += '<div class="tabs" data-tabs="exam">' + NL.join(
        '<button class="tab' + (' active' if i==0 else '') + '" data-tab="exam" data-val="' + esc(l) + '">' + (EXAM_ICON.get(l,"") + " " if EXAM_ICON.get(l,"") else "") + esc(l) + "</button>"
        for i,l in enumerate(EXAM_TABS)
    ) + '</div>'
    exam_listing += '<div class="grid-4">' + exam_html + "</div></div></section>"
    wp("exam/index.html", page("Exam Prep Articles", exam_listing, "exam"))

    ai_listing = section_hero("AI Tools & Guides","Workflows, prompts, and honest comparisons for students and creators.","AI")
    ai_listing += '<section class="section-ai" data-section="ai"><div class="container">'
    ai_listing += '<div class="tabs" data-tabs="ai">' + NL.join(
        '<button class="tab' + (' active' if i==0 else '') + '" data-tab="ai" data-val="' + esc(l) + '">' + (AI_ICON.get(l,"") + " " if AI_ICON.get(l,"") else "") + esc(l) + "</button>"
        for i,l in enumerate(AI_TABS)
    ) + '</div>'
    ai_listing += '<div class="grid-4">' + ai_html + "</div></div></section>"
    wp("ai/index.html", page("AI Tools & Guides", ai_listing, "ai"))

    # ARTICLE PAGES
    for a in exam_arts:
        slug = a["_slug"]
        meta, body = fm(a["_body"])
        html = page(a["title"],
            '<article class="article">'
            + '<div class="article-hero"><div class="container">'
            + '<span class="tag">' + esc(a.get("section","Exam")) + '</span>'
            + '<h1>' + esc(a["title"]) + '</h1>'
            + '<div class="meta"><span>&#9200; ' + str(max(1, a["_wc"] // 220)) + ' min read</span><span>' + esc(a.get("date","")[:10]) + '</span><span>' + esc(a["_display_cat"]) + '</span></div>'
            + '</div></div>'
            + '<div class="article-body">' + (lambda h: h[:h.find(chr(60)+chr(47)+chr(112)+chr(62), len(h)//2)] + AD_UNIT + h[h.find(chr(60)+chr(47)+chr(112)+chr(62), len(h)//2):])(md2html(body)) + '</div>'
            + '</article>', "exam")
        wp("exam/article/" + slug + ".html", html)

    for a in ai_arts:
        slug = a["_slug"]
        meta, body = fm(a["_body"])
        html = page(a["title"],
            '<article class="article">'
            + '<div class="article-hero"><div class="container">'
            + '<span class="tag">' + esc(a.get("category","AI")) + '</span>'
            + '<h1>' + esc(a["title"]) + '</h1>'
            + '<div class="meta"><span>&#9200; ' + str(max(1, a["_wc"] // 220)) + ' min read</span><span>' + esc(a.get("date","")[:10]) + '</span><span>' + esc(a["_display_cat"]) + '</span></div>'
            + '</div></div>'
            + '<div class="article-body">' + (lambda h: h[:h.find(chr(60)+chr(47)+chr(112)+chr(62), len(h)//2)] + AD_UNIT + h[h.find(chr(60)+chr(47)+chr(112)+chr(62), len(h)//2):])(md2html(body)) + '</div>'
            + '</article>', "ai")
        wp("ai/article/" + slug + ".html", html)

    print("Built:", len(exam_arts), "exam +", len(ai_arts), "ai + 1 about")
    print("  /  /exam/  /ai/  /about.html  /privacy.html  /search.html")

if __name__ == "__main__":
    main()
