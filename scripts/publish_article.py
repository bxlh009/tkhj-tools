"""Promote a gate-approved draft into the curated site manifest."""

from __future__ import annotations

import json
import hashlib
import pathlib
import re
from datetime import date
from urllib.parse import urlsplit

from content_quality import evaluate_article


ENGINE_DIR = pathlib.Path(__file__).resolve().parent.parent
CONTENT_DIR = ENGINE_DIR / "site" / "content"
MANIFEST = CONTENT_DIR / "guides.json"
CURATION = CONTENT_DIR / "curation.json"

AUTO_PRIMARY_DOMAINS = {
    "learning": {
        "ets.org", "ielts.org", "britishcouncil.org", "cambridgeenglish.org",
        "cambridge.org", "pearsonpte.com", "collegeboard.org", "act.org",
    },
    "ai": {
        "nist.gov", "google.dev", "developers.google.com", "openai.com",
        "anthropic.com", "microsoft.com", "github.com", "huggingface.co",
        "oecd.ai", "eur-lex.europa.eu",
    },
}


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
    rows: list[list[str]] = []
    for raw_url in urls:
        url = raw_url.rstrip(".,")
        hostname = (urlsplit(url).hostname or "source").casefold().removeprefix("www.")
        rows.append([hostname, url])
    return rows


def _has_primary_source(domain: str, sources: list[list[str]]) -> bool:
    allowed = AUTO_PRIMARY_DOMAINS[domain]
    return any(
        hostname == primary or hostname.endswith(f".{primary}")
        for hostname, _ in sources
        for primary in allowed
    )


def _primary_source_domains(domain: str, sources: list[list[str]]) -> set[str]:
    return {
        primary
        for hostname, _ in sources
        for primary in AUTO_PRIMARY_DOMAINS[domain]
        if hostname == primary or hostname.endswith(f".{primary}")
    }


def publish(
    draft_path: str | pathlib.Path,
    *,
    editorial_approval: bool = False,
    automatic_policy_approval: bool = False,
) -> pathlib.Path:
    if not editorial_approval and not automatic_policy_approval:
        raise ValueError(
            "explicit editorial approval or automatic policy approval is required"
        )
    if editorial_approval and automatic_policy_approval:
        raise ValueError("exactly one publication approval mode is required")
    draft = pathlib.Path(draft_path)
    draft_text = draft.read_text("utf-8")
    metadata, body = _frontmatter(draft_text)
    pathway_id = metadata.get("pathway_id", "").strip()
    if automatic_policy_approval and not pathway_id:
        raise ValueError("automatic publication requires a configured reader pathway")
    slug = metadata.get("slug") or draft.stem
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("article slug must be a safe lowercase slug")
    domain = metadata.get("domain", "learning")
    if domain not in {"learning", "ai"}:
        raise ValueError(f"unsupported domain: {domain}")
    source_rows = _sources(body)
    if automatic_policy_approval and not _has_primary_source(domain, source_rows):
        raise ValueError(
            f"automatic {domain} publication requires a primary-source domain"
        )
    primary_domains = _primary_source_domains(domain, source_rows)
    if automatic_policy_approval and domain == "ai" and len(primary_domains) < 2:
        raise ValueError(
            "automatic AI publication requires two independent primary-source domains"
        )
    curation: dict | None = None
    pathway: dict | None = None
    if automatic_policy_approval:
        curation = json.loads(CURATION.read_text("utf-8"))
        pathway = next(
            (
                candidate
                for candidate in curation.get("pathways", [])
                if candidate.get("id") == pathway_id
            ),
            None,
        )
        if pathway is None:
            raise ValueError(f"unknown reader pathway: {pathway_id}")
        if pathway.get("track") != domain:
            raise ValueError(f"reader pathway {pathway_id} does not belong to {domain}")

    quality_report = None
    if automatic_policy_approval:
        minimum = int(metadata.get("min_words", 1500 if domain == "learning" else 800))
        maximum = int(metadata.get("max_words", 2500 if domain == "learning" else 1500))
        quality_report = evaluate_article(
            draft_text,
            domain=domain,
            min_words=minimum,
            max_words=maximum,
            source_urls=[row[1] for row in source_rows],
            # Generation already checked corpus similarity immediately before saving.
            # Publication re-runs all intrinsic checks without comparing the draft to itself.
            existing_dir=None,
        )
        if not quality_report.passed:
            raise ValueError(f"automatic quality gate failed: {quality_report.summary()}")

    destination = CONTENT_DIR / f"{slug}.md"
    manifest = json.loads(MANIFEST.read_text("utf-8")) if MANIFEST.exists() else []
    title = metadata.get("title", slug.replace("-", " ").title()).strip()
    normalized_title = re.sub(r"\W+", " ", title.casefold()).strip()
    duplicate_title = next(
        (
            existing
            for existing in manifest
            if existing.get("slug") != slug
            and re.sub(r"\W+", " ", existing.get("title", "").casefold()).strip()
            == normalized_title
        ),
        None,
    )
    if duplicate_title:
        raise ValueError(
            f"duplicate public title: {duplicate_title.get('slug')} already uses {title!r}"
        )
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

    if automatic_policy_approval and curation is not None and pathway is not None:
        if slug in curation.get("excluded", {}):
            raise ValueError(f"excluded slug cannot be automatically republished: {slug}")
        existing_pathway = next(
            (
                candidate.get("id")
                for candidate in curation.get("pathways", [])
                if slug in candidate.get("slugs", [])
            ),
            None,
        )
        if existing_pathway and existing_pathway != pathway_id:
            raise ValueError(
                f"{slug} is already assigned to reader pathway {existing_pathway}"
            )
        if not existing_pathway:
            pathway.setdefault("slugs", []).append(slug)
        curation["updated"] = today

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    destination.write_text(body, encoding="utf-8")
    item = {
        "slug": slug,
        "file": destination.name,
        "title": title,
        "description": metadata.get("description") or _description(body),
        "category": metadata.get("category", "AI" if domain == "ai" else "Learning"),
        "track": domain,
        "published": today,
        "updated": today,
        "sources": source_rows,
        "automation_assisted": True,
        "editorial_status": "approved" if editorial_approval else "automatic_policy",
    }
    if automatic_policy_approval and quality_report is not None:
        item.update(
            {
                "publication_mode": "automatic_policy",
                "pathway_id": pathway_id,
                "quality_policy_version": 1,
                "quality_metrics": quality_report.metrics,
                "quality_fingerprint": hashlib.sha256(draft_text.encode("utf-8")).hexdigest(),
                "primary_source_domains": sorted(primary_domains),
            }
        )
    for index, existing in enumerate(manifest):
        if existing.get("slug") == slug:
            manifest[index] = item
            break
    else:
        manifest.append(item)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if automatic_policy_approval and curation is not None:
        CURATION.write_text(
            json.dumps(curation, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return destination


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("draft")
    parser.add_argument(
        "--editorial-approval",
        action="store_true",
        help="Confirm that an editor reviewed this draft and chose to publish it.",
    )
    args = parser.parse_args()
    print(publish(args.draft, editorial_approval=args.editorial_approval))
