# Filesystem-like / Vector-Graph-like Agent Memory 证据矩阵

> 说明：
> - `类别` 按 `report_v3.md` 的主导接口划分
> - `证据等级` 含义见主报告
> - `主线结论` 表示该系统是否直接用于支撑报告的主结论
> - 访问与核验时间：2026-04-15

## 主线系统

| 系统 | 类别 | 一手来源 | 已核验的核心事实 | 公开量化 / 公开信号 | 证据等级 | 主线结论 | 备注 |
|------|------|----------|------------------|---------------------|----------|----------|------|
| OpenViking | Filesystem-like | 官方 GitHub README / 官方站点 | filesystem paradigm；`viking://`；L0/L1/L2；目录递归检索；retrieval trajectory；session self-iteration | README 给出相对 OpenClaw / LanceDB 的 completion 与 token 改善 | A | 是 | 量化为项目 README 官方口径，不做跨论文总排 |
| memsearch | Filesystem-like | 官方 GitHub README / 官方文档 | Markdown source of truth；Milvus shadow index；dense + BM25 + RRF；`search -> expand -> transcript` | 4 个 coding-agent 平台；3 层 recall；Milvus Lite 单文件 | A | 是 | coding agent 场景证据最清晰 |
| memU | Filesystem-like | 官方 GitHub README / 官方站点 | memory as file system；24/7 proactive agents；categories/items/resources/cross refs | one-click install `<3 min`；token 成本约 `~1/10` 为官方口径 | B | 是 | 方向鲜明，但量化主要来自官方自报 |
| Acontext | Filesystem-like | 官方 GitHub README / 官方 docs | skill memory layer；task learnings -> skill files；Markdown skill files；progressive disclosure | 后台学习延迟与默认 agent loops 有官方文档说明 | A | 是 | 对“技能即记忆”定义最清晰 |
| Voyager | Filesystem-like / Procedural | 原始论文 | executable code skill library；iterative prompting；long-horizon skill accumulation | 论文给出 `3.3x` 更多 unique items、`15.3x` 更快里程碑 | A | 是 | 程序性记忆的学术代表 |
| lossless-claw | Filesystem-like / Compaction | 官方 GitHub README | SQLite 持久化；DAG summary；`lcm_grep` / `lcm_describe` / `lcm_expand`；保留原始消息可恢复 | 无统一 benchmark，但机制可核验 | B | 是 | 解决上下文压缩与可恢复展开，不是通用 memory 平台 |
| Memoria | Filesystem-like / Governance | 官方 GitHub README / 官方站点 | Git for AI agent memory；snapshot/branch/merge/rollback；CoW；contradiction detection；quarantine；audit trail | 部署拓扑、版本语义、治理能力公开清晰 | A | 是 | 治理层代表 |
| mem0 | Vector/Graph-like | 官方 docs / 官方 repo / 原始论文 / 官方 research page | universal self-improving memory layer；extract/consolidate/retrieve；graph-enhanced path | 论文与官方 research page 都有 benchmark；新研究页口径更激进但展示层次不完全一致 | A | 是 | 强生态样本；最新 benchmark 需显式标注官方口径 |
| Honcho | Vector/Graph-like | 官方 GitHub README / 官方 docs / 官方 benchmark blog | entities/peers/sessions/representations；continual learning；entity state modeling | 官方 blog 自报 LongMem S 90.4、LoCoMo 89.9、BEAM 多档分数 | B | 是 | entity-aware memory 代表；benchmark 非论文主线 |
| Graphiti / Zep | Vector/Graph-like | 官方 GitHub README / 官方 docs / 原始论文 | temporal knowledge graph；dynamic graph；time+full-text+semantic+graph retrieval | 论文给出 DMR 与 LongMemEval 结果 | A | 是 | 时序关系 memory 的强代表 |
| eion | Vector/Graph-like | 官方 GitHub README / 官方站点 | shared memory storage；unified knowledge graph；PostgreSQL + pgvector + Neo4j；guest access | 架构参数和工具集公开，但无统一 benchmark | B | 是 | 多 agent + 权限模型表达清晰 |
| ContextLoom | Vector/Graph-like | 官方 GitHub README | shared brain；Redis-first；memory from compute decoupling；cold-start hydration；cycle hash | 官方宣称 sub-millisecond retrieval | B | 是 | shared context plane 方向明确，产品成熟度仍较早 |
| mem9 | Vector/Graph-like | 官方 GitHub README / 官方站点 | stateless plugin + central memory server；shared memory pool；TiDB hybrid retrieval；visual dashboard | 插件数量、memory tools、免费层规格公开 | B | 是 | coding-agent 协作与集中治理样本 |
| UltraContext | Adjacent context infrastructure | 官方 docs / 官方站点 | Context API；history/fork/clone/edit；CLI + MCP；same context everywhere | 无统一 memory benchmark | B | 否 | 重要邻接基础设施；更像 context plane 而非完整长期 memory 系统 |
| XiaoClaw | 生态包装层 | 官方站点 / 安装页 | 更像 OpenClaw 安装封装、API 产品层，不是独立 memory core | 无可靠官方 benchmark | X | 否 | 不进入主线技术结论 |

## 学术与方法论参照

| 系统 / 论文 | 角色 | 一手来源 | 吸收的合理结论 | 证据等级 | 备注 |
|-------------|------|----------|----------------|----------|------|
| CoALA | 认知架构参照 | 原始论文 | memory 应按模块化认知架构理解，而非单库外挂 | A | 用于定义问题空间 |
| MemGPT / Letta | 虚拟上下文管理参照 | 原始论文 / 官方 docs | memory tiers 与 context management 是核心视角 | A | 更偏调度与 OS-like framing |
| LoCoMo | 基准参照 | 原始论文 / 项目页 | 长对话、多跳、时间、人物关系 benchmark | A | 不等于通用工程 memory 评测 |
| LongMemEval | 基准参照 | 原始论文 | 信息抽取、多 session、时间、知识更新、abstention 很关键 | A | 对“长期 chat memory”定义更细 |
| BEAM | 新一代基准参照 | 原始论文 | 百万 token 长时记忆评测开始成为 frontier | A | 更多用于判断评测趋势 |
| TiMem | 时间层次化参照 | 原始论文 | 时间树式 consolidation 与 complexity-aware recall 值得借鉴 | A | 学术路线强，但产业化尚早 |
| LiCoMemory | 轻量图参照 | 原始论文 | 图更适合作为导航与候选缩减层，而非总是重型 KG | A | 用于支持轻量结构化索引判断 |
| MIRIX | 多类型编排参照 | 原始论文 | memory types orchestration 与 active retrieval 很重要 | A | 用于支持“memory orchestration”观点 |

## 证据使用原则

### 可以作为强支撑的结论

- Filesystem-like 路线强调可读、可编辑、渐进式披露、程序性沉淀与治理能力
- Vector/graph-like 路线强调 northbound memory plane、共享状态、实体关系和时序演化
- `CortexMem` 适合做混合架构，而不是单路线押注
- `lossless-claw` 已可作为 append-only + layered summaries 的工程样本

### 不能作为强支撑的结论

- 把所有公开 benchmark 混成单一“总冠军榜”
- 用官方 blog / research page 数字替代同行评审 benchmark
- 把 `UltraContext` 当成已经成熟的长期 memory layer
- 把 `XiaoClaw` 当成独立 memory core

## 本轮最关键的证据判断

1. `memsearch`、`Acontext`、`Memoria`、`lossless-claw` 共同说明 filesystem-like 路线不是“没有检索能力”，而是把检索放在真相层之下。
2. `mem0`、`Honcho`、`Graphiti`、`eion`、`mem9`、`ContextLoom` 共同说明 northbound memory plane 已经从“向量库外挂”推进到“共享状态 / 实体表示 / 时序图 / 后台 consolidation”。
3. `UltraContext` 很有价值，但更适合作为 context plane / context engineering 邻接基础设施，而不是直接作为成熟 memory 主线代表。
4. `XiaoClaw` 仍应保留在生态包装层，不应被误读为独立 memory architecture.

---

## 🆕 新增：report.md 薄弱声明清单（批判性研究，2026-04-23）

> 来源：`critical-research/critical-analysis.md`
> 标注规则：A（peer-reviewed + 独立复现）| B（arXiv 预印本）| C（官方自报）| D（推测/零实现）

| 报告行号 | 声明内容 | 证据等级 | 缺失的证据类型 | 建议补救措施 |
|----------|---------|---------|---------------|-------------|
| 11 | Mem0 "26%准确率提升与91%延迟降低" | C | 独立复现数据 | 查找 mem0 最新研究论文或 benchmark 框架 |
| 15-17 | OpenViking "83-91% token 节省, 43-49%完成率提升" | C | peer-reviewed 论文 | 补充论文引用或标注为"官方自报" |
| 73 | "MemBrain LoCoMo 93.25%" | C | peer-reviewed 论文 + 独立复现 | 标注为"feeling.ai 自建基准自报数据" |
| 170 | "MAGMA 超越现有 SOTA"（具体数值缺失） | B | 具体 benchmark 分数 | 查阅 MAGMA 全文 PDF 补充具体数值 |
| 190 | AgentMem L2.5 机器推理衍生层 | D | 任何产业/学术先例 | 标注为"概念设计"，做 PoC 验证 |
| 192 | L4 多 Agent 并发保护伞（MVCC+CoW） | D | 多 Agent 并发验证 | 标注为"推测性设计"，降为 Phase 2 功能 |
| 200-201 | MUSE TAC 基准 51.78% 成功率 | ⚠️ 占位符 | 真实 arXiv 编号 | 补充正确论文编号（报告中为 "arXiv:2601.xxxxx"） |
| 254 | 三层防御总延迟 <300ms | D | 工程验证 | 修正为 <500ms 或改用纯规则引擎 |
| 269 | "净 Token 效率"公式的合理性 | D | 任何系统的实际报告 | 在 MVP 中实际测量并报告 |
| 276-277 | AgentMem "task completion 提升 30-45%" | D | 实现与验证 | 标注为"预期目标"而非"可实现" |
| 281 | AgentPoison + eTAMP 攻击拦截率 >80% | D | 准确论文编号 | 补充正确引用或标注为推测 |
| 282 | MINJA 免疫力提升 30-50%（7+天后） | C | 实验数据 | 标注为"基于 MINJA 趋势推算" |

### 更新后的证据使用原则

**新增不能为强支撑的结论**：
- 不将不同定义（如"召回冗余减少" vs "Token 节省"）的指标进行直接比较
- 不将 arXiv 预印本数据等同于正式发表的 peer-reviewed 结果
- 不假设 AgentMem 的任何未实现组件已达到报告中的性能指标
- 不将 Omni-SimpleMem +411% 提升作为"性能领先"证据（绝对值 0.598 低于 TiMem 0.753 和 mem0 0.916）

### 🆕 2026-04-23 更新（第二轮深度溯源后新增）

#### 上轮修正记录（2026-04-23 深度验证后）

| 修正项 | 原报告状态 | 修正后状态 | 来源 |
|--------|----------|-----------|------|
| Graphiti 论文编号 | 报告暗示 "2026年3月" | **arXiv:2501.13956**（2025年1月） | Graphiti GitHub README arXiv badge |
| Graphiti 架构描述 | 报告混淆为"三层类人记忆架构" | 实际为**时序上下文图**（Entities/Facts/Episodes），非 EPISODES/ENTITIES/COMMUNITIES | Graphiti README "What is a Context Graph" |
| OpenViking benchmark 数据 | 证据等级 C（官方站点） | **升级为 B**（README 数据表可验证，AGPL-3.0 已确认） | OpenViking GitHub README |
| OpenViking AGPL-3.0 | 未验证（报告提到但未验证） | **已确认为 A**（LICENSE 文件） | OpenViking GitHub LICENSE |
| mem0 graph-enhanced | 报告暗示完整 graph DB | ⚠️ 仅有 **entity linking**，无 Neo4j/graph DB 能力 | mem0 README |
| memU LoCoMo 92.09% | 报告引用 | 已验证为**自报数据** | memU README Performance 段 |
| 6 个 GitHub 项目一致性 | 仅 2 个验证（mem0+Memoria） | **全部 6 个已验证** | 本报告 |

#### 本轮新确认的学术论文（4项）
| 论文 | arXiv ID | 新增信息 |
|------|---------|---------|
| **MUSE** | arXiv:2510.08002 | 替换原占位符 "arXiv:2601.xxxxx"；确认 TAC 51.78% 数据来源 |
| **PlugMem** | arXiv:2603.03296 | Task-Agnostic Plugin Memory Module；与 SKILL.md 规范高度一致 |
| **Memp** | arXiv:2508.06433 | "Exploring Agent Procedural Memory" — 报告原遗漏的关键论文 |
| **AgentPoison** | arXiv:2407.12784 | 2024年的记忆投毒攻击论文，应作为安全防御基线 |

#### 本轮新确认的 AgentTrace 变体
| 论文 | arXiv ID | 差异 |
|------|---------|------|
| AgentTrace (结构化日志) | arXiv:2602.10133 | 原报告引用，编号正确 ✅ |
| AgentTrace (因果图 RCA) | arXiv:2603.14688 | 独立论文，聚焦根因分析，应补充到 L3 层参考 |

#### 本轮仍无法确认的引用（3项）
| 论文 | 报告中描述 | 搜索状态 |
|------|----------|---------|
| **eTAMP** | 环境指令注入 | arXiv全文搜索无结果 |
| **DeepSeek Engram** | MoE条件记忆模块 | 未找到任何论文 |
| **STEM (ICLR)** | FFN查表替换 | 未找到匹配论文 |
