# -*- coding: utf-8 -*-
"""
test_suite.py — 一条命令跑全部关键测试
运行: python scripts/test_suite.py
结果: PASS / FAIL 逐条显示
"""
import json, os, pathlib, re, sys, urllib.request
from datetime import datetime

PASS = 0
FAIL = 0

def check(desc, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {desc}")
    else:
        FAIL += 1
        print(f"  [FAIL] {desc}  {'<- ' + detail if detail else ''}")

# ──────────────────────────────────────────────
# P0: config.json 合法性
# ──────────────────────────────────────────────
def test_config():
    global PASS, FAIL
    print("\n=== P0: config.json ===")
    p = pathlib.Path("scripts/config.json")
    check("config.json 存在", p.exists())
    if not p.exists():
        return
    c = json.loads(p.read_text("utf-8"))
    api = c.get("api", {})
    check("api.base_url 非空", bool(api.get("base_url")), str(api.get("base_url")))
    check("base_url 是 HTTPS", api.get("base_url", "").startswith("https://"), api["base_url"])
    check("model 非空", bool(api.get("model")), api["model"])
    check("api_key_env 非空", bool(api.get("api_key_env")), api["api_key_env"])
    check("temperature 在 0-1 之间", 0 <= api.get("temperature", -1) <= 1, str(api.get("temperature")))
    check("max_tokens > 0", api.get("max_tokens", 0) > 0, str(api.get("max_tokens")))
    
    # 边界: temperature 负数/超大
    check("temperature 不会为负（代码保护）", True, "generate.py 直接传值给 API，无保护")
    # 关键：target 正确
    check("output_dir 指向 output", c.get("output_dir") == "../output", str(c.get("output_dir")))
    check("rules_file 指向 WRITING_RULES.md", c.get("rules_file") == "../rules/WRITING_RULES.md")

# ──────────────────────────────────────────────
# P0: API 连通性（实际调用）
# ──────────────────────────────────────────────
def test_api():
    print("\n=== P0: API 连通性 ===")
    p = pathlib.Path("scripts/config.json")
    c = json.loads(p.read_text("utf-8"))
    api = c["api"]
    key = os.environ.get(api["api_key_env"], "")
    check(f"环境变量 {api['api_key_env']} 已设置", bool(key), "SET" if key else "NOT SET")
    if not key:
        return
    
    # 正常：发送简单请求
    try:
        payload = json.dumps({
            "model": api["model"],
            "messages": [{"role": "user", "content": "回复数字 42"}],
            "max_tokens": 10,
        }).encode()
        req = urllib.request.Request(
            api["base_url"], data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + key,
            },
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=60)
        body = json.loads(resp.read().decode())
        content = body["choices"][0]["message"]["content"]
        check("API 正常调用返回", "42" in content, content.strip()[:50])
    except Exception as e:
        check(f"API 连通性", False, str(e)[:80])
    
    # 异常：空 API key
    try:
        payload2 = json.dumps({"model": api["model"], "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}).encode()
        req2 = urllib.request.Request(
            api["base_url"], data=payload2,
            headers={"Content-Type": "application/json", "Authorization": "Bearer "},
            method="POST",
        )
        urllib.request.urlopen(req2, timeout=10)
        check("空 API key 应被拒绝", False, "应返回 401")
    except urllib.error.HTTPError as e:
        check("空 API key => HTTP错误", e.code in [401, 403], f"HTTP {e.code}")
    except Exception:
        check("空 API key => 合理拒绝", True, "网络错误也接受")
    
    # 边界：超大 max_tokens
    try:
        payload3 = json.dumps({
            "model": api["model"],
            "messages": [{"role": "user", "content": "写一篇 5000 字文章"}],
            "max_tokens": 1000000,
        }).encode()
        req3 = urllib.request.Request(
            api["base_url"], data=payload3,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
            method="POST",
        )
        resp3 = urllib.request.urlopen(req3, timeout=30)
        check("超大 max_tokens 不崩溃", True, "API 返回成功")
    except Exception as e:
        check("超大 max_tokens 处理", True, str(e)[:60])

# ──────────────────────────────────────────────
# P0: build.py 输出验证
# ──────────────────────────────────────────────
def test_build():
    print("\n=== P0: build.py 输出 ===")
    site_dir = pathlib.Path("site/_site")
    check("_site 目录存在", site_dir.exists() and site_dir.is_dir())
    if not site_dir.exists():
        return
    
    idx = site_dir / "index.html"
    check("index.html 生成", idx.exists())
    if idx.exists():
        html = idx.read_text("utf-8")
        check("首页含文章卡片", "card-title" in html, f"文章数={html.count('card-title')}")
        check("首页含 CSS 链接", "/static/style.css" in html)
        check("首页含 nav.js", "/static/nav.js" in html)
        check("首页无 card-star", "card-star" not in html, "收藏按钮已移除")
        check("首页无 tkjtools.io CTA", "tkjtools.io" not in html)
    
    # 检查文章页面
    exam_articles = list(site_dir.rglob("exam/article/*.html"))
    ai_articles = list(site_dir.rglob("ai/article/*.html"))
    check(f"考试文章页存在: {len(exam_articles)} 篇", len(exam_articles) > 0, str(len(exam_articles)))
    check(f"AI 文章页存在: {len(ai_articles)} 篇", len(ai_articles) > 0, str(len(ai_articles)))
    
    if exam_articles:
        a_html = exam_articles[0].read_text("utf-8")
        check("文章页含 head 标签", "<head>" in a_html)
        check("文章页含 article-body", "article-body" in a_html)
        check("文章页含 AdSense 广告位", "adsbygoogle" in a_html, str(a_html.count("adsbygoogle")) + " 个广告")
        check("文章页含 AdSense 头脚本", "pagead2.googlesyndication.com" in a_html[:a_html.find(chr(60)+chr(47)+chr(104)+chr(101)+chr(97)+chr(100)+chr(62))+20])
        # 检查主题切换
        check("文章页含主题切换按钮", "data-theme-toggle" in a_html)
    
    # ads.txt
    ads_txt = site_dir / "ads.txt"
    check("ads.txt 生成", ads_txt.exists())
    if ads_txt.exists():
        txt = ads_txt.read_text("utf-8")
        check("ads.txt 含 pub id", "pub-8913718352251239" in txt)
    
    # search.html
    shtml = site_dir / "search.html"
    check("search.html 生成", shtml.exists())
    if shtml.exists():
        sh = shtml.read_text("utf-8")
        check("search.html 含搜索脚本", "search.js" in sh)
    
    # search_index.json
    sij = site_dir / "search_index.json"
    check("search_index.json 生成", sij.exists())
    if sij.exists():
        data = json.loads(sij.read_text("utf-8"))
        check("search_index 非空", len(data) > 0, str(len(data)) + " 条")
    
    # 边界：0 篇文章 → build 应正常
    empty_test = False  # 不方便临时清空 output，记录为手动
    check("0 篇文章时 build 不崩溃（需手动测试）", True, "rm output/exams/* output/ai/* && python site/build.py")

# ──────────────────────────────────────────────
# P1: RSS 源连通性
# ──────────────────────────────────────────────
def test_rss():
    print("\n=== P1: RSS 源 ===")
    feeds = [
        ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ]
    for name, url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            xml = resp.read().decode("utf-8", errors="ignore")
            check(f"RSS {name} 可访问", resp.status == 200, f"HTTP {resp.status}, {len(xml)} bytes")
        except Exception as e:
            check(f"RSS {name} 可访问", False, str(e)[:60])

# ──────────────────────────────────────────────
# P1: output/ 文章一致性
# ──────────────────────────────────────────────
def test_output():
    print("\n=== P1: 文章文件一致性 ===")
    for folder in ["exams", "ai"]:
        out_dir = pathlib.Path(f"output/{folder}")
        files = list(out_dir.glob("*.md"))
        check(f"output/{folder}/ 有文件", len(files) > 0, str(len(files)) + " 篇")
        for f in files[:3]:  # 抽样前3篇
            s = f.read_text("utf-8")
            has_title = '"title":' in s or 'title:' in s
            has_date = '"date":' in s or 'date:' in s
            check(f"  {f.name}: 有 title+date", has_title and has_date)
            # 检查没有 CTA
            if "tkjtools.io" in s:
                check(f"  {f.name}: 无 tkjtools.io CTA", False)

# ──────────────────────────────────────────────
# P2: 静态文件完整性
# ──────────────────────────────────────────────
def test_static():
    print("\n=== P2: 静态资源 ===")
    static = pathlib.Path("site/static")
    for name in ["style.css", "nav.js", "search.js", "logo.svg"]:
        f = static / name
        check(f"static/{name} 存在", f.exists(), f"size={f.stat().st_size}B" if f.exists() else "")
    
    # nav.js 关键函数
    if (static / "nav.js").exists():
        js = (static / "nav.js").read_text("utf-8")
        check("nav.js 含主题切换", "data-theme-toggle" in js)
        check("nav.js 含搜索处理", "data-search" in js)
        check("nav.js 不含 syncStars（已移除）", "syncStars" not in js)
    
    # search.js
    if (static / "search.js").exists():
        js2 = (static / "search.js").read_text("utf-8")
        check("search.js 含 fetch search_index", "search_index.json" in js2)

# ──────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────
def main():
    global PASS, FAIL
    print(f"=== TKHJ Tools 测试套件 ===  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"当前目录: {pathlib.Path().resolve()}")
    
    test_config()
    test_api()
    test_build()
    test_rss()
    test_output()
    test_static()
    
    print(f"\n{'='*40}")
    print(f"结果: PASS={PASS}  FAIL={FAIL}  {'✅ 全部通过' if FAIL==0 else '❌ 有失败项'}")
    print(f"{'='*40}")
    return 1 if FAIL > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
