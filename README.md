# 小说创作辅助技能卡组（Novel Skill Cards）

面向中文网文与长篇小说创作的技能卡仓库，提供两种接入形态：

- **11 张独立 Agent Skills 技能卡**：适合支持 `SKILL.md + scripts/ + references/ + assets/` 的系统，可按需插拔。
- **2 套平台无关通用提示词**：包含 AI 自动写作总控与 14 张功能卡、人工稿件核对总控与 15 张检查卡，适合其他智能体和工作流系统。

## 选择哪个版本

| 需求 | 推荐版本 | 入口 |
|---|---|---|
| 单项深度处理，如大纲、设定、文风、拆书 | 独立 Agent Skills 专精卡 | [`skills/`](skills/) |
| 自动连续写作，需要状态回写和质量门禁 | AI 自动写作通用版 | [`universal/ai-auto-writing-cards.zh-CN.md`](universal/ai-auto-writing-cards.zh-CN.md) |
| 人工写稿后检查矛盾、逻辑、节奏和表达 | 人工写作核对通用版 | [`universal/human-writing-audit-cards.zh-CN.md`](universal/human-writing-audit-cards.zh-CN.md) |
| 新旧卡重叠，不确定调用哪张 | 路由与职责说明 | [`universal/routing.md`](universal/routing.md) |
| 自有平台需要自动读取输入、输出和依赖 | 机器可读清单 | [`universal/manifest.json`](universal/manifest.json) |

## 独立 Agent Skills 技能卡

每张卡为一个独立文件夹，零互相依赖，可按需插拔组合。

### 创作生产（写前／写中）

| 技能卡 | 用途 |
|---|---|
| `outline-architect` | 大纲架构师：主线／升级线／伏笔台账三线合一，卷结构＋章级细纲＋爽点排期 |
| `worldbuilding-bible` | 设定集构建器：力量体系、势力、地理、经济，产出带“可证伪规则”的世界观圣经 |
| `opening-crafter` | 开篇打磨器：黄金三章设计与诊断，“立人／立困／立钩”硬框架验收 |
| `chapter-hook-crafter` | 章节卡点师：六大章末钩子类型，断点位置＋结尾改写＋兑现约束 |
| `name-forge` | 取名炉：人名／地名／功法／势力／法宝批量生成，附寓意与四重筛查 |
| `book-packager` | 文案包装卡：书名／简介／标签／章节名，按番茄／起点／晋江平台范式产出 |

### 诊断改稿（写后质检）

| 技能卡 | 用途 |
|---|---|
| `novel-consistency-checker` | 穿帮猎手：数值算术／设定口径／细节连续三层核对＋伏笔台账 |
| `webnovel-pace-analyzer` | 爽点节奏分析仪：逐章扫描钩子／爽点信号，定位爽点荒、铺垫过长和水文区 |
| `deai-rewrite` | 去 AI 味改写：AI 高频词词表＋千字频率阈值预警＋六类 AI 腔改写手册 |
| `style-fingerprint` | 文风指纹：句长／对话占比／高频词客观测量＋四层文风档案，用于续写对齐 |
| `novel-deconstruction` | 拆书：黄金三章／情节／人物／世界观／爽点五维拆解，输出结构化拆书报告 |

## 通用提示词套件

### AI 自动写作版

包含 A00 总控卡与 A01—A14 功能卡，覆盖任务解析、作品圣经、人物与声纹、分卷规划、章节任务、上下文装配、写前校验、伏笔与信息差、连续性、状态回写、质量门禁和定向修订。

适用于“规划—校验—正文生成—回写—审校—修订”的自动写作闭环。正文生成模块可接入任意模型。

### 人工写作检查核对版

包含 B00 总控卡与 B01—B15 检查卡，覆盖文本完整性、设定、人物、因果、时间线、空间、状态物品、伏笔、节奏、视角、对话、表达、事实、包装与发布风险。

默认只诊断、不改稿，输出带位置、依据、级别和置信度的核对报告。

### 配套资源

- [路由与职责说明](universal/routing.md)：避免新旧卡重复调用，明确深度规则归属。
- [机器可读清单](universal/manifest.json)：卡片输入、输出、依赖、权限和关联专精卡。
- [调用示例](universal/examples.md)：最小输入、调用方式和预期输出。
- [验收用例](universal/evaluation.md)：矛盾检出、误报控制、状态证据与回归测试。
- [变更记录](CHANGELOG.md)：版本和兼容性变化。

## 推荐流水线

### 独立专精卡

```text
worldbuilding-bible 建档 → outline-architect 排期 → opening-crafter 开篇
→ 正文写作（style-fingerprint 挂文风档案）→ chapter-hook-crafter 逐章卡点
→ 质检三连：novel-consistency-checker + webnovel-pace-analyzer + deai-rewrite
→ book-packager 上架包装 → novel-deconstruction 复盘同类作品
```

### 通用自动写作套件

```text
A01 任务解析 → A02/A03 建档 → A04 长篇规划
→ A05 章节任务 → A07 写前校验 → A06 上下文装配
→ 正文生成 → A10 状态回写 → A11/A12 审校
→ A13 定向修订与复检 → 章节归档
```

## 安装使用

### OpenClaw

将所需技能卡文件夹放入 `~/.openclaw/workspace/skills/`，或执行 `openclaw skills install <技能卡目录>`。各卡 `description` 已内置中文触发语，Agent 可自动路由。

### Kimi／其他 AgentSkills 系统

将技能卡文件夹放入系统的技能目录即可；`.skill` 后缀的打包文件可直接导入支持该格式的系统。

### 其他智能体或工作流系统

1. 复制 `universal/` 中对应套件的整份提示词，或按编号复制单张卡。
2. 将 `{{变量}}` 配置为实际输入字段；必需输入、可选输入和权限以 `manifest.json` 为准。
3. 需要自动路由时读取 `manifest.json`，不要依赖对自然语言文档的临时解析。
4. 按 `routing.md` 决定调用通用卡还是已有专精卡，避免重复执行同一检查。
5. 使用 `examples.md` 做接入冒烟测试，使用 `evaluation.md` 做修改后的回归验收。

### 自有平台接入独立 Agent Skills

1. 读取每张卡 `SKILL.md` 的 YAML frontmatter（`name + description`）作为展示与路由依据。
2. 用户启用某张卡时，将 `SKILL.md` 正文注入 prompt。
3. 若平台支持执行环境，暴露该卡的 `scripts/` 目录；不支持则退化为指令中的人工步骤。
4. 卡内引用资源时使用 `{baseDir}` 占位符指代该卡的安装目录。

## 目录结构

```text
skills/                       # 11 张独立 Agent Skills 专精卡
universal/
├── ai-auto-writing-cards.zh-CN.md
├── human-writing-audit-cards.zh-CN.md
├── manifest.json             # 机器可读卡片清单
├── routing.md                # 新旧卡职责与调用路由
├── examples.md               # 最小调用示例
└── evaluation.md             # 验收用例与回归标准
CHANGELOG.md
```

## 许可

仅供学习交流使用。许可条款保持仓库原有约定；如需扩大使用、修改或分发权限，应由仓库所有者另行明确。
