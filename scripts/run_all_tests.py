# -*- coding: utf-8 -*-
"""
一键全量测试脚本
运行: python scripts/run_all_tests.py
退出码: 0 = 全通过, 1 = 有失败
"""
import json
import os
import pathlib
import re
import sys
import tempfile
from collections import Counter as _Ctr

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
VARS = ROOT / "vars"
OUTPUT = ROOT / "output"

sys.path.insert(0, str(SCRIPTS))

import check_similarity
import content_quality
import generate


class _Result:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []


_RESULT = _Result()


def check(desc, ok, detail=""):
    if ok:
        _RESULT.passed += 1
        print(f"  [PASS] {desc}")
    else:
        _RESULT.failed += 1
        _RESULT.errors.append((desc, detail))
        print(f"  [FAIL] {desc}  <- {detail}" if detail else f"  [FAIL] {desc}")


# 1. API Key 校验
def test_api_key_validation():
    print("\n=== 1. API Key 校验 ===")
    cfg = json.loads((SCRIPTS / "config.json").read_text(encoding="utf-8"))
    key_name = cfg["api"]["api_key_env"]
    orig_key = os.environ.get(key_name)

    os.environ[key_name] = "sk-test-valid"
    try:
        k = generate.get_api_key()
        check("有效 key 返回正确", k == "sk-test-valid", f"got {k}")
    except RuntimeError:
        check("有效 key 返回正确", False, "不应报错")

    os.environ[key_name] = ""
    try:
        generate.get_api_key()
        check("空 key 应拒绝", False, "没有报错")
    except RuntimeError:
        check("空 key 应拒绝", True)

    os.environ[key_name] = "   "
    try:
        generate.get_api_key()
        check("纯空格 key 应拒绝", False, "没有报错")
    except RuntimeError:
        check("纯空格 key 应拒绝", True)

    if orig_key is not None:
        os.environ[key_name] = orig_key
    elif key_name in os.environ:
        del os.environ[key_name]


# 2. Token 计费控制
def test_token_control():
    print("\n=== 2. Token 计费控制 ===")
    cfg = json.loads((SCRIPTS / "config.json").read_text(encoding="utf-8"))
    api = cfg["api"]

    check("max_tokens > 0", api["max_tokens"] > 0, f"got {api['max_tokens']}")
    check("max_tokens 合理（<= 32768）", api["max_tokens"] <= 32768, f"got {api['max_tokens']}")
    check("temperature 在 [0,1]", 0 <= api["temperature"] <= 1, f"got {api['temperature']}")
    check("model 非空", bool(api.get("model")), str(api.get("model")))
    check("base_url 是 HTTPS", api["base_url"].startswith("https://"), api["base_url"])


# 3. 内容质量门禁
def test_scoring():
    print("\n=== 3. 内容质量门禁 ===")
    source = "https://example.com/source"
    paragraph = (
        "This section explains a concrete decision and the evidence a reader "
        "should use before taking the next reversible step.\n\n"
    )
    good = (
        "## Method\n\n" + paragraph * 8
        + "## Original practice example one\n\nScenario and answer with reasoning.\n\n"
        + paragraph * 6
        + "## Original practice example two\n\nTry this scenario and check your answer.\n\n"
        + paragraph * 6
        + f"## Sources\n\n- {source}\n"
    )
    report = content_quality.evaluate_article(
        good,
        domain="learning",
        min_words=200,
        max_words=1200,
        source_urls=[source],
    )
    check("合格学习稿通过", report.passed, str(report.errors))

    fake = good + "\nI have taught 300+ students and guarantee results."
    report = content_quality.evaluate_article(
        fake,
        domain="learning",
        min_words=200,
        max_words=1200,
        source_urls=[source],
    )
    check("虚构权威和结果承诺被阻断", not report.passed, str(report.errors))


# 4. 元数据与来源组装
def test_contraction_injection():
    print("\n=== 4. 元数据与来源组装 ===")
    values = {"slug": "test-guide", "primary_keyword": "Test guide", "exam_name": "TOEFL"}
    source = "https://www.ets.org/toefl/test-takers/ibt/prepare.html"
    article = generate.build_article(
        "## One\n\nText.\n\n## Two\n\nText.\n\n## Three\n\nText.",
        article_type="exam",
        values=values,
        urls=[source],
    )
    check("生成 domain=learning", 'domain: "learning"' in article)
    check("来源写入正文", source in article)
    check("slug 写入 frontmatter", '"test-guide"' in article)


# 5. 相似度检测
def test_similarity():
    print("\n=== 5. 相似度检测 ===")

    a = "The quick brown fox jumps over the lazy dog. " * 20
    b = "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 20
    fa = _Ctr(check_similarity._ngrams(a, 3))
    fb = _Ctr(check_similarity._ngrams(b, 3))
    sim = max(check_similarity.jaccard(fa, fb), check_similarity.cosine(fa, fb))
    check(f"不同文章相似度低（{sim:.2f}）", sim < 0.3, f"got {sim}")

    sim = max(check_similarity.jaccard(fa, fa), check_similarity.cosine(fa, fa))
    check(f"完全相同相似度=1.0（{sim:.2f}）", sim == 1.0)

    fempty = _Ctr(check_similarity._ngrams("", 3))
    sim = check_similarity.jaccard(fempty, fempty)
    check("空字符串不 crash", sim == 0.0)

    cn = "这是一个测试文章，用于检测中文字符的相似度计算是否正确。" * 10
    fcn = _Ctr(check_similarity._ngrams(cn, 3))
    sim = check_similarity.jaccard(fcn, fcn)
    check(f"中文字符不 crash（{sim:.2f}）", sim == 1.0)


# 6. AI 叙事去重
def test_dedup():
    print("\n=== 6. AI 叙事去重 ===")
    import daily_ai_news as dan

    item1 = {"title": "OpenAI launches GPT-5", "link": "https://openai.com/gpt5"}
    item2 = {"title": "Anthropic releases Claude 4", "link": "https://anthropic.com/claude4"}
    check("不同故事指纹不同", dan._fingerprint(item1) != dan._fingerprint(item2))

    item3 = {"title": "OpenAI launches GPT-5", "link": "https://blog.openai.com/gpt5"}
    check("同标题不同链接指纹不同", dan._fingerprint(item1) != dan._fingerprint(item3))

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    tmp.write("{broken json")
    tmp.close()
    orig = dan.SEEN_DB
    dan.SEEN_DB = pathlib.Path(tmp.name)
    result = dan._load_seen()
    check("损坏 JSON 返回空 dict", result == {})
    dan.SEEN_DB = orig
    os.unlink(tmp.name)

    dan.SEEN_DB = pathlib.Path("/nonexistent/path/seen.json")
    result = dan._load_seen()
    check("不存在返回空 dict", result == {})
    dan.SEEN_DB = orig


# 7. 每日 AI 新闻管线
def test_daily_pipeline():
    print("\n=== 7. 每日 AI 新闻管线 ===")
    import daily_ai_news as dan

    check("days_since 正常日期", dan.days_since("2026-07-08") >= 0)
    check("days_since(None)=999", dan.days_since(None) == 999)

    future = "2099-12-31"
    result = dan.days_since(future)
    check(f"未来日期返回负数或 0（got {result}）", result <= 0)

    slug = dan._slugify("OpenAI launches GPT-5 with reasoning!")
    check("slugify 去标点", slug == "openai-launches-gpt-5-with-reasoning", f"got {slug}")
    check("slugify 小写", slug == slug.lower())

    slug = dan._slugify("")
    check("空标题 slugify 不 crash", isinstance(slug, str))


# 8. Site 构建
def test_site_build():
    print("\n=== 8. Site 构建 ===")
    import sys
    sys.path.insert(0, str(ROOT / "site"))
    import build

    static = ROOT / "site" / "static"
    check("logo.png 存在", (static / "logo.png").exists())
    check("favicon.png 存在", (static / "favicon.png").exists())

    try:
        from PIL import Image
        img = Image.open(static / "logo.png")
        check(f"logo.png 可打开 ({img.size})", img.size[0] > 0 and img.size[1] > 0)
    except ImportError:
        check("PIL 未安装，跳过图片验证", True)

    footer = build.footer()
    check("footer 包含 </footer>", footer.strip().endswith("</footer>"))
    check("footer 无乱码 </", "</ " not in footer, "发现损坏的 HTML")

    sample = '<a href="https://x.com?a=1&b=2">link</a>'
    escaped = build.esc(sample)
    check("esc 转义 < 和属性", "&lt;a href=" in escaped)
    check("esc 转义 &", "&amp;" in escaped)
    check("esc 转义 引号", "&quot;" in escaped)


class _TestCounter:
    pass


# main
def main():
    print("=" * 60)
    print("  Content Engine - 全量测试")
    print("=" * 60)

    tests = [
        test_api_key_validation,
        test_token_control,
        test_scoring,
        test_contraction_injection,
        test_similarity,
        test_dedup,
        test_daily_pipeline,
        test_site_build,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"  [ERROR] {t.__name__} 崩溃: {e}")
            _RESULT.failed += 1
            _RESULT.errors.append((t.__name__, str(e)))

    print("\n" + "=" * 60)
    print(f"  结果: {_RESULT.passed} 通过 / {_RESULT.failed} 失败")
    print("=" * 60)

    if _RESULT.errors:
        print("\n失败详情:")
        for desc, detail in _RESULT.errors:
            print(f"  - {desc}: {detail}")

    return 0 if _RESULT.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
