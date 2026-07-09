# -*- coding: utf-8 -*-
"""
相似度检测脚本

用法：
  python check_similarity.py
  python check_similarity.py --threshold 0.25

逻辑：
  - 读取 output/ 目录下所有 .md 文件
  - 提取正文（去掉 YAML frontmatter）
  - 用字符级 3-gram 向量化
  - 两两计算 Jaccard 相似度
  - 超过阈值则报警
"""

import argparse
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ENGINE_DIR  = SCRIPTS_DIR.parent
OUTPUT_DIR  = ENGINE_DIR / "output"


def file_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # 去掉 YAML frontmatter
    content = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL)
    # 去掉 markdown 符号，仅保留中英文字符
    content = re.sub(r"[^一-鿿a-zA-Z0-9]", "", content)
    return content.lower()


def _ngrams(text: str, n: int = 3) -> Counter:
    return Counter(text[i:i+n] for i in range(len(text) - n + 1))


def jaccard(a: Counter, b: Counter) -> float:
    if not a and not b:
        return 0.0
    intersection = sum((a & b).values())
    union        = sum((a | b).values())
    return intersection / union if union else 0.0


def cosine(a: Counter, b: Counter) -> float:
    common = set(a) | set(b)
    dot    = sum(a[k] * b[k] for k in common)
    norm_a = sum(v*v for v in a.values()) ** 0.5
    norm_b = sum(v*v for v in b.values()) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def main():
    parser = argparse.ArgumentParser(description="检查 output/ 目录下文章相似度")
    parser.add_argument("--threshold", type=float, default=0.30,
                        help="相似度阈值，超过则报警（默认 0.30）")
    parser.add_argument("--ngram", type=int, default=3,
                        help="n-gram 大小（默认 3）")
    args = parser.parse_args()

    md_files = list(OUTPUT_DIR.rglob("*.md"))
    if len(md_files) < 2:
        print(f"[OK]  目录下只有 {len(md_files)} 篇文章，跳过检测")
        return

    print(f"[INFO] 读取到 {len(md_files)} 篇文章，使用 {args.ngram}-gram 对比")
    print()

    fingerprints = {f: _ngrams(file_text(f), args.ngram) for f in md_files}

    alerts = []
    for fa, fb in combinations(md_files, 2):
        sim_ng = jaccard(fingerprints[fa], fingerprints[fb])
        sim_co = cosine(fingerprints[fa], fingerprints[fb])
        sim_max = max(sim_ng, sim_co)
        flag = "  ⚠️" if sim_max >= args.threshold else ""
        print(f"  {fa.name:45} vs  {fb.name:45}  ngram={sim_ng:.2f}  cosine={sim_co:.2f}{flag}")
        if sim_max >= args.threshold:
            alerts.append((fa, fb, sim_max))

    print()
    if alerts:
        print(f"[WARN] 发现 {len(alerts)} 对文章相似度超过 {args.threshold:.0%}：")
        for fa, fb, s in alerts:
            print(f"       {fa.name} <-> {fb.name}  ({s:.1%})")
        sys.exit(1)
    else:
        print(f"[OK]  所有文章对相似度均在 {args.threshold:.0%} 以下")


def check_new_article(new_text, existing_dir, threshold=0.30):
    """Check if new_text is too similar to any existing .md file in existing_dir.

    Returns (is_too_similar, most_similar_name, max_similarity).
    """
    new_clean = re.sub(r"[^一-鿿a-zA-Z0-9]", "", re.sub(r"^---\n.*?\n---\n", "", new_text, flags=re.DOTALL)).lower()
    new_fp = Counter(_ngrams(new_clean, 3))
    max_sim = 0.0
    max_name = None
    for f in Path(existing_dir).glob("*.md"):
        other = file_text(f)
        other_fp = Counter(_ngrams(other, 3))
        sim = max(jaccard(new_fp, other_fp), cosine(new_fp, other_fp))
        if sim > max_sim:
            max_sim = sim
            max_name = f.name
    return max_sim >= threshold, max_name, max_sim


if __name__ == "__main__":
    main()
