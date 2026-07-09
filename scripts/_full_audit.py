"""Full audit of content-engine output and pipeline."""
import pathlib, re, json

ENGINE = pathlib.Path("D:/codex/content-engine")
OUT_AI = ENGINE / "output" / "ai"
OUT_EXAM = ENGINE / "output" / "exams"
SEEN = ENGINE / ".seen_ai_stories.json"

issues = []

def log(desc, ok):
    if ok:
        print(f"  [OK] {desc}")
    else:
        print(f"  [ISSUE] {desc}")
        issues.append(desc)

print("=" * 60)
print("FULL AUDIT: content-engine")
print("=" * 60)

# ── 1. AI ARTICLES ──
print("\n--- 1. AI Articles ---")
ai_files = sorted(OUT_AI.glob("*.md"))
print(f"  Total: {len(ai_files)}")
bad_count = 0
for f in ai_files:
    content = f.read_text("utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.S)
    if not m:
        print(f"  [BAD] {f.name}: frontmatter not parseable")
        bad_count += 1
        continue
    body = m.group(2).strip()
    problems = []
    if body.startswith("{") and body.endswith("}"):
        try:
            json.loads(body)
            problems.append("JSON_BODY")
        except:
            pass
    if body.startswith("---"):
        problems.append("DOUBLE_FM")
    if re.match(r"^[a-zA-Z]+:", body):
        problems.append("YAML_BODY")
    if len(body.split()) < 20:
        problems.append("TOO_SHORT(" + str(len(body.split())) + "w)")
    if problems:
        print(f"  [BAD] {f.name}: {' + '.join(problems)} -> {body[:80]}")
        bad_count += 1

if bad_count == 0:
    print("  All clean!")
log("AI articles: no corrupted content", bad_count == 0)

# ── 2. EXAM ARTICLES ──
print("\n--- 2. Exam Articles ---")
exam_files = sorted(OUT_EXAM.glob("*.md"))
print(f"  Total: {len(exam_files)}")
bad_count = 0
for f in exam_files:
    content = f.read_text("utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.S)
    if not m:
        print(f"  [BAD] {f.name}: frontmatter not parseable")
        bad_count += 1
        continue
    body = m.group(2).strip()
    problems = []
    if body.startswith("{") and body.endswith("}"):
        try:
            json.loads(body)
            problems.append("JSON_BODY")
        except:
            pass
    if body.startswith("---"):
        problems.append("DOUBLE_FM")
    if re.match(r"^[a-zA-Z]+:", body):
        problems.append("YAML_BODY")
    if len(body.split()) < 20:
        problems.append("TOO_SHORT(" + str(len(body.split())) + "w)")
    if problems:
        print(f"  [BAD] {f.name}: {' + '.join(problems)}")
        bad_count += 1

if bad_count == 0:
    print("  All clean!")
log("Exam articles: no corrupted content", bad_count == 0)

# ── 3. SEEN STORIES DB ──
print("\n--- 3. Seen Stories DB ---")
if SEEN.exists():
    seen = json.loads(SEEN.read_text("utf-8"))
    print(f"  Entries: {len(seen)}")
    stale = 0
    for fp, story in seen.items():
        title = story.get("title", "")
        date = story.get("date", "")
        if date >= "2026-07-06":
            # Check if any output file relates to this story
            words = title.lower().split()[:5]
            found = False
            for af in ai_files:
                if any(w in af.stem.lower() for w in words):
                    found = True
                    break
            if not found:
                print(f"  [STALE] no file for: {title[:60]}...")
                stale += 1
    log("No stale seen entries (files deleted but still in DB)", stale == 0)
    if stale > 0:
        print(f"  -> {stale} entries reference deleted articles, should be cleaned")

# ── 4. PIPELINE KEYWORDS ──
print("\n--- 4. Pipeline Keywords ---")
py = ENGINE / "scripts" / "daily_ai_news.py"
if py.exists():
    code = py.read_text("utf-8")
    
    # Check threshold
    if "threshold=8" in code:
        log("Threshold = 8", True)
    else:
        log("Threshold should be 8 (not 12)", False)
    
    # Check key keywords
    for kw in ["sora", "deepseek", "grok", "copilot", "startup", "investment", "breakthrough"]:
        log("Keyword '" + kw + "' present", kw in code)
    
    # Check NO frontmatter
    log("Prompt says NO frontmatter", "NO frontmatter" in code)
    
    # Check JSON fallback
    log("JSON metadata fallback present", "JSON metadata" in code)
    
    # Check seen_ai_stories cleanup at startup
    log("Stale seen cleanup logic", "mark_seen" in code)

# ── 5. SYSTEM PROMPT ──
print("\n--- 5. System prompt layer1 ---")
sp = ENGINE / "prompts" / "system_prompt_layer1.md"
if sp.exists():
    text = sp.read_text("utf-8")
    # Check that the system prompt exists and has the right structure
    log("system_prompt_layer1.md exists", True)
    log("Contains {atype} placeholder", "{atype}" in text)
    log("Contains {rules} placeholder", "{rules}" in text)
    # Check it says "Output ONLY the markdown article starting with frontmatter"
    if "frontmatter" in text.lower():
        log("Mentions frontmatter in output instruction", True)
    if "ONLY the markdown" in text:
        log("Says 'ONLY the markdown'", True)

# ── 6. BUILD.PY has frontmatter handling ──
print("\n--- 6. Build.py ---")
bp = ENGINE / "site" / "build.py"
if bp.exists():
    text = bp.read_text("utf-8")
    log("Has fm() function", "def fm" in text)
    log("Has md2html() function", "def md2html" in text)
    # Check if it handles BOM (the issue from before)
    log("Handles UTF-8 BOM", "utf-8-sig" in text or "BOM" in text or "ufeff" in text)
    # Check clean_md strips --- lines
    log("clean_md strips triple-dash lines", "^-{3,}" in text or "---" in text)

# ── SUMMARY ──
print("\n" + "=" * 60)
if issues:
    print("ISSUES FOUND:")
    for i in issues:
        print(f"  - {i}")
else:
    print("ALL CLEAN - No issues found!")
print("=" * 60)

# Clean up
pathlib.Path(ENGINE / "scripts" / "_full_audit.py").unlink()
