# Vector/Graph-like 与 Filesystem-like Agent Memory 研究

> 目录：`AgentOS-Memory/fs-vector-graph/`
>
> 更新时间：2026-04-16

---

## 0. 研究范围、方法与先给结论

### 0.1 研究范围

本报告聚焦 **external memory augmentation**，即模型外的持久化记忆系统，不把 Transformer 原生记忆、参数编辑、KV cache 机制本身当作主线。

纳入主研究对象的标准是同时具备三点：

1. **跨会话持久化**
2. **可检索 / 可复用**
3. **可更新 / 可巩固**

因此，本报告的主线对象仍以已有研究材料中的系统为主：

- `Vector/Graph-like`：`MemGPT/Letta`、`mem0`、`Honcho`、`Graphiti/Zep`、`eion`、`ContextLoom`、`mem9`、`UltraContext`
- `Filesystem-like`：`OpenViking`、`memsearch`、`memU`、`Acontext`、`Voyager`、`lossless-claw`、`Memoria`

为回答“业界 SOTA 是什么”，本轮仍保留截至 `2026-04-16` 的公开一手材料校正，例如 `Mem0`、`Honcho`、`Hindsight`、`Graphiti/Zep`、`Letta` 官方文档与 benchmark / research 页面。

### 0.2 `vector-like -> filesystem-like` 理解技术演进【 -> graph-like】

从公开材料看，**行业主流最先大规模讨论和产品化的，是 `vector-like`**。原因很直接：

- 早期长期记忆问题首先被定义成 **“如何突破 context window 限制”**
- 接着被定义成 **“如何把对话抽取成长期可检索的记忆”**
- 再往后被定义成 **“如何让多个 agent / 终端共享同一个 memory plane”**

这个阶段最关键的几个公开节点是：

- `MemGPT` 论文发表于 **2023 年 10 月**
- `Letta` 官方 naming history 明确写出其演进是：
  - `MemGPT (2023)`
  - `MemGPT v2 (2024)`
  - `Letta v1 (2025)`
- `mem0`、`Graphiti/Zep`、`Honcho`、`mem9` 等后续系统，进一步把这条路线推向：
  - extraction / consolidation
  - hybrid retrieval
  - temporal graph
  - entity representation
  - shared memory service

但随着真实工程落地，行业又暴露出另一组问题：

- 记忆能召回，但**人看不懂、改不动**
- 记忆能共享，但**冲突、污染、回滚、审计困难**
- 记忆能存事实，但**技能、SOP、策略这类高价值资产沉不下来**

这正是 `filesystem-like` 在 `coding-agent / workspace memory` 语境里于 `2025-2026` 快速显学化的原因。它不是“更晚才被发明”，也不是“替代 vector memory”，而是作为一条工程回摆路线，把下面这些东西拉回了一等公民：

- 文件真相层
- 可读、可改、可迁移
- 分层加载
- skill / SOP 沉淀
- 版本治理

因此，本报告现在按下面这条主线展开：

> 业界先用 `vector-like` 解决“记得住、找得到、能共享”，再用 `filesystem-like` 补上“看得懂、改得动、可治理、能沉淀技能”，最终收敛到混合架构。

### 0.2.1 对“最新版本”和“上一版本”的批判性校正

对本文**上一版本**与**最新改写版本**做对照后，可以得到一个更稳的判断：

- **上一版本的优势**：并列比较更稳，较少把两条路线写成单线替代史；对 `filesystem-like` 的“文件真相层、可治理、可读性”把握更扎实。
- **最新版本的优势**：更接近公开材料里的主流时间线，能解释为什么 `MemGPT/Letta`、`mem0`、`Graphiti/Zep`、`Honcho` 这些系统更早占据“长期记忆”讨论中心。

公开材料支持这个校正：

- `Voyager` 的 `2023` 论文已经明确给出 **“ever-growing skill library of executable code”**，说明程序性 / skill-based memory 很早就成立。
- `Letta` 的 naming history 也显示 `memgpt_v2_agent (2024)` 已带有 **file tools** 与 **unified recall**，说明“文件/工具化记忆”并非后发明。
- 但从公开讨论中心、产品化叙事和 benchmark 驱动看，`vector/graph-like` 仍然是更早成为主流框架的一侧。

因此，本报告最终采用的不是“严格线性替代史”，而是：

> **`vector-like` 先成为主流讨论与产品化主线；`filesystem-like / procedural` 早期并行存在，但在 coding-agent 与 context-engineering 工程阶段更晚被系统性凸显。**

### 0.3 分类规则与证据等级

#### 分类规则

同一系统可能同时有文件层、向量层和图层。本报告按 **主导接口** 归类：

- 主导接口是 `API / SDK / shared memory pool / vector retrieval / graph retrieval / managed service`：归为 `vector-like`
- 主导接口是 `Markdown / 文件树 / URI / skill file / 版本对象`：归为 `filesystem-like`

#### 证据等级

| 等级 | 含义 |
|------|------|
| A | 官方仓库 / 官方文档 / 原始论文相互印证，关键机制可核验 |
| B | 官方仓库或官方文档较清晰，但效果主要依赖项目自报 |
| C | 官方入口存在，但实现细节或评测链条不够稳 |
| X | 本轮未拿到足够稳定的一手技术材料，只作弱引用 |

### 0.4 如何正确理解“SOTA”

“SOTA”在 agent memory 里不能被理解成一个总冠军数字。更合理的读法是：

| 信号类型 | 能说明什么 | 不能说明什么 |
|----------|------------|-------------|
| 同行评审论文 / 官方 benchmark | 方法在某个测试集上有效 | 一定最适合生产，也不一定可迁移到别的场景 |
| 官方 research / benchmark 页面 | 当前公开前沿和产品方向 | 独立复核、可重复性、跨系统公平性 |
| README / Docs 工程数据 | 架构形态、接入方式、成本和产品成熟度 | 通用记忆质量冠军 |

因此，后文不会写“唯一 SOTA”，而会写：

- **哪类问题已经被较好解决**
- **哪类切片上谁更强**
- **哪些还是 vendor self-report**
- **还有哪些空间**

### 0.5 七个高层结论

1. **行业主流最先强化的是 `vector-like`：先解决跨会话 recall、上下文压缩和共享语义平面。**
2. **`filesystem-like / procedural` 并非后发明路线，而是早期就并行存在；只是它在 coding-agent 与 workspace memory 中更晚成为显性主角。**
3. **`vector-like` 的核心价值，不是“多存 embedding”，而是构建共享语义平面、关系平面和服务平面。**
4. **`filesystem-like` 的核心价值，不是“回到纯文件”，而是把文件真相层、skill 文件和版本治理重新提升为主角。**
5. **当前已经被证明能解决的问题，主要是跨会话 recall、按需压缩上下文成本、以及一定程度的多 agent 状态共享。**
6. **当前还没有成为行业默认能力的问题，主要是程序性记忆治理、记忆回滚/审计、以及安全遗忘与知识更新。**
7. **`CortexMem` 最合理的方向不是二选一，而是“北向吸收 vector/graph-like 的共享语义平面，南向落到 filesystem-like 的文件真相层和治理层”的混合架构。**

---

## 1. 解决了哪些关键问题，当前解决到什么程度，业界 SOTA 是什么，还有哪些空间

### 1.1 总表

| 关键问题 | 当前解决程度 | 当前公开强信号 / SOTA 切片（截至 2026-04-16） | 主要代表 | 仍有空间 |
|----------|-------------|-----------------------------------------------|---------|---------|
| **跨会话失忆，记忆不可读** | 事实 recall 已较成熟；“可读可改”仍主要依赖 filesystem-like 补强 | 长对话 recall 的公开高分前沿已进入 vendor self-report 阶段，例如 `Hindsight` 官方页给出 `94.6% LongMemEvalS / 92.0% LoCoMo10`，`Mem0` 官方研究页给出 `92.0% LongMemEval`，`Honcho` 官方 blog 给出 `90.4% LongMem S / 89.9% LoCoMo`；但“人能读懂、纠正、迁移”的强信号仍主要来自 `memsearch`、`Acontext`、`OpenViking` | Hindsight, Mem0, Honcho, memsearch, Acontext, OpenViking | 时间边界、来源溯源、冲突处理、人类纠错与跨系统迁移一致性 |
| **有限上下文窗口中的注意力质量与 token 成本** | 工程收益已经很明确 | `Mem0` 官方研究页报告相对 full-context 的 `91%` 延迟下降与 `90%` token 节省；`OpenViking` README 报告相对 OpenClaw 的 `83%-91%` 输入 token 降低；`BEAM` 等新 benchmark 开始逼迫系统在 1M-10M 级历史上工作 | Mem0, OpenViking, Hindsight, Honcho, Graphiti | 缺统一的成本-质量-延迟联合基准，很多结果仍不便横向公平比较 |
| **多 agent 协作时没有共享脑** | 架构需求明确，工程样本已出现，但没有统一 benchmark | 这一维没有公认分数冠军；更强的是架构信号：`mem9` 的中心化 memory pool、`eion` 的 shared knowledge graph、`ContextLoom` 的 Redis-first shared brain、`UltraContext` 的 context plane、`Honcho` 的 entity-aware shared state | mem9, eion, ContextLoom, UltraContext, Honcho | 权限边界、并发冲突、命名空间、事务语义、共享一致性仍未标准化 |
| **高价值长期资产：技能 / 策略 / SOP** | 已被证明可行，但远未成为行业默认 | `Voyager` 用 executable skill library 证明程序性记忆有效；`Acontext` 把 “skill is memory” 做成产品接口；但主流 memory 系统仍偏向“记事实”而不是“记做法” | Voyager, Acontext | 技能验证、失效检测、版本升级、与语义记忆联动仍弱 |
| **记忆治理 / 回滚 / 审计** | 仍是行业短板，只有少数系统做成一等能力 | 这条线没有 benchmark 型 SOTA，**架构 SOTA** 更接近 `Memoria`：snapshot / branch / merge / rollback / quarantine / audit trail | Memoria | 需要从“少数系统特性”变成“行业默认能力” |
| **记忆遗忘 / 过期 / 知识更新** | 最弱的一环 | `Graphiti/Zep` 在 temporal validity 和 fact invalidation 上最有代表性；`LongMemEval` 已把 knowledge update / abstention 纳入 benchmark；但“安全遗忘、置信度衰减、策略淘汰”仍基本缺位 | Graphiti/Zep, TiMem, LongMemEval | 缺安全遗忘策略、衰减函数、过期治理和低置信隔离机制 |

### 1.2 第一阶段：主流讨论与产品化先集中在 `vector/graph-like`

从公开主线看，行业最先大规模解决的是三件事：

1. **跨会话 recall**
2. **上下文压缩与 selective retrieval**
3. **共享 memory plane**

这类问题天然更容易被定义成：

- semantic storage
- memory extraction
- long-term retrieval
- entity / graph reasoning
- shared context service

所以在公开论文、产品叙事和 benchmark 视角里，最先强势占据中心的是 `MemGPT/Letta`、`mem0`、`Graphiti/Zep`、`Honcho`、`mem9` 这一类系统。

#### 1.2.1 先解决“跨会话失忆”

在 coding agent、research agent、assistant 场景里，早期最直接的问题是：

- 历史对话一结束就蒸发
- 上下文窗口装不下更长历史
- 模型对旧事实没有可持续访问路径

`MemGPT` 把这个问题框成“有限 context window 下的虚拟内存管理”；`Letta` 后续把它产品化为：

- core memory
- recall memory
- archival memory
- context hierarchy

再往后，`mem0`、`Honcho`、`Graphiti/Zep` 把这个思路做得更强：

- 不只存对话块
- 而是抽取事实、实体状态、图关系与时间信息

这一阶段的核心成果是：

> “跨会话能不能记住”这件事，已经不再是不可做，而是工程上可做、可 benchmark、可产品化。

#### 1.2.2 再解决“长上下文不等于好记忆”

纯粹扩大 context window 很快暴露出两个问题：

- token 成本高
- 注意力质量并不会线性变好

于是行业主流开始转向：

- consolidation
- selective retrieval
- hybrid search

这条线上，`mem0` 很典型：

- extraction
- update / reconciliation
- selective retrieve

`Graphiti/Zep` 和 `Honcho` 则继续往前推：

- temporal graph
- representation modeling
- entity-aware memory

所以在“有限上下文窗口里如何把最重要的内容送给模型”这个问题上，`vector/graph-like` 路线先形成了主流方法论。

#### 1.2.3 还先解决了“多 agent 需要共享脑”

一旦进入多 agent 协作，问题马上不再只是 recall，而是：

- agent A 的状态如何给 agent B 看见
- 多个 agent 怎么共享同一记忆池
- 如何跨终端、跨产品复用同一 memory layer

这恰好天然适合服务化 memory plane，因此 `vector/graph-like` 更早跑出来：

- `mem9`：central server + stateless plugin
- `eion`：shared memory storage + knowledge graph
- `ContextLoom`：Redis-first shared brain
- `UltraContext`：same context everywhere
- `Honcho`：workspace / peer / session / representation

所以，如果把行业问题按时间线看，最先被优先解的是：

> 记得住、找得到、能共享。

### 1.3 第二阶段：工程落地把 `filesystem-like / procedural` 诉求推到前台

当 `vector/graph-like` 路线把 recall、压缩和共享做出来之后，新的痛点也被放大了：

- 记忆虽然能召回，但**人看不懂**
- 记忆虽然能共享，但**写错了难纠正**
- 记忆虽然能抽取事实，但**很难沉淀成技能和 SOP**
- 记忆虽然能服务化，但**provenance、回滚、审计不够**

这也是为什么 `filesystem-like` 在工程侧迅速变重要。这里需要批判性校正的是：这并不是说 `filesystem-like` 到这时才出现，而是说它到这时才被系统性地提升为主问题。

#### 1.3.1 真正困扰用户的，不只是“不会检索”，而是“记忆不可读”

对 coding agent、research agent 来说，用户的真实抱怨通常不是：

- “为什么不是 top-k 更准一点”

而是：

- 上一轮有效讨论没稳定落盘
- 即使落盘，人类也看不懂、改不动
- 换个 agent / 终端 / 模型后上下文断掉

这正是 `memsearch`、`OpenViking`、`Acontext` 这类系统的起点。它们解决的是另一个层级的问题：

> 记忆不只是给模型看的，也必须给人看、给人改、给人迁移。

#### 1.3.2 高价值长期资产，往往不是事实，而是 skill / SOP

`vector/graph-like` 的主流强项是“记事实、记关系、记状态”；但工程里更高价值的长期资产常常是：

- 哪种 debug 步骤有效
- 哪个工具组合最稳
- 哪个 workflow 在当前环境能跑通
- 什么失败模式出现后该怎么修

这类东西天然更像：

- skill file
- SOP
- playbook
- executable code

于是 `Voyager` 和 `Acontext` 的价值就非常大：

- `Voyager` 证明了 executable skill library 可行
- `Acontext` 把 “skill is memory” 做成了产品接口

这一步不是 recall 的自然延伸，而是**记忆资产化方向的转向**。`Voyager (2023)` 也说明这条程序性记忆支线其实很早就存在，只是此前没有成为“主流长期记忆”讨论的中心。

#### 1.3.3 记忆进入生产后，治理问题压过了纯 recall 问题

当记忆真的持续写入生产系统，新的问题变成：

- 写错了怎么办
- 记忆互相矛盾怎么办
- 哪次 mutation 让 agent 行为变差了
- 不同实验分支怎么并存
- 低置信记忆要不要隔离

`Memoria` 的意义就在这里。它的吸引力不是“又一种检索”，而是：

- snapshot
- branch
- merge
- rollback
- contradiction detection
- quarantine
- audit trail

这说明 `filesystem-like` 不是回到“老式文件存储”，而是把**可治理性**做成 memory architecture 的核心属性。

### 1.4 尚未被行业默认解决的三件事

#### 1.4.1 程序性记忆治理还没成熟

虽然 `Voyager` 和 `Acontext` 已经证明方向成立，但行业还没默认解决：

- skill 自动验证
- skill 失效检测
- skill 版本升级
- skill 与 declarative memory 的联动

#### 1.4.2 记忆回滚 / 审计仍是短板

当前只有少数系统把这些做成一等能力：

- provenance
- rollback
- branch
- quarantine

多数系统仍停留在“写入 / 检索 / 更新”，还不是真正可治理。

#### 1.4.3 安全遗忘与知识更新仍然最弱

今天绝大多数 memory system 会：

- 写
- 找
- 做一定 consolidation

但不会很好地：

- 忘
- 降权
- 过期
- 归档
- 做时间冲突治理

这一点仍然是未来的核心分水岭。

---

## 2. 核心实现机制和原理

### 2.1 机制总表

| 机制 | 范式 | 核心原理 | 代表系统 | 价值 | 主要边界 |
|------|------|----------|---------|------|---------|
| **Consolidation / Reconciliation** | Vector/Graph-like | 从对话里提取 salient info，并做 ADD / UPDATE / DELETE / NOOP | mem0, mem9 | 避免只堆历史，让记忆自更新 | 成本高，受抽取质量影响 |
| **Hybrid Retrieval** | Vector/Graph-like | dense + keyword + metadata + graph traversal 组合检索 | mem0, mem9, Graphiti, Hindsight | 平衡语义召回与精确关系 | 链路更复杂，调参更重 |
| **Representation Modeling** | Vector/Graph-like | 围绕实体形成持续状态表示，而不只是 chunk recall | Honcho | 更适合长期个体/实体理解 | 黑箱程度更高 |
| **Temporal Graph** | Vector/Graph-like | 关系携带时间边界与有效窗，支持 point-in-time 查询 | Graphiti/Zep | 更贴近真实业务状态演化 | 图维护和查询复杂 |
| **Shared Memory Plane** | Vector/Graph-like | 以中心化服务 / pool / namespace 供多 agent 共享 | mem9, ContextLoom, eion, UltraContext | 多 agent 协作和跨端同步更强 | ACL、并发、事务仍难 |
| **文件真相层** | Filesystem-like | 记忆对象以 Markdown / skill / 版本对象落盘，文件为 source of truth | memsearch, Acontext, Memoria | 人类可读、可审阅、可迁移 | 服务化共享不如 northbound plane 自然 |
| **Shadow Index** | Filesystem-like | 向量 / FTS 从文件真相层重建，负责加速而不负责真相 | memsearch | 快速检索且不牺牲可读性 | 需要同步与 rebuild 策略 |
| **分层加载（L0-L2）** | Filesystem-like | 先给目录/摘要，再按需递归披露细节 | OpenViking, memsearch, Acontext | 降 token、提注意力质量、提可解释性 | 要求 agent 有更强 tool-use 能力 |
| **程序性记忆 / Skill 文件** | Filesystem-like | 把经验沉淀为 SOP、playbook、可执行 skill | Acontext, Voyager | 高价值经验可复用、可验证、可组合 | 需要 skill schema 与失效治理 |
| **Append-only + Layered Summary** | Filesystem-like | 原始 episode 不丢失，上层摘要可压缩可展开 | lossless-claw, OpenViking | 可追溯、可压缩、可恢复 | 主要解决上下文管理，不等于完整 memory 栈 |
| **Branch / Rollback / Quarantine** | 治理层 | 把记忆 mutation 纳入版本和安全治理 | Memoria | 可审计、可修复、可实验 | 基础设施和流程成本更高 |

### 2.2 Vector-like 范式：记忆首先是共享语义 / 关系平面

#### 2.2.1 为什么它先成为行业主线

这一路线最早成为**主流叙事与产品化中心**，不是偶然，而是因为它最自然地回答了第一阶段的问题：

- 怎么突破 context limit
- 怎么做跨会话 recall
- 怎么让 memory 变成共享基础设施

也因此，这一范式的主导接口天然是：

- SDK
- API
- memory server
- vector / graph retrieval
- shared context plane

#### 2.2.2 Consolidation：先把原始对话抽成更高浓度的记忆单位

`vector-like` 路线的主流做法，不是保存全部原话，而是保存**抽取后的记忆单位**。

典型流程是：

1. **Extraction**
   从最近消息、滚动摘要、上下文中提取候选事实 / 实体 / 关系
2. **Update / Reconciliation**
   将新候选与已有记忆比较，决定：
   - `ADD`
   - `UPDATE`
   - `DELETE`
   - `NOOP`

`mem0`、`mem9` 都属于这一类。

这一机制的价值在于：

- 避免重复存原文
- 让记忆可演化
- 让“更新”成为一等能力

#### 2.2.3 Hybrid Retrieval：纯向量检索已经不够

当前较成熟的系统，几乎都在走向：

- dense vector
- keyword / BM25
- metadata / entity filters
- graph traversal
- reranking

原因很直接：

- 纯语义检索对精确关系和否定信息不稳
- 纯关键词对近义表达和抽象偏好不稳
- 没有结构化关系时，多会话与跨实体推理很弱

因此这条路线真正成熟的标志，不是“更大的 embedding 池”，而是：

> 多信号检索 + 更好的路由与重排。

#### 2.2.4 Representation Modeling 与 Temporal Graph：从“找句子”走向“建状态”

这是 `vector/graph-like` 与传统 RAG 最大的分野。

`Honcho` 的核心不是更多 chunks，而是：

- entities
- sessions
- representations
- background reasoning / dreaming

`Graphiti/Zep` 的核心则是：

- temporal knowledge graph
- `valid_at / invalid_at`
- point-in-time reasoning
- source provenance

这说明长期记忆的核心问题，已经从“找一条旧文本”转向：

- 某个实体当前是什么状态
- 这个状态是如何变化过来的
- 某个旧事实是已失效，还是仍应保留为历史事实

#### 2.2.5 Shared Memory Plane：多 agent 协作天然更适合这一层

`vector/graph-like` 在多 agent 场景更强，核心原因不是“检索更快”，而是它更容易长成一个：

- northbound API
- shared pool
- multi-tenant memory service
- context / state plane

典型代表：

- `mem9`：central server + stateless plugin
- `eion`：shared memory storage + knowledge graph + guest access
- `ContextLoom`：Redis-first shared brain
- `UltraContext`：history / fork / clone / same context everywhere

#### 2.2.6 这一路线的优势与边界

**优势**

- 更早解决了 recall、压缩与共享
- 更适合多 agent、多端同步、服务化接入
- 更适合实体关系、时序和长期状态建模

**边界**

- 可读性和可手动纠错较弱
- 容易黑箱化
- provenance / rollback / 审计若不足，长期风险很高

### 2.3 Filesystem-like 范式：记忆首先是文件真相层和技能对象

#### 2.3.1 为什么它在工程阶段变得关键

当 memory 真正进入 coding、research、long-running workflow 这些场景后，大家逐渐意识到：

> 记忆不只是要给模型检索，还必须能被人类审阅、修正、迁移和治理。

因此 `filesystem-like` 的主导接口是：

- Markdown
- 文件树
- URI
- skill file
- 版本对象

#### 2.3.2 文件真相层 + Shadow Index：文件为真相，向量为加速

`filesystem-like` 路线最关键的原则之一是：

> 文件作为真相，向量作为加速。

这意味着：

- 真正被审阅、修正的是文件本身
- 向量库或 FTS 只是可重建的检索缓存
- 检索层坏了，真相层仍在

`memsearch` 是这一思路最清晰的样本：

- Markdown 是 source of truth
- Milvus 是 shadow index
- recall 链路是 `search -> expand -> transcript`

#### 2.3.3 分层加载（L0-L2）：按需递归披露，而不是一次塞满【可落地到传统文件系统上层，也可落地到传统文件系统内部（改造文件系统，最大优势是业务无感，难点是如何透传语义）】

`filesystem-like` 在上下文管理上的核心创新，不是“存成文件”，而是**层级披露**：

- `L0`：核心摘要
- `L1`：目录 / 索引 / 结构化摘要
- `L2`：完整正文 / 完整 skill / 完整资源

这等于把 memory 做成一种“分页读取”：

- 先缩小空间
- 再按需下钻

`OpenViking`、`memsearch`、`Acontext` 都在说明同一件事：

> 稳定的 retrieval 往往不是一步命中，而是先给结构，再给细节。

#### 2.3.4 程序性记忆：skill file 比抽象摘要更接近高价值资产

`filesystem-like` 天然更适合把记忆沉淀成：

- skill
- playbook
- SOP
- workflow
- executable code

这比把所有经验都压成一段自然语言摘要更稳，因为它：

1. 可验证
2. 可组合
3. 可版本化

`Acontext` 和 `Voyager` 分别给出了产业和学术两类强样本。

#### 2.3.5 治理友好：branch / rollback / quarantine 更自然

当记忆是：

- 文件
- skill
- 版本对象
- append-only 轨迹

治理能力就更容易落地：

- diff
- branch
- rollback
- quarantine
- provenance

这也是 `Memoria` 的核心价值：它把治理语义直接做进了 memory architecture。

#### 2.3.6 这一路线的优势与边界

**优势**

- 人类可读、可改、可迁移
- skill / SOP / artifact 更容易沉淀
- 治理与版本化更自然
- 特别适合 coding / research / local-first 场景

**边界**

- 共享和服务化不如 northbound memory plane 顺手
- 多实体关系建模不如图结构强
- 多 agent 并发写入仍需要额外治理层

### 2.4 行业真实演进：`vector/graph-like` 先成为主流，但 `filesystem-like / procedural` 早有并行支线

这次改写最重要的结论就是这条演进线。

#### 阶段一：`2023-2025`，行业主线先围绕语义平面和上下文突破展开

公开主线里，最先被放大讨论的是：

- `MemGPT (2023)`：把长期记忆看成 virtual context management
- `Letta`：把这条路线产品化，并持续演进到 `MemGPT v2 (2024)`、`Letta v1 (2025)`
- `mem0`：把 extraction / update / selective retrieval 做成通用 memory layer
- `Graphiti/Zep`：把 temporal graph 和 hybrid graph retrieval 做成长期记忆结构
- `Honcho`：把 entity representation 和 peer-centric memory 做成主接口

这一阶段的行业关键词是：

- context hierarchy
- semantic retrieval
- consolidation
- graph / entity memory
- shared memory service

需要强调的是，这里说的是**主流讨论和产品化中心**，不是说其他路线尚不存在。

#### 阶段一的并行支线：`filesystem-like / procedural` 其实很早就已经出现

如果只看“最新版本”的线性叙事，会漏掉一个重要事实：文件化 / 程序性记忆并不是后来的补丁，而是很早就已经存在的并行路线。

公开材料中至少有两个强信号：

- `Voyager (2023)` 已经把长期能力沉淀成 **“ever-growing skill library of executable code”**
- `Letta` 的 legacy docs 显示 `memgpt_v2_agent (2024)` 已经包含 **sleep-time agents、file tools、unified recall**

这说明更准确的历史不是：

- 先完全只有 vector
- 后来才发明 filesystem

而是：

- `vector/graph-like` 更早成为主流外显框架
- `filesystem / procedural` 早就存在，但更晚才在工程实践中被系统性命名和放大

#### 阶段二：工程落地暴露出黑箱、技能缺位和治理缺位

随着这些系统真正进入生产或复杂 workflow，工程团队开始发现：

- 召回正确不等于记忆可用
- memory service 不等于 memory 可治理
- 抽取事实不等于沉淀 skill
- 共享状态不等于人类可审阅

这一阶段的用户痛点开始从“记不住”转向：

- 看不懂
- 改不动
- 迁不走
- 回不去

#### 阶段三：`filesystem-like` 成为工程回摆与补强方向

于是 `filesystem-like` 开始变重要：

- `memsearch`：把 Markdown source of truth + shadow index 做成 coding agent memory
- `Acontext`：把 “skill is memory” 做成明确接口
- `OpenViking`：把 context filesystem、L0/L1/L2 和 retrieval trajectory 做成主体验面
- `Memoria`：把 rollback / branch / quarantine / audit 做成一等能力
- `lossless-claw`：把 append-only raw messages + layered summaries 做成可恢复上下文管理

这不是一条“反向量”的路线，而是一条**对黑箱 memory architecture 的工程补强路线**。

#### 阶段四：未来稳定形态将是混合栈

行业最终不会停在二选一：

- `vector/graph-like` 负责 northbound shared memory plane
- `filesystem-like` 负责 southbound source of truth、skill surface 和治理友好性

更合理的稳定形态会是：

1. 原始事件层
2. 文件真相层
3. 语义 / 图检索层
4. 程序性记忆层
5. 治理 / 遗忘层

---

## 3. 面向的关键场景

### 3.1 场景总表

| 场景 | 更适合的主导范式 | 原因 | 代表系统 |
|------|------------------|------|---------|
| **全天候个性化助手（Proactive Assistants）** | Vector/graph-like 优先 | 需要跨设备同步、后台更新偏好、围绕人和关系持续建模 | mem0, Honcho, Graphiti/Zep, memU |
| **多agent协同系统（Planner / Executor / Reviewer）** | Vector/graph-like 优先 | 多个 agent 需要共享状态池、共享实体关系和中心化权限边界 | mem9, eion, ContextLoom, UltraContext |
| **高复杂度编程（Coding Agents）** | Filesystem-like 优先，必要时加 shadow index | 代码库本身就是文件系统；需要记录架构决策、版本依赖、调试经验；必须支持人工审核和记忆修正 | memsearch, OpenViking, Acontext, Memoria |
| **长程研究（Research Agents）** | Filesystem-like 优先 | 输出物本身是结构化文档；需要多轮整理、改写、引用和人工干预 | OpenViking, memsearch, lossless-claw |

### 3.2 为什么 `vector/graph-like` 更早适配 proactive assistant 与 multi-agent

这类场景的共同特征是：

- 多端同步
- 长期在线
- 高并发
- 多实体关系
- 中央化服务治理

所以它们天然更适合：

- shared memory pool
- entity representation
- temporal graph
- northbound API

这也是为什么 `mem0`、`Honcho`、`Graphiti/Zep`、`mem9`、`eion`、`ContextLoom` 更早在这些场景里显得顺手。

### 3.3 为什么 `filesystem-like` 更适配 coding 与 research

这类任务有两个共同点：

1. **任务对象本来就天然是文件和文档**
2. **人类工程师必须能看懂 agent 在记什么**

所以最关键的不是极致 recall 分数，而是：

- 记忆能不能被 review
- 技术决策能不能被纠正
- SOP 能不能沉淀成 skill
- 历史过程能不能被追溯

这也是为什么 `memsearch`、`Acontext`、`OpenViking`、`Memoria` 在这类场景更有说服力。

---

## 4. 对 CortexMem 的直接启示

### 4.1 总体架构判断：北向先吸收语义平面，落到文件真相层

这轮研究给 `CortexMem` 最直接的结论不是“该选 vector-like 还是 filesystem-like”，而是：

> `CortexMem` 应先吸收 `vector/graph-like` 在 shared memory plane、temporal/entity modeling 上的优点，再以 `filesystem-like` 作为文件真相层、skill surface 和治理基座。

可以把它理解为：

```
L4 治理 / 审计 / 回滚 / 遗忘
L3 程序性记忆 / Skill / SOP
L2 Shared Memory Plane / 语义索引 / 图关系
L1 文件真相层（Markdown / Resource / Skill Files）
L0 Append-only 原始事件与轨迹
```

### 4.2 六个优先建设方向

#### 4.2.1 Shared Memory Plane：先把多agent的共享脑做对
> 说明： `CortexMem` 面向 planner / executor / reviewer 这类多agent编排，或者面向跨终端、跨会话的长期助手，首先要建设的就不是某个单点检索技巧，而是一个真正可共享的 memory plane。这里的“共享”不是简单把所有记忆堆到同一数据库里，而是要明确 workspace、tenant、agent scope 这类命名空间边界，明确不同 agent 对哪些状态可读、可写、可继承，并为共享>状态池补上最基本的冲突处理和事务语义；否则表面上是“共享脑”，实际上只是把不同 agent 的局部认知、错误写入和脏状态混在一起。之所以把这件事放在最前，是因为 shared plane 是多agent系统成立的前提：如果共享层没有先做对，后面的检索增强、技能沉淀和治理机制都会在错误的状态基座上运行。

`CortexMem` 面向 planner / executor / reviewer 或跨终端助手需要先解决：

- workspace / tenant / agent scopes
- 读写权限
- 共享状态池
- 冲突和事务语义

否则所谓“共享脑”只会变成“共享污染”。

#### 4.2.2 Temporal / Entity Modeling：不只记事实，还要记状态如何变化
> 说明：`CortexMem` 不应只把长期记忆理解成一组可召回的事实片段，而应进一步把“谁、在什么时候、处于什么状态、与谁发生什么关系”作为核心建模对象，这就是 temporal / entity modeling 的
意义。落地上应吸收 `Graphiti/Zep` 和 `Honcho` 的优点：围绕实体维护持续状态表示，为事实和关系附带时间有效窗，记录关系如何演化，并保留足够的 source provenance，让系统不仅能
回答“记住了什么”，还能回答“这是何时成立的、是否仍然成立、为什么现在会这么判断”。之所以这一步重要，是因为长期 memory 最常见的失败不是完全找不到，而是把旧事实当成当前事实、
把历史关系错认成现状关系；没有时间和实体维度，记忆系统就只能做静态回忆，无法支撑真实世界里持续变化的用户、任务和环境。

应吸收 `Graphiti/Zep`、`Honcho` 这一侧的优点：

- 实体状态表示
- 时间有效窗
- 关系演化
- source provenance

否则长期记忆很容易把“旧事实”错当“当前事实”。

#### 4.2.3 文件真相层：让记忆可以被人类审阅、修正、迁移
> 说明：`CortexMem` 应明确保留一个 human-readable 的文件真相层，把 Markdown、resource files、skill files 和人类可读索引作为 source of truth，而不是把唯一真相层放进向量库、图数据>库或中心服务内部。这里的关键不是“偏爱文件”这种形式偏好，而是要确保记忆对象能够被人审阅、纠错、迁移、版本化和跨工具复用：工程师应能直接打开一条长期记忆、一个 skill 文件或>一份任务总结，知道 agent 记住了什么、哪里有误、该如何修。向量与图在这个架构里的职责应当是检索和路由加速，而不是取代真相层本身；否则一旦记忆被抽取错、索引错或服务状态污染>，人就失去了干预入口。之所以这个方向重要，是因为 coding 和 research 场景里的长期记忆不是纯机器内部状态，而是必须被人和 agent 共同维护的工程资产。

`CortexMem` 不应把唯一真相层放在向量库或中心服务里，而应保留：

- Markdown / resource files
- skill files
- human-readable indexes

向量与图应服务于检索和路由，而不是取代真相层。

#### 4.2.4 分层递归检索 + Shadow Index：先缩小空间，再向下钻
> 说明：`CortexMem` 的检索逻辑不应默认把完整记忆全文一次性塞给模型，而应采用“先缩小空间，再向下钻”的分页式策略：先返回目录、摘要和候选路径，再给出命中文件与命中原因，只有在模型确
认需要细节时才继续读取正文、原始轨迹或完整 skill。这要求系统同时具备一个可读的文件层和一个 shadow index / hybrid retrieval 层，后者的职责不是充当真相，而是帮助快速缩小检>索空间、提供高质量候选并压低 token 成本。之所以这种分层递归检索比“一次性 top-k 回填全文”更重要，是因为长期 memory 的核心瓶颈早已不是“有没有内容”，而是“如何让模型在有限上>下文里集中注意力”；如果没有层次化路由，长上下文只会把记忆系统重新拖回高成本、低注意力质量的老路。

`CortexMem` 不应该默认把完整记忆全文塞给模型，而应支持：

- 先给目录和摘要
- 再给命中文件路径和原因
- 仅在需要时读取正文

shadow index / hybrid retrieval 的职责是：

- 缩小检索空间
- 提供候选
- 降 token 成本

#### 4.2.5 程序性记忆治理：把成功做法沉淀成 skill，而不是只记事实
> 说明：`CortexMem` 不能只把长期记忆理解为“用户说过什么”或“系统观察到什么”，还要把真正高复利的做法沉淀成程序性记忆，例如调试步骤、工具组合、环境 workaround、失败模式与修复 SOP。>更稳妥的实现方式不是把这些经验压成抽象总结，而是把它们单独建模成 skill、playbook、SOP 之类可维护对象，并围绕它们建立自动 distill、版本化、失效检测和人工 review 的治理链路
。这样做的原因在于，很多对 agent 最有价值的长期资产并不是 declarative fact，而是“下次遇到类似问题应该怎么做”的操作性知识；如果系统只能记住事实，却不能稳定复用做法，那么每
次复杂任务仍然要从头推理，长期记忆就很难产生真正的能力复利。

高复利价值的长期资产往往是：

- 调试步骤
- 工具组合
- 环境 workaround
- 失败模式与修复 SOP

`CortexMem` 应把这些对象单独建模成：

- skill
- playbook
- SOP

并支持：

- 自动 distill
- 版本化
- 失效检测
- 人工 review

#### 4.2.6 回滚 / 审计 / 遗忘：像代码一样治理记忆

> 说明：果 `CortexMem` 要进入生产，记忆就不能只是“会写、会找、会更新”，而必须像代码和数据一样可治理、可追溯、可回退。具体来说，它需要内建 snapshot、branch、rollback、provenance、low-confidence quarantine 等能力，用来回答“这条记忆是谁写入的、什么时候写入的、是否可信、坏行为从哪次 mutation 开始出现”；同时还要把遗忘做成一等策略，引入时间衰减、访问
频次衰减和过期归档，让系统能够安全地压缩、淘汰、隔离和忘掉不再可靠的内容。之所以这一方向必须单独提出，是因为 memory system 一旦长期运行，真正危险的往往不是漏记，而是写错>、污染、投毒和过时信息持续影响后续行为；一个只会积累而不会回滚、审计和遗忘的系统，本质上仍然是不完整的。

`CortexMem` 若想进入生产，必须内建：

- snapshot
- branch
- rollback
- provenance
- low-confidence quarantine
- 时间衰减
- 访问频次衰减
- 过期归档

成熟的 memory system，不是无限堆积，而是能**安全地压缩、淘汰、归档和忘记**。

---

## 5. 最终判断

1. **从业界事实看，`vector/graph-like` 是更早成为主流叙事和产品化主线的一侧。**
2. **它先解决了三件事：跨会话 recall、上下文压缩与 selective retrieval、以及共享 memory plane。**
3. **但更准确的历史不是严格线性替代史，因为 `filesystem-like / procedural` 从 2023 起就已有并行支线。**
4. **`filesystem-like` 后来变得关键，是因为工程落地要求记忆必须可读、可改、可迁移、可治理，并能沉淀 skill / SOP。**
5. **对 `CortexMem` 来说，最有价值的不是押注单一路线，而是做“北向 shared memory plane + 文件真相层 + 程序性记忆层 + 治理/遗忘层”的混合栈。**

---

## 附录 A：Benchmark / SOTA 的正确读法（截至 2026-04-16）

| 切片 | 更该看什么 | 当前公开强信号 | 如何使用 |
|------|-----------|---------------|---------|
| **标准长对话 recall** | `LongMemEval / LoCoMo` | `Hindsight` 官方 benchmark 页给出 `94.6% LongMemEvalS / 92.0% LoCoMo10`；`Mem0` 官方 research-2 页给出 `92.0% LongMemEval`；`Honcho` 官方 blog 给出 `90.4% LongMem S / 89.9% LoCoMo` | 可判断公开 recall 前沿，但多为厂商自报，不宜直接当统一总榜 |
| **超长历史真正需要 memory 架构的切片** | `BEAM 1M / 10M` | `Hindsight` 官方 blog 报告 `64.1% BEAM 10M`；`Mem0` 官方页展示 `45.0% BEAM 10M`；`Honcho` 官方 blog 报告 `0.406 BEAM 10M` | 更接近“context stuffing 已经失效”的 frontier，但仍需注意评测配置差异 |
| **多 agent 共享脑** | 架构能力 | `mem9`、`eion`、`ContextLoom`、`UltraContext` 提供强架构信号，但无统一 benchmark | 这是“缺 benchmark 但工程需求真实”的典型领域 |
| **时间变化与知识更新** | `LongMemEval` 的 knowledge update、temporal reasoning；`Graphiti/Zep` 的 temporal graph | `Graphiti/Zep` 明确支持 validity / invalidation / historical context | 这里更应看架构是否真建模时间，而不是只看总分 |
| **可读性 / 可治理性** | 文件真相层、trace、rollback、audit | `memsearch`、`Acontext`、`OpenViking`、`Memoria` | 这条线目前更该看机制和可操作性，而不是分数 |

### 附录 A 的核心结论

- `LoCoMo / LongMemEval` 仍有价值，但在更大 context window 时代，已经不够单独代表“真实 memory frontier”。
- `BEAM 10M` 更能测试“无法靠塞上下文取巧”的能力，因此更接近真正的长期 memory frontier。
- 但即便如此，agent memory 也不能只看 benchmark；生产上同样重要的是：
  - 可读
  - 可调试
  - 可治理
  - 可共享
  - 可遗忘

## 附录 B：本轮补充核验的一手来源

- `MemGPT` 原始论文：<https://arxiv.org/abs/2310.08560>
- `Letta` Agent Architecture Naming History：<https://docs.letta.com/guides/legacy/naming_history>
- `Letta` Legacy Agent Architectures：<https://docs.letta.com/guides/legacy/architectures_overview>
- `Letta` Agent memory & architecture：<https://docs.letta.com/guides/agents/architectures/memgpt>
- `Voyager` 原始论文：<https://arxiv.org/abs/2305.16291>
- `Mem0` 官方 research page：<https://mem0.ai/research>
- `Mem0` 官方 research-2 page：<https://mem0.ai/research-2>
- `Honcho` 官方 benchmark blog（`2025-12-19`）：<https://blog.plasticlabs.ai/research/Benchmarking-Honcho>
- `Hindsight` 官方 benchmark 页：<https://benchmarks.hindsight.vectorize.io/>
- `Hindsight` 官方 BEAM 文章（`2026-04-02`）：<https://hindsight.vectorize.io/blog/2026/04/02/beam-sota>
- `Graphiti/Zep` 官方文档：<https://help.getzep.com/graphiti/graphiti/overview>
- `memsearch` 官方 GitHub：<https://github.com/zilliztech/memsearch>
- `OpenViking` 官方 GitHub：<https://github.com/volcengine/OpenViking>
- `Acontext` 官方 GitHub：<https://github.com/memodb-io/Acontext>
- `Memoria` 官方 GitHub：<https://github.com/matrixorigin/Memoria>

如需进一步追溯各系统的仓库、论文和细节材料，可继续参考同目录下的 `sources.md` 与 `evidence-matrix.md`。
