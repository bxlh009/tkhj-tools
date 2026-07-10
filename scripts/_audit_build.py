import pathlib, re

issues = []
pages = list(pathlib.Path("site/_site/exam/article").glob("*.html")) + list(pathlib.Path("site/_site/ai/article").glob("*.html"))
print(f"Checking {len(pages)} article pages...")

for f in pages:
    html = f.read_text("utf-8")
    name = f.relative_to("site/_site")

    # Favicon
    if 'rel="icon"' not in html:
        issues.append(f"NO FAVICON: {name}")

    # Article body class
    if 'article-body' not in html:
        issues.append(f"NO article-body: {name}")

    # Theme toggle with sun+moon
    if 'icon-sun' not in html:
        issues.append(f"NO icon-sun: {name}")
    if 'icon-moon' not in html:
        issues.append(f"NO icon-moon: {name}")

    # nav.js loaded
    if 'nav.js' not in html:
        issues.append(f"NO nav.js: {name}")

    # style.css loaded
    if 'style.css' not in html:
        issues.append(f"NO style.css: {name}")

    # Has heading
    if "<h1>" not in html:
        issues.append(f"NO H1: {name}")

    # Has related articles
    if "Related Articles" not in html:
        issues.append(f"NO related: {name}")

    # Has disclaimer-like text
    if "Disclaimer" not in html and "disclaimer" not in html and "independently" not in html.lower():
        issues.append(f"NO DISCLAIMER: {name}")

    # No broken links (internal)
    bad_links = re.findall(r'href="([^"]*\.html)"', html)
    for link in bad_links:
        if link.startswith("/"):
            target = pathlib.Path(f"site/_site{link}")
            if not target.exists():
                issues.append(f"BROKEN LINK {link} in {name}")

print(f"\nChecked: {len(pages)} pages")
if issues:
    print(f"Issues: {len(issues)}")
    for i in issues[:30]:
        print(f"  - {i}")
    if len(issues) > 30:
        print(f"  ... and {len(issues)-30} more")
else:
    print("ALL CLEAN - zero issues")
