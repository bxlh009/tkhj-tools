"""Static AdSense-readiness checks for the generated TKHJ Tools site.

This is intentionally stricter than a generic HTML validator.  It protects the
editorial decisions made after the site's "low value content" rejection:
curated scope, transparent authorship, source notes, readable structure, and no
ad code before approval.
"""

from __future__ import annotations

import itertools
import pathlib
import re
import sys
from urllib.parse import urlsplit


ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site" / "_site"
ARTICLE_DIR = SITE / "guides"


def text_from_html(html: str) -> str:
    html = re.sub(r"<script\b.*?</script>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<style\b.*?</style>", " ", html, flags=re.I | re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip().lower()


def shingles(text: str, size: int = 5) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z0-9']+", text)
    return set(zip(*(words[offset:] for offset in range(size))))


def local_target(source: pathlib.Path, href: str) -> pathlib.Path | None:
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        return None
    path = parsed.path
    if not path:
        return None
    if path.startswith("/"):
        target = SITE / path.lstrip("/")
    else:
        target = source.parent / path
    if path.endswith("/"):
        target /= "index.html"
    return target


def main() -> int:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    require(SITE.exists(), "site/_site is missing; run: python site/build.py")
    if not SITE.exists():
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    html_files = sorted(SITE.rglob("*.html"))
    articles = (
        sorted(path for path in ARTICLE_DIR.glob("*.html") if path.name != "index.html")
        if ARTICLE_DIR.exists()
        else []
    )
    require(8 <= len(articles) <= 60, f"expected 8-60 gated guides, found {len(articles)}")

    all_html = "\n".join(path.read_text("utf-8") for path in html_files)
    require('<ins class="adsbygoogle"' not in all_html, "manual ad units are present before approval")
    require("(adsbygoogle=" not in all_html, "manual ad initialization is present before approval")
    require(':0">{items}' not in all_html, "malformed table-of-contents fragment is present")
    require((SITE / "learning" / "index.html").exists(), "Learning track index is missing")
    require((SITE / "ai" / "index.html").exists(), "AI track index is missing")
    require("Learning × AI" in all_html, "dual-domain positioning is missing")
    require("300+ students" not in all_html, "unverified teaching-volume claim is still published")

    suspicious_claims = (
        "i've watched hundreds",
        "i've graded thousands",
        "i ran a benchmark",
        "student named raj",
        "student named maria",
        "don't @ me",
    )

    article_text: dict[pathlib.Path, str] = {}
    for article in articles:
        html = article.read_text("utf-8")
        lower = html.lower()
        article_text[article] = text_from_html(html)
        require('<article class="article-body">' in html, f"{article.name}: missing article landmark")
        require('class="byline"' in html, f"{article.name}: missing visible byline")
        require("/about.html#editorial-team" in html, f"{article.name}: byline does not link to editorial details")
        require('class="editorial-note"' in html, f"{article.name}: missing creation/review disclosure")
        require('class="source-notes"' in html, f"{article.name}: missing source notes")
        require(len(re.findall(r"<h2\b", html, flags=re.I)) >= 3, f"{article.name}: fewer than three H2 sections")
        require(bool(re.search(r"<(?:ol|ul)\b", html, flags=re.I)), f"{article.name}: no semantic list")
        require('<link rel="canonical"' in html, f"{article.name}: missing canonical URL")
        require('dateModified' in html, f"{article.name}: schema lacks dateModified")
        for phrase in suspicious_claims:
            require(phrase not in lower, f"{article.name}: contains unverified/template phrase {phrase!r}")

    for left, right in itertools.combinations(articles, 2):
        a = shingles(article_text[left])
        b = shingles(article_text[right])
        score = len(a & b) / len(a | b) if a and b else 0.0
        require(score < 0.18, f"{left.name} and {right.name}: 5-word shingle similarity {score:.1%}")

    for source in html_files:
        html = source.read_text("utf-8")
        require('class="skip-link"' in html, f"{source.relative_to(SITE)}: missing skip link")
        for href in re.findall(r'href="([^"]+)"', html, flags=re.I):
            target = local_target(source, href)
            if target is not None:
                require(target.exists(), f"{source.relative_to(SITE)}: broken internal link {href}")

    if failures:
        print(f"AdSense readiness audit: {len(failures)} failure(s)")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    print(f"AdSense readiness audit: PASS ({len(articles)} curated guides, {len(html_files)} HTML pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
