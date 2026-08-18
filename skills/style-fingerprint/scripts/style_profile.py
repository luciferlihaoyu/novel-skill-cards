#!/usr/bin/env python3
"""测量中文小说文本的文风客观指标，输出 JSON。

用法:
    python style_profile.py <文本文件或目录> [--out style_profile.json]

指标:句长分布、对话占比、段落长度、标点频率、高频实词 Top50、句首字 Top20。
目录输入时统计目录下全部 .txt 文件（如 chapter_splitter 的 chapters/ 目录）。
"""
import argparse
import glob
import json
import os
import re
from collections import Counter

SENT_SPLIT = re.compile(r"[^。！？…；!?;]+[。！？…；!?;]*")
DIALOGUE_RE = re.compile(r"[“\"「『]([^”\"」』]*)[”\"」』]")
CN_WORD_RE = re.compile(r"[一-龥]{2,4}")

# 分词停用：虚词与过泛词，只保留有辨识度的实词
STOP = {"我们", "你们", "他们", "她们", "自己", "什么", "怎么", "这样", "那样",
        "一个", "没有", "不是", "知道", "已经", "就是", "还是", "可以", "这个",
        "那个", "这些", "那些", "因为", "所以", "但是", "如果", "虽然", "现在",
        "时候", "东西", "事情", "地方", "起来", "下去", "过来", "过去", "觉得"}


def load_texts(path):
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "**/*.txt"), recursive=True))
    else:
        files = [path]
    parts = []
    for fp in files:
        with open(fp, "rb") as f:
            raw = f.read()
        for enc in ("utf-8", "gb18030"):
            try:
                parts.append(raw.decode(enc))
                break
            except UnicodeDecodeError:
                continue
    return "\n".join(parts)


def profile(text):
    chars = len(re.sub(r"\s", "", text))
    sentences = [s.strip() for s in SENT_SPLIT.findall(text) if s.strip()]
    sent_lens = [len(s) for s in sentences]

    paras = [p.strip() for p in text.split("\n") if p.strip()]
    para_lens = [len(p) for p in paras]

    dialogue_chars = sum(len(m) for m in DIALOGUE_RE.findall(text))

    punct = {p: text.count(p) for p in ["。", "，", "！", "？", "……", "—", "：", "；"]}
    per_k = {k: round(v / max(chars, 1) * 1000, 2) for k, v in punct.items()}

    # 高频词提取：有 jieba 用 jieba；否则用滑动 2-3 字窗口（无依赖回退，
    # 只保留出现 >=3 次的串，真词会被重复计数自然浮出，碎串不会）
    words = None
    try:
        import jieba  # type: ignore

        words = Counter(
            w for w in jieba.lcut(text)
            if 2 <= len(w) <= 4 and CN_WORD_RE.fullmatch(w) and w not in STOP
        )
    except ImportError:
        cn = re.findall(r"[一-龥]+", text)
        grams = Counter()
        for seg in cn:
            for n in (2, 3):
                grams.update(seg[i : i + n] for i in range(len(seg) - n + 1))
        words = Counter({w: c for w, c in grams.items() if c >= 3 and w not in STOP})
    # 句首字（叙述起笔习惯）
    heads = Counter(s[0] for s in sentences if s)

    def bucket(lens, edges):
        out = {}
        total = max(len(lens), 1)
        prev = 0
        for e in edges:
            out[f"{prev}-{e}"] = round(sum(1 for l in lens if prev < l <= e) / total, 3)
            prev = e
        out[f"{prev}+"] = round(sum(1 for l in lens if l > prev) / total, 3)
        return out

    return {
        "total_chars": chars,
        "sentence_count": len(sentences),
        "avg_sentence_len": round(sum(sent_lens) / max(len(sent_lens), 1), 1),
        "sentence_len_dist": bucket(sent_lens, [5, 10, 20, 35]),
        "avg_para_len": round(sum(para_lens) / max(len(para_lens), 1), 1),
        "para_len_dist": bucket(para_lens, [30, 80, 150, 300]),
        "dialogue_ratio": round(dialogue_chars / max(chars, 1), 3),
        "punct_per_1000_chars": per_k,
        "top_words": words.most_common(50),
        "top_sentence_starters": heads.most_common(20),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    text = load_texts(args.input)
    result = profile(text)
    result["input"] = os.path.abspath(args.input)

    out = args.out or "style_profile.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"样本字数: {result['total_chars']}, 句子数: {result['sentence_count']}")
    print(f"平均句长: {result['avg_sentence_len']} 字, 对话占比: {result['dialogue_ratio']}")
    print(f"句长分布: {result['sentence_len_dist']}")
    print(f"高频词 Top10: {[w for w, _ in result['top_words'][:10]]}")
    print(f"已写入 {out}")


if __name__ == "__main__":
    main()
