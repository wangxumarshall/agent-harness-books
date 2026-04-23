# Agent Memory System 深度洞察研究报告（融合版）

> 作者：汪旭 / Claude Code / Codex  
> 时间：2026-04-16  
> 说明：以C.A.P.E 对比、CortexMem 技术方案和附录为主体，证据优先方法论、九类分类、五层工程栈、跨体系综合判断与参考文献组织方式。  
> 原则：分类边界清晰、证据等级明确、正文与附录口径一致、技术方案与研究结论可相互映射。

---

## 执行摘要

本报告压缩为七个核心判断：

1. **Agent Memory 不是单一技术，而是一组跨层问题。**  
   同一个“memory”常常混用了模型记忆、推理态记忆、外部持久记忆、上下文管理、图式索引和多 Agent 共享状态。把它们塞进一个总榜，是许多报告失真的根源。

2. **当前工程上证据最强的主线不是“外挂向量库”或“模型自己记住一切”，而是：**  
   **外部持久记忆 + 结构化索引/时间结构 + 检索/压缩/治理策略。**  
   mem0、LangMem、OpenViking、memsearch、Graphiti、TiMem、MemOS 都朝这条线收敛。

3. **模型记忆必须拆开看。**  
   `MSA` 一类路线发生在推理中，本质是运行时访问或扩展有效上下文；`MemoryLLM`、`STEM` 一类路线把记忆内化到参数或参数化模块。它们同属“模型记忆”，但解决的不是同一层问题。

4. **Memory OS 是有用隐喻，但不是硬件页表的字面实现。**  
   Letta/MemGPT、MemOS、TiMem、EverMemOS 借用的是“分层、冷热分离、调度、回收、生命周期治理”的软件工程思想，而不是操作系统物理内存管理的等价实现。

5. **真正成熟的长期记忆系统，必须把写入、更新、遗忘、回滚、审计都看作一等能力。**  
   只有检索、没有治理的 memory store，只是半成品。

6. **多 Agent 共享记忆会把收益和风险一起放大。**  
   共享状态能提升协作效率，但也会扩大权限越界、错误扩散、提示注入传播和记忆投毒的影响。因此 provenance、隔离、审计、回滚和隔离域设计不能是附加项。

7. **面向通用 Agent 的 memory core，最终会收敛为“北向语义记忆 + 南向 KV 协同 + 治理平面”的混合栈。**  
   单层向量库、单一图谱、纯 Markdown 或纯模型参数都不够。

---

## 研究方法与证据规则

### 0.1 本报告如何定义“Agent Memory”

本报告只把同时满足以下三个条件的能力，视为严格意义上的 Agent Memory：

- **跨会话持久化**：信息在一次交互结束后仍可被未来任务调用。
- **可检索/可复用**：系统能在后续推理、行动或工具调用中主动使用这些信息。
- **可更新**：系统能增量写入、合并、失效、压缩、重组或回滚既有记忆。

### 0.2 本报告明确区分的四层对象

| 层次 | 定义 | 典型代表 |
|------|------|---------|
| **模型记忆** | 直接修改 Transformer 结构、参数或稀疏注意力访问方式 | Memorizing Transformers、MSA、MemoryLLM、STEM |
| **推理态记忆 / KV 协同** | 围绕运行时 KV cache、稀疏访问、上下文压缩的状态管理 | H2O / SnapKV 一类方法、MSA、MemOS Activation Memory |
| **外部持久记忆** | 在模型外保存事实、偏好、技能、资源、实体关系，并在未来任务中调用 | mem0、LangMem、OpenViking、memsearch、Graphiti |
| **管理与治理层** | 分层调度、生命周期、共享/隔离、审计、回滚、安全控制 | Letta、MemOS、TiMem、EverMemOS、ContextLoom、eion |

### 0.3 本报告不把什么当作主线对象

- **长上下文能力**：上下文窗口很长，不等于已经具备长期记忆。
- **纯 RAG / 向量检索**：如果没有稳定的写入、更新、遗忘和治理机制，它更像检索增强，而不是完整 memory system。
- **纯 KV cache 优化**：它解决的是推理态状态管理，不天然具备跨会话持久记忆。
- **只有营销口号、缺少稳定一手技术材料的项目**：不进入主论证，只进附录。

### 0.4 证据等级与标注口径

为兼容两份源文稿，本报告同时保留字母等级和星级标注，映射关系如下：

| 等级 | 星级 | 含义 |
|------|------|------|
| **A** | **★** | 官方文档/官方仓库/原始论文可交叉印证，系统定位清晰 |
| **B** | **★☆** | 有一手来源，但关键量化主要来自论文或项目自报 |
| **C** | **☆** | 有官方来源，但产品、代码和论文口径不完全一致，需谨慎 |
| **X** | **X / 待确认** | 本轮没有拿到足够稳定的一手技术链条，不纳入主结论 |

### 0.5 如何看待 benchmark 和分数

本版不再给出统一“总榜”，原因有四：

- 不同系统解决的问题层级不同。
- 不同论文/项目使用的 benchmark、指标、底模、检索设置不一致。
- README 自报、论文自报、媒体报道和独立复现不属于同一种证据。
- 多数系统的生产延迟、成本和安全性没有随精度一起披露。

因此，本报告只允许两种比较：

- **同一 benchmark、同一任务、同一口径下的结果对比**
- **同一类别系统的机制、边界与治理能力对比**

---

## 第1章：产业界 Agent Memory System 深度洞察

### 1.1 技术总图：九类体系与 30+ 系统映射

本报告将当前产业界和近产业化研究型系统整理为九类：

| 类别 | 核心问题 | 记忆载体 | 代表系统/技术 |
|------|----------|---------|--------------|
| **1. 模型记忆** | 模型本体如何直接拥有或访问记忆 | 参数、潜空间记忆池、稀疏注意力访问记忆 | Memorizing Transformers、MSA、MemoryLLM、STEM |
| **2. LLM 决策记忆** | 什么值得记、何时更新、何时召回、如何忘记 | 向量、图、文件、结构化对象 | mem0、LangMem、Hermes Agent |
| **3. 外部记忆增强** | 如何在模型外构建可持久、可读、可检索的长期记忆 | 文件系统、Markdown、向量库、图数据库 | OpenViking、memsearch、memU、Graphiti |
| **4. 记忆与 KV 协同** | 如何把上层语义记忆与底层推理态缓存打通 | KV cache、activation memory、稀疏路由 | MSA、MemOS、H2O/SnapKV 一类方法 |
| **5. 类 OS 分层记忆管理** | 如何像软件层内存管理一样分层调度记忆 | 分层 memory block、TMT、MemCell/MemScene | Letta/MemGPT、MemOS、TiMem、EverMemOS |
| **6. 仿生认知记忆** | 如何借鉴 episodic / semantic / forgetting / graph cognition | 图、超图、层次图、生命周期对象 | EverMemOS、HyperMem、LiCoMemory、MemoryOS |
| **7. 多 Agent 记忆共享/隔离** | 多 Agent 如何共享状态又避免污染与越权 | 共享总线、知识图谱、中心化 memory server | ContextLoom、eion、MIRIX、honcho |
| **8. 记忆插件与基础设施** | 主流 Agent/IDE 如何把记忆能力落到工作流中 | 插件、日志、Markdown、后台压缩 | claude-mem、lossless-claw、xiaoclaw-memory、ultraContext |
| **9. 评测与治理** | 长期记忆到底该测什么、如何防失控 | benchmark、leaderboard、安全机制 | LoCoMo、LongMemEval、MemBench、AgentPoison、MINJA、eTAMP |

对应到系统版图，可以简化为如下结构：

```text
Agent Memory
├── 模型记忆
│   ├── 推理中访问：Memorizing Transformers / MSA
│   └── 参数内化：MemoryLLM / STEM / Engram
├── LLM决策记忆：mem0 / LangMem / Hermes Agent
├── 外部记忆增强：OpenViking / memsearch / memU / Graphiti
├── 记忆与KV协同：MSA / MemOS Activation / H2O / SnapKV
├── 类OS分层管理：Letta / MemOS / TiMem / EverMemOS
├── 仿生认知记忆：HyperMem / LiCoMemory / MemoryOS
├── 多Agent共享/隔离：ContextLoom / eion / MIRIX / honcho
├── 记忆插件与基础设施：claude-mem / lossless-claw / xiaoclaw-memory / ultraContext
└── 评测与治理：LoCoMo / LongMemEval / MemBench / AgentPoison / eTAMP
```

### 1.2 一个更接近工程现实的分层栈

如果从系统架构看，一个可落地的通用 Agent Memory Stack 至少应有五层：

| 层 | 作用 | 典型内容 |
|----|------|---------|
| **L0 原始交互层** | 保留不可逆损失前的原始 episode | 对话、工具调用、网页观察、文件 diff、环境事件 |
| **L1 工作记忆层** | 当前会话内的 scratchpad 与短期状态 | 当前目标、子任务、暂存变量、短时上下文 |
| **L2 语义记忆层** | 可长期复用的事实、偏好、资源、技能、实体关系 | 用户画像、项目知识、任务经验、工具策略 |
| **L3 结构化组织层** | 用 filesystem / graph / temporal hierarchy 管理 L2 | 文件树、时间树、知识图、MemScene、Persona 层级 |
| **L4 推理态桥接层** | 把 L2/L3 的结果接入当前推理态 | sparse retrieval、KV placement、activation memory、context packing |

所有真正能进入生产的系统，最终都要回答两个问题：

- **北向问题**：如何组织、更新、治理长期语义记忆？
- **南向问题**：如何把这些记忆高效、正确地注入当前推理态？

### 1.3 C.A.P.E 框架深度对比

#### 1.3.1 架构与底层范式层 (Architecture & Paradigm)

##### 技术分类 (Tech Taxonomy)

经源码级和文档级对照，原“OS 内存页置换”分类应视为营销隐喻而非真实实现。本表按实际技术内核修正：

| 分类 | 代表系统 | 核心特征 | 关键边界 |
|------|---------|---------|---------|
| **模型记忆** | MSA、MemoryLLM、STEM | 直接改模型结构、参数或注意力访问路径 | 适合模型能力扩展，不直接解决用户级治理 |
| **LLM 决策记忆** | mem0、LangMem、Hermes Agent | LLM 决定写入、更新、遗忘与召回 | 决策质量强依赖模型与提示设计 |
| **外部记忆增强** | OpenViking、memsearch、memU | 模型外可持久、可读、可检索的长期记忆层 | 需要额外索引、路由和压缩策略 |
| **记忆与 KV 协同** | H2O、SnapKV、MSA、MemOS Activation | 北向语义记忆与南向推理态协同 | 不是完整长期记忆系统 |
| **类 OS 分层管理** | Letta、MemOS、TiMem、EverMemOS | 分层、冷热分离、调度、生命周期治理 | 是软件调度，不是硬件页置换 |
| **仿生认知记忆** | HyperMem、LiCoMemory、MemoryOS | episodic/semantic/forgetting/graph cognition | 理论表达强，工程复杂度高 |
| **多 Agent 共享/隔离** | ContextLoom、eion、MIRIX、honcho | 跨 Agent 共享状态、租户隔离、协作治理 | 安全和权限边界是刚需 |
| **记忆插件/基础设施** | claude-mem、ultraContext、lossless-claw | 将 memory 嵌入现有工作流或框架 | 更像生态落地形态，不是理论终点 |

##### 存储范式 (Storage Paradigm)

| 存储范式 | 代表系统 | 优势 | 劣势 |
|---------|---------|------|------|
| **扁平向量 (Flat Vector)** | mem0、langmem、mem9 | 部署简单、语义检索强 | 人类不可读、关系表达弱 |
| **会话时序 (Time-Series)** | Letta Recall、lossless-claw | 时序推理直观、保真度高 | 召回成本高、长程压缩难 |
| **图数据库 (GraphDB)** | MemOS、eion、Graphiti | 关系建模强、适合结构化推理 | 部署和维护成本高 |
| **超图 (Hypergraph)** | EverMemOS、HyperMem | 可表达 n 元关系和多跳关联 | 计算开销大，生态仍早期 |
| **文件目录树 (File System)** | OpenViking、memsearch、memU、xiaoclaw-memory | 人类可读、可 git 化、可审计 | 语义检索需额外影子索引 |
| **模型参数 (Parameters)** | MemoryLLM、STEM | 推理时零外部检索开销 | 容量有限、不可解释、难精确编辑 |
| **KV Cache / Activation** | Memorizing Transformers、MSA、Infini-attention | 可直接介入推理态 | 无跨会话持久性 |
| **混合范式** | MemOS、CortexMem、LiCoMemory | 同时兼顾可读性、效率和结构 | 系统复杂度高 |

##### 系统定位 (System Positioning)

| 定位 | 代表系统 | 集成成本 | 灵活性 | 风险 |
|------|---------|---------|--------|------|
| **中间件 SDK** | mem0、LangMem、mindforge | 低 | 高 | 容易沦为“只有 API 没有治理” |
| **中间件插件** | claude-mem、mem9、lossless-claw | 低 | 中 | 深度依赖宿主工作流 |
| **独立 Memory-as-a-Service** | eion、honcho、ultraContext | 中 | 中 | 运维与权限模型复杂 |
| **Agent 平台内置** | Letta、Hermes Agent | 高 | 低 | 生态锁定强 |
| **Memory OS / 调度层** | MemOS、EverMemOS、MindOS | 高 | 中 | 理论叙事和工程实现容易脱节 |
| **模型底座** | MemoryLLM、MSA、STEM | 极高 | 低 | 难解释、难迁移、难治理 |

##### 检索机制 (Retrieval Mechanism)

| 检索策略 | 代表系统 | 精确度 | 泛化能力 | 典型问题 |
|---------|---------|--------|---------|---------|
| **纯向量语义** | mem0、mem9 | 中 | 高 | 容易漏掉时间、版本和否定关系 |
| **混合检索 (dense + BM25 + RRF)** | memsearch | 高 | 高 | 需要较复杂索引维护 |
| **目录浏览 / 递归探索** | OpenViking、MineContext | 高 | 中 | 依赖目录设计质量 |
| **图遍历 / 图重排** | MemOS、eion、Graphiti | 高 | 中 | 延迟和部署成本偏高 |
| **超图遍历** | EverMemOS、HyperMem | 高 | 高 | 工程成熟度偏低 |
| **LLM 自驱检索** | Letta、MemBrain | 取决于模型 | 高 | 代价高、不可预测 |
| **复杂度感知召回** | TiMem | 中高 | 中高 | 需要合理任务复杂度判别 |

#### 1.3.2 认知与演进能力层 (Cognition & Evolution)

##### 自我进化 (Self-Evolution) 光谱

| 等级 | 特征 | 代表 |
|------|------|------|
| **L0 死记忆** | 只存不更新 | 纯日志型或只追加型插件 |
| **L1 半活记忆** | 支持增量写入与简单去重 | mem0、LangMem、claude-mem |
| **L2 活记忆** | 后台压缩、摘要、反思或融合 | OpenViking、memU、Letta |
| **L3 强演进记忆** | 具备调度器、生命周期、遗忘和主动整理 | MemOS、EverMemOS、Hermes Agent |

##### 遗忘机制 (Forgetting) 对比

| 机制 | 代表 | 优点 | 局限 |
|------|------|------|------|
| **无遗忘** | 多数基础 RAG / 插件系统 | 实现简单 | 污染和过时信息会持续累积 |
| **TTL / 时间过期** | 基础缓存系统 | 成本低 | 无法表达重要性差异 |
| **重要性评分淘汰** | EverMemOS、honcho | 更贴近使用价值 | 评分策略容易偏置高频热点 |
| **召回触发再巩固** | TiMem、MemoryBank | 更接近记忆动力学 | 需要稳定的巩固逻辑 |
| **隔离 / 归档 / 回滚** | Memoria、CortexMem | 适合安全治理 | 实现复杂，需要版本链和审计 |

##### 结构化推理能力 (Structural Reasoning)

| 能力等级 | 表达能力 | 代表 |
|---------|---------|------|
| **扁平事实** | 只支持 chunk 或 fact | mem0、claude-mem |
| **分类标签** | 能区分 skill / preference / resource 等 | memsearch、Hermes Agent、xiaoclaw-memory |
| **实体关系图** | 可表达 A 属于 B、B 被 C 修改 | Graphiti、MemOS、eion |
| **时间层次图** | 可表达“昨天/本周/长期画像” | TiMem、Letta Recall |
| **超图 / 认知图谱** | 可表达 n 元关系、多跳、多角色交互 | EverMemOS、HyperMem、LiCoMemory |

#### 1.3.3 工程与生产力层 (Production & Engineering)

##### Token 效率：不能只看节省率

Token 效率必须同时看四个维度：

| 维度 | 关注点 | 典型现象 |
|------|--------|---------|
| **节省率** | 召回长度相对 naive full-context 降多少 | mem0、OpenViking、TiMem 都主打压缩与路由 |
| **准确率影响** | 节省 token 之后，事实一致性和推理能力是否下降 | 极端压缩时 accuracy 往往回落 |
| **时延响应** | 搜索延迟和总响应延迟是否还能进生产 | 图遍历和 LLM 自驱检索常是瓶颈 |
| **用户体验** | 人类能否理解“为什么召回了这些记忆” | 可观测性决定可调试性和可信度 |

##### 可观测性与可读性 (Observability & Readability)

| 形态 | 代表系统 | 可读性 | 可调试性 |
|------|---------|--------|---------|
| **二进制 / 参数隐式** | MemoryLLM、STEM | 低 | 低 |
| **向量库 / JSON API** | mem0、langmem | 中 | 中 |
| **Markdown / 文件树** | memsearch、OpenViking、memU | 高 | 高 |
| **图谱 / 可视化面板** | MemOS、Graphiti、eion | 中高 | 高 |
| **追踪式 IDE / 控制台** | Letta ADE、LangSmith、claude-mem | 中高 | 高 |

##### 部署复杂度对比

| 复杂度 | 代表系统 | 典型依赖 |
|--------|---------|---------|
| **零配置 / 本地优先** | xiaoclaw-memory、lossless-claw | 纯 Markdown / SQLite |
| **轻量级** | memsearch、claude-mem | 本地文件 + 向量影子 |
| **中等** | mem0、langmem、Graphiti | 外部向量库 / PG / API |
| **较高** | MemOS、eion、EverMemOS | 图数据库 + 向量库 + 调度器 |
| **极高** | MSA、MemoryLLM、STEM | 模型结构改动 / 训练与推理系统 |

#### 1.3.4 业务与生态层 (Business & Ecosystem)

##### 适用场景矩阵

| 场景 | 更合适的路线 | 原因 |
|------|-------------|------|
| **Coding Agent** | 文件系统式外部记忆 + 技能记忆 + 版本控制 | 工程师需要可读、可改、可追责 |
| **长期个人助理** | LLM 决策记忆 + 时间层次化 + 隐私治理 | 画像变化与时间一致性更重要 |
| **企业流程 / 运维 Agent** | 分层调度 + 图式记忆 + 安全治理 | 审计、权限和回滚是刚需 |
| **多 Agent 协作** | 共享总线 + 强隔离 + provenance | 状态共享与防污染必须同时成立 |
| **模型能力增强** | 模型记忆 + KV 协同 | 重点在推理态效率与模型能力，而非用户级治理 |

##### 多 Agent 支持对比

| 模式 | 代表系统 | 风险 |
|------|---------|------|
| **单 Agent 私有记忆** | Hermes Agent、claude-mem | 难共享经验 |
| **多 Agent 隔离** | Letta、LangMem | 共享能力有限 |
| **共享记忆池 / 总线** | ContextLoom、eion、MIRIX、honcho | 污染、越权、投毒会放大 |
| **共享 + 分区 + 回滚** | CortexMem、Memoria（恢复能力） | 实现复杂，但更接近企业可用 |

### 1.4 主要局限与短板

#### 1.4.1 共性局限

当前大多数系统仍存在四个共性短板：

1. **写入策略不稳**：什么值得长期保留，仍过度依赖 LLM 提取提示。
2. **更新与冲突处理薄弱**：很多系统只能 append，难处理互斥事实、版本漂移和时间演化。
3. **遗忘机制不成熟**：真正支持降权、归档、隔离、回滚的系统极少。
4. **安全设计滞后**：记忆投毒、环境注入、跨 Agent 污染在公开实现里仍普遍缺位。

#### 1.4.2 各范式特有局限

| 路线 | 局限 |
|------|------|
| **模型记忆** | 难解释、难精准删除、难跨模型迁移 |
| **LLM 决策记忆** | 决策链路不稳定、成本受模型调用放大 |
| **外部记忆增强** | 若无结构和治理，易退化成“只会搜文档” |
| **类 OS 分层管理** | 隐喻容易过强，工程上常难落到清晰 API |
| **图式 / 超图记忆** | 关系表达强，但部署复杂、更新成本高 |
| **共享记忆总线** | 权限、隔离和 provenance 是最大短板 |

#### 1.4.3 评估可信度危机与安全盲区

需要特别警惕三个问题：

1. **README 自报分数常与论文条件不一致。**
2. **很多“高分”不披露延迟、硬件、召回 token 长度与失败用例。**
3. **安全 benchmark 仍未像 LoCoMo / LongMemEval 那样成为主流门槛。**

### 1.5 Agent Memory System 演进方向趋势

未来 2-3 年最确定的趋势大致如下：

1. **静态 -> 动态**：从“存进去”走向“持续整理、更新、遗忘、回滚”。
2. **被动 -> 主动**：从“用户问了再找”走向“后台 consolidation、主动预取、主动关联”。
3. **文本块 -> 类型化对象**：从 chunk 走向 fact / preference / plan / skill / resource / entity / relation。
4. **单层向量 -> 混合组织**：filesystem、vector、graph、temporal hierarchy 会共存。
5. **单 Agent 私有记忆 -> 多 Agent 共享总线 + 强隔离**：共享会成为主流，但治理是前提。
6. **黑箱检索 -> 可观测、可编辑、可审计**：可读性和 traceability 将成为产品竞争力。
7. **北向语义层 -> 北向语义层 + 南向 KV 协同**：高效通用 Agent 不能只会从数据库取文本。

---

## 第2章：Agent Memory 学术论文深度洞察

### 2.1 检索方法与论文全景图

本章围绕以下检索轴组织学术材料：

- **记忆类型**：episodic / semantic / working / procedural
- **记忆过程**：formation / retrieval / evolution / forgetting
- **技术底座**：vector DB / graph memory / RAG / OS-like / model memory
- **认知能力**：reflection / self-evolving / continual learning
- **协作形态**：multi-agent / shared memory / collective bus
- **评测与安全**：evaluation / benchmark / poisoning / privacy

按问题域归类，核心论文可压缩为以下几组：

| 组别 | 代表论文 | 解决的核心问题 |
|------|---------|---------------|
| **理论框架** | CoALA | 如何给 Agent memory 建立认知架构坐标系 |
| **模型记忆** | Memorizing Transformers、MSA、MemoryLLM、STEM | 模型如何在推理中访问或内化记忆 |
| **LLM 决策记忆** | mem0 paper、LangMem、Hermes 相关实现 | 什么值得写、何时召回、何时忘记 |
| **OS-like / 时序分层** | MemGPT、TiMem、EverMemOS、MemoryOS | 如何分层、调度和巩固长期记忆 |
| **反思与自进化** | Reflexion、Generative Agents、MemoryBank、ExpeL、A-MEM | 如何通过反思和经验闭环让 memory 变“活” |
| **图式记忆与共享** | Graphiti、HyperMem、LiCoMemory、MINDSTORES、MIRIX | 如何表示关系、时间与多主体共享 |
| **评测与安全** | LoCoMo、LongMemEval、MemBench、AgentPoison、MINJA、eTAMP | 如何测记忆，如何防失控 |

### 2.2 核心论文深度分析

#### 2.2.1 理论框架：CoALA 是认知分层的公共坐标

CoALA 的价值不在于给出一个可直接部署的 memory engine，而在于给 Agent memory 讨论建立了一个较稳定的认知坐标：

- **工作记忆**：当前任务循环中的 scratchpad 和短期状态。
- **情景记忆**：事件、经历、时间链。
- **语义记忆**：稳定事实、概念、用户画像。
- **程序性记忆**：技能、策略、可执行方案。

它对产业界的真正启发有三点：

1. 让“把所有记忆都塞进一个向量库”的设计显得过于扁平。
2. 让“技能是不是记忆”的争论有了更清晰的位置。
3. 为后续的 TiMem、Hermes、Acontext、Voyager、CortexMem 提供了合理的分层映射。

#### 2.2.2 模型记忆：从推理中访问到参数内化

模型记忆必须拆成三条路线看：

| 子路线 | 代表 | 读写时机 | 记忆载体 | 是否跨会话持久 | 主要价值 | 主要边界 |
|--------|------|----------|---------|---------------|---------|---------|
| **推理中访问运行时记忆** | Memorizing Transformers、MSA | 推理中 | 非可微记忆库、稀疏 K/V 表示 | 否 | 扩展有效上下文、提升长程推理 | 本质仍是运行时态 |
| **参数化记忆池 / 模型内化** | MemoryLLM | 训练后/更新后写入 | 潜空间记忆池、参数 | 是 | 零检索链路、长期保留 | 难解释、难精准删除 |
| **可解释参数记忆模块** | STEM、Engram | 训练或编辑时写入 | token-indexed modules | 是 | 提升 parametric memory 的可编辑性 | 更偏模型结构创新 |

核心判断：

- **KV cache 压缩不是完整记忆系统。** 它解决的是上下文窗口与推理态状态管理，不具备跨会话持久记忆。
- **MSA 的“端到端”主要发生在训练层面。** 推理仍需要离线编码、在线路由和稀疏生成等环节。
- **MemoryLLM 的“百万次更新”有前提条件。** 它是在受控训练环境下得到的结论，不等同于现实生产环境的任意知识写入。

#### 2.2.3 LLM 决策记忆与外部持久记忆

这条路线关注的不是“存到哪里”，而是“怎么决定什么值得留下”。

| 系统/论文 | 关键创新 | 工程启发 | 局限 |
|-----------|---------|---------|------|
| **mem0** | LLM 决定提取、更新、删除和召回 | write policy 成为一等问题 | 容易把记忆治理过度外包给 LLM |
| **LangMem** | 把记忆能力嵌入 Agent framework | 记忆成为框架级能力，而非外挂脚本 | 仍偏 SDK 化，治理面较薄 |
| **Hermes Agent** | Markdown 持久记忆 + 闭环学习 + skills 自演进 | 技能可以被看作程序性记忆 | Windows/大上下文支持仍不够优雅 |
| **OpenViking** | filesystem-like 统一管理 memory / resource / skill | 可读性与层次化上下文组织很强 | AGPL 和生态成熟度是约束 |
| **memsearch** | Markdown-first + 向量影子索引 + 渐进披露 | 人类可读和机器检索可以兼容 | 仍依赖外部向量能力 |

学术与产业在这一组上的共同结论是：  
**如果没有清晰的 write policy、update policy 和 read policy，所谓“长期记忆”很快就会退化成带噪的向量仓库。**

#### 2.2.4 OS-like 与时序分层：分层、调度、巩固而非“硬件页置换”

| 论文 / 系统 | 核心创新 | 价值 | 局限 |
|-------------|---------|------|------|
| **MemGPT / Letta** | 虚拟上下文管理，LLM 主动换页 | 首次把 memory 当作上下文外部化问题认真处理 | 仍强依赖 LLM 决策质量 |
| **TiMem** | 5 层时序记忆树 + 复杂度感知召回 | 时间层次化做得最清楚 | 层级设计并非所有场景都适用 |
| **EverMemOS** | 自组织 memory OS + EverCore 调度 + HyperMem | 生命周期与结构表达完整 | 高分主要来自自报，需谨慎解读 |
| **MemoryOS** | 三层记忆 + 热度驱动更新 | 热度机制直观，利于部署 | 热度偏置可能误伤低频关键记忆 |

本组论文共同支撑了一个判断：  
**“像 OS 一样管理 memory”这个叙事是成立的，但必须反对把它按硬件页表字面理解。**

#### 2.2.5 反思、自进化与程序性记忆

| 论文 | 核心创新 | 对 memory 的意义 | 局限 |
|------|---------|------------------|------|
| **Reflexion** | 语言反思强化学习 | 证明错误回顾可提升策略质量 | 反思质量强依赖模型 |
| **Generative Agents** | 记忆流 + 反思 + 三维检索 | 给出了“记忆驱动行为涌现”的经典结构 | 成本高、无成熟遗忘 |
| **MemoryBank** | Ebbinghaus 遗忘曲线 | 首次把遗忘动力学引入 Agent memory | 参数调优复杂 |
| **ExpeL** | 经验 -> 洞察 -> 技能闭环 | 证明经验可转化为程序性记忆 | 洞察可能错误泛化 |
| **Voyager** | 可执行代码技能库 | 技能就是可执行的程序性记忆 | 场景受限于特定环境 |
| **A-MEM** | 记忆即 Agent | 把记忆从被动对象推向主动生命体 | 工程复杂度极高 |

这条线最重要的学术启发是：  
**“活记忆”不只是会检索，而是会反思、会融合、会遗忘、会固化成技能。**

#### 2.2.6 图式记忆、时间结构与多 Agent 共享

| 论文 / 系统 | 核心创新 | 价值 | 局限 |
|-------------|---------|------|------|
| **Graphiti / Zep** | 时序知识图谱 | 把时间维度变成一等公民 | 维护成本高于扁平向量 |
| **HyperMem** | 超图记忆 | 表达 n 元关系与多角色交互 | 计算成本与工程复杂度高 |
| **LiCoMemory** | 轻量认知图谱 + 时序层次搜索 | 在表达力和轻量化之间折中 | 表达力弱于超图 |
| **MINDSTORES** | 多 Agent 共享记忆架构 | 明确共享总线的结构价值 | 治理机制不够成熟 |
| **MIRIX** | 6 类记忆 + Active Retrieval | 强调多记忆类型联动与多 Agent 协同 | 分类和维护成本较高 |

这一组最重要的现实判断是：  
**一旦进入多 Agent 或长期复杂任务，时间结构与共享治理会迅速变成刚需，而不是高级可选项。**

#### 2.2.7 评测基准：不要只看榜单，要看在测什么

| 基准 | 主要测试点 | 强项 | 局限 |
|------|-----------|------|------|
| **LoCoMo** | 长期对话、多 session、事件链与时间一致性 | 是长期对话记忆的基础 benchmark | 对编码/运维场景覆盖不足 |
| **LongMemEval** | 注入、检索、推理、更新、遗忘 | 更强调更新和拒答能力 | 仍偏对话和 QA 场景 |
| **MemBench** | 统一评估框架 + 效率维度 | 有利于讨论 token 与准确率权衡 | 生态采用度还不够高 |
| **EverBench** | 多方协作对话评估 | 指向多 Agent / 多角色场景 | 自建基准偏置需警惕 |

正确理解记忆能力，至少要同时看八项诉求：

1. 召回正确
2. 时间一致
3. 更新正确
4. 遗忘正确
5. 拒答正确
6. 召回代价可控
7. 过程可解释
8. 错误可回滚

#### 2.2.8 安全与隐私：从附属话题变成必要组件

| 论文 / 攻击 | 关键发现 | 影响 |
|-------------|---------|------|
| **AgentPoison** | 记忆投毒攻击成功率高 | 暴露长期记忆系统的系统性脆弱性 |
| **BadRAG / PoisonedRAG** | 利用恶意文档或知识链污染检索 | 说明外挂记忆并不天然安全 |
| **间接注入攻击** | 可经外部数据源把恶意指令带入 Agent | 共享与自动抓取场景尤其危险 |
| **MINJA** | 真实条件下攻击效果会受已有合法记忆影响 | 也说明防御必须考虑信任评分和记忆清洗 |
| **eTAMP** | 可跨会话、跨站点实施环境注入记忆投毒 | 把安全问题从 prompt 扩大到环境与记忆总线 |

学术和产业的共同缺口在于：  
**安全仍常被当成附加层处理，而不是 memory stack 的内生结构。**

### 2.3 学术论文与产业系统映射

| 学术概念 | 产业实现 | 成熟度 | 说明 |
|---------|---------|--------|------|
| **CoALA 分层** | Hermes、Acontext、CortexMem | 中 | 更像设计坐标，而非现成产品 |
| **MemGPT 虚拟上下文** | Letta | 高 | 是 OS-like 路线的现实起点 |
| **复杂度感知召回** | TiMem | 中高 | 是低成本分层路由的代表 |
| **记忆动力学 / 遗忘曲线** | MemoryBank、EverMemOS、CortexMem | 中 | 还缺统一生产实现 |
| **图式与超图记忆** | Graphiti、MemOS、EverMemOS、LiCoMemory | 中 | 表达力强，但工程门槛高 |
| **程序性记忆 / 技能化** | Voyager、Acontext、Hermes | 中 | 在特定场景表现好 |
| **共享记忆总线** | ContextLoom、eion、MIRIX | 中低 | 治理与安全仍薄弱 |
| **版本回滚与审计** | Memoria、CortexMem | 低到中 | 方向很强，但公开实现还早 |

### 2.4 跨体系综合判断

#### 2.4.1 哪条路线证据最强

当前证据最强的工程路线不是某个单点系统，而是一种组合：

- 外部持久记忆
- 时间/图/层级化组织
- 背景 consolidation
- 精准召回与压缩
- 必要的治理与隔离

这也是为什么：

- mem0、LangMem 提醒我们要重视 write policy
- OpenViking、memsearch 提醒我们要重视可读性与可观测性
- Graphiti、TiMem 提醒我们要重视时间与结构
- Letta、MemOS 提醒我们要重视分层调度
- MSA、MemoryLLM 提醒我们模型层和推理态层也在演化

#### 2.4.2 哪些路线是互补，不是替代

| 路线 A | 路线 B | 关系 |
|--------|--------|------|
| **MSA** | **外部长期记忆** | 互补：前者解决推理中访问，后者解决跨会话持久化 |
| **MemoryLLM** | **外部长期记忆** | 互补：前者适合通用知识，后者适合用户/任务特定知识 |
| **filesystem-like** | **vector/graph-like** | 互补：前者做人类可读表层，后者做机器高效索引 |
| **OS-like 调度** | **仿生认知** | 互补：前者偏系统工程，后者偏组织原则 |
| **共享记忆总线** | **隔离与治理** | 必须共存：没有治理的共享不可用 |

#### 2.4.3 当前最值得警惕的三个误区

1. **把所有 memory 技术混成一个总榜**
2. **把 OS 隐喻按字面理解**
3. **把 KV 优化误写成完整长期记忆系统**

#### 2.4.4 学术前沿趋势总结

1. **从 RAG 到 Memory-aware Generation**：记忆不再只是召回，而是参与生成过程的决策对象。
2. **从被动存储到主动整理**：背景巩固、主动关联和主动提醒会越来越重要。
3. **从扁平事实到类型化对象**：事实、偏好、技能、关系和资源会分层组织。
4. **从单 Agent 到共享总线**：多 Agent 协作会推动 provenance、隔离与 ACL 进入内核层。
5. **从精度榜单到治理指标**：错误可追踪、可回滚、可隔离会成为新的 benchmark 维度。

---

## 第3章：面向通用 Agent 的 Memory 系统技术方案

### 3.1 目标业务场景

#### 3.1.1 核心场景定义

| 场景 | 描述 | 记忆需求特征 |
|------|------|-------------|
| **编码 Agent** | 24/7 自主编码、调试、重构 | 精确代码上下文、项目架构理解、失败模式记忆、版本回滚 |
| **运维 Agent** | 系统监控、故障诊断、自动修复 | 时序事件记忆、因果关系推理、历史故障模式、安全审计 |
| **研究 Agent** | 文献调研、实验设计、知识发现 | 大规模知识图谱、跨域关联推理、假设追踪 |
| **个人助手** | 日程管理、信息整理、决策辅助 | 用户画像建模、偏好演化追踪、隐私保护 |
| **多 Agent 协作** | 团队任务分配、知识共享、集体决策 | 共享记忆总线、隔离机制、一致性与 provenance |

#### 3.1.2 核心用户痛点

1. **跨会话遗忘**：每次新会话都从零开始，重复解释背景和偏好。
2. **记忆黑箱**：不知道 Agent “记住了什么”，无法审计和修正。
3. **Token 成本高**：全量上下文注入导致推理开销爆炸。
4. **记忆不进化**：Agent 不会从错误中学习，重复犯错。
5. **多 Agent 孤岛**：不同 Agent 之间无法共享知识和经验。
6. **记忆不安全**：缺乏投毒防御、溯源和版本回滚。

### 3.2 问题挑战

| 挑战 | 详细描述 | 当前最佳实践的局限 |
|------|---------|-------------------|
| **写入问题** | 什么值得进入长期记忆，如何避免噪声堆积 | 过度依赖 LLM 提示设计 |
| **结构问题** | 如何把事实、偏好、技能、资源、关系分层组织 | 扁平向量表达不足 |
| **更新问题** | 新事实如何覆盖旧事实，如何处理冲突与版本漂移 | 多数系统只擅长 append |
| **遗忘问题** | 何时降权、归档、隔离或删除 | 缺少四级遗忘体系 |
| **召回问题** | 如何按任务复杂度决定召回深度和格式 | 简单 Top-K 检索常噪声过高 |
| **KV 协同问题** | 召回后的记忆如何高效进入当前推理态 | 很多系统只做到“召回文本” |
| **共享/隔离问题** | 多 Agent、多租户如何共享而不污染 | 缺少成熟的 scope / ACL / provenance |
| **治理与安全问题** | 如何审计、回滚、防投毒、防越权 | 公开系统普遍不足 |

### 3.3 方案定位：CortexMem 不是“拼装竞品”，而是重构记忆栈

CortexMem 的目标不是把市面上的系统简单拼接，而是把证据较强的设计原则重组为一个一致的 memory core：

| 设计元素 | 主要借鉴来源 | CortexMem 的取舍 |
|---------|-------------|------------------|
| **Markdown-first 可读层** | memsearch、OpenViking、xiaoclaw-memory | 保留可读、可改、可审计的源头真相层 |
| **层次化时间结构** | TiMem、Letta Recall | 采用五层记忆主干，而不是单层扁平 chunk |
| **图式 / 关系索引** | Graphiti、MemOS、LiCoMemory | 用作结构化索引层，而不是唯一真相层 |
| **主动整理与融合** | Hermes、EverMemOS、MemoryBank | 通过调度器做 consolidation、融合与遗忘 |
| **LLM 亲和检索路径** | MemBrain 的方向性启发 | 让 LLM 参与复杂查询，但简单查询坚持低成本路径 |
| **版本回滚与恢复** | Memoria | 将分支、回滚、隔离引入治理平面 |
| **Active Retrieval** | MIRIX | 只在合适场景启用，避免全量主动噪声 |

因此，CortexMem 的总视角固定为：

- **北向语义记忆**：长期事实、偏好、技能、关系和资源
- **南向 KV 协同**：把北向召回结果压缩并桥接进当前推理态
- **治理平面**：provenance、ACL、branch、rollback、quarantine

### 3.4 CortexMem 架构：五层记忆主干 + 两个控制平面

#### 3.4.1 分层结构

CortexMem 采用“五层记忆主干 + 两个控制平面”的结构。这样既保留 v0.2 中 L0-L4 的分层，又把 report.md 中的 retrieval planner 和 governance 拉成显式平面，避免语义混乱。

| 层 / 平面 | 主要职责 | 典型内容 |
|-----------|---------|---------|
| **L0 感知 / 推理态层** | 当前请求级的 KV、prefix cache、运行时感知状态 | KV cache、attention signals、runtime scratch state |
| **L1 原始事件层** | append-only 原始 episode，保留真相来源 | 对话、工具调用、网页观察、错误日志、diff |
| **L2 工作与会话层** | 当前任务相关的 typed memory objects | 当前目标、临时事实、session summary、活跃技能 |
| **L3 长期语义层** | 稳定事实、偏好、资源、技能、实体关系 | fact / preference / skill / resource / entity / relation |
| **L4 模式与画像层** | 日/周模式、偏好演化、长期画像与经验归纳 | trend、persona、habit、lessons learned |
| **P1 召回规划平面** | complexity-aware retrieval 与 semantic-to-KV bridge | planner、packer、router、reranker |
| **P2 治理与安全平面** | provenance、ACL、branch、rollback、quarantine | trust score、audit log、version graph |

#### 3.4.2 CortexMem 架构图

```text
┌──────────────────────────────────────────────────────────────────────┐
│                           CortexMem                                  │
├──────────────────────────────────────────────────────────────────────┤
│ L0 感知/推理态层                                                     │
│ KV cache / prefix cache / runtime state                              │
├──────────────────────────────────────────────────────────────────────┤
│ L1 原始事件层                                                        │
│ append-only episodes: dialogue / tools / web / diff / env events     │
├──────────────────────────────────────────────────────────────────────┤
│ L2 工作与会话层                                                      │
│ typed memory objects: fact / plan / session / active skill           │
├──────────────────────────────────────────────────────────────────────┤
│ L3 长期语义层                                                        │
│ filesystem + vector shadow + graph index                             │
│ facts / preferences / resources / skills / entities / relations      │
├──────────────────────────────────────────────────────────────────────┤
│ L4 模式与画像层                                                      │
│ daily/weekly patterns / persona / long-term lessons                  │
├──────────────────────────────────────────────────────────────────────┤
│ P1 召回规划平面                                                      │
│ complexity-aware retrieval / rerank / packing / semantic-to-KV       │
├──────────────────────────────────────────────────────────────────────┤
│ P2 治理与安全平面                                                    │
│ provenance / ACL / branch / rollback / quarantine / trust scoring    │
└──────────────────────────────────────────────────────────────────────┘
```

#### 3.4.3 类型化 memory objects

为避免“只有 chunk，没有语义类型”的老问题，CortexMem 默认使用以下对象类型：

- `fact`
- `preference`
- `plan`
- `skill`
- `resource`
- `entity`
- `relation`
- `episode`
- `pattern`
- `risk_event`

### 3.5 核心流程与机制

#### 3.5.1 写入路径

1. 原始交互先进入 `L1 原始事件层`
2. 由轻量规则和 LLM 决策器共同做 `salience detection`
3. 提取为 typed memory objects，进入 `L2 / L3`
4. 对高风险来源先打 `risk label`，必要时进入 `quarantine`
5. 后台 consolidation 再把稳定模式上升到 `L4`

#### 3.5.2 召回路径

1. query 先做任务复杂度与目的分类
2. 简单 query 优先走浅层、低成本召回
3. 复杂 query 再向图谱、时间树、技能库和模式层扩展
4. 召回结果做去重、冲突裁决、来源排序
5. 最终通过 `semantic-to-KV bridge` 做 context packing

对应到查询路径，可拆成三级：

| 路径 | 触发场景 | 调用代价 |
|------|---------|---------|
| **Path A：低成本路径** | 简单事实、关键词、近期上下文 | BM25 / 向量 / FTS5，无额外强模型 |
| **Path B：结构化路径** | 关系、版本、时间链问题 | 图遍历 / 时间树 / 轻量重排 |
| **Path C：LLM 亲和路径** | 多跳、假设、跨类型综合推理 | 允许多轮 LLM 参与，但只对复杂查询启用 |

#### 3.5.3 更新与遗忘路径

遗忘不能只等于删除。CortexMem 把遗忘拆成四级：

- **降权**：降低召回优先级
- **归档**：保留，但默认不参与在线召回
- **隔离**：进入可疑区等待确认
- **硬删除**：仅对不应保留内容启用

后台调度器 `CortexCore` 负责三类事情：

| 引擎 | 作用 |
|------|------|
| **重要性评分引擎** | 综合频率、近期性、任务依赖、来源可信度和关系中心性 |
| **融合引擎** | 去重、冲突检测、事实覆盖、关系补全 |
| **巩固/遗忘引擎** | 回忆触发再巩固、模式提升、降权、归档、隔离 |

#### 3.5.4 共享与隔离路径

共享记忆总线应支持三类 memory：

- `public/shared memory`
- `team/workspace memory`
- `private agent memory`

同时所有写入必须带：

- `actor`
- `source`
- `timestamp`
- `scope`
- `risk label`
- `version`

#### 3.5.5 Security Layer：把防御做成内核结构

回应 AgentPoison、eTAMP、MINJA 等研究，CortexMem 将安全作为横切关注点，而不是外挂：

1. **写入防火墙**：对外部环境、网页、共享总线来源做风险打分和模式过滤。
2. **provenance 链**：每条记忆记录来源、修改、融合、检索历史。
3. **quarantine 隔离区**：可疑记忆先隔离，再决定是否晋升。
4. **版本回滚**：采用 Memoria 启发的分支、快照和回滚。
5. **ACL 与 scope**：按 `tenant / user / agent / task / workspace` 控制访问。

### 3.6 存储、命名空间与部署模式

#### 3.6.1 存储设计

| 层 / 平面 | 存储方式 | 格式 | 可读性 | 检索方式 |
|-----------|---------|------|--------|---------|
| **L0** | GPU 显存 / 内存 | KV cache | 不可读 | 注意力机制 |
| **L1** | 本地文件系统 | Markdown / JSONL | 高 | FTS5 / 顺序扫描 |
| **L2** | 本地文件系统 + SQLite | Markdown + typed index | 高 | FTS5 + 轻量语义 |
| **L3** | 文件系统 + 向量影子 + 图索引 | Markdown + vector + graph | 中高 | 混合检索 |
| **L4** | 摘要文件 + 模式索引 | Markdown summary / graph node | 中高 | 时序 + 关系 + 语义 |
| **P1** | 内存态 planner | routes / packs | 中 | rerank / packing |
| **P2** | 审计库 + 版本库 | audit log / version graph | 高 | provenance / rollback |

#### 3.6.2 命名空间与隔离域

建议至少同时使用以下维度：

- `tenant`
- `user`
- `agent`
- `session`
- `task`
- `workspace / project`

原因很简单：

- 用户偏好不应直接污染某次任务状态
- 任务中的临时错误不应直接写进全局长期画像
- 不同 agent 既需要共享层，也需要严格的私有层

#### 3.6.3 部署模式弹性

| 模式 | 依赖 | 适用场景 |
|------|------|---------|
| **轻量模式** | SQLite + 本地文件 + 可选向量影子 | 个人开发者、本地优先 |
| **标准模式** | PostgreSQL + pgvector + 图索引 | 小团队、跨会话业务 |
| **企业模式** | PostgreSQL + Qdrant + Neo4j + Redis | 多租户、多 Agent、强治理 |

### 3.7 差异化竞争优势、Benchmark 与 KPI

#### 3.7.1 差异化主张

如果把 CortexMem 当作通用 Agent 的 memory core，差异化不应写成“我们比所有系统都强”，而应落在五个可证伪主张上：

1. **类型化 memory objects，而不是只有 chunk**
2. **filesystem + vector + graph + temporal 的混合组织**
3. **northbound semantic memory 与 southbound KV/cache 的桥接**
4. **shared bus + isolation + provenance 的原生治理**
5. **append-only raw log + background consolidation + rollback/quarantine**

#### 3.7.2 外部 benchmark

| 基准 | 评估维度 | 在 CortexMem 中的用途 |
|------|---------|----------------------|
| **LoCoMo** | 长期对话记忆、时间一致性 | 验证长期召回与时间链 |
| **LongMemEval** | 注入、检索、推理、更新、遗忘 | 验证 memory lifecycle |
| **MemBench** | 效率与质量统一评估 | 验证 token / latency / quality 权衡 |
| **安全攻击集** | 投毒、环境注入、越权访问 | 验证治理平面有效性 |

#### 3.7.3 内部验收指标

建议至少跟踪以下指标：

- `memory precision / recall`
- `stale fact rate`
- `update correctness`
- `abstention correctness`
- `p95 retrieval latency`
- `retrieved token length`
- `wrong-memory-induced failure rate`
- `rollback / quarantine response time`
- `cross-agent contamination rate`

#### 3.7.4 目标效果

以下是工程目标，不是已验证结论：

- 相比 naive full-context，在同等预算下把召回记忆长度压缩 **30%-60%**
- 在 LoCoMo / LongMemEval 一类任务上，较“无长期记忆或单层 RAG”获得更高的长程一致性
- `p95 retrieval + memory decision` 控制在可生产使用的亚秒到数秒级区间
- 对错误记忆具备可追踪、可隔离、可回滚能力

### 3.8 分阶段落地路线

#### 3.8.1 MVP（4 周）

| 组件 | 实现内容 | 目标 |
|------|---------|------|
| **L1-L2** | Markdown + SQLite + typed objects | 先把真相层和工作层建对 |
| **L3 轻量索引** | FTS5 + 向量影子 + 简化关系索引 | 支撑基础混合召回 |
| **P1 基础 planner** | complexity-aware retrieval + packing | 压低 token 开销 |
| **P2 基础治理** | 审计日志 + risk label + quarantine | 建立最小安全闭环 |
| **CLI / SDK** | add / search / consolidate / forget | 让开发者可直接验证 |

#### 3.8.2 Phase 2（MVP 后 8 周）

| 交付物 | 描述 |
|--------|------|
| **完整 L3-L4** | 增加时间层次化、模式提升、画像层 |
| **融合引擎** | 去重、冲突检测、关系补全、事实覆盖 |
| **版本回滚** | 引入 branch / snapshot / rollback |
| **共享总线** | 支持 shared/team/private 三层记忆域 |
| **LLM 亲和路径** | 只为复杂查询开放多轮推理路径 |

#### 3.8.3 Phase 3（场景化打磨）

| 方向 | 描述 |
|------|------|
| **Coding Agent 适配** | 项目结构记忆、失败模式、补丁回放、偏好规则 |
| **运维 Agent 适配** | 事件链、故障模式、安全审计 |
| **个人助手适配** | 画像进化、隐私保护、被遗忘权 |
| **多 Agent 协作** | 强 ACL、cross-agent provenance、污染检测 |

#### 3.8.4 Phase 4（前沿探索）

| 方向 | 说明 |
|------|------|
| **User as Code** | 作为高级可选模式，而不是默认主路径 |
| **模型记忆联动** | 与 MSA / STEM / MemoryLLM 等做混合实验 |
| **多模态扩展** | 把图像、音频和工具轨迹纳入 typed objects |
| **AutoML / 自主优化** | 只在有足够 benchmark 数据后再做架构搜索 |

---

## 附录

### A. 核心产业界系统 C.A.P.E 全景对比表（33 个条目）

**说明**：

- 本表保留了 v0.2 的对比维度，但统一了分类口径。
- `★ / ★☆ / ☆ / 待确认` 与正文证据等级映射。
- 标题从“24 个系统”修正为与表内实际条目一致的“33 个条目”。

| 系统 | 技术分类 | 存储范式 | 系统定位 | 自我进化 | 遗忘 | 结构化推理 | Token效率 | 搜索延迟p95 | 总延迟p95 | LOCOMO | LongMemEval | 可观测性 | 多Agent | 开源许可 |
|------|---------|---------|---------|---------|------|-----------|----------|------------|-----------|--------|-------------|---------|---------|---------|
| OpenViking | 外部记忆增强 | 虚拟文件+向量 | MaaS | L2活 | 隐式 | 目录层次 | 83-91%☆ | - | - | - | - | URI可寻址 | 多租户 | AGPL-3.0 |
| memsearch | 外部记忆增强 | Markdown+向量影子 | CLI插件 | L1半活 | 无 | 分类标签 | 显著 | - | - | - | - | 人类可读 | 共享 | MIT |
| Hermes Agent | LLM决策记忆 | Markdown+FTS5 | Agent框架 | L3活 | 无 | 分类标签 | 中等 | - | - | - | - | 人类可读 | 单Agent | MIT |
| Letta | 类OS分层记忆管理 | 分层存储(Core/Recall/Archival) | Agent平台 | L2活 | 手动 | 扁平块 | 中等 | - | - | 83.2%☆ | - | ADE面板 | 隔离 | Apache 2.0 |
| mem0 | LLM决策记忆 | 扁平向量+图 | SDK+MaaS | L1半活 | 手动 | 扁平/图 | ~90%★(@1.8K tokens) | 200ms | 1.44s | 66.9%★ / 64.2%★ | 66.4%★ | API+Dashboard | 跨Agent | Apache 2.0 |
| mem0g | LLM决策记忆+图 | 向量+图 | SDK+MaaS | L1半活 | 手动 | 图关系 | ~93%★(@14K tokens) | 660ms | 2.59s | 68.4%★ | 72.18%★ | API+Dashboard | 跨Agent | Apache 2.0 |
| MemOS | 类OS分层记忆管理 | 图+向量(MemCube) | Memory OS | L3活 | 调度器 | 图遍历 | 70-72%☆(~2.5K tokens) | 1,983ms | 7,957ms | 80.76%★ | 77.80%★ | 可视化面板 | 隔离+共享 | Apache 2.0 |
| EverMemOS | 类OS分层记忆管理 | 超图+向量(EverCore) | Memory OS | L3活 | EverCore | 超图多跳 | ~85%☆(@2.3K tokens) | - | - | 93.05%☆ | 83.00%☆ | 超图可视化 | 共享+分区 | 待确认 |
| Zep / Graphiti | 图式记忆 | 时序知识图 | MaaS | L2活 | 衰减 | 时序图 | ~1.4K tokens | 522ms | 3,255ms | 85.22%★ | 63.80%★ | Web Console | - | BSL |
| ENGRAM | 模型记忆 | typed extraction | 架构级 | 无 | 无 | dense聚合 | ~99%★(@1-1.2K tokens) | 806ms | 1,819ms | 77.55%★ | +15pts vs Full | 不可读 | 单模型 | - |
| SwiftMem | 记忆与KV协同 | multi-token agg | 架构级 | 无 | 无 | 多token聚合 | 显著 | 11-15ms | 1,289ms | 70.4%★ | - | 不可读 | 单模型 | - |
| MemMachine v0.2 | 待确认 | 待确认 | 新兴 | - | - | - | 80%减少 vs mem0 | - | - | 91.69%☆ | - | - | - | - |
| claude-mem | 记忆插件与基础设施 | SQLite+Chroma | 插件 | L1半活 | 无 | 扁平 | 智能压缩 | - | - | - | - | 人类可读 | 单Agent | AGPL-3.0 |
| mem9 | LLM决策记忆 | TiDB向量+全文 | 插件(云) | L1半活 | 记忆调和 | 扁平 | 按需检索 | - | - | - | - | 日志 | 单Agent | Apache 2.0 |
| lossless-claw | 外部记忆增强 | SQLite DAG | 插件 | L0死 | 无 | 时序DAG | 渐进披露 | - | - | - | - | 人类可读 | 单Agent | MIT |
| memU | 外部记忆增强 | 文件目录树+pgvector | 插件+服务 | L2活 | 隐式淘汰 | 标签+符号链接 | ~90%☆(@4.0K tokens) | - | - | 66.67%★ | 38.40%★ | 人类可读 | 多Agent协作 | Apache 2.0 |
| xiaoclaw-memory | 记忆插件与基础设施 | 纯Markdown | 插件 | L1半活 | 隐式淘汰 | 标签分类 | 零成本 | - | - | - | - | 人类可读 | 单Agent | MIT |
| langmem | 记忆插件与基础设施 | 可插入(内存/PG) | SDK | L1半活 | 手动 | 命名空间 | ~130*/query | 54,340ms | 60,000ms | 58.1%★ | - | LangSmith | 多Agent隔离 | MIT |
| honcho | 多Agent共享/隔离 | 向量+关系型(对等体) | MaaS | L3活 | 重要性 | 认知图谱 | 个性化路由 | - | - | - | - | Thought可追溯 | 多Agent共享 | AGPL-3.0 |
| ContextLoom | 多Agent共享/隔离 | Redis+时序 | 中间件 | L0死 | 无 | 无 | 无优化 | - | - | - | - | 日志 | 共享记忆 | 待确认 |
| eion | 多Agent共享/隔离 | PostgreSQL+Neo4j | MaaS | L0死 | 无 | 图遍历 | 无优化 | - | - | - | - | 图可视化 | 隔离+共享 | 待确认 |
| mindforge | 类OS分层记忆管理 | 向量+概念图 | Python库 | L2部分 | 无 | 概念图 | 多层分流 | - | - | - | - | 概念图可视化 | 单Agent | 待确认 |
| Acontext | 程序性/技能记忆 | Markdown技能+向量 | 插件 | L2活 | 无 | 技能匹配 | 技能复用 | - | - | - | - | 技能审计 | 跨Agent共享 | Apache 2.0 |
| ultraContext | 记忆插件与基础设施 | 分布式结构化 | CaaS | L0死 | 无 | 无 | 智能压缩 | - | - | - | - | 版本控制 | 跨环境共享 | Apache 2.0 |
| Voyager | 程序性/技能记忆 | JavaScript代码技能 | Agent框架 | L2活 | 无 | 技能检索 | 技能复用 | - | - | - | - | 代码可读 | 单Agent | MIT |
| MemoryLLM | 模型记忆 | 模型参数 | 模型底座 | 自监督 | 蒸馏 | 无 | 零检索开销 | - | - | - | - | 不可读 | 单模型 | 待确认 |
| Memorizing Transformers | 模型记忆 | KV Cache | 模型修改 | 无 | 无 | kNN注意力 | kNN开销 | - | - | - | - | 不可读 | 单模型 | Google |
| Infini-attention | 模型记忆 | 压缩记忆+线性注意力 | 模型修改 | 无 | 无 | 压缩检索 | 恒定内存 | - | - | - | - | 不可读 | 单模型 | Google |
| MemaryAI | 类OS分层记忆管理 | 向量+图+时序 | Python库 | L2活 | 衰减曲线 | 知识图谱 | 衰减淘汰 | - | - | - | - | 三层可视化 | 单Agent | 待确认 |
| MindOS | 类OS分层记忆管理 | 状态机+文件 | MaaS | L3活 | 无 | 心智状态机 | 全局同步 | - | - | - | - | 心智审计 | 全局同步 | 待确认 |
| MineContext | 外部记忆增强 | 文件树+向量 | 插件 | L1半活 | 无 | 目录浏览 | 主动预加载 | - | - | - | - | 目录浏览 | 单Agent | 待确认 |
| Ori-Mnemos | 类OS分层记忆管理 | 文件树+向量 | MaaS | L2活 | 重要性 | 层次结构 | 递归压缩 | - | - | - | - | 可视化 | 单Agent | 待确认 |
| agentmemory | 外部记忆增强 | BM25+Vector(本地) | npm插件 | L0死 | 无 | 混合检索 | ~99%★(170K/yr vs 19.5M) | - | - | 95.2%(R@5,LongMemEval-S) | - | Real-time Viewer | 单Agent | MIT |

> 注：部分系统仍以项目自报、媒体报道或待确认材料为主，不能与独立 benchmark 结果等量齐观。

### B. 核心学术论文索引（34 篇主论文 + 6 篇安全论文）

#### B.1 主论文

| # | 论文 | 年份 | arXiv ID | 核心创新 | 数据可信度 |
|---|------|------|----------|---------|-----------|
| 1 | Memorizing Transformers | 2022 | 2203.08913 | kNN-注意力外部KV记忆 | ★☆ |
| 2 | MemoryLLM | 2024 | 2402.04624 | 参数级自更新记忆 | ★☆ |
| 3 | LongMem | 2023 | 2305.06239 | 解耦记忆侧网络 | ★☆ |
| 4 | Infini-attention | 2024 | 2404.07143 | 压缩记忆融入注意力 | ★☆ |
| 5 | LM2 | 2024 | 2411.02237 | 精确+压缩双记忆 | ★☆ |
| 6 | MemGPT / Letta | 2023 | 2310.08560 | 虚拟上下文管理 | ★☆ |
| 7 | EverMemOS | 2026 | 2601.02163 | 自组织记忆OS | ☆ 自建基准 |
| 8 | HyperMem | 2026 | 2604.08256 | 超图记忆模型 | ☆ 自建基准 |
| 9 | RMT | 2022 | 2207.06881 | 循环记忆 token | ★☆ |
| 10 | Reflexion | 2023 | 2303.11366 | 语言反思强化学习 | ★☆ |
| 11 | Generative Agents | 2023 | 2304.03442 | 记忆流+反思+三维检索 | ★ |
| 12 | MemoryBank | 2024 | 2305.10250 | Ebbinghaus遗忘曲线 | ★☆ |
| 13 | A-MEM | 2025 | 2502.12110 | 记忆即Agent | ★☆ |
| 14 | ExpeL | 2024 | 2308.10144 | 经验->洞察->技能闭环 | ★☆ |
| 15 | Voyager | 2023 | 2305.16291 | 可执行代码技能库 | ★☆ |
| 16 | Zep / Graphiti | 2024 | - | 时序知识图谱 | ★☆ |
| 17 | RAP | 2023 | 2305.14992 | LLM推理重构为规划 | ★☆ |
| 18 | MemoRAG | 2024 | 2409.05591 | 记忆引导检索 | ★☆ |
| 19 | LoCoMo | 2024 | 2402.17753 | 长期对话记忆基准 | ★ |
| 20 | LongMemEval | 2024 | 2410.10813 | 五大核心能力评估 | ★ |
| 21 | MemBench | 2025 | 2506.21605 | 统一评估框架 | ★ |
| 22 | EverBench | 2026 | 2602.01313 | 多方协作对话评估 | ★☆ |
| 23 | MINDSTORES | 2024 | 2406.03023 | 多Agent记忆架构 | ★☆ |
| 24 | MemLong | 2024 | 2402.15359 | 选择性KV保留+检索增强 | ★☆ |
| 25 | CacheGen | 2024 | 2310.07240 | KV Cache压缩流式传输 | ★☆ |
| 26 | CoALA | 2024 | 2309.02427 | 认知架构理论框架 | ★ |
| 27 | DeepSeek Engram | 2026 | 待确认 | 条件记忆模块嵌入 MoE 架构 | ☆ 待验证 |
| 28 | ICLR STEM | 2026 | 2601.10639 | 查表式记忆，提升可编辑性 | ★☆ |
| 29 | TiMem | 2026 | 2601.02845 | CLS 时序分层记忆树 + 复杂度感知召回 | ★☆ |
| 30 | Omni-SimpleMem | 2026 | 2604.01007 | AI 自主研究发现记忆架构 | ★☆ |
| 31 | LiCoMemory | 2025 | 2511.01448 | 轻量认知图谱 + 时序层次搜索 | ★☆ |
| 32 | MIRIX | 2025 | 待确认 | 6 类记忆 + Active Retrieval + 多智能体协同 | ★☆ |
| 33 | MemBrain 1.0 | 2026 | Feeling AI技术报告 | LLM亲和记忆 + 子Agent协调 + 时间戳标准化 | ☆ 自报 |
| 34 | MemoryOS | 2025 | 2506.06326 | 三层记忆 + 热度驱动更新 + 语义感知检索 | ★☆ |

#### B.2 安全论文

| # | 论文 | 年份 | arXiv ID | 核心发现 |
|---|------|------|----------|---------|
| S1 | AgentPoison | 2024 | 2407.12784 | 记忆投毒攻击框架，成功率高 |
| S2 | BadRAG | 2024 | 2402.16893 | RAG 后门攻击 |
| S3 | PoisonedRAG | 2024 | 2402.07867 | 知识投毒攻击 |
| S4 | 间接注入攻击 | 2023 | 2302.12173 | 可经外部数据源注入恶意指令 |
| S5 | MINJA 防御 | 2026 | 2601.05504 | 提出 trust-aware moderation 与 sanitization |
| S6 | eTAMP | 2026 | 2604.02623 | 跨会话跨站点环境注入记忆投毒 |

### C. 弱证据与生态补充条目

以下条目值得跟踪，但**不进入主论证链条**：

| 条目 | 说明 | 本轮处理 |
|------|------|---------|
| **xiaoclaw-memory** | 极简 Markdown 分层设计有启发 | 保留为低成本方案参考 |
| **lossless-claw** | append-only / lossless context 管理思想有价值 | 保留为设计模式参考 |
| **MindForge** | multi-level memory library 方向清晰，但一手评测链条不足 | 不纳入主结论 |
| **MineContext** | 更接近 context engineering / proactive assistant | 视为相邻方向 |
| **MemaryAI** | “模仿人类记忆”叙事成立，但技术链条有限 | 不纳入主线 |
| **MindOS** | 更偏人机协作心智系统叙事 | 视为相邻系统 |
| **Ori-Mnemos** | local-first persistent agentic memory 值得跟踪 | 作为 local-first 路线补充观察 |
| **MemMachine v0.2** | 公开证据链不足，需进一步核验 | 标记为待确认 |

### D. 参考文献与一手来源

#### D.1 核心理论与 benchmark

- CoALA: <https://arxiv.org/abs/2309.02427>
- LoCoMo: <https://arxiv.org/abs/2402.17753>
- LoCoMo Project Page: <https://snap-research.github.io/locomo/>
- LongMemEval: <https://arxiv.org/abs/2410.10813>
- MemBench: <https://arxiv.org/abs/2506.21605>

#### D.2 模型记忆

- Memorizing Transformers: <https://arxiv.org/abs/2203.08913>
- MSA: <https://arxiv.org/abs/2603.23516>
- MemoryLLM: <https://arxiv.org/abs/2402.04624>
- MemoryLLM GitHub: <https://github.com/wangyu-ustc/MemoryLLM>
- STEM: <https://arxiv.org/abs/2601.10639>

#### D.3 LLM 决策记忆与框架

- mem0 Docs: <https://docs.mem0.ai/introduction>
- mem0 GitHub: <https://github.com/mem0ai/mem0>
- Mem0 Paper: <https://arxiv.org/abs/2504.19413>
- LangMem GitHub: <https://github.com/langchain-ai/langmem>
- LangMem Docs: <https://langchain-ai.github.io/langmem/>
- Hermes Agent GitHub: <https://github.com/NousResearch/hermes-agent>

#### D.4 外部记忆增强

- OpenViking GitHub: <https://github.com/volcengine/OpenViking>
- OpenViking Blog: <https://www.openviking.ai/blog>
- memsearch GitHub: <https://github.com/zilliztech/memsearch>
- memsearch Docs: <https://zilliztech.github.io/memsearch/>
- memU GitHub: <https://github.com/NevaMind-AI/memU>
- memU Site: <https://memu.pro/>
- Acontext GitHub: <https://github.com/memodb-io/Acontext>
- Acontext Docs: <https://docs.acontext.io/>
- Voyager: <https://arxiv.org/abs/2305.16291>
- Memoria GitHub: <https://github.com/matrixorigin/Memoria>
- Graphiti GitHub: <https://github.com/getzep/graphiti>
- Graphiti Docs: <https://help.getzep.com/graphiti>

#### D.5 图式、分层与 OS-like

- Letta GitHub: <https://github.com/letta-ai/letta>
- Letta Docs: <https://docs.letta.com/>
- MemGPT Paper: <https://arxiv.org/abs/2310.08560>
- MemOS GitHub: <https://github.com/MemTensor/MemOS>
- MemOS Site: <https://memos.openmem.net/>
- TiMem: <https://arxiv.org/abs/2601.02845>
- EverMemOS: <https://arxiv.org/abs/2601.02163>
- HyperMem: <https://arxiv.org/abs/2604.08256>
- LiCoMemory: <https://arxiv.org/abs/2511.01448>

#### D.6 多 Agent 共享/隔离

- ContextLoom GitHub: <https://github.com/danielckv/ContextLoom>
- eion GitHub: <https://github.com/eiondb/eion>
- eion Site: <https://www.eiondb.com/>
- MIRIX Docs: <https://docs.mirix.io/>
- mem9 GitHub: <https://github.com/mem9-ai/mem9>
- mem9 Site: <https://mem9.ai/>
- honcho GitHub: <https://github.com/plastic-labs/honcho>
- honcho Docs: <https://docs.honcho.dev/>

#### D.7 插件与生态

- claude-mem GitHub: <https://github.com/thedotmack/claude-mem>
- claude-mem Site: <https://claude-mem.ai/>
- lossless-claw GitHub: <https://github.com/Martian-Engineering/lossless-claw>
- xiaoclaw-memory GitHub: <https://github.com/huafenchi/xiaoclaw-memory>
- ultraContext GitHub: <https://github.com/ultracontext/ultracontext>

#### D.8 方法论说明

本融合版相对两份源文稿的关键修正如下：

1. 将“模型原生记忆”统一重构为“模型记忆”，并拆成运行时访问、参数内化、可解释参数模块三条子路线。
2. 将“OS 内存页置换”统一修正为“类 OS 分层记忆管理”，避免误导性的硬件隐喻。
3. 将 v0.2 中的 C.A.P.E 对比、框架图、CortexMem 方案和附录保留为主体，并用证据等级和分类边界做逻辑校正。
4. 将原 report.md 的方法论、九类分类、五层工程栈、跨体系综合判断和参考文献组织方式并入主文。
5. 删除了与主题无关的示例段落，避免技术方案被杂音污染。
6. 修正了附录标题与实际条目数不一致的问题，使正文、附录和统计口径统一。
