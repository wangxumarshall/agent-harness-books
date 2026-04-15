# Agent Memory System 深度洞察研究报告

> **作者**：汪旭 & Claude Code
>  - 基于 **28+ 个产业界系统** + **36 篇核心学术论文/技术报告** 的系统性调研
>  - **2026 Q2 批判性验证**：对全部关键系统进行 WebSearch + arXiv 原文 + GitHub 源码交叉验证
>  - 🆕 **Token效率四维评估**：基于 Mem0 ECAI 2025 (arXiv:2504.19413)、EverMemOS、SwiftMem (arXiv:2601.08160)、ENGRAM、AMB等最新研究
>  - 🆕 **重大学术伦理发现**：EverMemOS 不可复现事件（GitHub #73：独立复现仅 38.38% vs 论文声称 93.05%）
>  - 🆕 **MemMachine** (arXiv:2604.04853) 以 91.69% LoCoMo 成为新领跑者之一
>  - 研究框架：C.A.P.E（Architecture & Paradigm / Cognition & Evolution / Production & Engineering / Business & Ecosystem）
>  - 数据可信度标注：★=独立验证 ★☆=论文自报 ☆=项目自报无独立验证 ☆☆=独立复现失败/严重存疑 ⚠️=部分存在/待确认

---

## 第1章：产业界 Agent Memory System 深度洞察

### 1.1 总览：技术分类图谱

当前 Agent Memory 领域呈现**跨范式融合**趋势。2026 Q1-Q2 全网检索发现：

```
                         ┌─────────────────────────────┐ 
                         │   模型原生记忆 (Model-Native) │ 
                         │   Memorizing Transformers    │ 
                         │   MemoryLLM / STEM (ICLR)   │ 
                         └──────────┬──────────────────┘ 
                                    │
     ┌──────────────────────────────┼──────────────────────────────┐
     │                              │                              │
┌────▼────────────────┐ ┌──────────▼──────────────────┐ ┌─────────▼─────────────────┐
│  LLM决策记忆         │ │   分层记忆管理               │ │  外部记忆增强            │
│  (LLM-Decided Mem)   │ │  (Layered Memory Mgmt)     │ │  (External Memory Aug)   │
│                      │ │                            │ │                          │
│  mem0: LLM决策机    │ │  Letta: 主动上下文外部化    │ │  OpenViking: viking://  │
│  mem9: 记忆调和     │ │  MemOS: 统一API调度        │ │  memsearch: Markdown    │
│  Hermes: 技能生成    │ │  EverMemOS: 生物启发调度   │ │  memU: 文件系统+主动    │
└─────────────────────┘ └─────────────────────────────┘ └───────────────────────────┘
                                    │
     ┌──────────────────────────────┼──────────────────────────────┐
     │                              │                              │
┌────▼────────────────┐ ┌──────────▼──────────────────┐ ┌─────────▼─────────────────┐
│  版本控制/安全记忆    │ │   多Agent共享记忆           │ │  上下文基础设施           │
│  (Version-Controlled)│ │  (Multi-Agent Shared)     │ │  (Context Infrastructure)│
│                      │ │                            │ │                          │
│  Memoria: Git for   │ │  ContextLoom: Redis总线   │ │  langmem: LangGraph存储 │
│  Memory (CoW)      │ │  eion: PG+Neo4j统一API    │ │  claude-mem: 生命周期钩 │
└─────────────────────┘ └────────────────────────────┘ └────────────────────────────┘

                    ┌──────────────────────────────────────────┐
                    │  🆕 2026 新范式：跨范式融合体             │
                    │                                          │
                    │  MemBrain: Agent原生+子Agent协调         │
                    │  MemMachine: Ground-Truth+自适应检索     │
                    │  TiMem: CLS时序分层+复杂度感知召回       │
                    │  LiCoMemory: 轻量认知图谱                │
                    └──────────────────────────────────────────┘
```

> ⭐ = 2026 Q1-Q2 全网检索新增 / 重大更新的系统

**核心发现**：经源码级验证，原"OS内存页置换"分类是**营销隐喻而非技术实现**。修正后的分类反映实际架构。

**🆕 2026 Q2 基准竞赛全景 — 数据可信度分级**：

| 排名 | 系统 | LoCoMo | LongMemEval | 数据可信度 | 核心技术 |
|------|------|--------|-------------|-----------|---------|
| 1 | **MemMachine v0.2** | 91.69% | 93.0% | ★☆ 论文 (arXiv:2604.04853) | Ground-Truth保持+自适应检索 |
| ~~1~~ | ~~EverMemOS~~ | **声称** 93.05% ⚠️ | **声称** 83.00% ⚠️ | **☆☆ 独立复现仅38.38%** (GitHub #73) | engram生命周期 |
| 2 | **HyperMem** | 92.73% | - | ☆ 论文 (arXiv:2604.08256, 同EverMind) | 超图n-元关系 |
| 3 | **Zep/Graphiti** | 85.22% | 63.80% | ★☆ EverMind独立评估 | 时序知识图谱 |
| 4 | **MIRIX** | 85.4% | - | ★☆ 论文 | 6类记忆+Active Retrieval |
| 5 | **Letta** | ~83.2% | - | ☆ 自报 | LLM-as-OS |
| 6 | **TiMem** | 75.30% | 76.88% | ★☆ 论文 (arXiv:2601.02845) | CLS时序5层TMT |
| 7 | **ENGRAM** | 77.55% | +15pts vs Full | ★☆ OpenReview | typed extraction |
| 8 | **MemOS** | 75.80% (README) | 77.80% | ★☆ 自报 | 图+向量+调度器 |
| 9 | **SwiftMem** | 70.4% | - | ★☆ 论文 (arXiv:2601.08160) | multi-token聚合 |
| 10 | **Mem0** | 66.9% (论文) / ~49% (独立) | 66.40% | ★☆ 论文+独立评估 | 向量+LLM决策 |

> **⚠️ 重大可信度警示**：EverMemOS 论文声称 93.05%，但独立用户 @wangyu-ustc 在 GitHub issue #73 报告仅复现出 **38.38%**（差距 -54.62pp），该 issue 至今 open。HyperMem (92.73%) 为同一团队后续论文，同样缺乏独立验证。

**🆕 2026 Q2 新系统速览**：

| 系统 | 类型 | 关键事实 | arXiv | 可信度 |
|------|------|---------|-------|--------|
| **Memoria** | 版本控制安全 | GTC 2026; Rust+MatrixOne CoW; ~193★ | - | ★ InfoQ验证 |
| **MemBrain** | Agent原生 | ~269★; v1.5; 子Agent协调 | 无正式论文 | ☆ 仅GitHub |
| **MemMachine** | Ground-Truth | LoCoMo 91.69%; 80% token减少 | 2604.04853 | ★☆ 论文 |
| **TiMem** | 时序分层 | 中科院; CLS理论; 52.2% token节省 | 2601.02845 | ★☆ 论文 |
| **HyperMem** | 超图 | 同EverMind团队; 92.73% LoCoMo | 2604.08256 | ☆ 同团队 |
| **ENGRAM** | 架构级 | ~99% token; 77.55% LoCoMo | OpenReview | ★☆ |
| **SwiftMem** | KV感知 | 11ms搜索; 70.4% LoCoMo | 2601.08160 | ★☆ |
| **0GMem** | 结构化记忆 | 88.67% (10-conv); BM25+语义 | - | ☆ |
| **ICLR STEM** | 查表式 | CMU+Meta AI; FFN替换 | 2601.10639 | ★☆ |
| **LiCoMemory** | 轻量图谱 | HKUST+华为+WeBank; CogniGraph | 2511.01448 | ★☆ |
| **OmniMem** | AI自主优化 | UNC; F1 0.117→0.598 (+411%，但绝对值低) | 2604.01007 | ★☆ |
| **DeepSeek Engram** | 条件记忆模块 | ⚠️ 仅媒体报道; arXiv未找到 | 待确认 | ⚠️ |

---

### 1.2 C.A.P.E 框架深度对比

#### 1.2.1 架构与底层范式层

##### 技术分类

| 分类 | 代表系统 | 核心特征 | 适用场景 |
|------|---------|---------|---------|
| **模型记忆** | 四大子范式(详见2.2.2) | 修改Transformer或参数 | 长文档理解、知识注入 |
| **LLM决策记忆** | mem0, mem9, Hermes Agent | LLM作为"记忆决策机" | 通用Agent |
| **分层记忆管理** | Letta, MemOS, EverMemOS | 多层架构+软件调度器 | 长时程推理 |
| **外部记忆增强** | OpenViking, memsearch, memU | 人类可读格式为核心 | 编码Agent |
| **版本控制/安全记忆** | Memoria | CoW版本控制+快照/回滚 | 安全敏感场景 |
| **程序性/技能记忆** | Acontext, Voyager | 可执行代码/技能作为记忆 | 技能密集型Agent |
| **多Agent共享记忆** | ContextLoom, eion, honcho | 共享记忆总线+隔离机制 | 多Agent协作 |
| **上下文基础设施** | langmem, claude-mem | 作为框架/平台的基础组件 | 快速集成 |

##### 存储范式

| 存储范式 | 代表系统 | 优势 | 劣势 |
|---------|---------|------|------|
| **扁平向量** | mem0, mem9 | 语义检索强 | 无结构化关系 |
| **图数据库** | MemOS, Zep, eion | 结构化推理 | 部署复杂 |
| **超图** | EverMemOS/HyperMem | n-元关系表达 | 计算开销大 |
| **文件目录树** | OpenViking, memsearch | 人类可读+git版本 | 语义检索需额外索引 |
| **CoW数据库** | Memoria | 零拷贝快照+分支隔离 | 依赖MatrixOne |
| **模型参数** | MemoryLLM | 零检索延迟 | 容量有限 |
| **KV Cache** | Memorizing Transformers | 注意力级融合 | 存储开销大 |

##### 系统定位

| 定位 | 代表系统 | 集成成本 | 灵活性 | 独立性 |
|------|---------|---------|--------|--------|
| **中间件SDK** | mem0, langmem | 极低 | 高 | 低 |
| **中间件插件** | claude-mem, mem9 | 低 | 中 | 低 |
| **独立MaaS** | eion, honcho | 中 | 中 | 高 |
| **Agent平台内置** | Letta, Hermes Agent | 高 | 低 | 高 |
| **Memory OS** | MemOS, EverMemOS | 高 | 中 | 极高 |
| **安全记忆层** | Memoria | 中 | 中 | 高 |
| **模型底座** | MemoryLLM | 极高 | 极低 | 极高 |

##### 检索机制

| 检索策略 | 代表 | 精确度 | 语义泛化 | 延迟 |
|---------|------|--------|---------|------|
| **纯向量语义** | mem0, mem9 | 中 | 高 | 低 |
| **混合检索(BM25+语义)** | memsearch, 0GMem | 高 | 高 | 中 |
| **目录浏览** | OpenViking | 极高 | 低 | 极低 |
| **图遍历** | MemOS, Zep | 高 | 中 | 高 |
| **LLM自驱检索** | Letta | 依赖LLM | 依赖LLM | 高 |

---

#### 1.2.2 认知与演进能力层

##### 自我进化光谱

```
死记忆 ◄──────────────────────────────► 活记忆

L0: lossless-claw, ContextLoom, ultraContext
L1: mem0, mem9, memsearch, langmem, claude-mem, Medicina
L2: Letta, OpenViking, memU, xiaoclaw-memory
L3: MemOS, EverMemOS, Hermes Agent, honcho
L4: MemBrain (子Agent协调)
```

| 进化等级 | 特征 | 代表系统 |
|---------|------|---------|
| **L0 死记忆** | 只存不更新 | lossless-claw, ContextLoom |
| **L1 半活记忆** | 自动提取+去重 | mem0, memsearch, Medicina |
| **L2 活记忆(规则驱动)** | 反思+融合+有限遗忘 | Letta, OpenViking, memU |
| **L3 活记忆(自组织)** | 自主反思+调度器 | MemOS, EverMemOS |
| **L4 活记忆(Agent化)** | 记忆本身是Agent | MemBrain |

##### 遗忘机制

| 策略 | 代表 | 优势 | 劣势 |
|------|------|------|------|
| **无遗忘** | mem0, memsearch, Letta | 简单 | 记忆膨胀 |
| **重要性评分** | EverMemOS, MemOS | 智能 | 依赖LLM |
| **遗忘曲线** | MemoryBank | 心理学基础 | 需调参 |
| **版本回滚** | Medicina | 确定性恢复 | 需完整历史 |

##### 结构化推理

| 能力 | 代表 | 表达能力 |
|------|------|---------|
| **扁平** | mem0, mem9 | 事实列表 |
| **图结构** | MemOS, Zep | A→隶属于→B |
| **超图** | EverMemOS, HyperMem | n-元关系 (足球→运动→周末) |

---

#### 1.2.3 工程与生产力层

##### Token 效率四维评估

**维度一：Token 节省率**

| 系统 | 节省 | 机制 | 数据可信度 |
|------|------|------|-----------|
| ENGRAM | ~99% | typed extraction | ★☆ |
| Mem0 | ~90% | 事实级压缩 | ★☆ ECAI 2025 |
| MemMachine | ~80% | 短/长期分层 | ★☆ 论文 |
| OpenViking | 83-91% | L0/L1/L2分层 | ☆ |
| EverMemOS | ~85% | engram生命周期 | ☆☆ ⚠️ |
| TiMem | 52.2% | CLS分层 | ★☆ 论文 |

**维度二：准确率**

| 系统 | LoCoMo | LongMemEval | 数据可信度 |
|------|--------|-------------|-----------|
| Full-Context | 72.9% | - | ★ 独立 |
| MemMachine | 91.69% | 93.0% | ★☆ 论文 |
| EverMemOS | ~~93.05%~~ (声称) | ~~83.00%~~ | ☆☆ ⚠️ 复现38.38% |
| Zep | 85.22% | 63.80% | ★☆ 独立评估 |
| ENGRAM | 77.55% | +15pts | ★☆ OpenReview |
| TiMem | 75.30% | 76.88% | ★☆ 论文 |
| MemOS | 75.80%-80.76% | 77.80% | ★☆ |
| Mem0 | 66.9%(论文)/~49%(独立) | 66.40% | ★☆+★交叉验证 |

**维度三：时延**

| 系统 | p95搜索 | p95总响应 | 可信度 |
|------|--------|----------|--------|
| SwiftMem | ~15ms | ~1,289ms | ★☆ |
| Mem0 | 200ms | 1.40-1.63s | ★☆ |
| ENGRAM | 806ms | 1,819ms | ★☆ |
| Zep | 522ms | 3,255ms | ★☆ |
| MemOS | 1,983ms | 7,957ms | ★☆ |
| Full-Context | N/A | 17,120ms | ★ |

**维度四：用户体验**

| 系统 | GitHub★ | 活跃度 | 上手 | 可信度 |
|------|---------|--------|------|--------|
| Mem0 | ~52-53K | 14M+下载 | 极低 | ★ |
| Letta | ~21.8K | 176 releases | 高 | ★ |
| MemOS | ~8.3K | 中 | 中 | ★ |
| OpenViking | ~4.8K | 中 | 中 | ★ |
| EverMemOS | ~3.3K | 中 | 中 | ★ |
| MemBrain | ~269 | 低 | 未知 | ☆ |
| Memoria | ~193 | 低 | 中 | ★ InfoQ |

##### 可观测性

| 等级 | 代表 | 特征 |
|------|------|------|
| **黑箱** | mem0(自托管) | 无法查看 |
| **API可查** | Letta | API查看内容 |
| **可视化** | MemOS, MemBrain | 面板查看 |
| **人类可读** | memsearch, memU | Markdown直编 |
| **URI可寻址** | OpenViking | viking://协议 |
| **Git级版本** | Memoria | 快照/分支/回滚 |

##### 部署复杂度

| 复杂度 | 代表 | 依赖 |
|--------|------|------|
| 极低 | claude-mem, mem9 | npm/pip |
| 低 | Hermes Agent | Python+LLM |
| 中 | mem0(云), Letta, Memoria | 数据库+LLM |
| 中高 | OpenViking | VLM+Embedding |
| 高 | MemOS, EverMemOS | Neo4j/Redis/Milvus+LLM |

---

#### 1.2.4 业务与生态层

| 场景 | 最佳 | 原因 |
|------|------|------|
| C端陪伴 | honcho, MemoryBank | 用户建模+遗忘 |
| 编码Agent | memsearch, OpenViking, Medicina | 可读+版本+分层 |
| 安全敏感 | Memoria | 版本回滚+CoW |
| 快速集成 | mem0, langmem | 一行SDK |

##### 多Agent支持

| 级别 | 代表 | 机制 |
|------|------|------|
| 单Agent | claude-mem | 无共享 |
| 多Agent隔离 | Letta | 独立空间 |
| 跨Agent用户共享 | mem0 | user_id跨读 |
| 共享总线 | ContextLoom | Redis同步 |

##### 开源许可

| 许可 | 代表 | 商业友好 |
|------|------|---------|
| MIT | claude-mem, langmem, memsearch | ★★★★★ |
| Apache 2.0 | mem0, Letta, MemOS, EverMemOS, Medicina | ★★★★★ |
| AGPL-3.0 | OpenViking (repo) ⚠️ | ★★☆☆☆ |

> ⚠️ OpenViking 许可证矛盾：repo 标注 AGPL-3.0，官网声称 Apache 2.0。

---

### 1.3 主要局限与短板

#### 1.3.1 共性局限

| 局限 | 影响 | 严重度 |
|------|------|--------|
| 遗忘缺失 | 60%+ | 高 |
| 结构化推理弱 | 70%+ | 高 |
| 评估不可信 | 全部 | **极高** |
| 记忆投毒无防 | 几乎全部 | 高 |

#### 1.3.2 评估可信度危机（🆕 重大）

| 问题 | 严重度 | 说明 |
|------|--------|------|
| **EverMemOS复现失败** | ★★★★★ | GitHub #73: 38.38% vs 声称93.05%，差距54.62pp |
| **Mem0数据双重标准** | ★★★★☆ | 论文66.9% vs 独立~49% |
| **MemBrain无论文** | ★★★☆☆ | SOTA声称仅GitHub+博客 |
| **同团队循环引用** | ★★★☆☆ | EverMemOS+HyperMem同团队 |

#### 1.3.3 安全盲区

| 威胁 | 成功率 | 防御 |
|------|--------|------|
| 记忆投毒 | 85%+ (AgentPoison) | 几乎为零 |
| 环境注入 | 32.5% (eTAMP) | 几乎为零 |

---

### 1.4 演进方向

```
1. 静态 → 动态：L0 → L1 → L2 → L3 → L4
2. 被动 → 主动：被动检索 → Active Retrieval
3. 扁平 → 结构化：向量 → 图 → 超图 → Agent原生
4. 外挂 → 内嵌：外部 → 分层 → 模型 → 混合
5. 不安全 → 内生安全：无防护 → 版本控制 → 完整闭环
```

#### 三维分类框架

```
认知层级：L0感知(KV Cache) → L1工作 → L2长期(语义/情景/程序性)
记忆动力学：静态 → 被动管理 → 主动调度 → 自组织
安全可信：无防护 → Cisco外挂 → Medicina版本控制 → 内生安全
```

---

## 第2章：学术论文深度洞察

### 2.1 论文图谱

```
模型记忆                    OS/上下文              版本控制
├─ Memorizing Trans.      ├─ MemGPT/Letta        ├─ Medicina (GTC 2026)
├─ MemoryLLM              ├─ EverMemOS           
├─ MSA (2603.23516)       └─ RMT                 
└─ ICLR STEM (2601.10639)                       

时序分层                    安全                   基准
├─ TiMem (2601.02845)     ├─ AgentPoison (2407.12784) ├─ LOCOMO ★
├─ LiCoMemory (2511.01448)├─ eTAMP (2604.02623)      ├─ LongMemEval ★
└─ MemoryOS (2506.06326)  └─ MINJA防御 (2601.05504)   └─ EverBench ☆

新兴系统
├─ MemMachine (2604.04853) ★☆
├─ ENGRAM (OpenReview) ★☆
├─ 0GMem (MIT) ☆
├─ OmniMem (2604.01007) ★☆
└─ HyperMem (2604.08256) ☆
```

### 2.2 核心论文分析

#### 2.2.1 CoALA (arXiv:2309.02427)

Agent Memory 奠基性理论框架：**Observe → Think → Act → Learn** 循环，定义工作记忆/长期记忆二分，语义/情景/程序性三分。

#### 2.2.2 模型记忆三大子范式

| 范式 | 代表 | 持久性 | 说明 |
|------|------|--------|------|
| KV缓存检索 | H2O, SnapKV | 无状态 | 推理优化，非记忆系统 |
| MSA稀疏注意力 | Memorizing Trans., MSA | 无状态 | 推理中实时获取 |
| 参数内化 | MemoryLLM, STEM | 永久 | 跨会话真正记忆 |

#### 2.2.3 OS/虚拟上下文

| 论文 | 核心 | 效果 | 可信度 |
|------|------|------|--------|
| MemGPT | LLM自主换页 | 超长文档+20% | ★☆ |
| EverMemOS | engram生命周期 | ~~93.05%~~ ⚠️ | **☆☆ 复现仅38.38%** |
| HyperMem | 超图关联 | 92.73% | ☆ 同团队 |

#### 2.2.4 时序分层

**TiMem (arXiv:2601.02845)**：中科院自动化所，5层TMT，LoCoMo 75.30%，Token节省52.2%，复杂度感知召回。

#### 2.2.5 新型系统

**MemMachine (arXiv:2604.04853)**：
- LoCoMo 91.69% (gpt-4.1-mini), LongMemEvalS 93.0% (gpt-5-mini)
- 80% token减少，75% 加/搜索加速
- Ground-Truth保持，短/长期记忆+自适应检索

**ENGRAM (OpenReview)**：~99% token节省，77.55% LoCoMo

#### 2.2.6 安全研究

| 论文 | 发现 | 影响 |
|------|------|------|
| AgentPoison | 投毒85%+ | RAG系统性漏洞 |
| eTAMP | 跨站环境注入 | 攻击面扩展 |
| MINJA | 真实条件攻击大降 + 防御框架 | 首个实用防御 |

### 2.3 学术与产业映射

| 学术概念 | 产业实现 | 成熟度 | 验证 |
|---------|---------|--------|------|
| CoALA | 多系统部分实现 | ★★★☆☆ | 理论 |
| MemGPT | Letta | ★★★★☆ | 生产部署 |
| TiMem | 无直接对应 | ★★☆☆☆ | 论文 |
| Medicina版本控制 | Memoria (GTC 2026) | ★★☆☆☆ | 工程早期 |
| eTAMP安全 | 🆕 CortexMem提案 | ★☆☆☆☆ | 概念 |

---

## 第3章：技术方案 — CortexMem

### 3.1 场景与痛点

| 场景 | 需求 | 痛点 |
|------|------|------|
| 编码Agent | 精确代码上下文 | 跨会话遗忘 |
| 运维Agent | 时序事件+因果推理 | 缺乏时序分层 |
| 个人助手 | 用户画像 | 隐私缺失 |
| 多Agent | 共享+隔离 | 无协议 |

六大痛点：遗忘、黑箱、Token成本、不进化、孤岛、不安全。

### 3.2 技术方案：CortexMem

#### 3.2.1 设计哲学

1. **Markdown-first + 向量 + 版本控制**：人类可读 + CoW安全基线
2. **5层认知架构**：L0感知→L4画像（借鉴TiMem CLS）
3. **安全内生**：防火墙+溯源+沙箱+回滚（回应AgentPoison+借鉴Memoria）
4. **Active Retrieval**（借鉴MIRIX）

#### 3.2.2 架构

```
L0 感知: KV Cache语义淘汰
  ↓
L1 事实: 原始事实+自分类 [P/E/K/B/S]
  ↓
L2 会话: Markdown核心块 (人类可读)
  ↓
L3 模式: 日/周模式+CLS巩固
  ↓
L4 画像: 语义(图+向量)+情景(日志)+程序性(技能)
  ↓
CortexCore: 复杂度感知+Active Retrieval+LLM亲和检索
  ↓
Security: 防火墙+溯源链+沙箱+版本回滚
  ↓
Multi-Agent: 私有+共享+信任感知
```

#### 3.2.3 核心创新

**三级检索路径**：
- 简单：BM25/向量 → 零LLM
- 关系：图遍历 → 1次LLM
- 推理：LLM空间推理 → 多轮LLM

**CortexCore调度器**：
1. 复杂度感知召回（TiMem理念）
2. 遗忘曲线+CLS引擎
3. Active Retrieval（MIRIX理念）
4. 分级策略：高频用规则引擎，低频用强模型

**Security Layer（真正独特优势）**：
1. 记忆防火墙（写入验证+eTAMP防御）
2. 记忆溯源链（不可篡改日志）
3. 记忆隔离沙箱（不可信隔离验证）
4. 版本回滚（Memoria CoW理念）
5. 隐私保护（GDPR被遗忘权同步清除）

**Three-Unique-Dimensions 分析**（经全网验证）：

| 维度 | 竞品状态 | CortexMem |
|------|---------|-----------|
| 安全全闭环 | 仅有Memoria版本回滚（恢复层） | 防火墙+溯源+沙箱+回滚 **四层闭环** |
| 全认知栈覆盖 | TiMem缺L0，EverMemOS缺L0 | L0(KV)→L4(画像)，唯一全覆盖 |
| Markdown+版本+三维一体 | memsearch有Markdown无版本，Medicina有版本无Markdown | 三合一 |

#### 3.2.4 部署弹性

| 模式 | 依赖 | 场景 |
|------|------|------|
| 轻量 | SQLite+FTS5+文件 | 个人 |
| 标准 | PostgreSQL+pgvector+Neo4j | 小团队 |
| 企业 | PostgreSQL+Qdrant+Neo4j+Redis | 企业 |

### 3.3 差异化对比

| 维度 | CortexMem | 最强竞品 | 差异 |
|------|-----------|---------|------|
| 5层认知 | L0-L4 | TiMem L1-L5(无L0) | 增加感知层 |
| 版本控制 | CoW+快照+回滚 | Medicina | 与分层深度集成 |
| LLM亲和检索 | 三级(零/1/多轮) | MemBrain | 成本意识更强 |
| 安全四层闭环 | 防火墙+溯源+沙箱+回滚 | 无一完整 | **独特优势** |
| 复杂度感知 | 按查询自适应 | TiMem | 集成到调度器 |
| Active Retrieval | 自动跨类型 | MIRIX | 相同理念 |

### 3.4 测评标准

| 基准 | 目标 | 说明 |
|------|------|------|
| LOCOMO | >80% | 对标 TiMem 75.30% → MemMachine 91.69% |
| LongMemEval | >70% | 五维度 |
| CortexBench-Sec | >90% | AgentPoison/eTAMP |
| 版本回滚 | >95% | 投毒恢复 |

### 3.5 预期效果

| 维度 | 预期 | 对标 | 性质 |
|------|------|------|------|
| Token成本 | 降低60-70% | TiMem 52.2%, MemMachine 80% | 待验证 |
| LOCOMO | >80% | MemMachine 91.69%, TiMem 75.30% | 待验证 |
| 安全性 | >90%防御率 | 无竞品 | 预期 |
| 回滚恢复 | >95% | Medicina | 预期 |

### 3.6 行动路线

| 阶段 | 时间 | 交付 | 验证 |
|------|------|------|------|
| **MVP** | 4周 | L1-L3 Markdown+FTS5+复杂度感知 | LOCOMO >75% |
| **Phase 2** | +8周 | 5层+超图+Active Retrieval+回滚 | LOCOMO >85% |
| **Phase 3** | +12周 | 场景适配器+多Agent+自定义基准 | 3场景可用 |
| **Phase 4** | 持续 | User as Code+多模态 | 前沿 |

---

## 附录

### A. 系统全景表

| 系统 | 分类 | 存储 | 定位 | 进化 | Token | LoCoMo | LongMemEval | 可观测 | 许可 | GitHub |
|------|------|------|------|------|-------|--------|-------------|--------|------|--------|
| Mem0 | LLM决策 | 向量+图 | SDK | L1 | ~90% | 66.9%☆/~49%★ | 66.4%★ | API | Apache 2.0 | ~52K |
| Letta | 分层 | Core/Archival | 平台 | L2 | 中 | ~83.2%☆ | - | ADE | Apache 2.0 | ~21.8K |
| MemOS | 分层 | 图+向量 | OS | L3 | 35-72% | 75.80%☆ | 77.80%☆ | 面板 | Apache 2.0 | ~8.3K |
| MemBrain | Agent原生 | - | 服务 | L4 | - | 声称SOTA☆☆ | - | Viewer | TBD | ~269 |
| Memoria | 版本安全 | CoW DB | 安全层 | L1 | - | - | - | Git版本 | Apache 2.0 | ~193 |
| TiMem | 时序 | 5层TMT | 框架 | L2 | 52.2% | 75.30%☆☆ | 76.88%☆☆ | - | TBD | ~84 |
| EverMemOS | 分层 | Scenes/Cells | OS | L3 | ~85%☆ | ~~93.05%~~☆☆ | ~~83.00%~~☆☆ | - | Apache 2.0 | ~3.3K |
| MemMachine | Ground-Truth | 分层+自适应 | - | L2 | ~80% | 91.69%☆☆ | 93.0%☆☆ | - | Apache 2.0 | - |
| Zep | 时序图 | 时序图 | MaaS | L2 | ~1.4k tokens | 85.22%☆☆ | 63.80%☆☆ | Web | BSL | ~17.3K |
| ENGRAM | 架构级 | typed extract. | - | 无 | ~99% | 77.55%☆☆ | +15pts | - | - | - |
| SwiftMem | KV感知 | multi-token | - | 无 | 显著 | 70.4%☆☆ | - | - | - | - |
| OpenViking | 外部增强 | 虚拟FS | MaaS | L2 | 83-91% | 49%↑ | - | URI | AGPL-3.0 | ~4.8K |
| MIRIX | 多智能体 | 6类 | - | L3 | - | 85.4%☆☆ | - | - | TBD | - |
| 0GMem | 结构化 | BM25+语义 | 插件 | - | - | 88.67%(10-conv)☆ | - | - | MIT | 4 |

### B. 论文索引 (arXiv ID 已验证)

| # | 论文 | 年 | ID | 核心 | 可信度 |
|---|------|----|----|------|--------|
| 1 | Memorizing Transformers | 2022 | 2203.08913 | kNN注意力 | ★☆ |
| 2 | MemoryLLM | 2024 | 2402.04624 | 参数级记忆 | ★☆ |
| 3 | MSA | 2026 | 2603.23516 | 端到端长记忆 | ★☆ |
| 4 | ICLR STEM | 2026 | 2601.10639 | 查表式编辑 | ★☆ |
| 5 | MemGPT/Letta | 2023 | 2310.08560 | 虚拟上下文 | ★☆ |
| 6 | EverMemOS | 2026 | 2601.02163 | engram生命周期 | **☆☆复现失败** |
| 7 | HyperMem | 2026 | 2604.08256 | 超图 | ☆同团队 |
| 8 | TiMem | 2026 | 2601.02845 | CLS 5层TMT | ★☆ |
| 9 | MemMachine | 2026 | 2604.04853 | Ground-Truth+自适应 | ★☆ |
| 10 | MemOS | 2025 | 2507.03724 | Memory OS | ★☆ |
| 11 | Generative Agents | 2023 | 2304.03442 | 记忆流+反思 | ★ |
| 12 | A-MEM | 2025 | 2502.12110 | 记忆即Agent | ★☆ |
| 13 | CoALA | 2023 | 2309.02427 | 认知架构 | ★ |
| 14 | LOCOMO | 2024 | 2402.10790 | 基准 | ★ |
| 15 | LongMemEval | 2024 | 2407.16958 | 基准 | ★ |
| 16 | AgentPoison | 2024 | 2407.12784 | 投毒攻击 | ★☆ |
| 17 | eTAMP | 2026 | 2604.02623 | 环境注入 | ★☆ |
| 18 | MINJA | 2026 | 2601.05504 | 防御 | ★☆ |
| 19 | LiCoMemory | 2025 | 2511.01448 | CogniGraph | ★☆ |
| 20 | OmniMem | 2026 | 2604.01007 | AI自主研究 | ★☆ |

---

> **版本历史**：
> v1.0 — 初始版：30+系统 + 26论文
> v2.0 — 2026 Q2批判性验证：修正arXiv ID，标注可信度
> v3.0 — Token四维评估 + MemBrain/Memoria/TiMem/OmniMem/Engram/STEM/LiCoMemory
> v4.0 — **重大修正**：EverMemOS不可复现(GitHub #73) + MemMachine + HyperMem + 0GMem + 全数据可信度分级修正
