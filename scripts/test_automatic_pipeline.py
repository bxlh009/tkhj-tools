import unittest
from pathlib import Path
from unittest.mock import patch

import daily_generate
import daily_ai_news


class AutomaticPipelineTests(unittest.TestCase):
    def test_learning_topics_are_assigned_only_to_known_reader_pathways(self):
        cases = {
            "toefl-reading-question-types": "learning-diagnose",
            "toefl-reading-inference-strategy": "learning-read",
            "toefl-listening-note-taking": "learning-listen",
            "toefl-speaking-templates": "learning-produce",
            "toefl-writing-integrated": "learning-produce",
            "toefl-reading-time-management": "learning-plan",
        }
        for slug, expected in cases.items():
            self.assertEqual(daily_generate.infer_learning_pathway(slug), expected)
        self.assertIsNone(daily_generate.infer_learning_pathway("unclassified-topic"))

    def test_exhausted_learning_topics_are_not_reused_with_numeric_suffixes(self):
        topic = Path("toefl-reading-inference-strategy.json")
        with patch.object(daily_generate, "EXAM_VARS", [topic]), patch.object(
            daily_generate, "SEEN_VARS"
        ) as seen, patch.object(daily_generate, "OUT_EXAM") as output:
            seen.exists.return_value = False
            output.glob.return_value = [Path("toefl-reading-inference-strategy.md")]
            self.assertIsNone(daily_generate.pick_exam_topic())

    def test_automatic_ai_topics_have_a_pathway_and_two_official_sources(self):
        topics = daily_ai_news.automatic_evergreen_topics()
        self.assertTrue(topics)
        for topic in topics:
            self.assertRegex(topic["pathway_id"], r"^ai-")
            self.assertEqual(len(topic["links"]), 2)


if __name__ == "__main__":
    unittest.main()
