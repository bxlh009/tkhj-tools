import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "_site"
DOMAIN = "tkhjtools.top"


def public_path_for(output_file: Path) -> str:
    relative = output_file.relative_to(SITE).as_posix()
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return "/" + relative.removesuffix("index.html")
    return "/" + relative.removesuffix(".html")


class CanonicalUrlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, "site/build.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_public_url_signals_use_cloudflare_redirect_targets(self):
        sitemap = (SITE / "sitemap.xml").read_text("utf-8")
        sitemap_urls = re.findall(r"<loc>(.*?)</loc>", sitemap)
        self.assertTrue(sitemap_urls)
        self.assertFalse(
            [url for url in sitemap_urls if urlparse(url).path.endswith(".html")],
            "Sitemap must list the extensionless URLs that Cloudflare serves.",
        )
        for url in sitemap_urls:
            path = urlparse(url).path
            target = (
                SITE / path.lstrip("/") / "index.html"
                if path.endswith("/")
                else SITE / f"{path.lstrip('/')}.html"
            )
            self.assertTrue(target.exists(), f"{url}: no generated page")

        for output_file in SITE.rglob("*.html"):
            html = output_file.read_text("utf-8")
            expected = f"https://{DOMAIN}{public_path_for(output_file)}"
            canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html)
            self.assertIsNotNone(canonical, f"{output_file}: missing canonical")
            self.assertEqual(expected, canonical.group(1), f"{output_file}: canonical")
            og_url = re.search(r'<meta property="og:url" content="([^"]+)"', html)
            self.assertIsNotNone(og_url, f"{output_file}: missing og:url")
            self.assertEqual(expected, og_url.group(1), f"{output_file}: og:url")

            internal_html_links = re.findall(r'href="(/[^"#?]*\.html)(?:[#?][^"]*)?"', html)
            self.assertFalse(
                internal_html_links,
                f"{output_file}: internal links must use extensionless URLs",
            )
            internal_html_signals = re.findall(
                rf'https://{re.escape(DOMAIN)}/[^"< ]*\.html', html
            )
            self.assertFalse(
                internal_html_signals,
                f"{output_file}: metadata must use extensionless URLs",
            )

        search_rows = json.loads((SITE / "search_index.json").read_text("utf-8"))
        search_urls = [
            url
            for row in search_rows
            for url in (row["url"], row.get("zh_url", ""))
            if url
        ]
        self.assertFalse(
            [url for url in search_urls if url.endswith(".html")],
            "Search results must link to canonical extensionless URLs.",
        )


if __name__ == "__main__":
    unittest.main()
