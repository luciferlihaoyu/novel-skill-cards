# 小说创作辅助技能卡组（Novel Skill Cards）

11 张即插即用的 **Agent Skills** 技能卡，专为中文网文/长篇小说创作设计。兼容 OpenClaw、Kimi 及所有遵循 AgentSkills 规范（`SKILL.md` + `scripts/` + `references/` + `assets/`）的 AI Agent 系统。

每张卡 = 一个独立文件夹，零互相依赖，可按需插拔组合。

## 技能卡总览

### 创作生产（写前 / 写中）

| 技能卡 | 用途 |
|---|---|
| `outline-architect` | 大纲架构师：主线/升级线/伏笔台账三线合一，卷结构 + 章级细纲 + 爽点排期 |
| `worldbuilding-bible` | 设定集构建器：力量体系、势力、地理、经济，产出带"可证伪规则"的世界观圣经 |
| `opening-crafter` | 开篇打磨器：黄金三章设计与诊断，"立人/立困/立钩"硬框架验收 |
| `chapter-hook-crafter` | 章节卡点师：六大章末钩子类型，断点位置 + 结尾改写 + 兑现约束 |
| `name-forge` | 取名炉：人名/地名/功法/势力/法宝批量生成，附寓意与四重筛查 |
| `book-packager` | 文案包装卡：书名/简介/标签/章节名，按番茄/起点/晋江平台范式产出 |

### 诊断改稿（写后质检）

| 技能卡 | 用途 |
|---|---|
| `novel-consistency-checker` | 穿帮猎手：数值算术/设定口径/细节连续三层核对 + 伏笔台账（含章节切分与锚点检索脚本） |
| `webnovel-pace-analyzer` | 爽点节奏分析仪：逐章扫描钩子/爽点信号，定位爽点荒、铺垫过长、水文区（含扫描脚本） |
| `deai-rewrite` | 去AI味改写：AI高频词词表 + 千字频率阈值预警 + 六类AI腔改写手册（含扫描脚本） |
| `style-fingerprint` | 文风指纹：句长/对话占比/高频词客观测量 + 四层文风档案，用于续写对齐（含测量脚本） |
| `novel-deconstruction` | 拆书：黄金三章/情节/人物/世界观/爽点五维拆解 + 强制一致性核对，输出结构化拆书报告 |

## 推荐流水线

```
worldbuilding-bible 建档 → outline-architect 排期 → opening-crafter 开篇
→ 正文写作（style-fingerprint 挂文风档案）→ chapter-hook-crafter 逐章卡点
→ 质检三连：novel-consistency-checker + webnovel-pace-analyzer + deai-rewrite
→ book-packager 上架包装 → novel-deconstruction 复盘同类爆款
```

## 安装使用

### OpenClaw
将所需技能卡文件夹放入 `~/.openclaw/workspace/skills/`，或执行 `openclaw skills install <技能卡目录>`。各卡 `description` 已内置中文触发语，Agent 可自动路由。

### Kimi / 其他 AgentSkills 系统
将技能卡文件夹放入系统的技能目录即可；`.skill` 后缀的打包文件（zip 格式）可直接导入支持该格式的系统。

### 自有平台接入
1. 读取每张卡 `SKILL.md` 的 YAML frontmatter（`name` + `description`）作为卡片展示与路由依据
2. 用户启用某张卡时，将 `SKILL.md` 正文注入 prompt
3. 若平台支持执行环境，暴露该卡的 `scripts/` 目录（全部为纯 Python 标准库脚本，零第三方依赖）；不支持则脚本环节自动退化为指令中的人工步骤
4. 卡内引用资源时使用 `{baseDir}` 占位符指代该卡的安装目录

## 目录结构

```
skills/
├── outline-architect/        # SKILL.md + references/
├── worldbuilding-bible/      # SKILL.md + assets/（设定集模板）
├── opening-crafter/          # SKILL.md + references/
├── chapter-hook-crafter/     # SKILL.md + references/（钩子类型库）
├── name-forge/               # SKILL.md + references/（分题材命名配方）
├── book-packager/            # SKILL.md + references/（平台文案范式）
├── novel-consistency-checker/# SKILL.md + scripts/×2 + references/
├── webnovel-pace-analyzer/   # SKILL.md + scripts/ + references/
├── deai-rewrite/             # SKILL.md + scripts/ + references/（AI词表）
├── style-fingerprint/        # SKILL.md + scripts/
└── novel-deconstruction/     # SKILL.md + scripts/ + references/×5 + assets/
```

## 许可

仅供学习交流使用。
