#!/usr/bin/env python3
"""扫描中文小说文本中的 AI 高频词/句式，输出次数、千字频率与超标预警。

用法:
    python ai_tells_scan.py <文本文件> [--per 1000] [--report]

阈值内嵌于 TELLS（每千字允许次数上限，超出即预警）。--report 输出全部命中明细。
"""
import argparse
import re
import sys

# 词表: {类别: [(词/正则, 每千字阈值)]}
TELLS = {
    "高频词-神态动作": [
        ("不禁", 1.5), ("仿佛", 2.0), ("眼底闪过", 0.8), ("闪过一丝", 0.8),
        ("嘴角勾起", 0.8), ("勾起一抹", 0.8), ("眸光", 1.0), ("挑眉", 1.5),
        ("微微一愣", 1.0), ("瞳孔一缩", 0.8), ("倒吸一口", 1.0),
    ],
    "高频词-氛围抒情": [
        ("空气仿佛凝固", 0.3), ("空气凝固", 0.5), ("心跳漏了", 0.3),
        ("命运的齿轮", 0.2), ("仿佛整个世界", 0.3), ("时间仿佛静止", 0.3),
        ("莫名的情绪", 0.3), ("说不出的", 1.0),
    ],
    "连接词": [
        ("然而", 2.5), ("与此同时", 1.0), ("紧接着", 1.2), ("旋即", 1.0),
        ("顷刻间", 0.8), ("霎时间", 0.8), ("陡然", 1.0),
    ],
    "解释型句式": [
        ("他知道，", 1.5), ("她明白，", 1.0), ("这意味着", 0.8),
        ("显而易见", 0.3), ("毫无疑问", 0.5), ("不得不说", 0.8),
    ],
}

TRIPLE_RE = re.compile(r"[，、][^，。！？]{1,12}[，、][^，。！？]{1,12}[，、][^，。！？]{1,12}。")


def load(path):
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--per", type=int, default=1000, help="频率基准字数")
    ap.add_argument("--report", action="store_true", help="输出全部命中明细")
    args = ap.parse_args()

    text = load(args.file)
    chars = len(re.sub(r"\s", "", text))
    if chars == 0:
        print("文本为空", file=sys.stderr)
        sys.exit(1)

    warnings = []
    rows = []
    for cat, items in TELLS.items():
        for word, limit in items:
            n = text.count(word)
            if n == 0:
                continue
            freq = n / chars * args.per
            flag = "⚠超标" if freq > limit else ""
            rows.append((cat, word, n, round(freq, 2), limit, flag))
            if freq > limit:
                warnings.append((word, n, round(freq, 2), limit))

    triples = len(TRIPLE_RE.findall(text))
    triple_freq = triples / chars * args.per

    print(f"总字数: {chars}")
    print(f"\n命中 {len(rows)} 个词项, 其中超标 {len(warnings)} 个:")
    for word, n, freq, limit in sorted(warnings, key=lambda x: -x[2]):
        print(f"  ⚠ {word}: {n} 次 ({freq}/千字, 阈值 {limit})")
    if triple_freq > 1.5:
        print(f"  ⚠ 疑似三连排比句: {triples} 处 ({round(triple_freq, 2)}/千字), 需人工复核")

    if args.report and rows:
        print("\n全部命中:")
        for cat, word, n, freq, limit, flag in rows:
            print(f"  [{cat}] {word}: {n} 次 ({freq}/千字, 阈值 {limit}) {flag}")

    if not warnings and triple_freq <= 1.5:
        print("未发现超标项。")


if __name__ == "__main__":
    main()
