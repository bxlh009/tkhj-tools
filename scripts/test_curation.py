"""Behavior tests for the public editorial selection."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "site"))

import build


class CurationTests(unittest.TestCase):
    def test_every_catalog_entry_is_intentionally_published_or_excluded(self) -> None:
        manifest = json.loads((ROOT / "site" / "content" / "guides.json").read_text("utf-8"))
        curation = json.loads((ROOT / "site" / "content" / "curation.json").read_text("utf-8"))

        selected = build.select_curated_guides(manifest, curation)
        selected_slugs = [item["slug"] for item in selected]
        excluded_slugs = set(curation["excluded"])
        catalog_slugs = {item["slug"] for item in manifest}

        self.assertGreaterEqual(len(selected_slugs), 39)
        self.assertEqual(set(selected_slugs) | excluded_slugs, catalog_slugs)
        self.assertFalse(set(selected_slugs) & excluded_slugs)

        normalized_titles = [
            re.sub(r"[^a-z0-9]+", " ", item["title"].lower()).strip()
            for item in selected
        ]
        self.assertEqual(len(normalized_titles), len(set(normalized_titles)))

    def test_thin_search_results_page_is_not_indexable_or_in_sitemap(self) -> None:
        self.assertIn('<meta name="robots" content="noindex,follow">', build.search_page())
        self.assertNotIn("https://tkhjtools.top/search</loc>", build.sitemap([]))

    def test_markdown_renderer_preserves_code_rules_and_unique_anchors(self) -> None:
        rendered, headings = build.markdown_to_html(
            "## Repeat\n\n## Repeat\n\n```python\nprint('safe')\n```\n\n---"
        )
        self.assertEqual([anchor for _, _, anchor in headings], ["repeat", "repeat-2"])
        self.assertIn('<pre><code class="language-python">', rendered)
        self.assertIn("print(&#x27;safe&#x27;)", rendered)
        self.assertIn("<hr>", rendered)

    def test_body_sources_are_removed_before_structured_source_notes(self) -> None:
        markdown = "## Method\n\nUseful body.\n\n## Sources\n\n- https://example.com/source\n"
        self.assertEqual(build.strip_trailing_sources(markdown), "## Method\n\nUseful body.")

    def test_excluded_duplicates_redirect_to_selected_canonical_guides(self) -> None:
        curation = {"redirects": {"duplicate-guide": "canonical-guide"}}
        redirects = build.redirects_file(curation)
        self.assertIn("/guides/duplicate-guide /guides/canonical-guide 301", redirects)
        self.assertIn("/zh/guides/duplicate-guide /zh/guides/canonical-guide 301", redirects)

    def test_generic_source_labels_are_replaced_with_publisher_hosts(self) -> None:
        guide = {
            "sources": [["Source", "https://developers.google.com/search/docs/fundamentals"]],
            "updated": "2026-08-03",
        }
        rendered = build.sources(guide)
        self.assertIn(">developers.google.com</a>", rendered)
        self.assertNotIn(">Source</a>", rendered)

    def test_home_surfaces_editorially_featured_guides(self) -> None:
        guides = build.load_guides()
        rendered = build.home_page(guides)
        featured = [guide for guide in guides if guide["featured"]]
        self.assertEqual(len(featured), 6)
        for guide in featured:
            self.assertIn(f'/guides/{guide["slug"]}', rendered)

    def test_track_pages_explain_and_group_reader_pathways(self) -> None:
        guides = build.load_guides()
        rendered = build.track_page(guides, "learning")
        pathway_titles = list(
            dict.fromkeys(
                guide["pathway_title"] for guide in guides if guide["track"] == "learning"
            )
        )
        self.assertGreaterEqual(len(pathway_titles), 3)
        for title in pathway_titles:
            self.assertIn(f"<h2>{title}</h2>", rendered)

    def test_related_guides_prefer_the_same_reader_pathway(self) -> None:
        guides = build.load_guides()
        guide = next(item for item in guides if item["slug"] == "ielts-general-reading-time-plan")
        rendered = build.article_page(guide, guides)
        self.assertIn('/guides/toefl-reading-time-management', rendered)

    def test_chinese_navigation_stays_on_chinese_routes(self) -> None:
        navigation = build.nav(language="zh")
        footer = build.footer("zh")
        self.assertIn('action="/zh/search"', navigation)
        self.assertIn('data-i18n="nav-home">首页</a>', navigation)
        self.assertIn('placeholder="搜索"', navigation)
        self.assertIn('href="/zh/privacy"', footer)
        self.assertIn("以可靠来源为基础的学习与 AI 指南", footer)

    def test_chinese_search_page_is_server_rendered_and_noindex(self) -> None:
        rendered = build.search_page("zh")
        self.assertIn('<html lang="zh-CN"', rendered)
        self.assertIn('<h1 data-i18n="search-title">搜索文章库</h1>', rendered)
        self.assertIn('<meta name="robots" content="noindex,follow">', rendered)

    def test_chinese_privacy_page_is_server_rendered(self) -> None:
        rendered = build.privacy_page("zh")
        self.assertIn('<html lang="zh-CN"', rendered)
        self.assertIn("<h1>隐私政策</h1>", rendered)
        self.assertIn('href="/zh/contact"', rendered)

    def test_chinese_home_has_complete_server_rendered_method_and_trust_copy(self) -> None:
        rendered = build.home_page(build.load_guides(), "zh")
        self.assertIn("找到控制判断的短语、规则或评分描述。", rendered)
        self.assertIn("编辑精选", rendered)
        self.assertNotIn("Automation creates drafts", rendered)

    def test_about_copy_describes_controlled_automation_without_a_daily_quota(self) -> None:
        english = build.about_page()
        chinese = build.about_page("zh")
        self.assertIn("at most two track slots per week", english)
        self.assertIn("skips when no candidate qualifies", english)
        self.assertIn("每周最多评估两个栏目位", chinese)
        self.assertIn("无合格主题就跳过", chinese)

    def test_public_card_descriptions_end_as_complete_sentences(self) -> None:
        for guide in build.load_guides():
            self.assertNotRegex(guide["description"], r"(?:…|\.\.\.)$")
            self.assertRegex(guide["description"], r"[.!?]$")


if __name__ == "__main__":
    unittest.main()
