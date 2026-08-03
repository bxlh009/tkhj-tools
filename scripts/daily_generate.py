# -*- coding: utf-8 -*-
"""
daily_generate.py — editorial draft generation pipeline

Behavior:
- Exam: picks one exam topic per run and generates an eligible draft
- AI:   fetches sources and generates an eligible draft
- Both use the same config.json and prompt templates as generate.py
- Nothing in this pipeline publishes, changes the public manifest, or rebuilds the site
"""
import argparse, json, pathlib, random, subprocess, sys
from datetime import datetime

HERE = pathlib.Path(__file__).resolve().parent
ENGINE = HERE.parent
VARS = ENGINE / "vars"
OUT_EXAM = ENGINE / "output" / "exams"
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


def infer_learning_pathway(slug):
    """Map a narrowly scoped learning slug to an existing public reader pathway."""
    slug = str(slug).strip().lower()
    if "question-types" in slug or "error-log" in slug:
        return "learning-diagnose"
    if "time-management" in slug or "time-plan" in slug or "study-plan" in slug:
        return "learning-plan"
    if "listening" in slug:
        return "learning-listen"
    if "speaking" in slug or "writing" in slug:
        return "learning-produce"
    if slug.startswith(("toefl-reading-", "toefl-primary-reading-")) or "vocabulary" in slug:
        return "learning-read"
    return None

if TOEFL_MODE:
    toefl_only = [f for f in EXAM_VARS if "toefl" in f.stem.lower()]
    if toefl_only:
        EXAM_VARS = toefl_only
        print(f"[TOEFL MODE] Focusing on TOEFL until {TOEFL_MODE_END.date()} ({len(EXAM_VARS)} topics available)")

def log_event(entry):
    entry["_time"] = datetime.now().isoformat()
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def pick_exam_topic(excluded=None, *, require_pathway=False):
    """Rotate through exam topics, one per day."""
    excluded = excluded or set()
    seen = {}
    if SEEN_VARS.exists():
        try:
            seen = json.loads(SEEN_VARS.read_text("utf-8"))
        except:
            seen = {}
    today = datetime.now().strftime("%Y-%m-%d")
    # If a draft already passed today, skip.
    if seen.get("date") == today:
        return None
    # Get list of already-generated topics (slugs)
    generated = set(f.stem for f in OUT_EXAM.glob("*.md"))
    available = [f for f in EXAM_VARS if f.stem not in generated and f not in excluded]
    # Skip var files marked as non-exam type (e.g. ai-news vars in the wrong folder)
    available = [
        f for f in available
        if json.loads(f.read_text('utf-8')).get('type', 'exam') == 'exam'
        and json.loads(f.read_text('utf-8')).get('exam_name')
    ]
    if require_pathway:
        available = [
            f for f in available
            if infer_learning_pathway(
                json.loads(f.read_text("utf-8")).get("slug", f.stem)
            )
        ]
    if not available:
        return None
    pick = random.choice(available)
    return pick


def mark_exam_drafted(var_path):
    SEEN_VARS.write_text(
        json.dumps(
            {"date": datetime.now().strftime("%Y-%m-%d"), "last": var_path.stem},
            indent=2,
        ),
        encoding="utf-8",
    )

def generate_exam(var_path, *, auto_publish=False):
    print(f"[exam] generating from {var_path.name}...")
    values = json.loads(var_path.read_text("utf-8"))
    pathway_id = infer_learning_pathway(values.get("slug", var_path.stem))
    if auto_publish and not pathway_id:
        print(f"[exam] skipped: no verified pathway for {var_path.name}")
        return False
    command = [
        sys.executable, str(HERE / "generate.py"), "--type", "exam", "--vars",
        str(var_path),
    ]
    if auto_publish:
        command.extend(["--auto-publish", "--pathway", pathway_id])
    r = subprocess.run(
        command,
        capture_output=True, text=True, timeout=600
    )
    if r.returncode == 0:
        print(r.stdout[-300:])
        log_event({"type": "exam", "var": var_path.name, "status": "ok", "output": r.stdout[-200:]})
    else:
        print(r.stderr[-300:])
        log_event({"type": "exam", "var": var_path.name, "status": "fail", "error": r.stderr[-200:]})
    return r.returncode == 0

def generate_ai_news(*, auto_publish=False):
    print("[ai] running daily_ai_news.py...")
    command = [sys.executable, str(HERE / "daily_ai_news.py")]
    if auto_publish:
        command.append("--auto-publish")
    r = subprocess.run(
        command,
        capture_output=True, text=True, timeout=180
    )
    print(r.stdout[-300:])
    log_event({"type": "ai", "status": "ok" if r.returncode == 0 else "fail", "output": r.stdout[-200:]})
    return r.returncode == 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", choices=["learning", "ai", "both"], default="both")
    parser.add_argument("--auto-publish", action="store_true")
    args = parser.parse_args()
    print(f"=== daily_generate.py — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    
    # 1. Exam: pick one topic and generate
    exam_ok = True
    if args.track in {"learning", "both"}:
        attempted = set()
        var_path = pick_exam_topic(attempted, require_pathway=args.auto_publish)
        if var_path is None:
            print("[exam] no unused eligible topic; safely skipping")
        else:
            exam_ok = False
            for attempt in range(1, 4):
                print(f"[exam] quality attempt {attempt}/3")
                attempted.add(var_path)
                if generate_exam(var_path, auto_publish=args.auto_publish):
                    mark_exam_drafted(var_path)
                    exam_ok = True
                    break
                var_path = pick_exam_topic(attempted, require_pathway=args.auto_publish)
                if var_path is None:
                    break
    
    # 2. AI: check news, generate if big story
    ai_ok = True
    if args.track in {"ai", "both"}:
        ai_ok = generate_ai_news(auto_publish=args.auto_publish)
    
    print("=== done ===")
    if not exam_ok or not ai_ok:
        print(
            f"[ERROR] draft generation incomplete: learning={exam_ok} ai={ai_ok}"
        )
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
