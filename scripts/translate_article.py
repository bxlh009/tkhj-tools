"""Generate faithful Simplified Chinese sidecars for curated English guides."""

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
from collections import Counter


ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "site" / "content"
TRANSLATIONS = CONTENT / "zh"
MANIFEST = CONTENT / "guides.json"
CONFIG = json.loads((ROOT / "scripts" / "config.json").read_text("utf-8"))


def urls(text: str) -> Counter[str]:
    return Counter(re.findall(r"https?://[^\s)\]>]+", text))


def heading_levels(text: str) -> list[int]:
    return [len(match.group(1)) for match in re.finditer(r"^(#{2,3})\s+", text, re.MULTILINE)]


def parse_response(response: str) -> tuple[str, str, str]:
    patterns = {
        "title": r"<translated-title>\s*(.*?)\s*</translated-title>",
        "description": r"<translated-description>\s*(.*?)\s*</translated-description>",
        "body": r"<translated-body>\s*(.*?)\s*</translated-body>",
    }
    values: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if not match:
            raise ValueError(f"translation response is missing {key}")
        values[key] = match.group(1).strip()
    return values["title"], values["description"], values["body"]


def validate_translation(source: str, title: str, description: str, body: str) -> list[str]:
    failures: list[str] = []
    if len(re.findall(r"[\u4e00-\u9fff]", title + description)) < 6:
        failures.append("translated title and description do not contain enough Chinese")
    minimum_han = max(80, len(re.findall(r"[A-Za-z]+", source)) // 4)
    if len(re.findall(r"[\u4e00-\u9fff]", body)) < minimum_han:
        failures.append("translated body is too short or not primarily Chinese")
    if heading_levels(source) != heading_levels(body):
        failures.append("Markdown H2/H3 structure changed")
    if urls(source) != urls(body):
        failures.append("source URLs changed or were omitted")
    if source.count("```") != body.count("```"):
        failures.append("fenced code block count changed")
    if re.search(r"<translated-(?:title|description|body)>", body, re.IGNORECASE):
        failures.append("response wrapper leaked into translated body")
    return failures


def sidecar(title: str, description: str, slug: str, body: str) -> str:
    return "\n".join(
        [
            "---",
            f"title: {json.dumps(title, ensure_ascii=False)}",
            f"description: {json.dumps(description, ensure_ascii=False)}",
            f"source_slug: {json.dumps(slug, ensure_ascii=False)}",
            "---",
            body.strip(),
            "",
        ]
    )


def call_agnes(system: str, user: str, retries: int = 3) -> str:
    key = os.environ.get(CONFIG["api"]["api_key_env"], "").strip()
    if not key:
        raise RuntimeError(f"missing environment variable {CONFIG['api']['api_key_env']}")
    payload = {
        "model": CONFIG["api"]["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": CONFIG["api"]["max_tokens"],
    }
    request = urllib.request.Request(
        CONFIG["api"]["base_url"],
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
            usage = result.get("usage", {})
            print(
                f"[INFO] translation tokens prompt={usage.get('prompt_tokens')} "
                f"completion={usage.get('completion_tokens')}"
            )
            return result["choices"][0]["message"]["content"]
        except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError) as error:
            last_error = error
            if attempt < retries:
                delay = 4 * attempt
                print(f"[WARN] translation API attempt {attempt}/{retries} failed; retry in {delay}s")
                time.sleep(delay)
    raise RuntimeError(f"translation API failed after {retries} attempts: {last_error}")


def prompt(item: dict[str, object], body: str) -> tuple[str, str]:
    system = (
        "You are the Chinese translation editor for TKHJ Tools. Translate faithfully into natural "
        "Simplified Chinese. Do not add, remove, soften, strengthen, or fact-check claims. Preserve "
        "every Markdown H2/H3 level, list, table, block quote, code fence, and URL exactly. Translate "
        "link labels and prose, but never alter a URL. Keep product and exam names accurate. Return "
        "only the three tagged sections requested."
    )
    user = f"""Translate this curated guide.

<source-title>{item["title"]}</source-title>
<source-description>{item["description"]}</source-description>
<source-body>
{body}
</source-body>

Return exactly:
<translated-title>Chinese title</translated-title>
<translated-description>Chinese description</translated-description>
<translated-body>
Full translated Markdown body
</translated-body>
"""
    return system, user


def translate_item(item: dict[str, object], *, force: bool = False) -> pathlib.Path:
    slug = str(item["slug"])
    destination = TRANSLATIONS / f"{slug}.md"
    if destination.exists() and not force:
        print(f"[SKIP] {slug}: Chinese sidecar already exists")
        return destination
    source = CONTENT / str(item["file"])
    body = source.read_text("utf-8")
    system, user = prompt(item, body)
    last_failures: list[str] = []
    for attempt in range(1, 3):
        title, description, translated_body = parse_response(call_agnes(system, user))
        last_failures = validate_translation(body, title, description, translated_body)
        if not last_failures:
            TRANSLATIONS.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                sidecar(title, description, slug, translated_body),
                encoding="utf-8",
            )
            print(f"[OK] translated {slug}")
            return destination
        print(f"[WARN] {slug} translation attempt {attempt} rejected: {'; '.join(last_failures)}")
    raise RuntimeError(f"{slug} translation failed validation: {'; '.join(last_failures)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Translate every missing curated guide")
    parser.add_argument("--slug", action="append", default=[], help="Translate one slug (repeatable)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not args.all and not args.slug:
        parser.error("choose --all or at least one --slug")

    items = json.loads(MANIFEST.read_text("utf-8-sig"))
    selected = items if args.all else [item for item in items if item["slug"] in set(args.slug)]
    if args.slug and len(selected) != len(set(args.slug)):
        found = {item["slug"] for item in selected}
        print(f"[ERROR] unknown slug(s): {', '.join(sorted(set(args.slug) - found))}")
        return 2

    failures: list[str] = []
    for index, item in enumerate(selected, 1):
        print(f"\n[{index}/{len(selected)}] {item['slug']}")
        try:
            translate_item(item, force=args.force)
        except (RuntimeError, ValueError) as error:
            failures.append(str(error))
            print(f"[ERROR] {error}")
    if failures:
        print(f"\n[ERROR] {len(failures)} translation(s) failed")
        return 1
    print(f"\n[OK] Chinese sidecars ready: {len(selected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
