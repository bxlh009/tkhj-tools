"""Backfill one Learning and one AI article per date through the normal gate."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta


ENGINE_DIR = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ENGINE_DIR / "scripts"
VARS_DIR = ENGINE_DIR / "vars"
MANIFEST = ENGINE_DIR / "site" / "content" / "guides.json"

AI_TOPICS = [
    (
        "Write Clear Instructions for a Repeatable AI Task",
        "Turn an informal request into a task, context boundary, output contract, and failure rule.",
        "https://ai.google.dev/gemini-api/docs/prompting-strategies",
    ),
    (
        "Use Few-Shot Examples Without Teaching the Wrong Pattern",
        "Choose varied examples, keep their format consistent, and test whether they narrow the intended behavior.",
        "https://ai.google.dev/gemini-api/docs/prompting-strategies",
    ),
    (
        "Design an AI Output Contract That Software Can Check",
        "Specify required fields, allowed values, missing-data behavior, and rejection conditions before generation.",
        "https://ai.google.dev/gemini-api/docs/prompting-strategies",
    ),
    (
        "Break a Complex AI Request into Verifiable Prompt Steps",
        "Use task decomposition and prompt chaining when one large response is difficult to inspect.",
        "https://ai.google.dev/gemini-api/docs/prompting-strategies",
    ),
    (
        "Add Context Without Letting an AI Invent Missing Facts",
        "Define a strict context boundary and an explicit response for information that is not supplied.",
        "https://ai.google.dev/gemini-api/docs/prompting-strategies",
    ),
    (
        "Build a Five-Case Test Set for an AI Prompt",
        "Test an ordinary case, ambiguity, missing information, distracting input, and a known edge case.",
        "https://ai.google.dev/gemini-api/docs/prompting-strategies",
    ),
    (
        "Keep a Failure Log for an AI-Assisted Workflow",
        "Record input, expected behavior, observed failure, prompt change, and regression result.",
        "https://ai.google.dev/gemini-api/docs/prompting-strategies",
    ),
    (
        "Decide When an AI Answer Needs Independent Verification",
        "Scale source checking and human review according to consequence and reversibility.",
        "https://airc.nist.gov/",
    ),
    (
        "Create a Human Review Checkpoint for AI Content",
        "Place review before the point where an unsupported claim becomes public or costly.",
        "https://airc.nist.gov/",
    ),
    (
        "Run a Reversible Pilot Before Automating Work with AI",
        "Define scope, success criteria, failure criteria, human authority, and rollback before expansion.",
        "https://www.nist.gov/itl/ai-risk-management-framework",
    ),
    (
        "Document Uncertainty in an AI-Assisted Decision",
        "Separate source evidence, model output, reviewer judgment, and unresolved questions.",
        "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
    ),
    (
        "Review AI-Generated Research Notes Before Reuse",
        "Trace claims to sources, distinguish quotations from paraphrases, and mark unresolved conflicts.",
        "https://airc.nist.gov/",
    ),
    (
        "Design a Safe AI Summarization Workflow",
        "Preserve source links, test omissions, flag unsupported additions, and require review for consequential summaries.",
        "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
    ),
    (
        "Choose What an AI Workflow Should Refuse to Do",
        "Turn missing context, high consequence, and conflicting instructions into explicit stop conditions.",
        "https://www.nist.gov/itl/ai-risk-management-framework",
    ),
    (
        "Compare Two Prompts with the Same Evaluation Cases",
        "Use fixed inputs and checks so a wording change can be evaluated without relying on preference alone.",
        "https://ai.google.dev/gemini-api/docs/prompting-strategies",
    ),
    (
        "Version an AI Prompt Without Losing Its Test History",
        "Connect each prompt change to a failure, expected improvement, and regression result.",
        "https://ai.google.dev/gemini-api/docs/prompting-strategies",
    ),
    (
        "Set a Risk Tier for AI-Generated Content",
        "Use consequence, audience, reversibility, and source availability to choose review depth.",
        "https://www.nist.gov/itl/ai-risk-management-framework",
    ),
    (
        "Create a Rollback Plan for an AI Automation",
        "Preserve the prior process, define monitoring signals, and assign authority to stop automated actions.",
        "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
    ),
]


def dates_between(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def published_dates() -> dict[str, set[str]]:
    result = {"learning": set(), "ai": set()}
    if not MANIFEST.exists():
        return result
    for item in json.loads(MANIFEST.read_text("utf-8")):
        track = item.get("track", "learning")
        published = item.get("published")
        if track in result and published:
            result[track].add(published)
    return result


def exam_vars() -> list[pathlib.Path]:
    candidates: list[pathlib.Path] = []
    for path in sorted(VARS_DIR.glob("*.json")):
        if path.name.startswith("example-"):
            continue
        try:
            values = json.loads(path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        exam_name = str(values.get("exam_name", "")).strip().lower()
        slug = str(values.get("slug", "")).strip().lower()
        exam_prefix = exam_name.replace(" ", "-")
        if (
            values.get("type", "exam") == "exam"
            and exam_name
            and slug.startswith(exam_prefix)
        ):
            candidates.append(path)
    return candidates


def run_generator(article_type: str, variables: pathlib.Path, publish_date: str) -> bool:
    command = [
        sys.executable,
        str(SCRIPTS_DIR / "generate.py"),
        "--type",
        article_type,
        "--vars",
        str(variables),
        "--date",
        publish_date,
        "--publish",
    ]
    result = subprocess.run(command, cwd=ENGINE_DIR)
    return result.returncode == 0


def ai_vars(topic: tuple[str, str, str], publish_date: str, directory: pathlib.Path) -> pathlib.Path:
    title, description, source = topic
    slug = "-".join(
        word.lower()
        for word in "".join(character if character.isalnum() else " " for character in title).split()
    )
    path = directory / f"ai-{publish_date}.json"
    path.write_text(
        json.dumps(
            {
                "type": "ai",
                "title": title,
                "description": description,
                "primary_keyword": title,
                "long_tail_keywords": [description],
                "slug": f"{publish_date}-{slug}",
                "min_words": 800,
                "max_words": 1500,
                "source_urls": [source],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2026-07-06")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end = datetime.strptime(args.end, "%Y-%m-%d").date()
    except ValueError:
        print("[ERROR] dates must use YYYY-MM-DD")
        return 2
    if end < start:
        print("[ERROR] --end must be on or after --start")
        return 2

    calendar = dates_between(start, end)
    existing = published_dates()
    missing_learning = [day for day in calendar if day.isoformat() not in existing["learning"]]
    missing_ai = [day for day in calendar if day.isoformat() not in existing["ai"]]
    print(
        f"Timeline {start}..{end}: missing Learning={len(missing_learning)}, "
        f"AI={len(missing_ai)}, total={len(missing_learning) + len(missing_ai)}"
    )
    if args.dry_run:
        for track, days in (("Learning", missing_learning), ("AI", missing_ai)):
            print(f"{track}: " + ", ".join(day.isoformat() for day in days))
        return 0

    if not os.environ.get("AGNES_API_KEY", "").strip():
        print("[ERROR] AGNES_API_KEY is not configured")
        return 2

    learning_topics = exam_vars()
    if not learning_topics:
        print("[ERROR] no Learning variable files are available")
        return 2

    failures: list[str] = []
    used_learning: set[pathlib.Path] = set()
    for day_index, day in enumerate(missing_learning):
        succeeded = False
        attempts = 0
        for offset in range(len(learning_topics)):
            topic = learning_topics[(day_index + offset) % len(learning_topics)]
            if topic in used_learning and len(used_learning) < len(learning_topics):
                continue
            attempts += 1
            print(f"\n[Learning {day}] attempt {attempts}: {topic.name}")
            if run_generator("exam", topic, day.isoformat()):
                used_learning.add(topic)
                succeeded = True
                break
            if attempts >= 3:
                break
        if not succeeded:
            failures.append(f"Learning {day}")

    with tempfile.TemporaryDirectory(prefix="tkhj-backfill-") as temp:
        temp_dir = pathlib.Path(temp)
        manifest_items = json.loads(MANIFEST.read_text("utf-8")) if MANIFEST.exists() else []
        used_ai_titles = {
            str(item.get("title", "")).strip()
            for item in manifest_items
            if item.get("track") == "ai"
        }
        for day_index, day in enumerate(missing_ai):
            succeeded = False
            attempts = 0
            for offset in range(len(AI_TOPICS)):
                topic = AI_TOPICS[(day_index + offset) % len(AI_TOPICS)]
                if topic[0] in used_ai_titles:
                    continue
                attempts += 1
                variables = ai_vars(topic, day.isoformat(), temp_dir)
                print(f"\n[AI {day}] attempt {attempts}: {topic[0]}")
                if run_generator("ai", variables, day.isoformat()):
                    used_ai_titles.add(topic[0])
                    succeeded = True
                    break
                if attempts >= 3:
                    break
            if not succeeded:
                failures.append(f"AI {day}")

    if failures:
        print("\n[ERROR] backfill incomplete:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    build = subprocess.run([sys.executable, str(ENGINE_DIR / "site" / "build.py")], cwd=ENGINE_DIR)
    if build.returncode != 0:
        return build.returncode
    audit = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "audit_adsense_readiness.py")],
        cwd=ENGINE_DIR,
    )
    if audit.returncode != 0:
        return audit.returncode
    print("\n[OK] timeline backfill complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
