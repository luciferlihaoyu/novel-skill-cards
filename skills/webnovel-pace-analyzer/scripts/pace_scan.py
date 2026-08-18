#!/usr/bin/env python3
"""逐章扫描网文节奏信号，输出 CSV：字数、章末钩子信号、爽点信号计数、对话占比。

用法:
    python pace_scan.py <工作目录> [--out pace_report.csv]

<工作目录> 为 chapter_splitter.py 的输出目录（含 chapter_index.json）。
信号只是定位线索，命中不代表爽点/钩子成立，需回读原文定性。
"""
import argparse
import csv
import json
import os
import re
import sys

# 爽点信号词（按类型分组，可按题材扩充）
SATISFY_SIGNALS = {
    "打脸": ["打脸", "跪下", "道歉", "脸色难看", "面如死灰", "哑口无言", "后悔", "求饶"],
    "突破": ["突破", "晋级", "进阶", "踏入", "瓶颈", "更上一层楼", "暴涨"],
    "收获": ["获得", "到手", "收入囊中", "奖励", "宝箱", "传承", "认主", "炼化"],
    "震惊": ["震惊", "哗然", "倒吸", "目瞪口呆", "不可思议", "轰动", "沸腾"],
    "揭秘": ["原来", "真相", "竟然", "没想到", "身份", "揭秘", "曝光"],
    "危机解除": ["脱险", "化解", "反杀", "逆转", "翻盘", "得救"],
}

# 章末钩子信号（检查每章最后 200 字）
HOOK_SIGNALS = ["突然", "就在此时", "就在这时", "然而", "一道", "异变", "变故",
                "危机", "杀意", "冷笑", "神秘", "何人", "是谁", "不好"]

DIALOGUE_RE = re.compile(r"[“\"「『]([^”\"」』]*)[”\"」』]")


def analyze_chapter(body: str):
    chars = len(body)
    tail = body[-200:] if len(body) > 200 else body

    hook_q = 1 if re.search(r"[?？!！…]\s*[\"”」』']?\s*$", body) else 0
    hook_kw = sum(1 for w in HOOK_SIGNALS if w in tail)

    satisfy = {}
    for cat, words in SATISFY_SIGNALS.items():
        satisfy[cat] = sum(body.count(w) for w in words)

    dialogue_chars = sum(len(m) for m in DIALOGUE_RE.findall(body))
    dialogue_ratio = round(dialogue_chars / chars, 3) if chars else 0

    return {
        "chars": chars,
        "hook_question_end": hook_q,
        "hook_keywords": hook_kw,
        "satisfy_total": sum(satisfy.values()),
        **{f"s_{k}": v for k, v in satisfy.items()},
        "dialogue_ratio": dialogue_ratio,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with open(os.path.join(args.workdir, "chapter_index.json"), encoding="utf-8") as f:
        meta = json.load(f)

    rows = []
    for ch in meta["chapters"]:
        with open(os.path.join(args.workdir, ch["file"]), encoding="utf-8") as f:
            body = f.read()
        stats = analyze_chapter(body)
        rows.append({"chapter": ch["chapter"], "title": ch["title"], **stats})

    fields = list(rows[0].keys()) if rows else []
    out = args.out or os.path.join(args.workdir, "pace_report.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # 控制台速览：爽点信号为 0 的连续区间
    zero_runs, run_start = [], None
    for r in rows:
        if r["satisfy_total"] == 0:
            if run_start is None:
                run_start = r["chapter"]
        else:
            if run_start is not None:
                zero_runs.append((run_start, prev))
                run_start = None
        prev = r["chapter"]
    if run_start is not None:
        zero_runs.append((run_start, rows[-1]["chapter"]))

    print(f"已扫描 {len(rows)} 章 -> {out}")
    if zero_runs:
        print("爽点信号为 0 的连续区间（需回读定性）:")
        for a, b in zero_runs:
            print(f"  第 {a}–{b} 章 (连续 {b - a + 1} 章)")
    else:
        print("未发现爽点信号空窗区间。")


if __name__ == "__main__":
    main()
