import tempfile
import unittest
from pathlib import Path

from content_quality import evaluate_article


SOURCE = "https://example.com/official"


def learning_article(extra: str = "") -> str:
    paragraph = (
        "This paragraph explains one concrete learner decision with enough detail "
        "to make the method usable during the next practice session.\n\n"
    )
    return f"""---
title: "Evidence method"
---

## Diagnose the decision

{paragraph * 12}

## Original practice example one

Scenario: A reader must separate a stated fact from an inference. {paragraph * 8}
The answer follows from the quoted evidence, and the reasoning rejects outside knowledge.

## Original practice example two

Try this scenario with a different topic. {paragraph * 8}
Check your answer by underlining the phrase that controls the decision.

## Sources

- {SOURCE}

{extra}
"""


def ai_article(extra: str = "") -> str:
    paragraph = (
        "This section separates the source claim from our interpretation and gives "
        "the reader a concrete decision without claiming a hands-on product test.\n\n"
    )
    return f"""---
title: "AI decision brief"
---

## What changed

{paragraph * 12}

## What this means

{paragraph * 10}

## Limits and uncertainty

The exact performance impact was not disclosed, so readers should verify the claim. {paragraph * 8}

## When to use it

Who should adopt it now, and when to skip it, depends on a small reversible trial. {paragraph * 8}

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


if __name__ == "__main__":
    unittest.main()
