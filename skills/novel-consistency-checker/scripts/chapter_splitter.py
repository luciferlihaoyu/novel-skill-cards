#!/usr/bin/env python3
"""切分长篇小说为单章文件，并生成章节索引 chapter_index.json。

用法:
    python chapter_splitter.py <小说文件> --out-dir <输出目录> [--chunk-size 4000]

- 识别"第X章 / 第X卷 / 楔子 / 序章 / Chapter N"等标题（中文与阿拉伯数字兼匹配）
- 识别不到标题时按 --chunk-size 字数切块，块名标注"自动分块"
"""
import argparse
import json
import os
import re
import sys

HEADING_RE = re.compile(
    r"^\s*(?:第\s*[0-9０-９一二三四五六七八九十百千万零两]+\s*[章卷节回]"
    r"|楔子|序章?|引子|番外篇?.{0,20}|尾声|终章"
    r"|Chapter\s+\d+|CHAPTER\s+\d+)"
    r"[^\n]{0,40}$"
)


def read_text(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8", "gb18030", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def split_by_heading(text: str):
    lines = text.splitlines()
    heads = [(i, ln.strip()) for i, ln in enumerate(lines) if HEADING_RE.match(ln)]
    if not heads:
        return []
    chapters = []
    for idx, (line_no, title) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        body = "\n".join(lines[line_no + 1 : end]).strip()
        chapters.append({"title": title, "body": body})
    # 忽略正文前几乎无内容的"伪章节"
    return [c for c in chapters if c["body"]]


def split_by_size(text: str, size: int):
    chapters, buf = [], []
    count = 0
    for para in text.split("\n"):
        buf.append(para)
        count += len(para)
        if count >= size:
            chapters.append({"title": None, "body": "\n".join(buf).strip()})
            buf, count = [], 0
    if buf:
        chapters.append({"title": None, "body": "\n".join(buf).strip()})
    return [c for c in chapters if c["body"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("novel")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--chunk-size", type=int, default=4000)
    args = ap.parse_args()

    text = read_text(args.novel)
    chapters = split_by_heading(text)
    mode = "按章节标题切分"
    if len(chapters) < 2:
        chapters = split_by_size(text, args.chunk_size)
        mode = f"未识别到章节标题，按每块约{args.chunk_size}字自动分块"

    os.makedirs(args.out_dir, exist_ok=True)
    ch_dir = os.path.join(args.out_dir, "chapters")
    os.makedirs(ch_dir, exist_ok=True)

    index = []
    for i, ch in enumerate(chapters, 1):
        title = ch["title"] or f"自动分块-{i}"
        fname = f"ch{i:04d}.txt"
        with open(os.path.join(ch_dir, fname), "w", encoding="utf-8") as f:
            f.write(ch["body"])
        index.append({
            "chapter": i,
            "title": title,
            "chars": len(ch["body"]),
            "file": f"chapters/{fname}",
        })

    meta = {
        "source": os.path.abspath(args.novel),
        "mode": mode,
        "total_chapters": len(index),
        "total_chars": sum(c["chars"] for c in index),
        "chapters": index,
    }
    with open(os.path.join(args.out_dir, "chapter_index.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"切分方式: {mode}")
    print(f"共 {meta['total_chapters']} 章/块, 总字数 {meta['total_chars']}")
    print(f"索引: {os.path.join(args.out_dir, 'chapter_index.json')}")


if __name__ == "__main__":
    main()
