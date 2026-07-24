"""Deterministic quality gate for automatically generated articles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


FALSE_AUTHORITY_PATTERNS = {
    "invented teaching or testing experience": (
        r"\bI (?:have |have personally |personally )?(?:taught|tested|reviewed|used)\b",
        r"\b(?:my|our) students?\b",
        r"\bI scored \d",
        r"\b\d+\+?\s+(?:students|hours testing|users|customers)\b",
        r"\bone of my students\b",
    ),
    "unsupported outcome promise": (
        r"\b(?:we|I|this method|this guide) guarantee(?:s|d)?\b",
        r"\bguaranteed (?:result|score|improvement|outcome)s?\b",
        r"\braise your score by\b",
        r"\bimprove(?:d)? from \d+ to \d+\b",
        r"\bsave(?:d|s)? \d+ (?:hours|minutes)\b",
    ),
    "fabricated social proof": (
        r"\bwent viral\b",
        r"\b\d[\d,]*\s+(?:likes|shares|views)\b",
        r"\bI screenshotted\b",
    ),
}

PLACEHOLDER_PATTERNS = (
    r"\[(?:insert|image|screenshot|chart)[^\]]*\]",
    r"\bTODO\b",
    r"\bTBD\b",
    r"\{\{[^}]+\}\}",
)


@dataclass(frozen=True)
class QualityReport:
    passed: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    metrics: dict[str, object]

    def summary(self) -> str:
        label = "PASS" if self.passed else "FAIL"
        details = "; ".join(self.errors or self.warnings) or "all checks passed"
        return f"{label}: {details}"


def article_body(text: str) -> str:
    match = re.match(r"^---\s*\n.*?\n---\s*\n", text, flags=re.DOTALL)
    return text[match.end() :] if match else text


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-zÀ-ž\u4e00-\u9fff]+(?:['’-][A-Za-zÀ-ž]+)?", text))


def _word_shingles(text: str, size: int = 5) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z0-9']+", article_body(text).lower())
    return set(zip(*(words[offset:] for offset in range(size))))


def _similarity_to_existing(text: str, existing_dir: str | Path) -> tuple[str | None, float]:
    candidate = _word_shingles(text)
    closest_name: str | None = None
    closest_score = 0.0
    for path in Path(existing_dir).glob("*.md"):
        existing = _word_shingles(path.read_text("utf-8"))
        score = len(candidate & existing) / len(candidate | existing) if candidate and existing else 0.0
        if score > closest_score:
            closest_name = path.name
            closest_score = score
    return closest_name, closest_score


def evaluate_article(
    text: str,
    *,
    domain: str,
    min_words: int,
    max_words: int,
    source_urls: list[str],
    existing_dir: str | Path | None = None,
    similarity_threshold: float = 0.30,
) -> QualityReport:
    """Return a blocking report for a learning or AI article."""
    if domain not in {"learning", "ai"}:
        raise ValueError("domain must be 'learning' or 'ai'")

    body = article_body(text)
    lowered = body.lower()
    errors: list[str] = []
    warnings: list[str] = []

    words = _word_count(body)
    headings = len(re.findall(r"^##\s+\S", body, flags=re.MULTILINE))
    paragraphs = len([p for p in re.split(r"\n\s*\n", body) if len(p.split()) >= 8])
    urls = sorted(set(re.findall(r"https?://[^\s)\]>]+", text)))

    if words < min_words:
        errors.append(f"too short: {words} words, minimum {min_words}")
    if words > int(max_words * 1.15):
        errors.append(f"too long: {words} words, maximum {max_words}")
    if headings < 3:
        errors.append(f"insufficient structure: {headings} section headings")
    if paragraphs < 6:
        errors.append(f"too few substantive paragraphs: {paragraphs}")
    if not source_urls:
        errors.append("no supplied source URL")
    missing_sources = [url for url in source_urls if url not in urls]
    if missing_sources:
        errors.append("supplied sources are missing from the article")

    for label, patterns in FALSE_AUTHORITY_PATTERNS.items():
        if any(re.search(pattern, body, flags=re.IGNORECASE) for pattern in patterns):
            errors.append(label)

    if any(re.search(pattern, body, flags=re.IGNORECASE) for pattern in PLACEHOLDER_PATTERNS):
        errors.append("unresolved placeholder")

    if domain == "learning":
        example_signals = len(
            re.findall(
                r"\b(?:worked example|practice example|original example|try this|sample question|scenario)\b",
                lowered,
            )
        )
        if example_signals < 2:
            errors.append("learning article needs at least two original practice/example sections")
        if not re.search(r"\b(?:answer|solution|reasoning|why it works|check your answer)\b", lowered):
            errors.append("learning article has no explained answer or reasoning")
    else:
        if re.search(r"\b(?:I|we) (?:ran|benchmarked|measured|compared) (?:the|this|these)\b", body):
            errors.append("unsupported first-person product test")
        if not re.search(r"\b(?:limitation|limits|uncertain|not disclosed|verify|caveat)\b", lowered):
            errors.append("AI article does not state limitations or uncertainty")
        if not re.search(r"\b(?:who should|when to use|when to skip|what this means|next step|decision)\b", lowered):
            errors.append("AI article lacks a reader decision or next step")

    max_similarity = 0.0
    similar_name: str | None = None
    if existing_dir is not None and Path(existing_dir).exists():
        similar_name, max_similarity = _similarity_to_existing(text, existing_dir)
        if max_similarity >= similarity_threshold:
            errors.append(
                f"too similar to {similar_name}: {max_similarity:.0%} "
                f"(limit {similarity_threshold:.0%})"
            )

    if words < int(min_words * 1.1):
        warnings.append("word count is close to the minimum")

    return QualityReport(
        passed=not errors,
        errors=tuple(dict.fromkeys(errors)),
        warnings=tuple(dict.fromkeys(warnings)),
        metrics={
            "domain": domain,
            "word_count": words,
            "headings": headings,
            "paragraphs": paragraphs,
            "source_count": len(urls),
            "max_similarity": round(max_similarity, 3),
            "similar_article": similar_name,
        },
    )
