# External Memory Augmentation 深度研究报告

> 目录：`AgentOS-Memory/fs-vector-graph/`
>
> 更新时间：2026-04-15
>
> 研究主题：Agent 外部记忆增强中的两条主路线
> 1. `filesystem-like agent memory`
> 2. `vector/graph-like agent memory`
>
> 研究目标：融合现有 `report.md` 与 `report_v2.md`，结合 2026-04-15 前可核验的一手材料，回答：
> - 这些 memory 方案究竟解决了哪些关键问题
> - 当前解决到什么程度，公开材料中的强信号 SOTA 是什么
> - 核心实现机制和原理是什么
> - 分别面向哪些关键场景
> - 对 `CortexMem` 的能力建设有什么直接启发

---

## 0. 研究范围、方法与结论先行

### 0.1 研究范围

本报告聚焦 **external memory augmentation**，即模型外的持久化记忆系统，不把 Transformer 原生记忆、参数编辑、KV-cache 机制本身当作主线。

纳入主研究对象的标准是同时具备三点：

1. **跨会话持久化**
2. **可检索 / 可复用**
3. **可更新 / 可巩固**

因此：

- `Voyager` 虽然不是通用聊天 memory 产品，但其可执行技能库满足“长期可复用程序性记忆”，纳入主研究。
- `MemGPT/Letta` 更接近虚拟上下文管理框架，作为重要学术参照。
- `UltraContext` 属于重要邻接基础设施：它解决跨 agent 上下文同步和版本化，但还不是典型的长期记忆抽取/巩固系统。
- `XiaoClaw` 仍不作为独立 memory architecture 处理，它更像 OpenClaw 的安装封装与生态包装层。

### 0.2 为什么单独研究 filesystem-like 与 vector/graph-like

“Agent Memory”经常被笼统地说成“长期记忆”，但实际至少有两套不同的工程目标：

- **Filesystem-like memory**
  重点是把记忆重新变成可读、可调试、可迁移、可治理的工程对象。
- **Vector/graph-like memory**
  重点是把记忆做成共享语义平面、关系平面和服务平面，支撑多 agent、跨产品、跨终端协同。

这个切分更接近真实工程问题：

> 生产里的 agent memory，到底更像“可审阅的知识工作区”，还是更像“可编排的共享语义基础设施”？

答案不是二选一，但两类系统的第一性设计目标明显不同。

### 0.3 主导接口判定规则

同一系统可能同时有文件层、向量层和图层，本报告按 **主导接口** 归类：

- 主导接口是文件树、Markdown、skill file、目录导航、版本对象：归 `filesystem-like`
- 主导接口是 API、SDK、共享状态、向量检索、图检索、managed service：归 `vector/graph-like`

例子：

- `memsearch` 内部有 Milvus 向量索引，但 Markdown 是 source of truth，仍归 filesystem-like。
- `mem9` 服务 coding agents，但主导接口是中心化 memory server、共享 memory pool、混合检索和可视控制，归 vector/graph-like。
- `lossless-claw` 以 SQLite + DAG 摘要和 recall tools 管理 OpenClaw 上下文，主导接口仍更接近 filesystem/context-engine，因此归 filesystem-like 的“上下文压缩子类型”。

### 0.4 证据等级

| 等级 | 含义 |
|------|------|
| A | 官方仓库 / 官方文档 / 原始论文相互印证，关键机制可核验 |
| B | 以官方仓库或官方文档为主，机制较清晰，但效果主要依赖项目自报 |
| C | 官方入口存在，但口径偏产品化、实现细节或评测链条不够稳 |
| X | 本轮未拿到足够稳定的一手技术链条，只能弱引用或不纳入主线 |

### 0.5 六个高层结论

1. **Filesystem-like memory 的价值不是“反向量库”，而是把记忆重新拉回可读、可控、可迁移的工程对象。**
2. **Vector/graph-like memory 的价值不是“多存 embedding”，而是为多 agent、跨会话、跨系统协作提供共享语义与关系平面。**
3. **两类路线解决的是不同层次的问题：前者先解决可观测性、程序性沉淀和治理；后者先解决共享、规模化、关系化和异步基础设施。**
4. **行业正在走向混合架构：filesystem-like 正引入 shadow index / hybrid retrieval，vector/graph-like 正补 provenance / versioning / observability。**
5. **公开 benchmark 很重要，但不能被滥用。LoCoMo、LongMem、LongMemEval、DMR、BEAM 测的是不同能力，不能做单一总冠军表。**
6. **`CortexMem` 最合理的方向不是押单一路线，而是“文件表面 + 语义索引 + 图关系 + 程序性记忆 + 治理层”的混合架构。**

---

## 1. 为什么会出现这两类 Agent Memory

### 1.1 传统 memory/RAG 在 agent 场景里暴露了什么问题

长期记忆在 agent 里不是锦上添花，而是因为传统做法在真实任务中出现了结构性缺陷。

#### 问题一：跨会话失忆，但记忆又不可读

在 coding agent、research agent、personal assistant 场景里，真正困扰用户的不是模型“不会检索”，而是：

- 上一轮有效讨论没有稳定落盘
- 即使落盘，人也无法读懂、改正、迁移
- 换一个 agent、换一个终端、换一个模型后上下文断掉

`memsearch`、`OpenViking`、`Acontext` 的兴起，都是在回答这个问题。

#### 问题二：上下文正在无限增长，但 token 成本和注意力质量不会线性变好

长上下文并不等于好记忆。`MemGPT` 把问题定义为“有限上下文窗口下的虚拟内存管理”；`memU`、`OpenViking`、`Mem0`、`Honcho` 都在强调：

- 需要比“每轮都全塞进去”更便宜
- 需要比“扁平 top-k chunk”更稳定
- 需要主动做 consolidation，而不是只堆历史

#### 问题三：多 agent 协作时，各自有状态，但没有共享脑

单 agent 还能靠本地文件或对话摘要勉强维持；多 agent 一旦串行或并行协作，就会遇到：

- 状态共享断裂
- 权限边界不清
- 关系信息难以表达
- 不同 agent 对同一实体的认知无法汇合

`ContextLoom`、`eion`、`mem9`、`UltraContext`、`Honcho` 都是在解决这个问题。

#### 问题四：真正高价值的长期资产，常常不是事实，而是技能和策略

记住“用户喜欢咖啡”当然有价值，但在大量 agent 工作流中，更高价值的是：

- 哪种调试步骤有效
- 哪个工具组合最稳
- 什么 workflow 在这个环境里能跑通
- 什么失败模式出现后该怎么修

`Voyager`、`Acontext` 和 filesystem-like 路线的“skill memory”本质上在回答：

> 经验能不能被沉淀成可执行资产，而不只是变成一段文字摘要？

#### 问题五：一旦记忆写错、被污染或过时，如何治理

长期记忆进入生产后，问题从“能不能记住”升级为：

- 写错了怎么办
- 记忆冲突怎么办
- 不同实验分支怎么办
- 哪次 mutation 导致坏行为
- 低置信信息如何隔离

`Memoria` 之所以重要，不在于它又加了一个向量库，而在于它把“Git for memory”做成了一等公民。

### 1.2 学术界如何组织这些问题

几篇关键论文把 memory 研究从零散技巧推进到更清晰的框架：

- `CoALA`：把 language agents 组织为带模块化记忆组件、动作空间和决策过程的认知架构。
- `MemGPT`：把 memory 理解为有限上下文下的虚拟上下文管理。
- `LoCoMo`：把“很长对话里的长期记忆”正式 benchmark 化。
- `LongMemEval`：把长期 chat assistant memory 拆成信息抽取、多会话推理、时间推理、知识更新和 abstention。
- `TiMem`、`LiCoMemory`、`MIRIX`、`Graphiti`：分别把问题推进到时间层次化、轻量图式、记忆类型编排和时序知识图谱。

这意味着 agent memory 已经从“外挂向量库”升级为一个明确的系统设计问题。

---

## 2. Filesystem-like Agent Memory

### 2.1 这一路线的定义

Filesystem-like memory 并不是“把所有内容存成 Markdown”这么简单。它的本质是：

> 记忆首先是人类可读、可编辑、可比较、可版本化的对象；语义索引只是加速层，不是真相层。

### 2.2 它主要解决哪些问题

这一路线最擅长解决五类问题：

1. **可读性**
   人能直接查看记忆对象，而不是只能相信 embedding 检索。
2. **可调试性**
   目录、文件、技能和版本对象天然可 diff、可 grep、可审计。
3. **程序性沉淀**
   经验可以落成 skill file、workflow 或代码。
4. **渐进式披露**
   先看索引，再看概览，再按需展开，避免一次性 top-k 拼一堆噪声。
5. **治理与迁移**
   记忆不是黑盒状态，而是能被导出、回滚、迁移的资产。

### 2.3 这一路线的共同机制

| 机制 | 原理 | 代表 |
|------|------|------|
| 文件真相层 | Markdown / skill file / 目录对象是 source of truth | memsearch, Acontext |
| 影子索引 | 向量库或 FTS 只是对文件真相层的重建缓存 | memsearch |
| 分层加载 | L0/L1/L2 或 search→expand→transcript，按需读取 | OpenViking, memsearch |
| 程序性记忆 | 把经验沉淀成 skill 或 executable code | Acontext, Voyager |
| append-only + consolidation | 保留原始 episode，再在上层总结、压缩、抽取 | lossless-claw, OpenViking |
| 版本治理 | branch / snapshot / rollback / diff / quarantine | Memoria |

### 2.4 内部子类型

| 子类型 | 要解决的核心问题 | 代表方案 |
|--------|------------------|---------|
| Context Filesystem | context 碎片化、检索不透明 | OpenViking, memU |
| Markdown-first Memory | 记忆不可读、不可改、不可迁移 | memsearch |
| Skill-first Memory | 经验无法沉淀为可复用资产 | Acontext, Voyager |
| Lossless Context Compaction | 上下文太长但不能丢细节 | lossless-claw |
| Governed Memory | 记忆污染、回滚困难、审计缺位 | Memoria |

### 2.5 代表系统深度分析

#### OpenViking

OpenViking 是 filesystem-like 路线里最“范式化”的方案之一。官方 README 直接把它定义为用于 AI agents 的 context database，并明确提出：

- filesystem paradigm 统一 memory / resources / skills
- `viking://` URI 组织上下文
- L0/L1/L2 tiered context loading
- directory recursive retrieval
- retrieval trajectory visualization
- session self-iteration

它的关键贡献不只是“能搜”，而是把检索过程显式化。相比扁平 RAG，它让 agent 的 context acquisition 更像“先定位目录、再逐层钻取”。

公开量化上，OpenViking 官方 README 仍给出基于 LoCoMo10 的相对提升结果：相对 OpenClaw 原生 memory 的 completion rate 提升和输入 token 显著下降。这些数字可作为**方向性工程信号**，但不应和论文 benchmark 直接混排。

#### memsearch

memsearch 是 coding-agent memory 中最具代表性的 Markdown-first 实现之一。其最新 README 非常清楚：

- Markdown 是 source of truth
- Milvus 是 rebuildable shadow index
- dense + BM25 + RRF
- 3-layer recall：`search -> expand -> transcript`
- 支持 Claude Code、OpenClaw、OpenCode、Codex CLI

它真正解决的问题不是“聊天人格记忆”，而是：

- coding sessions 的跨会话 recall
- 多 agent / 多终端的同一记忆表面
- 人类可编辑、可 version-control 的 memory 对象

这是目前 filesystem-like 路线里最工程化、最接近真实开发者使用形态的一支。

#### memU

memU 的定位很明确：`memory for 24/7 proactive agents`。它把 memory 明确比喻为文件系统：

- folders 对应 categories
- files 对应 memory items
- symlinks 对应 cross references
- mount points 对应 resources

其价值在于把长期在线 agent 的记忆组织问题说清楚：主动式 agent 不能只等 query 再检索，它需要更持久的结构化 memory space，以及更小的默认上下文。

但 memU 的公开量化仍以官方口径为主，例如“一键安装 <3 分钟”“token cost 约为 comparable usage 的 1/10”。这说明方向鲜明，但 benchmark 证据仍不如论文路线稳。

#### Acontext

Acontext 是“Skill is Memory, Memory is Skill”的代表。其 README 已经把设计理念讲得非常透：

- skill memory layer
- 自动从 agent run 中 distill learnings
- 存为 skill files
- Markdown skill files 可读、可改、可分享
- `get_skill` / `get_skill_file` 做 progressive disclosure
- 不走 embedding top-k

它不是在做“更多事实存储”，而是在把 memory 直接变成 agent 的技能层和工作方式层。

对 `CortexMem` 来说，这一点很关键：**高价值长期资产应优先以程序性/技能性对象存在，而不是先压成抽象文本再寄希望于检索。**

#### Voyager

Voyager 不是通用 memory 产品，但它在学术上把“程序性记忆”做得最彻底。论文明确指出其三大关键组成之一是：

- ever-growing skill library of executable code

这为 agent memory 提供了重要分界线：

- **事实记忆** 解决“知道什么”
- **程序性记忆** 解决“怎么做”

很多通用 memory 产品今天仍偏重前者，而真正决定 agent 长期能力增长的，常常是后者。

#### lossless-claw

这是本轮融合里最重要的修正之一。旧稿把 `lossless-claw` 作为弱证据条目处理，但截至 2026-04-15，官方 GitHub README 已足以支撑其作为 **可核验的 filesystem-like 子路线样本**：

- OpenClaw 的 Lossless Context Management plugin
- SQLite 持久化所有消息
- 对旧消息进行 DAG 式分层总结
- 通过 `lcm_grep` / `lcm_describe` / `lcm_expand` 从压缩历史中找回细节
- 目标不是通用 user memory，而是 **在不丢原始消息的前提下管理超长上下文**

它的价值不在“通用记忆 SOTA”，而在于给 `append-only raw episodes + layered summaries + recoverable expansion` 提供了一个很实际的工程实现。

#### Memoria

Memoria 是治理层的代表。官方 README 的核心信息很明确：

- Git for AI agent memory
- snapshot / branch / merge / rollback
- Copy-on-Write
- vector + full-text hybrid retrieval
- contradiction detection
- low-confidence quarantine
- full audit trail + provenance chain

如果说大多数 memory 系统还在解决“怎么写入/检索”，Memoria 在解决的是“长期生产记忆如何安全演进”。这不是附属功能，而是 memory system 迟早要面对的主问题。

### 2.6 Filesystem-like 路线的优势与边界

#### 主要优势

- **可观测性强**：人可以直接看、改、diff、grep
- **工程兼容性高**：文件、zip、git、workspace 都是成熟抽象
- **程序性沉淀自然**：skill / playbook / code 容易成为一等对象
- **治理实现直观**：branch、rollback、review 的语义天然成立

#### 主要边界

- **跨 agent 共享与实时协同偏弱**
- **图关系和实体长期演化表达不足**
- **当规模上升到多租户、多 agent、多产品时，单纯文件表面不够**
- **很多系统仍缺乏标准 benchmark 和统一权限模型**

#### 当前状态判断

Filesystem-like 路线已经证明：

- 它不是“没有检索能力的老派方案”
- 它能和向量检索共存，而且更适合作为真相层
- 它在 coding agent、research agent、个人工作流里已经足够有实际价值

但它还没有独自解决：

- 多 agent 共享脑
- 跨实体/跨时间关系建模
- 标准化 northbound API

---

## 3. Vector/Graph-like Agent Memory

### 3.1 这一路线的定义

Vector/graph-like memory 的本质不是“把 chunk 丢进向量库”，而是：

> 把 memory 做成一个可查询、可共享、可关系化、可后台演化的语义服务层。

### 3.2 它主要解决哪些问题

这一路线最擅长解决六类问题：

1. **多 agent 共享**
2. **跨会话、跨终端、跨产品统一接入**
3. **语义召回与结构化召回结合**
4. **实体、关系、时间、状态变化建模**
5. **后台 consolidation / representation 更新**
6. **作为 northbound API 供多个 agent runtime 复用**

### 3.3 这一路线的共同机制

| 机制 | 原理 | 代表 |
|------|------|------|
| northbound memory API | 主接口是 SDK / REST / managed service / MCP | mem0, mem9 |
| hybrid retrieval | dense + keyword + metadata + entity + graph | mem0, mem9, Graphiti |
| entity / representation modeling | 记忆不只是 chunk，而是持续更新的实体状态 | Honcho |
| temporal graph | 关系有时间窗、演化与历史版本 | Graphiti, TiMem |
| shared namespaces | tenant / workspace / agent scopes / guest access | mem9, eion |
| background consolidation | 异步抽取、调和、推理、写回 | mem0, Honcho, Graphiti |

### 3.4 内部子类型

| 子类型 | 核心目标 | 代表 |
|--------|---------|------|
| Universal Memory Layer | 为应用和 agent 提供通用 memory 服务 | mem0 |
| Shared Memory Plane | 让多 agent 共用上下文/状态 | ContextLoom, mem9 |
| Graph / Entity Memory | 围绕实体、关系、时序演化建模 | Honcho, Graphiti, eion |
| Temporal-Hierarchical Memory | 解决长时间尺度的层次化巩固 | TiMem |
| Multi-type Orchestrated Memory | 多类记忆协同检索与更新 | MIRIX |

### 3.5 代表系统深度分析

#### mem0

mem0 是今天最典型的 universal memory layer 之一。其 docs 与论文都强调：

- universal, self-improving memory layer
- extract / consolidate / retrieve
- graph-enhanced variant
- managed platform 与 open source 双路径

它的核心思想不是“把对话全量存下来”，而是用 LLM 抽取候选事实，再做 memory-level reconciliation。旧稿已经正确指出其典型工作流是 `ADD / UPDATE / DELETE / NOOP` 四路决策，这一点仍成立。

需要注意的是，mem0 的公开 benchmark 在 2025 论文页与 2026 研究页之间出现了两层口径：

- 论文与研究页给出相对 OpenAI memory、full-context 的准确率、延迟、token 成本对比
- 2026 新算法页又给出 LoCoMo / LongMemEval / BEAM 的更强结果，但同一页面的 summary 与可见 cutoff 表格存在呈现口径不完全一致的问题

因此，mem0 应被视为：

- **工程与生态上非常强**
- **公开 benchmark 很积极**
- **但最新 page-level 数字在写报告时必须标注“官方研究页自报，且展示口径有层次差异”**

#### Honcho

Honcho 的差异化不在“又一个向量库”，而在 **entity-aware, continual-learning memory**。

官方 docs 与 benchmark blog 给出的核心设计是：

- 存储消息后，后台推理形成 representations
- 这些 representations 是关于 users / agents / groups / ideas 的持续状态
- 系统会“dream”并做更进一步的推理
- API 不是简单 chunk recall，而是围绕 richer state 组织

这是一个重要方向：memory 不再只是“从历史中找一句话”，而是“对某个实体现在知道什么、确信什么、如何变化了”。

从公开评测看，Honcho 的官方 blog 在 2025-12-19 宣称：

- LongMem S 90.4%
- LoCoMo 89.9%
- BEAM 多档 top score

这些是强信号，但依然属于官方自报，应和论文 benchmark 分开看。

#### Graphiti / Zep

Graphiti 是 vector/graph-like 路线里非常重要的一支，因为它把时间问题正面引入了 memory 架构。

官方 docs 与论文共同强调：

- temporal knowledge graph
- 动态构建 evolving graph
- 保留 changing relationships 和 historical context
- 检索可融合时间、全文、语义和图算法

这比传统 RAG 更接近真实企业 memory：真实世界里的用户关系、业务状态、偏好、账户信息、任务状态都在变，不能只靠静态 chunk recall。

论文公开结果也比较有代表性：

- 在 DMR 上超过 MemGPT
- 在更贴近动态企业场景的评测上表现更好

Graphiti 的意义在于证明：

> 真正的 agent memory，必须显式建模“关系会变、时间会流、旧事实不会简单消失”。

#### eion

eion 的价值在于把“shared memory storage for multi-agent systems”说清楚，并把知识图谱和权限边界引入多 agent 协作：

- PostgreSQL + pgvector + Neo4j
- 统一 knowledge graph
- sequential / concurrent / guest access

它是少数公开把“外部 guest agent 访问”写进设计里的系统，说明它更像 agency / multi-agent runtime 的 memory substrate，而不是单一聊天记忆库。

#### ContextLoom

ContextLoom 的关键词是：

- shared brain
- Redis-first
- cold-start hydration from DB
- communication cycle / cycle hash

它更偏 shared context plane，而不是深层长期 persona memory。其价值在于：

- 把 memory 与 compute 解耦
- 让不同 framework 的 agent 能在同一上下文层工作
- 用 Redis 把 state update 做到很低延迟

这在 agent orchestration 层非常实用，但在长期知识治理和语义沉淀上仍偏早期。

#### mem9

mem9 的定位是：

- persistent memory across sessions and machines
- shared memory for multi-agent workflows
- hybrid recall
- visual dashboard
- central server + stateless plugins

它特别适合 coding-agent / terminal-agent 场景，因为它把边界划得很清楚：

- plugin 无状态
- 记忆在中心服务
- 所有 agent 指向同一 tenant 时共享 memory pool

这是 `CortexMem` 很值得吸收的一点：**插件或 client 端越无状态，memory 的治理、审计和共享越容易收口。**

#### UltraContext

UltraContext 是本轮新增的“邻接基础设施”样本。官方文档显示它提供：

- realtime capture of every agent's context
- Context API
- CLI + MCP Server
- store / retrieve / edit / history / fork / clone contexts
- “same context, everywhere”

它解决的是 **跨 agent 上下文同步与版本化**，而不是典型的长期记忆抽取、实体建模或程序性沉淀。因此更适合归入：

- **vector/graph-like 邻接层**
- 或更准确地说，**context plane / context engineering infrastructure**

它对 `CortexMem` 的启发主要在：

- context history
- fork/clone
- cross-agent awareness
- CLI/MCP/API 三层接入

而不在 memory quality benchmark。

### 3.6 Vector/Graph-like 路线的优势与边界

#### 主要优势

- **共享性强**：天然适合多 agent、多终端、多产品
- **关系化能力强**：能表达实体、关系、时间、状态变化
- **服务化成熟**：更容易做 API、租户、权限、观测和后台作业
- **适合大规模 memory operations**：抽取、更新、去重、异步写入更自然

#### 主要边界

- **可读性和可手动修正性弱于文件真相层**
- **更容易黑箱化**
- **如果 provenance、versioning 和 governance 不足，长期风险很高**
- **产品页 benchmark 往往漂亮，但实际跨系统可比性差**

#### 当前状态判断

Vector/graph-like 路线已经证明：

- 共享 memory plane 是真实需求，不是概念包装
- entity / temporal / graph memory 比扁平 RAG 更接近生产场景
- 评测 frontier 正在从“16k~100k token recall”转向“1M+ token / 多 session / 时间推理 / 知识更新 / abstention”

但它还没有解决：

- 让人直接看懂和修正 memory
- 通用治理标准
- 高可信的跨产品 benchmark 体系

---

## 4. 学术界与产业界的演进脉络

### 4.1 学术界的重要推进

#### CoALA：memory 类型与认知架构

CoALA 的价值在于给 language agents 提供了统一架构语言。它不是单一 memory 算法，但它明确了：

- memory 是多模块的
- memory 与 action space 紧耦合
- agent 的“会不会记”和“会不会用记忆行动”不能分开看

#### MemGPT：虚拟上下文管理

MemGPT 把 memory 问题类比为操作系统里的 memory tiers，这对今天仍有启发：

- memory 不只是存储问题
- 还是调度、换入换出、优先级和控制流问题

#### LoCoMo / LongMemEval：长期记忆 benchmark 化

LoCoMo 和 LongMemEval 的意义不只是分数，而是把 memory 能力拆成更明确的可测维度：

- 单跳和多跳
- 时间推理
- 知识更新
- 多 session 推理
- abstention

这迫使产业系统不能只讲“更像人一样记住了”，而要讲具体在哪类问题上有提升。

#### TiMem：时间层次化巩固

TiMem 提出的 Temporal Memory Tree 代表了一个非常强的学术方向：

- 从 raw observations 到 progressively abstracted persona
- 按时间层级做 memory consolidation

这比“把历史全总结一遍”更贴近长期 agent 的需要。

#### LiCoMemory：轻量图而不是重图

LiCoMemory 反对把所有 memory 都做成沉重 KG。它要解决的是：

- 图结构要提升导航和候选缩减
- 但不要让语义和拓扑纠缠到过重

这对于工程系统非常重要，因为很多“图 memory”最终死在复杂度和维护成本上。

#### MIRIX：多类型记忆编排

MIRIX 明确提出六类 memory：

- Core
- Episodic
- Semantic
- Procedural
- Resource Memory
- Knowledge Vault

其重要价值是把 memory 从“单一库”推进到“编排系统”。

### 4.2 产业界的重要推进

产业界真正推进了三个方向：

1. **从聊天记忆走向基础设施**
   `mem0`、`mem9`、`UltraContext`、`ContextLoom`
2. **从事实记忆走向技能和程序性资产**
   `Acontext`、`Voyager`
3. **从 recall 走向治理**
   `Memoria`

### 4.3 产业和学术正在收敛到哪些共识

#### 共识一：外部 memory 仍然必要

即使 context window 在变大，公开 benchmark 和产业实践都说明：

- 更长窗口不等于更强长期记忆
- 全量上下文方法在延迟和成本上不可持续
- 时间推理、知识更新、跨 session 结构化 recall 仍然是难点

#### 共识二：memory 必须分层

几乎所有成熟路线都在分层，只是分法不同：

- raw vs summary
- episodic vs semantic vs procedural
- file truth vs shadow index
- online writes vs background consolidation

#### 共识三：memory 不应只按“召回”定义

真正成熟的 memory system 还必须考虑：

- 写入策略
- 冲突调和
- 版本治理
- 权限隔离
- 遗忘和过期
- 可解释性

---

## 5. 两类路线的比较与融合判断

### 5.1 能力对比

| 维度 | Filesystem-like | Vector/Graph-like |
|------|-----------------|-------------------|
| 人类可读性 | 强 | 中到弱 |
| 手动可修正性 | 强 | 弱于文件层 |
| 多 agent 共享 | 中 | 强 |
| 关系 / 时序建模 | 中 | 强 |
| 程序性记忆沉淀 | 强 | 中 |
| 版本治理自然度 | 强 | 取决于系统设计 |
| northbound API | 弱到中 | 强 |
| 大规模服务化 | 中 | 强 |
| 黑箱风险 | 低到中 | 中到高 |

### 5.2 不是替代关系，而是分工关系

- Filesystem-like 更像 **southbound memory surface**
  - 让人和 agent 看懂记忆
  - 沉淀技能
  - 做局部修正和治理
- Vector/graph-like 更像 **northbound memory plane**
  - 支撑共享
  - 管理关系和时序
  - 为多个 agent / runtime 提供统一调用

### 5.3 当前真正的前沿在哪里

前沿已经不再是“谁又把向量检索调好了一点”，而是：

1. **时间结构**
   Graphiti、TiMem、LongMemEval、BEAM 指向了时间维度和超长时程 recall。
2. **实体持续建模**
   Honcho、Graphiti 把 memory 从 chunks 提升到 entity state。
3. **程序性记忆**
   Voyager、Acontext 把技能层推成一等公民。
4. **治理**
   Memoria 把版本、回滚、审计、隔离拉进主舞台。
5. **跨 agent context plane**
   mem9、ContextLoom、UltraContext 解决“记忆怎么共享和同步”。

### 5.4 两类路线的共同盲区

尽管生态已经明显进步，但仍存在共同缺口：

- **遗忘与过期策略仍弱**
  大多数系统会写入、会召回，但不太会安全地忘。
- **benchmark 与真实工程目标错位**
  benchmark 不直接测“工程师能不能修 memory”“团队能不能共享”“记忆污染后能不能恢复”。
- **跨系统可比性差**
  各家用不同模型、不同 judge、不同 cutoff、不同上下文预算。
- **provenance 与 trust 仍未成为行业默认项**
  除少数系统外，很多 memory 仍难回答“这条结论从哪来、置信度如何、能否回滚”。

---

## 6. 对 CortexMem 的直接启示

### 6.1 不要二选一，要做五层混合

| 层 | 目标 | 应借鉴的代表 |
|----|------|-------------|
| L0 原始事件层 | append-only 保存原始 observation / tool trace / transcript / artifact refs | lossless-claw, OpenViking |
| L1 文件记忆表面 | 人类可读、可局部编辑、可迁移的记忆对象 | memsearch, Acontext |
| L2 语义索引与图层 | dense + sparse + metadata + entity + temporal retrieval | mem0, Graphiti, Honcho |
| L3 程序性记忆层 | playbook / skill / executable workflow | Acontext, Voyager |
| L4 治理层 | snapshot / branch / rollback / provenance / quarantine | Memoria |

### 6.2 四条最重要的设计原则

#### 原则一：真相层必须可读

向量索引、图索引、reranker 都可以有，但 **source of truth 应该可审查**。至少对高价值长期记忆对象，要有可读表面。

#### 原则二：默认使用渐进式披露

不要默认“top-k 直接拼 prompt”。更合理的是：

1. namespace / trust filter
2. type / entity / time filter
3. search / graph expansion / rerank
4. 最小必要上下文组装

#### 原则三：程序性记忆与语义记忆分离治理

事实、偏好、摘要、操作套路、脚本、workflow 不应混成一锅。

#### 原则四：治理是内生能力，不是后补 feature

长期 memory 系统迟早会遇到污染、冲突、实验分支和恢复问题。branch、rollback、audit、quarantine 不应后补。

### 6.3 CortexMem 的优先能力方向

| 优先级 | 方向 | 为什么值得先做 |
|--------|------|---------------|
| P0 | `L0 + L1 + 基础检索` | 先让记忆可落盘、可读、可查、可扩展 |
| P0 | `progressive disclosure` | 立刻改善 token 成本和检索噪声 |
| P1 | `entity / temporal indexing` | 解决跨 session 与时间演化问题 |
| P1 | `skill memory` | 把真正高价值经验沉淀出来 |
| P1 | `governance primitives` | 为长期安全演化打底 |
| P2 | `shared memory plane + MCP/API` | 支撑多 agent 和跨产品 |

### 6.4 一个建议的最小演进顺序

1. 先做 `Markdown/structured object` 真相层和 `append-only raw episodes`
2. 再做 dense + sparse + metadata 的 hybrid retrieval
3. 再引入 entity / temporal graph 作为导航层
4. 再把程序性记忆独立成 skill / playbook 层
5. 最后把 branch / merge / rollback / provenance 做成常规操作

---

## 7. 最终判断

如果只用一句话总结本轮研究：

> **Filesystem-like 路线解决的是“让记忆成为可读、可控、可沉淀的工程资产”；vector/graph-like 路线解决的是“让记忆成为可共享、可关系化、可服务化的语义基础设施”。**

如果再进一步收敛成对 `CortexMem` 的一句话建议：

> **不要做“更大的记忆库”，而要做“可读的真相层 + 可编排的语义层 + 可演化的技能层 + 可恢复的治理层”。**

---

## 附录 A：关键问题、解决程度、SOTA 与剩余空间

### A.1 表格提炼

> 说明：`SOTA` 按“场景/基准”分别写，不给单一总冠军。`论文` 与 `官方自报` 分开标注。

| 关键问题 | 主要路线 | 当前解决程度 | 2026-04-15 公开强信号 / SOTA | 仍有空间 |
|----------|---------|-------------|-------------------------------|---------|
| 跨会话事实 recall | 两类都有 | 已较成熟，但对时间演化与冲突仍脆弱 | `Honcho` 90.4 LongMem S、89.9 LoCoMo（官方 blog 自报）；`Mem0` 在官方研究页持续强化 LongMemEval/LoCoMo 结果；`TiMem` 75.30 LoCoMo / 76.88 LongMemEval-S（论文） | 需要更强时间结构、知识更新和可解释性 |
| Coding/work session continuity | Filesystem-like 更强 | 工程实用性已很高 | `memsearch`、`OpenViking`、`lossless-claw` 是强工程样本；`OpenViking` 在官方 LoCoMo10 插件评测中给出 completion/token 强信号 | 共享协作、权限、图关系仍偏弱 |
| 程序性记忆复用 | Filesystem-like 更强 | 已证明可行，但仍未成为行业默认 | `Voyager` 的 executable skill library 是学术代表；`Acontext` 是产业化代表 | 技能验证、失效检测、版本升级仍弱 |
| 多 agent 共享脑 | Vector/graph-like 更强 | 真实需求明确，但无统一 benchmark | `ContextLoom`、`eion`、`mem9`、`UltraContext` 都给出可运行 shared context/memory plane | 权限模型、冲突解决、共享一致性仍未标准化 |
| 实体/关系/时序建模 | Vector/graph-like 更强 | 正快速推进 | `Graphiti/Zep` 是时序知识图谱代表；`Honcho` 是 entity representation 代表；`TiMem` 是时间层次化代表 | temporal reasoning 与历史版本管理仍不稳定 |
| 长上下文成本控制 | 两类都有 | 已有明显工程收益 | `Mem0` 论文/研究页持续强调 latency 与 token 节省；`OpenViking`、`memU`、`memsearch`、`Honcho` 都强调按需上下文 | 仍缺真实生产成本基准和跨系统可比性 |
| 记忆治理 / 回滚 / 审计 | Filesystem-like 当前更强 | 仍是行业短板，但方向清晰 | `Memoria` 在 snapshot / branch / rollback / quarantine / provenance 上最完整 | 需要成为行业默认能力，而不是少数系统特性 |
| 遗忘 / 过期 / 知识更新 | Vector/graph-like 略强 | 远未解决 | `LongMemEval` 已把 knowledge update / abstention 纳入 benchmark；`Graphiti`、`TiMem`、`Honcho` 有方向性优势 | 缺安全遗忘、置信度衰减和策略化淘汰机制 |

### A.2 详细补充

#### 1. 跨会话 recall 已经“能用”，但还没“可信”

今天大多数成熟系统已经能在跨会话事实 recall 上给出明显收益，但真正难点不再是“能否找到一句旧话”，而是：

- 这句话现在还对不对
- 它的时间边界是什么
- 这一结论是用户明确说的，还是系统推断的
- 多条记忆冲突时如何处理

因此，当前更像是“高可用的 recall 层”而不是“高可信的长期认知层”。

#### 2. Coding continuity 是 filesystem-like 路线最先跑通的真实场景

这类任务天然偏好：

- 人类可读
- 目录和项目结构相容
- 可 grep / 可 diff
- 能把知识、资源和技能统一到 workspace 里

这也是为什么 `memsearch`、`OpenViking`、`lossless-claw` 的工程价值非常明显。

#### 3. 多 agent 共享脑是真需求，但 industry 还没统一范式

`ContextLoom`、`mem9`、`eion`、`UltraContext` 都表明：

- 多 agent 系统无法只靠每个 agent 各自的本地 session 状态运行
- 必须有共享状态或共享上下文层

但这个方向目前仍缺：

- 权限与命名空间标准
- 冲突与并发写策略
- 标准 benchmark

#### 4. 治理是下一阶段 memory 的真正分水岭

今天很多系统“能记住”，但并不能：

- 可控地试验新记忆策略
- 在记忆污染时恢复
- 明确追踪 mutation provenance

从生产视角看，这比再多 3-5 个 benchmark 分数更关键。

---

## 附录 B：核心实现机制和原理

### B.1 表格提炼

| 机制 | 核心原理 | 代表方案 | 价值 | 代价 / 边界 |
|------|----------|---------|------|------------|
| 文件真相层 | 记忆对象以 Markdown / file / skill 落盘，便于人审阅 | memsearch, Acontext | 可读、可改、可迁移 | 共享与关系表达弱于服务层 |
| shadow index | 向量/全文索引从真相层重建 | memsearch | 检索快且不失真相层 | 需要同步和 rebuild 机制 |
| progressive disclosure | 先索引/概览，再按需展开细节 | OpenViking, memsearch, Acontext | 降 token，提解释性 | 需要更复杂的 agent tool-use |
| hierarchical context | L0/L1/L2 或时间树逐层压缩与加载 | OpenViking, TiMem | 适合长时程记忆 | consolidation 质量影响很大 |
| LLM reconciliation | 新事实与旧记忆比对，做 ADD/UPDATE/DELETE/NOOP | mem0, mem9 | 让记忆自更新 | 成本高，且受 judge/抽取质量影响 |
| representation modeling | 围绕实体形成持续状态表示 | Honcho | 更适合个体/实体长期理解 | 黑箱程度更高 |
| temporal graph | 关系带时间、历史与有效窗 | Graphiti | 更贴近真实业务状态 | 图维护和查询复杂 |
| multi-type orchestration | 核心、语义、程序、资源等记忆协同 | MIRIX | 更接近真实 agent memory | 系统复杂度高 |
| append-only + DAG compaction | 原始消息不丢，摘要 DAG 支撑恢复和扩展 | lossless-claw | 可压缩又可追溯 | 主要解决上下文管理，不等于全功能 memory |
| branch / rollback / quarantine | 把记忆 mutation 纳入版本治理 | Memoria | 可实验、可恢复、可审计 | 需要更重的基础设施和流程 |

### B.2 详细补充

#### 1. 为什么“文件真相层 + 索引缓存”值得默认采用

这是本轮研究里最稳定、最值得继承的设计原则之一：

- 真相层应便于人检查
- 检索层应便于机器加速
- 两者不要混成一个黑盒

`memsearch` 是最清晰的产业化样本：Markdown 是 source of truth，Milvus 是 rebuildable shadow index。

#### 2. progressive disclosure 比 top-k 全塞更符合 agent 工作方式

`OpenViking` 的目录递归检索、`memsearch` 的三段 recall、`Acontext` 的 `get_skill` / `get_skill_file` 都在说明同一件事：

- 真正稳定的 retrieval 往往不是“一步命中”
- 而是“先缩小空间，再按需向下钻”

#### 3. 图结构最有价值的地方不是“更酷”，而是显式表示变化关系

Graph memory 真正有价值的场景包括：

- 用户偏好发生变化
- 业务状态有历史版本
- 多个实体间存在关系和依赖
- 查询不是找一句话，而是找关系链和时间链

这正是 `Graphiti`、`Honcho`、`TiMem` 值得关注的地方。

#### 4. append-only 原始记录层应被视为基础设施

`lossless-claw` 证明了一点：

- 如果原始消息被过早压碎或覆盖，后续很多问题都无法修复

因此，`CortexMem` 的 L0 层应默认 append-only，并把上层 consolidation 视为可重建层。

#### 5. 治理不是“数据库 feature”，而是 memory semantics

`Memoria` 的真正意义在于：

- 把分支、回滚、隔离、审计从“运维附加项”变成 memory 的原生语义

这很像代码系统从“文件备份”走向 Git 的跃迁。

---

## 附录 C：面向的关键场景

| 场景 | 为什么需要 memory | 更优路线 | 合理混合形态 |
|------|------------------|---------|-------------|
| Coding Agent | 需要跨会话记住决策、代码约定、调试过程、失败经验 | Filesystem-like 起手 | 文件真相层 + shadow index + skill layer |
| Personal / Proactive Assistant | 需要长期偏好、关系、待办、提醒和主动行为 | 两类混合 | 文件偏好表面 + entity/temporal memory |
| Multi-Agent Workflow | 多 agent 必须共享状态与任务上下文 | Vector/graph-like 起手 | shared memory plane + namespaces + file artifacts |
| Enterprise Copilot | 需要把动态业务数据、用户历史和知识库统一进 agent | Vector/graph-like 更强 | graph/temporal layer + governed file truth |
| Research / Analysis Agent | 需要可追踪笔记、资源索引、可复查结论 | Filesystem-like 更强 | resource filesystem + retrieval trajectory + provenance |
| Long-running Autonomous Process | 需要持续压缩、巩固、更新和回滚 | 两类都需要 | append-only log + consolidation + governance |

### C.1 补充说明

#### Coding Agent

这个场景下最关键的不是“人格画像”，而是：

- 项目事实
- 决策历史
- 调试策略
- skill / playbook

因此，filesystem-like 路线先天占优。

#### Proactive Assistant

长期在线代理需要：

- 偏好
- 关系
- 时间线
- 待办和提醒
- 有时还需要主动触发

它需要文件层的可读性，也需要图/实体层对变化关系的表达。

#### Multi-Agent Workflow

只做本地 Markdown 不够，因为多个 agent 之间需要：

- 共享命名空间
- 并发控制
- 统一视图
- 跨终端和跨 runtime 的统一访问

因此需要 northbound memory plane。

---

## 附录 D：对 CortexMem 的启示

### D.1 关键思考提炼

| 方向 | 关键思考 | 初步价值方向 |
|------|----------|-------------|
| 文件表面 | 真相层必须可读，不要把向量库当 source of truth | 建立 `L1` 可读记忆对象层 |
| 原始事件层 | 原始 observation 不应被过早覆盖 | 建立 `L0 append-only event log` |
| 检索编排 | 默认做渐进式披露和复杂度感知召回 | 建立多阶段 retrieval pipeline |
| 图关系层 | 图首先是导航和时间关系层，不一定是重 KG | 建轻量 entity-temporal graph |
| 程序性记忆 | 高价值资产优先沉淀为 skill / playbook | 独立 `L3 skill memory` |
| 治理层 | branch / rollback / audit / quarantine 是长期生命线 | 治理内生化，而不是后补 |
| 共享平面 | 插件应尽量无状态，服务端集中治理 memory | MCP/API-first 的 northbound layer |

### D.2 可执行能力输入

#### 能力 1：L0 原始事件账本

目标：

- 保存对话、工具调用、网页观察、附件摘要、artifact refs
- append-only
- 每条记录带来源、时间、置信度和 namespace

价值：

- 为重建、审计、回滚和高层 consolidation 打基础

#### 能力 2：L1 可读记忆对象层

目标：

- 把高价值 memory 组织成 Markdown / JSON / skill objects
- 支持目录、标签、实体、时间维度索引

价值：

- 人能看懂、能修正、能迁移

#### 能力 3：多阶段检索编排

建议路径：

1. trust / namespace filter
2. entity / type / time pre-filter
3. dense + sparse + metadata retrieval
4. graph expansion
5. rerank
6. minimal-context assembly

价值：

- 减 token
- 减噪声
- 提升可解释性

#### 能力 4：程序性记忆层

目标：

- 将成功 workflow、shell pattern、debug playbook、tool-use strategy 独立存放

价值：

- 真正促进 agent capability accumulation

#### 能力 5：治理与恢复

最小语义：

- snapshot
- branch
- merge
- rollback
- diff
- provenance
- low-confidence quarantine

价值：

- 让 memory 能长期安全演进，而不是越记越危险

### D.3 初步优先级建议

| 阶段 | 重点能力 | 目标 |
|------|---------|------|
| Phase 1 | L0/L1 + hybrid retrieval + progressive disclosure | 跑通可读、可查、可扩 |
| Phase 2 | entity / temporal indexing + skill memory | 提升跨 session 和记忆复用质量 |
| Phase 3 | governance primitives + MCP/API plane | 进入多 agent / 产品级形态 |
| Phase 4 | active retrieval + adaptive forgetting + benchmark suite | 进入前沿能力竞争 |

---

## 参考与说明

- 本报告的一手来源索引见 `sources.md`
- 证据分级与主线纳入情况见 `evidence-matrix.md`
- 报告中的 SOTA 均指 **截至 2026-04-15 的公开材料强信号**
- 若数字来自官方 blog / README / 产品研究页，均应理解为 **项目自报或官方口径**，不可与论文 benchmark 直接混排
