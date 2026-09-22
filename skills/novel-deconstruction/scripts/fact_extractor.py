#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fact_extractor —— 事实/主题索引生成器(拆书技能辅助脚本)

用法:
    python fact_extractor.py <工作目录>

<工作目录> 必须是 chapter_splitter.py 的输出目录:内含 chapter_index.json
与按 "NNNN_标题.txt" 命名的单章文本文件。运行后在同目录写出 facts_index.json。

输出结构(与 consistency-check.md 第一步约定的统一口径):
    {"facts": [{"chapter": <int 章号>,
                "category": "numeric" | "temporal" | "entity" | "state",
                "text": "<原文摘句,≤60字>",
                "detail": "<规则要点,如 '每击杀1妖兽=10积分' 所命中句式的说明>"}],
     "topics": [{"term": "<术语/伏笔/人称代称>",
                 "chapters": [<出现章号列表>],
                 "first_chapter": <int 首次出现章号>}]}

category 语义:
    numeric  = 数值/结算规则(每X得Y、积分/灵石/金币结算、含数字句)
    temporal = 时间词/时长/年龄/间隔(第N天、三年后、岁月流转、已X年)
    entity   = 同一物品/能力/金手指的每一处描述(本脚本只抓引号专名,刻意保守)
    state    = 生死/下落/知情范围(本脚本只抓显式关键词,刻意保守)

设计原则:
    索引负责让事实碰面,完备性由核对者补漏保证。
    本脚本只是启发式辅助索引,不是完备提取:
    - numeric/temporal 句式覆盖较全,可直接作为事实清单雏形;
    - entity/state 召回低没关系(宁缺勿滥),最终清单以 AI 通读补漏为准;
    - 空章/无命中的章节优雅跳过,绝不虚构事实;
    - 纯 Python 标准库(re/json/pathlib),无网络、无重依赖。

控制台摘要:
    共索引 N 章 | facts M 条(numeric=a temporal=b entity=c state=d) | topics K 条
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

INDEX_NAME = "chapter_index.json"
OUTPUT_NAME = "facts_index.json"

# 每章每类最多收录条数(索引要精,不要淹没核对者)
MAX_FACTS_PER_CATEGORY_PER_CHAPTER = 20
MAX_TEXT_LEN = 60      # 摘句上限(口径约定 ≤60 字)
CONTEXT_BEFORE = 15    # 截断时向前保留的上下文字数


class FactExtractorError(Exception):
    """可读的业务错误:直接打印消息并以非 0 退出,不抛 traceback。"""


# ---------------------------------------------------------------- 句子切分
SENT_RE = re.compile(r"[^。！？!?；;\n]+")
# 章节标题行(正文首行多为 "第X章 ..." 等,不算事实)
TITLE_LINE_RE = re.compile(
    r"^(?:第[0-9零一二三四五六七八九十百千万两]+[章回节集]|[Cc]hapter\s*\d+|\d{1,5}[、.．])"
)

NUM_PAT = r"[0-9零一二三四五六七八九十百千万两]+"
CURRENCY = r"(?:积分|贡献点|贡献值|灵石|金币|银币|铜币|晶币|经验|经验值|点数|声望|功勋)"

# ------------------------------------------------------------ numeric 规则
NUMERIC_RULES = [
    ("数值规则:每X得Y", re.compile(r"每[^，。！？；;]{1,12}?[=＝]")),
    ("数值规则:每X得Y", re.compile(rf"每[^，。！？；;]{{1,12}}?(?:得|加|奖励|获得|赠)\s*{NUM_PAT}")),
    ("数值单位结算", re.compile(rf"{NUM_PAT}\s*(?:点)?{CURRENCY}")),
    ("收支/结算动作", re.compile(
        rf"(?:获得|奖励|结算|收入|进账|入账|收获|赚取|花费|消耗|支付)[^，。！？；;]{{0,15}}{NUM_PAT}")),
    ("含数字句(人工复核)", re.compile(r"\d")),
]

# ----------------------------------------------------------- temporal 规则
TEMPORAL_RULES = [
    ("时间锚:第N天/年", re.compile(rf"第\s*{NUM_PAT}\s*(?:天|日|年|月|次|夜)")),
    ("时间锚:X后/之内", re.compile(
        rf"{NUM_PAT}\s*(?:天|日|年|月|个时辰|刻钟|炷香)\s*(?:后|之内|以内|之前)")),
    ("时间锚:已/过了X年", re.compile(
        rf"(?:已|又|过了|足足|整整|时隔)\s*{NUM_PAT}\s*(?:年|天|日|月)")),
    ("时间锚:固定时间词", re.compile(
        "次日|翌日|翌晨|当夜|当晚|当下|如今|此时|片刻后|半晌后|"
        "岁月流转|时光荏苒|光阴似箭|转眼间|数年后|多年以后")),
]

# --------------------------------------------- entity 规则(保守:仅引号专名)
ENTITY_RULES = [
    ("专名描述线索(辅助,以AI补漏为准)", re.compile(r"[「“【《][^「」“”【】《》]{1,12}[」”】》]")),
]

# ------------------------------------------- state 规则(保守:仅显式关键词)
STATE_RULES = [
    ("知情范围线索(辅助,以AI补漏为准)", re.compile(
        "只有|仅|唯独|无人知晓|无人知道|没有人知道|瞒着|隐瞒|尚不知|并不知情|还不知道|全然不知")),
    ("生死/下落线索(辅助,以AI补漏为准)", re.compile(
        "已经死了|死了吗|身亡|陨落|丧命|尸体|尸首|葬在|下落不明|杳无音讯|失踪|还活着|未死")),
]

CATEGORY_ORDER = ("numeric", "temporal", "entity", "state")
CATEGORY_RULES = {
    "numeric": NUMERIC_RULES,
    "temporal": TEMPORAL_RULES,
    "entity": ENTITY_RULES,
    "state": STATE_RULES,
}

# ---------------------------------------------------------------- topics
# 常见姓氏:用于识别人名候选(2~3 字、以姓氏开头、全书重复出现)
SURNAMES = (
    "王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧"
    "田董袁潘蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦傅"
    "方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔"
    "向常汤"
)
NAME_3_RE = re.compile(rf"[{SURNAMES}][\u4e00-\u9fa5]{{2}}")
NAME_2_RE = re.compile(rf"[{SURNAMES}][\u4e00-\u9fa5]")
# 老陈/小林/阿黄 这类称谓型人名(只取两字,避免贪婪吞掉后续动词)
NAME_X_RE = re.compile(rf"[老小阿][\u4e00-\u9fa5]")
# 书名号/引号中的专名(物品、功法、地名候选)
QUOTED_RE = re.compile(r"[「“【《]([^「」“”【】《》]{1,12})[」”】》]")

# 伏笔信号词(出现即建倒查条目)
FORESHADOW_WORDS = [
    "伏笔", "暗自", "偷偷", "暗中", "悄悄", "殊不知",
    "却没有注意到", "没有注意到", "并未察觉", "不为人知",
]

# 3 字人名候选的尾字黑名单:过滤 "林凡说/陈默笑" 这类 "人名+动词" 误拼
NAME3_TRAILING_NOISE = set(
    "说想看走道来到去的是了有着在和也被把就对不中上都便才又再刚正在从向打问喊叫笑哭点头摇手开合站坐"
)
NAME_STOPWORDS = {"什么", "这个", "那个", "自己", "他们", "她们", "没有", "不是", "一下", "一声"}


def _clean(s: str) -> str:
    """去掉空白(中文正文空白无信息量),便于统一长度与去重。"""
    return re.sub(r"\s+", "", s)


def _match_facts(text: str) -> list:
    """共享内核:对单章文本跑四类规则,返回【无章号】的事实记录列表。

    CLI(run → extract_facts_for_chapter)与 Web 白名单纯函数(extract_facts)
    共用这一套正则/句子切分/摘句截取口径,避免两份实现漂移。
    """
    # 预切句子(带位置),供匹配定位所属句
    spans = []
    for m in SENT_RE.finditer(text):
        body = _clean(m.group())
        if body:
            spans.append((m.start(), m.end(), body))

    def sentence_of(pos: int):
        for start, end, body in spans:
            if start <= pos < end:
                return body, pos - start
        return None, 0

    facts = []
    for category in CATEGORY_ORDER:
        recorded = set()
        n_cat = 0
        for detail, pattern in CATEGORY_RULES[category]:
            if n_cat >= MAX_FACTS_PER_CATEGORY_PER_CHAPTER:
                break
            for m in pattern.finditer(text):
                if n_cat >= MAX_FACTS_PER_CATEGORY_PER_CHAPTER:
                    break
                body, offset = sentence_of(m.start())
                if not body or TITLE_LINE_RE.match(body):
                    continue  # 章节标题行不是事实
                win_start = max(0, offset - CONTEXT_BEFORE)
                excerpt = body[win_start:win_start + MAX_TEXT_LEN]
                if excerpt in recorded:
                    continue
                recorded.add(excerpt)
                n_cat += 1
                facts.append({
                    "category": category,
                    "text": excerpt,
                    "detail": detail,
                })
    return facts


def extract_facts_for_chapter(chapter_no: int, text: str) -> list:
    """对单章文本做启发式提取,返回该章的 facts 列表(按 category 顺序)。"""
    return [{"chapter": chapter_no, **f} for f in _match_facts(text)]


def extract_topics(chapter_texts: list, keep_total: bool = False) -> list:
    """从多章文本建主题倒查索引:人名/专名/伏笔词 → 出现章号列表。

    注意:这是辅助倒查,不是完备实体识别——高频、以姓氏开头的人名与
    引号专名才会入选;召回不足的部分由核对者/AI 补漏。

    keep_total: 内部开关。True 时把排序用的总次数以 "count" 键保留
    (供 Web 纯函数 extract_facts 做章内主题展示);默认 False,保持
    facts_index.json 的既有输出一字不变。
    """
    stats = {}  # term -> {"kind": str, "per_chapter": {no: count}}

    def record(term, kind, no, n):
        if n <= 0 or not term:
            return
        entry = stats.setdefault(term, {"kind": kind, "per_chapter": {}})
        entry["per_chapter"][no] = entry["per_chapter"].get(no, 0) + n

    for no, text in chapter_texts:
        for pattern, kind in ((NAME_3_RE, "name3"), (NAME_2_RE, "name2"), (NAME_X_RE, "name2")):
            for m in pattern.finditer(text):
                record(m.group(0), kind, no, 1)
        for m in QUOTED_RE.finditer(text):
            record(m.group(1).strip(), "quoted", no, 1)
        for word in FORESHADOW_WORDS:
            record(f"伏笔词·{word}", "foreshadow", no, text.count(word))

    topics = []
    for term, entry in stats.items():
        kind, per_ch = entry["kind"], entry["per_chapter"]
        total = sum(per_ch.values())
        if kind in ("name2", "name3"):
            # 人名候选:全书至少出现 3 次才算"重复出现"
            if total < 3 or term in NAME_STOPWORDS:
                continue
            if kind == "name3" and term[-1] in NAME3_TRAILING_NOISE:
                continue  # 大概率是 "人名+动词" 误拼
        elif kind == "quoted":
            # 物品/功法专名:至少出现 2 次且有长度
            if total < 2 or len(term) < 2:
                continue
        # foreshadow 词出现 1 次即收录(伏笔本就稀疏)
        chapters = sorted(per_ch)
        topics.append({
            "term": term,
            "chapters": chapters,
            "first_chapter": chapters[0],
            "_total": total,
        })

    topics.sort(key=lambda t: (-t["_total"], t["term"]))
    for t in topics:
        if keep_total:
            t["count"] = t.pop("_total")
        else:
            del t["_total"]  # 内部排序字段,不进产物
    return topics


def _empty_facts_result() -> dict:
    """extract_facts 的空结构(空输入/异常兜底共用,保证五个键永远齐全)。"""
    out = {f"facts_{cat}": [] for cat in CATEGORY_ORDER}
    out["topics"] = []
    return out


def extract_facts(text: str) -> dict:
    """Web 白名单纯函数(skilltools.py WHITELIST,chapter 粒度):单章 → 事实/主题索引。

    skilltools 对正文章节逐章调用本函数(输入规模由 MAX_CHAPTERS /
    MAX_CHAPTER_CHARS 兜住),返回值由 skilltools._fmt_facts 汇总成
    「服务端工具输出·事实索引」文本块注入 prompt。章号由调用方提供,
    故结果不含 chapter 字段;skilltools 的调用语义允许 chapter 粒度
    返回 dict(格式化函数只按已知键取值),此为该粒度的适配口径。

    输入: text —— 单章正文纯文本(典型几千~上万字)。
          非 str / 空白 / 内部异常一律返回空结构,绝不抛异常。

    返回(键名与 facts_index.json 的 category 口径一一对应):
        {
          "facts_numeric":  [{"category": "numeric",  "text": "<≤60字摘句>", "detail": "<命中规则>"}, ...],
          "facts_temporal": [{"category": "temporal", ...}, ...],
          "facts_entity":   [{"category": "entity",   ...}, ...],
          "facts_state":    [{"category": "state",    ...}, ...],
          "topics":         [{"term": "<人名/引号专名/伏笔词>", "chapters": [1],
                              "first_chapter": 1, "count": <本章出现次数>}, ...]
        }

    口径说明(facts_* 与 CLI 产物同源——共用 _match_facts 同一套规则):
        - numeric/temporal 句式覆盖较全,可直接作事实清单雏形;
        - entity/state 刻意保守(宁缺勿滥),完备性由 AI 通读补漏;
        - topics 复用 extract_topics 全书阈值(单章口径:人名候选≥3次、
          引号专名≥2次、伏笔词≥1次),chapters/first_chapter 为占位章号 1,
          承接方按 "term + count" 解读即可。
    """
    out = _empty_facts_result()
    try:
        if not isinstance(text, str) or not text.strip():
            return out
        for f in _match_facts(text):
            out[f"facts_{f['category']}"].append(f)
        out["topics"] = extract_topics([(1, text)], keep_total=True)
        return out
    except Exception:  # Web 工具失败必须兜底为空结构,绝不向上抛
        return out


def _load_index(workdir: Path):
    idx_path = workdir / INDEX_NAME
    if not idx_path.is_file():
        raise FactExtractorError(
            f"缺少 {INDEX_NAME}:目录 {workdir} 下没有章节索引。\n"
            f"请先运行 chapter_splitter.py 生成索引与单章 txt,再运行本脚本。"
        )
    try:
        data = json.loads(idx_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        raise FactExtractorError(f"{INDEX_NAME} 读取/解析失败: {e}")
    chapters = data.get("chapters") if isinstance(data, dict) else None
    if not isinstance(chapters, list) or not chapters:
        raise FactExtractorError(f"{INDEX_NAME} 中没有可用的 chapters 列表,无法建立索引。")
    return chapters


def _find_chapter_file(workdir: Path, no: int) -> Path:
    """按前缀 NNNN_ 定位单章文件(不依赖标题转义细节,兼容 splitter 命名)。"""
    matches = sorted(workdir.glob(f"{no:04d}_*.txt"))
    if not matches:
        raise FactExtractorError(
            f"章节文件缺失:在 {workdir} 下找不到 {no:04d}_*.txt"
            f"(chapter_index.json 中声明的第 {no} 章)。\n"
            f"请确认 chapter_splitter.py 已写出全部单章文件(勿用 --list-only)。"
        )
    return matches[0]


def run(workdir: str) -> dict:
    """主流程:校验 → 逐章提取 → 建主题索引 → 写 facts_index.json。"""
    d = Path(workdir)
    if not d.is_dir():
        raise FactExtractorError(f"工作目录不存在或不是目录: {d}")

    raw_chapters = _load_index(d)
    facts = []
    chapter_texts = []  # [(no, text)] 仅非空章
    empty_skipped = 0

    def chapter_key(c):
        try:
            return int(c.get("no", 0))
        except (TypeError, ValueError):
            raise FactExtractorError(f"{INDEX_NAME} 中存在无法解析的章号字段 no={c.get('no')!r}")

    for c in sorted(raw_chapters, key=chapter_key):
        try:
            no = int(c["no"])
        except (KeyError, TypeError, ValueError):
            raise FactExtractorError(f"{INDEX_NAME} 中某章节条目缺少有效的 no 字段: {c!r}")
        path = _find_chapter_file(d, no)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            raise FactExtractorError(f"读取章节文件失败: {path} ({e})")
        if not text.strip():
            empty_skipped += 1
            continue  # 空章优雅跳过
        chapter_texts.append((no, text))
        facts.extend(extract_facts_for_chapter(no, text))

    facts.sort(key=lambda f: f["chapter"])  # 输出按章号排序
    topics = extract_topics(chapter_texts)

    out_path = d / OUTPUT_NAME
    try:
        out_path.write_text(
            json.dumps({"facts": facts, "topics": topics}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        raise FactExtractorError(f"写出 {OUTPUT_NAME} 失败: {e}")

    dist = {cat: sum(1 for f in facts if f["category"] == cat) for cat in CATEGORY_ORDER}
    return {
        "chapters": len(chapter_texts),
        "empty_skipped": empty_skipped,
        "facts": facts,
        "topics": topics,
        "dist": dist,
        "out_path": out_path,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="为拆书工作目录生成事实/主题索引 facts_index.json(辅助索引,完备性靠核对者补漏)")
    ap.add_argument("workdir", help="工作目录:内含 chapter_index.json 与单章 txt(chapter_splitter.py 的输出目录)")
    args = ap.parse_args(argv)

    try:
        r = run(args.workdir)
    except FactExtractorError as e:
        print(f"[fact_extractor] 错误: {e}", file=sys.stderr)
        return 2

    dist = r["dist"]
    print(
        f"共索引 {r['chapters']} 章(空章跳过 {r['empty_skipped']}) | "
        f"facts {len(r['facts'])} 条(numeric={dist['numeric']} temporal={dist['temporal']} "
        f"entity={dist['entity']} state={dist['state']}) | "
        f"topics {len(r['topics'])} 条"
    )
    print(f"输出: {r['out_path']}")
    print("提示: 本索引只保证'让事实碰面',完备性请按 consistency-check.md 第一步补漏。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
