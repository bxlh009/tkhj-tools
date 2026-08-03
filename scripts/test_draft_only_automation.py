import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class ControlledAutomationTests(unittest.TestCase):
    def test_daily_workflow_uses_two_controlled_slots_and_full_verification(self):
        workflow = (ROOT / ".github" / "workflows" / "daily.yml").read_text("utf-8")
        self.assertIn("schedule:", workflow)
        self.assertEqual(len(re.findall(r"- cron:", workflow)), 2)
        self.assertIn("--auto-publish", workflow)
        self.assertIn("translate_article.py --all", workflow)
        self.assertIn("site/build.py", workflow)
        self.assertIn("audit_adsense_readiness.py", workflow)
        self.assertRegex(workflow, r"git add[^\n]*site/content")
        self.assertIn("concurrency:", workflow)

    def test_backfill_remains_manual_and_cannot_publish(self):
        workflow = (ROOT / ".github" / "workflows" / "backfill.yml").read_text("utf-8")
        backfill = (ROOT / "scripts" / "backfill_timeline.py").read_text("utf-8")
        self.assertNotIn("schedule:", workflow)
        self.assertNotRegex(backfill, r'["\']--(?:auto-)?publish["\']')
        self.assertNotRegex(workflow, r"git add[^\n]*site/content")


if __name__ == "__main__":
    unittest.main()
