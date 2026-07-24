"""Generate a source-grounded Learning or AI draft and apply a blocking gate."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

from content_quality import evaluate_article
from publish_article import publish


SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
ENGINE_DIR = SCRIPTS_DIR.parent
CONFIG = json.loads((SCRIPTS_DIR / "config.json").read_text("utf-8"))
PROMPTS = ENGINE_DIR / "prompts"
RULES_FILE = ENGINE_DIR / "rules" / "WRITING_RULES.md"
EXAM_OUT = ENGINE_DIR / "output" / "exams"
AI_OUT = ENGINE_DIR / "output" / "ai"

OFFICIAL_EXAM_SOURCES = {
    "toefl": [
        "https://www.ets.org/toefl/test-takers/ibt/about/content.html",
        "https://www.ets.org/toefl/test-takers/ibt/prepare.html",
    ],
    "gre": [
        "https://www.ets.org/gre/test-takers/general-test/about/content.html",
        "https://www.ets.org/gre/test-takers/general-test/prepare.html",
    ],
    "ielts": [
        "https://ielts.org/take-a-test/test-types/ielts-academic-test",
        "https://ielts.org/take-a-test/preparation-resources",
    ],
    "sat": [
        "https://satsuite.collegeboard.org/sat/whats-on-the-test",
        "https://satsuite.collegeboard.org/practice",
    ],
}


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def inject(template: str, values: dict[str, object]) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template


def get_api_key() -> str:
    key = os.environ.get(CONFIG["api"]["api_key_env"], "").strip()
    if not key:
        raise RuntimeError(f"missing environment variable {CONFIG['api']['api_key_env']}")
    return key


def call_api(system: str, user: str, retries: int = 3, base_delay: int = 5) -> str:
    payload = {
        "model": CONFIG["api"]["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": CONFIG["api"]["temperature"],
        "top_p": CONFIG["api"].get("top_p", 1.0),
        "max_tokens": CONFIG["api"]["max_tokens"],
    }
    request = urllib.request.Request(
        CONFIG["api"]["base_url"],
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + get_api_key(),
        },
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                body = json.loads(response.read().decode())
            usage = body.get("usage", {})
            print(
                f"[INFO] prompt={usage.get('prompt_tokens')} "
                f"completion={usage.get('completion_tokens')}"
            )
            return body["choices"][0]["message"]["content"]
        except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError) as error:
            last_error = error
            if attempt < retries:
                delay = base_delay * (2 ** (attempt - 1))
                print(f"[WARN] API attempt {attempt}/{retries} failed; retry in {delay}s")
                time.sleep(delay)
    raise RuntimeError(f"API call failed after {retries} attempts: {last_error}")


def source_urls(article_type: str, values: dict[str, object]) -> list[str]:
    supplied = values.get("source_urls", [])
    if isinstance(supplied, str):
        supplied = [value.strip() for value in supplied.split(",") if value.strip()]
    urls = [str(value) for value in supplied if str(value).startswith("http")]
    if article_type == "exam":
        exam = str(values.get("exam_name", "")).lower()
        for key, official_urls in OFFICIAL_EXAM_SOURCES.items():
            if key in exam:
                urls.extend(official_urls)
                break
    return list(dict.fromkeys(urls))


def clean_body(text: str) -> str:
    text = text.strip().removeprefix("```markdown").removesuffix("```").strip()
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)
    text = re.sub(r"^#\s+.+\n+", "", text, count=1)
    return text.strip()


def build_article(
    body: str,
    *,
    article_type: str,
    values: dict[str, object],
    urls: list[str],
    publish_date: str | None = None,
) -> str:
    body = re.sub(r"\n## Sources\s*\n.*$", "", body, flags=re.IGNORECASE | re.DOTALL).rstrip()
    source_lines = "\n".join(f"- {url}" for url in urls)
    body = f"{body}\n\n## Sources\n\n{source_lines}\n"
    slug = str(values.get("slug", "untitled")).strip()
    title = str(values.get("title") or values.get("primary_keyword") or slug.replace("-", " ").title())
    domain = "learning" if article_type == "exam" else "ai"
    publish_date = publish_date or datetime.now().strftime("%Y-%m-%d")
    word_count = len(re.findall(r"[A-Za-zÀ-ž\u4e00-\u9fff]+", body))
    frontmatter = "\n".join(
        [
            "---",
            f"title: {json.dumps(title, ensure_ascii=False)}",
            f"slug: {json.dumps(slug, ensure_ascii=False)}",
            f'date: "{publish_date}"',
            f'domain: "{domain}"',
            f"category: {json.dumps(str(values.get('exam_name', 'AI')), ensure_ascii=False)}",
            f"primary_keyword: {json.dumps(str(values.get('primary_keyword', '')), ensure_ascii=False)}",
            f"word_count: {word_count}",
            "---",
            "",
        ]
    )
    return frontmatter + body


def first_free(directory: pathlib.Path, slug: str) -> pathlib.Path:
    candidate = directory / f"{slug}.md"
    suffix = 2
    while candidate.exists():
        candidate = directory / f"{slug}-{suffix}.md"
        suffix += 1
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["exam", "ai"])
    parser.add_argument("--vars", required=True)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument(
        "--date",
        help="Publication date in YYYY-MM-DD format (used by timeline backfills)",
    )
    args = parser.parse_args()

    values = json.loads(pathlib.Path(args.vars).read_text("utf-8"))
    publish_date = args.date or datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(publish_date, "%Y-%m-%d")
    except ValueError:
        print(f"[ERROR] invalid --date: {publish_date}")
        return 2
    values["current_date"] = publish_date
    urls = source_urls(args.type, values)
    values["source_urls"] = "\n".join(f"- {url}" for url in urls)

    prompt_name = "exam-method-prompt.md" if args.type == "exam" else "ai-news-prompt.md"
    user_prompt = inject(read(PROMPTS / prompt_name), values)
    system_prompt = inject(
        read(PROMPTS / "system_prompt_editorial.md"),
        {"rules": read(RULES_FILE)},
    )

    print(f"[INFO] generating [{args.type}] with {len(urls)} supplied source(s)")
    try:
        body = clean_body(call_api(system_prompt, user_prompt))
    except RuntimeError as error:
        print(f"[ERROR] {error}")
        return 2
    if not body:
        print("[ERROR] model returned an empty draft")
        return 2

    article = build_article(
        body,
        article_type=args.type,
        values=values,
        urls=urls,
        publish_date=publish_date,
    )
    out_dir = EXAM_OUT if args.type == "exam" else AI_OUT
    domain = "learning" if args.type == "exam" else "ai"
    minimum = int(values.get("min_words", 1500 if domain == "learning" else 800))
    maximum = int(values.get("max_words", 2500 if domain == "learning" else 1500))
    report = evaluate_article(
        article,
        domain=domain,
        min_words=minimum,
        max_words=maximum,
        source_urls=urls,
        existing_dir=out_dir,
    )
    print(f"[GATE] {report.summary()} | {report.metrics}")
    if not report.passed:
        return 3

    out_dir.mkdir(parents=True, exist_ok=True)
    slug = str(values.get("slug", f"draft-{datetime.now():%Y%m%d-%H%M%S}"))
    output = first_free(out_dir, slug)
    actual_slug = output.stem
    if actual_slug != slug:
        article = re.sub(
            r'^slug:\s*.+$',
            f"slug: {json.dumps(actual_slug, ensure_ascii=False)}",
            article,
            count=1,
            flags=re.MULTILINE,
        )
    output.write_text(article, encoding="utf-8")
    print(f"[OK] eligible draft written: {output}")
    if args.publish:
        destination = publish(output)
        print(f"[OK] published into site manifest: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
