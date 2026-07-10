import pathlib, re
issues = []
for folder in ["output/exams", "output/ai"]:
    for f in sorted(pathlib.Path(folder).glob("*.md")):
        content = f.read_text("utf-8")
        name = f.name
        no_math = re.sub(r"\$\$[^$]*\$\$|\$[^$]*\$|\\\\begin\{[a-zA-Z]*\}|\\\\end\{[a-zA-Z]*\}", "", content)
        unfilled = re.findall(r"\{[a-zA-Z_]+\}", no_math)
        if unfilled:
            issues.append(f"UNFILLED VARS {unfilled} in {name}")
        body = content.split("---\n")[-1] if content.startswith("---") else content
        if len(body.split()) < 100:
            issues.append(f"TOO SHORT ({len(body.split())}w): {name}")
        if 'title: "' not in content and "title: " not in content:
            issues.append(f"NO TITLE: {name}")
        if content.startswith("---"):
            parts = content.split("---\n", 2)
            if len(parts) < 3:
                issues.append(f"BROKEN YAML: {name}")
            elif "title:" not in parts[1]:
                issues.append(f"YAML NO TITLE: {name}")
for folder in ["site/_site/exam/article", "site/_site/ai/article"]:
    for f in sorted(pathlib.Path(folder).glob("*.html")):
        html = f.read_text("utf-8")
        name = f.relative_to("site/_site")
        m = re.search(r"<article class=\"article-body\">(.*?)</article>", html, re.S)
        if m and len(m.group(1).split()) < 50:
            issues.append(f"EMPTY BODY ({len(m.group(1).split())}w): {name}")
md_count = len(list(pathlib.Path("output/exams").glob("*.md"))) + len(list(pathlib.Path("output/ai").glob("*.md")))
print(f"Total articles: {md_count}")
print(f"Issues: {len(issues)}")
if issues:
    for i in issues:
        print(f"  - {i}")
else:
    print("ALL CLEAN - zero issues")
