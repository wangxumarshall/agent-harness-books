# AgentRuntimeFabric Findings

## File Inventory

- `insight-v1.md`: 企业架构文档雏形，覆盖背景、目标、非目标、五平面、六对象、runtime 状态机、API、事件、安全、观测、部署、roadmap。
- `insight-v2.md`: 对五平面职责和对象语义的精炼版，强调 control/execution/state/policy/observability 解耦，runtime 可插拔，workspace/snapshot 是恢复与协作基础。
- `insight-v3.md`: 偏概念与行业类比，补充 Semantic Context Plane、分支/锁、多智能体协同、可插拔 compute pool、HITL、Semantic Firewall、标准协议边界。
- `insight-v4.md`: 技术对标分析，强调行业从“会调用工具”走向“会运行工作流”；OpenAI/Google/AWS/E2B/Modal/Daytona/OpenHands/AutoGen 分别验证编排、治理、pause/resume、snapshot、低延迟 stateful sandbox、workspace lifecycle、actor event model 等能力。
- `insight-v5.md`: 面向研发实现的详细设计，提出 7 个物理服务域、六对象字段、runtime 类型、正常执行/失败恢复流程、多 Agent 协作、事件模型、存储设计、API、默认安全策略、部署建议和三阶段 MVP。
- `AgentRuntimeFabric-v2.md`: 当前最强目标架构，升级为 durable workflow kernel + runtime adapter contract + workspace lineage + governance fabric；拆分 WorkflowRun / Task / ExecutionLease / RuntimeInstance 生命周期；定义 RuntimeAdapter、RuntimeCapabilities、PolicyDecision、A2AEnvelope、Semantic Context Plane、Replayable Event Fabric、Phase 0-5 演进路线。
- `AgentRuntimeFabric-Solution.md`: 综合方案，补齐业务场景、问题挑战、AgentOps Layer、KnowledgeBase、Skill Registry、关键技术、部署拓扑、Phase 1-4 MVP，以及风险缓解矩阵。相对 v2 更重产品与场景表达，但生命周期模型仍偏早期，需要以 v2 的四层生命周期拆分修正。

## Extracted Concepts

- 已有材料共同收敛到：Control Plane / Execution Plane / State Plane / Policy Plane / Observability Plane。
- 核心对象稳定为：Session、Task、Workspace、Snapshot、Policy、Artifact。
- `Workspace` 是长期状态与协作边界；`Runtime` 是短生命周期、可替换的执行资源。
- `Snapshot` 是恢复、分支、回放的原语，应优先支持增量、可恢复、可分叉。
- `Event Log` 是可观测、审计、回放和恢复编排的事实源。
- `Policy` 必须外置且声明式，覆盖命令、路径、网络、密钥和审批。
- `Semantic Context Plane` 在 insight-v3 中被引入，用于把长日志、错误和产物压缩为可用于 LLM 决策的高信息上下文。
- v2 新增稳定对象：AgentSpec、AgentActor、EnvironmentSpec、WorkflowRun、ExecutionLease、RuntimeInstance、WorkspaceBranch、PolicyDecision、Approval、SecretGrant、ToolCall、A2AEnvelope、Event。
- v2 新增稳定边界：Workflow Boundary、Computer Boundary、Governance Boundary、Protocol Boundary、Collaboration Boundary、Context Boundary、Evidence Boundary。
- RuntimeAdapter 必须提供能力声明、allocate/connect/reconnect/mount/execute/stream/open_port/snapshot/restore/pause/resume/teardown，并返回结构化事件。
- Governance Fabric 明确 UserIdentity、AgentIdentity、ToolIdentity、RuntimeIdentity、SecretIdentity 分层；高风险动作默认审批；SecretBroker 和 EgressGateway 为平台能力。
- Workflow Kernel 负责 durable state machine、Task DAG、checkpoint、retry、timeout、approval wait、runtime lost、compensation、handoff/review/merge。
- Solution 文件新增业务需求：复杂软件工程、长时后台任务、多 Agent 并发协作、浏览器/UI 自动化、数据/GPU 任务、高安全执行环境、AgentOps 团队协作、知识库与技能复用。
- Solution 文件新增产品入口：AgentOps Layer 只通过 Session/Task/Approval/Comment/Blocker API 影响执行，不能直接调用 Runtime。
- Solution 文件新增复用闭环：KnowledgeBase 是上下文来源，Skill/Playbook 是成功任务沉淀，但二者都不能绕过 Policy。

## Requirements and Gaps

- 早期文档把 Runtime 与 Task 状态机混在一起；最终设计需要拆成 WorkflowRun/TaskRun、ExecutionLease、RuntimeInstance、WorkspaceSnapshot 等不同生命周期。
- 已有 API 示例较粗，需要补输入输出契约、幂等键、错误码、状态转移前置条件和稳定版本边界。
- 已有路线给出 Phase，但缺少每阶段交付件、使用者、成功标准和明确不做事项。
- 需要明确哪些模块是核心必建，哪些是可复用库/适配器，哪些依赖外部系统。
- `AgentRuntimeFabric-v2.md` 的 Phase 0-5 可作为阶段基础，但用户要求更清楚“谁使用、解决什么问题、成功标准、哪些不做”，需扩展成交付矩阵。
- `AgentRuntimeFabric-Solution.md` 的 Phase 1-4 与 v2 Phase 0-5 命名不完全一致；最终文档应统一为 Foundation -> Lease/Daemon -> Governance -> Collaboration -> Multi-backend -> Knowledge/Replay 的阶段序列。

## Architecture Synthesis Notes

- 文档应采用“需求可验证 -> 模块边界 -> 对象模型 -> 协议契约 -> 状态机 -> 实现阶段”的顺序，便于后续 Codex 按任务拆解开发。
- 最终文档应明确“事实源”和“投影”的区别：EventLog / Workspace / Snapshot / Artifact / PolicyDecision 是事实；日志摘要、ContextIndex、Skill 建议是投影。
- 保留六平面 + AgentOps，但把 Durable Workflow Kernel 放在 Control Plane 与 State Plane 之间作为内核；把 Policy Plane 升级为 Governance Fabric。
- 针对“基于现有开源项目的堆加和重构”，最终设计应采用防腐层：OpenHands/Vercel Open Agents/AutoGen/Temporal/MCP/OPA/Vault/OpenTelemetry 等可以复用能力，但不能把其内部对象泄漏为 AgentRuntimeFabric 核心对象。
- 每个外部项目接入都应通过 contract tests 和 mapping ADR，稳定输出 Event、RuntimeAdapter、ToolCall、A2AEnvelope、PolicyDecision、SecretGrant 等内部契约。
