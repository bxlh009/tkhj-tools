# -*- coding: utf-8 -*-
"""content-engine 自动测试套件"""
import sys, os, re, json, pathlib, statistics, tempfile, hashlib
from collections import Counter
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "site"))
HERE = pathlib.Path(__file__).resolve().parent
ENGINE = HERE.parent

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    def ok(self, name):
        self.passed += 1
        print(f"  [PASS] {name}")
    def fail(self, name, reason):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  [FAIL] {name}: {reason}")

R = TestResult()

def assert_eq(name, actual, expected):
    if actual == expected:
        R.ok(name)
    else:
        R.fail(name, f"expected {expected!r}, got {actual!r}")

def assert_true(name, cond, detail=""):
    if cond:
        R.ok(name)
    else:
        R.fail(name, f"condition false {detail}")

def assert_raises(name, exc_type, fn, *args):
    try:
        fn(*args)
        R.fail(name, f"expected {exc_type.__name__} but no exception")
    except exc_type:
        R.ok(name)
    except Exception as e:
        R.fail(name, f"expected {exc_type.__name__}, got {type(e).__name__}: {e}")

def _mock_response(data):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(data).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp

def test_api_retry():
    print("\n=== P0-1: API 重试 ===")
    import generate as gen
    # 正常: 首次成功
    mock_data = {"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
    with patch("urllib.request.urlopen", return_value=_mock_response(mock_data)):
        result = gen.call_api("sys", "user")
        assert_eq("首次调用返回内容", result, "ok")
    # 边界: 2次超时后成功
    call_count = [0]
    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] <= 2:
            raise TimeoutError("simulated timeout")
        return _mock_response({"choices": [{"message": {"content": "recovered"}}], "usage": {}})
    with patch("urllib.request.urlopen", side_effect=side_effect):
        result = gen.call_api("sys", "user")
        assert_eq("2次超时后恢复", result, "recovered")
        assert_eq("调用次数=3", call_count[0], 3)
    # 边界: 3次全超时
    with patch("urllib.request.urlopen", side_effect=TimeoutError("always")):
        assert_raises("3次全超时抛异常", RuntimeError, lambda: gen.call_api("sys", "user"))

def test_frontmatter():
    print("\n=== P0-2: frontmatter/BOM ===")
    import build
    text = '---\ntitle: "Test"\ndate: "2026-07-09"\n---\nHello world.'
    meta, body = build.fm(text)
    assert_eq("提取 title", meta.get("title"), "Test")
    assert_true("body 不含 ---", "---" not in body)
    assert_eq("body 内容", body.strip(), "Hello world.")
    text_bom = '\ufeff' + text
    meta2, body2 = build.fm(text_bom)
    assert_eq("BOM: 提取 title", meta2.get("title"), "Test")
    assert_eq("BOM: body 内容", body2.strip(), "Hello world.")
    meta3, body3 = build.fm("Just plain text")
    assert_eq("无 fm: meta 为空", meta3, {})
    assert_eq("无 fm: body=全文", body3, "Just plain text")
    meta4, body4 = build.fm("")
    assert_eq("空文件: meta", meta4, {})
    assert_eq("空文件: body", body4, "")

def test_hallucination():
    print("\n=== P0-3: 幻觉检测 ===")
    def detect(text):
        patterns = [r"(?:^|\b)\d+\.\d+%\b", r"(?:^|\b)\d+\.\d+\s*(points?|score)\b"]
        has_num = any(re.search(p, text) for p in patterns)
        has_attr = bool(re.search(r"(according to|reportedly|claimed|stated|said)", text, re.I))
        return has_num and not has_attr
    assert_true("无数字不触发", not detect("This is great."))
    assert_true("有来源不触发", not detect("According to OpenAI, 94.2% accuracy."))
    assert_true("无来源数字触发", detect("GPT-5.6 scored 94.2% on benchmarks."))
    assert_true("空文本不触发", not detect(""))

def test_similarity():
    print("\n=== P1-1: 相似度 ===")
    from check_similarity import _ngrams, jaccard, cosine
    a = _ngrams("abcdefg", 3)
    b = _ngrams("xyzwvut", 3)
    assert_true("完全不同相似度=0", jaccard(a, b) == 0.0)
    c = _ngrams("abcdefg", 3)
    assert_true("完全相同 jaccard=1", jaccard(a, c) == 1.0)
    empty = _ngrams("", 3)
    assert_true("空文本不崩溃", isinstance(jaccard(empty, a), float))
    single = _ngrams("a", 3)
    assert_true("单字符不崩溃", isinstance(cosine(single, single), float))

def test_scoring():
    print("\n=== P1-2: 评分机制 ===")
    import generate as gen
    good_text = "---\ntitle: test\n---\nI've been testing AI tools for five years now, and honestly? Most of them don't live up to the hype. But this one's different - it actually works. I can't believe I'm saying that.\n\nLook, I don't say that lightly. I've tested hundreds of tools. This one? It's the real deal. The interface is clean, the output is solid, and it doesn't crash every five minutes like some competitors I could name. You know what kills me? The ones that promise everything and deliver nothing.\n\nHere's the thing though: you need to know what you're buying. Is it perfect? No. Nothing is. But for the price? It's a steal. I'd recommend it to anyone who's serious about getting work done. Don't just take my word for it though. Try it yourself. See if it fits your workflow. That's the only way you'll know for sure. Honestly, I was shocked."
    sc, verdict, det = gen.score(good_text, 200, 3000)
    assert_true(f"高质量 PASS (score={sc})", verdict == "PASS")
    sc2, verdict2, _ = gen.score("", 200, 3000)
    assert_eq("空文本=0分", sc2, 0)
    assert_eq("空文本=EMPTY", verdict2, "EMPTY")
    sc3, verdict3, _ = gen.score("Hi.", 200, 3000)
    assert_true(f"超短 WARN (score={sc3})", verdict3 == "WARN")

if __name__ == "__main__":
    print("=" * 60)
    print("content-engine 自动测试套件")
    print("=" * 60)
    test_api_retry()
    test_frontmatter()
    test_hallucination()
    test_similarity()
    test_scoring()
    print("\n" + "=" * 60)
    print(f"结果: PASS={R.passed}  FAIL={R.failed}")
    if R.errors:
        print("\n失败项:")
        for name, reason in R.errors:
            print(f"  - {name}: {reason}")
    print("=" * 60)
    sys.exit(0 if R.failed == 0 else 1)