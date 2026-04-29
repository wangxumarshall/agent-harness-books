# OpenClaw 记忆系统深度解析

OpenClaw 的记忆系统（Memory System）是其架构中最核心、最具创新性的部分之一。它没有采用传统的“简单向量数据库+被动RAG”模式，而是设计了一套**分层式、以文件为中心、且具备主动检索能力**的混合记忆架构。

以下从源码级别为您深度解析 OpenClaw 记忆系统解决了什么问题、其底层实现原理，以及对下一代 Agent 记忆系统的启示。

---

### 一、 解决了什么问题？

1. **长对话“失忆”与上下文窗口溢出：**
   传统 Agent 在对话变长后，只能粗暴地截断早期对话或进行无损耗的摘要压缩，导致细节永久丢失。
2. **多会话间的状态与偏好隔离：**
   用户在不同会话、不同任务中产生的偏好（如代码风格、工具配置），传统系统很难跨会话共享，导致 Agent 每次都在“重新认识”用户。
3. **被动 RAG 的迟钝性：**
   多数框架依赖 LLM 自己判断何时调用 `search_memory` 工具。如果 LLM 觉得“不需要”，就会凭幻觉瞎编。
4. **黑盒化与人类不可干预：**
   当所有记忆被切片塞入向量数据库时，人类无法直观地查看、修改或使用 Git 进行版本控制。

---

### 二、 架构设计与核心组件（源码级剖析）

OpenClaw 记忆架构摒弃了单一的 RAG 思路，转而采用了一套多层调度设计。从宏观架构来看，控制流被设计为：
**用户输入 -> Active Memory 前置拦截与预检索 -> 主 Agent 上下文组装（融合长期记忆与会话历史） -> 会话压缩与持久化冲洗（Flush）**。

整个架构可分为三大核心支柱：**长期记忆（Durable Memory）**、**主动预检记忆（Active Memory）**、以及**基于 DAG 的无损上下文压缩（Lossless Context / Compaction）**。

#### 1. 长期记忆：File-first 与 SQLite-vec 混合检索
**架构设计：** 
采用“文件即真理”（Source of Truth）的原则。系统最高优的记忆不是存在黑盒数据库里，而是直接以人类可读的 Markdown 形式存放在用户的工作区中，底层数据库仅作为“索引”和“缓存”层存在，允许人类随时介入并利用 Git 进行版本控制。

**核心组件与源码实现：** 
*   **根记忆文件追踪**：在 `src/memory/root-memory-files.ts` 中定义了 `MEMORY.md` 和 `memory/**/*.md` 作为规范的记忆载体。系统会自动同步工作区中这些文件的变化，确保 LLM 拥有稳定且最新的长效知识。
*   **本地存储与缓存引擎 (`src/memory-host-sdk/host/sqlite-vec.ts`)**：
    为了在本地实现低延迟、不依赖云端的高效检索，OpenClaw 没有引入沉重的专用向量数据库，而是巧妙利用了 Node.js 的原生 **SQLite** 并加载了 **`sqlite-vec`** 动态扩展库 (`loadSqliteVecExtension` 方法)。这使得它能在单个轻量级本地文件（如 `~/.openclaw/memory/{agentId}.sqlite`）中同时管理元数据、文本缓存和向量数据。
*   **混合权重检索算法 (`src/agents/memory-search.ts`)**：
    代码中实现了一个高健壮性的**混合检索 (Hybrid Search)**。它定义了 `vectorWeight`（默认 0.7）和 `textWeight`，将基于 `sqlite-vec` 返回的 Dense Vector 相似度和原生 SQLite 提供的 FTS（全文检索，如 BM25）文本得分进行归一化合并计算。这完美解决了纯向量检索面对代码专有名词、API 名称和特定缩写时“语义相近但精准度极差”的痛点。
*   **向量生成层 (`src/memory-host-sdk/host/embeddings-remote-fetch.ts`)**：
    提供解耦的 Embeddings 抽象，通过 `fetchRemoteEmbeddingVectors` 等方法，允许系统按需对接 Gemini、OpenAI、Ollama 等任意外部/本地模型来生成上下文切片的 Embedding 向量。

#### 2. 主动记忆（Active Memory）：阻断式前置子代理
**架构设计：** 
为了解决传统被动 RAG 系统“大模型容易忘调用工具”的问题，系统在主对话流程开始前引入了“阻断式预处理钩子”。主动将关联记忆像人类潜意识一样“浮现”到上下文中。

**核心组件与源码实现：**
*   **子代理拦截机制 (`extensions/active-memory/index.ts`)**：
    这是一个标准的 Pre-agent Hook 插件实现。每当用户输入消息，系统会拉起一个轻量级的**阻塞式记忆子代理**（Blocking memory sub-agent）。配置接口 `ActiveRecallPluginConfig` 允许深度定制：通过 `queryMode` 决定喂给子代理的输入是单条消息、近期尾部对话（`recent`）还是全文；通过 `maxSummaryChars` 严格限制返回摘要的长度以节省主 Agent Token（默认仅 220 字符）。
*   **上下文无缝注入**：
    子代理独立执行向量和全文查询，一旦命中有价值的知识（Status 为 `ok`，并过滤掉诸如 `timeout`, `none`, `[]` 等无效召回 `NO_RECALL_VALUES`），它会提炼出一份极简的摘要（Summary）。这份摘要会被打上标志性标签（如 `🧩 Active Memory:` 或 XML Tag `<active_memory_plugin>`）强行注入到主 Agent 接下来要看到的 Context 最前端，使得主 Agent “未卜先知”。

#### 3. 无损上下文管理（LCM）与 DAG 会话压缩
**架构设计：** 
会话记录在底层不是线性数组（Array），而是有向无环图（DAG）。系统将对话节点化，从而支持复杂的无损压缩、分支、以及历史状态回溯，确保在极长对话中不会丢失重要逻辑链。

**核心组件与源码实现：**
*   **DAG 链式数据结构 (`AGENTS.md` 架构准则)**：
    源码规约中特别强调：*“Pi session transcripts are a `parentId` chain/DAG; never append Pi `type: "message"` entries via raw JSONL writes.”* 每条消息插入时不仅包含内容，还必须有对应的 `parentId`，并产生新的 `leafId`。这意味着对话树可以任意分叉。
*   **自适应触发与检查点捕获 (`src/gateway/session-compaction-checkpoints.ts`)**：
    当上下文逼近预算（Token Limit）或发生显式溢出时，触发 `resolveSessionCompactionCheckpointReason`。
    压缩前，系统调用 `captureCompactionCheckpointSnapshot` 将当前带 DAG 的 `.jsonl` 对话历史备份为 `.checkpoint.<uuid>.jsonl` 的磁盘快照，最大限制为 64MB。
*   **智能修剪与精准回溯 (`src/gateway/server-methods/sessions.ts`)**：
    为了控制磁盘膨胀，`trimSessionCheckpoints` 函数限制每个会话最多保留 25 个压缩快照（`MAX_COMPACTION_CHECKPOINTS_PER_SESSION`）。
    更强大的是，通过 RPC 接口如 `sessions.compaction.restore` 和 `sessions.compaction.branch`，无论是用户还是系统都可以凭借 DAG 的 `leafId` 结构，精确地回滚对话状态或开启并行的对话分支，真正实现了上下文“可压缩但也随时可展开（Lossless）”。

---

### 三、 对下一代 Agent 记忆系统的借鉴意义

OpenClaw 这种“不盲目堆砌前沿概念，而是注重工程落地与边界情况”的架构，为下一代 Agent 记忆系统指明了几个极为务实的方向：

1. **“文件即数据库”降低系统熵值 (File-first over DB-first)**
   下一代 Agent 不应把所有记忆都困在不可见的 ChromaDB / Pinecone 中。把最高优的长期记忆存在类似 `MEMORY.md` 这样的纯文本中，**将数据库退化为“索引（Index）”和“缓存（Cache）”**（如 OpenClaw 用 SQLite 做的事）。这赋予了系统无与伦比的可观测性、可编辑性和 Git 级版本控制能力。
2. **变“被动调用”为“主动预检” (Active Pre-retrieval)**
   依赖大模型自己决定是否调用 `SearchMemory` 是不稳定的，常常造成昂贵的往返对话和幻觉。系统级架构应该引入“双循环”：一个快速便宜的检索 Agent 在后台实时工作（如同人类的潜意识），为主 Agent 的“思考”提前备好弹药。
3. **基于图结构（DAG）的对话记录基建**
   把聊天记录当作 `List[Message]` 已经落后了。当 Agent 需要纠错回退、人类干预、或者进行多层级树状思考（Tree of Thoughts）时，线性记录会导致状态彻底混乱。必须从底层将消息存储设计为带有 `parentId` 和 `leafId` 的 DAG 结构，这是实现“无损压缩（Lossless Compaction）”的唯一工程正解。
4. **混合检索是生产环境的底线**
   在代码生成等精确任务中，纯向量（Dense Vector）对变量名和缩写是灾难。利用本地轻量级方案（SQLite FTS + `sqlite-vec`）低成本地实现 Keyword + Vector 混合权重打分，兼顾语义泛化与符号精准度，应当成为所有开发态 Agent 的标配基建。
