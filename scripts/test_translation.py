"""Unit tests for bilingual article sidecars."""

from __future__ import annotations

import unittest

from translate_article import (
    heading_levels,
    parse_response,
    sidecar,
    urls,
    validate_translation,
)


SOURCE = """## Method

Use the [official guide](https://example.com/guide) before deciding.

### Check

1. Read the evidence.
2. Record the result.

## Sources

- https://example.com/guide
"""

TRANSLATED = """## 方法

做决定前，请先阅读[官方指南](https://example.com/guide)。这是一个用于测试的完整中文段落，
它保留原文含义、结构与链接，不添加新的事实主张。读者应根据证据记录结果，并明确仍需核实的部分。

### 检查

1. 阅读证据并标记关键条件。
2. 记录结果以及尚未解决的问题。

## 来源

- https://example.com/guide
"""


class TranslationTests(unittest.TestCase):
    def test_parse_tagged_response(self) -> None:
        title, description, body = parse_response(
            "<translated-title>中文标题</translated-title>"
            "<translated-description>中文摘要说明</translated-description>"
            f"<translated-body>{TRANSLATED}</translated-body>"
        )
        self.assertEqual(title, "中文标题")
        self.assertEqual(description, "中文摘要说明")
        self.assertIn("## 方法", body)

    def test_structure_and_urls_are_measured(self) -> None:
        self.assertEqual(heading_levels(SOURCE), [2, 3, 2])
        self.assertEqual(urls(SOURCE), urls(TRANSLATED))

    def test_valid_translation_passes(self) -> None:
        self.assertEqual(
            validate_translation(SOURCE, "中文测试标题", "这是中文摘要说明", TRANSLATED),
            [],
        )

    def test_missing_url_is_rejected(self) -> None:
        failures = validate_translation(
            SOURCE,
            "中文测试标题",
            "这是中文摘要说明",
            TRANSLATED.replace("https://example.com/guide", "", 1),
        )
        self.assertIn("source URLs changed or were omitted", failures)

    def test_sidecar_contains_metadata_and_body(self) -> None:
        result = sidecar("中文标题", "中文摘要", "example-slug", TRANSLATED)
        self.assertIn('source_slug: "example-slug"', result)
        self.assertTrue(result.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
