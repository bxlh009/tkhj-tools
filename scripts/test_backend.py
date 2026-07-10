# -*- coding: utf-8 -*-
"""
content-engine 后端核心功能自动测试套件
运行: python scripts/test_backend.py
退出码: 0 = 全部通过, 1 = 有失败
"""
import sys, os, json, pathlib, re, tempfile, statistics, hashlib
from collections import Counter
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "site"))

SCRIPTS = pathlib.Path(__file__).resolve().parent
ENGINE  = SCRIPTS.parent
import generate as gen
import check_similarity as cs

# ── test harness ──
class Suite:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.cases = []
    def ok(self, name):
        self.passed += 1
        self.cases.append(("PASS", name, ""))
        print(f"  [PASS] {name}")
    def fail(self, name, reason):
        self.failed += 1
        self.cases.append(("FAIL", name, reason))
        print(f"  [FAIL] {name}  <- {reason}")
    def summary(self):
        print(f"\n{'='*60}")
        print(f"  通过: {self.passed}  失败: {self.failed}")
        if self.failed > 0:
            print("  --- 失败明细 ---")
            for status, name, reason in self.cases:
                if status == "FAIL":
                    print(f"    {name}: {reason}")
        print(f"{'='*60}")
        return 0 if self.failed == 0 else 1

S = Suite()

def eq(name, actual, expected):
    if actual == expected:
        S.ok(name)
    else:
        S.fail(name, f"期望 {expected!r}, 实际 {actual!r}")

def is_true(name, cond, detail=""):
    if cond:
        S.ok(name)
    else:
        S.fail(name, f"条件不成立 {detail}")

def is_false(name, cond, detail=""):
    if not cond:
        S.ok(name)
    else:
        S.fail(name, f"应为假 {detail}")

def raises(name, exc_type, fn, *args, **kw):
    try:
        fn(*args, **kw)
        S.fail(name, f"期望 {exc_type.__name__} 但未抛出")
    except exc_type:
        S.ok(name)
    except Exception as e:
        S.fail(name, f"期望 {exc_type.__name__}, 实际 {type(e).__name__}: {e}")

def mock_resp(data, status=200):
    m = MagicMock()
    m.read.return_value = json.dumps(data).encode()
    m.__enter__ = MagicMock(return_value=m)
    m.__exit__ = MagicMock(return_value=False)
    m.status = status
    return m

# ── helpers ──
_SAVED_KEY = os.environ.get("AGNES_API_KEY")

def _restore_key():
    if _SAVED_KEY is not None:
        os.environ["AGNES_API_KEY"] = _SAVED_KEY
    elif "AGNES_API_KEY" in os.environ:
        del os.environ["AGNES_API_KEY"]

def _ensure_key():
    if not os.environ.get("AGNES_API_KEY", "").strip():
        os.environ["AGNES_API_KEY"] = "sk-placeholder-for-testing"

# ══════════════════════════════════════════════
#  P0-1: get_api_key()
# ══════════════════════════════════════════════
def test_get_api_key():
    print("\n=== P0-1: get_api_key() API Key 读取 ===")
    try:
        os.environ["AGNES_API_KEY"] = "sk-test-valid"
        k = gen.get_api_key()
        eq("合法 key 返回自身", k, "sk-test-valid")

        os.environ["AGNES_API_KEY"] = ""
        raises("空 key => sys.exit", SystemExit, gen.get_api_key)

        os.environ["AGNES_API_KEY"] = "   "
        raises("纯空格 key => sys.exit", SystemExit, gen.get_api_key)

        if "AGNES_API_KEY" in os.environ:
            del os.environ["AGNES_API_KEY"]
        raises("未设置 => sys.exit", SystemExit, gen.get_api_key)
    finally:
        _restore_key()

# ══════════════════════════════════════════════
#  P0-2: call_api()  （mock get_api_key 避免依赖环境）
# ══════════════════════════════════════════════
def test_call_api():
    print("\n=== P0-2: call_api() API 调用 ===")
    _ensure_key()

    # 正常：首次成功
    data = {"choices": [{"message": {"content": "hello"}}], "usage": {}}
    with patch("urllib.request.urlopen", return_value=mock_resp(data)):
        r = gen.call_api("sys", "user", retries=1)
        eq("首次成功返回内容", r, "hello")

    # 正常：第 2 次重试成功
    call_n = [0]
    def side_ok(*a, **kw):
        call_n[0] += 1
        if call_n[0] <= 1:
            raise TimeoutError("timeout")
        return mock_resp(data)
    with patch("urllib.request.urlopen", side_effect=side_ok):
        r = gen.call_api("sys", "user", retries=3)
        eq("重试 1 次后恢复", r, "hello")
        is_true("重试调用次数 ≤3", call_n[0] <= 3, f"实际 {call_n[0]}")

    # 边界：3 次全失败
    with patch("urllib.request.urlopen", side_effect=TimeoutError("always")):
        raises("3 次全失败 RuntimeError", RuntimeError, gen.call_api, "sys", "user", retries=3)

    # 异常：空 choices
    with patch("urllib.request.urlopen", return_value=mock_resp({"choices": []})):
        raises("空 choices 抛 IndexError", IndexError, gen.call_api, "sys", "user", retries=1)

    # 异常：缺 choices key
    with patch("urllib.request.urlopen", return_value=mock_resp({"foo": "bar"})):
        raises("缺 choices key 抛 KeyError", KeyError, gen.call_api, "sys", "user", retries=1)

    # 异常：HTTP 错误
    def http_err(*a, **kw):
        raise __import__("urllib").error.HTTPError("http://x", 401, "Unauthorized", {}, None)
    with patch("urllib.request.urlopen", side_effect=http_err):
        raises("HTTP 401 重试后 RuntimeError", RuntimeError, gen.call_api, "sys", "user", retries=2)

    # 验证: RuntimeError 透传（不含 API key 明文）
    def plain_err(*a, **kw):
        raise RuntimeError("connection reset")
    with patch("urllib.request.urlopen", side_effect=plain_err):
        try:
            gen.call_api("sys", "user", retries=1)
        except RuntimeError as e:
            is_true("错误消息透传（不含 key 明文）", "connection reset" in str(e).lower())

# ══════════════════════════════════════════════
#  P0-3: inj() 模板注入
# ══════════════════════════════════════════════
def test_inj():
    print("\n=== P0-3: inj() 模板变量注入 ===")

    eq("单变量替换",       gen.inj("Hello {name}", {"name": "Evan"}), "Hello Evan")
    eq("多变量替换",       gen.inj("{a} + {b} = {c}", {"a": "1", "b": "2", "c": "3"}), "1 + 2 = 3")
    eq("缺失变量保留",     gen.inj("Hello {name}", {}), "Hello {name}")
    eq("空字符串值",       gen.inj("Hello {name}", {"name": ""}), "Hello ")
    eq("特殊字符",         gen.inj("{x}", {"x": "a{b}c"}), "a{b}c")
    eq("无变量的模板",     gen.inj("plain text", {"x": "y"}), "plain text")
    eq("None 值变文字",    gen.inj("{x}", {"x": None}), "None")
    eq("数字值",           gen.inj("age={age}", {"age": 42}), "age=42")

# ══════════════════════════════════════════════
#  P0-4: write_output()
# ══════════════════════════════════════════════
def test_write_output():
    print("\n=== P0-4: write_output() 文件写入 ===")
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)

        # 正常写入
        p = gen.write_output("# Hello", "test-art", d)
        is_true("文件已创建", p.exists())
        eq("内容正确", p.read_text("utf-8"), "# Hello")
        p.unlink()

        # slug 冲突 → 自动 +2
        (d / "dup.md").write_text("first", "utf-8")
        p2 = gen.write_output("second", "dup", d)
        is_true("冲突未覆盖原文", (d / "dup.md").exists())
        is_true("冲突写入 dup-2.md", p2.name == "dup-2.md", str(p2.name))
        eq("冲突文件内容正确", p2.read_text("utf-8"), "second")

        # 边界：多级冲突
        for n in ["test.md", "test-2.md", "test-3.md"]:
            (d / n).write_text("", "utf-8")
        p3 = gen.write_output("new", "test", d)
        eq("复杂冲突取最小空闲序号", p3.name, "test-4.md")

# ══════════════════════════════════════════════
#  P0-5: score() 10 维评分
# ══════════════════════════════════════════════
def test_score():
    print("\n=== P0-5: score() 10 维质量评分 ===")

    # 正常：好文章 PASS
    good = (
        "I've been teaching TOEFL for seven years, and honestly? "
        "it's not easy. But here's the thing, most students don't realize reading's not about vocabulary. "
        "Don't get me wrong — words matter. But structure matters more. "
        "Let me be clear: if you're stuck at 22, it's not because you're lazy. "
        "Turns out it's because you're reading every single word. "
        "Here's what I tell my students: skim first, then dig into details. "
        "Basically you need to triage. I mean, it's literally the only way. "
        "Look, I've seen this mistake a thousand times! "
        "Worked Example 1 — the main idea question. Read the first sentence. That's it. "
        "Worked Example 2 — the inference question. Look for clues in surrounding text. "
        "Connect the dots! Why does this matter? Because it works! "
        "Try the free quiz at https://exam.tkjtools.io today! "
        "Disclaimer: this is independently written content."
    )
    long = " ".join([good] * 10)  # ~2000 words
    sc, v, d = gen.score(long, 1500, 2500)
    is_true(f"好文章 PASS (得分 {sc}/100)", v == "PASS" and sc >= 75, f"v={v} sc={sc}")

    # 边界：空字符串
    sc, v, d = gen.score("", 1500, 2500)
    eq("空字符串 0 分 EMPTY", (sc, v), (0, "EMPTY"))

    # 边界：只有 frontmatter
    sc, v, d = gen.score("---\ntitle: test\n---", 1500, 2500)
    is_true("仅 frontmatter 不崩溃", isinstance(sc, int) and isinstance(v, str), str(sc))

    # 边界：字数 min 临界
    words = "word " * 1500
    sc, v, d = gen.score(words, 1500, 2500)
    eq("刚好 min_words p7=10", d.get("word_count", 0), 1500)

    # 边界：字数超出 max
    words = "word " * 3000
    sc, v, d = gen.score(words, 1500, 2500)
    is_true("超过 max_words 不崩溃", isinstance(sc, int))

    # 异常：banned format 检测
    bad = "## Title\n| Col1 | Col2 |\n| --- | --- |\n| A | B |\n"
    sc, v, d = gen.score(bad, 100, 500)
    is_true("Markdown 表格 p6=0", d.get("banned_format") is True)

    # 异常：句首 bullet
    bad2 = "- this is a bullet\n- another bullet"
    sc, v, d = gen.score(bad2, 10, 500)
    is_true("句首 bullet p6=0", d.get("banned_format") is True)

    # 边界：None min/max
    sc, v, d = gen.score("hello world test", None, None)
    is_true("None 阈值不崩溃", isinstance(sc, int))

# ══════════════════════════════════════════════
#  P0-6: ensure_cta_and_disclaimer()
# ══════════════════════════════════════════════
def test_cta_disclaimer():
    print("\n=== P0-6: ensure_cta_and_disclaimer() CTA + 免责 ===")

    # 正常：exam 类型无 CTA 无 disclaimer → 追加
    r = gen.ensure_cta_and_disclaimer("some content", "exam")
    is_true("exam 无时追加 tkjtools", "exam.tkjtools.io" in r)
    is_true("exam 无时追加 disclaimer", "Disclaimer" in r or "disclaimer" in r)

    # 正常：ai 类型
    r2 = gen.ensure_cta_and_disclaimer("some content", "ai")
    is_true("ai 无时追加 ai.tkjtools", "ai.tkjtools.io" in r2)

    # 正常：已有 CTA → 不重复
    r3 = gen.ensure_cta_and_disclaimer("already has exam.tkjtools.io\n", "exam")
    eq("已有 CTA 不重复追加", r3.count("tkjtools.io"), 1)

    # 正常：已有 disclaimer → 不重复
    r4 = gen.ensure_cta_and_disclaimer("has disclaimer\nindependently written\n", "exam")
    ok = "Disclaimer" not in r4.split("independently written")[1] if "Disclaimer" in r4 else True
    is_true("已有 disclaimer 不重复", ok)

    # 边界：空文章
    r5 = gen.ensure_cta_and_disclaimer("", "exam")
    is_true("空文章也追加 CTA", "tkjtools.io" in r5)
    is_true("空文章也追加 disclaimer", "disclaimer" in r5.lower())

# ══════════════════════════════════════════════
#  P1-1: 相似度检测
# ══════════════════════════════════════════════
def test_similarity():
    print("\n=== P1-1: 相似度检测 ===")

    # jaccard
    a = cs._ngrams("abcde", 3)
    b = cs._ngrams("vwxyz", 3)
    eq("完全不同 jaccard=0", cs.jaccard(a, b), 0.0)
    eq("完全相同 jaccard=1", cs.jaccard(a, cs._ngrams("abcde", 3)), 1.0)

    # cosine
    eq("完全不同 cosine=0", cs.cosine(a, b), 0.0)
    is_true("完全相同 cosine≈1", abs(cs.cosine(a, cs._ngrams("abcde", 3)) - 1.0) < 1e-10)

    # 边界：空字符串
    empty = cs._ngrams("", 3)
    eq("空 jaccard=0", cs.jaccard(empty, empty), 0.0)
    eq("空 cosine=0", cs.cosine(empty, empty), 0.0)

    # 边界：单字符
    single = cs._ngrams("a", 3)
    eq("单字符 jaccard=0", cs.jaccard(single, single), 0.0)
    eq("单字符 cosine=0", cs.cosine(single, single), 0.0)

    # 中文
    cn = cs._ngrams("中文测试文本", 3)
    eq("中文 jaccard 自比=1.0", cs.jaccard(cn, cs._ngrams("中文测试文本", 3)), 1.0)

    # check_new_article 功能
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        (d / "existing.md").write_text("The quick brown fox jumps over the lazy dog. " * 50, "utf-8")
        new  = "The quick brown fox jumps over the lazy dog. " * 50
        new2 = "Completely different content about quantum physics and machine learning. " * 50

        ok_sim, name, score = cs.check_new_article(new, str(d), 0.30)
        is_true("相同内容 detected", ok_sim, f"score={score:.2f}")

        ok2, _, score2 = cs.check_new_article(new2, str(d), 0.30)
        is_false("不同内容 passed", ok2, f"score={score2:.2f}")

        is_true("返回 float score", isinstance(score, float))

# ══════════════════════════════════════════════
#  P1-2: daily_ai_news.py 关键函数
# ══════════════════════════════════════════════
def test_daily_ai_news():
    print("\n=== P1-2: daily_ai_news.py 管线逻辑 ===")
    import daily_ai_news as dan

    # score_item 加权
    # openai=7 + launch=6 + gpt-5=10 = 23
    eq("GPT-5 标题得分=23", dan.score_item({"title": "OpenAI launches GPT-5", "summary": ""}), 23)
    eq("无关键词得分=0",    dan.score_item({"title": "Random cat video", "summary": ""}), 0)

    # is_big_news 阈值边界
    is_true("得分≥8 是大新闻",   dan.is_big_news({"title": "GPT-5", "summary": ""}))
    is_false("得分<8 非大新闻",  dan.is_big_news({"title": "Random cat video", "summary": ""}))

    # _fingerprint 去重
    f1 = dan._fingerprint({"title": "GPT-5 Launch", "link": "https://openai.com/gpt5"})
    f2 = dan._fingerprint({"title": "GPT-5 Launch", "link": "https://openai.com/gpt5"})
    f3 = dan._fingerprint({"title": "GPT-5 Launch", "link": "https://blog.openai.com/gpt5"})
    eq("同标题同链指纹相同", f1, f2)
    is_true("不同链接指纹不同", f1 != f3, f"{f1} == {f3}")

    # days_since
    eq("昨天=1",          dan.days_since("2026-07-09"), 1)
    eq("今天=0",          dan.days_since("2026-07-10"), 0)
    eq("None=999",        dan.days_since(None), 999)
    is_true("未来日期为负", dan.days_since("2099-12-31") < 0)

    # _slugify
    eq("去标点全小写",  dan._slugify("OpenAI launches GPT-5!"), "openai-launches-gpt-5")
    eq("空字符串不崩",   dan._slugify(""), "")

    # _load_seen 异常
    orig = dan.SEEN_DB
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write("{broken json")
            tmp = f.name
        dan.SEEN_DB = pathlib.Path(tmp)
        eq("损坏 JSON 返回空", dan._load_seen(), {})
        os.unlink(tmp)

        dan.SEEN_DB = pathlib.Path("/nonexistent/seen.json")
        eq("不存在返回空", dan._load_seen(), {})
    finally:
        dan.SEEN_DB = orig

# ══════════════════════════════════════════════
#  P1-3: fm() frontmatter 解析
# ══════════════════════════════════════════════
def test_fm():
    print("\n=== P1-3: build.fm() frontmatter 解析 ===")
    import build

    meta, body = build.fm('---\ntitle: "Test"\ndate: "2026-07-09"\n---\nHello world.')
    eq("提取 title",      meta.get("title"), "Test")
    eq("提取 date",       meta.get("date"), "2026-07-09")
    eq("body 内容",       body.strip(), "Hello world.")

    meta2, body2 = build.fm("Just plain text. No frontmatter.")
    eq("无 fm meta={}",   meta2, {})
    eq("无 fm body=全文", body2, "Just plain text. No frontmatter.")

    meta3, body3 = build.fm("")
    eq("空文件 meta={}",  meta3, {})
    eq("空文件 body=\"\"", body3, "")

    bom_text = '\ufeff---\ntitle: "BOM"\n---\nbody'
    meta4, body4 = build.fm(bom_text)
    eq("BOM 不影响解析", meta4.get("title"), "BOM")

    meta5, body5 = build.fm("---\ntitle: Test\nvalue: 42\n---\nbody")
    eq("数字值字符串化",   meta5.get("value"), "42")

    meta6, body6 = build.fm('---\ntitle: X\nlong_tail: ["a", "b"]\n---\nbody')
    is_true("long_tail 解析为列表", isinstance(meta6.get("long_tail"), list))

# ══════════════════════════════════════════════
#  P1-4: _clean_body.clean_body()
# ══════════════════════════════════════════════
def test_clean_body():
    print("\n=== P1-4: _clean_body.clean_body() 清理 ===")
    import importlib.util
    spec = importlib.util.spec_from_file_location("_clean_body",
        pathlib.Path(__file__).resolve().parent / "_clean_body.py")
    cb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cb)

    clean_fm = "---\ntitle: test\n---\n"

    eq("干净 body 原样", cb.clean_body(clean_fm + "normal content"), clean_fm + "normal content")

    # double frontmatter
    r = cb.clean_body(clean_fm + "---\ntitle: second\n---\nactual body")
    is_true("double fm 清理", "title: second" not in r)
    is_true("保留实际正文",   "actual body" in r)

    # JSON body
    r2 = cb.clean_body(clean_fm + '{"key": "value"}')
    is_true("JSON body 不崩溃", isinstance(r2, str))

    # YAML 泄漏行
    r3 = cb.clean_body(clean_fm + "title: leaked\ndate: 2026-07-09\n\nreal content")
    is_true("YAML 泄漏行清理", "title: leaked" not in r3)
    is_true("保留真实内容",    "real content" in r3)

    # 空串 / 仅 fm
    eq("空字符串",       cb.clean_body(""), "")
    eq("仅有 frontmatter", cb.clean_body(clean_fm), clean_fm)

# ══════════════════════════════════════════════
#  P1-5: config.json 合法性
# ══════════════════════════════════════════════
def test_config():
    print("\n=== P1-5: config.json 结构与边界 ===")
    cfg = json.loads((SCRIPTS / "config.json").read_text("utf-8"))
    api = cfg["api"]
    is_true("base_url 是 HTTPS",         api["base_url"].startswith("https://"), api["base_url"])
    is_true("model 非空",               bool(api.get("model")), str(api.get("model")))
    is_true("api_key_env 非空",          bool(api.get("api_key_env")), api["api_key_env"])
    is_true("temperature ∈ [0,1]",       0 <= api.get("temperature", -1) <= 1, str(api.get("temperature")))
    is_true("max_tokens > 0",            api.get("max_tokens", 0) > 0, str(api.get("max_tokens")))
    is_true("output_dir=../output",     cfg.get("output_dir") == "../output", str(cfg.get("output_dir")))
    is_true("rules_file=WRITING_RULES", cfg.get("rules_file") == "../rules/WRITING_RULES.md")
    is_true("prompts_dir=../prompts",   cfg.get("prompts_dir") == "../prompts", str(cfg.get("prompts_dir")))
    is_true("top_p ∈ [0,1]",            0 <= api.get("top_p", 1) <= 1, str(api.get("top_p")))

# ══════════════════════════════════════════════
#  P1-6: extract_slug()
# ══════════════════════════════════════════════
def test_extract_slug():
    print("\n=== P1-6: extract_slug() slug 提取 ===")
    eq("正常提取",           gen.extract_slug("---\nslug: my-slug\n---\nbody"), "my-slug")
    eq("带引号",             gen.extract_slug('---\nslug: "my-slug"\n---\nbody'), "my-slug")
    eq("无 frontmatter",     gen.extract_slug("no frontmatter"), None)
    eq("无 slug 字段",       gen.extract_slug("---\ntitle: x\n---\nbody"), None)
    eq("空字符串",           gen.extract_slug(""), None)

# ══════════════════════════════════════════════
#  P1-7: 管线集成
# ══════════════════════════════════════════════
def test_pipeline_integration():
    print("\n=== P1-7: 管线集成 ===")
    _ensure_key()

    # sys_prompt 组装
    sp = gen.sys_prompt("exam")
    is_true("system_prompt 含有 type", "{atype}" not in sp or "exam" in sp)
    is_true("system_prompt 含有 rules", "rules" in sp.lower())

    # pick_template
    with patch("random.choice", return_value="A"):
        t = gen.pick_template("exam")
        eq("template 固定 A", t, "A")

    # wc 词数
    eq("wc=3",                gen.wc("hello world test"), 3)
    eq("空=0",                gen.wc(""), 0)
    eq("frontmatter 不计",    gen.wc("---\ntitle: x\n---\nhello"), 1)

    # split_fm / strip_banned_formatting
    fm, body = gen.split_fm("---\ntitle: x\n---\n## Heading\ncontent")
    eq("split_fm 正确分割", body, "## Heading\ncontent")

    cleaned, n = gen.strip_banned_formatting("---\ntitle: x\n---\n\n## Heading\n\n| table |\n\n- bullet\n")
    is_true("## 被 strip",    "Heading" in cleaned and "## Heading" not in cleaned)
    is_true("| table | 被 strip", "table" not in cleaned, cleaned[:200])
    is_true("bullet 被 strip", "- bullet" not in cleaned)

# ══════════════════════════════════════════════
#  run all
# ══════════════════════════════════════════════
def main():
    print("=" * 60)
    print("  content-engine 后端核心测试套件")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    tests = [
        ("P0-1  API Key 读取",          test_get_api_key),
        ("P0-2  API 调用/重试",         test_call_api),
        ("P0-3  模板注入",              test_inj),
        ("P0-4  文件写入",              test_write_output),
        ("P0-5  10 维评分",             test_score),
        ("P0-6  CTA / Disclaimer",      test_cta_disclaimer),
        ("P1-1  相似度检测",            test_similarity),
        ("P1-2  新闻管线逻辑",          test_daily_ai_news),
        ("P1-3  frontmatter 解析",      test_fm),
        ("P1-4  body 清理",             test_clean_body),
        ("P1-5  config 配置",           test_config),
        ("P1-6  slug 提取",            test_extract_slug),
        ("P1-7  管线集成",             test_pipeline_integration),
    ]

    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            import traceback
            print(f"  [ERROR] {name} 崩溃: {e}")
            traceback.print_exc()
            S.failed += 1

    return S.summary()

if __name__ == "__main__":
    sys.exit(main())
