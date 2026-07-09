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

# AdSense ca-pub line
AD_HEAD = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8913718352251239"></script>'

EXAM_TABS = ["All Exams","IELTS","TOEFL","GRE","SAT","More"]
AI_TABS   = ["All","AI","Tools","Prompts","Workflows","Productivity"]

if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir(parents=True, exist_ok=True)
for d in ["static","exam","exam/article","exam/tools","ai","ai/article","ai/tools"]:
    (OUT / d).mkdir(parents=True, exist_ok=True)
for f in STA.iterdir():
    if f.is_file(): shutil.copy2(str(f), str(OUT / "static" / f.name))

# favicon copied from static
_fav_src = HERE / "static" / "favicon.png"
if _fav_src.exists():
    shutil.copy2(str(_fav_src), str(OUT / "favicon.png"))

NL = chr(10)
def esc(s):
    s = str(s).replace("&","&amp;").replace("<","&lt;").replace('"',"&quot;")
    return s

def read(p): return pathlib.Path(p).read_text("utf-8")
def fm(md):
    md = md.lstrip("﻿")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", md, re.S)
    if not m: return {}, md
    meta = {}
    for line in m.group(1).splitlines():
        if ":" not in line: continue
        k,v = line.split(":",1)
        v = v.strip().strip("'""")
        if v.startswith("["):
            inner = v.strip("[]")
            v = [x.strip().strip("'""") for x in inner.split(",") if x.strip()]
        meta[k.strip()] = v
    return meta, m.group(2)

def clean_md(text):
    out = []
    for line in text.split(chr(10)):
        if re.match(r"^\s*\|[\s:]*-{3,}\|", line) or re.match(r"^\s*\|.*\|\s*$", line): continue
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

def load_articles(folder, is_exam=True):
    arts = []
    if not folder.exists(): return arts
    for f in folder.glob("*.md"):
        if re.search(r"-\d{1,2}$", f.stem) and not re.search(r"20\d{2}$", f.stem): continue
        body = read(f)
        meta, _ = fm(body)
        slug = f.stem
        title = meta.get("title", slug.replace("-"," ").title())
        arts.append({"_slug":slug,"_body":body,"_wc":len(body.split()),"title":title,"date":"","primary_keyword":""},)
    arts.sort(key=lambda a: a.get("date",""), reverse=True)
    return arts

print("build.py placeholder")