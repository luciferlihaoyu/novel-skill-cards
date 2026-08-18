#!/usr/bin/env python3
"""跨章节关键词检索：在已切分的工作目录中查找关键词，返回章节号+标题+上下文。

用法:
    python anchor_grep.py <工作目录> "关键词" [--context 60] [--max 20]

用于一致性核对时快速定位同一事物（丹药名、地名、人物、规则）在全书的所有出现位置，
避免逐章重读。
"""
import argparse
import json
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir", help="chapter_splitter.py 的输出目录")
    ap.add_argument("keyword")
    ap.add_argument("--context", type=int, default=60, help="命中点两侧保留的字符数")
    ap.add_argument("--max", type=int, default=20, help="最多输出多少条命中")
    args = ap.parse_args()

    index_path = os.path.join(args.workdir, "chapter_index.json")
    if not os.path.exists(index_path):
        print(f"错误: 未找到 {index_path}，请先运行 chapter_splitter.py", file=sys.stderr)
        sys.exit(1)

    with open(index_path, encoding="utf-8") as f:
        meta = json.load(f)

    hits = []
    for ch in meta["chapters"]:
        with open(os.path.join(args.workdir, ch["file"]), encoding="utf-8") as f:
            body = f.read()
        start = 0
        while True:
            pos = body.find(args.keyword, start)
            if pos == -1:
                break
            lo = max(0, pos - args.context)
            hi = min(len(body), pos + len(args.keyword) + args.context)
            snippet = body[lo:hi].replace("\n", " ")
            hits.append({
                "chapter": ch["chapter"],
                "title": ch["title"],
                "snippet": f"…{snippet}…",
            })
            start = pos + len(args.keyword)

    print(f"关键词「{args.keyword}」共命中 {len(hits)} 处" + (f"，以下显示前 {args.max} 条:" if len(hits) > args.max else ":"))
    for h in hits[: args.max]:
        print(f"[第{h['chapter']}章 {h['title']}] {h['snippet']}")


if __name__ == "__main__":
    main()
