#!/usr/bin/env python3
"""validate_skillcard.py —— 北斗技能卡结构校验器。

设计原则：结构损伤自动拦截；内容质量仍靠评审。
本脚本只读校验技能卡目录（SKILL.md / references/ / assets/report-template.md /
scripts/），绝不修改任何技能卡文件。零第三方依赖（纯标准库）。

用法:
    python3 validate_skillcard.py [--skill-dir <技能卡目录>]

缺省 --skill-dir 为本脚本所在目录上一级，即其所属技能卡根目录
（novel-deconstruction）。
退出码: 0 = 全部通过; 1 = 存在 FAIL; 2 = --skill-dir 不存在/不可用。

检查项（编号固定，便于引用）:
  1. frontmatter 完整性
  2. 路由引用存在性（SKILL.md 提到的 references/<file>.md 必须存在）
  3. references 无孤儿（references/*.md 必须被 SKILL.md 至少引用一次）
  4. 四件套体例完整（Key Questions / 警示信号 / Agent 硬指令；豁免见下）
  5. SKILL.md 步骤号合法（### 第 X 步 严格递增无重复）
  6. report-template.md 大节号连续（## 一、… 递增；### n.m 的 n 须匹配
     其前方最近的中文大节序数——拦下"七、下挂 8.2"这类历史错号）
  7. 脚本引用存在性（SKILL.md 提到的 scripts/<file>.py 必须存在）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 检查项 4 的豁免清单（文件名 → 原因）：
# - consistency-check.md: 由 T1 口径维护，本就无四件套体例。
# 豁免原则：仅豁免体例上明确不适用四件套的文件；其余文件须通过校验
# （syntopical-mode.md 已补齐四件套并在 2026-09 移出本清单）。
EXEMPT_FOUR_PART = {"consistency-check.md"}

FOUR_PART_KEYWORDS = ("Key Questions", "警示信号", "Agent 硬指令")

RE_STEP = re.compile(r"^###\s*第\s*(\d+(?:\.\d+)?)\s*步", re.MULTILINE)
RE_CN_SECTION = re.compile(r"^##\s*([一二三四五六七八九十]+)\s*、", re.MULTILINE)
RE_HEADING_LINE = re.compile(r"^(#+)\s*(.*)$")
RE_REF_LINK = re.compile(r"references/([A-Za-z0-9][A-Za-z0-9._-]*\.md)")
RE_SCRIPT_LINK = re.compile(r"scripts/([A-Za-z0-9][A-Za-z0-9._-]*\.py)")

CN_DIGIT = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
            "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def parse_cn_numeral(text: str):
    """解析中文数字（支持 一~二十，超出该范围亦尽力）。无法解析返回 None。

    >>> parse_cn_numeral("七")
    7
    >>> parse_cn_numeral("十")
    10
    >>> parse_cn_numeral("十二")
    12
    >>> parse_cn_numeral("二十")
    20
    """
    text = text.strip()
    if not text:
        return None
    if "十" in text:
        left, _, right = text.partition("十")
        tens = CN_DIGIT[left] if left else 1
        if left and left not in CN_DIGIT:
            return None
        if right:
            if right not in CN_DIGIT:
                return None
            ones = CN_DIGIT[right]
        else:
            ones = 0
        return tens * 10 + ones
    if len(text) == 1 and text in CN_DIGIT:
        return CN_DIGIT[text]
    if all(ch in CN_DIGIT for ch in text):  # 如 "二一" 这类罕见写法按位数拼
        value = 0
        for ch in text:
            value = value * 10 + CN_DIGIT[ch]
        return value
    return None


def check_frontmatter(skill_dir: Path) -> list[str]:
    """检查项 1：SKILL.md frontmatter 完整性（行级检查，不做 YAML 解析）。"""
    problems: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return ["缺少 SKILL.md 文件"]
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ["首行不是 '---'，缺少 frontmatter 围栏开头"]
    fence_count = sum(1 for ln in lines if ln.strip() == "---")
    if fence_count < 2:
        problems.append(f"frontmatter 围栏不足两道 '---'（发现 {fence_count} 道）")
    block = []
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        block.append(ln)
    for field in ("name:", "description:"):
        hit = [ln for ln in block
               if ln.lstrip().startswith(field) and ln.split(":", 1)[1].strip()]
        if not hit:
            problems.append(f"frontmatter 内缺少非空 {field} 行")
    return problems


def check_reference_links(skill_dir: Path, skill_text: str) -> list[str]:
    """检查项 2：SKILL.md 引用的 references/<file>.md 都必须存在。"""
    refs_dir = skill_dir / "references"
    problems: list[str] = []
    for name in sorted(set(RE_REF_LINK.findall(skill_text))):
        if not (refs_dir / name).is_file():
            problems.append(f"路由引用 404: references/{name}（SKILL.md 引用但文件不存在）")
    return problems


def check_orphans(skill_dir: Path, skill_text: str) -> list[str]:
    """检查项 3：references/ 下每个 .md 都须被 SKILL.md 至少引用一次。"""
    refs_dir = skill_dir / "references"
    if not refs_dir.is_dir():
        return ["references/ 目录不存在"]
    cited = set(RE_REF_LINK.findall(skill_text))
    problems: list[str] = []
    for path in sorted(refs_dir.glob("*.md")):
        if path.name not in cited:
            problems.append(
                f"孤儿 reference: references/{path.name} 存在于目录但 SKILL.md 从未引用（加文件记得挂路由）")
    return problems


def check_four_part(skill_dir: Path) -> list[str]:
    """检查项 4：references/*.md 应含 Key Questions / 警示信号 / Agent 硬指令 三节。"""
    refs_dir = skill_dir / "references"
    if not refs_dir.is_dir():
        return ["references/ 目录不存在"]
    problems: list[str] = []
    for path in sorted(refs_dir.glob("*.md")):
        if path.name in EXEMPT_FOUR_PART:
            continue
        text = path.read_text(encoding="utf-8")
        # 关键词必须出现在节标题行（^#+ …）上：只有顶部目录里出现不算数，
        # 否则删节头不删目录的“假四件套”会被目录行救走。
        missing = [kw for kw in FOUR_PART_KEYWORDS
                   if not re.search(rf"^#+.*{re.escape(kw)}", text, re.MULTILINE)]
        if missing:
            problems.append(
                f"references/{path.name} 缺少四件套节: {'、'.join(missing)}")
    return problems


def check_steps(skill_text: str) -> list[str]:
    """检查项 5：'### 第 X 步' 序列必须按数值严格递增且无重复。"""
    nums = [float(m) for m in RE_STEP.findall(skill_text)]
    problems: list[str] = []
    if not nums:
        return ["未找到任何 '### 第 X 步' 标题"]
    for prev, cur in zip(nums, nums[1:]):
        if cur <= prev:
            problems.append(
                f"步骤号乱序或重复: 第 {prev:g} 步之后出现 第 {cur:g} 步（应严格递增）")
    return problems


def check_template(skill_dir: Path) -> list[str]:
    """检查项 6：report-template.md 中文大节号递增无重复，且 ### n.m 的 n
    必须等于其前方最近的 '## X、' 的阿拉伯序数。"""
    tpl = skill_dir / "assets" / "report-template.md"
    if not tpl.is_file():
        return ["缺少 assets/report-template.md"]
    text = tpl.read_text(encoding="utf-8")
    problems: list[str] = []
    section_values: list[int] = []
    last_section: int | None = None  # None = 尚未出现任何中文大节
    for line in text.splitlines():
        m_cn = re.match(r"^##\s*(\S+?)、", line)
        if m_cn:
            value = parse_cn_numeral(m_cn.group(1))
            if value is None:
                problems.append(f"无法解析大节号 '## {m_cn.group(1)}、'")
            else:
                if section_values and value <= section_values[-1]:
                    problems.append(
                        f"大节号乱序或重复: '## {m_cn.group(1)}、'（序数 {value}"
                        f" 出现在序数 {section_values[-1]} 之后，应严格递增）")
                section_values.append(value)
                last_section = value
            continue
        m_sub = re.match(r"^###\s*(\d+)\.(\d+)", line)
        if m_sub:
            n = int(m_sub.group(1))
            if last_section is None:
                problems.append(
                    f"小节 '### {m_sub.group(1)}.{m_sub.group(2)}' 出现在任何 "
                    f"'## X、' 大节之前，无归属大节")
            elif n != last_section:
                cn = "一二三四五六七八九十"[last_section - 1] if 1 <= last_section <= 10 else str(last_section)
                problems.append(
                    f"小节错号: '### {m_sub.group(1)}.{m_sub.group(2)}' 出现在 "
                    f"'{cn}、' 大节之下，首位 {n} 与大节序数 {last_section} 不符")
    return problems


def check_script_links(skill_dir: Path, skill_text: str) -> list[str]:
    """检查项 7：SKILL.md 提到的 scripts/<file>.py 都必须存在。"""
    scripts_dir = skill_dir / "scripts"
    problems: list[str] = []
    for name in sorted(set(RE_SCRIPT_LINK.findall(skill_text))):
        if not (scripts_dir / name).is_file():
            problems.append(f"脚本引用 404: scripts/{name}（SKILL.md 提到但文件不存在）")
    return problems


CHECKS = [
    ("frontmatter 完整性", lambda d, t: check_frontmatter(d)),
    ("路由引用存在性", lambda d, t: check_reference_links(d, t)),
    ("references 无孤儿", lambda d, t: check_orphans(d, t)),
    ("四件套体例完整", lambda d, t: check_four_part(d)),
    ("SKILL.md 步骤号合法", lambda d, t: check_steps(t)),
    ("report-template.md 大节号连续", lambda d, t: check_template(d)),
    ("脚本引用存在性", lambda d, t: check_script_links(d, t)),
]


def validate(skill_dir: Path) -> list[tuple[str, list[str]]]:
    """执行全部检查，按检查项序返回 [(检查项名, 问题列表), ...]。"""
    skill_md = skill_dir / "SKILL.md"
    skill_text = skill_md.read_text(encoding="utf-8") if skill_md.is_file() else ""
    return [(label, fn(skill_dir, skill_text)) for label, fn in CHECKS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="北斗技能卡结构校验器（只读，零依赖）")
    parser.add_argument("--skill-dir", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="技能卡目录（缺省为本脚本所属技能卡根目录）")
    args = parser.parse_args(argv)
    skill_dir: Path = args.skill_dir
    if not skill_dir.is_dir():
        print(f"错误: skill 目录不存在或不是目录: {skill_dir}", file=sys.stderr)
        return 2
    results = validate(skill_dir)
    failed = 0
    for idx, (label, problems) in enumerate(results, start=1):
        if problems:
            failed += 1
            print(f"❌ 检查{idx} [{label}]")
            for p in problems:
                print(f"    - {p}")
        else:
            print(f"✅ 检查{idx} [{label}] 通过")
    passed = len(results) - failed
    print(f"PASS: {passed} checks, FAIL: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
