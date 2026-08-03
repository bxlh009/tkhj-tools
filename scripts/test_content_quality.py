import tempfile
import unittest
from pathlib import Path

from content_quality import evaluate_article


SOURCE = "https://developers.google.com/search/docs/fundamentals/creating-helpful-content"


def distinct_paragraphs(count: int, topic: str) -> str:
    return "\n\n".join(
        f"{topic} step {index} focuses on evidence item {index}, records a distinct observation, "
        f"and produces a checkable action for practice round {index}."
        for index in range(1, count + 1)
    )


def learning_article(extra: str = "") -> str:
    return f"""---
title: "Evidence method"
---

## Diagnose the decision

{distinct_paragraphs(12, "Diagnosis")}

## Original practice example one

Scenario: A reader must separate a stated fact from an inference.

{distinct_paragraphs(8, "First scenario")}

The answer follows from the quoted evidence, and the reasoning rejects outside knowledge.

## Original practice example two

Try this scenario with a different topic.

{distinct_paragraphs(8, "Second scenario")}

Check your answer by underlining the phrase that controls the decision.

## Sources

- {SOURCE}

{extra}
"""


def ai_article(extra: str = "") -> str:
    return f"""---
title: "AI decision brief"
---

## What changed

{distinct_paragraphs(12, "Source claim")}

## What this means

{distinct_paragraphs(10, "Interpretation")}

## Limits and uncertainty

The exact performance impact was not disclosed, so readers should verify the claim.

{distinct_paragraphs(8, "Uncertainty")}

## When to use it

Who should adopt it now, and when to skip it, depends on a small reversible trial.

{distinct_paragraphs(8, "Decision")}

## Sources

- {SOURCE}

{extra}
"""


class ContentQualityTests(unittest.TestCase):
    def test_good_learning_article_passes(self):
        report = evaluate_article(
            learning_article(),
            domain="learning",
            min_words=300,
            max_words=1500,
            source_urls=[SOURCE],
        )
        self.assertTrue(report.passed, report.errors)

    def test_fake_authority_is_blocked(self):
        report = evaluate_article(
            learning_article("I have taught 300+ students and my students always improve."),
            domain="learning",
            min_words=300,
            max_words=1500,
            source_urls=[SOURCE],
        )
        self.assertFalse(report.passed)
        self.assertIn("invented teaching or testing experience", report.errors)

    def test_ai_stub_is_blocked(self):
        report = evaluate_article(
            f"## News\nDetails are emerging. See {SOURCE}",
            domain="ai",
            min_words=300,
            max_words=1500,
            source_urls=[SOURCE],
        )
        self.assertFalse(report.passed)

    def test_ai_decision_brief_passes(self):
        report = evaluate_article(
            ai_article(),
            domain="ai",
            min_words=300,
            max_words=1500,
            source_urls=[SOURCE],
        )
        self.assertTrue(report.passed, report.errors)

    def test_duplicate_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "existing.md").write_text(learning_article(), encoding="utf-8")
            report = evaluate_article(
                learning_article(),
                domain="learning",
                min_words=300,
                max_words=1500,
                source_urls=[SOURCE],
                existing_dir=directory,
            )
        self.assertFalse(report.passed)
        self.assertTrue(any("too similar" in error for error in report.errors))

    def test_repeated_paragraph_filler_is_blocked(self):
        repeated = (
            "This generic paragraph repeats the same claim without adding new evidence, "
            "reasoning, examples, or a different reader decision."
        )
        report = evaluate_article(
            learning_article(f"\n\n## Extra section\n\n{repeated}\n\n{repeated}\n\n{repeated}"),
            domain="learning",
            min_words=300,
            max_words=1500,
            source_urls=[SOURCE],
        )
        self.assertFalse(report.passed)
        self.assertIn("repeated paragraph filler", report.errors)

    def test_body_h1_is_blocked(self):
        report = evaluate_article(
            learning_article("\n\n# A second page title"),
            domain="learning",
            min_words=300,
            max_words=1500,
            source_urls=[SOURCE],
        )
        self.assertFalse(report.passed)
        self.assertIn("body must not contain an H1 heading", report.errors)

    def test_duplicate_sources_sections_are_blocked(self):
        report = evaluate_article(
            learning_article(f"\n\n## Sources\n\n- {SOURCE}"),
            domain="learning",
            min_words=300,
            max_words=1500,
            source_urls=[SOURCE],
        )
        self.assertFalse(report.passed)
        self.assertIn("article must contain exactly one Sources section", report.errors)

    def test_placeholder_source_is_blocked(self):
        placeholder = "https://example.com/official"
        report = evaluate_article(
            learning_article().replace(SOURCE, placeholder),
            domain="learning",
            min_words=300,
            max_words=1500,
            source_urls=[placeholder],
        )
        self.assertFalse(report.passed)
        self.assertIn("sources must be HTTPS links to real publishers", report.errors)


if __name__ == "__main__":
    unittest.main()
