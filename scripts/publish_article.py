"""Promote a gate-approved draft into the curated site manifest."""

from __future__ import annotations

import json
import pathlib
import re
from datetime import date


ENGINE_DIR = pathlib.Path(__file__).resolve().parent.parent
CONTENT_DIR = ENGINE_DIR / "site" / "content"
MANIFEST = CONTENT_DIR / "guides.json"


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.DOTALL)
    if not match:
        raise ValueError("article has no YAML frontmatter")
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        try:
            metadata[key.strip()] = str(json.loads(value))
        except (json.JSONDecodeError, TypeError):
            metadata[key.strip()] = value.strip("\"'")
    return metadata, match.group(2).strip() + "\n"


def _description(body: str) -> str:
    for paragraph in re.split(r"\n\s*\n", body):
        plain = re.sub(r"[#>*_`\[\]()]", "", paragraph).strip()
        if len(plain.split()) >= 12 and not plain.startswith("http"):
            return plain[:220].rsplit(" ", 1)[0] + ("…" if len(plain) > 220 else "")
    return "A source-grounded guide from the TKHJ Tools Editorial Team."


def _sources(body: str) -> list[list[str]]:
    urls = list(dict.fromkeys(re.findall(r"https?://[^\s)\]>]+", body)))
    return [["Source", url.rstrip(".,")] for url in urls]


def publish(draft_path: str | pathlib.Path) -> pathlib.Path:
    draft = pathlib.Path(draft_path)
    metadata, body = _frontmatter(draft.read_text("utf-8"))
    slug = metadata.get("slug") or draft.stem
    domain = metadata.get("domain", "learning")
    if domain not in {"learning", "ai"}:
        raise ValueError(f"unsupported domain: {domain}")

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    destination = CONTENT_DIR / f"{slug}.md"
    manifest = json.loads(MANIFEST.read_text("utf-8")) if MANIFEST.exists() else []
    today = metadata.get("date") or date.today().isoformat()
    same_day = next(
        (
            existing
            for existing in manifest
            if existing.get("track") == domain
            and existing.get("published") == today
            and existing.get("slug") != slug
        ),
        None,
    )
    if same_day:
        raise ValueError(
            f"{domain} already has an article for {today}: {same_day.get('slug')}"
        )

    destination.write_text(body, encoding="utf-8")
    item = {
        "slug": slug,
        "file": destination.name,
        "title": metadata.get("title", slug.replace("-", " ").title()),
        "description": metadata.get("description") or _description(body),
        "category": metadata.get("category", "AI" if domain == "ai" else "Learning"),
        "track": domain,
        "published": today,
        "updated": today,
        "sources": _sources(body),
        "automated": True,
    }
    for index, existing in enumerate(manifest):
        if existing.get("slug") == slug:
            manifest[index] = item
            break
    else:
        manifest.append(item)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return destination


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("draft")
    args = parser.parse_args()
    print(publish(args.draft))
