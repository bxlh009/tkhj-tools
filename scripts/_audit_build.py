import pathlib, re

issues = []

# 1. Check all articles for missing dates
for folder in ["output/exams", "output/ai"]:
    for f in pathlib.Path(folder).glob("*.md"):
        content = f.read_text("utf-8")
        m = re.search(r'date:\s*"([^"]+)"', content)
        if not m or not m.group(1).strip():
            issues.append(f"MISSING DATE: {f.name}")

# 2. All HTML pages have favicon
for f in pathlib.Path("site/_site").rglob("*.html"):
    html = f.read_text("utf-8")
    if 'rel="icon"' not in html:
        issues.append(f"MISSING FAVICON TAG: {f.name}")
    if 'favicon.png' not in html:
        issues.append(f"MISSING FAVICON FILE: {f.name}")

# 3. Article pages have article-body class
for f in list(pathlib.Path("site/_site/exam/article").glob("*.html")) + list(pathlib.Path("site/_site/ai/article").glob("*.html")):
    html = f.read_text("utf-8")
    if 'article-body' not in html:
        issues.append(f"MISSING article-body CLASS: {f.name}")

# 4. Article pages have theme toggle
for f in list(pathlib.Path("site/_site/exam/article").glob("*.html"))[:3]:
    html = f.read_text("utf-8")
    if 'icon-sun' not in html:
        issues.append(f"MISSING theme-toggle SUN: {f.name}")
    if 'icon-moon' not in html:
        issues.append(f"MISSING theme-toggle MOON: {f.name}")

# 5. Check sitemap XML validity
smap = pathlib.Path("site/_site/sitemap.xml").read_text("utf-8")
empty_lastmod = re.findall(r"<lastmod></lastmod>", smap)
if empty_lastmod:
    issues.append(f"SITEMAP: {len(empty_lastmod)} empty lastmod tags")

# 6. Robots.txt has sitemap
robots = pathlib.Path("site/_site/robots.txt").read_text("utf-8")
if "sitemap.xml" not in robots:
    issues.append("ROBOTS.TXT: missing sitemap reference")

if issues:
    print("ISSUES FOUND:")
    for i in issues:
        print(f"  - {i}")
else:
    print("ALL CLEAN - no issues found")
