import json
import unittest
from pathlib import Path
from unittest.mock import patch

import publish_article
import generate
from content_quality import QualityReport


SOURCE = "https://www.ets.org/toefl/test-takers/ibt/prepare.html"


def draft_text(
    *,
    title: str = "Approved Guide",
    slug: str = "approved-guide",
    domain: str = "learning",
    pathway_id: str = "",
    source: str = SOURCE,
    extra_sources: tuple[str, ...] = (),
) -> str:
    pathway = f'pathway_id: "{pathway_id}"\n' if pathway_id else ""
    sources = "\n".join(f"- {url}" for url in (source, *extra_sources))
    return f'''---
title: "{title}"
slug: "{slug}"
domain: "{domain}"
{pathway}date: "2026-08-03"
description: "A complete description for one focused reader task."
---

## Method

Candidate body with an explicit reader decision.

## Practice

Original practice and explained reasoning.

## Sources

{sources}
'''


class PublishArticleTests(unittest.TestCase):
    def test_generator_carries_the_reader_pathway_into_the_draft(self):
        article = generate.build_article(
            "## Method\n\nBody.\n\n## Limits\n\nLimits.\n\n## Decision\n\nDecision.",
            article_type="exam",
            values={
                "slug": "pathway-guide",
                "title": "Pathway Guide",
                "exam_name": "TOEFL",
                "pathway_id": "learning-read",
            },
            urls=[SOURCE],
        )
        self.assertIn('pathway_id: "learning-read"', article)

    def test_publish_requires_explicit_editorial_approval_before_any_write(self):
        with patch.object(Path, "read_text") as read_text, patch.object(
            Path, "write_text"
        ) as write_text:
            with self.assertRaisesRegex(ValueError, "editorial approval"):
                publish_article.publish("candidate.md")
        read_text.assert_not_called()
        write_text.assert_not_called()

    def test_automatic_publish_requires_a_configured_reader_pathway(self):
        with patch.object(Path, "read_text", return_value=draft_text()), patch.object(
            Path, "write_text"
        ) as write_text:
            with self.assertRaisesRegex(ValueError, "reader pathway"):
                publish_article.publish(
                    "candidate.md", automatic_policy_approval=True
                )
        write_text.assert_not_called()

    def test_automatic_publish_rejects_secondary_only_sources(self):
        draft = draft_text(
            domain="ai",
            pathway_id="ai-verify",
            source="https://www.the-decoder.com/secondary-recap",
        )
        with patch.object(Path, "read_text", return_value=draft), patch.object(
            Path, "write_text"
        ) as write_text:
            with self.assertRaisesRegex(ValueError, "primary-source domain"):
                publish_article.publish(
                    "candidate.md", automatic_policy_approval=True
                )
        write_text.assert_not_called()

    def test_automatic_ai_publish_requires_two_independent_primary_domains(self):
        draft = draft_text(
            domain="ai",
            pathway_id="ai-verify",
            source="https://airc.nist.gov/",
        )
        with patch.object(Path, "read_text", return_value=draft), patch.object(
            Path, "write_text"
        ) as write_text:
            with self.assertRaisesRegex(ValueError, "two independent"):
                publish_article.publish(
                    "candidate.md", automatic_policy_approval=True
                )
        write_text.assert_not_called()

    def test_automatic_publish_rechecks_the_quality_gate_before_writing(self):
        draft = draft_text(pathway_id="learning-read")
        failed = QualityReport(False, ("too short",), (), {"word_count": 42})
        curation = {
            "pathways": [{"id": "learning-read", "track": "learning", "slugs": []}],
            "featured": [], "overrides": {}, "redirects": {}, "excluded": {},
        }
        with patch.object(
            Path, "read_text", side_effect=[draft, json.dumps(curation)]
        ), patch.object(
            publish_article, "evaluate_article", return_value=failed
        ), patch.object(Path, "write_text") as write_text:
            with self.assertRaisesRegex(ValueError, "quality gate"):
                publish_article.publish(
                    "candidate.md", automatic_policy_approval=True
                )
        write_text.assert_not_called()

    def test_automatic_publish_rejects_a_pathway_from_the_wrong_track(self):
        curation = {
            "pathways": [{"id": "ai-verify", "track": "ai", "slugs": []}],
            "featured": [],
            "overrides": {},
            "redirects": {},
            "excluded": {},
        }
        draft = draft_text(pathway_id="ai-verify")
        with patch.object(
            Path, "read_text", side_effect=[draft, json.dumps(curation)]
        ), patch.object(Path, "write_text") as write_text:
            with self.assertRaisesRegex(ValueError, "does not belong to learning"):
                publish_article.publish(
                    "candidate.md", automatic_policy_approval=True
                )
        write_text.assert_not_called()

    def test_automatic_publish_adds_the_guide_to_its_reader_pathway(self):
        curation = {
            "pathways": [
                {"id": "learning-read", "track": "learning", "slugs": []}
            ],
            "featured": [],
            "overrides": {},
            "redirects": {},
            "excluded": {},
        }
        draft = draft_text(pathway_id="learning-read")
        passed = QualityReport(True, (), (), {"word_count": 1600})
        with patch.object(
            Path,
            "read_text",
            side_effect=[draft, json.dumps(curation), "[]"],
        ), patch.object(Path, "exists", return_value=True), patch.object(
            Path, "mkdir"
        ), patch.object(Path, "write_text") as write_text, patch.object(
            publish_article, "evaluate_article", return_value=passed
        ):
            publish_article.publish(
                "candidate.md", automatic_policy_approval=True
            )

        manifest = json.loads(write_text.call_args_list[-2].args[0])
        updated_curation = json.loads(write_text.call_args_list[-1].args[0])
        self.assertEqual(manifest[0]["editorial_status"], "automatic_policy")
        self.assertEqual(manifest[0]["pathway_id"], "learning-read")
        self.assertEqual(manifest[0]["quality_metrics"]["word_count"], 1600)
        self.assertIn("quality_fingerprint", manifest[0])
        self.assertEqual(
            updated_curation["pathways"][0]["slugs"], ["approved-guide"]
        )

    def test_approved_publish_rejects_unsafe_slug(self):
        with patch.object(Path, "read_text", return_value=draft_text(slug="Bad Slug")), patch.object(
            Path, "write_text"
        ) as write_text:
            with self.assertRaisesRegex(ValueError, "safe lowercase slug"):
                publish_article.publish("candidate.md", editorial_approval=True)
        write_text.assert_not_called()

    def test_approved_publish_rejects_duplicate_public_title(self):
        existing = {
            "slug": "existing-guide",
            "title": "Existing Guide",
            "track": "learning",
            "published": "2026-08-02",
        }
        with patch.object(
            Path,
            "read_text",
            side_effect=[draft_text(title="existing guide!", slug="new-slug"), json.dumps([existing])],
        ), patch.object(Path, "exists", return_value=True), patch.object(
            Path, "mkdir"
        ), patch.object(Path, "write_text") as write_text:
            with self.assertRaisesRegex(ValueError, "duplicate public title"):
                publish_article.publish("candidate.md", editorial_approval=True)
        write_text.assert_not_called()

    def test_approved_publish_records_editorial_status_and_named_sources(self):
        with patch.object(
            Path, "read_text", side_effect=[draft_text(), "[]"]
        ), patch.object(Path, "exists", return_value=True), patch.object(
            Path, "mkdir"
        ), patch.object(Path, "write_text") as write_text:
            result = publish_article.publish("candidate.md", editorial_approval=True)

        manifest_json = write_text.call_args_list[-1].args[0]
        item = json.loads(manifest_json)[0]
        self.assertEqual(result, publish_article.CONTENT_DIR / "approved-guide.md")
        self.assertEqual(item["editorial_status"], "approved")
        self.assertEqual(item["sources"][0][0], "ets.org")
        self.assertEqual(
            item["description"], "A complete description for one focused reader task."
        )


if __name__ == "__main__":
    unittest.main()
