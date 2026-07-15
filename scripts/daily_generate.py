# -*- coding: utf-8 -*-
"""
daily_generate.py — daily exam + AI content pipeline

Schedule: run daily at 08:00 US Eastern (via Windows Task Scheduler)

Behavior:
- Exam: picks one exam topic per day (rotates), generates 1 article
- AI:   fetches RSS feeds, if big news found generates 1 article
- Both use the same config.json and prompt templates as generate.py
"""
import json, os, pathlib, random, subprocess, sys
from datetime import datetime

HERE = pathlib.Path(__file__).resolve().parent
ENGINE = HERE.parent
VARS = ENGINE / "vars"
OUT_EXAM = ENGINE / "output" / "exams"
OUT_AI = ENGINE / "output" / "ai"
LOG = ENGINE / "daily_log.jsonl"

# TOEFL focus mode: July 12-26, 2026
TOEFL_MODE_END = datetime(2026, 7, 26)
TOEFL_MODE = datetime.now() <= TOEFL_MODE_END
SEEN_VARS = ENGINE / ".seen_exam_vars.json"

# ---- Exam rotation ----
# All exam var files (excluding the examples)
EXAM_VARS = sorted([
    f for f in VARS.glob("*.json")
    if f.name not in [
        "example-toefl-reading.json", "example-ielts-writing.json",
        "example-gre-verbal.json", "example-sat-math.json",
        "example-ai-gpt5.json", "example-ai-claude.json",
    ]
])

if TOEFL_MODE:
    toefl_only = [f for f in EXAM_VARS if "toefl" in f.stem.lower()]
    if toefl_only:
        EXAM_VARS = toefl_only
        print(f"[TOEFL MODE] Focusing on TOEFL until {TOEFL_MODE_END.date()} ({len(EXAM_VARS)} topics available)")

def log_event(entry):
    entry["_time"] = datetime.now().isoformat()
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def pick_exam_topic():
    """Rotate through exam topics, one per day."""
    seen = {}
    if SEEN_VARS.exists():
        try:
            seen = json.loads(SEEN_VARS.read_text("utf-8"))
        except:
            seen = {}
    today = datetime.now().strftime("%Y-%m-%d")
    # If already picked today, skip
    if seen.get("date") == today:
        return None
    # Get list of already-generated topics (slugs)
    generated = set(f.stem for f in OUT_EXAM.glob("*.md"))
    available = [f for f in EXAM_VARS if f.stem not in generated]
    # Skip var files marked as non-exam type (e.g. ai-news vars in the wrong folder)
    available = [f for f in available if json.loads(f.read_text('utf-8')).get('type', 'exam') == 'exam']
    if not available:
        available = [f for f in EXAM_VARS if json.loads(f.read_text('utf-8')).get('type', 'exam') == 'exam']
        if not available:
            available = EXAM_VARS  # last resort
    pick = random.choice(available)
    seen["date"] = today
    seen["last"] = pick.stem
    SEEN_VARS.write_text(json.dumps(seen, indent=2), encoding="utf-8")
    return pick

def generate_exam(var_path):
    print(f"[exam] generating from {var_path.name}...")
    r = subprocess.run(
        [sys.executable, str(HERE / "generate.py"), "--type", "exam", "--vars", str(var_path)],
        capture_output=True, text=True, timeout=300
    )
    if r.returncode == 0:
        print(r.stdout[-300:])
        log_event({"type": "exam", "var": var_path.name, "status": "ok", "output": r.stdout[-200:]})
    else:
        print(r.stderr[-300:])
        log_event({"type": "exam", "var": var_path.name, "status": "fail", "error": r.stderr[-200:]})
    return r.returncode == 0

def generate_ai_news():
    print("[ai] running daily_ai_news.py...")
    r = subprocess.run(
        [sys.executable, str(HERE / "daily_ai_news.py")],
        capture_output=True, text=True, timeout=180
    )
    print(r.stdout[-300:])
    log_event({"type": "ai", "status": "ok" if r.returncode == 0 else "fail", "output": r.stdout[-200:]})
    return r.returncode == 0

def rebuild_site():
    print("[site] rebuilding...")
    r = subprocess.run(
        [sys.executable, str(ENGINE / "site" / "build.py")],
        capture_output=True, text=True, timeout=30
    )
    print(r.stdout.strip())
    log_event({"type": "build", "status": "ok" if r.returncode == 0 else "fail"})
    return r.returncode == 0

def main():
    print(f"=== daily_generate.py — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    
    # 1. Exam: pick one topic and generate
    var_path = pick_exam_topic()
    if var_path:
        generate_exam(var_path)
    else:
        print("[exam] already generated today, skipping")
    
    # 2. AI: check news, generate if big story
    generate_ai_news()
    
    # 3. Rebuild site
    rebuild_site()
    
    print("=== done ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
