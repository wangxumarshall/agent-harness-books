# MAS System（MAS）

---

## 摘要

1. **MAS并非万能解法**：严格控制 Token 预算的实验证明，单体模型在顺序推理任务上碾压多体系统（性能下降 39-70%），MAS所谓"涌现优势"多为算力堆砌的假象。
2. **MAS业务场景**：仅当业务场景面临不可调和的**并行**瓶颈、硬性认知**隔离**、复杂对抗**博弈**、高**容错**诉求、必须映射到企业**组织结构**时，MAS 架构才具备技术合理性。
3. **MAS关键挑战**：协议碎片化、执行语义缺失、语义意图歧义、副作用失控。其中，“执行语义缺失”是最关键瓶颈，根据MAST，大规模生产环境中，79% 的MAS故障源于**系统协调**问题而非模型智能不足，协调开销占执行时间 40-60%。系统级"执行语义"的系统性匮乏（挂起恢复、状态版本控制、安全副作用审查边界缺失）。
4. **MAS核心原语**：事务性执行内核（如SagaLLM）、语义状态管理（AgentGit+SCF）、安全隔离（SAL）、协议统一网关（A2A/ACP/AG-UI等）。
5. **统一Agent抽象**：以 AgentUnit 统一抽象、TaskEnvelope 统一载体、Capability Graph 能力路由、六层分层架构为核心，构建可治理、可恢复、可审计的生产级运行时。

> 论文（SAL、SagaLLM、AgentGit、SCF、AIOS、UFO 系列、CASCADE、ACE-ROUTER、AGNT2、CodeRL+ 等）与实践（AgentPool、MCP+A2A、LangGraph、CrewAI）。

---

## 第一章 MAS 必要性

### 1.1 MAS并非无脑最优

2026 年 4 月，arXiv:2604.02460 通过严格控制"思考阶段 Token 生成总预算"证明：**拥有长上下文和强思维链的单体模型（SAS）在多步推理基准上几乎永远持平甚至碾压任何结构的 MAS 系统**。其理论基础是信息论中的**数据处理不等式（Data Processing Inequality）**：信息在多个独立 Agent 的上下文中来回传递时，每一次总结与转发都会导致关键信息比特的绝对丢失。单体模型在统一完整的连续上下文窗口内自回归生成，保留了无损的高维度语义梯度。失效根因分类：

| 失败根因分类 | 占比 | 典型表现 |
|:---|:---|:---|
| 宏观系统设计硬伤 | ~30% | 不合理拓扑、冗余调用、缺乏终止条件 |
| Agent间对齐失误 | ~49% | 有效信息丢失、幻觉雪崩、上下文重置 |
| 闭环验证失败 | ~21% | 过早终止、缺乏交叉校验、错误传播 |

**总结**：79%的失败源于系统规范与协调问题，协调开销占执行时间 40-60%，在顺序推理任务中 MAS 性能下降 39-70%。

### 1.2 需要MAS场景的判定维度思考

MAS 架构仅在满足以下**至少一项**刚需条件时才具备技术合理性：

| 条件 | 定义 | 量化判定标准 | 典型场景 |
|:---|:---|:---|:---|
| **并行**吞吐 | 任务含大量可并发 I/O 密集子任务 | 串行时间 >> 业务SLA | 多源检索、分布式爬取 |
| 认知**隔离** | 异构角色需独立推理路径与状态空间 | 角色混淆致准确率下降 >15% | 代码生成 vs 安全审计 |
| **对抗**验证 | 需多视角交叉校验或红蓝博弈 | 单模型确认偏误致关键错误率 >10% | 红蓝对抗、Actor-Critic |
| **容错**鲁棒 | 需局部失败隔离与优雅降级 | 单点故障传播致全链路崩溃 | 金融交易、运维自动化 |
| 组织**协作** | 任务天然对应多部门权限与合规边界 | 存在不可跨越的数据访问隔离 | 跨部门审批、合规审计 |

### 1.3 MAS场景特征空间模型

| 维度 | 核心驱动力 | 典型架构模式 | 解决的核心痛点 |
|:---|:---|:---|:---|
| 并行（Parallelism） | 降低端到端延迟 | Scatter-Gather、Map-Reduce | I/O 阻塞与长耗时 |
| 隔离（Isolation） | 防御上下文污染 | 角色沙箱、权限边界 | 推理衰退与越权 |
| 对抗（Adversarial） | 消除模型幻觉 | Actor-Critic、红蓝对抗 | 确认偏误与逻辑盲区 |
| 鲁棒（Robustness） | 容忍局部失败 | 冗余节点、看门狗 | 概率性输出不稳定 |
| 协作（Coordination） | 全局任务规划 | 黑板模式、Saga 编排 | 跨域依赖与状态同步 |

---

## 第二章 业务场景分类与特征空间映射

### 2.1 企业级软件研发自治

**特征权重**：协作 > 隔离 > 对抗

- 产如AgentPool，真实研发场景需要 Claude Code（架构理解）、Codex（快速实现）、Trae（代码评审）等异构 Agent 协作。核心价值不在于"让代码更聪明"，而在于将开发组织结构数字化——"写代码"与"审代码"具备系统级隔离。

### 2.2 长周期研究与决策支持

**特征权重**：并行 > 对抗 > 协作

- 多 Agent 并行检索多源数据，通过 Critic Agent 反驳验证，Evidence Agent 校验引用链。AgentPool 的 Team parallel 模式支撑此场景。核心挑战在于证据链可追溯性。

### 2.3 跨应用/跨端桌面自动化

**特征权重**：协作 > 鲁棒 > 并行

UFO 2 [arXiv:2504.14603] 提出 Desktop AgentOS 理念，通过混合检测（UIA 树 + 视觉语义）与 PiP 虚拟桌面隔离，解决了 Agent"霸占鼠标"的痛点。UFO^3 [arXiv:2511.11332] 通过 TaskConstellation（分布式 DAG）与 AIP 协议实现跨设备编排，子任务完成率 83.3%，端到端任务成功率 70.9%。

### 2.4 企业流程自动化与合规

**特征权重**：组织映射 > 隔离 > 鲁棒

CrewAI Flows 和 LangGraph 的持久化执行已在此领域验证。但关键缺失是：**动态补偿能力（API 变更时的回滚）** 与严格的 **不可篡改审计轨迹**。

### 2.5 极大规模仿真

**特征权重**：并行 > 鲁棒 > 协作

CASCADE [arXiv:2604.03091] 通过三级级联架构（宏观导演 → 协同枢纽 → 标签微观引擎），将 LLM 调用频率削减 95%。底层算法跑物理规则，中间件做群体意图路由，仅对玩家关注的 NPC 启动 LLM 实时渲染。

### 2.6 场景特征矩阵

| 业务场景 | 并行 | 隔离 | 对抗 | 鲁棒 | 协作 | 核心前沿实践 |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| 软件研发自治 | ◐ | ● | ◐ | ○ | ● | SolAgent 双环炼金、agentpool L4-L5 |
| 长周期研究 | ● | ○ | ● | ○ | ◐ | AgentPool Team parallel |
| 跨端自动化 | ◐ | ○ | ○ | ● | ● | UFO^3 TaskConstellation |
| 流程自动化 | ○ | ● | ○ | ◐ | ● | SCF 语义共识、SagaLLM |
| 极大规模仿真 | ● | ○ | ○ | ● | ◐ | CASCADE 级联架构 |
| Agent 经济网络 | ● | ● | ● | ● | ● | AGNT2 三维 L2 协议 |

（●=核心驱动 ◐=重要支撑 ○=非核心）

---

## 第三章 当前面临的挑战

### 3.1 协议碎片化

当前 Agent 生态存在六大协议，各自关注不同语义层面：

| 协议 | 关注层 | 核心能力 | 成熟度 |
|:---|:---|:---|:---|
| MCP（Anthropic） | Agent ↔ 工具/数据 | 工具发现、资源标准化、prompt 模板 | ★★★★☆ |
| A2A（Google） | Agent ↔ Agent | 对等发现、任务委托、跨框架协作 | ★★★★☆ |
| AG-UI（CopilotKit） | Agent ↔ 前端 | 流式事件、人类反馈、状态可视化 | ★★★☆☆ |
| ACP | Agent ↔ IDE | 会话、文件系统、终端、权限确认 | ★★★☆☆ |
| OpenCode | Agent ↔ 开发环境 | TUI/Desktop、LSP、MCP 管理 | ★★★☆☆ |
| OpenAI API | 兼容层 | 低迁移成本集成 | ★★★★★ |

**问题本质**：如果没有统一网关网关，系统将陷入适配器爆炸（N×M 复杂度）。
> 目前MCP + A2A 已形成工业界共识的双层协议栈：MCP 负责垂直（Agent→工具），A2A 负责水平（Agent→Agent），两者互补，均由 Linux Foundation 托管。

### 3.2 执行语义缺失

当前主流框架（LangGraph、CrewAI、AutoGen）本质上是"应用层编排"，缺乏如下原语：

| 缺失原语 | 问题表现 | 后果 |
|:---|:---|:---|
| **幂等性** | Agent 重试含外部突变操作时重复执行 | 支付重复、数据污染 |
| **挂起/恢复** | 缺乏 OS 级上下文栈快照能力 | 长任务断点不可续 |
| **事务保障** | 中间环节失败时无法干净回滚 | 80% 进度时全面崩溃 |
| **并发控制** | 多 Agent 并发读写共享环境缺乏锁语义 | 状态污染、幻读脏写 |

### 3.3 语义意图分歧

SCF 研究 [arXiv:2604.16339] 指出：企业级 Agent 部署失败率高达 41%-86.7%，79% 源于各自治 Agent 对共享业务目标的"认知撕裂"（无法达成语义一致）。SCF 语义共识框架在600 次高难度测试中唯一达成 100% 工作流完成率。

### 3.5 副作用失控

SAL [arXiv:2604.22136] 的实证表明：不经验证的 Agent 操作中 93% 可能触发不安全意图。大模型随机推理直接生成系统命令的架构，在幻觉发生时将引发不可逆的物理破坏。

---

## 第四章 现有技术方案对比

### 4.1 评估维度框架

对每项技术从五个维度进行严格评估：解决了什么问题（Solved）、未解决什么问题（Unsolved）、适用范围（Scope）、工程成熟度（Maturity）、对 AgentOS 的借鉴价值（Value）。

### 4.2 协议统一与路由层

#### MCP + A2A 协议栈

- **Solved**：MCP 统一 Agent↔工具接口标准，A2A 统一 Agent↔Agent 对等通信。两者互补，已被 Linux Foundation 托管，获 AWS/Microsoft/Salesforce/Google 等 150+ 组织支持。A2A 已于 2026 年初达到 v1.0
- **Unsolved**：两者均未定义 Agent 内部的执行语义（挂起/恢复/事务）。MCP 在万级工具下路由精度急剧下降
- **Scope**：通信与发现层，不涉及执行控制
- **Maturity**：★★★★☆

#### AIP [UFO^3, arXiv:2511.11332]

- **Solved**：专为 LLM Agent 设计的持久化、低延迟跨端通信协议，支持端到端加密
- **Unsolved**：目前仅在 Windows 生态验证
- **Maturity**：★★★☆☆

#### AgentPool MessageNode 抽象

- **Solved**：将 PydanticAI、Claude Code、Codex、ACP、AG-UI 等异构 Agent 统一为 MessageNode，YAML 配置驱动；支持A2A、ACP、AG-UI、MCP等协议。
- **Unsolved**：wrapped agents 对 pool-level MCP 可见性不一致；长时任务 durable execution 仍需上升为内核能力
- **Maturity**：★★★☆☆

### 4.3 状态一致性与版本控制

#### AgentGit [arXiv:2511.00628]

- **Solved**：引入 Commit/Revert/Branch 原语，Agent 可"时间倒流"并分裂多宇宙试错
- **Unsolved**：状态树计算开销在生产环境可能过大；语义合并精度依赖模型能力
- **Maturity**：★★☆☆☆

#### SCF 语义共识框架 [arXiv:2604.16339]

- **Solved**：将 Agent 意图提取为逻辑图谱，实时检测幻觉导致的资源竞争与因果倒置，600 次测试中唯一达 100% 完成率
- **Unsolved**：意图图谱提取精度受限于 NLU；仲裁延迟在极端并发下可能成瓶颈
- **Maturity**：★★☆☆☆

### 4.4 事务控制与容错

#### SagaLLM [arXiv:2503.11951, VLDB 2025]

- **Solved**：将分布式 Saga 模式引入 MAS，后置节点失败时自动触发补偿事务链，实现最终一致性
- **Unsolved**：要求下游 API 支持逆向操作（补偿接口），对遗留系统改造成本高
- **Maturity**：★★★☆☆

### 4.5 AgentOS 内核与调度

#### 深层语义上下文管理 [arXiv:2602.20934]

- **Solved**：将上下文视为"可寻址语义空间"，通过语义切片与认知同步脉冲根除长程认知漂移
- **Unsolved**：语义切片粒度自动化调优未解决
- **Maturity**：★★☆☆☆

### 4.6 主权安全与执行对齐

#### SAL [arXiv:2604.22136]

- **Solved**：推理与执行彻底解耦。模型仅输出受限意图，混淆膜屏蔽敏感标识，93% 拦截率，密码学证据链
- **Unsolved**：意图表达受限语法可能限制复杂操作灵活性
- **Maturity**：★★★☆☆

#### CodeRL+ [arXiv:2510.18471]

- **Solved**：将运行时栈变量动态轨迹融入策略网络，Pass@1 提升 4.6%，高难场景提升 15.5%
- **Unsolved**：训练成本高，泛化至非代码领域需验证
- **Maturity**：★★☆☆☆

### 4.7 综合对比矩阵

| 技术挑战 | 方案 | 已解决 | 未解决 | 成熟度 |
|:---|:---|:---|:---|:---:|
| 协议统一 | MCP + A2A + AgentPool | 工具/Agent 发现与通信 | 执行语义、万级路由 | ★★★★ |
| 状态一致 | AgentGit + SCF | 版本控制、意图冲突检测 | 计算开销、合并精度 | ★★ |
| 事务容错 | SagaLLM | 补偿事务、最终一致 | 遗留 API 适配 | ★★★ |
| 执行安全 | SAL | 推理执行解耦、审计链 | 灵活性、维护成本 | ★★★ |
| 跨端编排 | UFO^3 AIP | 跨设备 DAG | 跨 OS 能力 | ★★★ |
| 海量仿真 | CASCADE | 惰性推理、95% Token 节省 | 行为多样性保证 | ★★★ |
| 自我进化 | CodeRL+ | 执行语义对齐 RL | 训练成本、领域泛化 | ★★ |
| Agent 经济 | AGNT2 | 原生 L2、毫秒结算 | 工程验证阶段 | ★★ |

---

## 第五章 从 AgentPool 到 agentpool 的工程演进启示

### 5.1 AgentPool 已证明的核心价值

AgentPool 解决了"如何让不同 Agent 能够在同一系统中被发现、调用、组合和暴露"的问题：

- **YAML-first 配置**：用一个配置文件描述完整多 Agent 系统
- **MessageNode 统一抽象**：将 PydanticAI、Claude Code、Codex、ACP、AG-UI 等异构 Agent 统一
- **多协议 Server 暴露**：同一套能力通过 ACP/MCP/A2A/AG-UI/OpenCode/OpenAI API 暴露
- **Team 协作**：支持 parallel 和 sequential 组合
- **MCPManager + ToolManagerBridge**：区分 inbound MCP（消费外部工具）和 outbound bridge（暴露内部工具）

### 5.2 agentpool 的六层架构设想

agentpool 在 AgentPool 基础上提出了面向生产级的六层架构：

```
┌─────────────────────────────────────────────────────┐
│ Application Layer (IDE/Web/API/A2A Peer/Apps)        │
├─────────────────────────────────────────────────────┤
│ Protocol Gateway (ACP/MCP/A2A/AG-UI/OpenCode/API)    │
├─────────────────────────────────────────────────────┤
│ Orchestration Kernel (TaskEnvelope/AgentUnit/Policy)  │
├─────────────────────────────────────────────────────┤
│ Swarm Runtime (Teams/DAG/Autonomous Topology)         │
├─────────────────────────────────────────────────────┤
│ Memory & Durable State (Event Sourcing/Checkpoint)    │
├─────────────────────────────────────────────────────┤
│ Infrastructure & Observability (Tracing/Cost/Model)   │
└─────────────────────────────────────────────────────┘
```

### 5.3 关键演进抽象

| AgentPool 抽象 | agentpool 演进 | 核心提升 |
|:---|:---|:---|
| MessageNode | **AgentUnit** | 从"可处理消息的节点"→"可治理、可调度、可审计的执行单元" |
| 原始消息传递 | **TaskEnvelope** | 统一任务载体：goal + constraints + budget + SLA + evidence chain |
| 名称路由 | **Capability Graph** | 按能力而非名称路由，融合 ACE-ROUTER 历史轨迹感知 |
| Team parallel/sequential | **L1-L5 复杂度分级** | 同一内核不同控制强度 |

### 5.4 从学术原语到工程实践的桥梁

| 学术原语 | 工程化路径 | AgentOS 定位 |
|:---|:---|:---|
| SagaLLM 补偿事务 | 集成 Temporal/DBOS 作为 durable execution 后端 | 事务性执行内核 |
| AgentGit 状态版本 | 基于 event sourcing 实现轻量级 checkpoint/replay | 状态管理层 |
| SCF 语义共识 | 在 Policy Engine 中内嵌意图冲突检测规则 | 编排内核 |
| SAL 主权隔离 | 在 Protocol Gateway 实施零信任意图验证 | 安全内核 |
| AIOS 调度器 | 在 Swarm Runtime 中实现优先级队列与资源预留 | 调度内核 |
| CASCADE 惰性推理 | 在调度器中实现按需 LLM 调用策略 | 资源优化层 |

---

## 第六章 下一代 AgentOS MAS 子系统架构设计

### 6.1 设计原则

基于前五章的分析，下一代 AgentOS MAS 子系统的架构设计遵循以下七大原则：

1. **最小多体原则**：默认单 Agent，仅在满足五大刚需条件时拉起多进程 MAS
2. **执行语义完备性**：内核层必须原生支持挂起/恢复、事务回滚、幂等性保证
3. **协议中立性**：通过统一网关消化 MCP/A2A/AG-UI/ACP 等协议差异
4. **推理-执行解耦**：模型仅输出受限意图，由确定性控制平面验证后执行
5. **状态可溯源性**：所有状态变更均有版本、有证据链、可回放
6. **惰性推理优先**：在资源调度中优先使用轻量级确定性引擎，按需启动 LLM
7. **零信任安全**：每个 Agent 的每次操作都必须通过意图验证与权限校验

### 6.2 总体架构

```
┌──────────────────────────────────────────────────────────────┐
│  L7  Application & Scenario Layer                             │
│      业务场景模板 / L1-L5 复杂度分级 / 领域垂直系统            │
├──────────────────────────────────────────────────────────────┤
│  L5  Protocol Gateway & Routing Layer                         │
│      MCP/A2A 双层协议栈 / AG-UI/ACP/OpenCode 适配器           │
│      ACE-ROUTER 动态路由 / 协议语义中间件                     │
├──────────────────────────────────────────────────────────────┤
│  L4  Orchestration & Consensus Kernel                         │
│      TaskEnvelope 任务状态机 / SCF 语义共识仲裁                │
│      Capability Graph 能力路由 / Policy Engine 策略引擎        │
├──────────────────────────────────────────────────────────────┤
│  L3  Transactional Execution Engine                           │
│      SagaLLM 补偿事务链 / Durable Execution 持久化执行         │
│      Checkpoint/Replay / Idempotency Key 幂等保证             │
├──────────────────────────────────────────────────────────────┤
│  L2  Swarm Runtime & Scheduling                               │
│      AIOS 调度器 / AgentUnit 生命周期管理                      │
│      动态拓扑(Chain/Parallel/DAG/Swarm) / 沙箱隔离             │
│      CASCADE 惰性推理策略 / 资源预留与负载均衡                  │
├──────────────────────────────────────────────────────────────┤
│  L1  Semantic State & Memory Layer                            │
│      AgentGit 状态版本控制 / Event Sourcing 事件溯源           │
│      语义切片 + 认知同步脉冲 / Evidence Graph 证据图谱          │
│      多级记忆(Task/Agent/Org) / 记忆压缩与遗忘                 │
└──────────────────────────────────────────────────────────────┘
```

### 6.3 核心组件设计

#### 6.3.1 AgentUnit：统一执行单元

继承 AgentPool 的 MessageNode，升级为可治理的执行单元：

```
AgentUnit {
    identity:     名称/类型/版本/owner/tenant
    capabilities: 能力声明/工具边界/协议支持/成本模型
    runtime:      执行后端(native/claude_code/codex/acp/agui/a2a)
    memory_scope: 可读写的记忆空间
    state_policy: checkpoint/retry/timeout/compaction 策略
    tool_policy:  可用工具/审批策略/危险操作拦截
    security:     权限域/信任等级/审计等级
}
```

#### 6.3.2 TaskEnvelope：统一任务载体

所有协议入口归一化为结构化任务包：

```
TaskEnvelope {
    task_id / parent_task_id          // 任务标识与层级
    goal / constraints                // 目标与约束
    required_capabilities             // 所需能力
    budget_limits / deadline / SLA    // 资源约束
    input_artifacts / memory_refs     // 输入与记忆引用
    expected_output_schema            // 输出 schema
    permission_context                // 权限上下文
    evidence_chain                    // 证据链
    compensation_plan                 // 补偿事务计划
    current_state                     // 状态机当前态
}
```

#### 6.3.3 Capability Graph：能力路由图

不按名称而按能力路由，融合 ACE-ROUTER 的历史轨迹感知：

- **能力维度**：代码重构/测试生成/检索/推理/UI 反馈
- **环境维度**：本地/Docker/SSH/K8s/E2B/浏览器
- **成本维度**：延迟/Token/金额/可靠性
- **信任维度**：租户/密级/审计等级
- **历史维度**：成功率/平均延迟/失败模式

### 6.4 关键流程设计

#### 任务执行全链路

```
入口归一化 → 意图验证(SAL) → 能力路由(Capability Graph)
    → 拓扑规划(Chain/DAG/Swarm) → 沙箱分配
    → 并行执行 + 语义共识检测(SCF)
    → 验证 → [失败: 补偿事务(SagaLLM) → 重试/降级]
    → [成功: 状态提交(AgentGit) → 证据链写入]
    → 记忆更新 → 结果交付
```

#### 故障恢复流程

```
异常检测 → 状态快照(Checkpoint)
    → 依赖 DAG 分析 → 影响域计算
    → 补偿事务生成(SagaLLM) → 逆向执行
    → 状态回滚至最近一致点(AgentGit Revert)
    → 重新规划 → 替代路径执行
```

---

## 第七章 关键技术与实现路径

### 7.1 协议统一网关

**目标**：消化 MCP/A2A/AG-UI/ACP/OpenCode/OpenAI API 的语义差异。

**实现路径**：
- 采用中间件链模式：`auth → tenant → quota → policy → normalize → route → execute → audit`
- 每个协议适配器仅负责协议语义转换，不持有业务逻辑
- 典型转换：ACP session → TaskEnvelope；AG-UI action → HumanFeedbackEvent；MCP tool call → ToolInvocation；A2A task → ExternalDelegationTask

**技术选型**：基于 MCP + A2A 双层协议栈作为核心，其他协议通过适配器接入。ACE-ROUTER 的依赖图谱与合成轨迹训练方法可集成为路由网关的智能调度引擎。

### 7.2 事务性执行内核

**目标**：为长周期跨系统任务提供工业级事务保障。

**实现路径**：
- 集成 Temporal/DBOS 作为 durable execution 后端
- SagaLLM 模式的补偿事务引擎：任务切分为局部原子步骤，失败时自动触发逆向补偿链
- 幂等性保证：每个外部突变操作附带 Idempotency Key
- 模块化检查点：在分布式存储中实时持久化 DAG 状态树

**关键接口**：
```
TransactionEngine {
    begin_saga(task_envelope) → SagaContext
    commit_step(saga_ctx, step_result) → StepReceipt
    compensate(saga_ctx, failed_step) → CompensationChain
    checkpoint(saga_ctx) → CheckpointID
    restore(checkpoint_id) → SagaContext
}
```

### 7.3 语义状态管理

**目标**：解决多 Agent 并发环境下的状态一致性与认知漂移。

**实现路径**：
- AgentGit 模式的状态版本控制：Commit/Revert/Branch/Merge 原语
- Event Sourcing 事件溯源：所有状态变更以不可变事件流记录
- SCF 语义共识引擎：实时检测 Agent 间的意图图谱冲突
- 语义切片 + 认知同步脉冲（CSP）：在特定时间戳强制对齐环境状态

**多级记忆架构**：

| 记忆层级 | 作用 | 生命周期 | 存储形态 |
|:---|:---|:---|:---|
| Task Scratch | 单任务内临时工作记忆 | 任务结束即清理 | 内存/临时文件 |
| Agent Personal | Agent 个体经验与偏好 | 跨任务持久 | 向量索引 |
| Team Shared | 团队级共享知识 | 项目周期 | 知识图谱 |
| Organization | 组织级规则与策略 | 长期持久 | 规则引擎+图谱 |
| Evidence Graph | 决策证据与审计链 | 永久不可变 | 事件日志+密码学签名 |

### 7.4 主权安全隔离

**目标**：切断"随机推理"与"确定性执行"之间的直接耦合。

**实现路径**：
- SAL 模式的推理-执行解耦：模型仅输出受限意图，由控制平面验证后执行
- 混淆膜（Obfuscation Membrane）：屏蔽敏感标识符
- 主权评估函数：根据真实系统状态和预设策略进行硬性验证
- 密码学证据链：所有执行记录生成密码学签名永久留存
- 分级审批：低风险自动执行，中风险异步审批，高风险同步阻断

### 7.5 自适应调度引擎

**目标**：在多 Agent 并发环境下实现高效的资源分配与负载均衡。

**实现路径**：
- AIOS 模式的内核调度：公平轮转/优先级队列/中断机制
- CASCADE 惰性推理策略：绝大多数时间使用轻量级规则引擎，仅在需要时调用 LLM
- 动态拓扑切换：根据子任务性质在 Chain/Parallel/DAG/Swarm 间无缝切换
- 资源预留与抢占：关键路径任务可抢占非关键任务的计算资源

**调度策略矩阵**：

| 任务特性 | 调度策略 | 拓扑模式 |
|:---|:---|:---|
| 低延迟敏感 | 优先级抢占 + 资源预留 | 单 Agent 直连 |
| I/O 密集并发 | 公平轮转 + 挂起等待 | Scatter-Gather |
| 强依赖链路 | 拓扑排序 + 关键路径优化 | DAG |
| 探索性试错 | 分支并行 + 择优合并 | AgentGit Branch |
| 长期自治 | 任务板 + 空闲认领 | Autonomous Swarm |

### 7.6 分阶段建设路线图

| 阶段 | 目标 | 核心交付 | 预计周期 |
|:---|:---|:---|:---|
| **P1: 协议增强** | AgentPool 生产化 | A2A CLI、MCP 可见性统一、跨协议模型 | 4-6 周 |
| **P2: 编排内核** | agentpool Kernel | TaskEnvelope、AgentUnit、Capability Graph、Policy Engine | 6-8 周 |
| **P3: 持久运行时** | Durable Runtime | Event Sourcing、Checkpoint/Replay、Temporal 集成 | 8-10 周 |
| **P4: 蜂群运行时** | Swarm Runtime | Worker 原型、动态拓扑、沙箱隔离、Merge Coordinator | 8-10 周 |
| **P5: 安全内核** | Sovereign Security | SAL 意图验证、混淆膜、证据链、分级审批 | 6-8 周 |
| **P6: 记忆计算** | Memory Compute | 多级记忆、Evidence Graph、记忆压缩、Agent 路由优化 | 8-10 周 |

---

## 第八章 预期效果与评估框架

### 8.1 量化预期效果

| 指标 | 当前基线 | 预期目标 | 依据 |
|:---|:---|:---|:---|
| 长时任务成功率 | 13.3%-59% | >85% | SagaLLM 补偿事务 + Checkpoint 恢复 |
| 语义冲突检出率 | 未检测 | >65% | SCF 框架实证 65.2% |
| 不安全意图拦截率 | 未拦截 | >93% | SAL 框架实证 93% |
| 并发调度吞吐量 | 1× | 2.1× | AIOS 内核实验数据 |
| 大规模仿真 Token 成本 | 100% | <5% | CASCADE 95% 削减 |
| 跨框架集成时间 | 基线 | -70% | MCP 协议标准化实证 |
| 协调开销占比 | 40-60% | <20% | 结构化编排替代自由对话 |
| 万级工具路由精度 | 低 | 高 | ACE-ROUTER 图谱路由 |

### 8.2 评估框架

#### 8.2.1 功能正确性评估

- **单元级**：每个 AgentUnit 的能力声明与实际执行一致性
- **事务级**：SagaLLM 补偿事务链的完整性与正确性
- **系统级**：端到端 TaskEnvelope 从入口到交付的全链路成功率

#### 8.2.2 性能基准

- **延迟**：任务端到端延迟、协调开销比例、调度器排队时间
- **吞吐**：并发 Agent 数量、每秒处理任务数、资源利用率
- **成本**：Token 消耗、API 调用次数、计算资源占用

#### 8.2.3 鲁棒性测试

- **故障注入**：随机 Agent 崩溃、网络分区、API 超时
- **幻觉压力测试**：注入幻觉输出，验证 SCF 检出率与 SAL 拦截率
- **长时稳定性**：连续运行 24h+ 的状态一致性与记忆完整性

#### 8.2.4 安全性审计

- **意图验证覆盖率**：高危操作经过 SAL 验证的比例
- **证据链完整性**：密码学签名链的完整性与不可篡改性
- **权限隔离有效性**：跨租户/跨 Agent 的数据访问隔离

---

## 参考文献

| 编号 | 论文/项目 | 来源 | 时间 |
|:---|:---|:---|:---|
| [1] | Sovereign Agentic Loops (SAL) | arXiv:2604.22136 | 2026.04 |
| [2] | SagaLLM: Transaction Guarantees for MAS | arXiv:2503.11951 (VLDB 2025) | 2025.03 |
| [3] | AgentGit: Version Control for MAS | arXiv:2511.00628 | 2025.11 |
| [4] | Semantic Consensus Framework (SCF) | arXiv:2604.16339 | 2026.04 |
| [5] | AIOS: LLM Agent Operating System | arXiv:2403.16971 (COLM 2025) | 2024.03 |
| [6] | UFO^3: Weaving the Digital Agent Galaxy | arXiv:2511.11332 | 2025.11 |
| [7] | UFO 2: The Desktop AgentOS | arXiv:2504.14603 | 2025.04 |
| [8] | CASCADE: Cascading Architecture for Social Coordination | arXiv:2604.03091 | 2026.04 |
| [9] | ACE-ROUTER: History-Aware Routing | arXiv:2601.08276 | 2026.01 |
| [10] | AGNT2: Agent Economies on L2 Infrastructure | arXiv:2604.21129 | 2026.04 |
| [11] | CodeRL+: Execution Semantics Alignment | arXiv:2510.18471 | 2025.10 |
| [12] | Why Do MAS LLM Systems Fail? (MAST) | arXiv:2503.13657 | 2025.03 |
| [13] | Single-Agent Outperform MAS | arXiv:2604.02460 | 2026.04 |
| [14] | MCP: Model Context Protocol | Anthropic | 2024 |
| [15] | A2A: Agent-to-Agent Protocol v1.0 | Google / Linux Foundation | 2025-2026 |
| [16] | MultiAgentBench | arXiv:2503.01935 | 2025.03 |
| [17] | SolAgent: MAS for Solidity | arXiv:2601.23009 | 2026.01 |
| [18] | Architecting AgentOS: Token to System Intelligence | arXiv:2602.20934 | 2026.02 |
| [19] | AgentOS: NL-Driven Data Ecosystem | arXiv:2603.08938 | 2026.03 |
| [20] | AgentPool: 多协议异构 Agent 编排 | ClawTeam | 2025 |
| [21] | agentpool: 下一代生产级多智能体框架 | ClawTeam | 2025 |
