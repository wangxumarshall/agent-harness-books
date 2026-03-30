# 第二部分：语言层契约 — 跨语言类型对齐

## 本章Q

如何保证Rust→TypeScript编译时100%类型一致？

## 魔法时刻

跨语言类型对齐的难点不是技术，而是谁是新真实来源（SSOT）。

技术上有三种解法：ts-rs（Rust生成TS）、specta（TS生成Rust）、Protobuf（中立协议）。每种都能工作。但谁来决定用哪个？谁来维护映射规则？当Rust工程师加了一个字段，TS那边谁负责同步？这个"谁"的问题，是组织问题，不是技术问题。技术上永远有解；政治上，真实来源只能有一个。

## 五分钟摘要

第二章建立了GRT栈架构，第五章用Rust类型状态模式解决了单Agent状态机的编译期约束，第六章用Go控制平面解决了多Agent调度。但这三个语言层之间的类型如何跨越网络边界保持一致？答案是ts-rs和specta构成的类型双向生成体系。本章用三个代码实战展示：ts-rs如何将Rust结构体自动生成TS接口、Result/Option如何映射为TS联合类型、GRT栈如何实现SSOT实践。关键洞察：类型对齐的技术解法是成熟的，但SSOT问题是组织问题——谁有权力决定"这是唯一真实来源"，才是真正的难题。本章最后抛出开放问题：如果验证者本身出错，谁来验证验证者？这是Bootstrap问题，是所有类型安全体系的阿喀琉斯之踵。

**魔法时刻：** 跨语言类型对齐的难点不是技术，而是谁是新真实来源（SSOT）。技术上有ts-rs、specta、Protobuf三种解法，每种都能工作。但谁来决定用哪个、谁来同步、谁来维护——这是组织问题，不是技术问题。

---

## SSOT问题：政治问题，不是技术问题

### 什么是SSOT

SSOT（Single Source of Truth，单点真实来源）是跨语言系统设计的核心问题。在GRT栈中，当Rust定义了一个结构体，TypeScript需要一份等价的接口定义，Go需要一份等价的struct定义——这三份定义必须100%一致，否则网络传输时的序列化/反序列化就会悄悄出错。

理论上，定义一次，生成所有。但谁定义？

### 三种技术路线

| 路线 | 代表工具 | 真实来源 | 优点 | 缺点 |
|------|---------|---------|------|------|
| Rust生成TS | ts-rs | Rust | 编译期保证，无遗漏 | Rust团队必须懂TS |
| TS生成Rust | specta | TypeScript | 前端主导，迭代快 | Rust团队变成下游 |
| 中立协议 | Protobuf | `.proto`文件 | 独立于语言 | 需要额外编译步骤，类型表达能力受限 |

三种都能工作。但现实中的问题是：**Rust团队说"我们定义，TS团队负责同步"，TS团队说"我们定义，Rust团队负责翻译"**。没有共识，类型漂移是必然的。

### 组织的真相

SSOT问题在技术上是中立的。真正的问题是：

1. **谁有权力定义？** 结构体由Rust写出，TS必须跟着变——但TS可能有自己的业务需求不想被Rust支配
2. **谁来同步？** 每改一次，谁负责更新另一边的类型定义？人工同步必然出错
3. **冲突了听谁的？** Rust加了字段，TS不想跟——听谁的？

这些问题没有技术解法。只有组织决策：指定一个团队作为真实来源，其他团队必须接受其定义。如果做不到，就用自动化工具（ts-rs/specta）减少人工犯错的机会，但最终还是要有人承担责任。

**魔法时刻：类型对齐的技术解法是成熟的，但SSOT问题是组织问题——当两个团队对"真实来源"没有共识时，最好的工具也会失败。**

---

## Step 1: ts-rs实战 — Rust结构体自动生成TS接口

### 核心机制

ts-rs是一个Rust宏库，在`cargo test`时自动将Rust结构体/枚举生成为TypeScript类型声明文件。Rust是SSOT，TypeScript接口是派生出来的人工产物。

### 完整代码示例

```rust
// Cargo.toml
[dependencies]
ts-rs = "12.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```

```rust
// src/types/task.rs

use serde::{Deserialize, Serialize};
use ts_rs::TS;

// ============================================================
// Part 1: Agent任务状态 —— Rust结构体定义
// ============================================================

#[derive(Serialize, Deserialize, TS)]
#[ts(export)]
#[serde(tag = "phase")]
pub enum AgentPhase {
    Idle,
    Planning { plan: String },
    Executing { step: u32, total: u32 },
    WaitingForApproval { message: String },
    Completed { output: String },
    Failed { error: String },
}

#[derive(Serialize, Deserialize, TS)]
#[ts(export)]
pub struct Task {
    pub id: String,
    pub description: String,
    pub assigned_agent: Option<String>,
    pub phase: AgentPhase,
    pub created_at: i64,  // Unix timestamp
}

#[derive(Serialize, Deserialize, TS)]
#[ts(export)]
pub struct ToolCall {
    pub tool_name: String,
    pub arguments: serde_json::Value,  // 动态参数，TS端用 unknown
    pub result: Option<serde_json::Value>,
    pub called_at: i64,
}

// ============================================================
// Part 2: HarnessError —— 错误类型映射
// ============================================================

#[derive(Serialize, Deserialize, TS)]
#[ts(export)]
#[serde(tag = "kind")]
pub enum HarnessError {
    Timeout { task_id: String, waited_secs: u64 },
    InvalidToolCall { reason: String, attempted: String },
    PermissionDenied { resource: String },
    NetworkError { message: String },
    Internal { detail: String },
}

impl HarnessError {
    pub fn timeout(task_id: &str, secs: u64) -> Self {
        HarnessError::Timeout { task_id: task_id.to_string(), waited_secs: secs }
    }

    pub fn invalid_tool(reason: &str, attempted: &str) -> Self {
        HarnessError::InvalidToolCall { reason: reason.to_string(), attempted: attempted.to_string() }
    }
}

// ============================================================
// Part 3: AgentResult —— 包含Result/Option的复杂类型
// ============================================================

#[derive(Serialize, Deserialize, TS)]
#[ts(export)]
pub struct AgentResult {
    pub task_id: String,
    // Result<T, HarnessError> 在 TS 中映射为联合类型
    pub success: Option<String>,      // Some = 成功，None = 失败
    pub error: Option<HarnessError>,  // 有 error 时 success 必为 None
    pub logs: Vec<String>,
}

impl AgentResult {
    pub fn ok(task_id: &str, output: String) -> Self {
        AgentResult {
            task_id: task_id.to_string(),
            success: Some(output),
            error: None,
            logs: vec![],
        }
    }

    pub fn err(task_id: &str, e: HarnessError) -> Self {
        AgentResult {
            task_id: task_id.to_string(),
            success: None,
            error: Some(e),
            logs: vec![],
        }
    }
}
```

运行`cargo test`后，ts-rs自动生成`bindings/task.ts`：

```typescript
// bindings/task.ts —— 自动生成，不要手动修改

export type AgentPhase =
    | { phase: 'Idle' }
    | { phase: 'Planning'; plan: string }
    | { phase: 'Executing'; step: number; total: number }
    | { phase: 'WaitingForApproval'; message: string }
    | { phase: 'Completed'; output: string }
    | { phase: 'Failed'; error: string };

export interface Task {
    id: string;
    description: string;
    assigned_agent: string | null;
    phase: AgentPhase;
    created_at: number;
}

export interface ToolCall {
    tool_name: string;
    arguments: unknown;
    result: unknown | null;
    called_at: number;
}

export type HarnessError =
    | { kind: 'Timeout'; task_id: string; waited_secs: number }
    | { kind: 'InvalidToolCall'; reason: string; attempted: string }
    | { kind: 'PermissionDenied'; resource: string }
    | { kind: 'NetworkError'; message: string }
    | { kind: 'Internal'; detail: string };

export interface AgentResult {
    task_id: string;
    success: string | null;
    error: { kind: string; [key: string]: unknown } | null;
    logs: string[];
}
```

**关键映射规则：**
- `Option<T>` → `T | null`
- `Result<T, E>` → 语义映射为两个字段（`success: T | null` + `error: E | null`）
- `serde_json::Value` → `unknown`（TS端需要用Zod再做运行时验证）
- 枚举（带`tag`）→ TypeScriptdiscriminated union

---

## Step 2: Result映射 — Rust Result/Option → TS联合类型映射

### 为什么Result映射是难点

Rust的`Result<T, E>`是**代数数据类型**：它表达了"成功返回T或失败返回E"的**和类型**。TypeScript没有内建的Result类型，但可以用联合类型+接口语义模拟。关键是**映射策略的选择**——这又是SSOT问题的体现。

### 两种Result映射策略

#### 策略A：双字段模式（我们上面用的）

```rust
// Rust
pub struct AgentResult {
    pub success: Option<String>,      // Some = 成功时的值
    pub error: Option<HarnessError>,  // Some = 失败时的错误
}
```

```typescript
// TypeScript —— 双字段模式
interface AgentResult {
    success: string | null;  // 有值 = 成功，null = 失败
    error: HarnessError | null;  // 有值 = 失败，null = 成功
}
```

**优点：** 简单，TypeScript端容易理解
**缺点：** 语义上不是互斥的（理论上可以同时有值）

#### 策略B：Tagged Union模式（更类型安全）

```rust
// Rust —— 枚举比结构体更精确
#[derive(Serialize, Deserialize, TS)]
#[ts(export)]
#[serde(tag = "status")]
pub enum AgentOutcome {
    Success { output: String, logs: Vec<String> },
    Failure { error: HarnessError, logs: Vec<String> },
}
```

```typescript
// TypeScript —— discriminated union
type AgentOutcome =
    | { status: 'Success'; output: string; logs: string[] }
    | { status: 'Failure'; error: HarnessError; logs: string[] };
```

**优点：** 编译期强制互斥，更安全
**缺点：** 需要修改Rust结构体定义

### 完整映射对照表

| Rust类型 | TS映射 | 备注 |
|---------|--------|------|
| `Option<T>` | `T \| null` | |
| `Result<T, E>` (双字段) | `{ ok: T \| null, err: E \| null }` | 简单场景 |
| `Result<T, E>` (tagged) | `\| { ok: true, value: T } \| { ok: false, error: E }` | 互斥保证 |
| `Vec<T>` | `T[]` | |
| `HashMap<K, V>` | `Record<K, V>` | K必须是string |
| `Box<str>` | `string` | |
| `chrono::DateTime` | `string (ISO8601)` | 需要`chrono` feature |
| `uuid::Uuid` | `string` | 需要`uuid` feature |

---

## Step 3: SSOT实践 — GRT栈单点真实来源的完整代码

### 架构设计

在GRT栈中，我们选择**Rust作为SSOT**。理由：

1. Rust的类型系统最严格，定义时必须考虑所有权和生命周期
2. Rust编译期检查确保类型定义完整（所有字段都必须初始化或标注`#[serde(skip)]`）
3. ts-rs在测试阶段自动生成TS，无需人工同步

### 完整GRT栈类型对齐实现

#### Rust端：类型定义（SSOT）

```rust
// src/types/mod.rs —— 真实来源，Rust定义

pub mod agent {
    pub mod task {
        use serde::{Deserialize, Serialize};
        use ts_rs::TS;

        #[derive(Serialize, Deserialize, TS)]
        #[ts(export)]
        #[serde(tag = "type")]
        pub enum AgentType {
            Planner,
            Executor,
            Reviewer,
            Coordinator,
        }

        #[derive(Serialize, Deserialize, TS)]
        #[ts(export)]
        pub struct AgentConfig {
            pub name: String,
            pub agent_type: AgentType,
            pub max_retries: u32,
            pub timeout_secs: u64,
            pub tools: Vec<String>,
        }

        #[derive(Serialize, Deserialize, TS)]
        #[ts(export)]
        pub struct AgentState {
            pub id: String,
            pub config: AgentConfig,
            pub current_task: Option<String>,
            pub history: Vec<String>,  // Task ID历史
        }
    }

    pub mod execution {
        use serde::{Deserialize, Serialize};
        use ts_rs::TS;

        #[derive(Serialize, Deserialize, TS)]
        #[ts(export)]
        #[serde(tag = "status")]
        pub enum ExecutionStatus {
            Pending,
            Running { started_at: i64 },
            Completed { finished_at: i64, output: String },
            Failed { finished_at: i64, reason: String },
            Cancelled,
        }

        #[derive(Serialize, Deserialize, TS)]
        #[ts(export)]
        pub struct ExecutionPlan {
            pub plan_id: String,
            pub steps: Vec<ExecutionStep>,
            pub estimated_duration_secs: u64,
        }

        #[derive(Serialize, Deserialize, TS)]
        #[ts(export)]
        pub struct ExecutionStep {
            pub step_id: String,
            pub description: String,
            pub tool: Option<String>,
            pub dependencies: Vec<String>,  // 前置step_id列表
        }
    }
}

// 导出所有类型（供ts-rs生成）
pub fn export_types() {
    // 调用这个函数以触发ts-rs宏展开
    // 实际使用中不需要这个函数，宏在编译时展开
}
```

#### TypeScript端：自动生成的绑定

```typescript
// bindings/agent/task.ts —— 自动生成，版本控制中跟踪

export enum AgentType {
    Planner = "Planner",
    Executor = "Executor",
    Reviewer = "Reviewer",
    Coordinator = "Coordinator",
}

export interface AgentConfig {
    name: string;
    agent_type: AgentType;
    max_retries: number;
    timeout_secs: number;
    tools: string[];
}

export interface AgentState {
    id: string;
    config: AgentConfig;
    current_task: string | null;
    history: string[];
}
```

```typescript
// bindings/agent/execution.ts —— 自动生成

export type ExecutionStatus =
    | { status: 'Pending' }
    | { status: 'Running'; started_at: number }
    | { status: 'Completed'; finished_at: number; output: string }
    | { status: 'Failed'; finished_at: number; reason: string }
    | { status: 'Cancelled' };

export interface ExecutionPlan {
    plan_id: string;
    steps: ExecutionStep[];
    estimated_duration_secs: number;
}

export interface ExecutionStep {
    step_id: string;
    description: string;
    tool: string | null;
    dependencies: string[];
}
```

#### TypeScript端：运行时验证（Zod）

自动生成的类型只有**编译期**保障，没有**运行时**保障。跨网络边界的反序列化需要Zod兜底：

```typescript
// src/agent/validation.ts —— 运行时验证

import { z } from 'zod';
import type { AgentState, AgentConfig, ExecutionPlan, ExecutionStatus } from '../bindings/agent/task';

// Zod schema从TS类型自动推断（如果用zod-to-ts可以进一步自动化）
const AgentTypeSchema = z.enum(['Planner', 'Executor', 'Reviewer', 'Coordinator']);

const AgentConfigSchema = z.object({
    name: z.string(),
    agent_type: AgentTypeSchema,
    max_retries: z.number().int().min(0),
    timeout_secs: z.number().int().positive(),
    tools: z.array(z.string()),
});

const AgentStateSchema = z.object({
    id: z.string().uuid(),
    config: AgentConfigSchema,
    current_task: z.string().uuid().nullable(),
    history: z.array(z.string().uuid()),
});

// ExecutionStatus的discriminated union验证
const ExecutionStatusSchema = z.discriminatedUnion('status', [
    z.object({ status: z.literal('Pending') }),
    z.object({ status: z.literal('Running'), started_at: z.number().int() }),
    z.object({ status: z.literal('Completed'), finished_at: z.number().int(), output: z.string() }),
    z.object({ status: z.literal('Failed'), finished_at: z.number().int(), reason: z.string() }),
    z.object({ status: z.literal('Cancelled') }),
]);

const ExecutionStepSchema = z.object({
    step_id: z.string(),
    description: z.string(),
    tool: z.string().nullable(),
    dependencies: z.array(z.string()),
});

const ExecutionPlanSchema = z.object({
    plan_id: z.string().uuid(),
    steps: z.array(ExecutionStepSchema),
    estimated_duration_secs: z.number().int().positive(),
});

// 验证函数
export function validateAgentState(raw: unknown): AgentState {
    return AgentStateSchema.parse(raw);
}

export function validateExecutionPlan(raw: unknown): ExecutionPlan {
    return ExecutionPlanSchema.parse(raw);
}

export function validateExecutionStatus(raw: unknown): ExecutionStatus {
    return ExecutionStatusSchema.parse(raw);
}
```

#### Go端：类型映射

Go作为控制平面层，也需要接收这些类型。手动维护或用代码生成：

```go
// internal/types/agent.go —— Go端类型（从Rust手动同步，不推荐自动生成）

package types

// AgentType 对应 Rust 的 AgentType
type AgentType string

const (
    AgentTypePlanner     AgentType = "Planner"
    AgentTypeExecutor    AgentType = "Executor"
    AgentTypeReviewer    AgentType = "Reviewer"
    AgentTypeCoordinator AgentType = "Coordinator"
)

// AgentConfig 对应 Rust 的 AgentConfig
type AgentConfig struct {
    Name          string   `json:"name"`
    AgentType     AgentType `json:"agent_type"`
    MaxRetries    uint32   `json:"max_retries"`
    TimeoutSecs   uint64   `json:"timeout_secs"`
    Tools         []string `json:"tools"`
}

// AgentState 对应 Rust 的 AgentState
type AgentState struct {
    ID           string       `json:"id"`
    Config       AgentConfig  `json:"config"`
    CurrentTask  *string      `json:"current_task"`  // null → nil
    History      []string     `json:"history"`
}

// ExecutionStatus 对应 Rust 的 ExecutionStatus
type ExecutionStatus struct {
    Status string `json:"status"`  // discriminated union的tag
    // 条件字段（根据Status的值填充）
    StartedAt  *int64  `json:"started_at,omitempty"`
    FinishedAt *int64  `json:"finished_at,omitempty"`
    Output     *string `json:"output,omitempty"`
    Reason     *string `json:"reason,omitempty"`
}

// ExecutionPlan 对应 Rust 的 ExecutionPlan
type ExecutionPlan struct {
    PlanID                string          `json:"plan_id"`
    Steps                 []ExecutionStep `json:"steps"`
    EstimatedDurationSecs uint64          `json:"estimated_duration_secs"`
}

// ExecutionStep 对应 Rust 的 ExecutionStep
type ExecutionStep struct {
    StepID       string   `json:"step_id"`
    Description  string   `json:"description"`
    Tool         *string  `json:"tool"`  // null → nil
    Dependencies []string `json:"dependencies"`
}
```

### SSOT工作流

```
1. Rust工程师在 src/types/mod.rs 定义/修改类型
2. 运行 cargo test → ts-rs自动生成 bindings/agent/*.ts
3. Git提交 bindings/agent/*.ts（TS团队必须接受这些文件）
4. Go团队手动同步（或者未来用代码生成工具自动化）
```

**关键规则：**
- Rust是SSOT，所有其他语言的类型定义都是派生的
- `bindings/`目录下的`.ts`文件是自动生成的，**不要手动修改**
- 如果Rust工程师加了字段但TS没更新，TypeScript编译会报错（通过显式类型声明）
- Go团队需要自己维护对应的struct（目前是手动同步，未来可以加自动化）

---

## Step 4: 魔法时刻段落 — SSOT问题是政治问题

### 类型对齐的技术解法是成熟的

ts-rs和specta已经解决了技术问题：
- Rust结构体自动生成TypeScript接口
- 支持泛型、Option、Result、serde属性
- 编译期生成，无遗漏
- 可以集成到CI流程中

技术上有三种对齐路线：Rust生成TS、TS生成Rust、中立协议（Protobuf）。每种都能工作。

### 但SSOT问题是政治问题

然而，技术再先进，也无法解决以下问题：

**问题一：谁有权决定"这是真实来源"？**

如果Rust团队定义类型，TypeScript团队觉得Rust的命名不符合前端习惯，谁赢？反之亦然。组织内的权力结构决定真实来源，而不是技术本身。

**问题二：当真实来源变更时，谁来同步？**

Rust团队改了一个字段，TS团队必须跟着变——但如果TS团队在发布窗口期，拒绝同步怎么办？自动化工具只能减少人工错误，不能消除组织摩擦。

**问题三：跨组织时怎么办？**

如果你的API要暴露给第三方，第三方用什么语言？你无法要求他们也用Rust。Protobuf是妥协方案，但引入了额外复杂度。

### 魔法时刻的核心洞察

> SSOT问题在技术上永远有解（ts-rs、specta、Protobuf都能工作）。真正的难题是：**当两个团队对"谁定义、谁同步"没有共识时，最先进的工具也会失败。**
>
> 这不是技术问题，是组织问题。是政治问题。

技术解法是成熟的。政治共识是稀缺的。

---

## Step 5: 开放问题 — Bootstrap问题

### 谁来验证验证者？

我们构建了一套类型安全体系：Rust定义类型 → ts-rs生成TS → Zod运行时验证。但谁来验证Zod schema是否正确？谁能保证Zod schema和Rust类型真正一致？

这是一个递归问题：

- Rust类型是SSOT？→ 谁来验证Rust类型是正确的？
- Zod schema是运行时验证？→ 谁来验证Zod schema是正确的？
- 测试覆盖了所有分支？→ 谁来验证测试覆盖了所有分支？

### Bootstrap问题的具体场景

**场景一：Rust加了字段，TS忘了更新**

```rust
// Rust
#[derive(Serialize, Deserialize, TS)]
pub struct Task {
    pub id: String,
    pub description: String,
    pub new_field: String,  // 新加的
}
```

ts-rs会生成新的TS接口。但如果有其他地方显式声明了旧接口（没有用`import from bindings`），编译不会报错，但运行时可能出错。

**场景二：Zod schema和Rust语义不一致**

```rust
// Rust: max_retries 是 u32，范围 [0, 2^32-1]
pub struct AgentConfig {
    pub max_retries: u32,  // Rust允许任意u32值
}
```

```typescript
// TS: Zod schema可能限制了范围
const AgentConfigSchema = z.object({
    max_retries: z.number().int().min(0).max(10),  // 业务逻辑限制为0-10
});
```

Rust的类型系统不会报错（u32可以是任何值），但运行时Zod会拒绝>10的值。如果Rust没有对应的验证逻辑，这个差异会导致"合法的Rust值被TS拒绝"。

**场景三：枚举扩展导致TS switch遗漏分支**

```rust
// Rust加了一个新枚举变体
#[derive(TS)]
pub enum AgentType {
    Planner,
    Executor,
    Reviewer,
    Coordinator,
    NewRole,  // 新加的
}
```

TS的discriminated union自动更新，但如果TS代码有`switch (agentType.type)`，新变体会导致编译警告（如果用strict）或静默失败（如果不用strict）。

### 没有完美的答案

Bootstrap问题没有彻底的技术解法。只能缓解：

1. **类型生成+测试覆盖**：生成的类型要有测试验证
2. **CI强制检查**：如果TS编译警告新枚举分支未处理，不允许合并
3. **人工review**：最终还是要有人检查类型变更是否正确

但这些措施本身也需要验证。递归无穷无尽。

**开放问题：Bootstrap问题是否意味着完美的类型安全是不可能的？或者只有形式化验证（如TLA+、Coq）才能给出数学证明？**

---

## Step 6: 桥接语

- **承上：** 第五章的Rust类型状态模式解决了单Agent状态机的编译期约束，第六章的Go控制平面解决了多Agent调度与Context传播，但三个语言层之间的类型跨越网络边界时如何保持一致，是前三章没有回答的问题。

- **启下：** 编译器可以作为类型一致性的守护者——下一章将回答：编译器如何做判别？当Rust→TypeScript的类型映射出现不一致时，编译器能自动检测吗？还是需要人工review？

- **认知缺口：** 即使我们用了ts-rs实现了类型自动生成，Bootstrap问题依然存在：谁验证验证者本身？如果Zod schema写错了，类型安全体系的第一块多米诺骨牌就倒了。形式化验证能解决这个问题吗？

---

## 本章来源

### 一手来源

| 来源 | URL | 关键数据 |
|------|-----|---------|
| ts-rs官方文档 | https://github.com/Aleph-Alpha/ts-rs | Rust结构体自动生成TS类型声明，支持serde、泛型、Option/Result映射 |
| specta官方文档 | https://docs.rs/specta | TypeScript端类型导出Rust，支持chrono、uuid、serde等生态 |
| GRT栈架构 | p3.txt | Go + Rust + TypeScript三层职责划分，跨语言类型对齐方案 |
| VERT验证 | https://arxiv.org/2404.18852 | WASM oracle作为参考实现验证类型等价性 |

### 二手来源

| 来源 | 用途 |
|------|------|
| research-findings.md (Section 4.4) | ts-rs/specta工具对比 |
| research-findings.md (Section 6.2) | GRT栈架构对照 |
| p3.txt | 跨语言类型对齐完整方案 |
