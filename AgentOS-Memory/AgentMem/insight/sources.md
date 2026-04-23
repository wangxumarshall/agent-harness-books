# Filesystem-like / Vector-Graph-like Agent Memory 来源索引

> 访问与核验时间：2026-04-15
>
> 使用原则：
> - 优先采用官方仓库、官方文档、原始论文、官方 benchmark / research page
> - 新闻稿、二手综述、社区复述只用于发现线索，不用于支撑主结论
> - 若同一系统同时存在论文口径与产品页口径，报告中会明确区分

---

## Filesystem-like Agent Memory

### OpenViking

- 官方仓库：<https://github.com/volcengine/OpenViking>
- 官方站点：<https://www.openviking.ai/>

本轮主要使用内容：

- context database for AI agents
- filesystem paradigm
- `viking://` context filesystem
- L0/L1/L2 tiered context delivery
- directory recursive retrieval
- retrieval trajectory
- 相对 OpenClaw / LanceDB 的 README benchmark 口径

### memsearch

- 官方仓库：<https://github.com/zilliztech/memsearch>
- 官方文档：<https://zilliztech.github.io/memsearch/>

本轮主要使用内容：

- Markdown source of truth
- Milvus shadow index
- dense + BM25 + RRF
- `search -> expand -> transcript`
- Claude Code / OpenClaw / OpenCode / Codex CLI 插件形态

### memU

- 官方仓库：<https://github.com/NevaMind-AI/memU>
- 官方站点：<https://memu.pro/>

本轮主要使用内容：

- memory for 24/7 proactive agents
- memory as file system
- categories / items / resources / cross references
- smaller context / proactive memory lifecycle
- token cost 官方口径

### Acontext

- 官方仓库：<https://github.com/memodb-io/Acontext>
- 官方文档：<https://docs.acontext.io/>
- 官方站点：<https://acontext.io/>

本轮主要使用内容：

- skill memory layer
- task learnings -> skill files
- Markdown skill files
- `get_skill` / `get_skill_file`
- no embeddings / no top-k retrieval as primary interface

### Voyager

- 原始论文：<https://arxiv.org/abs/2305.16291>

本轮主要使用内容：

- ever-growing skill library
- executable code as procedural memory
- long-horizon autonomous skill accumulation

### Memoria

- 官方仓库：<https://github.com/matrixorigin/Memoria>
- 官方站点：<https://thememoria.ai/>

本轮主要使用内容：

- Git for AI agent memory
- snapshot / branch / merge / rollback
- Copy-on-Write
- contradiction detection
- low-confidence quarantine
- audit trail / provenance chain

### lossless-claw

- 官方仓库：<https://github.com/Martian-Engineering/lossless-claw>

本轮主要使用内容：

- Lossless Context Management plugin for OpenClaw
- SQLite persistence
- DAG summary layers
- `lcm_grep` / `lcm_describe` / `lcm_expand`
- append-only raw messages + recoverable expansion

### XiaoClaw

- 官方站点：<https://xiaoclaw.com/>
- 安装与产品页：<https://www.xiaoclaw.xyz/>

本轮主要使用内容：

- 仅用于判断其更像 OpenClaw 的产品包装 / 一键安装层
- 不将其作为独立 memory architecture 代表

---

## Vector/Graph-like Agent Memory

### mem0

- 官方文档：<https://docs.mem0.ai/introduction>
- 官方仓库：<https://github.com/mem0ai/mem0>
- 原始论文：<https://arxiv.org/abs/2504.19413>
- 官方研究页：<https://mem0.ai/research>
- 官方研究页（新算法展示）：<https://mem0.ai/research-2>

本轮主要使用内容：

- universal, self-improving memory layer
- extract / consolidate / retrieve
- graph-enhanced memory path
- 论文 benchmark 口径
- 2026 官方研究页 benchmark 口径及其展示层次差异

### Honcho

- 官方仓库：<https://github.com/plastic-labs/honcho>
- 官方文档：<https://docs.honcho.dev/>
- 官方 benchmark blog：<https://blog.plasticlabs.ai/research/Benchmarking-Honcho>

本轮主要使用内容：

- entities / peers / sessions / contexts / representations
- continual learning over changing entities
- dream / representation update
- LongMem S / LoCoMo / BEAM 的官方 blog 口径

### Graphiti / Zep

- 官方仓库：<https://github.com/getzep/graphiti>
- 官方文档：<https://help.getzep.com/graphiti/getting-started/overview>
- 原始论文：<https://arxiv.org/abs/2501.13956>

本轮主要使用内容：

- temporal knowledge graph
- dynamic graph construction over evolving data
- time + full-text + semantic + graph retrieval
- DMR / LongMemEval 论文口径

### eion

- 官方仓库：<https://github.com/eiondb/eion>
- 官方站点：<https://www.eiondb.com/>

本轮主要使用内容：

- shared memory storage for multi-agent systems
- unified knowledge graph
- PostgreSQL + pgvector + Neo4j
- sequential / concurrent / guest access

### ContextLoom

- 官方仓库：<https://github.com/danielckv/ContextLoom>

本轮主要使用内容：

- shared brain for multi-agent systems
- Redis-first shared context state
- decoupled memory / compute
- cold-start hydration
- communication cycle / cycle hash

### mem9

- 官方仓库：<https://github.com/mem9-ai/mem9>
- 官方站点：<https://mem9.ai/>

本轮主要使用内容：

- persistent memory across sessions and machines
- stateless plugin + central memory server
- shared memory pool
- TiDB hybrid retrieval
- visual dashboard / access control

### UltraContext

- 官方文档：<https://ultracontext.ai/docs>
- 官方站点：<https://ultracontext.ai/>

本轮主要使用内容：

- Context API
- realtime capture of every agent's context
- history / fork / clone / edit contexts
- CLI + MCP server
- “same context, everywhere” 的上下文平面定位

---

## 学术界关键参照

### 架构与问题定义

- CoALA：<https://arxiv.org/abs/2309.02427>
- MemGPT：<https://arxiv.org/abs/2310.08560>
- Letta docs：<https://docs.letta.com/>

本轮主要使用内容：

- 模块化 agent memory 视角
- 虚拟上下文 / memory tiers 视角

### Benchmark

- LoCoMo：<https://arxiv.org/abs/2402.17753>
- LoCoMo 项目页：<https://snap-research.github.io/locomo/>
- LongMemEval：<https://arxiv.org/abs/2410.10813>
- BEAM：<https://arxiv.org/abs/2510.27246>

本轮主要使用内容：

- 长期对话 recall
- 时间推理
- 多 session 推理
- knowledge update / abstention
- 百万 token 级 benchmark 方向

### 结构化与多类型记忆

- TiMem：<https://arxiv.org/abs/2601.02845>
- LiCoMemory：<https://arxiv.org/abs/2511.01448>
- MIRIX：<https://arxiv.org/abs/2507.07957>

本轮主要使用内容：

- 时间层次化 consolidation
- 轻量图式导航
- multi-type memory orchestration

---

## 说明

- `report_v3.md` 中的 SOTA 判断，默认只代表 2026-04-15 前公开材料中的强信号。
- 如果某条 benchmark 来自官方 blog / README / research page，而不是同行评审论文或公开可复核 benchmark 页面，会在正文中明确标为“官方口径 / 自报”。
- `xiaoclaw` 不进入主线结论；`UltraContext` 作为 memory 邻接基础设施看待；`lossless-claw` 由于已有稳定官方仓库与机制说明，本轮升级为可核验样本。
