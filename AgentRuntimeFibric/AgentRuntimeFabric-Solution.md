# AgentRuntimeFabric方案设计

## 0. 摘要

AgentRuntimeFabric 是面向复杂 Multi Agent 任务的执行基础设施。它不是把 Agent 简单放进一个 sandbox，也不是给模型一个 remote shell，而是把 Agent 执行问题拆成可治理的分布式系统问题：控制面负责规划和决策，执行面负责隔离计算，状态面负责 workspace、snapshot、event、knowledge 和 artifact 的持久化，策略面负责权限、审批和网络出口，可观测面负责追踪、回放和故障复盘，协作入口负责把 Agent 变成可分派、可评论、可复盘的团队成员。

该架构的核心判断是：长时 Multi Agent 任务的成功率不只取决于模型能力，还取决于 runtime 是否可恢复、workspace 是否完整、状态是否可分支、安全策略是否可声明、执行过程是否可回放、知识上下文是否可治理、成功经验是否能沉淀复用。OpenAI 的 sandbox agent 文档把 harness/control plane 与 sandbox compute plane 明确拆分，Codex 文档把 sandbox 边界与 approval policy 区分开来；Anthropic Managed Agents 把 session event stream、harness 和 sandbox 解耦；Cabinet 和 Multica 则分别从知识库与 AgentOps 协作入口证明 Agent 基础设施正在向知识、任务、技能闭环扩展。[^openai-sandbox-agents][^openai-codex-sandbox][^anthropic-tool-use][^anthropic-managed-agents-events][^anthropic-managed-agents-engineering][^cabinet][^multica]

## 1. 业务场景

### 1.1 复杂软件工程任务

典型任务包括修复大型仓库 bug、通过 SWE-bench 类评测、迁移框架版本、重构模块、补齐测试、运行构建链和生成 PR。此类任务的 runtime 需要完整持有仓库、依赖缓存、构建产物、日志、端口、浏览器状态和历史尝试。单轮对话上下文无法承载真实工程现场，workspace 必须成为长期状态的主载体。

### 1.2 长时后台任务

企业会把 “升级一个服务依赖并验证兼容性” 这类目标交给 Agent 后台运行数十分钟到数小时。任务期间会遇到依赖下载、测试矩阵、网络抖动、进程挂死、机器抢占、审批等待。AgentRuntimeFabric 必须支持暂停、恢复、迁移、重试和人工接管，不能把任务生命绑定到单个容器进程。

### 1.3 多 Agent 并发协作

一个大目标可能拆成多个子任务：A Agent 修改后端接口，B Agent 调整前端调用，C Agent 写测试，Reviewer Agent 汇总 diff。并发执行需要 workspace branch、状态锁、merge/rebase、冲突检测和审计链路，否则多个 Agent 会在同一目录中互相覆盖。

### 1.4 浏览器与 UI 自动化

前端应用开发、网页登录、控制台操作、设计回归和端到端测试需要 headless browser 或可视化 browser sandbox。浏览器会产生本地缓存、会话、截图、trace、录屏和端口映射，这些状态应归入 workspace 与 artifact，而不是散落在一次性 runtime 中。

### 1.5 数据、模型与 GPU 任务

数据清洗、向量索引构建、模型微调、推理验证和大规模批处理可能需要 GPU、对象存储、专用镜像和长时间运行。AgentRuntimeFabric 不直接替代训练平台，而是把 GPU job sandbox 作为可插拔执行后端，纳入同一套 task、policy、snapshot、event 和 artifact 模型。

### 1.6 高安全执行环境

企业 Agent 会读取第三方仓库、安装依赖、运行脚本、访问内网 API、操作密钥和提交代码。这些动作天然带来 supply chain、数据泄露、prompt injection、越权网络访问和误发布风险。平台需要默认最小权限、网络出口白名单、敏感动作审批、密钥代理和可审计日志。

### 1.7 AgentOps 团队协作

当多个 Agent 像团队成员一样参与项目，用户需要的不只是 “启动 N 个进程”，而是任务看板、负责人、评论、阻塞、审批、进度流和复盘记录。AgentRuntimeFabric 应把多 Agent 协作暴露为可管理的工作流，同时保证所有分派、评论、阻塞和审批都进入 event log，而不是停留在 UI 本地状态。

### 1.8 知识库与技能复用

Agent 的有效性依赖可用上下文：产品文档、架构决策、历史 PR、运行手册、客户反馈、竞品观察和团队约定都应该成为可挂载、可索引、可审计的知识源。成功任务还应沉淀为 Skill 或 Playbook，用于同类任务的计划生成、环境准备、命令选择和测试策略，但复用能力必须保留来源、版本和审批记录。

## 2. 问题挑战

| 挑战 | 现象 | 架构含义 |
| --- | --- | --- |
| 状态与执行耦合 | container crash 后进程、缓存、日志和现场一起丢失 | runtime 不能作为状态边界，状态必须外置 |
| Workspace 不完整 | Agent 只看到片段日志，无法复现构建现场 | workspace 应包含 repo、deps、cache、logs、ports、browser state |
| 长任务不可恢复 | 抢占、超时、OOM、断网后只能重跑 | 需要 snapshot、event log 和 task-level lifecycle |
| 安全策略粗糙 | 只有 “能不能联网/能不能执行” 的粗粒度开关 | 需要声明式 policy、approval、egress control、secret scope |
| Prompt injection | README、网页、测试输出诱导 Agent 忽略系统约束 | 工具结果和外部内容必须进入安全过滤与上下文分级 |
| 多 Agent 冲突 | 多个 Agent 改同一文件，谁覆盖谁不可追踪 | 需要 workspace branch、lock、merge queue 和 reviewer |
| 可观测不足 | 只保存最终回答，无法解释失败路径 | every command/event/artifact 都要可追踪、可回放 |
| 知识上下文失控 | Agent 临时抓取文档、复制历史日志，来源不明且不可复盘 | 需要 KnowledgeBase、Context Index、来源分级和挂载审计 |
| 经验无法复用 | 每次任务都重新摸索命令、测试入口和失败修复 | 需要 Skill/Playbook registry 和成功路径沉淀 |
| 成本与延迟 | 大量全量复制 workspace、重复安装依赖、冷启动慢 | 需要 CoW delta snapshot、缓存分层和 runtime pool |

这些问题的共同点是：Agent 执行不是单模型调用问题，而是一个有生命周期、有状态、有权限、有恢复语义的系统问题。

## 3. 现有技术研究

### 3.1 托管智能体平台：产品形态最接近

这一类产品把 Agent 从 SDK 推到托管运行平台，覆盖编排、工具、会话、治理、追踪和后台执行，是 Anthropic Managed Agents 的直接参照物。从硅谷基础设施视角看，竞争焦点已经不是 “谁的 agent loop 更聪明”，而是谁能把 agent loop 外围的身份、策略、运行时、观测和恢复边界做成稳定平台。

OpenAI 的 Agents SDK 提供代码化编排、handoff、guardrails、tracing、工具调用和 sandbox execution；Codex cloud / background execution 则把代码任务放到云端后台运行。它的启发是：AgentRuntimeFabric 需要同时服务 SDK 编排和长时后台任务，把 tracing、handoff、guardrail、sandbox 和 approval 统一到同一个 task/session 事实流里，不能只提供一个远程 shell。[^openai-agents-sdk][^openai-sandbox-agents][^openai-codex-sandbox]

Google 的 ADK 是代码优先、模型相对中立的 agent 框架；Gemini Enterprise 侧重把企业内部、第三方和 ADK agent 注册、部署、治理和集中管理起来，并通过 Agent Runtime / Agent Engine 承接生产化运行。它的启发是：AgentRuntimeFabric 需要 Agent Registry、Identity、Gateway、Observability 这类企业治理入口，并把 agent 身份、用户身份、工具身份和 runtime 身份分开管理，而不是只做执行容器。[^google-adk][^google-gemini-enterprise-agents][^google-agent-runtime]

AWS Bedrock Agents / AgentCore 代表强托管、强治理路线。AgentCore Runtime 明确提供安全、serverless、框架无关、模型无关的 agent/tool 托管运行环境，并支持 MCP、A2A、多模态和多 Agent 工作流。它的启发是：AgentRuntimeFabric 的 Runtime 层应做到 framework-neutral、model-neutral、protocol-neutral，Policy 与 IAM/secret/egress 边界必须是一等能力。[^aws-bedrock-agentcore-runtime][^aws-bedrock-multi-agent]

Vercel Open Agents 是开源产品形态参考：Web 负责 auth、session、chat 和流式 UI，agent 作为 durable workflow 运行，sandbox VM 只负责文件系统、shell、git、dev server 和 preview port。它最关键的判断是 “agent is not the sandbox”，与 AgentRuntimeFabric 的脑体分离完全一致。[^vercel-open-agents]

### 3.2 执行面与沙箱底座：最接近 Runtime 后端

这一类不试图定义完整 Agent 产品，而是提供可编程、隔离、可恢复的执行环境，适合作为 AgentRuntimeFabric 的 Execution Plane 后端。它们共同说明：Agent 执行面不是 “容器 API”，而是一台可恢复、可连接、可审计、可传递的计算机。

E2B 提供面向 AI Agent 的 secure sandbox，并支持 pause/resume、filesystem + memory persistence、跨进程重新连接到同一个 sandbox。它证明 workspace/runtime persistence 是长时 Agent 的基础能力，而不是优化项；AgentRuntimeFabric 应把 reconnect、resume 和 snapshot lineage 做成 RuntimeAdapter 的标准契约。[^e2b-persistence]

Modal Sandboxes 提供可执行不可信用户或 Agent 代码的 secure container，支持程序化创建、依赖安装、端口、网络限制和 sandbox snapshot。它证明托管 Agent 的执行层需要 secure-by-default、可编程、可控网络和低冷启动成本；snapshot 不只是恢复机制，也是并行实验、debug fork 和冷启动优化的统一原语。[^modal-sandbox][^modal-sandbox-snapshots][^modal-networking]

Daytona 明确把 sandbox 定义为给 AI agents 使用的 composable computer，并将 runner 作为 compute plane、sandbox daemon 作为每个 sandbox 内的执行代理。它的启发是：Execution Plane 可以抽象为可调度 runner + sandbox daemon，而不是把执行逻辑塞进控制面。[^daytona-sandboxes][^daytona-architecture]

Firecracker 提供 microVM 级隔离、快速启动和 snapshot 恢复。对不可信代码、未知依赖和高隔离需求的 Agent 任务，microVM 是 container/gVisor 之外的强隔离后端。[^firecracker][^firecracker-snapshot]

### 3.3 开源自建框架：最接近参考实现

这一类更适合作为 AgentRuntimeFabric 的自建参考，而不是完整托管产品。它们暴露出的关键问题是：多 Agent 协作不是线程池问题，而是 actor identity、message routing、lifecycle、backpressure、checkpoint 和 replay 的运行时问题。

OpenHands 将 agent server、runtime、workspace 拆开，runtime 负责执行动作和管理运行环境，agent server 通过事件流协调交互。它证明 “stateless agent + workspace/runtime” 是可落地的开源架构，也说明 AgentRuntimeFabric 的控制面应尽量保持无状态，真正事实必须进入 EventLog 和 Workspace。[^openhands-runtime][^openhands-agent-server]

Microsoft AutoGen Runtime 提供 agent 通信、生命周期、安全边界、监控和调试等运行时能力。它更偏多 Agent 框架层，但对 AgentRuntimeFabric 的 Agent identity、message routing、lifecycle、observability 有直接参考价值。[^autogen-runtime]

Cabinet 和 Multica 分别补上两个产品侧缺口：Cabinet 强调 markdown/Git 知识库、定时任务和 Agent 角色编排，说明知识库是长期上下文底座；Multica 用看板、分派、评论、阻塞和 skill 复用组织 Agent 工作，说明多 Agent 系统需要 AgentOps，而不是只管理进程。[^cabinet][^multica]

### 3.4 顶级专家视角：Agent Runtime 的真正边界

这些方案共同说明，Agent 基础设施的长期稳定边界不是 planner、prompt 模板或某个模型版本，而是五个系统接口：

1. **Durable Workflow Boundary**：Session、Task、EventLog、Workflow state 必须可恢复、可回放、可迁移。
2. **Computer Boundary**：Workspace、Sandbox、Port、Process、Dependency、Snapshot 是 Agent 的执行身体。
3. **Governance Boundary**：Identity、Policy、Approval、Secret、Egress、Audit 必须独立于模型能力存在。
4. **Protocol Boundary**：MCP、A2A、tool call、runtime adapter 要让模型、框架和执行后端可替换。
5. **Collaboration Boundary**：Agent identity、message routing、assignment、blocker、handoff、review 和 merge 要进入统一事件流。

AgentRuntimeFabric 因此不应定位为 “另一个 Agent 框架”，而应定位为 Agentic Workflow Operating Layer：上接 OpenAI/Google/AWS/Anthropic/Vercel 这类编排和产品入口，下接 E2B/Modal/Daytona/OpenHands/Firecracker 这类执行后端，中间用 Session、Workspace、Policy、Event 和 RuntimeAdapter 固化长期接口。

### 3.5 技术收敛结论

按接近 Anthropic Managed Agents 的程度，可以分三层看：

1. **最像产品形态**：OpenAI Agents SDK + Codex cloud、Google Gemini Enterprise Agent Platform、AWS Bedrock AgentCore、Vercel Open Agents。
2. **最像执行底座**：E2B、Modal Sandboxes、Daytona、Firecracker。
3. **最像自建参考架构**：OpenHands、AutoGen、Cabinet、Multica。

如果为 AgentRuntimeFabric 的底层执行引擎选型，应优先研究 OpenAI Agents SDK + sandbox、E2B、Daytona、OpenHands Runtime 四个组合：它们分别覆盖编排层、沙箱层、状态恢复和开源参考实现。

行业前沿实现正在收敛到十二个原则：

1. **Control/Execution 分离**：模型编排与危险执行不在同一安全域。
2. **Workspace-first**：真实工程状态由 workspace 承载，而不是由 prompt 承载。
3. **Snapshot-first**：恢复、分支、调试和冷启动优化都围绕 snapshot 设计。
4. **Policy as Code**：网络、文件、命令、密钥、审批都应声明式表达。
5. **Everything is Event**：每次命令、工具调用、文件变化、审批和产物都进入事件流。
6. **Tool Protocol Standardization**：MCP/tool call 是控制面和外部能力之间的标准边界。
7. **Agent/Environment 分离**：Agent 身份、模型与工具配置不应和 runtime 镜像、依赖、资源规格混在一起。
8. **Knowledge-first Context**：长期上下文应来自可治理知识库和可索引 workspace，而不是临时拼接 prompt。
9. **AgentOps as Interface**：多 Agent 系统需要 issue、comment、assignment、blocker、approval 和 skill registry 作为团队协作入口。
10. **Identity-first Governance**：用户、Agent、工具、runtime、secret 都要有独立身份和最小权限边界。
11. **Durable Workflow as Kernel**：长任务不是后台线程，而是可恢复 workflow + 可审计事件流。
12. **Protocol-neutral Runtime**：运行时不绑定模型、框架或云厂商，必须通过 adapter 和标准协议接入。

## 4. AgentRuntimeFabric 方案

### 4.1 定义

AgentRuntimeFabric 是一个开源、模型无关、可自托管的 Managed Agents 基础设施。它以控制面为大脑、以可恢复 workspace 为身体、以 snapshot 和 policy 为边界、以 event stream 为神经系统、以 AgentOps 为协作入口、以 KnowledgeBase 和 Skill Registry 形成上下文与经验闭环。它向上服务 IDE、Web、API、CI、任务看板和自动化平台，向下调度 container、gVisor、Wasm、microVM、browser sandbox、GPU job 等异构 runtime。

更准确地说，AgentRuntimeFabric 是 Agentic Workflow Operating Layer：它不替代 OpenAI、Google、AWS、Anthropic 或本地 agent framework 的编排能力，也不替代 E2B、Modal、Daytona、Firecracker 的执行能力，而是在二者之间提供持久化 workflow kernel、workspace lineage、policy governance、runtime adapter 和 replayable event fabric。

### 4.2 设计目标

| 目标 | 设计要求 |
| --- | --- |
| Durable Execution | task/session 可暂停、恢复、迁移、重试，不绑定单个 runtime |
| Workspace-first | repo、deps、cache、env、logs、ports、browser state 统一进入 workspace |
| Snapshot Recovery | 通过增量 snapshot 支持恢复、回滚、分支和调试 |
| Secure by Default | 默认最小权限，网络、文件、命令、密钥和审批可声明 |
| Multi-Agent Collaboration | workspace branch、stateful lock、merge/review 支持并发协作 |
| AgentOps Workflow | task board、assignment、comment、blocker、approval、progress stream 统一进入事件流 |
| Identity-first Governance | 用户、Agent、工具、runtime、secret、artifact 拥有独立身份和最小权限边界 |
| Protocol-neutral Runtime | MCP、A2A、tool call、runtime adapter 可插拔，不绑定模型、框架或云厂商 |
| Knowledge-first Context | 团队知识、历史记录和 workspace 现场可挂载、可索引、可审计 |
| Skill Reuse | 成功任务沉淀为带来源、版本和审批的 Skill/Playbook |
| Replayable Execution | 所有命令、事件、diff、artifact、approval 可追踪和回放 |
| Pluggable Runtime | 按风险、资源和交互需求选择不同 execution backend |

### 4.3 非目标

AgentRuntimeFabric 不实现 LLM 本身，不替代 Kubernetes、CI/CD、数据库、对象存储、项目管理系统或企业知识库，也不把某一种 sandbox 技术、模型 provider 或 agent CLI 绑定为唯一实现。它定义的是 Agent 执行层的控制边界、状态模型、安全策略、运行时编排、协作事件和经验复用闭环。

### 4.4 六个平面与一个协作入口

| 层/平面 | 职责 | 典型组件 |
| --- | --- | --- |
| AgentOps Layer | 任务看板、分派、评论、阻塞、审批入口、进度流 | Task Board、Issue Adapter、Comment Service、Blocker Tracker、Approval UI |
| Control Plane | 规划、任务拆解、模型路由、审批决策、恢复编排 | Planner、Router、Memory Manager、Reviewer、Scheduler |
| Execution Plane | 运行命令、测试、浏览器、GPU job、工具调用 | Runtime Pool、Sandbox Adapter、Browser Pool、GPU Worker |
| State Plane | 持久化 workspace、snapshot、event、artifact、knowledge、skill、metadata | W-Volume、Snapshot Store、Event Log、Artifact Store、Knowledge Store、Skill Registry、Metadata DB |
| Policy Plane | 权限、审批、网络出口、密钥、审计 | Policy Engine、Approval Service、Egress Gateway、Secret Broker |
| Observability Plane | trace、metrics、日志、replay、time-travel debug | Trace Store、Replay Engine、Timeline UI、Alerting |
| Semantic Context Plane | 日志压缩、上下文分级、外部内容安全过滤 | Log Summarizer、Semantic Firewall、Context Index |

AgentOps Layer 是用户入口，不是新的执行面。它只能通过 Control Plane 创建和更新 Session、Task、Comment、Blocker 和 Approval，不能直接调用 Runtime。KnowledgeBase 和 Skill Registry 是状态资产，只有经过 Semantic Context Plane 的索引、摘要和安全过滤后，才能进入模型上下文。

### 4.5 稳定接口与可替换 Harness

AgentRuntimeFabric 不应把当前模型的短期缺陷固化成长期系统边界。规划、重试、工具纠错、日志压缩、记忆检索和上下文拼装都可能随着模型能力升级而被简化或重写，因此它们应作为 Harness 策略存在，而不是成为不可替换的平台内核。

长期稳定接口包括：

- `Session / EventLog`：执行事实流。
- `Workspace / Snapshot`：工程现场和恢复边界。
- `Policy / Approval`：权限和人工授权边界。
- `Secret Broker / Vault`：凭证隔离边界。
- `RuntimeAdapter / Sandbox`：可插拔执行边界。
- `Tool / MCP Execute Interface`：外部能力调用边界。
- `AgentSpec / EnvironmentSpec`：Agent 能力和执行环境配置边界。

可替换 Harness 策略包括：

- Planner、Router、Reviewer、Memory Manager。
- 上下文压缩、检索、重排和提示词组装。
- 工具调用修复、失败重试、反思和自检逻辑。
- 针对特定模型版本的 prompt、schema 和解析适配。

设计目标是让 Harness 可以热替换：模型变强时，系统可以删掉复杂补丁，换成更薄的调度层；Session、Workspace、Snapshot、Policy、Secret 和 Runtime 数据不需要迁移。

## 5. AgentRuntimeFabric 架构

### 5.1 总体架构图

```mermaid
flowchart TB
    U[User / IDE / API / CI] --> GW[API Gateway]
    AO[AgentOps Layer<br/>Task Board / Issue / Comment / Blocker] --> GW
    GW --> CP

    subgraph CP[Control Plane]
        Planner[Planner]
        Router[Model & Runtime Router]
        Scheduler[Task Scheduler]
        AgentCfg[AgentSpec Manager]
        EnvCfg[EnvironmentSpec Manager]
        Memory[Memory / Context Manager]
        Reviewer[Reviewer Agent]
        SkillUse[Skill Planner]
    end

    CP --> PP
    CP --> EP
    CP --> SCP

    subgraph PP[Policy Plane]
        AuthZ[AuthZ / RBAC]
        Policy[Policy Engine]
        Approval[HITL Approval]
        Egress[Egress Gateway]
        Secret[Secret Broker]
    end

    subgraph EP[Execution Plane]
        C[Container / gVisor Runtime]
        W[Wasm Runtime]
        M[Firecracker MicroVM Runtime]
        B[Browser Sandbox]
        G[GPU Job Sandbox]
    end

    EP --> SP
    PP --> EP

    subgraph SP[State Plane]
        WV[(Workspace Volume)]
        SS[(Snapshot Store)]
        EL[(Event Log)]
        AS[(Artifact Store)]
        KS[(Knowledge Store)]
        SR[(Skill Registry)]
        MDB[(Metadata DB)]
    end

    SP --> OP
    SCP --> CP
    EL --> SCP
    AS --> SCP
    KS --> SCP
    SR --> CP

    subgraph SCP[Semantic Context Plane]
        LS[Log Summarizer]
        SF[Semantic Firewall]
        CI[Context Index]
    end

    subgraph OP[Observability Plane]
        Trace[Trace / Metrics]
        Replay[Replay Engine]
        Audit[Audit Timeline]
        Debug[Time Travel Debug]
    end
```

### 5.2 核心对象模型

| 对象 | 定义 | 关键字段 | 关系 |
| --- | --- | --- | --- |
| AgentSpec | Agent 身份与能力定义 | `agent_spec_id`, `provider`, `model`, `system_prompt_ref`, `tool_refs`, `mcp_servers`, `default_policy_id`, `capability_tags` | Session/Task 可引用 AgentSpec |
| EnvironmentSpec | 执行环境模板 | `environment_spec_id`, `image_ref`, `dependency_profile`, `resource_spec`, `network_profile`, `mounts`, `secret_scope` | Task 通过 EnvironmentSpec 选择 Runtime |
| Identity | 用户、Agent、工具、runtime 和 secret 的权限主体 | `identity_id`, `type`, `principal_ref`, `scopes`, `trust_domain`, `expires_at` | Policy、Secret、Runtime lease 均绑定 Identity |
| Session | 用户宏观目标和对话任务容器 | `session_id`, `owner`, `goal`, `status`, `agent_spec_id`, `workflow_state_ref`, `policy_bundle_id`, `created_at` | 一个 Session 包含多个 Task |
| Task | 可调度、可恢复、可审计的执行单元 | `task_id`, `session_id`, `parent_task_id`, `assignee`, `status`, `priority`, `plan`, `workflow_step`, `agent_spec_id`, `environment_spec_id`, `runtime_profile` | Task 可递归拆分 |
| Workflow | durable workflow 状态机 | `workflow_id`, `session_id`, `state`, `cursor`, `retry_policy`, `compensation_policy`, `checkpoint_ref` | Session 绑定 Workflow |
| Workspace | 持久化工作区，是工程现场的事实源 | `workspace_id`, `base_image`, `mount_spec`, `env`, `branch_id`, `snapshot_head`, `lineage_ref` | Task 绑定 Workspace |
| Snapshot | 某一时刻的增量检查点 | `snapshot_id`, `workspace_id`, `parent_snapshot_id`, `delta_ref`, `memory_ref`, `created_at` | Workspace 拥有 snapshot DAG |
| Policy | 声明式执行约束 | `policy_id`, `allowed_tools`, `allowed_paths`, `network_rules`, `approval_rules`, `secret_scope` | 可附着到 Session/Task/Workspace |
| KnowledgeBase | 可治理的上下文来源 | `knowledge_base_id`, `source_type`, `uri`, `version_ref`, `trust_level`, `mount_policy`, `index_ref` | 可挂载到 Session/Task/Workspace |
| Skill / Playbook | 成功任务沉淀出的可复用经验 | `skill_id`, `name`, `version`, `applicability`, `steps_ref`, `provenance`, `approval_status` | Planner 可引用，Task 可生成 |
| Artifact | 执行证据和交付物 | `artifact_id`, `task_id`, `snapshot_id`, `type`, `uri`, `checksum`, `provenance` | 由 Task 产生并可被后续 Task 消费 |
| Runtime | 一次实际执行资源实例 | `runtime_id`, `backend`, `resource_spec`, `status`, `workspace_id`, `lease_ttl` | 可销毁、可恢复、可替换 |
| Event | 所有状态变化和动作结果 | `event_id`, `type`, `task_id`, `runtime_id`, `timestamp`, `payload` | Event Log 是 replay 基础 |

对象语义：

- Session 是目标容器，不是执行容器。
- Workflow 是长任务内核，不是后台线程。
- Identity 是权限主体，不等同于用户会话或模型身份。
- AgentSpec 定义谁来做，EnvironmentSpec 定义在哪里做，二者必须解耦。
- Task 是调度和审计边界，不是长期状态边界。
- Workspace 是身体，承载代码、依赖、缓存、日志和交互状态。
- Snapshot 是恢复和分支边界。
- Policy 是安全边界。
- KnowledgeBase 是上下文来源，不是系统指令。
- Skill/Playbook 是可复用经验，不是未经审查的自动权限升级。
- Artifact 是结果，也是证据链和后续推理输入。
- Runtime 是可替换执行后端，不是 Agent 身份。
- Event 是系统事实，不依赖模型总结。

### 5.3 Runtime 生命周期状态机

```mermaid
stateDiagram-v2
    [*] --> Drafted
    Drafted --> Queued: TaskCreated
    Queued --> Scheduling: TaskScheduled
    Scheduling --> Provisioning: RuntimeSelected
    Provisioning --> Mounted: RuntimeAllocated / WorkspaceMounted
    Mounted --> Priming: CacheWarmup / DependencyInstall
    Priming --> Running: RuntimeReady

    Running --> WaitingApproval: RiskActionDetected
    WaitingApproval --> Running: ApprovalGranted
    WaitingApproval --> Failed: ApprovalDenied / ApprovalTimeout

    Running --> Snapshotting: CheckpointRequested
    Snapshotting --> Running: SnapshotCommitted
    Snapshotting --> Failed: SnapshotFailed

    Running --> Suspended: Idle / UserPause / Preemption
    Suspended --> Recovering: ResumeRequested
    Recovering --> Running: StateRestored

    Running --> Recovering: RuntimeCrashed / HeartbeatLost
    Recovering --> Failed: RecoveryBudgetExceeded

    Running --> Succeeded: GoalSatisfied
    Running --> Failed: UnrecoverableError
    Running --> Aborted: UserCancelled
    Suspended --> Evicted: TTLExpired
    Evicted --> Recovering: RestoreFromSnapshot

    Succeeded --> [*]
    Failed --> [*]
    Aborted --> [*]
```

关键状态解释：

- `Drafted`：目标存在，尚未分配资源。
- `Queued`：等待调度。
- `Provisioning`：选择 backend，准备镜像、网络、密钥和资源。
- `Mounted`：workspace 已挂载。
- `Priming`：依赖安装、缓存预热、服务启动。
- `Running`：执行命令、工具调用或浏览器动作。
- `WaitingApproval`：触发高风险动作，runtime 挂起等待审批。
- `Snapshotting`：创建一致性检查点。
- `Suspended`：暂停或被抢占，状态仍可恢复。
- `Recovering`：从 snapshot/event 恢复现场并继续任务。
- `Evicted`：资源释放，task 仍可通过状态面恢复。

### 5.4 事件模型

标准事件结构：

```json
{
  "event_id": "uuid",
  "type": "CommandFinished",
  "session_id": "uuid",
  "task_id": "uuid",
  "workspace_id": "uuid",
  "runtime_id": "uuid",
  "timestamp": "2026-05-06T00:00:00Z",
  "actor": "agent|user|system|policy",
  "payload": {},
  "causation_id": "event_id",
  "correlation_id": "session_id"
}
```

核心事件类型：

- `AgentSpecRegistered`
- `EnvironmentSpecRegistered`
- `SessionCreated`
- `TaskCreated`
- `TaskAssigned`
- `TaskScheduled`
- `RuntimeAllocated`
- `WorkspaceMounted`
- `KnowledgeMounted`
- `CommandStarted`
- `CommandFinished`
- `ToolCallRequested`
- `ToolCallFinished`
- `AgentCommented`
- `BlockerReported`
- `ApprovalRequested`
- `ApprovalGranted`
- `ApprovalDenied`
- `SnapshotCreated`
- `ArtifactEmitted`
- `SkillProposed`
- `SkillApproved`
- `SkillApplied`
- `RuntimeSuspended`
- `RuntimeRecovered`
- `TaskCompleted`
- `TaskFailed`

事件设计原则是 append-only、可重放、可索引、可关联 artifact、snapshot、knowledge 和 skill。Session 不是模型上下文窗口，也不是聊天记录；它是执行事实流。模型上下文只是 Harness 从 Session、Workspace、KnowledgeBase 和 Artifact 中临时投影出的工作视图，可以被截断、压缩或重组，但原始执行事实必须永久保留。模型总结可以辅助理解事件，但不能替代事件事实。AgentOps UI 中的分派、评论、阻塞和审批也是系统事实，必须进入 event log，不能只保存在前端或项目管理工具中。

### 5.5 API 边界

AgentRuntimeFabric 的 API 以任务、状态和策略为中心，而不是以 “给 shell 发字符串” 为中心。

```http
POST /agent-specs
GET  /agent-specs/{agent_spec_id}

POST /environment-specs
GET  /environment-specs/{environment_spec_id}

POST /sessions
GET  /sessions/{session_id}

POST /tasks
POST /tasks/{task_id}/run
POST /tasks/{task_id}/cancel
POST /tasks/{task_id}/approve
POST /tasks/{task_id}/assign
POST /tasks/{task_id}/comments
POST /tasks/{task_id}/blockers

POST /workspaces
POST /workspaces/{workspace_id}/snapshot
POST /workspaces/{workspace_id}/restore
POST /workspaces/{workspace_id}/branch
POST /workspaces/{workspace_id}/merge

POST /knowledge-bases
POST /knowledge-bases/{knowledge_base_id}/mount

POST /skills
POST /skills/{skill_id}/approve
POST /skills/{skill_id}/apply

POST /runtime/allocate
POST /runtime/{runtime_id}/execute
POST /runtime/{runtime_id}/pause
POST /runtime/{runtime_id}/resume

GET  /events?session_id=...
GET  /artifacts/{artifact_id}
GET  /replay/{session_id}
```

接口原则：

- AgentSpec 和 EnvironmentSpec 是配置入口，不是执行授权；真正执行仍由 Task、Policy 和 Runtime lease 决定。
- AgentOps 只能通过 Session/Task/Approval/Comment/Blocker API 影响执行，不能绕过 Control Plane 直接调用 Runtime。
- Control Plane 只提交 intent、task 和 policy，不直接绕过策略面操作 runtime。
- Execution Plane 的命令执行必须绑定 task、workspace、runtime 和 policy。
- KnowledgeBase mount 必须绑定 trust level、policy version 和 Semantic Firewall 处理结果。
- Skill apply 必须绑定 skill version、applicability check、producer provenance 和审批状态。
- Snapshot/restore 必须产生日志事件，并绑定审批和审计上下文。
- Artifact 必须带 checksum、producer event 和 snapshot provenance。

### 5.6 Runtime 路由策略

| 任务类型 | 推荐后端 | 原因 |
| --- | --- | --- |
| 可信轻量脚本、格式化、静态分析 | container / gVisor | 启动快、成本低、隔离足够 |
| 高风险第三方依赖、不可信代码、编译脚本 | Firecracker microVM | 隔离强，适合运行未知代码 |
| 纯函数、插件、边缘轻任务 | Wasm runtime | 能力面小，权限易声明 |
| UI 测试、网页操作、截图和录屏 | browser sandbox | 需要 DOM、浏览器状态和端口 |
| 数据处理、训练、推理验证 | GPU job sandbox | 需要专用资源和长任务调度 |

路由输入包括：task risk、resource profile、network policy、secret scope、expected duration、interactive requirement、snapshot requirement。路由结果必须写入 Task 和 Runtime 元数据，便于审计和成本归因。

### 5.7 Workspace 与 Snapshot 架构

Workspace 建议采用 W-Volume 抽象：

```text
workspace/
  repo/
  deps/
  cache/
  logs/
  browser/
  ports/
  artifacts/
  snapshots/
  metadata/
```

Snapshot 建议采用 DAG：

```text
base-snapshot
  ├── task-a-step-001
  │   └── task-a-step-002
  └── task-b-branch-001
      └── reviewer-merge-001
```

设计原则：

- 文件系统 snapshot 优先使用 CoW/delta，而不是全量复制。
- 内存 snapshot 只用于需要恢复运行态的高价值场景，默认以文件系统和事件恢复为主。
- snapshot 必须包含一致性级别：`fs-only`、`fs+process-metadata`、`fs+memory`。
- 每个 snapshot 记录 parent、producer event、workspace branch、policy version 和 checksum。
- snapshot GC 按 session TTL、artifact retention、审计要求和人工 pin 规则执行。

### 5.8 多 Agent 协作模型

多 Agent 协作以 workspace branch 为边界：

```text
main
  ├── branch/task-backend-api
  ├── branch/task-frontend-ui
  └── branch/task-tests
       └── reviewer-merge
```

协作流程：

1. Planner 将目标拆成多个 Task。
2. 每个 Task 从同一 base snapshot fork 出独立 workspace branch。
3. Agent 在分支内执行，生成 patch、artifact 和 event。
4. Reviewer Agent 对分支结果做测试、diff review 和冲突检测。
5. Merge Queue 合并到 main workspace branch。
6. 合并后创建 reviewer snapshot，作为后续任务基线。

冲突控制：

- 文件级 optimistic lock 用于低冲突任务。
- 目录级 stateful lock 用于高风险改动。
- merge 前必须运行最低测试集。
- 任何自动合并都保留可回滚 snapshot。

### 5.9 AgentOps 协作模型

AgentOps Layer 把多 Agent 执行映射成团队可理解的工作流：

```text
Issue / Goal
  -> Session
  -> Task Board
  -> Task Assignment
  -> Progress / Comment / Blocker
  -> Approval / Review
  -> Merge / Artifact / Skill Candidate
```

设计原则：

- Issue、看板卡片和 CI job 都只是入口，内部统一转换为 Session 和 Task。
- Agent 被分配的是 Task，不是直接获得 workspace 写权限。
- 评论、阻塞、进度报告、人工审批都写入 Event Log，成为 replay 和审计的一部分。
- Blocker 必须能被 Planner 消费，触发重规划、转人工、换 AgentSpec 或换 EnvironmentSpec。
- AgentOps UI 不持有安全真相；权限、网络、密钥和审批仍由 Policy Plane 判断。

### 5.10 Policy Plane 设计

Policy 使用声明式策略表达：

```yaml
policy_id: policy-prod-code-agent
filesystem:
  allow_write:
    - /workspace/repo
    - /workspace/artifacts
  deny_write:
    - /workspace/secrets
network:
  default: deny
  allow:
    - domain: registry.npmjs.org
      ports: [443]
    - domain: api.github.com
      ports: [443]
commands:
  allow:
    - npm
    - node
    - git
    - pytest
  require_approval:
    - git push
    - npm publish
    - terraform apply
secrets:
  scope: task
  expose_as: brokered
approvals:
  timeout_seconds: 3600
  approver_groups:
    - repo-maintainers
```

关键机制：

- 默认拒绝网络，按域名、CIDR、端口和协议放行。
- 密钥不直接写入 workspace，通过 Secret Broker 注入短期凭证。
- 高风险动作进入 `WaitingApproval`，审批结果写入 event log。
- 策略版本固定到 task execution，避免运行中策略漂移不可解释。
- 对外部网页、README、日志、测试输出进入 Semantic Firewall，降低 prompt injection 风险。

### 5.11 Semantic Context Plane

Semantic Context Plane 解决两类问题：日志太大和外部内容不可信。

能力：

- 将 GB 级 stdout/stderr、构建日志、测试失败压缩成 KB 级高信号摘要。
- 将 artifact、event、diff、snapshot、knowledge 和 skill 编入 Context Index，供模型按需检索。
- 标记上下文来源：`trusted-system`、`user-provided`、`tool-output`、`external-web`、`untrusted-repo`。
- 对不可信内容做 prompt injection 检测，禁止其覆盖系统策略、审批规则和安全边界。
- 保留原始日志引用，摘要只作为模型输入，不作为审计事实。

### 5.12 Observability 与 Replay

可观测性不是 “能看日志”，而是 “能重建现场”。

核心能力：

- Session/Task/Runtime/Command 级 trace。
- stdout/stderr、exit code、duration、resource usage 结构化采集。
- 文件 diff、artifact、snapshot 与 command event 关联。
- Replay Engine 可按事件顺序重放执行轨迹。
- Time Travel Debug 可恢复到指定 snapshot，由人类接管 shell/browser，再交还 Agent。
- 审计视图显示谁批准了什么动作、在哪个策略版本下执行、产生了哪些外部访问。
- AgentOps timeline 显示任务分派、评论、阻塞、skill 应用和 knowledge mount 对执行结果的影响。

### 5.13 部署拓扑

```mermaid
flowchart LR
    Client[IDE / Web / API] --> APIGW[API Gateway]
    Board[AgentOps Board] --> APIGW
    APIGW --> CP[Control Plane Services]
    CP --> MQ[(Event Bus)]
    CP --> DB[(Metadata DB)]
    CP --> SK[(Skill Registry)]
    CP --> KB[(Knowledge Store)]
    CP --> PE[Policy Engine]
    PE --> EG[Egress Gateway]
    PE --> SB[Secret Broker]

    CP --> RP[Runtime Pool Manager]
    RP --> K8S[Kubernetes Node Pool]
    RP --> FC[MicroVM Node Pool]
    RP --> GPU[GPU Pool]
    RP --> Browser[Browser Pool]

    K8S --> WV[(Workspace Volume)]
    FC --> WV
    GPU --> WV
    Browser --> WV

    WV --> OSS[(Object Storage / Snapshot Store)]
    KB --> OSS
    SK --> OSS
    MQ --> OBS[Observability / Replay]
    OSS --> OBS
```

推荐技术组合：

- Control Plane：微服务或模块化单体，优先保证幂等、重试和事件一致性。
- Event Bus：Kafka、Redpanda、Pulsar 或云原生事件流。
- Metadata DB：PostgreSQL，保存 session/task/runtime/snapshot/artifact 元数据。
- Workspace：高性能块存储 + OverlayFS/ZFS/Btrfs/自研 CoW 层。
- Snapshot Store：S3 兼容对象存储，热快照可放高性能缓存层。
- Knowledge Store：Git/Markdown、对象存储、文档系统或企业知识库 adapter，原文与索引分离。
- Skill Registry：PostgreSQL 元数据 + 对象存储步骤模板，必须保存 provenance、版本和审批状态。
- Runtime：container/gVisor 作为 MVP，microVM 作为高风险任务增强，browser/GPU 作为专用池。
- Observability：OpenTelemetry + 日志索引 + replay service。

## 6. 关键技术

### 6.1 Workspace-first

Workspace 是 Agent 执行的事实源。模型上下文只携带当前需要推理的信息，真实现场必须保留在 workspace 中。设计上应避免把文件内容、日志和依赖状态复制到控制面内存；控制面只持有 metadata、summary、event cursor 和策略状态。

### 6.2 Delta Snapshot 与 CoW

Snapshot 的目标是降低恢复成本、支持分支和提升调试能力。全量复制 workspace 会造成不可接受的 I/O 与存储成本，因此默认采用 CoW delta。内存 snapshot 用于浏览器会话、长进程、REPL、调试现场等高价值场景；普通构建任务优先通过文件系统 snapshot + event replay 恢复。

### 6.3 Durable Task Lifecycle

Task 生命周期与 runtime 生命周期解耦。runtime 可以崩溃、被抢占或释放，task 仍可根据 event log、snapshot 和 policy 恢复。所有外部副作用动作必须具有 idempotency key 或至少写入 compensating event，避免恢复后重复发布、重复提交或重复调用生产 API。

### 6.4 Durable Workflow Kernel

长任务不应实现为后台线程或长连接进程，而应实现为 durable workflow：每个 Session 绑定一个 Workflow，Workflow 只保存状态机 cursor、checkpoint、retry policy、compensation policy 和未完成外部副作用记录。Harness、Runtime、Sandbox、Browser 或 MCP tool 可以随时崩溃或替换，Workflow 仍能从 EventLog、Snapshot 和 Artifact 中恢复。

Workflow Kernel 的最小职责：

- 将 Session goal 投影为可调度 Task DAG 或动态任务图。
- 记录每个 step 的状态、输入、输出、idempotency key 和补偿动作。
- 在 runtime crash、approval wait、network failure、quota limit 时恢复或重试。
- 将 handoff、blocker、review、merge、skill proposal 纳入同一状态机。

### 6.5 Stateless Harness

Harness 是无状态的推理调度脑干，不保存不可恢复的会话状态。它从 Session EventLog 查询事实，从 Workspace、Artifact、KnowledgeBase 和 Context Index 拉取必要上下文，调用模型生成下一步动作，再通过标准工具接口提交执行请求。Harness 崩溃、升级或替换不应影响 Session、Workspace、Snapshot、Policy 和 Runtime。

最小 Harness 接口：

```text
Harness
  wake(session_id)
  read_events(session_id, cursor | query)
  build_context(session_id, task_id, policy)
  propose_action(context) -> ToolCall | PlanUpdate | Comment | ApprovalRequest
  emit_event(session_id, event)
```

Harness 只能提出 action，不能绕过 Policy Plane 直接执行，也不能直接修改 Workflow truth。不同模型时代可以使用不同 Harness：早期模型需要显式 planner、tool repair 和 retry；更强模型可以使用更薄的 harness，甚至主要由模型自主调度。

### 6.6 Pluggable Hand Interface

AgentRuntimeFabric 将 sandbox、browser、GPU job、MCP server 和企业内部工具统一视为可插拔的 “Hand”。Hand 是执行能力，不是 Agent 身份；一个 Session 可以按需调用多个 Hand，一个 Hand 也可以被多个 Session 在策略允许下复用。

统一执行接口：

```text
Hand
  execute(name, input, policy_context) -> ToolResult

ToolResult
  event_id
  status
  stdout_ref
  stderr_ref
  artifacts
  exit_code
  resource_usage
  policy_decision
  provenance
```

所有 Hand 调用必须先经过 Policy Plane，并把请求、结果、产物和凭证访问写入 EventLog。这样 container shell、microVM、browser automation、MCP tool、GitHub API 和内部发布系统都能共用同一套审计、恢复和审批语义。

### 6.7 Pluggable Sandbox Adapter

Execution Plane 通过 adapter 接入不同后端：

```text
RuntimeAdapter
  allocate(profile, policy, workspace)
  execute(command, env, timeout)
  snapshot(level)
  restore(snapshot)
  pause()
  resume()
  stream_events()
  teardown()
```

adapter 屏蔽容器、microVM、browser、GPU job 的实现差异，但必须向上暴露一致的 event、artifact、exit status、resource usage 和 snapshot handle。

Runtime 应按需懒加载。Session 创建、Harness 唤醒和模型推理不应默认预启动完整 sandbox；只有 Task 需要 shell、browser、GPU 或外部工具时才 allocate runtime 或 hand lease。这样可以降低首 token 延迟、减少空闲资源浪费，并支持 “many brains, many hands” 的跨环境执行。

### 6.8 Egress Control

Agent 运行第三方代码时，网络出口是主要风险面。Egress Gateway 应支持 domain allowlist、CIDR allowlist、port/protocol 控制、DNS 审计、TLS SNI 记录、速率限制和任务级网络身份。默认策略应为 deny all，只为任务需要的 registry、GitHub、包管理源、目标 API 开口。

### 6.9 Identity 与 Secret Broker

密钥不应直接落入模型上下文、workspace、环境变量、日志或 artifact。Secret Broker 提供短期、可撤销、最小权限凭证，并根据 user identity、agent identity、tool identity、runtime identity、task、policy、approval 状态动态发放。任何 secret access 都必须产生日志事件，并在 stdout/stderr 采集层进行泄露检测和脱敏。

推荐采用 `MCP Proxy + Vault` 的凭证隔离模式：模型和 Harness 只看到代理能力或 session token；MCP Proxy 校验 session、task、policy 和 approval 后，代表 Agent 去 Vault 换取真实 Git token、API key 或云凭证并完成调用。真实密钥不暴露给模型，不写入 sandbox，不进入 workspace，不出现在 replay 原文中。安全边界建立在系统权限隔离上，而不是建立在 “模型不会想到越权方法” 的假设上。

Identity-first governance 的核心是把人、Agent、工具、runtime 和 secret 分成不同权限主体。Agent 不能继承用户全量权限，runtime 不能继承 Agent 全量权限，工具调用不能继承 runtime 全量权限；每次跨边界调用都需要 policy decision 和 audit event。

### 6.10 HITL 审批

高风险动作包括但不限于：

- `git push`、创建 release、合并 PR。
- `npm publish`、`pip publish`、发布容器镜像。
- `terraform apply`、修改生产基础设施。
- 访问生产数据库或生产 API。
- 发送外部邮件、消息、付款或删除数据。

审批卡点必须暂停状态机，保留 runtime 或创建 snapshot 后释放 runtime。审批结果进入 event log，并固定到后续执行上下文。

### 6.11 Semantic Firewall

Semantic Firewall 不试图 “完全理解恶意内容”，而是执行来源分级和策略隔离：

- 不可信内容不能修改系统指令、policy、approval rule 和 secret scope。
- 外部网页、README、issue、日志只作为 data，不作为 instruction。
- 工具输出中的命令建议必须再次经过 policy engine。
- 检测到注入风险时，生成安全摘要而不是把原文直接送入模型。

### 6.12 Replay 与 Time Travel Debug

Replay 依赖三类数据：event log、snapshot、artifact。用户可以从 timeline 选择某个失败点，恢复当时 workspace，查看命令、日志、diff、资源指标和策略状态。人类修复后创建新的 snapshot，Agent 从该点继续执行。这是复杂工程任务从 “黑箱自动化” 走向 “可协作自动化” 的关键。

### 6.13 多 Agent Branch/Merge

多 Agent 并发不是共享同一个目录，而是共享同一个 base snapshot。每个 Agent 在 branch 中工作，输出 patch 和 artifact，由 reviewer 合并。这样可以把并发协作转化为版本控制问题，沿用 diff、test、review、merge queue、rollback 等成熟工程机制。

### 6.14 AgentSpec 与 EnvironmentSpec 分离

AgentSpec 描述 Agent 的认知与能力配置：模型 provider、模型版本、系统提示词、工具集合、MCP server、默认策略和能力标签。EnvironmentSpec 描述执行环境：镜像、依赖、资源、网络、挂载、secret scope 和 snapshot 能力。二者解耦后，同一个 Agent 可以在低风险 container、高风险 microVM、browser sandbox 或 GPU job 中运行；同一个 Environment 也可以被不同 AgentSpec 复用。

这种分离避免 “agent = container” 的错误建模。Agent 本体绑定的是可恢复状态和可调用能力，不是某个执行壳。Agent 身份不随 runtime crash 消失，Environment 也不隐含模型权限。调度时由 Planner 选择 AgentSpec，由 Router 选择 EnvironmentSpec 和 Runtime backend，由 Policy Plane 最终裁决是否允许执行。

### 6.15 Knowledge-first Context Engineering

KnowledgeBase 保存团队知识的原始来源，如 markdown 仓库、设计文档、历史 issue、运行手册、PR 记录、客户反馈和外部网页抓取。Context Index 保存索引、摘要、embedding 和引用位置。模型上下文只拿最小必要片段，并携带来源、版本、trust level 和原文引用。

知识挂载必须满足四条规则：

- 原始知识是数据，不是系统指令。
- Knowledge mount 必须产生日志事件，记录来源、版本、挂载范围和策略版本。
- 不可信知识进入模型前必须经过 Semantic Firewall。
- Memory 写入必须可导出、可回滚、可审计，不能成为隐藏状态。

上下文工程是可替换 Harness 策略，而不是永久固化的平台逻辑。KnowledgeBase、EventLog、Workspace 和 Context Index 是稳定事实源；检索哪些片段、如何压缩、如何重排、如何写入 prompt，应由 Harness 根据模型能力和任务类型决定。未来模型上下文更长或工具使用更稳时，可以替换这层策略，而不迁移底层事实数据。

### 6.16 Skill / Playbook 反馈闭环

成功任务可以从 event、command、diff、artifact、test result 和 reviewer comment 中提炼 Skill/Playbook。Skill 不是简单保存 prompt，而是保存适用条件、准备步骤、常用命令、失败处理、测试入口、所需权限和产物检查方法。

Skill 进入全局 registry 前必须经过审批或自动门禁：

- `SkillProposed`：由 Planner、Reviewer 或用户从成功任务中提出。
- `SkillApproved`：由维护者或策略门禁确认适用范围和安全边界。
- `SkillApplied`：后续 Task 使用某个 skill version，事件中记录命中原因和效果。

Skill 不能自动扩大权限。它只能影响计划生成和执行建议，真实命令、网络和密钥仍由 Policy Plane 审批。

### 6.17 AgentOps Workflow

AgentOps 把底层执行状态转化为团队协作状态，但不改变安全边界。一个典型流程是：用户创建 issue，系统创建 Session，Planner 拆出 Task，Scheduler 分配 AgentSpec 和 EnvironmentSpec，Agent 在 workspace branch 中执行，过程中报告评论和阻塞，Reviewer Agent 或人类进行 review，Merge Queue 合并，成功路径进入 Skill 候选。

状态映射原则：

- 看板状态来自 Task 状态和 Event Log，不由 UI 手工维护第二套状态机。
- Agent comment 和 blocker 是可消费事件，Planner 可以据此重规划。
- Approval UI 只是 Policy Plane 的人类入口，审批结果必须回写事件流。
- 任务完成不等于经验可复用；只有通过 review 的成功路径才能生成 Skill。

## 7. MVP 落地方案

### 7.1 Phase 1：可恢复单 Agent 执行

目标：支持一个 Agent 在持久化 workspace 中执行命令、生成 artifact、创建 snapshot，并能从失败中恢复。

范围：

- 核心对象：AgentSpec、EnvironmentSpec、Session、Task、Workspace、Snapshot、Policy、Artifact、Runtime、Event。
- Runtime：container/gVisor。
- Workspace：持久化目录 + 基础 snapshot。
- Event：命令级、artifact 级、approval 级事件。
- Policy：文件写路径、命令 allowlist、网络开关。
- Observability：task timeline 和日志查看。

验收标准：

- 同一个 AgentSpec 可绑定不同 EnvironmentSpec 创建任务。
- runtime crash 后可从最近 snapshot 恢复并继续 task。
- 每条命令有 event、stdout/stderr、exit code 和 artifact 关联。
- 高风险命令会进入 WaitingApproval。

### 7.2 Phase 2：安全增强与多后端 runtime

目标：支持高风险代码、浏览器任务和更细粒度安全治理。

范围：

- 增加 Firecracker microVM adapter。
- 增加 browser sandbox。
- 引入 egress whitelist 和 Secret Broker。
- 引入 Semantic Firewall。
- snapshot 支持 delta 和分层存储。

验收标准：

- 高风险任务自动路由到 microVM。
- 默认无网络，按 policy 放行。
- 外部内容不能绕过 approval 和 policy。

### 7.3 Phase 3：多 Agent 协作与 Replay

目标：支持复杂项目的并发协作、AgentOps 工作流、reviewer 合并和时间旅行调试。

范围：

- Task Board、assignment、comment、blocker。
- Workspace branch/merge。
- Reviewer Agent。
- Replay Engine。
- Time Travel Debug UI。
- 成本归因和 snapshot GC。

验收标准：

- 多个 Agent 可从同一 base snapshot 并发执行。
- 分派、评论、阻塞和审批都能在 timeline 中回放。
- 自动合并前可运行测试并检测冲突。
- 用户可恢复到任意关键 snapshot 接管修复。

### 7.4 Phase 4：KnowledgeBase 与 Skill Registry

目标：支持团队知识挂载、上下文索引和成功路径复用。

范围：

- KnowledgeBase adapter：Git/Markdown、对象存储、文档系统。
- Context Index：知识、event、artifact、diff、snapshot 的统一检索。
- Skill Registry：skill proposal、approval、versioning、application。
- Memory 写入审计和导出。

验收标准：

- Task 可挂载指定版本的 KnowledgeBase，并记录 `KnowledgeMounted` 事件。
- 外部知识经过来源分级和 Semantic Firewall 后才能进入模型上下文。
- 成功任务可生成 Skill 候选，审批后被后续 Task 引用。
- Skill 应用不会绕过 policy、approval、egress 和 secret scope。

## 8. 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| Snapshot 数量膨胀 | TTL、GC、分层存储、人工 pin、按 session 归档 |
| Workspace 过大 | cache 分层、artifact 生命周期、依赖缓存去重 |
| 内存 snapshot 不稳定 | 默认 fs-only，memory snapshot 只用于特定 runtime/profile |
| 多 Agent 合并冲突 | branch 隔离、merge queue、reviewer、测试门禁 |
| Prompt injection | 来源分级、Semantic Firewall、policy 不受工具输出影响 |
| 知识库污染 | trust level、版本固定、mount 审计、索引与原文分离 |
| Skill 误用 | applicability check、版本化、审批、灰度启用、效果回溯 |
| AgentOps 状态分裂 | 看板状态从 Event Log 投影生成，不维护第二套事实源 |
| 密钥泄露 | Secret Broker、短期 token、日志脱敏、访问审计 |
| 网络滥用 | 默认 deny、egress gateway、DNS/TLS 审计、速率限制 |
| 成本失控 | runtime TTL、idle eviction、资源配额、成本归因 |
| 恢复重复副作用 | idempotency key、approval event、外部动作补偿日志 |

## 9. 架构设计原则总结

AgentRuntimeFabric 的专业架构原则可以压缩为二十一条：

1. 模型不直接拥有执行权，执行权由宿主和策略面授予。
2. Runtime 可丢弃，Workspace 才是长期事实源。
3. Snapshot 是恢复、回滚、分支和调试的统一原语。
4. Session 是执行事实流，不是模型上下文窗口。
5. Event log 是系统事实，模型摘要不是事实源。
6. Policy 必须声明式、版本化、可审计。
7. 网络出口和密钥访问默认拒绝。
8. 外部内容只能作为数据，不能升级为指令。
9. 多 Agent 协作走 branch、review、merge，而不是共享目录互写。
10. 可观测性必须支持 replay，而不仅是日志检索。
11. 执行后端必须可插拔，按风险和资源需求路由。
12. AgentSpec 定义能力，EnvironmentSpec 定义环境，二者不能混同。
13. AgentOps 是协作入口，不是执行授权入口。
14. KnowledgeBase 是可治理上下文源，Context Index 不是事实源。
15. Skill/Playbook 只能复用经验，不能自动扩大权限。
16. Harness 必须无状态、可替换、可升级，不持有不可恢复事实。
17. 工具、sandbox、browser、GPU 和 MCP 服务统一抽象为可插拔 Hand。
18. 真实凭证只存在 Vault，通过代理调用，不进入模型、workspace 或日志。
19. Durable Workflow 是长任务内核，不是后台线程或长连接。
20. 用户、Agent、工具、runtime 和 secret 必须使用独立身份与最小权限。
21. 不把模型短期缺陷固化成长期架构边界。

## 10. 结论

AgentRuntimeFabric 把 Agent 从 “一次模型调用 + 一个沙箱” 提升为 “可恢复、可治理、可审计、可并发协作、可沉淀经验的执行织网”。它参考 OpenAI、Anthropic 等前沿 Agent 产品和 API 设计中的控制边界，结合 E2B、Modal、Firecracker、OpenHands 等运行时基础设施的工程实践，并吸收 Cabinet 的知识库思路和 Multica 的 AgentOps 协作形态，形成一套适合企业级 Agent 平台落地的架构。

最终目标不是让 Agent 看起来更像一个会话机器人，而是让 Agent 像一个受控的分布式执行系统和可管理的团队成员：能接任务，能拆任务，能安全运行，能失败恢复，能解释过程，能使用团队知识，能与人类和其他 Agent 协作，能把成功经验沉淀为 Skill，并能在生产级约束下持续交付结果。

## References

[^openai-sandbox-agents]: OpenAI Developers, "Sandbox agents", https://developers.openai.com/api/docs/guides/agents/sandboxes
[^openai-agents-sdk]: OpenAI Developers, "Agents SDK", https://developers.openai.com/api/docs/guides/agents
[^openai-codex-sandbox]: OpenAI Developers, "Sandbox - Codex", https://developers.openai.com/codex/concepts/sandboxing
[^openai-mcp]: OpenAI Platform Docs, "MCP and connectors", https://platform.openai.com/docs/guides/tools-connectors-mcp
[^google-adk]: Google, "Agent Development Kit", https://google.github.io/adk-docs/
[^google-gemini-enterprise-agents]: Google Cloud, "Agents in Gemini Enterprise", https://cloud.google.com/gemini/enterprise/docs/agents
[^google-agent-runtime]: Google Cloud, "Configure the runtime for an agent", https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/configure/runtime
[^aws-bedrock-agentcore-runtime]: AWS Documentation, "Host agent workloads with Amazon Bedrock AgentCore Runtime", https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html
[^aws-bedrock-multi-agent]: AWS Documentation, "Use multi-agent collaboration with Amazon Bedrock Agents", https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html
[^vercel-open-agents]: Vercel Labs, "Open Agents", https://github.com/vercel-labs/open-agents
[^anthropic-tool-use]: Anthropic Claude Docs, "Tool use with Claude", https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview
[^anthropic-security]: Anthropic Claude Docs, "Claude Code security", https://docs.anthropic.com/en/docs/claude-code/security
[^anthropic-managed-agents-sessions]: Anthropic Claude Docs, "Managed Agents sessions", https://platform.claude.com/docs/en/managed-agents/sessions
[^anthropic-managed-agents-events]: Anthropic Claude Docs, "Managed Agents events and streaming", https://platform.claude.com/docs/en/managed-agents/events-and-streaming
[^anthropic-managed-agents-engineering]: Anthropic Engineering, "Scaling Managed Agents: Decoupling the brain from the hands", https://www.anthropic.com/engineering/managed-agents
[^e2b-persistence]: E2B Docs, "Sandbox persistence", https://e2b.dev/docs/sandbox/persistence
[^modal-sandbox]: Modal Docs, "Sandboxes", https://modal.com/docs/guide/sandboxes
[^modal-sandbox-snapshots]: Modal Docs, "Sandbox snapshots", https://modal.com/docs/guide/sandbox-snapshots
[^modal-networking]: Modal Docs, "Sandbox networking and security", https://modal.com/docs/guide/sandbox-networking
[^daytona-sandboxes]: Daytona Docs, "Sandboxes", https://www.daytona.io/docs/sandbox/
[^daytona-architecture]: Daytona Docs, "Architecture", https://www.daytona.io/docs/architecture/
[^firecracker]: Firecracker, "Firecracker MicroVM", https://firecracker-microvm.github.io/
[^firecracker-snapshot]: Firecracker GitHub Docs, "Snapshot support", https://github.com/firecracker-microvm/firecracker/blob/main/docs/snapshotting/snapshot-support.md
[^openhands-runtime]: OpenHands Docs, "Runtime architecture", https://docs.openhands.dev/openhands/usage/architecture/runtime
[^openhands-agent-server]: OpenHands Docs, "Agent server overview", https://docs.openhands.dev/sdk/guides/agent-server/overview
[^autogen-runtime]: Microsoft AutoGen, "Agent and Agent Runtime", https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/agent-and-agent-runtime.html
[^cabinet]: Hila Shmuel, "Cabinet", https://github.com/hilash/cabinet
[^multica]: Multica AI, "Multica", https://github.com/multica-ai/multica
