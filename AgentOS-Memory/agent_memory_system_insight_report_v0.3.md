# Agent Memory System 证据优先研究报告（2026-04 重写版）

> 重写目标：将原文从“综述 + 方案书 + 排行榜”混合体，重构为“证据优先、定义清晰、逻辑闭环”的研究报告。
>
> 本版只保留在本次修订中完成一手来源核验的系统、论文、基准与安全研究。对证据不足或难以核验的条目，不再放入主论证链条，而是降级到附录。

---

## 执行摘要

本次重写后，可以把 Agent Memory 领域压缩为四个核心判断：

1. **“Agent Memory”不是单一技术，而是一组不同层次的问题。**
   同一个词经常混用了四类对象：跨会话外部记忆、上下文管理框架、结构化知识层、模型原生记忆模块。把它们混成一个榜单，是当前许多报告失真的根本原因。

2. **当前证据最强的工程路线，不是“纯向量库外挂”，也不是“模型自己记住一切”，而是：**
   **外部持久记忆 + 结构化索引/时间结构 + 检索/压缩/治理策略**。
   这条路线在 mem0、Zep/Graphiti、TiMem、LiCoMemory、MIRIX 等工作中都能看到。

3. **“Memory OS”是有用的研究隐喻，但还不是统一的工业标准层。**
   MemGPT/Letta、MemOS、MemoryOS、EverMemOS 都借用了操作系统语言来描述记忆层级和调度，但它们实现的是软件层级的记忆组织与调度策略，而不是字面意义上的硬件页置换或虚拟内存。

4. **安全与治理不是附属问题，而是记忆系统的内生要求。**
   AgentPoison 与 eTAMP 表明：一旦记忆跨会话持久化，攻击面就从单轮 prompt 扩展为长期、跨任务、跨站点的持久攻击面。没有 provenance、隔离、回滚、写入审计的 memory system，在生产中并不完整。

---

## 第0章：方法论与证据规则

### 0.1 本报告如何定义“记忆”

本报告只把以下能力视为严格意义上的 Agent Memory：

- **跨会话持久化**：信息在一次对话结束后仍可被未来会话调用。
- **可检索或可复用**：系统能在后续任务中主动使用这些信息。
- **可更新**：系统能增量写入、合并、失效、压缩或重组既有记忆。

本报告明确区分四类对象：

| 类别 | 定义 | 典型代表 |
|------|------|---------|
| **外部持久记忆系统** | 在模型外保存用户事实、事件、技能、资源，并在后续任务中检索使用 | mem0、LangMem、Zep/Graphiti、TiMem |
| **上下文管理/Agent 平台** | 让 agent 管理当前上下文与外部记忆层之间的切换 | Letta / MemGPT |
| **结构化/图式记忆层** | 通过图、时间层次、实体关系或多记忆类型提升检索与推理 | Graphiti、LiCoMemory、A-MEM、MIRIX |
| **模型原生记忆** | 直接修改 Transformer 结构、参数或注意力中的“记忆原语” | Memorizing Transformers、Infini-attention、MemoryLLM、Engram、STEM |

### 0.2 本报告不把什么当作主线对象

以下内容在原报告中被混入同一比较框架，但本版将其剥离：

- **长上下文能力**：上下文窗口很长，不等于有长期记忆。
- **KV cache 优化**：这类工作主要优化推理时状态管理，不天然具备跨会话持久记忆。
- **单纯的 RAG / 向量检索**：如果没有稳定的记忆写入、更新与治理机制，它更像检索增强，而非完整 memory system。
- **仅有市场宣传而缺少一手技术材料的系统**：不进入主论证。

### 0.3 证据分级

| 等级 | 含义 |
|------|------|
| **A** | 官方文档/官方仓库与论文能够相互印证，系统定位清晰 |
| **B** | 有一手来源，但主要证据来自预印本或官方自报 |
| **C** | 有官方来源，但论文、产品、评测口径并不完全一致，结论需谨慎 |
| **X** | 本次修订未找到足够可靠的一手来源，不进入主文 |

### 0.4 本版修订原则

- **只用一手来源**：官方文档、官方仓库、原始论文、官方项目页。
- **数字必须带上下文**：必须说明 benchmark、metric、设置与“谁报告了这个数字”。
- **推断与事实分离**：文中会区分“已验证事实”和“作者分析”。
- **同类才比较**：文本记忆系统不与多模态记忆系统直接排榜；外部 memory layer 不与模型原生记忆直接排榜。

---

## 第1章：产业系统全景

### 1.1 当前版图：不是一个榜单，而是七类系统

经本次核验，当前 Agent Memory 的主流系统大致可分为七类：

1. **记忆层 SDK / 中间件**
   代表：mem0、LangMem
2. **上下文管理 / Stateful Agent 平台**
   代表：Letta / MemGPT
3. **时序图/上下文图记忆**
   代表：Zep / Graphiti、LiCoMemory、A-MEM
4. **分层或“Memory OS”式管理**
   代表：MemOS、TiMem、EverMemOS、MemoryOS
5. **多记忆类型 / 多智能体协调**
   代表：MIRIX、Omni-SimpleMem
6. **程序性/可执行技能记忆**
   代表：Voyager
7. **模型原生记忆机制**
   代表：Memorizing Transformers、Infini-attention、MemoryLLM、Engram、STEM

最重要的修正是：

- **“OS”不应被按字面理解为页置换实现。**
  现有系统借用的是“分层、调度、冷热分离、回收”这些软件工程思想，而非硬件或内核级机制。
- **“记忆系统”与“记忆研究论文”也不能混为一谈。**
  有些对象是可部署产品或 SDK，有些对象是结构论文，有些只是 benchmark 上的新方法。

### 1.2 代表系统证据卡

下表不是排行榜，而是“已核验系统的技术定位表”。

| 系统 | 类别 | 已验证机制 | 公开证据 | 证据等级 | 应如何解读 |
|------|------|-----------|---------|---------|-----------|
| **Letta / MemGPT** | 上下文管理 / Stateful agent | MemGPT 论文提出 **virtual context management**，Letta 当前文档明确提供 stateful agents、memory blocks、shared memory、archival memory、context hierarchy | [R3][R4] | A | 更适合视为“让 agent 主动管理记忆层级的框架”，而不是独立 benchmark leader |
| **mem0** | 记忆层 SDK / 中间件 | 官方文档定位为 universal, self-improving memory layer；论文描述为动态 **extract / consolidate / retrieve**，并扩展到 graph memory | [R1][R2] | B | 代表“工程上可落地的外部记忆层”路线；其优势主要来自稀疏记忆读写而非 full-context 暴力拼接 |
| **LangMem** | 框架级记忆基础设施 | 提供 hot-path memory tools、background memory manager、LangGraph store 原生集成 | [R5][R6] | A | 不是单独的 memory OS，而是把长期记忆能力嵌入 agent framework 的基础设施 |
| **Zep / Graphiti** | 时序图记忆 / 托管平台 | Graphiti 官方仓库明确是 temporal context graph；追踪事实有效期、source provenance，支持 semantic + keyword + graph traversal 混合检索 | [R7][R8] | A | 代表“时间与 provenance 作为一等公民”的图式记忆路线 |
| **MemOS** | Memory OS / 统一抽象 | 论文提出 parametric、activation、plaintext 三类记忆与 MemCube；官方仓库进一步产品化为 KB、multimodal memory、tool memory 与 scheduler | [R9][R10] | C | 概念论文与当前产品仓库存在演进关系，但不是完全同一工件，读数时必须避免混用 |
| **TiMem** | 分层时间记忆 | 提出 Temporal Memory Tree，强调 temporal-hierarchical organization、semantic-guided consolidation、complexity-aware recall | [R11] | B | 这是当前“时间层次化 consolidation”路线中表述最清晰的一篇工作 |
| **LiCoMemory** | 轻量图式记忆 | 提出 CogniGraph 作为 lightweight hierarchical graph，用 temporal/hierarchy-aware search + reranking 实时更新和检索 | [R12] | B | 代表“不要把图做得过重，而要把图当成认知索引层”这一方向 |
| **EverMemOS** | 自组织 Memory OS | 通过 MemCells、MemScenes 与 engram-inspired lifecycle 实现 episodic trace formation、semantic consolidation、reconstructive recollection | [R13] | B | 概念完整，评测声明强，但目前主要仍是论文自报 |
| **MemoryOS** | 三层 Memory OS | 定义 short-term、mid-term、long-term 三层，结合 dialogue-chain FIFO 与 segmented page organization | [R14] | B | 典型的“OS 隐喻型”研究系统；有明确层次与更新规则，但评测口径与其他工作不完全可比 |
| **MIRIX** | 多记忆类型 + 多智能体协调 | 官方文档与论文都明确给出 six memory types：Core、Episodic、Semantic、Procedural、Resource、Knowledge Vault，并由多 agent 协同管理 | [R15][R16] | A | 代表“把记忆拆成异构记忆类型，再用 controller 协调”的多智能体路线 |
| **Omni-SimpleMem** | 自动研究发现的多模态记忆 | 重点不是单一结构，而是 autonomous research pipeline 自动搜索 memory architecture、prompting、data pipeline | [R17] | B | 这项工作更重要的贡献是“让 AI 自己发现 memory design”，而不只是其最终结构 |
| **A-MEM** | Agentic memory / 动态链接记忆 | 以 Zettelkasten 为灵感，强调 dynamic indexing、linking 与 memory evolution | [R18] | B | 代表“记忆本身是动态组织过程”，而非固定 schema |
| **Voyager** | 程序性/技能记忆 | 把技能存成 executable code skill library，并通过 environment feedback 持续改进 | [R19] | A | 它不是对话记忆系统，而是程序性记忆的典型范例 |

### 1.3 已验证的系统级趋势

#### 结论一：外部记忆层已经从“向量库外挂”转向“写入治理 + 结构化索引”

mem0、LangMem、Zep/Graphiti、LiCoMemory、TiMem 的共同点是：

- 不再把“记忆”理解为一堆语义向量；
- 而是把“记忆写入”本身视为设计重点；
- 同时引入层次、时间、图关系、背景 consolidation 或多类型分工。

这意味着：**Agent Memory 的核心瓶颈，已经从“存不存得下”转向“写得对不对、取得准不准、错了怎么治理”。**

#### 结论二：时间结构正在取代扁平语义近邻，成为长期记忆的关键组织原则

这条线在不同系统里表现为不同形式：

- Zep / Graphiti：事实有效期与 provenance；
- TiMem：Temporal Memory Tree；
- LiCoMemory：temporal and hierarchy-aware search；
- MemoryOS：short/mid/long 三层；
- EverMemOS：episodic 到 semantic 的生命周期。

这不是巧合。长期记忆系统一旦跨会话运行，最常见错误不是“完全找不到”，而是：

- 找到了旧事实；
- 找到了过期事实；
- 找到了相关但时间顺序错误的事实；
- 找到了零散片段，却无法重建事件链。

#### 结论三：多智能体/多类型记忆是新趋势，但工程成熟度仍不均衡

MIRIX 与 Omni-SimpleMem 都说明，单一 memory bucket 很难覆盖：

- 个人画像；
- 事件轨迹；
- 工具使用经验；
- 文档资源；
- 敏感凭证；
- 多模态经验。

但这类系统的复杂度也显著更高，常见代价包括：

- 写入路径更长；
- 类型冲突更难治理；
- 评测更容易“自定义任务胜出、跨系统不可比”。

#### 结论四：Memory OS 是研究方向，不是行业标准

“Memory OS”目前至少对应四种不同含义：

- MemGPT/Letta：上下文层级管理；
- MemOS：统一记忆抽象与生命周期治理；
- MemoryOS：三层记忆与更新策略；
- EverMemOS：自组织、生命周期式记忆编排。

因此，“某系统是 Memory OS”并不能自动说明其结构、性能或适用场景，必须回到一手材料看具体实现。

---

## 第2章：核心技术与学术脉络

### 2.1 CoALA：为什么它仍然是理解记忆系统的最好起点

CoALA（Cognitive Architectures for Language Agents）提出，语言 agent 应该被理解为一个带有：

- 模块化记忆组件，
- 结构化动作空间，
- 广义决策过程

的认知架构，而不是单个 prompt 或单个模型调用 [R20]。

它对今天的价值不在于给出具体实现，而在于提供了一个稳定框架：

- **记忆不是单表存储，而是多模块协作；**
- **记忆、行动、外部环境访问是一个统一闭环；**
- **“语言 agent 记忆”应该被放回认知架构中理解。**

原报告中把许多系统直接按“实现技术”并列比较，这会掩盖一个更重要的事实：
**很多系统根本不在解决同一层的问题。**

### 2.2 外部持久记忆与上下文管理：最成熟、也最容易落地的一条路线

#### Letta / MemGPT：核心问题是“如何让有限上下文表现得像更大记忆”

MemGPT 的核心思想是 **virtual context management**：通过不同 memory tiers 的数据移动，让 LLM 在有限 context window 下表现出更长记忆 [R4]。Letta 当前产品与文档则把这条路线进一步平台化为：

- stateful agents，
- memory blocks，
- shared memory，
- archival memory，
- context hierarchy [R3]。

这条路线最重要的启示是：

- 它并不要求一开始就构建复杂知识图；
- 先把“当前上下文”和“外部记忆”分层，让 agent 能主动读写，已经能显著提升长期任务稳定性。

#### mem0：核心问题是“写入什么”和“何时召回”

mem0 的官方定位是 universal, self-improving memory layer [R1]；其论文则更明确地把问题拆成：

- 从对话中抽取 salient information；
- 对历史信息做 consolidation；
- 针对新 query 执行 retrieve [R2]。

mem0 论文报告：

- 在其 LoCoMo 设定下，相比 full-context 方法，**p95 latency 降低 91%**；
- **token cost 节省超过 90%**；
- 在其评测中，相比 OpenAI memory system 的 LLM-as-a-Judge 指标有 **26% 相对提升** [R2]。

这些结果的正确读法是：

- 说明“稀疏记忆读写”在工程上非常有价值；
- 但它们来自论文设定，不应被直接外推为所有 agent 场景下的普适结论；
- 特别是其中包含 **LLM-as-a-Judge** 指标，这与 exact-match / accuracy / F1 不是同一种度量。

#### LangMem：把记忆能力框架化，而不是单独做一个 memory 产品

LangMem 的特点是：

- 提供 memory API；
- 提供 hot-path memory tools；
- 提供 background memory manager；
- 直接依附 LangGraph store [R5][R6]。

它体现的不是“最强单体系统”，而是一种更现实的产品观：
**在 agent framework 内原生支持长期记忆，比单独再拼一层外部产品更容易被工程团队采用。**

### 2.3 时间图与结构化记忆：从“相似文本”走向“可追溯事实”

#### Zep / Graphiti：把“事实有效期”和“来源”做成一等公民

Graphiti 明确把自己定义为 **temporal context graph**：

- 跟踪事实如何随时间变化；
- 为事实保留 validity window；
- 为每个实体与关系保留 provenance 到原始 episode；
- 支持 semantic + keyword + graph traversal 混合检索 [R7]。

Zep 论文进一步给出两个重要点：

- 在 DMR benchmark 上，Zep 报告 **94.8% vs 93.4%** 优于 MemGPT；
- 在 LongMemEval 上，报告 **最高 18.5% 准确率提升** 与 **90% 响应延迟下降** [R8]。

无论这些数字未来是否被复现，Graphiti/Zep 路线本身已经给出一个强信号：
**长期记忆的正确数据结构，不应只包含“文本内容”，还应包含时间、失效机制与来源链条。**

#### LiCoMemory：不是图越重越好，而是图该承担“认知索引”的角色

LiCoMemory 试图解决传统 graph memory 的两个常见问题：

- 图结构过重；
- 语义与拓扑缠绕得太深，更新与检索都变慢。

它引入的 CogniGraph 是 **lightweight hierarchical graph**，把实体与关系作为语义索引层，再配合 temporal / hierarchy-aware search 和 reranking [R12]。

这一点非常重要，因为很多工业场景并不需要全量知识图推理，而只需要：

- 把“谁、何时、与什么相关”组织清楚；
- 让召回不再只靠 embedding 邻近。

#### A-MEM：结构化不仅是 schema，还是一种持续重组能力

A-MEM 的贡献不是“图数据库”本身，而是 **dynamic indexing and linking** 与 **memory evolution** [R18]。

这说明一个更深层的问题：
**长期记忆并不是“先定 schema，再一直写进去”就结束了；随着新经验到来，旧记忆的语义组织本身也需要被重写。**

### 2.4 分层 consolidation：长期记忆的关键不只是召回，还有压缩与升维

#### TiMem：时间层次树是当前最清晰的 consolidation 设计之一

TiMem 的核心是 Temporal Memory Tree：

- 从原始 conversational observations 逐级 consolidation；
- 向上抽象到 persona representations；
- 用 complexity-aware recall 在不同复杂度 query 下权衡精度与效率 [R11]。

论文自报结果中，TiMem 在统一设定下达到：

- **LoCoMo 75.30%**
- **LongMemEval-S 76.88%**
- 同时在 LoCoMo 上 **recalled memory length 降低 52.20%** [R11]

TiMem 值得重视，不仅因为数值本身，更因为它把“层次化 consolidation”说清楚了：

- 低层保留细节；
- 高层保留抽象画像；
- 查询复杂度决定走哪一层。

#### MemOS、MemoryOS、EverMemOS：三个不同版本的“层次化调度”

这三个名字相近，但不能混为一谈：

- **MemOS**：强调统一抽象，把 parametric、activation、plaintext memory 纳入同一语义框架，并用 MemCube 描述异构记忆 [R9]。当前官方仓库则进一步加入 KB、tool memory、multimodal memory 与 scheduler [R10]。
- **MemoryOS**：强调三层存储与显式更新规则，short-term -> mid-term 用 dialogue-chain FIFO，mid-term -> long-term 用 segmented page organization [R14]。
- **EverMemOS**：强调 engram-inspired lifecycle，通过 MemCells、MemScenes 与 reconstructive recollection 构造自组织记忆流程 [R13]。

这三者共同表明：

- 分层已经成为共识；
- 但“如何分层、如何迁移、何时失效、如何召回”仍然没有统一答案；
- 因此“Memory OS”更像一个研究议程，而不是收敛的工业标准。

### 2.5 程序性记忆：真正可复用的长期能力，往往不是文本，而是可执行技能

Voyager 是程序性记忆的经典例子。它把技能保存为 **ever-growing skill library of executable code**，而不是文本摘要 [R19]。

它的关键价值不在 Minecraft 本身，而在于说明：

- 某些长期能力无法被自然语言描述充分压缩；
- 最稳健的“记忆”形态，是可执行、可组合、可验证的技能单元。

如果面向 coding agent、运维 agent 或 workflow agent 设计记忆层，那么“程序性记忆”通常比“把经验总结成一段文字”更重要。

### 2.6 模型原生记忆：重要，但不能与外部 agent memory 混排

这一类工作直接改 Transformer 或参数，不等同于外部持久 memory system。

#### 模型原生记忆机制对比

| 技术 | 核心机制 | 已验证能力 | 应如何解读 |
|------|---------|-----------|-----------|
| **Memorizing Transformers** | 在推理时对最近 (key, value) 做 approximate kNN lookup | memory size 扩到 262K tokens 时性能继续提升，并可在测试时利用新定义函数/定理 [R25] | 这是 inference-time external memory primitive，不是跨会话用户记忆系统 |
| **Infini-attention** | 在 attention 中引入 compressive memory，把 local attention 与 long-term linear attention 合在一个 block 内 | 目标是 bounded memory and computation 下处理极长输入，论文展示 1M passkey retrieval 与 500K summarization [R26] | 重点是无限长上下文，不是用户级长期记忆 |
| **MemoryLLM** | 在 Transformer latent space 中加入 fixed-size memory pool，使模型可 self-update | 论文报告可进行大量 memory updates，并保持 long-term retention [R27] | 它解决的是“模型如何更新知识”，不是“agent 如何管理外部用户记忆” |
| **Engram** | 通过 O(1) deterministic lookup 的 conditional memory 模块，为 Transformer 增加 static memory 轴 | 官方仓库与论文都强调其是 MoE 之外的另一条 sparsity axis，并支持 host memory offload [R28] | 它更接近“知识查表原语”，适合讨论架构级记忆而非 agent product memory |
| **STEM** | 用 token-indexed embedding lookup 替换 FFN up-projection | 论文强调更高 parametric capacity、可解释知识编辑、长上下文随长度增长激活更多参数 [R29] | 这是 parametric memory scaling 技术，不是跨会话外部记忆 |

因此，本报告给出一个明确结论：

> **模型原生记忆与外部 agent memory 不是互斥关系，而是不同层级。**
>
> 对通用 agent 来说，更合理的完整栈通常是：
> **参数记忆 / 架构记忆 + 推理期上下文机制 + 外部持久用户记忆**。

---

## 第3章：基准、可信度与安全

### 3.1 当前最常见的记忆 benchmark

| Benchmark | 主要来源 | 关注点 | 使用时的注意事项 |
|-----------|---------|-------|----------------|
| **LoCoMo** | 官方项目页与论文《Evaluating Very Long-Term Conversational Memory of LLM Agents》[R22][R24] | 长期、多会话对话记忆；包含问答、事件总结、多模态对话生成 | LoCoMo 在不同公开版本摘要中的统计口径并不完全一致；引用数字时要标明版本与任务 |
| **LongMemEval** | 论文与官方仓库 [R23] | 五类长期记忆能力：information extraction、multi-session reasoning、temporal reasoning、knowledge updates、abstention | 论文同时存在 LongMemEval 与 LongMemEval-S 等设置，不能直接混排 |
| **DMR** | 由 MemGPT 团队建立，Zep 论文用于对比 [R8] | 深层记忆检索 | 覆盖面比 LongMemEval 更窄，不能代表完整长期记忆能力 |
| **ScreenshotVQA** | MIRIX 论文 [R16] | 多模态截图记忆与理解 | 与文本型 LoCoMo/LongMemEval 不可直接比较 |
| **Mem-Gallery** | Omni-SimpleMem 论文 [R17] | 多模态 lifelong memory | 不能拿其 F1 与 LoCoMo accuracy 做统一榜单 |

### 3.2 为什么当前“排行榜”大多不严谨

当前关于 agent memory 的大量横向比较并不可靠，原因至少有五类：

1. **benchmark 不同**
   LoCoMo、LongMemEval、DMR、ScreenshotVQA、Mem-Gallery 测的是不同能力。

2. **metric 不同**
   常见指标包括 accuracy、F1、BLEU-1、LLM-as-a-Judge、retrieval recall。它们不能直接并列排名。

3. **setting 不同**
   比如 TiMem 报告的是 LongMemEval-S [R11]，而 Zep 用的是 LongMemEval [R8]；这不是同一个测试集合。

4. **backbone 不同**
   不同论文使用不同基础模型、embedding、judge model、context budget；很多“memory 胜利”其实一部分来自底座差异。

5. **产品版本与论文版本漂移**
   MemOS 是最典型案例：概念论文、官方仓库、官方文档都在快速演进，若不标明来源，就容易把不同阶段的结构与数字混在一起。

因此，本报告拒绝使用“统一 SOTA 排名表”。在当前阶段，更科学的写法是：

- 先问：**比较的是不是同一类系统？**
- 再问：**benchmark、metric、模型底座是否一致？**
- 最后才问：**数字是否值得横向解读？**

### 3.3 数字应当如何被正确解读

下面是几个典型例子：

- **mem0**
  论文中的 91% p95 latency 下降与 >90% token 节省，比较对象是 full-context 方法 [R2]。这说明“记忆稀疏化”很有工程价值，但不是对所有 memory system 的统一胜率证明。

- **TiMem**
  论文给出了 LoCoMo 与 LongMemEval-S 的明确结果 [R11]。这使它比“只给提升百分比、不报绝对值”的工作更容易分析，但它依然是论文自报。

- **MemoryOS**
  论文给出的是“相对 baseline 平均提升 49.11% F1、46.18% BLEU-1” [R14]。这种数字说明方法有效，但不能直接与别家的绝对 accuracy 排名混排。

- **Omni-SimpleMem**
  论文强调的是从 0.117 到 0.598 的 F1 提升 [R17]。它非常适合证明“autoresearch pipeline 有用”，但不应用来声称“当前长时记忆精度第一”。

### 3.4 安全：长期记忆让 agent 更强，也让攻击更持久

#### AgentPoison：记忆库或知识库一旦被投毒，攻击可以长期生效

AgentPoison 直接把风险说得非常清楚：

- 目标是 generic and RAG-based LLM agents；
- 攻击方式是 **poisoning long-term memory or RAG knowledge base**；
- 不需要额外训练或微调；
- 在三个真实 agent 上，**平均 attack success rate 高于 80%**；
- benign performance 影响 **低于 1%**；
- poison rate **低于 0.1%** [R30]

这意味着：对长期记忆系统来说，“能写进去”本身就是风险入口。

#### eTAMP：更现实的威胁模型是“环境观察污染”，而不是黑客直接写库

eTAMP 进一步推进了这个结论：

- 只需要 agent 观察到一次被污染环境；
- 不需要直接访问 memory storage；
- 可以实现 **cross-session、cross-site** compromise；
- 在其实验中，ASR 最高可到 **32.5%**；
- 在 frustration exploitation 条件下，ASR 可提高 **最多 8 倍** [R31]

这篇工作最重要的启示不是具体数字，而是威胁模型：
**只要 agent 会把外部观察写入长期记忆，网页、文档、应用界面本身都可能成为持久投毒入口。**

### 3.5 从安全研究反推，生产级 memory system 至少应具备的治理能力

结合 AgentPoison、eTAMP 与已有系统设计，本报告认为生产级 memory system 至少应具备：

1. **写入 provenance**
   每条记忆要知道来自哪条对话、哪个页面、哪个工具调用、哪个时间点。

2. **source trust / namespace isolation**
   用户事实、网页观察、工具输出、第三方文档、系统提示衍生记忆，至少不能放在同一信任层。

3. **失效与冲突管理**
   Graphiti 的 validity window 是一种做法；更广义地说，系统必须能表达“曾经为真，但现在失效”。

4. **可审计与可回滚**
   安全上，回滚不是高级功能，而是污染修复能力。

5. **在线写入与后台 consolidation 分离**
   高风险观测先进入隔离层，再通过背景任务升格到长期语义记忆，通常比“直接写主库”更安全。

---

## 第4章：对通用 Agent Memory 设计的启示

本章不是“已验证产品方案”，而是基于前述证据推导出的工程原则。

### 4.1 应坚持的设计原则

#### 原则一：默认采用外部持久记忆，不指望单次上下文或模型参数包办一切

原因很直接：

- 用户偏好、长期任务、历史事件、工具经验，本质上都是跨会话状态；
- 这类状态不适合完全依赖 context window；
- 也不适合完全依赖参数更新。

#### 原则二：把时间与 provenance 做成一等公民

如果没有时间与来源字段，系统很快会在以下问题上失真：

- 新旧事实冲突；
- 历史事件顺序混乱；
- 画像被旧偏好污染；
- 安全审计无法定位写入源头。

#### 原则三：记忆至少分成语义、事件、程序性三类

这条原则同时得到 CoALA、MIRIX、Voyager 与实际工程经验支持：

- **语义记忆**：稳定事实、画像、偏好；
- **事件记忆**：发生了什么、何时发生、与谁相关；
- **程序性记忆**：能复用的步骤、脚本、工具调用模式、技能。

如果把三者全部压成“文本片段”，后续检索与治理都会变差。

#### 原则四：在线召回与后台 consolidation 必须并存

只做在线召回，系统会越来越嘈杂；
只做后台 consolidation，系统会失去交互时效性。

更合理的结构是：

- 在线层：快速写入、快速召回；
- 后台层：抽取事实、合并画像、形成技能、失效旧事实。

#### 原则五：可观测性不是附加项

对工程团队而言，长期记忆的最难点不是“怎么做出 Demo”，而是：

- 为什么这条记忆被写入？
- 为什么这条记忆被召回？
- 召回失败是因为没写、没索引、没命中，还是被过滤？

因此，人类可读的 inspection surface 很重要。纯黑盒向量层在生产调试中往往不够。

### 4.2 一个克制的通用架构草案（CortexMem 草案）

下述草案只代表“从现有证据导出的最小合理架构”，不代表已被实测验证。

#### 架构分层

| 层 | 作用 | 建议实现 |
|----|------|---------|
| **L0 Raw Episodes** | 保存原始对话、工具输出、网页观察、文档片段 | append-only event log，保留 provenance |
| **L1 Structured Facts / Events** | 抽取实体、关系、时序事件、可失效事实 | temporal graph 或层次索引 |
| **L2 Profiles / Semantic Memory** | 用户画像、长期偏好、稳定知识 | 结构化文档 + 检索索引 |
| **L3 Procedural Memory** | 可执行技能、脚本模板、工作流经验 | code / tool recipe / checked workflow |
| **治理侧车层** | trust、审计、冲突、隔离、回滚 | provenance ledger + write policy + quarantine |

#### 读路径

推荐采用四阶段：

1. **命名空间与信任过滤**
   先决定从哪些 memory spaces 读。

2. **时间 / 实体 / 类型过滤**
   先缩小候选集合，而不是直接全量语义检索。

3. **语义检索 + 结构扩展 + rerank**
   先找候选，再按关系/时间扩展，再重排。

4. **最小必要上下文拼装**
   返回 agent 真正需要的记忆，而不是把整库拼进 prompt。

#### 写路径

推荐采用双路径：

- **在线写入路径**
  记录原始 episode，并允许低风险事实快速写入。

- **后台 consolidation 路径**
  周期性抽取稳定语义、合并画像、发现技能、处理冲突与失效。

### 4.3 明确不应再重复的错误主张

结合本次重写中发现的问题，后续任何方案文档都应避免：

1. **把模型原生记忆与外部 agent memory 混排成一个榜单**
2. **把 LoCoMo、LongMemEval、ScreenshotVQA、Mem-Gallery 的结果直接排总榜**
3. **把 F1、accuracy、BLEU-1、LLM-as-a-Judge 混成同一性能指标**
4. **把“OS”语言直接解释成真实页置换机制**
5. **把缺少一手来源的系统当作主线证据**

---

## 附录 A：本版保留的主要参考来源

### 系统与产品

- **[R1]** Mem0 官方文档：<https://docs.mem0.ai/introduction>
- **[R3]** Letta 官方仓库与文档：<https://github.com/letta-ai/letta> / <https://docs.letta.com/>
- **[R5]** LangMem 官方仓库：<https://github.com/langchain-ai/langmem>
- **[R6]** LangChain / LangGraph 长期记忆文档：<https://docs.langchain.com/oss/python/langchain/long-term-memory>
- **[R7]** Graphiti 官方仓库：<https://github.com/getzep/graphiti>
- **[R10]** MemOS 官方仓库：<https://github.com/MemTensor/MemOS>
- **[R15]** MIRIX 官方文档：<https://docs.mirix.io/>
- **[R28]** Engram 官方仓库：<https://github.com/deepseek-ai/Engram>

### 论文与技术报告

- **[R2]** Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory：<https://arxiv.org/abs/2504.19413>
- **[R4]** MemGPT: Towards LLMs as Operating Systems：<https://arxiv.org/abs/2310.08560>
- **[R8]** Zep: A Temporal Knowledge Graph Architecture for Agent Memory：<https://arxiv.org/abs/2501.13956>
- **[R9]** MemOS: An Operating System for Memory-Augmented Generation (MAG) in Large Language Models：<https://arxiv.org/abs/2505.22101>
- **[R11]** TiMem: Temporal-Hierarchical Memory Consolidation for Long-Horizon Conversational Agents：<https://arxiv.org/abs/2601.02845>
- **[R12]** LiCoMemory: Lightweight and Cognitive Agentic Memory for Efficient Long-Term Reasoning：<https://arxiv.org/abs/2511.01448>
- **[R13]** EverMemOS: A Self-Organizing Memory Operating System for Structured Long-Horizon Reasoning：<https://arxiv.org/abs/2601.02163>
- **[R14]** Memory OS of AI Agent：<https://arxiv.org/abs/2506.06326>
- **[R16]** MIRIX: Multi-Agent Memory System for LLM-Based Agents：<https://arxiv.org/abs/2507.07957>
- **[R17]** Omni-SimpleMem: Autoresearch-Guided Discovery of Lifelong Multimodal Agent Memory：<https://arxiv.org/abs/2604.01007>
- **[R18]** A-MEM: Agentic Memory for LLM Agents：<https://arxiv.org/abs/2502.12110>
- **[R19]** Voyager: An Open-Ended Embodied Agent with Large Language Models：<https://arxiv.org/abs/2305.16291>
- **[R20]** Cognitive Architectures for Language Agents (CoALA)：<https://arxiv.org/abs/2309.02427>
- **[R22]** Evaluating Very Long-Term Conversational Memory of LLM Agents：<https://arxiv.org/abs/2402.17753>
- **[R23]** LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory：<https://arxiv.org/abs/2410.10813>
- **[R24]** LoCoMo 官方项目页：<https://snap-research.github.io/locomo/>
- **[R25]** Memorizing Transformers：<https://arxiv.org/abs/2203.08913>
- **[R26]** Leave No Context Behind: Efficient Infinite Context Transformers with Infini-attention：<https://arxiv.org/abs/2404.07143>
- **[R27]** MEMORYLLM: Towards Self-Updatable Large Language Models：<https://arxiv.org/abs/2402.04624>
- **[R29]** STEM: Scaling Transformers with Embedding Modules：<https://arxiv.org/abs/2601.10639>
- **[R30]** AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases：<https://arxiv.org/abs/2407.12784>
- **[R31]** Poison Once, Exploit Forever: Environment-Injected Memory Poisoning Attacks on Web Agents：<https://arxiv.org/abs/2604.02623>

---

## 附录 B：本次降级或移出主文的条目

以下条目在原文中占据较大篇幅，但本次修订未将其保留在主文。原因不是“确认不存在”，而是**在本轮重写所执行的一手来源核验中，未获得足够稳定、可直接支撑主论证的官方技术材料**。

### B.1 证据不足，暂不纳入主线论证

- **MemBrain 1.0**
  本轮检索未定位到足够稳定的官方技术报告或论文页面，无法让其承担主线结论。

- **Memoria（Git for Memory）**
  原文中的“Git for Memory / GTC 2026”主张，本轮未找到足够明确、可直接引用的官方技术一手来源，因此不进入主文。

### B.2 原文提及但本轮未逐个复核的项目

原报告包含大量插件、仓库或服务名，例如：

- OpenViking
- memsearch
- memU
- xiaoclaw-memory
- lossless-claw
- ContextLoom
- eion
- honcho
- claude-mem
- ultraContext
- mindforge
- MemaryAI
- MindOS
- Ori-Mnemos
- MineContext
- agentmemory

这些条目并非被判定为无效，而是本次重写优先保留了已经完成一手来源核验、且能构成完整论证链条的系统。若后续需要，可单独开一个“长尾系统复核附录”，逐项做源码或文档核验。

---

## 附录 C：本版最重要的修订结论

与原文相比，本版做了三类关键修正：

1. **修正了分类逻辑**
   不再把所有对象放进单一“memory system 大排名”，而是先区分系统层级。

2. **修正了证据逻辑**
   不再让缺少一手来源的项目支撑主论证；不再把自报结果写成客观定论。

3. **修正了工程逻辑**
   从“谁最强”转向“哪些结构已被证据支持、哪些能力仍是风险点、一个可信的通用 memory system 应该长什么样”。

本版报告因此不再追求“看起来无所不包”，而是追求：

- 事实更准，
- 类别更清，
- 比较更公允，
- 推论更可用。
