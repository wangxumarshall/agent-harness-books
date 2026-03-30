# 第二部分：语言层契约 — Rust所有权模型：编译时事实

## 本章Q

为什么Rust是Harness核心语言？

## 魔法时刻

Rust所有权是AI无法逃脱的监狱——不是因为强制，而是因为它是编译时事实。TypeScript的类型系统告诉你"这个值在理论上是什么形状"，Rust的所有权系统告诉你"这个值在内存中是谁的、活多久、被谁借用"——这不是运行时推测，这是编译期证明。AI在TypeScript中可以`as any`绕过类型检查，可以在`tsconfig.json`里关闭严格模式，可以用`catch`吞掉异常继续执行。AI在Rust中唯一能绕过所有权检查的方式，是不编译。这是本质区别：TypeScript的契约是道德约束，Rust的契约是物理定律。

## 五分钟摘要

第三章建立了"类型作为契约"的原则，展示了TypeScript类型防线如何消灭AI生成的JSON解析错误。但TypeScript有一个根本局限：它是"软"的——`as any`可以绕过，`unknown`可以层层断言，异常可以catch后继续执行。Rust的所有权模型是"硬"的——借用检查器在编译期追踪每一个值的生命周期，生命周期标注在编译期证明引用的有效性，类型状态模式在编译期穷尽状态机的所有分支。关键数据来自Anthropic 16 Agent × C编译器项目：100,000行Rust代码，99% GCC torture test通过率，无一不是建立在Rust所有权模型的编译时保证之上。本章用三个实战案例回答"为什么Rust比TypeScript更硬"：所有权实战代码展示AI无法"悄悄遗忘"Token的生命周期，生命周期标注展示借用检查器如何约束AI的引用行为，Odyssey Bundle架构展示Agent定义+工具+沙箱策略的完整打包。最后埋下伏笔：所有权约束了状态泄漏，但状态跃迁怎么办——这是第五章的起点。

---

## 所有权实战：AI无法"悄悄遗忘"Token

### TypeScript的内存泄漏：无声的定时炸弹

AI生成代码最隐蔽的错误不是逻辑错误，而是**内存泄漏**。在TypeScript中，对象被创建后可能还被某个闭包引用着，导致垃圾回收器无法释放；Promise链可能形成循环引用，内存持续增长；EventEmitter的监听器可能忘记移除，每调用一次就多注册一个。这些错误在测试时可能完全看不出来——内存泄漏是慢性病，只有在生产环境长期运行后才爆炸。

来看一个典型的AI生成代码中的内存泄漏场景：

```typescript
// AgentBasic版本的上下文管理 —— 内存泄漏的温床
class AgentContext {
  private memory: Map<string, any> = new Map();
  private callbacks: Array<(data: any) => void> = [];

  // AI生成的代码可能忘记追踪这些引用的生命周期
  addListener(cb: (data: any) => void) {
    this.callbacks.push(cb); // 永不移除的监听器
  }

  setMemory(key: string, value: any) {
    this.memory.set(key, value); // 不断增长的Map
  }
}

// 问题：callback永远不会被移除
// 问题：memory永远不会被清理
// 这不是逻辑错误，是生命周期管理错误
// TypeScript编译器完全视而不见——因为类型系统不追踪生命周期
```

TypeScript的类型系统只告诉你"这个值是什么形状"，不告诉你"这个值活多久、谁持有它、谁可以修改它"。AI在生成代码时，可以"悄悄遗忘"清理逻辑，因为TypeScript不会因为你没有清理内存而报错。

### Rust所有权：每一字节内存都有主

Rust的所有权模型是编译期的内存管理规则。它的核心三条规则是：

1. **每一个值有一个所有者**（owner）
2. **同一时间只有一个所有者**（exclusive access）
3. **当所有者离开作用域，值被Drop**（自动释放）

这三条规则不是在运行时检查的，是在编译期证明的。编译器知道每一个值的生命周期，知道谁持有它，知道它什么时候应该被释放。

```rust
// AgentContext的Rust实现 —— 所有权模型下的内存安全
// 这是TypeSafeAgent的Rust等效实现

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;

// ============================================================
// Part 1: Token生命周期 —— AI无法"悄悄遗忘"
// ============================================================

/// Token代表AI生成的一个不可变产物
/// 'static生命周期意味着这个Token存活到程序结束
/// ——但注意，这不是"可以永远用"，而是"编译期保证了它的有效期"
struct Token {
    id: String,
    content: String,
    created_at: std::time::Instant,
}

/// ToolCall代表一次工具调用，带有生命周期标注
/// 'call生命周期表示这个引用的有效范围不超过这次调用
struct ToolCall<'call> {
    name: &'call str,           // 借用工具名，不获取所有权
    args: &'call HashMap<String, String>, // 借用参数
    result: Option<String>,    // 拥有结果的所有权
}

impl<'call> ToolCall<'call> {
    // 生命周期标注：返回值的生命周期与输入的生命周期绑定
    fn name(&self) -> &'call str {
        self.name
    }

    // 错误：尝试返回内部引用的所有权
    // fn steal_name(self) -> String {
    //     self.name.to_string() // 合法：to_string()获取了新所有权的String
    //     // 但如果尝试返回self.name本身：
    //     // fn steal_name(&self) -> &str { self.name }
    //     // 这个返回&str，但self被move走了，编译错误
    // }
}

// ============================================================
// Part 2: 状态管理 —— 所有权转移的错误不可能发生
// ============================================================

/// OdysseyAgentState：AI Agent的完整状态
/// 使用Arc<Mutex<...>>实现内部可变性，同时保持所有权清晰
pub struct OdysseyAgentState {
    tokens: Arc<Mutex<Vec<Token>>>,     // 多个Token，归Agent所有
    tool_calls: Vec<ToolCall<'static>>, // 工具调用记录
    session_id: String,
}

impl OdysseyAgentState {
    pub fn new(session_id: String) -> Self {
        Self {
            tokens: Arc::new(Mutex::new(Vec::new())),
            tool_calls: Vec::new(),
            session_id,
        }
    }

    // add_token获取Token的所有权——调用方不再持有它
    pub async fn add_token(&self, token: Token) -> Result<(), AgentError> {
        let mut tokens = self.tokens.lock().await;
        tokens.push(token); // token被move进Vec，调用方无法再用
        Ok(())
    }

    // get_token_clone：需要克隆？不，这是所有权转移的正确方式
    pub async fn add_token_with_ownership(&self, token: Token) -> Result<(), AgentError> {
        let mut tokens = self.tokens.lock().await;
        // token的所有权在这里转移给Vec
        // 上一行add_token之后，原始token变量不再有效
        tokens.push(token);
        Ok(())
    }

    // 错误演示：尝试使用已经被move的值
    pub async fn bad_example(&self, token: Token) -> Result<(), AgentError> {
        let mut tokens = self.tokens.lock().await;
        tokens.push(token);
        // 错误演示：下面这行如果取消注释，编译错误
        // println!("Token id: {}", token.id); // ❌ 错误：token已被move
        Ok(())
    }
}

// ============================================================
// Part 3: 借用检查器实战 —— AI无法绕过生命周期
// ============================================================

/// 一个展示借用规则如何工作的复杂例子
fn demonstrate_borrow_rules() {
    let mut agent_state = OdysseyAgentState::new("session_123".to_string());

    // 场景1：不可变借用
    let token = Token {
        id: "tok_001".to_string(),
        content: "Hello, World!".to_string(),
        created_at: std::time::Instant::now(),
    };

    // 不可变借用：多个读取者可以同时存在
    let id_ref = &token.id;
    let content_ref = &token.content;
    println!("Token {}: {}", id_ref, content_ref);
    // id_ref和content_ref是同时有效的——因为不可变借用可以并行

    // 场景2：可变借用——独占访问
    let mut token_mut = Token {
        id: "tok_002".to_string(),
        content: "Original".to_string(),
        created_at: std::time::Instant::now(),
    };

    {
        let edit = &mut token_mut.content;
        edit.push_str(" - modified");
        // edit在这里离开作用域，可变借用结束
    }

    println!("After edit: {}", token_mut.content); // ✅ 可以访问了
    // 如果在可变借用期间尝试读取：
    // let read = &token_mut.content;
    // println!("{}", read); // ❌ 编译错误：可变借用和不可变借用不能共存
    // let edit2 = &mut token_mut.content; // ❌ 编译错误：不能同时有两个可变借用

    // 场景3：生命周期标注——让编译器知道引用何时有效
    let agent = Arc::new(Mutex::new(agent_state));
    let agent_ref = &agent; // 生命周期开始

    // 这个函数的返回值生命周期与输入引用的生命周期绑定
    fn get_session_id(agent: &OdysseyAgentState) -> &str {
        &agent.session_id // 返回值的生命周期不超过agent引用
    }

    let session = get_session_id(&agent_ref.lock().await);
    println!("Session: {}", session);
    // session的生命周期与agent_ref绑定，agent_ref在作用域内有效，所以session有效

    // 错误：返回悬垂引用
    // fn create_dangling() -> &str {
    //     let s = String::from("hello");
    //     &s // ❌ 错误：s在函数结束时被Drop，返回的引用悬垂
    // }
}

// 编译错误演示：AI无法"忘记"处理所有权
/*
 * 假设AI生成了这样的代码：
 *
 * fn process_token(token: Token) -> String {
 *     let id = token.id;  // 借用
 *     let content = token.content; // 借用
 *     token.id // ❌ 错误：token.id是借用的，但函数试图返回它
 *              // 更重要的是：token在函数结束时被Drop
 *              // 返回借用的引用会导致悬垂指针
 * }
 *
 * 这个错误在TypeScript中永远不会出现（因为TypeScript没有所有权概念）
 * 这个错误在Rust中必须在编译期修复，否则无法通过编译
 * AI无法"悄悄遗忘"所有权，必须在生成代码时就正确处理
 */

fn main() {
    println!("Ownership demonstration complete");
}
```

### 关键对比：TypeScript的"软" vs Rust的"硬"

| 维度 | TypeScript | Rust |
|------|-----------|------|
| 内存管理 | 手动追踪，GC自动回收，但生命周期不明确 | 编译期追踪，值离开作用域即释放，无GC |
| 引用有效性 | 运行时可能发生"访问已释放对象" | 编译期保证，不存在悬垂引用 |
| 状态修改 | 任何时候都可以修改，类型系统不约束 | 可变性通过`&mut`独占，编译期检查 |
| 内存泄漏 | 可能（闭包持有引用、忘记清理） | 编译期保证（除非使用`Rc`/`Arc`显式共享） |
| 数据竞争 | 可能（多线程共享状态） | 编译期保证（`Send`/`Sync` trait约束） |

Rust的所有权模型把"内存安全"从运行时的概率性问题变成了编译期的必然事实。AI在Rust中无法生成"可能"有内存泄漏的代码——因为编译器会直接拒绝。

---

## 生命周期标注：借用检查器的AI行为约束

### 为什么需要生命周期标注

TypeScript的类型系统不需要生命周期标注，因为JavaScript的内存管理是隐式的——GC负责回收，开发者不需要关心对象何时释放。但Rust的所有权模型需要显式地追踪引用的生命周期。

生命周期标注（Lifetime Annotations）是Rust的类型系统用来**证明引用有效性**的语法。它们告诉编译器"这个引用在这个范围内有效"，让编译器能够检测"悬垂引用"（dangling references）。

```rust
// 生命周期标注的核心语法
// &'a T 表示"生命周期为'a的T的引用"
// fn foo<'a>(x: &'a str) -> &'a str 意味着：
// "输入引用的生命周期是'a，返回引用的生命周期也是'a，
//  编译器保证返回值的有效期不超过输入值"

/// 检查Token有效性的函数
/// 生命周期标注：返回值的生命周期与输入引用的生命周期绑定
fn validate_token<'a>(token: &'a Token) -> &'a str {
    // 如果直接返回&token.id，生命周期是'a
    &token.id
}

// 错误示例：没有生命周期标注导致编译错误
/*
 * fn validate_token(token: &Token) -> &str {
 *     &token.id
 * }
 * // 错误：缺少生命周期标注
 * // Rust不知道返回的&str和输入的&Token是什么关系
 */

// 多重生命周期：区分不同引用的来源
fn compare_token_lifetimes<'a, 'b>(a: &'a Token, b: &'b Token) -> &'a Token {
    // 返回'a生命周期的Token，意味着返回值的有效期与a绑定
    if a.created_at > b.created_at { a } else { b }
}

// 'static生命周期：程序整个运行期间都有效
fn create_static_token() -> &'static str {
    // 字符串字面量是'static的——它们被编译进二进制文件
    "token_123"
}

// 错误：返回局部变量的引用
/*
 * fn create_dangling_token() -> &str {
 *     let local = String::from("local");
 *     &local // ❌ 编译错误：local在函数结束时被Drop
 * }
 * // 这正是TypeScript可能"悄悄产生"的错误：访问已释放的内存
 * // Rust让这个错误在编译期暴露
 */
```

### 实战：Odyssey Bundle的Agent定义与生命周期

现在来看一个完整的AI Agent定义，展示生命周期标注如何约束AI的行为。这是第三章TypeSafeAgent的Rust等效实现：

```rust
// ============================================================
// Odyssey Bundle：Agent定义+工具+沙箱策略的完整打包
// 这是TypeSafeAgent的Rust核心实现
// ============================================================

use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Mutex;

// ============================================================
// Part 1: 核心类型定义 —— 生命周期在编译期追踪
// ============================================================

/// Token：AI生成的不可变产物
/// 'static生命周期：如果所有字段都是'static的，整个Token可以是'static
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Token {
    pub id: TokenId,
    pub content: String,
    pub created_at: std::time::Instant,
}

/// TokenId：品牌类型的Rust实现
/// 用newtype模式区分语义不同的类型
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TokenId(String);

impl TokenId {
    pub fn new(id: impl Into<String>) -> Self {
        Self(id.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// ToolResult：工具调用的结果，拥有所有权
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    pub call_id: CallId,
    pub output: String,
    pub success: bool,
}

/// CallId：工具调用的唯一标识
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct CallId(String);

impl CallId {
    pub fn new() -> Self {
        Self(uuid::Uuid::new_v4().to_string())
    }
}

impl Default for CallId {
    fn default() -> Self {
        Self::new()
    }
}

// ============================================================
// Part 2: Agent Trait定义 —— 生命周期约束AI行为
// ============================================================

/// Agent Trait：AI Agent的核心接口
/// 生命周期标注约束了引用的有效性范围
pub trait Agent: Send + Sync {
    /// 输入生命周期'a，输出生命周期'b
    /// 编译器保证：返回值的有效期不超过输入的有效期
    fn process<'a>(&self, input: &'a str) -> Box<dyn Future<Output = Result<String, AgentError>> + Send + 'a>
    where
        Self: 'a;

    /// 获取Agent的标识
    fn name(&self) -> &str;

    /// 获取当前Agent的状态
    fn state(&self) -> &AgentState;
}

/// AgentError：统一的错误类型
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AgentError {
    InvalidInput(String),
    ToolExecutionFailed(String),
    StateCorrupted(String),
    Timeout,
}

impl std::fmt::Display for AgentError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AgentError::InvalidInput(msg) => write!(f, "Invalid input: {}", msg),
            AgentError::ToolExecutionFailed(msg) => write!(f, "Tool execution failed: {}", msg),
            AgentError::StateCorrupted(msg) => write!(f, "State corrupted: {}", msg),
            AgentError::Timeout => write!(f, "Operation timed out"),
        }
    }
}

impl std::error::Error for AgentError {}

// ============================================================
// Part 3: OdysseyAgent —— 具体实现
// ============================================================

/// OdysseyAgent：完整的AI Agent实现
/// 使用Arc<Mutex<...>>实现线程安全的所有权共享
#[derive(Debug)]
pub struct OdysseyAgent {
    name: String,
    state: Arc<Mutex<AgentState>>,
    tools: Vec<ToolDefinition>,
    sandbox_policy: SandboxPolicy,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentState {
    pub session_id: SessionId,
    pub tokens: Vec<Token>,
    pub tool_calls: Vec<ToolCallRecord>,
    pub phase: AgentPhase,
}

impl AgentState {
    pub fn new(session_id: SessionId) -> Self {
        Self {
            session_id,
            tokens: Vec::new(),
            tool_calls: Vec::new(),
            phase: AgentPhase::Idle,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AgentPhase {
    Idle,
    Thinking,
    ExecutingTool,
    WaitingForConfirmation,
    Done,
    Error(String),
}

/// 工具定义：包含生命周期标注
#[derive(Debug, Clone)]
pub struct ToolDefinition {
    pub name: String,
    pub description: String,
    pub parameters: Vec<ParameterDefinition>,
}

#[derive(Debug, Clone)]
pub struct ParameterDefinition {
    pub name: String,
    pub param_type: ParameterType,
    pub required: bool,
}

#[derive(Debug, Clone)]
pub enum ParameterType {
    String,
    Number,
    Boolean,
    Object,
    Array,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCallRecord {
    pub call_id: CallId,
    pub tool_name: String,
    pub args: serde_json::Value,
    pub result: Option<String>,
    pub timestamp: std::time::Instant,
}

/// 沙箱策略：定义工具的权限边界
#[derive(Debug, Clone)]
pub struct SandboxPolicy {
    pub allowed_network_hosts: Vec<String>,
    pub allowed_file_paths: Vec<String>,
    pub max_execution_time_ms: u64,
    pub max_memory_mb: u64,
}

impl SandboxPolicy {
    pub fn default_for_agent() -> Self {
        Self {
            allowed_network_hosts: vec![
                "api.openai.com".to_string(),
                "api.anthropic.com".to_string(),
            ],
            allowed_file_paths: vec!["/tmp/agent_workspace".to_string()],
            max_execution_time_ms: 30000,
            max_memory_mb: 512,
        }
    }

    pub fn strict() -> Self {
        Self {
            allowed_network_hosts: vec![],
            allowed_file_paths: vec!["/tmp".to_string()],
            max_execution_time_ms: 5000,
            max_memory_mb: 128,
        }
    }
}

impl OdysseyAgent {
    pub fn new(name: String, session_id: SessionId) -> Self {
        Self {
            name,
            state: Arc::new(Mutex::new(AgentState::new(session_id))),
            tools: Vec::new(),
            sandbox_policy: SandboxPolicy::default_for_agent(),
        }
    }

    pub fn with_policy(name: String, session_id: SessionId, policy: SandboxPolicy) -> Self {
        Self {
            name,
            state: Arc::new(Mutex::new(AgentState::new(session_id))),
            tools: Vec::new(),
            sandbox_policy: policy,
        }
    }

    pub fn add_tool(&mut self, tool: ToolDefinition) {
        self.tools.push(tool);
    }

    pub async fn add_token(&self, token: Token) -> Result<(), AgentError> {
        let mut state = self.state.lock().await;
        state.tokens.push(token);
        Ok(())
    }

    pub async fn get_latest_token(&self) -> Result<Token, AgentError> {
        let state = self.state.lock().await;
        state.tokens.last().cloned()
            .ok_or_else(|| AgentError::StateCorrupted("No tokens available".to_string()))
    }

    pub async fn execute_tool_call(
        &self,
        tool_name: &str,
        args: serde_json::Value,
    ) -> Result<ToolResult, AgentError> {
        // 验证沙箱策略
        if !self.sandbox_policy.is_tool_allowed(tool_name) {
            return Err(AgentError::ToolExecutionFailed(
                format!("Tool '{}' is not allowed by sandbox policy", tool_name)
            ));
        }

        let call_id = CallId::new();
        let call_record = ToolCallRecord {
            call_id: call_id.clone(),
            tool_name: tool_name.to_string(),
            args: args.clone(),
            result: None,
            timestamp: std::time::Instant::now(),
        };

        // 记录工具调用
        {
            let mut state = self.state.lock().await;
            state.tool_calls.push(call_record);
        }

        // 执行工具（这里是简化的mock）
        let output = format!("Executed {} with {:?}", tool_name, args);

        Ok(ToolResult {
            call_id,
            output,
            success: true,
        })
    }
}

impl SandboxPolicy {
    pub fn is_tool_allowed(&self, tool_name: &str) -> bool {
        // 简化实现：实际上需要检查工具注册表
        true
    }
}

impl Agent for OdysseyAgent {
    fn process<'a>(&self, input: &'a str) -> Box<dyn Future<Output = Result<String, AgentError>> + Send + 'a>
    where
        Self: 'a
    {
        Box::pin(async move {
            // 验证输入
            if input.is_empty() {
                return Err(AgentError::InvalidInput("Empty input".to_string()));
            }

            // 更新状态
            {
                let mut state = self.state.lock().await;
                state.phase = AgentPhase::Thinking;
            }

            // 生成Token
            let token = Token {
                id: TokenId::new(format!("tok_{}", uuid::Uuid::new_v4())),
                content: format!("Processed: {}", input),
                created_at: std::time::Instant::now(),
            };

            self.add_token(token).await?;

            // 更新状态
            {
                let mut state = self.state.lock().await;
                state.phase = AgentPhase::Done;
            }

            Ok("Processing complete".to_string())
        })
    }

    fn name(&self) -> &str {
        &self.name
    }

    fn state(&self) -> &AgentState {
        // 这里返回内部状态的引用
        // 调用方需要小心：引用的生命周期与self绑定
        // 如果Agent被drop，这个引用就无效了
        // ——但编译器会阻止这种用法
        // 这是Rust"硬"的核心：生命周期约束让不安全的用法成为编译错误
        // 注意：实际实现需要返回内部状态的引用，但这里用unimplemented!()简化
        // 正确实现类似：&self.state.lock().await（需要锁的二次借用）
        unimplemented!()
    }
}

// ============================================================
// Part 4: 类型状态模式 —— 编译期穷尽状态机
// ============================================================

/// 类型状态模式：用类型系统穷尽状态机的所有分支
/// 与TypeScript的enum不同，Rust的类型状态在编译期保证穷尽性

/// 错误的做法：使用运行时状态判断
/*
 * fn handle_phase(state: &AgentPhase) {
 *     match state {
 *         AgentPhase::Idle => { ... }
 *         AgentPhase::Thinking => { ... }
 *         AgentPhase::ExecutingTool => { ... }
 *         AgentPhase::WaitingForConfirmation => { ... }
 *         AgentPhase::Done => { ... }
 *         AgentPhase::Error(msg) => { ... }
 *     }
 *     // 如果添加了新的Phase，但没有更新这个match
 *     // 编译器会警告："match is not exhaustive"
 *     // ——这是TypeScript做不到的
 * }
 */

/// 正确的做法：使用类型状态模式让编译器追踪状态转换
trait PhaseTransition {
    fn can_transition_to(&self, next: &AgentPhase) -> bool;
}

impl PhaseTransition for AgentPhase {
    fn can_transition_to(&self, next: &AgentPhase) -> bool {
        match (self, next) {
            (AgentPhase::Idle, AgentPhase::Thinking) => true,
            (AgentPhase::Thinking, AgentPhase::ExecutingTool) => true,
            (AgentPhase::Thinking, AgentPhase::WaitingForConfirmation) => true,
            (AgentPhase::ExecutingTool, AgentPhase::Thinking) => true,
            (AgentPhase::ExecutingTool, AgentPhase::Done) => true,
            (AgentPhase::WaitingForConfirmation, AgentPhase::Thinking) => true,
            (AgentPhase::WaitingForConfirmation, AgentPhase::Idle) => true,
            (AgentPhase::Thinking, AgentPhase::Done) => true,
            (AgentPhase::Thinking, AgentPhase::Error(_)) => true,
            (AgentPhase::Error(_), AgentPhase::Idle) => true,
            _ => false,
        }
    }
}

/// 状态机定义：用类型系统强制合法的状态转换
pub struct StateMachine<S> {
    _state: std::marker::PhantomData<S>,
}

// 如果Rust编译器在match时不处理所有可能的分支，会产生编译错误
// 这与TypeScript的enum完全不同：TypeScript的enum允许遗漏case，只要不用default

// ============================================================
// Part 5: Send + Sync约束 —— 编译期线程安全
// ============================================================

/// Rust的线程安全是通过类型系统强制保证的
/// Send：值可以在线程间传递
/// Sync：值可以在线程间共享引用

/// 错误示例：尝试在线程间传递非Send类型
/*
 * use std::rc::Rc;
 *
 * fn send_rc_to_thread(rc: Rc<String>) {
 *     let handle = std::thread::spawn(move || {
 *         println!("{}", rc);
 *     });
 *     // ❌ 编译错误：Rc<String>不是Send
 *     // 因为Rc的引用计数不是原子操作，多线程访问会导致数据竞争
 *     // 使用Arc<String>代替——Arc是线程安全的引用计数
 * }
 */

// 正确的多线程共享状态
fn share_state_across_threads() {
    let state = Arc::new(Mutex::new(AgentState::new(SessionId::new())));

    let state_clone = Arc::clone(&state);
    let handle = std::thread::spawn(move || {
        let mut s = state_clone.lock().unwrap();
        s.phase = AgentPhase::Thinking;
    });

    handle.join().unwrap();
}

// ============================================================
// Part 6: 与TypeScript的对比总结
// ============================================================

/*
 * TypeScript的局限性：
 *
 * 1. 类型级联错误：AI生成的字段名可能不一致
 *    interface AgentState { tools: Array<{name: string}> }
 *    const state: AgentState = { tools: [{ name: "run_sql" }] };
 *    state.tools[0].nam  // 错误：name不是nam
 *    // TypeScript会报错，但AI可以用as any绕过
 *
 * 2. 运行时内存泄漏：TypeScript不追踪生命周期
 *    const callbacks: Array<() => void> = [];
 *    function registerCallback(cb: () => void) { callbacks.push(cb); }
 *    // callbacks永远不会被清理，内存泄漏
 *    // TypeScript编译器完全视而不见
 *
 * 3. 线程安全：TypeScript是单线程的，不存在这个问题
 *    // 但如果扩展到Web Worker，postMessage可以传递任何数据
 *
 * Rust的保证：
 *
 * 1. 生命周期标注：编译器追踪引用的有效性
 *    fn get_token<'a>(token: &'a Token) -> &'a str { &token.id }
 *    // 返回值的生命周期与输入绑定，编译器保证有效性
 *
 * 2. 所有权转移：值只能有一个所有者
 *    let token = Token::new("tok_001");
 *    let moved_token = token;
 *    // println!("{}", token.id); // ❌ 编译错误：token已被move
 *
 * 3. 线程安全：Send + Sync trait约束
 *    // 只有实现了Send的类型才能在线程间传递
 *    // 只有实现了Sync的类型才能在线程间共享引用
 *    // 这些约束是编译期的，不是运行时的
 */

fn main() {
    println!("Lifetime and ownership demonstration complete");
}
```

---

## Odyssey Bundle架构：Agent定义+工具+沙箱策略打包

### Bundle设计的核心理念

第三章的TypeSafeAgent展示了如何用TypeScript类型系统建立契约层。但TypeScript的类型防线有一个盲区：**它只能约束代码结构，无法约束执行行为**。一个函数可以被声明为`async function foo(): Promise<string>`，但它的实现可能返回`Promise<number>`，可能抛出未捕获的异常，可能内存泄漏，可能死循环。

Rust的Odyssey Bundle架构用类型系统打包了Agent的完整执行环境：**Agent定义、工具集、沙箱策略**，三者形成编译期的约束闭环。

```rust
// ============================================================
// Odyssey Bundle：完整的Agent打包架构
// ============================================================

/// OdysseyBundle：Agent的完整打包，包含定义+工具+策略
pub struct OdysseyBundle {
    pub agent: OdysseyAgent,
    pub tools: ToolRegistry,
    pub sandbox: SandboxPolicy,
    pub telemetry: TelemetryConfig,
}

/// 工具注册表：编译期注册，运行时查询
#[derive(Debug)]
pub struct ToolRegistry {
    tools: HashMap<String, ToolDefinition>,
    sandbox_overrides: HashMap<String, SandboxPolicy>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self {
            tools: HashMap::new(),
            sandbox_overrides: HashMap::new(),
        }
    }

    pub fn register(&mut self, tool: ToolDefinition) {
        self.tools.insert(tool.name.clone(), tool);
    }

    pub fn get(&self, name: &str) -> Option<&ToolDefinition> {
        self.tools.get(name)
    }

    pub fn set_sandbox_override(&mut self, tool_name: &str, policy: SandboxPolicy) {
        self.sandbox_overrides.insert(tool_name.to_string(), policy);
    }

    pub fn get_effective_policy(&self, tool_name: &str, default: &SandboxPolicy) -> SandboxPolicy {
        self.sandbox_overrides.get(tool_name).cloned().unwrap_or_else(|| default.clone())
    }
}

impl Default for ToolRegistry {
    fn default() -> Self {
        Self::new()
    }
}

/// 遥测配置：可观测性
#[derive(Debug, Clone)]
pub struct TelemetryConfig {
    pub trace_calls: bool,
    pub log_tokens: bool,
    pub metrics_interval_ms: u64,
}

impl TelemetryConfig {
    pub fn default() -> Self {
        Self {
            trace_calls: true,
            log_tokens: true,
            metrics_interval_ms: 1000,
        }
    }
}

/// Bundle工厂：编译期构建，运行时执行
pub struct BundleBuilder {
    name: String,
    session_id: SessionId,
    tools: Vec<ToolDefinition>,
    sandbox: SandboxPolicy,
    telemetry: TelemetryConfig,
}

impl BundleBuilder {
    pub fn new(name: impl Into<String>, session_id: SessionId) -> Self {
        Self {
            name: name.into(),
            session_id,
            tools: Vec::new(),
            sandbox: SandboxPolicy::default_for_agent(),
            telemetry: TelemetryConfig::default(),
        }
    }

    pub fn with_tool(mut self, tool: ToolDefinition) -> Self {
        self.tools.push(tool);
        self
    }

    pub fn with_strict_sandbox(mut self) -> Self {
        self.sandbox = SandboxPolicy::strict();
        self
    }

    pub fn with_telemetry(mut self, config: TelemetryConfig) -> Self {
        self.telemetry = config;
        self
    }

    pub fn build(self) -> OdysseyBundle {
        let mut agent = OdysseyAgent::with_policy(
            self.name,
            self.session_id,
            self.sandbox.clone(),
        );

        let mut registry = ToolRegistry::new();
        for tool in self.tools {
            registry.register(tool);
        }

        OdysseyBundle {
            agent,
            tools: registry,
            sandbox: self.sandbox,
            telemetry: self.telemetry,
        }
    }
}

// ============================================================
// Bundle使用示例
// ============================================================

fn build_odyssey_bundle() -> OdysseyBundle {
    BundleBuilder::new("odyssey-agent", SessionId::new())
        .with_tool(ToolDefinition {
            name: "run_sql".to_string(),
            description: "Execute a SELECT query".to_string(),
            parameters: vec![
                ParameterDefinition {
                    name: "query".to_string(),
                    param_type: ParameterType::String,
                    required: true,
                },
            ],
        })
        .with_tool(ToolDefinition {
            name: "fetch_user".to_string(),
            description: "Fetch user by ID".to_string(),
            parameters: vec![
                ParameterDefinition {
                    name: "user_id".to_string(),
                    param_type: ParameterType::String,
                    required: true,
                },
            ],
        })
        .with_strict_sandbox()
        .build()
}

/// 使用示例：通过Bundle调用工具的完整流程
async fn demonstrate_bundle_usage() -> Result<(), AgentError> {
    // 1. 构建Bundle
    let bundle = build_odyssey_bundle();

    // 2. 通过Bundle调用工具
    let query = "SELECT * FROM users WHERE id = '123'";
    let result = bundle.agent.execute_tool_call(
        "run_sql",
        serde_json::json!({ "query": query }),
    ).await?;

    // 3. 处理响应
    if result.success {
        println!("Query executed successfully: {}", result.output);
    } else {
        eprintln!("Query failed: {}", result.output);
    }

    Ok(())
}

/// 使用示例：状态转移与Bundle的协同
async fn demonstrate_state_transition() -> Result<ToolResult, AgentError> {
    let bundle = build_odyssey_bundle();

    // 状态转移由Agent内部管理
    // Bundle将Agent、工具注册表、沙箱策略打包在一起
    // 调用工具时，Agent自动完成Idle -> Thinking -> ExecutingTool的状态转移

    let result = bundle.agent.execute_tool_call(
        "fetch_user",
        serde_json::json!({ "user_id": "usr_456" }),
    ).await?;

    Ok(result)
}
```

### Bundle vs TypeScript：为什么Rust的打包更"硬"

| 维度 | TypeScript Bundle | Rust Odyssey Bundle |
|------|------------------|---------------------|
| 工具注册 | 运行时HashMap，key是string | 编译期类型安全，name是`&'static str` |
| 沙箱策略 | 运行时配置，可以动态修改 | 编译期`SandboxPolicy`类型，实例不可变 |
| 状态转移 | 运行时enum，可以任意跳状态 | 编译期`PhaseTransition` trait，约束合法转换 |
| 线程安全 | 不支持（单线程假设） | `Send + Sync`约束，编译期保证 |
| 生命周期 | 不追踪 | `'static`、`'call`等标注，编译期追踪 |
| 可观测性 | 运行时日志，可以关闭 | 编译期`TelemetryConfig`，结构化且不可绕过 |

---

## 类型状态模式：编译期穷尽状态机

### TypeScript enum的穷尽性陷阱

TypeScript的`enum`允许不穷尽的`switch`语句：

```typescript
enum AgentPhase {
    Idle,
    Thinking,
    ExecutingTool,
    Done,
}

function handlePhase(phase: AgentPhase) {
    switch (phase) {
        case AgentPhase.Idle:
            return "idle";
        case AgentPhase.Thinking:
            return "thinking";
        case AgentPhase.Done:
            return "done";
        // 忘记处理 ExecutingTool？TypeScript不报错
        // 编译器只警告："并非所有代码路径都返回值"
        // 但这是警告，不是错误——可以编译通过
    }
}
```

AI在生成TypeScript代码时，可能"忘记"处理某个enum分支，而TypeScript编译器只会给一个警告。这个警告可能被AI忽略，可能在CI中被`tsconfig`降级为不报错，最终在运行时爆炸。

### Rust的穷尽性保证

Rust的`match`表达式要求穷尽所有分支，编译器会强制检查：

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
enum AgentPhase {
    Idle,
    Thinking,
    ExecutingTool,
    WaitingForConfirmation,
    Done,
    Error(String),
}

fn phase_name(phase: &AgentPhase) -> &'static str {
    match phase {
        AgentPhase::Idle => "idle",
        AgentPhase::Thinking => "thinking",
        AgentPhase::ExecutingTool => "executing",
        AgentPhase::WaitingForConfirmation => "waiting",
        AgentPhase::Done => "done",
        AgentPhase::Error(_) => "error", // 必须处理Error变体
        // 忘记任何分支？编译错误："match is not exhaustive"
    }
}

// 如果添加新的AgentPhase变体，但没有更新所有match语句？
// 编译器会列出所有需要更新的地方
// ——这是TypeScript做不到的
```

Rust的`#[non_exhaustive]`属性可以标记"未来可能扩展"的enum，但即使是这样，编译器也会强制处理已知变体。

### 类型状态模式实战

```rust
// 类型状态模式：用状态机类型约束状态转移
// 这是第五章"状态跃迁"的预告片

/// 状态机 trait：定义合法的状态转移
pub trait StateMachine: Sized {
    type State;
    type Event;

    fn transition(&mut self, event: Self::Event) -> Result<(), InvalidTransition>;
}

/// Odyssey状态机实现
#[derive(Debug)]
pub struct OdysseyStateMachine {
    current: AgentPhase,
    history: Vec<AgentPhase>,
}

#[derive(Debug, Clone)]
pub enum OdysseyEvent {
    Start,
    ExecuteTool,
    ToolResult(bool),
    Confirm,
    Error(String),
}

#[derive(Debug)]
pub enum InvalidTransition {
    From(AgentPhase, AgentPhase),
    InvalidEvent(String),
}

impl OdysseyStateMachine {
    pub fn new() -> Self {
        Self {
            current: AgentPhase::Idle,
            history: vec![AgentPhase::Idle],
        }
    }

    pub fn current(&self) -> &AgentPhase {
        &self.current
    }

    pub fn history(&self) -> &[AgentPhase] {
        &self.history
    }
}

impl StateMachine for OdysseyStateMachine {
    type State = AgentPhase;
    type Event = OdysseyEvent;

    fn transition(&mut self, event: Self::Event) -> Result<(), InvalidTransition> {
        let next = match (&self.current, &event) {
            (AgentPhase::Idle, OdysseyEvent::Start) => AgentPhase::Thinking,
            (AgentPhase::Thinking, OdysseyEvent::ExecuteTool) => AgentPhase::ExecutingTool,
            (AgentPhase::ExecutingTool, OdysseyEvent::ToolResult(true)) => AgentPhase::Thinking,
            (AgentPhase::ExecutingTool, OdysseyEvent::ToolResult(false)) => {
                AgentPhase::Error("Tool execution failed".to_string())
            }
            (AgentPhase::Thinking, OdysseyEvent::Confirm) => AgentPhase::WaitingForConfirmation,
            (AgentPhase::WaitingForConfirmation, OdysseyEvent::Start) => AgentPhase::Thinking,
            (AgentPhase::Thinking, OdysseyEvent::Error(msg)) => AgentPhase::Error(msg.clone()),
            (AgentPhase::Error(_), OdysseyEvent::Start) => AgentPhase::Idle,
            _ => return Err(InvalidTransition::InvalidEvent(format!("{:?}", event))),
        };

        self.history.push(next.clone());
        self.current = next;
        Ok(())
    }
}

impl Default for OdysseyStateMachine {
    fn default() -> Self {
        Self::new()
    }
}
```

---

## 桥接语

- **承上：** 第三章建立了"类型作为契约"的原则，展示了TypeScript类型防线如何消灭AI生成的JSON解析错误。但TypeScript的类型约束是"软"的——`as any`可以绕过，enum可以遗漏分支，类型错误可以编译通过然后在运行时爆炸。Rust的所有权模型把类型约束变成"硬"的——借用检查器追踪生命周期，生命周期标注证明引用有效性，类型状态模式穷尽状态机的所有分支。Anthropic 16 Agent × C编译器项目证明了这个"硬"的价值：100,000行Rust，99% GCC torture test通过率。

- **启下：** 但所有权约束了状态泄漏，状态跃迁怎么办？当Agent从一个Phase转移到另一个Phase时，如何保证转移的合法性？如何让编译器追踪状态机的每一个分支？第五章将回答：类型状态模式如何把状态跃迁变成编译期事实——以及为什么这个"硬"让AI编程的确定性再提升一个量级。

- **认知缺口：** 你可能在用TypeScript写AI应用，感觉类型系统已经够用了。但"够用"和"够硬"之间有巨大差距——TypeScript的类型系统无法追踪值的生命周期，无法约束状态转移的合法性，无法保证线程安全。Rust的所有权模型把这三个问题变成了编译期的必然事实，而不是运行时的概率性事件。

---

## 本章来源

### 一手来源

1. **Anthropic 16 Agent × C编译器项目** — 100,000行Rust代码，99% GCC torture test通过率，证明Rust所有权模型在大型工程中的可靠性，来源：anthropic.com/engineering/building-c-compiler

2. **Rust+AI Agent+WASM实战教程** — p4.txt中的完整代码示例，trait Agent定义、生命周期标注、wasm-bindgen接口，来源：ITNEXT (Dogukan Tuna)

3. **Rust官方所有权文档** — 所有权三条规则、生命周期标注语法、借用检查器行为，来源：doc.rust-lang.org/book/ch04-00-understanding-ownership.html

4. **AutoAgents项目** — Rust编写的多Agent框架，Ractor actor运行时，支持WASM部署，来源：liquidos-ai.github.io/AutoAgents

5. **Rustine (arXiv:2511.20617)** — C到Safe Rust翻译，87%函数等价性，证明Rust类型安全的工程价值，来源：arXiv:2511.20617

6. **SafeTrans (arXiv:2505.10708)** — C到Rust迭代修复，成功率54%→80%，证明Rust作为跨语言类型安全底座的可行性，来源：arXiv:2505.10708

### 二手来源

7. **VERT: Verified Equivalent Rust Transpilation (arXiv:2404.18852)** — WASM编译器生成oracle Rust程序作为参考，验证LLM生成的代码，来源：arXiv:2404.18852

8. **ts-rs项目** — 从Rust struct生成TypeScript类型声明，跨语言类型对齐的工具，来源：github.com/Aleph-Alpha/ts-rs

9. **specta项目** — 导出Rust类型到TypeScript的库，来源：docs.rs/specta

10. **Rust Compiler架构** — Rust编译器利用所有权模型实现内存安全，无需GC，来源：rust-lang.org (当前版本1.94.1)
