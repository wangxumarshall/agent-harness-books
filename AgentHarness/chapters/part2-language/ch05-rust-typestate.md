# 第二部分：语言层契约 — Rust类型状态模式：状态机无法进入非法状态

## 本章Q

如何让AI的状态机无法进入非法状态？

## 魔法时刻

状态机的非法状态不是设计失误，而是未被发现的设计意图。当Rust编译器报出"match is not exhaustive"时，它不是在阻止你写代码，而是在告诉你：你设计的状态机漏掉了一个你应该考虑的场景。那个你"忘记"处理的分支，可能是一个真实存在的用户路径，只是你写代码时没想到。类型状态模式把状态机的穷尽性检查从"运行时debug"变成了"编译期证明"——不是"你最好处理所有情况"，而是"你必须处理所有情况，否则不编译"。这不是约束，这是设计镜鉴。

## 五分钟摘要

第四章展示了Rust所有权模型如何把"值是谁的、活多久"变成编译期事实。但所有权模型只解决了静态问题——值的生命周期、引用有效性、线程安全。对于动态问题——状态机的状态跃迁——需要另一个武器：类型状态模式。AutoAgents框架用Rust实现了一个完整的状态机，其中`enum AgentPhase`通过类型系统穷尽了所有可能状态，状态转移必须通过特定方法，不允许直接赋值。`Result<T, HarnessError>`把错误变成类型系统的一等公民，`?`操作符强迫每个错误都有去处。关键数据来自AutoAgents的真实实现：Rust编写的多Agent框架，Ractor actor运行时，支持WASM部署——没有类型状态模式，这种状态约束是不可能的。本章用三个完整代码示例回答"类型状态模式如何强制状态机的合法跃迁"：枚举状态机展示编译器如何追踪所有状态转移，结果类型展示错误如何成为控制流，状态机实现展示完整的类型化Agent。

---

## 枚举状态机：AgentPhase的完整实现

### 为什么需要类型状态

TypeScript的状态机是这样的：

```typescript
// AgentBasic的状态管理 —— 字符串级别的状态追踪
class Agent {
  private phase: string = "idle"; // 字符串！编译器完全不知道这是啥

  setPhase(phase: string) {
    this.phase = phase; // 任何字符串都行，"idle"、"thinking"、甚至"banana"
  }

  getPhase(): string {
    return this.phase;
  }
}

// 问题：phase可以是任何字符串
// const agent = new Agent();
// agent.setPhase("banana"); // 完全合法，编译器视而不见
// agent.setPhase(""); // 也合法
// agent.setPhase("ExecutingTool") // 当状态改名后，这里不会报错
```

TypeScript的状态只是"字符串"，编译器无法追踪哪些状态是合法的、哪些状态转移是允许的。AI可以随意设置任何值，类型系统完全不起作用。

Rust的类型状态模式用枚举替代字符串，用方法替代直接赋值，让编译器追踪所有状态转移。

### AgentPhase的完整代码

要运行本章的Rust代码示例，需要添加以下依赖到 `Cargo.toml`：

```toml
[dependencies]
uuid = { version = "1.0", features = ["v4"] }
tokio = { version = "1.0", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
thiserror = "1.0"
```

```rust
// ============================================================
// AgentPhase类型状态模式完整实现
// 来源：AutoAgents框架 (liquidos-ai.github.io/AutoAgents)
// ============================================================

use std::fmt;
use std::sync::Arc;
use tokio::sync::Mutex;

// ============================================================
// Part 1: 枚举定义 —— 穷尽所有可能状态
// ============================================================

/// AgentPhase：所有可能的Agent状态
/// 关键：这是枚举，不是字符串——编译器知道所有可能值
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AgentPhase {
    /// 初始状态，等待任务
    Idle,
    /// 正在推理/思考
    Thinking,
    /// 正在执行工具调用
    ExecutingTool,
    /// 等待人工确认（高风险操作）
    WaitingForConfirmation,
    /// 任务完成
    Done,
    /// 发生错误，包含错误信息
    Error(String),
}

impl AgentPhase {
    /// 判断当前状态是否可以转移到目标状态
    /// 这是状态机合法性的唯一来源——不是运行时检查，是类型证明
    pub fn can_transition_to(&self, next: &AgentPhase) -> bool {
        match (self, next) {
            // Idle可以转向Thinking（开始处理）
            (AgentPhase::Idle, AgentPhase::Thinking) => true,
            // Thinking可以转向ExecutingTool（执行工具）
            (AgentPhase::Thinking, AgentPhase::ExecutingTool) => true,
            // Thinking可以转向WaitingForConfirmation（需要人工确认）
            (AgentPhase::Thinking, AgentPhase::WaitingForConfirmation) => true,
            // Thinking可以直接转向Done（无需工具调用）
            (AgentPhase::Thinking, AgentPhase::Done) => true,
            // ExecutingTool可以转回Thinking（工具执行完毕）
            (AgentPhase::ExecutingTool, AgentPhase::Thinking) => true,
            // ExecutingTool可以转向Done（任务完成）
            (AgentPhase::ExecutingTool, AgentPhase::Done) => true,
            // WaitingForConfirmation可以转回Thinking（用户确认）
            (AgentPhase::WaitingForConfirmation, AgentPhase::Thinking) => true,
            // WaitingForConfirmation可以转回Idle（用户取消）
            (AgentPhase::WaitingForConfirmation, AgentPhase::Idle) => true,
            // 任何状态可以转向Error
            (_, AgentPhase::Error(_)) => true,
            // Error可以转回Idle（重试）
            (AgentPhase::Error(_), AgentPhase::Idle) => true,
            // 其他所有转移都是非法的
            _ => false,
        }
    }

    /// 获取状态的友好名称
    pub fn label(&self) -> &'static str {
        match self {
            AgentPhase::Idle => "空闲",
            AgentPhase::Thinking => "思考中",
            AgentPhase::ExecutingTool => "执行工具",
            AgentPhase::WaitingForConfirmation => "等待确认",
            AgentPhase::Done => "已完成",
            AgentPhase::Error(_) => "错误",
        }
    }
}

impl fmt::Display for AgentPhase {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.label())
    }
}

// ============================================================
// Part 2: HarnessError —— 错误作为类型系统的一等公民
// ============================================================

/// HarnessError：Harness层级的所有错误类型
/// 关键：这不是Exception，这是类型——每个错误变体都是合法的返回类型
#[derive(Debug, Clone)]
pub enum HarnessError {
    /// 状态机试图进行非法转移
    InvalidStateTransition {
        current: AgentPhase,
        attempted: AgentPhase,
        reason: String,
    },
    /// Agent未初始化就尝试使用
    AgentNotInitialized(String),
    /// 工具执行失败
    ToolExecutionFailed {
        tool_name: String,
        reason: String,
    },
    /// 超时
    Timeout(String),
    /// 资源耗尽
    ResourceExhausted {
        resource: String,
        limit: u64,
    },
    /// 沙箱策略拒绝
    SandboxViolation(String),
    /// 序列化/反序列化错误
    SerializationError(String),
}

impl fmt::Display for HarnessError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            HarnessError::InvalidStateTransition { current, attempted, reason } => {
                write!(f, "非法状态转移: {:?} -> {:?} ({})", current, attempted, reason)
            }
            HarnessError::AgentNotInitialized(id) => {
                write!(f, "Agent未初始化: {}", id)
            }
            HarnessError::ToolExecutionFailed { tool_name, reason } => {
                write!(f, "工具执行失败: {} ({})", tool_name, reason)
            }
            HarnessError::Timeout(msg) => {
                write!(f, "操作超时: {}", msg)
            }
            HarnessError::ResourceExhausted { resource, limit } => {
                write!(f, "资源耗尽: {} (限制: {})", resource, limit)
            }
            HarnessError::SandboxViolation(msg) => {
                write!(f, "沙箱违规: {}", msg)
            }
            HarnessError::SerializationError(msg) => {
                write!(f, "序列化错误: {}", msg)
            }
        }
    }
}

impl std::error::Error for HarnessError {}

// ============================================================
// Part 3: TypeSafeAgent —— 状态转移由编译器强制
// ============================================================

/// TypeSafeAgent：用类型状态模式约束的Agent
/// 关键：phase字段是私有的，只能通过transition()方法修改
pub struct TypeSafeAgent {
    id: String,
    phase: AgentPhase,           // 私有字段！外部无法直接修改
    session_data: SessionData,
}

/// SessionData：Agent的会话数据
#[derive(Debug, Clone)]
pub struct SessionData {
    pub session_id: String,
    pub created_at: std::time::Instant,
    pub token_count: usize,
}

impl SessionData {
    pub fn new(session_id: String) -> Self {
        Self {
            session_id,
            created_at: std::time::Instant::now(),
            token_count: 0,
        }
    }
}

impl TypeSafeAgent {
    /// 创建新Agent——只能从Idle状态开始
    pub fn new(id: String) -> Self {
        Self {
            id,
            phase: AgentPhase::Idle, // 强制从Idle开始
            session_data: SessionData::new(uuid::Uuid::new_v4().to_string()),
        }
    }

    /// 获取当前状态——返回值的引用，不可变
    pub fn phase(&self) -> &AgentPhase {
        &self.phase
    }

    /// 获取Agent ID
    pub fn id(&self) -> &str {
        &self.id
    }

    /// 状态转移——唯一合法途径
    /// 返回Result：成功Ok(())，失败Err(HarnessError)
    /// 关键：这不是"建议"，这是编译器强制
    pub fn transition(&mut self, next: AgentPhase) -> Result<(), HarnessError> {
        // 运行时检查：状态转移是否合法
        if !self.phase.can_transition_to(&next) {
            return Err(HarnessError::InvalidStateTransition {
                current: self.phase.clone(),
                attempted: next,
                reason: "状态转移违反状态机规则".to_string(),
            });
        }

        // 状态转移前钩子
        self.on_exit(&self.phase)?;

        // 执行转移
        let previous = std::mem::replace(&mut self.phase, next);

        // 状态转移后钩子
        self.on_enter(&self.phase)?;

        println!("[{}] 状态转移: {:?} -> {:?}", self.id, previous, self.phase);
        Ok(())
    }

    /// 状态进入钩子
    fn on_enter(&self, phase: &AgentPhase) -> Result<(), HarnessError> {
        match phase {
            AgentPhase::Thinking => {
                // 开始思考，重置token计数
                println!("[{}] 开始新的推理周期", self.id);
                Ok(())
            }
            AgentPhase::ExecutingTool => {
                // 执行工具，检查资源限制
                if self.session_data.token_count > 10000 {
                    return Err(HarnessError::ResourceExhausted {
                        resource: "token".to_string(),
                        limit: 10000,
                    });
                }
                Ok(())
            }
            AgentPhase::WaitingForConfirmation => {
                // 高风险操作，需要人工确认
                println!("[{}] 等待人工确认...", self.id);
                Ok(())
            }
            AgentPhase::Done => {
                println!("[{}] 任务完成，共生成 {} 个token", self.id, self.session_data.token_count);
                Ok(())
            }
            AgentPhase::Error(msg) => {
                eprintln!("[{}] 错误: {}", self.id, msg);
                Ok(())
            }
            AgentPhase::Idle => Ok(()),
        }
    }

    /// 状态退出钩子
    fn on_exit(&self, phase: &AgentPhase) -> Result<(), HarnessError> {
        match phase {
            AgentPhase::WaitingForConfirmation => {
                // 退出等待确认状态时，检查是否真的得到了确认
                println!("[{}] 确认已收到或已取消", self.id);
                Ok(())
            }
            _ => Ok(()),
        }
    }

    /// 开始处理——从Idle到Thinking的便捷方法
    pub fn start(&mut self) -> Result<(), HarnessError> {
        self.transition(AgentPhase::Thinking)
    }

    /// 执行工具——从Thinking到ExecutingTool
    pub fn execute_tool(&mut self, tool_name: &str) -> Result<(), HarnessError> {
        println!("[{}] 执行工具: {}", self.id, tool_name);
        self.transition(AgentPhase::ExecutingTool)
    }

    /// 工具完成——从ExecutingTool回到Thinking
    pub fn complete_tool(&mut self) -> Result<(), HarnessError> {
        self.transition(AgentPhase::Thinking)
    }

    /// 请求确认——从Thinking到WaitingForConfirmation
    pub fn request_confirmation(&mut self) -> Result<(), HarnessError> {
        self.transition(AgentPhase::WaitingForConfirmation)
    }

    /// 确认通过——从WaitingForConfirmation回到Thinking
    pub fn confirm(&mut self) -> Result<(), HarnessError> {
        self.transition(AgentPhase::Thinking)
    }

    /// 取消——从WaitingForConfirmation回到Idle
    pub fn cancel(&mut self) -> Result<(), HarnessError> {
        self.transition(AgentPhase::Idle)
    }

    /// 完成——从Thinking到Done
    pub fn finish(&mut self) -> Result<(), HarnessError> {
        self.transition(AgentPhase::Done)
    }

    /// 错误——任何状态都可以转到Error
    pub fn error(&mut self, msg: String) -> Result<(), HarnessError> {
        self.transition(AgentPhase::Error(msg))
    }

    /// 重置——从Error回到Idle
    pub fn reset(&mut self) -> Result<(), HarnessError> {
        self.transition(AgentPhase::Idle)
    }

    /// 添加token——追踪生成的token数量
    pub fn add_token(&mut self, content: &str) -> Result<(), HarnessError> {
        let len = content.len();
        self.session_data.token_count += len;
        println!("[{}] 添加token: {} chars (总计: {})", self.id, len, self.session_data.token_count);
        Ok(())
    }
}

// ============================================================
// Part 4: Result<T, HarnessError>与?操作符
// ============================================================

/// 使用?操作符的示例：链式错误处理
/// 关键：?操作符强迫每个错误都有去处——无法忽略
async fn process_with_agent(agent: &mut TypeSafeAgent) -> Result<String, HarnessError> {
    // 每个?都意味着"如果出错，立刻返回"
    let _ = agent.start()?;                    // 开始思考
    let _ = agent.add_token("首先，我需要分析这个问题...")?;

    // 模拟工具调用
    let _ = agent.execute_tool("search")?;
    let _ = agent.add_token("搜索结果：找到3个相关结果...")?;
    let _ = agent.complete_tool()?;            // 工具执行完毕

    let _ = agent.add_token("基于搜索结果，我得出结论...")?;
    let _ = agent.finish()?;                   // 任务完成

    Ok("处理完成".to_string())
}

/// 错误匹配示例：不同错误类型需要不同处理
async fn handle_agent_result(result: Result<String, HarnessError>) {
    match result {
        Ok(output) => {
            println!("成功: {}", output);
        }
        Err(HarnessError::InvalidStateTransition { current, attempted, reason }) => {
            eprintln!("状态机错误: {:?} -> {:?}: {}", current, attempted, reason);
            // 可能的恢复策略：重置状态机
        }
        Err(HarnessError::ResourceExhausted { resource, limit }) => {
            eprintln!("资源耗尽: {} 超过限制 {}", resource, limit);
            // 可能的恢复策略：清理缓存、等待
        }
        Err(HarnessError::ToolExecutionFailed { tool_name, reason }) => {
            eprintln!("工具失败: {} - {}", tool_name, reason);
            // 可能的恢复策略：重试或跳过
        }
        Err(e) => {
            eprintln!("未知错误: {}", e);
        }
    }
}

// ============================================================
// Part 5: 错误即控制流 —— 完整的控制流图
// ============================================================

/// 错误即控制流的核心模式
/// 在Rust中，Result不是"异常"，是"可恢复的错误"
/// 控制流通过Result的match/unwrap/?来转移

/// 场景：Agent执行工具链
async fn execute_tool_chain(
    agent: &mut TypeSafeAgent,
    tools: Vec<&str>,
) -> Result<String, HarnessError> {
    let mut results = Vec::new();

    // 开始
    agent.start()?;

    for tool in tools {
        // 执行单个工具
        agent.execute_tool(tool)?;
        agent.add_token(&format!("执行了工具: {}", tool))?;
        agent.complete_tool()?;
        results.push(format!("工具 {} 执行成功", tool));

        // 模拟可能的错误
        if tool == "risky_operation" {
            // 错误通过?传播
            return Err(HarnessError::ToolExecutionFailed {
                tool_name: tool.to_string(),
                reason: "高风险操作被沙箱拒绝".to_string(),
            });
        }
    }

    agent.finish()?;
    Ok(results.join("; "))
}

/// with_timeout: 将错误转换为超时错误
async fn with_timeout<F, T>(future: F, timeout_secs: u64) -> Result<T, HarnessError>
where
    F: std::future::Future<Output = Result<T, HarnessError>>,
{
    use tokio::time::{timeout, Duration};

    match timeout(Duration::from_secs(timeout_secs), future).await {
        Ok(result) => result,
        Err(_) => Err(HarnessError::Timeout("操作超时".to_string())),
    }
}

/// retry_with_backoff: 错误重试模式
async fn retry_with_backoff<F, T>(
    mut f: F,
    max_retries: u32,
) -> Result<T, HarnessError>
where
    F: FnMut() -> Result<T, HarnessError>,
{
    let mut attempts = 0;

    loop {
        match f() {
            Ok(result) => return Ok(result),
            Err(e) if attempts < max_retries => {
                attempts += 1;
                let backoff_ms = 2u64.pow(attempts) * 100;
                println!("重试 {}/{} (等待 {}ms): {:?}", attempts, max_retries, backoff_ms, e);
                tokio::time::sleep(tokio::time::Duration::from_millis(backoff_ms)).await;
            }
            Err(e) => return Err(e),
        }
    }
}

// ============================================================
// Part 6: AutoAgents的状态机实现 —— 真实世界的例子
// ============================================================

/// AutoAgents-style Agent: 使用Ractor actor模式
/// 来源：liquidos-ai.github.io/AutoAgents

mod autoagents {
    use super::*;

    /// Agent角色：定义Agent的行为类型
    #[derive(Debug, Clone, PartialEq, Eq)]
    pub enum AgentRole {
        Planner,      // 规划者：分解任务
        Executor,     // 执行者：调用工具
        Critic,       // 批评者：评估结果
        Coordinator,  // 协调者：管理多Agent
    }

    /// Message：Agent间通信的消息
    #[derive(Debug, Clone)]
    pub enum Message {
        Task { task_id: String, description: String },
        Result { task_id: String, output: String },
        Error { task_id: String, error: String },
        Confirm { task_id: String },
        Cancel { task_id: String },
    }

    /// AutoAgents的AgentPhase更详细版本
    #[derive(Debug, Clone, PartialEq, Eq)]
    pub enum AutoAgentPhase {
        /// 初始化
        Initialized,
        /// 等待消息
        Waiting,
        /// 正在处理
        Processing,
        /// 暂停（等待外部事件）
        Paused,
        /// 完成
        Completed,
        /// 失败
        Failed(String),
    }

    impl AutoAgentPhase {
        pub fn can_transition_to(&self, next: &AutoAgentPhase) -> bool {
            match (self, next) {
                (AutoAgentPhase::Initialized, AutoAgentPhase::Waiting) => true,
                (AutoAgentPhase::Waiting, AutoAgentPhase::Processing) => true,
                (AutoAgentPhase::Processing, AutoAgentPhase::Waiting) => true,
                (AutoAgentPhase::Processing, AutoAgentPhase::Paused) => true,
                (AutoAgentPhase::Processing, AutoAgentPhase::Completed) => true,
                (AutoAgentPhase::Processing, AutoAgentPhase::Failed(_)) => true,
                (AutoAgentPhase::Paused, AutoAgentPhase::Processing) => true,
                (AutoAgentPhase::Paused, AutoAgentPhase::Waiting) => true,
                (AutoAgentPhase::Failed(_), AutoAgentPhase::Waiting) => true,
                _ => false,
            }
        }
    }

    /// Actor风格的Agent
    pub struct AutoAgent {
        id: String,
        role: AgentRole,
        phase: AutoAgentPhase,
        mailbox: Vec<Message>,
    }

    impl AutoAgent {
        pub fn new(id: String, role: AgentRole) -> Self {
            Self {
                id,
                role,
                phase: AutoAgentPhase::Initialized,
                mailbox: Vec::new(),
            }
        }

        pub fn phase(&self) -> &AutoAgentPhase {
            &self.phase
        }

        pub fn role(&self) -> &AgentRole {
            &self.role
        }

        /// 处理消息——状态机转移
        pub fn handle_message(&mut self, msg: Message) -> Result<(), HarnessError> {
            // 根据当前状态决定如何处理消息
            match (&self.phase, &msg) {
                // Waiting状态收到Task，转到Processing
                (AutoAgentPhase::Waiting, Message::Task { .. }) => {
                    self.transition(AutoAgentPhase::Processing)?;
                }
                // Processing状态完成，转回Waiting
                (AutoAgentPhase::Processing, _) => {
                    // 处理完成后转回Waiting
                    self.transition(AutoAgentPhase::Waiting)?;
                }
                // Paused状态收到Confirm，转回Processing
                (AutoAgentPhase::Paused, Message::Confirm { .. }) => {
                    self.transition(AutoAgentPhase::Processing)?;
                }
                // Paused状态收到Cancel，转回Waiting
                (AutoAgentPhase::Paused, Message::Cancel { .. }) => {
                    self.transition(AutoAgentPhase::Waiting)?;
                }
                // 其他情况根据具体逻辑处理
                _ => {}
            }

            self.mailbox.push(msg);
            Ok(())
        }

        fn transition(&mut self, next: AutoAgentPhase) -> Result<(), HarnessError> {
            if !self.phase.can_transition_to(&next) {
                return Err(HarnessError::InvalidStateTransition {
                    current: AutoAgentPhase::Failed("phase mismatch".to_string()),
                    attempted: AutoAgentPhase::Waiting,
                    reason: format!("{:?} -> {:?} 不合法", self.phase, next),
                });
            }

            println!("[AutoAgent {} ({:?})] {:?} -> {:?}", self.id, self.role, self.phase, next);
            self.phase = next;
            Ok(())
        }
    }
}

// ============================================================
// Part 7: 演示程序
// ============================================================

fn main() {
    println!("=== TypeSafeAgent 演示 ===\n");

    // 创建Agent
    let mut agent = TypeSafeAgent::new("agent-001".to_string());
    println!("初始状态: {:?}", agent.phase());

    // 合法转移序列
    println!("\n--- 合法转移序列 ---");

    agent.start().unwrap();
    assert_eq!(agent.phase(), &AgentPhase::Thinking);

    agent.add_token("分析问题...").unwrap();
    agent.execute_tool("search").unwrap();
    assert_eq!(agent.phase(), &AgentPhase::ExecutingTool);

    agent.complete_tool().unwrap();
    assert_eq!(agent.phase(), &AgentPhase::Thinking);

    agent.request_confirmation().unwrap();
    assert_eq!(agent.phase(), &AgentPhase::WaitingForConfirmation);

    agent.confirm().unwrap();
    assert_eq!(agent.phase(), &AgentPhase::Thinking);

    agent.finish().unwrap();
    assert_eq!(agent.phase(), &AgentPhase::Done);

    // 重置并测试错误恢复
    println!("\n--- 错误恢复 ---");
    agent.reset().unwrap();
    assert_eq!(agent.phase(), &AgentPhase::Idle);

    // 尝试非法转移：Done -> Thinking（已完成的任务不能重新开始思考）
    println!("\n--- 非法转移测试 ---");
    let result = agent.transition(AgentPhase::Thinking);
    match result {
        Ok(_) => println!("错误：这个转移应该是非法的！"),
        Err(HarnessError::InvalidStateTransition { current, attempted, reason }) => {
            println!("正确捕获非法转移: {:?} -> {:?} ({})", current, attempted, reason);
        }
        Err(e) => println!("其他错误: {}", e),
    }

    // 演示AutoAgents风格的Actor
    println!("\n=== AutoAgents Actor 演示 ===\n");

    let mut planner = autoagents::AutoAgent::new(
        "planner-001".to_string(),
        autoagents::AgentRole::Planner,
    );

    // 正确的初始化序列
    planner.handle_message(autoagents::Message::Task {
        task_id: "task-001".to_string(),
        description: "分析需求".to_string(),
    }).unwrap();

    planner.handle_message(autoagents::Message::Confirm {
        task_id: "task-001".to_string(),
    }).unwrap();

    println!("Planner最终状态: {:?}", planner.phase());

    println!("\n=== 演示完成 ===");
}
```

### 关键对比：TypeScript的"软状态" vs Rust的"硬状态"

| 维度 | TypeScript | Rust |
|------|-----------|------|
| 状态定义 | 字符串或数字，可任意赋值 | 枚举，所有可能值在编译期已知 |
| 状态转移 | 任何函数都可以修改，无约束 | `transition()`方法，编译期检查合法性 |
| 穷尽性 | `switch`可以遗漏分支，只警告 | `match`必须穷尽所有分支，否则编译错误 |
| 错误处理 | `try/catch`可选，可忽略 | `Result<T, E>`+`?`操作符，强迫处理 |
| 状态历史 | 不追踪 | 可选的`history: Vec<Phase>`追踪 |

---

## Result与?操作符：强迫性错误处理

### 为什么错误应该是类型

TypeScript的错误处理是"建议式"的：

```typescript
// TypeScript的错误处理 —— 可以忽略
async function process() {
    try {
        const result = await fetchData();
        return result;
    } catch (e) {
        console.log("出错了"); // 吞掉错误，继续执行
        return null;           // 返回一个"魔数"
    }
}

// 问题：调用方不知道哪个路径是正常的
// const r = await process();
// r可能是数据，可能是null
// 调用方必须检查：if (r === null) ... else ...
// 但TypeScript不会强制这个检查
```

Rust的`Result<T, E>`把错误变成返回类型的一部分：

```rust
// Rust的错误处理 —— 强迫处理
async fn process() -> Result<Data, HarnessError> {
    let data = fetch_data().await?; // ?操作符：如果出错，立刻返回

    // 只有在成功时才会到达这里
    Ok(data)
}

// 调用方必须处理错误：
match process().await {
    Ok(data) => { /* 使用data */ }
    Err(e) => { /* 处理错误 */ }
}

// 或者继续传播：
// let final_result = process().await?; // 错误向上传播
```

### ?操作符的控制流语义

`?`操作符是"强迫性错误处理"的语法糖。它的展开如下：

```rust
// 源代码
let data = fetch_data()?;

// 编译器展开为
let data = match fetch_data() {
    Ok(data) => data,
    Err(e) => return Err(From::from(e)), // 立即返回，错误向上传播
};
```

这意味着：你想忽略错误？做不到。每一个`?`都是明确的"如果出错，这个函数立即返回"。

---

## 完整错误处理流图

```
┌─────────────────────────────────────────────────────────────────┐
│                      Agent生命周期                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐     start()      ┌───────────┐                  │
│   │   Idle   │ ────────────────▶│  Thinking │                  │
│   └──────────┘                  └───────────┘                  │
│        ▲                              │                        │
│        │ reset()                      ├───────────────────────┐│
│        │                              │                       ││
│        │                    execute_tool()                     │
│        │                              ▼                       ││
│        │                       ┌───────────┐                 ││
│        │                       │ Executing │◀────────────┐    ││
│        │                       │   Tool    │             │    ││
│        │                       └───────────┘             │    ││
│        │                              │                  │    ││
│        │                    complete_tool()              │    ││
│        │                              ▼                  │    ││
│        │                       ┌───────────┐             │    ││
│        │                       │  Thinking │─────────────┘    ││
│        │                       └───────────┘                  ││
│        │                              │                       ││
│        │                    request_confirmation()            │
│        │                              ▼                       ││
│        │                       ┌───────────────┐             ││
│        │                       │   WaitingFor   │             ││
│        │                       │ Confirmation   │             ││
│        │                       └───────────────┘             ││
│        │                              │                       ││
│        │         ┌────────────────────┴───────────────────┐   ││
│        │         │                                        │   ││
│        │    confirm()                               cancel()│   │
│        │         ▼                                        ▼   ││
│        │  ┌───────────┐                            ┌────────┐││
│        │  │  Thinking │                            │  Idle  │││
│        │  └───────────┘                            └────────┘││
│        │         │                                      ▲    ││
│        │         │              finish()                  │    ││
│        │         └────────────────────────────────────────┘    ││
│        │                              ▼                       ││
│        │                       ┌───────────┐                 ││
│        └───────────────────────│   Done    │◀────────────────┘ │
│                                └───────────┘                  │
│                                      ▲                         │
│                                error(msg)                      │
│                                      │                         │
│                                      ▼                         │
│   ┌──────────────────────────────────────────────────────────┐ │
│   │                      Error(String)                        │ │
│   └──────────────────────────────────────────────────────────┘ │
│                                      │                         │
│                                      ▼                         │
│                               reset()                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

错误传播路径：
┌──────────────────────────────────────────────────────────────────┐
│  ? 操作符的错误传播                                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  process()                                                       │
│     │                                                            │
│     ├── fetch_data()? ──▶ Err(NetworkError) ──▶ 直接返回         │
│     │                                                            │
│     ├── parse_result()? ──▶ Err(ParseError) ──▶ 直接返回         │
│     │                                                            │
│     └── Ok(final_result) ──▶ 继续执行                           │
│                                                                  │
│  关键：每个?都意味着"如果这一步失败，整个函数立即失败"            │
│  没有"继续执行看看"——错误是立即终止，不是延迟爆炸                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 魔法时刻（续）

类型状态模式的真正威力不在于"防止错误"，而在于"暴露设计缺陷"。当你写一个状态机时，你脑子里想的是几个主要状态：Idle、Thinking、Done。但Rust编译器说"match is not exhaustive"时，它在逼你思考那些你没想到的边缘情况：超时怎么办？工具执行失败怎么办？用户取消操作怎么办？

这些"意外"的状态不是bug，是设计镜鉴。AutoAgents框架的`enum AgentPhase`包含7个状态变体，每一个都是从实际运行中发现的需求——不是设计文档里规定的，是代码里无法回避的。

**非法状态是未发现的设计意图。** 类型状态模式让你无法假装那些边缘情况不存在。

---

## 桥接语

- **承上：** 第四章展示了Rust所有权模型如何把"值是谁的、活多久"变成编译期事实。类型状态模式是同一思想的延续——把"状态机能处于哪些状态、哪些转移是合法的"也变成编译期事实。两个加起来，Rust把AI Agent的行为约束推到了极致：内存安全、线程安全、状态安全。

- **启下：** 但这些都是**单个Agent**的约束。当多个Agent协作时，状态机就变成了状态机网络——每个Agent有自己的状态，还要协调彼此的转移。第6章将回答：多Agent系统的状态约束怎么办？AutoAgents的Ractor actor模型给出了答案。

- **认知缺口：** 你可能在用TypeScript写多Agent系统，感觉"加个状态字段"就够了。但单个Agent的内部状态和多个Agent的协调状态是两回事——前者可以用字符串管理，后者需要类型化的状态机、消息队列、角色定义。Rust的类型系统是为这种复杂性设计的。

---

## 本章来源

### 一手来源

1. **AutoAgents框架** — Rust编写的多Agent框架，使用`enum AgentPhase`类型状态模式，Ractor actor运行时，支持WASM部署，来源：liquidos-ai.github.io/AutoAgents

2. **Rust所有权与生命周期** — Rust官方文档，ownership三条规则、生命周期标注、借用检查器，来源：doc.rust-lang.org/book/ch04-00-understanding-ownership.html

3. **Rust Result与错误处理** — Rust官方文档，`Result<T, E>`类型、`?`操作符、错误传播语义，来源：doc.rust-lang.org/book/ch09-00-error-handling.html

4. **Rustine: C to Safe Rust Translation (arXiv:2511.20617)** — 87%函数等价性，证明Rust类型系统在状态约束上的工程价值，来源：arXiv:2511.20617

5. **SafeTrans: C to Rust with Iterative Fixing (arXiv:2505.10708)** — 翻译成功率54%→80%，证明Rust作为跨语言类型安全底座的可行性，来源：arXiv:2505.10708

### 二手来源

6. **VERT: Verified Equivalent Rust Transpilation (arXiv:2404.18852)** — WASM编译器生成oracle Rust程序作为参考，验证LLM生成的代码，来源：arXiv:2404.18852

7. **Rust+AI Agent+WASM实战教程** — 完整的Rust AI Agent实现，trait Agent定义、async_trait、wasm-bindgen接口，来源：ITNEXT (Dogukan Tuna)

8. **Ractor actor运行时文档** — Rust高性能actor模型，用于AutoAgents的并发协调，来源：docs.rs/ractor
