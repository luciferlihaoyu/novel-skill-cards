#!/usr/bin/env python3
"""章节切分与统计工具 —— 拆书技能辅助脚本

用途:将上传的网文/小说 txt 文件按章节切分,输出章节清单与统计信息,
便于后续分块分析(长篇小说明文可能达数百万字,必须先切分再分批处理)。

用法:
    python chapter_splitter.py <novel.txt> [--out-dir DIR] [--max-chars N] [--list-only]

功能:
    1. 自动识别常见章节标题格式(第X章/第X回/Chapter X/卷章结构等)
    2. 输出章节索引 chapter_index.json(章节号、标题、起止位置、字数)
    3. 可选:将每章写入独立文件 chapters/0001_标题.txt
    4. 打印全书统计:总字数、章节数、均章字数、前3章字数(黄金三章分析用)
"""
import argparse
import json
import os
import re
import sys

# 常见网文章节标题模式(按优先级排列)
CHAPTER_PATTERNS = [
    # 第X卷/部 + 第X章 组合行,或单独 "第123章 标题" / "第123章:标题"
    r"^\s*第[0-9零一二三四五六七八九十百千万两]+[章回节集][^\n]{0,60}$",
    # "Chapter 123" / "chapter 123 title"
    r"^\s*[Cc]hapter\s+\d+[^\n]{0,60}$",
    # "123、标题" / "123. 标题"(番茄等平台导出格式)
    r"^\s*\d{1,5}\s*[、.．]\s*\S[^\n]{0,60}$",
    # "正文 第X章" 残留
    r"^\s*正文\s*第[0-9零一二三四五六七八九十百千万两]+章[^\n]{0,60}$",
]

COMBINED = re.compile("|".join(f"({p})" for p in CHAPTER_PATTERNS), re.MULTILINE)


def find_chapters(text: str):
    """返回 [(start, end, title), ...];若未识别到章节则返回空列表。"""
    matches = list(COMBINED.finditer(text))
    # 过滤:标题命中过密(<200字)通常不是真章节,可能是目录或引用
    chapters = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = m.group(0).strip()
        if end - start >= 200 or i == len(matches) - 1:
            chapters.append((start, end, title))
    return chapters


def safe_name(s: str, maxlen: int = 40) -> str:
    s = re.sub(r'[\\/:*?"<>|\s]+', "_", s)
    return s[:maxlen] or "untitled"


def main():
    ap = argparse.ArgumentParser(description="小说章节切分与统计")
    ap.add_argument("input", help="小说 txt 文件路径")
    ap.add_argument("--out-dir", default=None, help="输出目录(默认:与输入同级的 <书名>_chapters/)")
    ap.add_argument("--list-only", action="store_true", help="只生成索引,不写单章文件")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    total_chars = len(re.sub(r"\s", "", text))
    chapters = find_chapters(text)
    base = os.path.splitext(os.path.basename(args.input))[0]
    out_dir = args.out_dir or os.path.join(os.path.dirname(os.path.abspath(args.input)), f"{base}_chapters")
    os.makedirs(out_dir, exist_ok=True)

    if not chapters:
        # 未识别章节:按固定字数兜底切块
        chunk = 8000
        chapters = []
        for i in range(0, len(text), chunk):
            chapters.append((i, min(i + chunk, len(text)), f"block_{i // chunk + 1:04d}"))
        print(f"[警告] 未识别到章节标题,已按 {chunk} 字切块,共 {len(chapters)} 块。", file=sys.stderr)

    index = []
    for i, (start, end, title) in enumerate(chapters, 1):
        body = text[start:end]
        n = len(re.sub(r"\s", "", body))
        index.append({"no": i, "title": title, "chars": n, "start": start, "end": end})
        if not args.list_only:
            fn = os.path.join(out_dir, f"{i:04d}_{safe_name(title)}.txt")
            with open(fn, "w", encoding="utf-8") as f:
                f.write(body)

    idx_path = os.path.join(out_dir, "chapter_index.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump({"source": os.path.abspath(args.input), "total_chars": total_chars,
                   "chapter_count": len(index), "chapters": index}, f, ensure_ascii=False, indent=2)

    avg = total_chars // max(len(index), 1)
    first3 = sum(c["chars"] for c in index[:3])
    print(f"全书统计: 总字数≈{total_chars} | 章节/块数={len(index)} | 均章≈{avg}字 | 前三章≈{first3}字")
    print(f"章节索引: {idx_path}")
    if not args.list_only:
        print(f"单章文件: {out_dir}/0001_*.txt ...")


if __name__ == "__main__":
    main()
