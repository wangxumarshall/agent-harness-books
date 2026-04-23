# Agent Memory System 深度技术报告

> 研究范围：`AgentOS-Memory/fs-vector-graph/` 目录下的 Filesystem-like 与 Vector/Graph-like 两大 Agent Memory 技术路线
>
> 研究方法：基于 15 份研究文档（含 5 轮批判性评审）、28+ 产业系统分析、36 篇核心学术论文综述、源码级验证
>
> 报告目标：全面分析架构设计、数据存储机制、检索算法、更新策略及性能优化方法，提出针对性改进建议

---

## 一、系统原理分析

### 1.1 Agent Memory 的本质问题

Agent Memory 不是单一技术，而是一组不同层次的问题。本报告采用严格的定义：只有同时具备**跨会话持久化、可检索/可复用、可更新**三种能力的系统，才属于严格意义上的 Agent Memory。

当前 Agent Memory 生态存在四类本质不同的对象，它们经常被混为一谈：

| 类别 | 定义 | 典型代表 |
|------|------|---------|
| 外部持久记忆系统 | 在模型外保存用户事实、事件、技能、资源，后续任务中检索使用 | mem0、Zep/Graphiti、TiMem |
| 上下文管理/Agent 平台 | 让 agent 管理当前上下文与外部记忆层之间的切换 | Letta/MemGPT |
| 结构化/图式记忆层 | 通过图、时间层次、实体关系或多记忆类型提升检索与推理 | Graphiti、LiCoMemory、MIRIX |
| 模型原生记忆 | 直接修改 Transformer 结构、参数或注意力中的记忆原语 | Memorizing Transformers、MemoryLLM、STEM |

**核心判断**：当前证据最强的工程路线，不是"纯向量库外挂"，也不是"模型自己记住一切"，而是**外部持久记忆 + 结构化索引/时间结构 + 检索/压缩/治理策略**。

### 1.2 两大技术路线的分化逻辑

Agent Memory 领域出现了两条清晰的技术分化路线，它们解决的是不同层级的问题：

#### Filesystem-like Agent Memory

**根本价值**：把记忆重新拉回可读、可控、可迁移的工程对象。

这类系统的出现不是因为大家突然喜欢 Markdown，而是因为传统 memory/RAG 方案在 Agent 场景里暴露了四类真实问题：

1. **Coding Agent 跨会话"失忆"且记忆不可读**：memsearch 直接瞄准此痛点——过去的讨论没有稳定落盘，落盘后人类也看不懂，不同 Agent 各写各的本地状态
2. **24/7 proactive agent 必须持续在线但 token 成本不能线性爆炸**：memU 明确强调长时间运行、持续捕捉用户意图、通过更小上下文压低成本
3. **Agent 上下文散落在代码、资源、技能、工具结果里，RAG 很黑箱**：OpenViking 把这一痛点说得很透——检索链条不透明，出问题时工程师看不到根因
4. **真正可复用的长期能力常常不是一句总结，而是一段可执行技能**：Acontext 和 Voyager 都直指同一问题——经验能不能变成可执行资产

#### Vector/Graph-like Agent Memory

**根本价值**：为多 Agent 和复杂检索提供共享语义平面。

这类系统解决的核心问题是**可共享、可扩展、可关系化**：

1. **多 Agent 框架各有状态但彼此失忆**：ContextLoom 把问题定义为 multi-agent systems 的"shared brain"
2. **多个 Agent 串行或并行协作时缺少统一 memory/knowledge graph**：eion 为 multi-agent systems 提供 shared memory storage
3. **个性化 agent 不只是记住消息，还要持续建模"实体"**：honcho 把记忆看成关于 users/agents/groups/ideas 等实体的持续状态建模
4. **生产级 AI 应用需要通用 memory layer**：mem0 的定位是 universal, self-improving memory layer

### 1.3 两类路线的分工关系

两类路线不是替代关系，而是分工关系：

- **Filesystem-like** 更像 **southbound** 的人类可读 memory surface——擅长让人和 agent 一起看懂、修正和沉淀记忆
- **Vector/Graph-like** 更像 **northbound** 的共享语义/关系 memory plane——擅长让多个 agent 和产品系统在统一平面上调用记忆

---

## 二、架构设计深度分析

### 2.1 Filesystem-like 路线的架构共性

#### 共性一：人类可读文件作为源头真相

在这类系统里，Markdown 不是导出格式而是主存格式，技能文件不是附属物而是核心记忆单元，文件树不是 UI 皮肤而是信息组织方式。这带来三个后果：便于审计、便于 git/version control、便于跨 Agent 跨模型迁移。

#### 共性二：向量检索退居为加速层

典型形态：
- **memsearch**：Markdown 是 source of truth，Milvus 是可重建的 shadow index
- **OpenViking**：目录定位 + 语义搜索 + 递归获取，而不是纯 top-k
- **Memoria**：vector + full-text hybrid retrieval，但版本化对象才是核心

Vector retrieval 退居为**加速层**，而不是**真相层**。

#### 共性三：渐进式披露优于一次性 top-k 拼上下文

Filesystem-like memory 天然适合 progressive disclosure：先看目录→再看概览→再按需拉取细节。这比"一次性 top-k 拼上下文"更符合人类与 Agent 协同的实际工作方式。

#### 共性四：程序性记忆是一等公民

这类系统更容易把操作套路、工作流模板、调试经验、工具调用策略沉淀成 skill 或 code artifact，而不只是文字摘要。

#### 共性五：治理与版本化更容易落地

当记忆是文件、目录、版本对象时，diff/branch/rollback/quarantine/provenance/规则化组织更自然。

#### 共性六：append-only 原始记录 + 分层摘要

这是反复出现的合理结构：原始 episode/transcript 不应轻易覆写，面向召回的摘要层可以逐步压缩和重组，人类可读的索引层应当独立于原始记录存在。

### 2.2 Vector/Graph-like 路线的架构共性

#### 共性一：memory 做成 northbound service/API/shared plane

主接口通常不是文件树，而是 SDK/REST API/managed service/shared Redis/DB context plane/MCP integration。

#### 共性二：语义召回和结构化召回共同出现

引入 vector + keyword hybrid search、entity representation、session context、graph traversal、knowledge graph/temporal graph。

#### 共性三：共享命名空间与隔离机制成为一等配置

哪些 agent 共享同一 memory pool、哪些只读、哪些 tenant 隔离、哪些 guest access、哪些 workspace/scopes。

#### 共性四：后台 consolidation/representation 更常见

在后台生成 representation、summary、entity state、relation edge、session context，让检索结果不仅是文档片段，而是"关于某个对象的结构化认识"。

#### 共性五：规模化与多 Agent 协作优先于人类直接编辑

擅长共享/并发/服务治理/大规模接入，但代价是人类直接编辑不如文件型直观、黑箱风险更高。

### 2.3 Cortex-Mem 五层混合架构设计

基于两类路线的研究，推导出 Cortex-Mem 的合理架构：

```
┌─────────────────────────────────────────────────────────┐
│                    L4 治理与版本层                        │
│    snapshot / branch / merge / rollback / audit trail   │
├─────────────────────────────────────────────────────────┤
│                    L3 程序性/技能层                       │
│    skill memory / playbook / 可执行技能                  │
├─────────────────────────────────────────────────────────┤
│                 L2 Vector/Graph 语义索引层               │
│    shadow index / dense retrieval / graph traversal     │
├─────────────────────────────────────────────────────────┤
│              L1 Filesystem-like 记忆表面                 │
│    Markdown / resource file / skill file / 版本对象     │
├─────────────────────────────────────────────────────────┤
│                    L0 原始事件层                          │
│    append-only event log / provenance                   │
└─────────────────────────────────────────────────────────┘
```

| 层 | 借鉴来源 | 目标 |
|----|---------|------|
| 文件表面层 | OpenViking / memsearch / Acontext | 可读、可调试、可迁移 |
| 技能层 | Acontext / Voyager | 经验复用、程序性记忆 |
| 主动记忆层 | memU | 后台监控、意图捕捉、长期连续性 |
| 北向语义层 | mem0 / mem9 / ContextLoom | 通用 API、共享 memory pool、跨框架接入 |
| 图关系层 | eion / honcho | 实体关系、时序、表示层 |
| 治理层 | Memoria | 审计、分支、回滚、隔离 |

---

## 三、源代码关键模块解读

### 3.1 OpenViking：虚拟文件系统范式

**源码结构**：
```
crates/ov_cli/          # Rust CLI 工具
viking:// 协议实现       # 虚拟文件系统协议
自动 Session 管理       # 记忆自迭代回路
```

**核心架构——viking:// 协议**：
```
viking://
├── memory/
│   ├── session/     # 会话记忆
│   ├── task/       # 任务记忆
│   └── long_term/  # 长期记忆
├── resources/
│   ├── docs/       # 文档资源
│   ├── code/       # 代码资源
│   └── knowledge/  # 知识库
└── skills/
    ├── tools/      # 工具能力
    └── workflows/  # 工作流
```

**三层加载策略**：

| 层级 | 内容 | Token 占比 | 加载时机 |
|------|------|-----------|----------|
| L0 | 核心摘要 ~100 tokens | ~5% | 始终加载 |
| L1 | 结构化摘要 ~2k tokens | ~25% | 按需加载 |
| L2 | 完整原始内容 | 100% | 精确查询时 |

**关键模块**：
- 目录递归检索 + 语义预滤
- 可视化 retrieval trajectory
- 自动压缩 session 内容，提取长期记忆，形成自迭代回路

### 3.2 memsearch：Markdown-first + Shadow Index

**核心架构**：
```
memory/
├── MEMORY.md              # 手写的长期记忆
├── 2026-02-09.md          # 今天的工作日志
├── 2026-02-08.md
└── .memsearch/            # 向量索引缓存（可重建）
```

**三层渐进检索**：
1. **L1 Search** → `memsearch search` → rank chunks
2. **L2 Expand** → `memsearch expand <chunk_hash>` → full section
3. **L3 Transcript** → parse raw session JSONL

**关键模块**：
- **混合搜索**：BM25 + Dense Vector + RRF Reranking
- **SHA-256 内容去重**：只对变化内容重新嵌入
- **文件监听器**：实时同步 Milvus shadow index
- **本地 ONNX 嵌入模型**：bge-m3，约 558 MB，降低云依赖

### 3.3 mem0：LLM 驱动的智能记忆管理系统

**源码验证的核心架构——两阶段处理**：

```
Extraction Phase（记忆提取）
    ↓
接收对话消息 + 检索历史摘要上下文
    ↓
LLM (GPT-4o-mini) 提取原子事实
    ↓
Update Phase（记忆决策）
    ↓
候选记忆 vs 已有记忆 → LLM 决策：
    - ADD: 新信息直接添加
    - UPDATE: 补充/更新现有记忆
    - DELETE: 删除矛盾记忆
    - NOOP: 重复信息不操作
```

**存储范式**：双重存储——向量数据库 + 图数据库
- 通过 `VectorStoreFactory` 支持 15+ 种向量数据库
- 通过 `GraphStoreFactory` 支持知识图谱存储
- 核心存储机制：**图内存**，将记忆表示为有向标记图 G = (V, E, L)

**关键创新**：使用 LLM 作为"记忆决策机"，而非简单的向量相似度匹配。

### 3.4 mem9：两段式提取流水线

**源码验证的核心架构**：

```
Step 1: 事实提取（Fact Extraction）
    ↓
对话结束后，插件发送聊天记录到服务端
    ↓
LLM 从用户消息提取原子事实（只提取用户说的，不提取 AI 回复）
    ↓
Step 2: 记忆调和（Memory Reconciliation）
    ↓
新事实 vs 已有记忆 → LLM 决策：
    - ADD: 全新事实
    - UPDATE: 有变化需更新
    - DELETE: 矛盾标记过时
    - NOOP: 已记录不重复
```

**技术细节**：
- 单次最多提取 50 条事实，检索 60 条已有记忆比对
- 记忆带"年龄"标签（"3 天前"、"2 周前"），冲突时老记忆优先被判定过时
- 防幻觉设计：真实 UUID 替换为整数 ID 供给 LLM
- 5 个核心工具：`memory_store / memory_search / memory_get / memory_update / memory_delete`

### 3.5 memU：类文件系统记忆架构

**核心架构**：
```
memory/
├── preferences/
│   ├── communication_style.md
│   └── topic_interests.md
├── relationships/
│   ├── contacts/
│   └── interaction_history/
├── knowledge/
│   ├── domain_expertise/
│   └── learned_skills/
└── context/
    ├── recent_conversations/
    └── pending_tasks/
```

**五种记忆类型标签**：

| 标签 | 类型 | 示例 |
|------|------|------|
| [P] | Profile | 用户身份、偏好、稳定特征 |
| [E] | Event | 具体事件、时间、结果、教训 |
| [K] | Knowledge | 客观知识、技术事实 |
| [B] | Behavior | 行为模式、工作习惯 |
| [S] | Skill | 踩坑经验、技术方案 |

**核心 API**：
```python
result = await service.memorize(
    resource_url="chat_history.json",
    modality="conversation",
    user={"user_id": "123"}
)

context = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "用户偏好？"}}],
    method="rag"  # 或 "llm" 深度推理
)
```

### 3.6 Acontext：Skill Memory Layer

**核心流程**：
1. 自动从 agent run 中提取 learnings
2. 在任务完成或失败时触发 distillation
3. 由 skill agent 决定更新已有 skill 还是创建新 skill
4. 用 `SKILL.md` 定义结构
5. 召回不依赖 embedding top-k，而是依赖 `list_skills / get_skill / get_skill_file` 等逐层获取

**运行参数**：
- 2 个官方 SDK：Python 与 TypeScript
- skill 学习是后台异步过程，常见延迟约 10-30s
- runtime 默认 `DEFAULT_TASK_AGENT_MAX_ITERATIONS=4`
- 生产推荐 buffer 为 24-32 turns、TTL 为 6-10s

### 3.7 lossless-claw：DAG 摘要系统

**核心机制**：
```
SQLite DB
├── messages/           # 原始消息（永不丢失）
├── leaf_summaries/    # 叶子层摘要
├── d1_summaries/      # 一级摘要
└── d2_summaries/      # 二级摘要
```

**上下文组装**：
- Fresh Tail：最近 N 条原始消息（默认 64 条）
- Summary DAG：层级摘要结构
- 动态展开：Agent 可随时 `lcm_expand` 查看原文

**检索工具**：
- `lcm_grep` - 全文搜索
- `lcm_describe` - 查看摘要详情
- `lcm_expand` - 展开摘要恢复原文

### 3.8 ContextLoom：Redis-First 共享上下文

**核心架构**：
- Redis-first memory backend
- decouple memory from compute
- 从 PostgreSQL / MySQL / MongoDB 拉冷启动数据
- communication cycle + cycle hash
- 检测 loop/repetition 并推动 agent pivot

### 3.9 eion：统一知识图谱共享存储

**核心架构**：
- PostgreSQL + pgvector 负责 memory storage 与 semantic search
- Neo4j 负责 knowledge graph
- unified API
- register console 管理 agents、permissions、resource snippets
- 支持 sequential agency、live agency、guest access
- 384 维 embedding（all-MiniLM-L6-v2）
- 4 个 memory MCP tools + 4 个 knowledge MCP tools

### 3.10 honcho：Entity-Aware State Modeling

**核心抽象**：
- workspace / peer / session
- 持续维护实体状态
- `chat` 直接对实体提问
- `search` 查找相似消息
- `context` 生成 session-scoped context
- `representation` 获取某个 peer 在特定 session 下的状态表示

**示例**：
```python
alice.chat("What learning styles does the user respond to best?")
session.context(summary=True, tokens=10_000)
```

### 3.11 Memoria：Git for AI Agent Memory

**核心机制**：
- snapshot / branch / merge / rollback
- Copy-on-Write 驱动的 memory mutation 管理
- vector + full-text hybrid retrieval
- contradiction detection
- low-confidence memory quarantine
- provenance chain + full audit trail

---

## 四、论文核心观点提炼

### 4.1 CoALA（arXiv:2309.02427）：认知架构奠基框架

**核心观点**：语言 agent 应被理解为带有模块化记忆组件、结构化动作空间、广义决策过程的认知架构。

**关键贡献**：
1. 定义了 **Observe → Think → Act → Learn** 循环
2. 工作记忆/长期记忆二分
3. 语义/情景/程序性三分

**对工程的最大启示**：记忆不是单表存储而是多模块协作；记忆、行动、外部环境访问是统一闭环。很多系统根本不在解决同一层的问题，把它们混成一个榜单是当前许多报告失真的根本原因。

### 4.2 MemGPT/Letta（arXiv:2310.08560）：虚拟上下文管理

**核心观点**：通过不同 memory tiers 的数据移动，让 LLM 在有限 context window 下表现出更长记忆。

**关键贡献**：
- virtual context management 概念
- Letta 当前产品化：stateful agents、memory blocks、shared memory、archival memory、context hierarchy

**批判性审视**：更适合视为"让 agent 主动管理记忆层级的框架"，而不是独立 benchmark leader。"OS"隐喻是营销而非技术实现——它实现的是"LLM 按需换页"的被动管理模式。

### 4.3 TiMem（arXiv:2601.02845）：时间层次化记忆树

**核心观点**：长期记忆应按时间尺度分层组织，查询复杂度不同，召回层级也应不同。

**关键创新**：
- **5 层时序记忆树**：L1 事实层 → L2 会话层 → L3 日模式层 → L4 周趋势层 → L5 人格画像层
- **Complexity-Aware Recall**：简单问题只检索浅层，复杂问题才往深层找，**无需 LLM 决策即可实现分层路由**
- **Semantic-Guided Consolidation**：从原始观察逐级向上抽象到 persona representations
- 理论基础来自**互补学习系统理论（CLS）**：海马体到新皮层转移的系统巩固机制

**基准结果**（论文自报）：LoCoMo 75.30%、LongMemEval-S 76.88%、Recalled Memory Length 降低 52.20%

**最大启示**：northbound memory plane 不能只有 top-k recall，还要有时间尺度感知。复杂度感知召回为"零成本路由"提供了新思路。

### 4.4 LiCoMemory（arXiv:2511.01448）：轻量认知图谱

**核心观点**：图不一定要做成重型知识图谱，也可以是轻量认知索引层。图的主要职责可以是导航和候选缩减，而不是全量推理引擎。

**关键创新**：
- **CogniGraph**：lightweight hierarchical graph
- **temporal / hierarchy-aware search + reranking**

**最大启示**：结构化层不一定要上重型 KG；轻量图能在表达力和运维复杂度之间找到更好的平衡。很多场景并不需要全量知识图推理，而只需要把"谁、何时、与什么相关"组织清楚。

### 4.5 MIRIX（arXiv:2507.07957）：多类型记忆编排

**核心观点**：vector/graph-like memory 真正走向成熟时，不会只剩一个统一 embedding 池，而会出现更明确的 memory type orchestration。

**关键创新**：
- **6 类记忆类型**：Core、Episodic、Semantic、Procedural、Resource、Knowledge Vault
- **Active Retrieval**：Agent 不被动等待查询，主动关联所有记忆类型，减少 87% 的 API 调用
- **多 Agent 协调**：由 controller 编排不同 memory types 的读写与协调

**基准结果**（论文自报）：LoCoMo 85.4%

**最大启示**：Active Retrieval 理念（自动跨类型检索）是核心设计之一。但写入路径更长，类型冲突更难治理。

### 4.6 EverMemOS（arXiv:2601.02163）：自组织记忆操作系统

**核心观点**：借鉴 engram 生命周期理论，构建三阶段自组织记忆流程。

**关键创新**：
- **Episodic Trace Formation** → **Semantic Consolidation** → **Reconstructive Recollection**
- **MemCells**：基本记忆单元
- **MemScenes**：场景级记忆组织

**重大发现**：论文声称 LoCoMo 93.05%、LongMemEval 83.00%，但独立用户在 GitHub issue #73 报告仅复现出 **38.38%**（差距 -54.62pp），该 issue 至今 open。

**正确处理**：保留方法论启发（engram lifecycle 概念有启发），不将其高分结果写入主结论。证据等级 C。

### 4.7 Zep/Graphiti（arXiv:2501.13956）：时序知识图谱

**核心观点**：长期记忆的正确数据结构，不应只包含"文本内容"，还应包含时间、失效机制与来源链条。

**关键创新**：
- **事实有效期（Validity Window）**：跟踪事实如何随时间变化
- **Source Provenance**：为每个实体与关系保留来源链条
- **混合检索**：semantic + keyword + graph traversal 三路检索

**基准结果**（论文自报）：DMR 94.8% vs MemGPT 93.4%；LongMemEval 最高 +18.5% 准确率提升

**最大启示**：长期记忆系统最常见错误不是"完全找不到"，而是找到了旧事实、过期事实、时间顺序错误的事实、零散片段却无法重建事件链。

### 4.8 Voyager（arXiv:2305.16291）：程序性/技能记忆

**核心观点**：在开放世界任务里，长期记忆最稳的形态常常不是摘要，而是可执行代码技能。

**关键创新**：
- 自动课程生成
- 环境交互后总结成功/失败经验
- 将技能沉淀为 **executable code skill library**
- 下次任务优先复用已有 skill

**基准结果**：Minecraft 中 3.3x 更多独特物品、15.3x 更快达成科技树里程碑

**最大启示**：某些长期能力无法被自然语言描述充分压缩，最稳健的"记忆"形态是可执行、可组合、可验证的技能单元。

### 4.9 模型原生记忆三大范式

| 维度 | KV 缓存检索（推理前） | MSA 稀疏注意力（推理中） | MemoryLLM 参数内化 |
|------|---------------------|------------------------|-------------------|
| 记忆时机 | 推理前压缩/选择 | 推理中实时检索 | 预训练/后训练期间写入 |
| 记忆载体 | KV cache 向量 | 外部/稀疏 KV 对 | 模型参数(权重) |
| 持久性 | 无状态(单次推理) | 无状态(单次推理) | 永久(跨会话) |
| 可解释性 | 中 | 中 | 无(隐式参数编码) |
| 容量 | 受 GPU 显存限制 | 百万-亿级 tokens | 受参数预算限制 |
| 与外部记忆关系 | 互补 | 互补 | 互补 |

**关键判断**：模型原生记忆与外部 agent memory 不是互斥关系，而是不同层级。完整栈通常是：**参数记忆/架构记忆 + 推理期上下文机制 + 外部持久用户记忆**。

---

## 五、数据存储机制对比

### 5.1 存储范式分类

| 范式 | 代表系统 | 优势 | 劣势 |
|------|---------|------|------|
| 扁平向量 | mem0 基础版 | 语义召回强 | 缺乏结构化推理 |
| 会话时序 | Zep/Graphiti | 时间感知 | 复杂度高 |
| 图数据库 | eion | 关系建模强 | 部署重 |
| 文件目录树 | OpenViking | 人类可读 | 共享能力弱 |
| Markdown-first | memsearch | 可审计可迁移 | 图关系弱 |
| SQLite + DAG | lossless-claw | 无损压缩 | 扩展性受限 |
| Redis-first | ContextLoom | 实时共享 | 关系建模弱 |
| TiDB 混合 | mem9 | 云端共享 | 本地可编辑性弱 |

### 5.2 检索机制分类

| 机制 | 适用场景 | 代表系统 | 技术细节 |
|------|---------|---------|---------|
| 向量相似度 | 语义召回 | mem0 | dense embedding + cosine similarity |
| 关键词 BM25 | 精确匹配 | memsearch | full-text search |
| 混合检索 | 平衡召回 | OpenViking、memsearch | dense + BM25 + RRF |
| 目录浏览 | 层次导航 | Acontext | list_skills → get_skill → get_skill_file |
| 图遍历 | 关系推理 | eion | Neo4j traversal |
| 复杂度感知 | 分层路由 | TiMem | 简单→浅层，复杂→深层，零 LLM 开销 |
| Active Retrieval | 多类型协同 | MIRIX | 自动跨类型检索，减少 87% API 调用 |
| DAG 展开 | 无损回溯 | lossless-claw | lcm_expand 恢复原文 |

---

## 六、更新策略与治理机制

### 6.1 记忆更新策略对比

| 策略 | 代表系统 | 机制 | 优劣 |
|------|---------|------|------|
| LLM 决策机 | mem0、mem9 | ADD/UPDATE/DELETE/NOOP 四路决策 | 精确但成本高 |
| 后台蒸馏 | Acontext | 任务完成/失败后异步蒸馏为 skill | 低干扰但有延迟 |
| 文件监听同步 | memsearch | file watcher 实时同步 shadow index | 实时但依赖文件系统 |
| Copy-on-Write | Memoria | 快照 + 分支 + 合并 | 安全但存储开销大 |
| DAG 增量摘要 | lossless-claw | 原始消息不丢失，逐层压缩 | 无损但结构复杂 |
| 时间层次巩固 | TiMem | L1→L2→L3→L4→L5 逐级抽象 | 理论扎实但 L2-L5 需 LLM |
| 事实有效期 | Zep/Graphiti | validity window + provenance | 时间感知但维护复杂 |

### 6.2 治理能力现状

| 治理能力 | 具备的系统 | 缺失的系统 |
|---------|-----------|-----------|
| 版本控制/回滚 | Memoria | 大多数系统 |
| 写入溯源(provenance) | Zep/Graphiti、Memoria | 大多数系统 |
| 冲突检测 | Memoria | 大多数系统 |
| 低置信隔离 | Memoria | 大多数系统 |
| 命名空间隔离 | eion、mem9 | memsearch、Acontext |
| 审计追踪 | Memoria、mem9 | 大多数系统 |
| 遗忘/过期 | Zep/Graphiti(validity window) | 大多数系统 |

**核心发现**：大多数系统擅长"写入"和"召回"，但不擅长"治理"。遗忘与记忆治理仍然普遍缺位。

---

## 七、性能优化方法

### 7.1 Token 效率优化

| 方法 | 代表系统 | 效果 |
|------|---------|------|
| 分层加载(L0/L1/L2) | OpenViking | 输入 token 降低 83%-91% |
| 稀疏记忆读写 | mem0 | token 节省 90%+ |
| 更小上下文 | memU | comparable usage 约 1/10 |
| 渐进式披露 | memsearch、Acontext | 按需加载，避免全量拼入 |
| 复杂度感知召回 | TiMem | recalled memory length 降低 52.20% |
| DAG 压缩 | lossless-claw | 保留原始但压缩上下文 |

### 7.2 检索效率优化

| 方法 | 代表系统 | 效果 |
|------|---------|------|
| 混合检索(BM25+Dense+RRF) | memsearch | 平衡精确与语义 |
| 目录递归+语义预滤 | OpenViking | 比扁平检索更容易拿到任务完成率收益 |
| 图导航+候选缩减 | LiCoMemory | 轻量图替代重型 KG |
| Redis sub-millisecond | ContextLoom | 实时共享场景 |
| Active Retrieval | MIRIX | 减少 87% API 调用 |

### 7.3 Benchmark 数据汇总与正确解读

| 系统 | LoCoMo | LongMemEval | 证据等级 | 正确解读 |
|------|--------|-------------|---------|---------|
| mem0 | +26% vs OpenAI Memory | - | B | LLM-as-a-Judge 指标，非 exact-match |
| TiMem | 75.30% | 76.88%(S) | B | 论文自报，但口径清晰 |
| MIRIX | 85.4% | - | A | 自定义任务胜出，跨系统不可比 |
| Zep/Graphiti | 85.22% | 63.80% | A | 证据较强 |
| EverMemOS | 93.05% | 83.00% | C | 独立复现失败(38.38%)，严重存疑 |
| honcho | 89.9% | 90.4%(LongMem S) | B | 官方博客自报 |
| OpenViking | +43%-49% improvement | - | A | 项目 README 自报，相对 OpenClaw |

**方法论警示**：
1. 不同 benchmark（LoCoMo、LongMemEval、LongMemEval-S、DMR）测的是不同能力，不能直接混排
2. 不同 metric（accuracy、F1、BLEU-1、LLM-as-a-Judge）不能直接并列排名
3. 不同论文使用不同基础模型、embedding、judge model、context budget
4. 产品版本与论文版本可能漂移

---

## 八、安全分析

### 8.1 攻击面分析

**AgentPoison（arXiv:2407.12784）**：
- 目标：generic and RAG-based LLM agents
- 攻击方式：poisoning long-term memory or RAG knowledge base
- 不需要额外训练或微调
- 平均 attack success rate 高于 80%
- benign performance 影响低于 1%
- poison rate 低于 0.1%

**eTAMP（arXiv:2604.02623）**：
- 更现实的威胁模型：环境观察污染
- 只需要 agent 观察到一次被污染环境
- 可以实现 cross-session、cross-site compromise
- ASR 最高可到 32.5%
- frustration exploitation 条件下 ASR 可提高最多 8 倍

### 8.2 生产级 memory system 应具备的安全能力

1. **写入 provenance**：每条记忆要知道来自哪条对话、哪个页面、哪个工具调用、哪个时间点
2. **source trust / namespace isolation**：用户事实、网页观察、工具输出、第三方文档至少不能放在同一信任层
3. **失效与冲突管理**：系统必须能表达"曾经为真，但现在失效"
4. **可审计与可回滚**：回滚不是高级功能，而是污染修复能力
5. **在线写入与后台 consolidation 分离**：高风险观测先进入隔离层

---

## 九、现有实现的优势与不足

### 9.1 Filesystem-like 路线

**核心优势**：
- 人类可读、可审计、可修正
- 便于 git/version control
- 适合沉淀 skill/SOP/code artifact
- 更贴近 coding agent 和本地工作区
- 更容易做渐进式披露和层次浏览
- 程序性记忆是一等公民

**核心短板**：
- 大规模共享与服务化不如 northbound memory plane 顺手
- 多实体关系推理天然弱于图结构
- 一旦 schema/file layout 设计不好，目录会变脏
- 在多 Agent 并发写入时，需要更强治理机制

### 9.2 Vector/Graph-like 路线

**核心优势**：
- 多 Agent 共享更自然
- 更适合 northbound service 化
- 语义召回与关系推理能力更强
- 易于做多租户、权限、tenant、workspace
- 更适合规模化生产接入

**核心短板**：
- 人类可读和直接编辑能力通常较差
- provenance 若设计不足，会形成更深黑箱
- 图/向量基础设施会提高部署复杂度
- 容易把"记忆"退化成难以审计的 embedding 池

### 9.3 两类路线的共同盲区

#### 盲区一：遗忘与记忆治理普遍缺位

无论是 filesystem-like 还是 vector/graph-like，真正把过期判定、冲突解决、低置信内容隔离、回滚、清理策略做完整的系统都很少。

#### 盲区二：安全治理远落后于记忆能力

大多数系统还没有把长期记忆当作高风险面来设计，而只是当作增强 recall 的功能模块。

#### 盲区三：benchmark 经常衡量不了真正的工程价值

LoCoMo、LongMemEval 更多测的是长期召回与问答正确率，并不直接衡量工程师能否修 memory、团队能否共享 memory、memory 被污染后能否回滚、程序性经验能否稳定复用。

#### 盲区四：很多"强结论"建立在不可比口径上

同一系统的论文口径、项目 README 口径、独立复现实验可能完全不同；不同系统使用的 benchmark、judge model、上下文预算和基座模型也经常不同。

---

## 十、改进建议

### 10.1 架构层面

#### 建议 1：采用"文件表面 + 语义索引 + 图关系 + 版本治理"的混合架构

不应在两类路线中二选一。Cortex-Mem 的五层架构（L0 原始事件 → L1 文件表面 → L2 语义索引 → L3 技能层 → L4 治理层）是目前最合理的设计方向。

#### 建议 2：将 KV Cache 语义淘汰纳入记忆系统统一管理

当前没有任何竞品将感知层（KV Cache）纳入记忆系统。将 L0 感知层纳入可实现"感知→工作→认知"全栈覆盖，这是差异化优势。

#### 建议 3：引入复杂度感知召回机制

借鉴 TiMem 的 CLS 理论，实现三级检索路径：
- **简单路径**：BM25/向量检索，零 LLM 开销
- **关系路径**：图遍历，1 次 LLM 调用
- **推理路径**：LLM 空间推理，多轮 LLM 调用

### 10.2 存储层面

#### 建议 4：Markdown 是真相，向量索引是缓存

memsearch 的"Markdown 是 source of truth，Milvus 是可重建的 shadow index"应成为基本原则。向量检索退居为加速层，而不是真相层。

#### 建议 5：采用 append-only 原始记录 + 分层摘要结构

原始 episode/transcript 不应轻易覆写，面向召回的摘要层可以逐步压缩和重组，人类可读的索引层应当独立于原始记录存在。

#### 建议 6：引入轻量认知图谱而非重型知识图谱

借鉴 LiCoMemory 的 CogniGraph 思路，图的主要职责是导航和候选缩减，而不是全量推理引擎。

### 10.3 检索层面

#### 建议 7：默认采用 progressive disclosure 而非一次性 top-k

先看目录→再看概览→再按需拉取细节，比"一次性 top-k 拼上下文"更符合实际工作方式。

#### 建议 8：引入 Active Retrieval 机制

借鉴 MIRIX，Agent 不应被动等待查询，而应主动关联所有记忆类型，在用户输入时自动触发跨类型检索。

#### 建议 9：实现四阶段读路径

1. 命名空间与信任过滤
2. 时间/实体/类型过滤（先缩小候选集合）
3. 语义检索 + 结构扩展 + rerank
4. 最小必要上下文拼装

### 10.4 更新与治理层面

#### 建议 10：内建版本治理和 provenance ledger

借鉴 Memoria，记忆更新不应只有 overwrite，要有 branch/merge/rollback 语义。安全治理不是附属功能，而是 memory system 的一等公民。

#### 建议 11：采用双路径写策略

- **在线写入路径**：记录原始 episode，允许低风险事实快速写入
- **后台 consolidation 路径**：周期性抽取稳定语义、合并画像、发现技能、处理冲突与失效

#### 建议 12：实现四层安全闭环

1. **预防**：写入 provenance + source trust + namespace isolation
2. **检测**：contradiction detection + anomaly detection
3. **隔离**：low-confidence quarantine + sandbox
4. **恢复**：snapshot/branch/rollback + audit trail

### 10.5 工程层面

#### 建议 13：提供 northbound memory API/SDK

Cortex-Mem 需要 northbound SDK/API，而不只是本地文件层。通用 memory layer 必须有足够好的接入体验，否则很难进入实际产品。

#### 建议 14：插件无状态、后端有状态

借鉴 mem9 的边界划分：插件无状态，后端有状态。这样运维边界更清晰，也更容易做跨终端共享。

#### 建议 15：程序性记忆与语义记忆分离治理

借鉴 Acontext/Voyager，程序性记忆应该独立于语义记忆存在。长期高价值资产要优先沉淀为"可执行技能"而不是长文本总结。

### 10.6 评测层面

#### 建议 16：拒绝统一 SOTA 排名表，采用场景化评测

- 先问：比较的是不是同一类系统？
- 再问：benchmark、metric、模型底座是否一致？
- 最后才问：数字是否值得横向解读？

#### 建议 17：建立自定义工程 benchmark

除了 LoCoMo/LongMemEval，还应衡量：
- 工程师能否修 memory
- 团队能否共享 memory
- memory 被污染后能否回滚
- 程序性经验能否稳定复用
- 安全攻击能否被检测和隔离

### 10.7 行动路线

| 阶段 | 交付 | 验证目标 |
|------|------|---------|
| MVP | L1-L3 Markdown + FTS5 + 复杂度感知召回 | LoCoMo >75% |
| Phase 2 | 5 层完整架构 + 安全内生 + Active Retrieval + MCP Server | LoCoMo >85% |
| Phase 3 | 场景适配器 + 多 Agent 总线 + 自定义 Benchmark | 3 场景可用 |
| Phase 4 | User as Code + 多模态 + AI 自主优化 + 模型原生联动 | 前沿 |

---

## 十一、结论

### 11.1 一句话总结

**Filesystem-like agent memory 解决的是"让记忆成为可读、可控、可沉淀的工程资产"；vector/graph-like agent memory 解决的是"让记忆成为可共享、可语义化、可关系化的北向基础设施"。**

### 11.2 六个核心判断

1. Filesystem-like memory 的根本价值不是"替代向量检索"，而是把记忆重新拉回可读、可控、可迁移的工程对象
2. Vector/graph-like memory 的根本价值不是"存更多 embedding"，而是为多 Agent 和复杂检索提供共享语义平面
3. 两类系统分别擅长不同问题：前者擅长可观测性与技能沉淀，后者擅长共享、规模化与关系建模
4. 两类系统都在逐步走向混合：filesystem-like 开始引入 shadow index、hybrid retrieval；vector/graph-like 开始补充 provenance、治理和可视化
5. Cortex-Mem 不应二选一，而应做"文件表面 + 语义索引 + 图关系 + 版本治理"的混合架构
6. 安全与治理不是附属问题，而是记忆系统的内生要求

### 11.3 最终方向

Cortex-Mem 最合理的方向不是站队，而是融合：
- 以 filesystem-like 路线保证可读、可审计、可技能化
- 以 vector/graph-like 路线保证共享、关系化、服务化
- 以 Memoria 式治理层保证长期安全演进

这比单纯做"更大的记忆库"更接近真正可用的 Agent Memory System。

---

## 附录 A：证据等级定义

| 等级 | 含义 |
|------|------|
| **A** | 官方文档、官方仓库、论文/技术说明能够相互印证 |
| **B** | 有官方仓库或文档，但很多效果仍是项目自报 |
| **C** | 有官方入口，但技术实现、产品包装、评测口径不完全稳定 |
| **X** | 未找到足够稳定的一手技术材料，只能作弱证据处理 |

## 附录 B：核心参考来源

### 产业系统
- OpenViking: https://github.com/volcengine/OpenViking
- memsearch: https://github.com/zilliztech/memsearch
- memU: https://github.com/NevaMind-AI/memU
- Acontext: https://github.com/memodb-io/Acontext
- Memoria: https://github.com/matrixorigin/Memoria
- mem0: https://github.com/mem0ai/mem0
- mem9: https://github.com/mem9-ai/mem9
- ContextLoom: https://github.com/danielckv/ContextLoom
- eion: https://github.com/eiondb/eion
- honcho: https://github.com/plastic-labs/honcho

### 核心论文
- CoALA: arXiv:2309.02427
- MemGPT: arXiv:2310.08560
- Voyager: arXiv:2305.16291
- LoCoMo: arXiv:2402.17753
- LongMemEval: arXiv:2410.10813
- mem0: arXiv:2504.19413
- Zep/Graphiti: arXiv:2501.13956
- TiMem: arXiv:2601.02845
- LiCoMemory: arXiv:2511.01448
- MIRIX: arXiv:2507.07957
- EverMemOS: arXiv:2601.02163
- AgentPoison: arXiv:2407.12784
- eTAMP: arXiv:2604.02623
- MemoryLLM: arXiv:2402.04624
- STEM: arXiv:2601.10639
- Memorizing Transformers: arXiv:2203.08913
