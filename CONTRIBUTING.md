# 贡献指南

感谢你对《Easy Data x AI》课程的关注！🙏

这是一门面向所有 AI 爱好者的「Data 与 AI」入门教程，目前处于 **Alpha 内测阶段**，正在邀请社区一起把课程打磨完善。无论是修正一个错别字、补充一段实验、还是认领一节扩展课程，每一份贡献都很有价值。

> 本课程由 [Datawhale](https://github.com/datawhalechina) 与 [OceanBase 社区](https://open.oceanbase.com/) 联合共建。

---

## 一、欢迎的贡献类型

| 类型 | 说明 | 是否需先开 Issue |
| --- | --- | --- |
| **错别字 / 标点修正** | 直接提 PR | 否 |
| **表述改善** | 措辞不清、语句不通、逻辑跳跃 | 否 |
| **排版修复** | 代码块格式、列表缩进、图片说明 | 否 |
| **事实性勘误** | 技术描述有误（请附参考链接） | 否 |
| **完善已有章节** | 对 P / D / X 已有内容提出修正或补充 | 建议（先说明范围） |
| **完善产业应用篇** | 认领 `docs/industry/` 下的 I1–I8 共建任务（见第四节列表 D） | **是**（在对应 Issue 留言认领） |
| **新增扩展章节** | 在 `docs/extra/` 下提出新的扩展方向 | **是**（先开 Issue 对齐方向） |
| **工程 / 基建改进** | CI、依赖、示例代码 bug（见第四节列表 C） | 否 |
| **问题反馈 / 讨论** | 知识点不清楚、想提建议 | 通过 Issue |

---

## 二、快速上手

### 1. Fork 并克隆仓库

```bash
git clone https://github.com/<your-username>/easy-data-x-ai.git
cd easy-data-x-ai
```

### 2. 本地预览课程文档

课程站点基于 **VitePress** 构建：

```bash
npm install
npm run docs:dev
```

开发服务器启动后，按提示访问本地地址（默认 `http://localhost:5173`），修改 Markdown 会自动热重载。

### 3. 找到要修改的文件

课程正文都在 `docs/` 目录下，按篇章组织：

```
docs/
├── base_knowledge/   # 公共基础篇 F0–F2
├── pm/               # 道篇 P1–P5（产品 / 心法）
├── dev/              # 术篇 D1–D5（开发 / 功法）
├── industry/         # 产业应用篇 I1–I8（当前开放共建）
└── extra/            # 扩展篇 X1–X6（新的扩展方向先开 Issue）
```

配套示例代码在 `code/` 目录，按章节分文件夹（`code/D1/`、`code/D2/` …）。

### 4. 提交 PR

```bash
git checkout -b fix/typo-p3
git add docs/pm/"P3 课程稿：Agent 记忆系统设计.md"
git commit -m "fix: 修正 P3 章节若干错别字"
git push origin fix/typo-p3
```

PR 标题建议遵循如下格式：

```
fix:  修正 <章节> <简要说明>      # 错别字、勘误
docs: 完善 <章节> <简要说明>      # 内容补充
docs: 完善产业应用篇 <I编号> <标题> # Industry Practice
feat: 新增扩展篇 <X编号> <标题>   # Extra-Chapter
chore: <工程/基建说明>            # CI、依赖、脚本
```

> ✅ **认领任务的同学**：请在 PR 描述里注明认领的任务编号（如「认领 [#21](https://github.com/datawhalechina/easy-data-x-ai/issues/21)」），方便归档统计。

---

## 三、Markdown 写作规范

- 中文与英文、数字之间加空格：`LangChain 是一个框架` ✓，`LangChain是一个框架` ✗
- 代码、命令、变量名用反引号包裹：`` `HYBRID_SEARCH()` ``
- 专有名词保持原文大小写：`OceanBase`、`seekdb`、`PowerMem`、`LangChain`、`RAGAS`
- 图片放在 `docs/public/images/` 下，正文用相对路径引用
- 涉及可运行代码的章节，请把示例同步放到 `code/` 对应目录，并保证能跑通

---

## 四、共建任务列表（认领制）

> 已完成的任务保留在列表 A–C 中作为历史记录；当前可认领的新任务见列表 D。你可以在感兴趣的 Issue 下留言认领，完成后提 PR。
> 课程中涉及 LangChain 相关内容，也欢迎 LangChain 社区的同学一起参与。
> **完成一条任务即可提交一个 PR。**

### 难度说明

| 级别 | 适合人群 | 典型任务 |
| --- | --- | --- |
| **L1** | 第一次参与共建，有写作能力即可 | 补充文档说明、衔接段落、设计规范 |
| **L2** | 能基于课程内容做实验分析 | 对比实验、选型指南、成本分析 |
| **L3** | 有工程实现能力，能写可运行代码 | 完整代码实现、benchmark 复现、MCP 实战 |

### 列表 A：已完成 · 完善已有章节（P3–P5 / D2–D5）

| # | 章节 | 待完善的点 | 共建方向 | 难度 | 状态 |
| --- | --- | --- | --- | --- | --- |
| [#19](https://github.com/datawhalechina/easy-data-x-ai/issues/19) | **P3** | 记忆时效性管理只提了难点，没有给解法 | 补充「记忆衰减策略」：结合艾宾浩斯曲线，给出遗忘分数计算 + 主动淘汰的具体方案 | L2 | ✅ 已完成 |
| [#20](https://github.com/datawhalechina/easy-data-x-ai/issues/20) | **P3** | 多 Agent 共享记忆的边界问题未展开 | 补充「多 Agent 记忆隔离与共享」：何时隔离、何时共享、如何设计命名空间 | L2 | ✅ 已完成 |
| [#21](https://github.com/datawhalechina/easy-data-x-ai/issues/21) | **P3** | 记忆冲突处理（新旧信息矛盾）完全缺失 | 补充「记忆冲突解决策略」：时间戳优先 / 置信度加权 / 人工介入三种模式对比 | L2 | ✅ 已完成 |
| [#22](https://github.com/datawhalechina/easy-data-x-ai/issues/22) | **P4** | Skill 全量注入上下文导致爆炸，课程没有给解法 | 补充「通过 seekdb 结构化管理 Skill」：把 Skill 存入数据库，按需语义检索加载，对比全量注入 vs 按需加载的 Token 占用 | L3 | ✅ 已完成 |
| [#23](https://github.com/datawhalechina/easy-data-x-ai/issues/23) | **P4** | Skill 标准化的具体原则没有展开 | 补充「Skill 设计规范」：命名、描述、参数、示例的标准格式，参考 MCP Tool 规范 | L1 | ✅ 已完成 |
| [#24](https://github.com/datawhalechina/easy-data-x-ai/issues/24) | **P4 → D5** | P4 讲了 Skill 分割问题，但没有为 D5 的 MCP 做铺垫，两篇脱节 | 在 P4 结尾补「从 Skill 到 MCP：为什么需要标准化协议」，作为 D5 的引入 | L1 | ✅ 已完成 |
| [#25](https://github.com/datawhalechina/easy-data-x-ai/issues/25) | **P5** | 三层度量框架讲了指标，但没有说怎么落地监测 | 补充「度量框架实施指南」：用 LangSmith / Prometheus 搭一套最小可用监控 dashboard | L3 | ✅ 已完成 |
| [#26](https://github.com/datawhalechina/easy-data-x-ai/issues/26) | **P5** | 缺少成本–收益分析 | 补充「AI Agent ROI 计算模型」：数据层 / 模型层 / 业务层的投入产出估算框架 | L2 | ✅ 已完成 |
| [#27](https://github.com/datawhalechina/easy-data-x-ai/issues/27) | **D2** | 向量化模型选型只推荐了 bge-m3，没有讲怎么选 | 补充「Embedding 模型选型指南」：中英文、多模态、成本、延迟四个维度横评 | L2 | ✅ 已完成 |
| [#28](https://github.com/datawhalechina/easy-data-x-ai/issues/28) | **D2** | Chunking 策略只讲了基础分块，高级技巧缺失 | 补充「高级 Chunking 策略」：语义分块、动态 overlap、父子 chunk 三种策略对比实验 | L3 | ✅ 已完成 |
| [#29](https://github.com/datawhalechina/easy-data-x-ai/issues/29) | **D3** | 对比实验样本量太小，无统计显著性 | 扩充评测数据集，补充更多场景（多跳问题、时效性查询、模糊表达），重跑 RAGAS 对比 | L3 | ✅ 已完成 |
| [#30](https://github.com/datawhalechina/easy-data-x-ai/issues/30) | **D3** | P2 梳理的工程痛点在 D3 没有逐一给出解法 | 按 P2 痛点列表逐一补充对应代码实现（查询改写 / 自适应检索 / 答案验证等） | L3 | ✅ 已完成 |
| [#31](https://github.com/datawhalechina/easy-data-x-ai/issues/31) | **D3** | 缺检索延迟和成本数据 | 补充「混合检索 vs 纯向量」的延迟 / 成本 / 精度三角对比实验 | L2 | ✅ 已完成 |
| [#32](https://github.com/datawhalechina/easy-data-x-ai/issues/32) | **D4** | 记忆存储成本没有讨论 | 补充「长期记忆的存储成本控制」：压缩策略、冷热分层、定期清理的工程实践 | L2 | ✅ 已完成 |
| [#33](https://github.com/datawhalechina/easy-data-x-ai/issues/33) | **D4** | 多用户记忆隔离方案缺失 | 补充「多用户 / 多租户记忆隔离」：user_id 命名空间 + 权限校验的实现示例 | L3 | ✅ 已完成 |
| [#34](https://github.com/datawhalechina/easy-data-x-ai/issues/34) | **D5** | MCP 标准化几乎完全缺失（标题承诺但正文没展开） | 补充「MCP 实战」：从零实现一个 MCP Server，把 P4 设计的 Skill 发布成 MCP Tool，跑通 Claude / Cursor 调用 | L3 | ✅ 已完成 |
| [#35](https://github.com/datawhalechina/easy-data-x-ai/issues/35) | **D5** | 跨平台 Skill 互操作没有示例 | 补充「同一个 Skill 在 Claude Code / Cursor / Copilot 中的调用差异」对比 | L2 | ✅ 已完成 |

### 列表 B：已完成 · 扩展篇共建（Extra Chapter X1–X6）

> X1–X6 已经纳入 `docs/extra/` 目录，下表保留其历史共建入口。
>
> 新的扩展篇方向请先开 Issue 对齐内容大纲，避免与已有章节重复。

| # | 扩展课程标题 | 相关主题 | 共建入口 | 状态 |
| --- | --- | --- | --- | --- |
| **X1** | 探究 AI Agent 记忆系统：从遗忘曲线到永久记忆 | AI 记忆 | [#19](https://github.com/datawhalechina/easy-data-x-ai/issues/19) / [#20](https://github.com/datawhalechina/easy-data-x-ai/issues/20) / [#21](https://github.com/datawhalechina/easy-data-x-ai/issues/21) | ✅ 已完成 |
| **X2** | 多 Skill 给上下文工程带来的麻烦：如何应对 Agent「爆上下文」 | 多 Skill / 上下文工程 | [#22](https://github.com/datawhalechina/easy-data-x-ai/issues/22) / [#23](https://github.com/datawhalechina/easy-data-x-ai/issues/23) | ✅ 已完成 |
| **X3** | 从零到一上手混合检索：AI Native 统一数据基座实战 | Agentic RAG / 混合检索 | [#29](https://github.com/datawhalechina/easy-data-x-ai/issues/29) / [#30](https://github.com/datawhalechina/easy-data-x-ai/issues/30) | ✅ 已完成 |
| **X4** | 海量 AI Agent 多模数据降本：数据湖库登场 | 数据湖库 × AI | [#32](https://github.com/datawhalechina/easy-data-x-ai/issues/32) / [#33](https://github.com/datawhalechina/easy-data-x-ai/issues/33) | ✅ 已完成 |
| **X5** | 从 Skill 到 MCP Tool | Skill / MCP | [#34](https://github.com/datawhalechina/easy-data-x-ai/issues/34) / [#35](https://github.com/datawhalechina/easy-data-x-ai/issues/35) | ✅ 已完成 |
| **X6** | 从 Harness 到 Loop，再到 Graph Engineering | Agent 工程 / Graph Engineering | — | ✅ 已完成 |

### 列表 C：已完成 · 工程 / 基建任务（Good First Issue）

> 以下任务均已关闭并标记为 completed，保留作为历史共建记录。

| 关联 Issue | 待办 | 难度 | 状态 |
| --- | --- | --- | --- |
| [#6](https://github.com/datawhalechina/easy-data-x-ai/issues/6) | `.env.example` 占位符与 `Config.check_api_key` 判定不一致，修正误判逻辑 | L1 | ✅ 已完成 |
| [#7](https://github.com/datawhalechina/easy-data-x-ai/issues/7) | `config.py` 注释与实现不一致：按注释实现向上查找 `.env` | L1 | ✅ 已完成 |
| [#8](https://github.com/datawhalechina/easy-data-x-ai/issues/8) | 示例脚本 `sys.path.append('..')` 从根目录运行会导入失败，改为稳健的路径处理 | L2 | ✅ 已完成 |
| [#9](https://github.com/datawhalechina/easy-data-x-ai/issues/9) | README 补充 Windows PowerShell 命令示例（`cp` / `python3` 等） | L1 | ✅ 已完成 |
| [#10](https://github.com/datawhalechina/easy-data-x-ai/issues/10) | Tool Use 示例只处理首个 tool_call，且 `list(stream)` 聚合不通用，改为通用实现 | L2 | ✅ 已完成 |
| [#12](https://github.com/datawhalechina/easy-data-x-ai/issues/12) | VitePress 依赖为 alpha 且用 `^` 范围，锁定版本提升构建可复现性 | L2 | ✅ 已完成 |
| [#13](https://github.com/datawhalechina/easy-data-x-ai/issues/13) | 补充 PR/Push 的 CI 校验工作流（docs build / Python 示例语法检查等） | L2 | ✅ 已完成 |

### 列表 D：产业应用篇共建（Industry Practice I1–I8）

> I1–I8 当前均为开放共建任务。认领后请在 `docs/industry/` 对应页面中补充学习材料、可选实验和验收方式；优先讲清通用能力、工程边界与可复现结果。

| # | 章节 | 共建重点 | 难度 | 状态 |
| --- | --- | --- | --- | --- |
| [#90](https://github.com/datawhalechina/easy-data-x-ai/issues/90) | **I1：AI 原生数据库基础** | 补齐核心概念、数据类型、部署模式与能力边界 | L2 | 🟡 待认领 |
| [#91](https://github.com/datawhalechina/easy-data-x-ai/issues/91) | **I2：向量数据库与 RAG** | 设计向量、全文、标量过滤的对比实验与评测 | L3 | 🟡 待认领 |
| [#92](https://github.com/datawhalechina/easy-data-x-ai/issues/92) | **I3：SQL × AI —— AI Functions 的设计与执行** | 验证模型函数、批处理、失败处理与成本控制 | L3 | 🟡 待认领 |
| [#93](https://github.com/datawhalechina/easy-data-x-ai/issues/93) | **I4：File SQL for AI Agent** | 补充文件建模、查询、权限、引用与变更追踪实验 | L3 | 🟡 待认领 |
| [#94](https://github.com/datawhalechina/easy-data-x-ai/issues/94) | **I5：AI 列 —— 模型驱动派生数据的自动维护** | 验证回填、更新、重试、幂等性与可追溯性 | L3 | 🟡 待认领 |
| [#95](https://github.com/datawhalechina/easy-data-x-ai/issues/95) | **I6：上下文工程概述** | 讲清来源、记忆、任务状态、上下文预算与引用的完整链路 | L2 | 🟡 待认领 |
| [#96](https://github.com/datawhalechina/easy-data-x-ai/issues/96) | **I7：PowerContext 的设计与实现** | 以上下文管理系统为案例，分析数据关系、接口边界与存储契约 | L3 | 🟡 待认领 |
| [#97](https://github.com/datawhalechina/easy-data-x-ai/issues/97) | **I8：案例场景和测评构建** | 构建任务、数据集、运行链路、测评指标与可复现证据 | L3 | 🟡 待认领 |

---

## 五、参与方式总览

1. **提 Issue 参与讨论**：先开 Issue 说明你的建议、需求或共建思路（在 [New Issue](https://github.com/datawhalechina/easy-data-x-ai/issues/new/choose) 页选择对应的 Issue 模板）。
2. **认领产业应用篇**：在列表 D 对应 Issue 下留言认领，完善 `docs/industry/` 中的课程页，完成后提 PR。
3. **完善已有内容**：对 P / D / X 已有章节提出勘误或增量改进，在 PR 中说明问题和验证方式。
4. **贡献新扩展篇**：先开 Issue 对齐大纲，确认与 X1–X6 不重复后，再在 `docs/extra/` 下创建新章节。

> 提交 PR 后，记得在描述里注明认领的任务编号（#编号），方便归档。

---

## 六、致谢与收获

我们希望每一位参与者不仅留下贡献，也能收获成长。所有被合并 PR 的贡献者都会获得以下激励：

### 🏆 贡献者墙

所有合并过 PR 的贡献者会自动登上仓库 README 的**贡献者墙**（头像 + GitHub 主页 + 贡献量），由 GitHub Action 自动更新，无需手动申请。

### 🎁 实体礼品

按贡献量分档赠送 **OceanBase 社区定制周边**：

| 档位 | 条件（示例） | 礼品 |
| --- | --- | --- |
| 入门 | 合并 1 个有效的 PR | OceanBase 定制贴纸 / 徽章 |
| 进阶 | 合并 2 个及以上的内容完善类 PR | OceanBase 专属马克杯 / 帆布包 |
| 核心 | 独立完成一节产业应用篇或新扩展篇 | OceanBase 定制 T 恤 |

### 🌟 成长与社区收获

- **课程署名**：扩展篇作者会在课程对应章节页面**正式署名**。
- **纳入 OceanBase 社区布道师体系**：表现突出的共建者可被推荐为「种子布道师」，获得 OceanBase 官方证书。
- **讲师 / 露出机会**：受邀参与社区直播、线下 Meetup、高校行，输出自己的内容。
- **优秀贡献者评选**：定期评选季度优秀贡献者，额外礼品 + 社区公众号专访。
- **职业机会**：优秀贡献者可获得蚂蚁集团及 OceanBase 实习 / 内推推荐。
- **联合社区礼品**：根据课程共建的贡献量，还可获得 OceanBase 社区为大家准备的定制礼物，以及 LangChain 中国社区的礼品。

---

## 七、提问与讨论

- **课程内容问题**：在 [Issues](https://github.com/datawhalechina/easy-data-x-ai/issues) 提问，或在配套视频评论区留言。
- **加入交流群**：扫描 README 底部二维码，加入 Data x AI 课程交流群。

再次感谢你的贡献，期待与你一起把这门课打磨成精品！🚀
