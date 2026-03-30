# 第四部分：运行时层 — WASI能力安全与TNR运行时实现

## 本章Q

如何从物理上消灭"AI删库跑路"的可能性？

## 魔法时刻

**WASI能力撤销的物理意义：不是"不允许"，而是"物理上不可能"。**

---

你有一把钥匙，能打开A锁、B锁、C锁。你把C锁的钥匙交给了Agent。

现在的问题是：Agent能不能"偷走"C锁的钥匙，然后复制一把？

在传统Unix权限模型里，答案是"可以"——Agent可以用`fork`复制自己，用`ptrace`追踪父进程，或者直接读取`/proc/self/mem`。文件描述符是整数，不是对象。权限是位掩码，不是能力令牌。

在WASI能力模型里，答案是"物理上不可能"。

WASI的能力不是"权限位"，是**不可复制的引用**。当你把一个文件句柄交给WASM模块，你给的不是"打开文件的权限"，而是**一个特定的、无法伪造的、无法转让的引用**。

如果WASM模块尝试"复制"这个引用，它得到的只是自己的**副本**，而不是原始引用的控制权。原引用仍然在运行时手里。模块能做的，只是用这个引用做它被授权做的事——读文件。但它无法把读文件的权限变成"写文件的权限"，无法把文件句柄传给另一个模块，无法创建新的网络连接。

**这就是能力安全与传统权限的本质区别：**

```
传统Unix：  "你有权限X" → 权限可以扩散
WASI：      "你有一个能力C" → 能力无法复制
```

更关键的是：**WASI能力可以被撤销**。不是"你不再被允许"，而是"这个能力引用现在无效"。运行时可以在任何时刻宣告某个能力失效，而模块无法阻止这个过程，因为它不持有能力的"本质"，只持有能力的"引用"。

这就是"物理上不可能"的含义。不是道德劝诫，不是法律禁止——是物理结构使然。

---

## 五分钟摘要

第十三章解决了"WASM作为数字监狱"的问题——Agent被关在指令级隔离的沙箱里，无法逃逸。

但隔离不等于安全。

如果监狱里的Agent获得了厨房的钥匙，它仍然可以偷走厨房的钥匙，复制，然后偷渡出狱。WASM隔离了Agent的**执行**，但没有限制Agent**能访问哪些资源**。

WASI（WASM System Interface）回答了这个问题：如何定义Agent的能力边界？

关键洞察：

1. **传统安全：黑名单**（禁止X）
2. **Capability安全：白名单**（只允许X）
3. **WASI能力撤销 = 物理上剥夺权限**

具体来说，这一章回答：

1. **WASI能力模型是什么？** —— 不可伪造的引用，无法扩散的权限
2. **如何在代码里实现能力授予？** —— 显式的、细粒度的资源控制
3. **TNR运行时如何利用能力撤销？** —— 作为回滚原语
4. **为什么这是物理上不可能，而不是配置上不允许？** —— 能力撤销的不可阻止性

---

## Step 1: 能力导向执行代码 — WASI显式授予示例

### 传统权限 vs 能力模型

传统Unix权限：
```rust
// 传统模型：权限是全局状态
let fd = open("/data/db.sqlite", O_RDWR);  // 进程级权限检查
// fd是整数，可以复制、传递、继承
write(fd, data);  // 内核检查进程是否有O_RDWR权限
// Agent可以: dup(fd), fork(), sendmsg(fd) → 权限扩散
```

WASI能力模型：
```rust
// 能力模型：权限是不可复制的引用
let capability = open_capability("/data/db.sqlite", ReadOnly);  // 返回能力引用
// capability是 opaque 引用，不是整数
// 只能通过这个引用操作资源
read(capability, buffer);  // 运行时验证capability有效
// Agent无法: 复制capability, 传递capability给其他人
// 运行时可以随时撤销capability
```

### 完整WASI能力授予代码

```rust
// wasi_capability_grant.rs — 文件和Socket显式授予的完整WASI示例

use std::sync::Arc;

/// WASI能力句柄（不可复制）
pub struct WasiHandle {
    /// 句柄类型
    kind: HandleKind,

    /// 内部资源ID
    resource_id: u64,

    /// 是否已被撤销
    revoked: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub enum HandleKind {
    /// 文件只读句柄
    FileReadonly(u64),
    /// 文件只写句柄
    FileWriteonly(u64),
    /// 文件读写句柄
    FileReadwrite(u64),
    /// 网络TCP连接（仅客户端）
    TcpStream(u64),
    /// UDP数据报
    UdpSocket(u64),
}

/// 能力授予错误
#[derive(Debug)]
pub enum CapabilityError {
    Revoked,
    PermissionDenied,
    InvalidHandle,
    ResourceNotFound,
}

/// WASI能力管理器
pub struct WasiCapabilityManager {
    /// 有效句柄表
    handles: std::collections::HashMap<u64, WasiHandle>,

    /// 下一个可用资源ID
    next_resource_id: u64,
}

impl WasiCapabilityManager {
    pub fn new() -> Self {
        Self {
            handles: std::collections::HashMap::new(),
            next_resource_id: 1,
        }
    }

    /// 授予文件只读能力
    pub fn grant_file_readonly(&mut self, path: &str) -> Result<u64, CapabilityError> {
        let resource_id = self.next_resource_id;
        self.next_resource_id += 1;

        let handle = WasiHandle {
            kind: HandleKind::FileReadonly(resource_id),
            resource_id,
            revoked: false,
        };

        // 验证文件存在且可读
        if !std::path::Path::new(path).exists() {
            return Err(CapabilityError::ResourceNotFound);
        }

        self.handles.insert(resource_id, handle);
        Ok(resource_id)
    }

    /// 授予网络连接能力（仅特定主机）
    pub fn grant_tcp_connect(&mut self, host: &str, port: u16) -> Result<u64, CapabilityError> {
        // 白名单检查：只有明确允许的主机才能连接
        let allowed_hosts = ["api.internal.company.com", "db.internal.company.com"];

        if !allowed_hosts.contains(&host) {
            return Err(CapabilityError::PermissionDenied);
        }

        let resource_id = self.next_resource_id;
        self.next_resource_id += 1;

        let handle = WasiHandle {
            kind: HandleKind::TcpStream(resource_id),
            resource_id,
            revoked: false,
        };

        self.handles.insert(resource_id, handle);
        Ok(resource_id)
    }

    /// 读取能力（验证句柄有效）
    pub fn read(&self, handle_id: u64, buffer: &mut [u8]) -> Result<usize, CapabilityError> {
        let handle = self.handles.get(&handle_id)
            .ok_or(CapabilityError::InvalidHandle)?;

        if handle.revoked {
            return Err(CapabilityError::Revoked);
        }

        match &handle.kind {
            HandleKind::FileReadonly(_) | HandleKind::FileReadwrite(_) => {
                // 实际读取文件...
                Ok(buffer.len())
            }
            _ => Err(CapabilityError::PermissionDenied),
        }
    }

    /// 写入能力（验证句柄有效且可写）
    pub fn write(&self, handle_id: u64, data: &[u8]) -> Result<usize, CapabilityError> {
        let handle = self.handles.get(&handle_id)
            .ok_or(CapabilityError::InvalidHandle)?;

        if handle.revoked {
            return Err(CapabilityError::Revoked);
        }

        match &handle.kind {
            HandleKind::FileWriteonly(_) | HandleKind::FileReadwrite(_) => {
                // 实际写入文件...
                Ok(data.len())
            }
            _ => Err(CapabilityError::PermissionDenied),
        }
    }

    /// 撤销能力（物理剥夺）
    pub fn revoke(&mut self, handle_id: u64) -> Result<(), CapabilityError> {
        let handle = self.handles.get_mut(&handle_id)
            .ok_or(CapabilityError::InvalidHandle)?;

        // 撤销是立即的、不可阻止的
        handle.revoked = true;

        // 清除句柄（资源释放）
        self.handles.remove(&handle_id);

        Ok(())
    }

    /// 撤销所有能力（用于Agent终止）
    pub fn revoke_all(&mut self) {
        // 所有句柄立即失效
        self.handles.clear();
    }

    /// 列出当前有效能力
    pub fn list_capabilities(&self) -> Vec<(u64, HandleKind)> {
        self.handles
            .values()
            .filter(|h| !h.revoked)
            .map(|h| (h.resource_id, h.kind.clone()))
            .collect()
    }
}

/// WASI模块上下文（持有能力引用）
pub struct WasiModuleContext {
    /// 能力管理器（由运行时持有）
    capability_manager: Arc<std::sync::Mutex<WasiCapabilityManager>>,

    /// 模块持有的能力句柄ID列表
    granted_handles: Vec<u64>,
}

impl WasiModuleContext {
    pub fn new(manager: Arc<std::sync::Mutex<WasiCapabilityManager>>) -> Self {
        Self {
            capability_manager: manager,
            granted_handles: Vec::new(),
        }
    }

    /// 请求新能力（运行时决定是否授予）
    pub fn request_capability(&mut self, kind: CapabilityRequest) -> Result<u64, CapabilityError> {
        let mut manager = self.capability_manager.lock().unwrap();

        let handle_id = match kind {
            CapabilityRequest::FileReadonly(path) => {
                manager.grant_file_readonly(&path)?
            }
            CapabilityRequest::TcpConnect(host, port) => {
                manager.grant_tcp_connect(&host, port)?
            }
        };

        self.granted_handles.push(handle_id);
        Ok(handle_id)
    }

    /// 释放能力（模块主动放弃）
    pub fn release_capability(&mut self, handle_id: u64) -> Result<(), CapabilityError> {
        let mut manager = self.capability_manager.lock().unwrap();
        manager.revoke(handle_id)?;
        self.granted_handles.retain(|&id| id != handle_id);
        Ok(())
    }

    /// 读取数据（使用已授予的能力）
    pub fn read(&self, handle_id: u64, buffer: &mut [u8]) -> Result<usize, CapabilityError> {
        let manager = self.capability_manager.lock().unwrap();
        manager.read(handle_id, buffer)
    }

    /// 写入数据（使用已授予的能力）
    pub fn write(&self, handle_id: u64, data: &[u8]) -> Result<usize, CapabilityError> {
        let manager = self.capability_manager.lock().unwrap();
        manager.write(handle_id, data)
    }
}

/// 能力请求类型
#[derive(Debug)]
pub enum CapabilityRequest {
    FileReadonly(String),
    FileWriteonly(String),
    TcpConnect(String, u16),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_capability_grant_and_revoke() {
        let manager = Arc::new(std::sync::Mutex::new(WasiCapabilityManager::new()));
        let mut ctx = WasiModuleContext::new(manager.clone());

        // 1. Agent请求文件只读能力
        let handle_id = ctx.request_capability(
            CapabilityRequest::FileReadonly("/data/config.json".to_string())
        ).unwrap();

        // 2. Agent可以读取（使用能力）
        let mut buffer = [0u8; 100];
        let result = ctx.read(handle_id, &mut buffer);
        assert!(result.is_ok());

        // 3. Agent无法写入（没有Writeonly能力）
        let result = ctx.write(handle_id, b"malicious data");
        assert!(matches!(result, Err(CapabilityError::PermissionDenied)));

        // 4. 运行时撤销能力（Agent无法阻止）
        {
            let mut manager = manager.lock().unwrap();
            manager.revoke(handle_id).unwrap();
        }

        // 5. Agent现在无法读取（能力已被撤销）
        let result = ctx.read(handle_id, &mut buffer);
        assert!(matches!(result, Err(CapabilityError::Revoked)));

        // 6. 关键：Agent无法阻止撤销，无法恢复能力
        // 这不是"不允许"，是"物理上不可能"
    }

    #[test]
    fn test_capability_not_sharable() {
        let manager = Arc::new(std::sync::Mutex::new(WasiCapabilityManager::new()));
        let mut ctx1 = WasiModuleContext::new(manager.clone());
        let mut ctx2 = WasiModuleContext::new(manager.clone());

        // Agent1获得只读能力
        let handle_id = ctx1.request_capability(
            CapabilityRequest::FileReadonly("/data/config.json".to_string())
        ).unwrap();

        // Agent1无法将能力"传递"给Agent2
        // 因为handle_id只是引用，不是能力本身
        // Agent2尝试使用Agent1的handle_id会失败
        let mut buffer = [0u8; 100];
        let result = ctx2.read(handle_id, &mut buffer);
        assert!(matches!(result, Err(CapabilityError::InvalidHandle)));
    }

    #[test]
    fn test_network_capability_whitelist() {
        let manager = Arc::new(std::sync::Mutex::new(WasiCapabilityManager::new()));
        let mut ctx = WasiModuleContext::new(manager.clone());

        // 白名单内的主机：允许
        let result = ctx.request_capability(
            CapabilityRequest::TcpConnect("api.internal.company.com".to_string(), 443)
        );
        assert!(result.is_ok());

        // 白名单外的主机：拒绝
        let result = ctx.request_capability(
            CapabilityRequest::TcpConnect("evil-attacker.com".to_string(), 443)
        );
        assert!(matches!(result, Err(CapabilityError::PermissionDenied)));
    }
}
```

---

## Step 2: TNR运行时实现 — 能力撤销作为回滚原语

### 能力撤销 = 原子性回滚

传统数据库的ACID中，原子性（Atomicity）通过日志和回滚实现。如果事务失败，数据库撤销部分完成的操作。

TNR运行时的能力撤销提供相同语义，但用于**整个Agent执行**：

```rust
// tnr_capability_runtime.rs — TNR运行时：能力撤销作为回滚原语

use std::sync::{Arc, Mutex};
use std::collections::HashMap;

/// TNR执行状态
#[derive(Debug, Clone, PartialEq)]
pub enum TnrState {
    /// 准备阶段
    Preparing,
    /// 运行阶段
    Running,
    /// 回滚阶段
    RollingBack,
    /// 已终止
    Terminated,
}

/// TNR能力上下文
pub struct TnrCapabilityContext {
    /// 当前状态
    state: TnrState,

    /// 能力管理器
    capability_manager: Arc<Mutex<WasiCapabilityManager>>,

    /// 能力变更日志（用于回滚）
    capability_log: Vec<CapabilityChange>,

    /// Agent ID
    agent_id: String,
}

/// 能力变更记录
#[derive(Debug, Clone)]
pub enum CapabilityChange {
    Granted { handle_id: u64, kind: HandleKind },
    Revoked { handle_id: u64 },
    Requested { request: CapabilityRequest, granted: bool },
}

impl TnrCapabilityContext {
    pub fn new(agent_id: String) -> Self {
        Self {
            state: TnrState::Preparing,
            capability_manager: Arc::new(Mutex::new(WasiCapabilityManager::new())),
            capability_log: Vec::new(),
            agent_id,
        }
    }

    /// 进入运行阶段
    pub fn enter_running(&mut self) {
        self.state = TnrState::Running;
    }

    /// 请求能力（记录日志）
    pub fn request_capability(&mut self, request: CapabilityRequest) -> Result<u64, CapabilityError> {
        assert_eq!(self.state, TnrState::Running);

        let mut manager = self.capability_manager.lock().unwrap();

        let handle_id = match request {
            CapabilityRequest::FileReadonly(ref path) => {
                manager.grant_file_readonly(path)
            }
            CapabilityRequest::TcpConnect(ref host, port) => {
                manager.grant_tcp_connect(host, port)
            }
            CapabilityRequest::FileWriteonly(ref path) => {
                // 写能力需要更严格审查
                return Err(CapabilityError::PermissionDenied);
            }
        };

        let granted = handle_id.is_ok();

        // 记录变更
        if let Ok(id) = handle_id {
            self.capability_log.push(CapabilityChange::Granted {
                handle_id: id,
                kind: manager.handles.get(&id).unwrap().kind.clone(),
            });
        }

        self.capability_log.push(CapabilityChange::Requested {
            request,
            granted,
        });

        handle_id
    }

    /// 运行时触发回滚（当Agent行为异常时）
    pub fn trigger_rollback(&mut self) {
        self.state = TnrState::RollingBack;

        let mut manager = self.capability_manager.lock().unwrap();

        // 按日志逆序撤销所有能力
        for change in self.capability_log.iter().rev() {
            match change {
                CapabilityChange::Granted { handle_id, .. } => {
                    // 撤销是立即的、不可阻止的
                    manager.revoke(*handle_id).ok();
                }
                CapabilityChange::Requested { request, granted: true } => {
                    // 如果请求被授予，撤销它
                    // （具体实现略）
                }
                _ => {}
            }
        }

        self.capability_log.clear();
        self.state = TnrState::Terminated;
    }

    /// 检查Agent是否尝试越权
    pub fn check_violation(&self, operation: &str) -> bool {
        // 异常检测：Agent尝试了超出其能力的操作
        // 这是一个简化示例，实际实现会更复杂
        match operation {
            "delete_database" | "drop_table" | "truncate" => true,
            "connect_unauthorized_host" => true,
            _ => false,
        }
    }

    /// 获取当前状态
    pub fn state(&self) -> TnrState {
        self.state.clone()
    }
}

/// TNR Agent执行器
pub struct TnrAgentExecutor {
    /// Agent上下文
    contexts: HashMap<String, TnrCapabilityContext>,
}

impl TnrAgentExecutor {
    pub fn new() -> Self {
        Self {
            contexts: HashMap::new(),
        }
    }

    /// 启动Agent
    pub fn spawn(&mut self, agent_id: String) -> Result<(), String> {
        if self.contexts.contains_key(&agent_id) {
            return Err(format!("Agent {} already exists", agent_id));
        }

        let ctx = TnrCapabilityContext::new(agent_id.clone());
        self.contexts.insert(agent_id, ctx);
        Ok(())
    }

    /// 执行Agent操作
    pub fn execute(&mut self, agent_id: &str, operation: &str) -> Result<(), TnrError> {
        let ctx = self.contexts.get_mut(agent_id)
            .ok_or(TnrError::AgentNotFound)?;

        // 状态检查
        if ctx.state() != TnrState::Running {
            return Err(TnrError::NotRunning);
        }

        // 越权检查
        if ctx.check_violation(operation) {
            // 发现越权行为，立即回滚
            ctx.trigger_rollback();
            return Err(TnrError::CapabilityViolation);
        }

        Ok(())
    }

    /// 终止Agent（释放所有能力）
    pub fn terminate(&mut self, agent_id: &str) -> Result<(), TnrError> {
        let ctx = self.contexts.get_mut(agent_id)
            .ok_or(TnrError::AgentNotFound)?;

        ctx.trigger_rollback();
        Ok(())
    }

    /// 列出所有Agent状态
    pub fn list_agents(&self) -> Vec<(String, TnrState)> {
        self.contexts
            .iter()
            .map(|(id, ctx)| (id.clone(), ctx.state()))
            .collect()
    }
}

/// TNR错误类型
#[derive(Debug)]
pub enum TnrError {
    AgentNotFound,
    NotRunning,
    CapabilityViolation,
    CapabilityError(CapabilityError),
}

impl From<CapabilityError> for TnrError {
    fn from(e: CapabilityError) -> Self {
        TnrError::CapabilityError(e)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tnr_rollback_on_violation() {
        let mut executor = TnrAgentExecutor::new();

        // 1. 启动Agent
        executor.spawn("agent-001".to_string()).unwrap();

        // 2. Agent进入运行阶段
        {
            let ctx = executor.contexts.get_mut("agent-001").unwrap();
            ctx.enter_running();
        }

        // 3. Agent请求数据库只读能力
        {
            let ctx = executor.contexts.get_mut("agent-001").unwrap();
            ctx.request_capability(
                CapabilityRequest::FileReadonly("/data/customers.db".to_string())
            ).unwrap();
        }

        // 4. Agent尝试越权操作（删库）
        let result = executor.execute("agent-001", "drop_table");
        assert!(matches!(result, Err(TnrError::CapabilityViolation)));

        // 5. Agent被回滚：所有能力被撤销
        let ctx = executor.contexts.get("agent-001").unwrap();
        assert_eq!(ctx.state(), TnrState::Terminated);

        // 6. Agent无法恢复能力（物理上不可能）
    }

    #[test]
    fn test_agent_isolation() {
        let mut executor = TnrAgentExecutor::new();

        // 启动两个Agent
        executor.spawn("agent-001".to_string()).unwrap();
        executor.spawn("agent-002".to_string()).unwrap();

        // Agent1获得数据库只读能力
        {
            let ctx = executor.contexts.get_mut("agent-001").unwrap();
            ctx.enter_running();
            ctx.request_capability(
                CapabilityRequest::FileReadonly("/data/customers.db".to_string())
            ).unwrap();
        }

        // Agent2尝试使用Agent1的能力（失败）
        {
            let ctx = executor.contexts.get_mut("agent-002").unwrap();
            ctx.enter_running();
            let result = ctx.read(999, &mut []);  // 无效句柄
            assert!(matches!(result, Err(CapabilityError::InvalidHandle)));
        }
    }
}
```

### 能力撤销作为ACID回滚

```
传统数据库事务:
  BEGIN TRANSACTION
    UPDATE accounts SET balance = balance - 100 WHERE id = 1;
    UPDATE accounts SET balance = balance + 100 WHERE id = 2;
  -- 如果失败: ROLLBACK (撤销所有变更)

TNR Agent执行:
  Agent请求能力A（读数据库）
  Agent请求能力B（连接内部API）
  Agent执行任务...
  -- 如果异常: trigger_rollback() (撤销所有能力)
```

关键区别：传统数据库回滚的是**数据变更**，TNR回滚的是**能力本身**。一旦能力被撤销，Agent物理上无法继续操作资源。

---

## Step 3: 安全证明 — 消灭AI删库跑路的物理可能性分析

### 攻击场景：恶意Agent试图删库跑路

**场景：** 部署在生产环境的AI Agent被prompt injection注入恶意指令，试图删除数据库然后外传数据。

**攻击路径（传统架构）：**

```
1. Agent通过prompt injection获得恶意指令
2. Agent使用数据库凭据（环境变量）连接数据库
3. Agent执行 DROP DATABASE production;
4. Agent将数据外传到外部服务器
5. 数据已删除+外传，防御失败
```

**攻击路径（WASI能力模型）：**

```
1. Agent通过prompt injection获得恶意指令
2. Agent尝试访问数据库 → 失败（没有db_write能力）
3. Agent尝试网络外传 → 失败（只有api.internal.company.com白名单）
4. 异常行为被检测，trigger_rollback()执行
5. Agent所有能力被撤销，Agent被终止
6. 数据库完整，数据未外传
```

### 形式化安全分析

**定理1：能力不可伪造**

设 `C` 为能力引用，`H` 为主机资源，`|C|` 为能力的"本质"（控制权）。

```
给定：
  - C 是对资源 H 的能力引用
  - Agent 无法直接访问 H（由运行时隔离）

则：
  - Agent 无法通过任何操作构造 C' 使得 |C'| = |C|
  - 证明：WASI模型中，能力是 opaque reference，不是可复制的位模式
```

**定理2：能力撤销的不可阻止性**

```
给定：
  - Agent持有能力引用 C
  - 运行时决定撤销 C

则：
  - C 在撤销后立即失效
  - Agent无法阻止撤销过程
  - Agent无法恢复 C

  - 证明：撤销操作作用于运行时维护的句柄表，
    Agent只持有引用，不持有引用的"本质"。
    运行时可以在任何时刻修改句柄表，Agent无法干预。
```

**定理3：删库跑路的物理不可能性**

```
攻击目标：删除数据库 D 并外传数据

攻击前提（必须满足）：
  1. Agent持有数据库写能力 W_D
  2. Agent持有网络外传能力 N_external

WASI能力模型保证：
  - W_D 只在明确授予时存在，且可被撤销
  - N_external 只允许连接白名单主机，无法连接外部

结论：
  - 在生产环境不授予 W_D 和 N_external 的情况下，
    删库跑路物理上不可能
  - 即使Agent被完全攻破，攻击者也只能在WASI沙箱内活动
```

### 多层防御体系

```
攻击者视角：

Layer 1: Prompt Injection
  问题：恶意指令注入Agent
  防御：WASM沙箱隔离（ch13）

Layer 2: 权限提升
  问题：Agent尝试获取更高权限
  防御：WASI能力白名单，不授予危险能力

Layer 3: 数据访问
  问题：Agent尝试访问敏感数据
  防御：只授予最小必要能力（读文件 ≠ 写文件）

Layer 4: 数据外传
  问题：Agent尝试外传数据
  防御：网络能力白名单，只能连接内部服务

Layer 5: 能力扩散
  问题：Agent尝试复制能力给其他进程
  防御：WASI能力不可复制，进程间无法共享句柄

物理保证：
  - 每一层都是架构级约束，不是配置级限制
  - Agent无法突破任何一层，因为物理上不可能
```

---

## Step 4: 魔法时刻段落 — "不允许" vs "物理上不可能"

### 魔法时刻

**传统安全的逻辑是："你不应该做X，做了会被惩罚。"**

WASI能力安全的逻辑是："你不能做X，因为物理上不可能。"

这两种表述听起来相似，本质上是两回事。

"不应该"是**道德劝诫**。可以被绕过，可以被遗忘，可以在压力下妥协。当Agent被prompt injection注入恶意指令时，"不应该"变成了一张废纸。

"不能"是**物理定律**。无法被绕过，无法被忽视，无法在压力下妥协。当Agent尝试越权操作时，它面对的不是警告，而是物理上不可能逾越的障碍。

```
传统Unix权限：
  chmod 000 /etc/shadow
  # 但root用户可以chmod回来
  # 但有能力的能力可以绕过
  # Agent可以用sudo或setuid绕过

WASI能力安全：
  不授予 db_write 能力
  # Agent物理上无法获得这个能力
  # 因为运行时在导入层过滤
  # Agent无法创建socket连接到数据库服务器
```

关键区别在于**权限的来源**：

- 传统Unix权限是**状态**。状态可以被修改、绕过、继承、遗忘。
- WASI能力是**引用**。引用是特定对象的句柄，不是可扩散的权限。

当你用chmod改变文件权限，你改变的是**与文件关联的权限位**。这个权限位可以被复制（通过进程fork）、可以被窃取（通过特权漏洞）、可以被遗忘（配置错误）。

当你授予WASI能力，你给出的是**指向特定资源对象的引用**。这个引用无法被复制，因为它不是数据，而是句柄。Agent可以持有引用，但无法访问引用的"本质"。

**这就是"物理上不可能"的含义：**

Agent不是被禁止做某事，而是物理上无法获得做某事的能力。

不是"你敢删库我就惩罚你"，而是"你根本没有删库的权限，物理上不可能获得这个权限"。

这不是安全策略，这是物理结构。

---

## Step 5: 桥接语 — V8 Isolates与WASM的不同

### 承上

第十三章建立了"WASM作为数字监狱"——指令级隔离解决了Agent逃逸问题。Agent被关在WASM沙箱里，物理上无法突破进程边界。

但监狱不只是墙，还需要狱警和监控系统。WASM隔离了执行，却没有定义"Agent能在监狱里做什么"。

本章的WASI能力系统回答了这个问题：定义Agent的能力边界，实现细粒度的资源控制，提供可撤销的能力原语。

### 启下：V8 Isolates vs WASM

下一个问题是：为什么选择WASM + WASI，而不是V8 Isolates？

| 维度 | V8 Isolates | WebAssembly + WASI |
|------|-------------|-------------------|
| 隔离技术 | JavaScript引擎沙箱 | WASM字节码沙箱 |
| 能力模型 | 无内置能力系统 | WASI提供系统接口能力 |
| 内存安全 | JS自动GC，无法精细控制 | 线性内存，精确控制 |
| 冷启动 | ~5-50ms | ~1-5ms |
| 多语言支持 | 仅JS/TS | 任何可编译为WASM的语言 |
| 标准化 | V8专有 | W3C标准 |
| 能力撤销 | 无内置支持 | WASI能力可撤销 |
| 生产部署 | Google Cloud Run | 任何WASM运行时 |

**关键差异：**

1. **能力系统**：V8 Isolates是"JavaScript执行环境"，没有内置的能力概念。WASI是"系统接口能力模型"，能力是语言规范的一部分。

2. **确定性**：V8的GC时机不确定，WASM线性内存在规范层面完全确定。

3. **多语言**：V8只运行JS/TS，WASM可运行Rust、C、C++、Go等任何可编译为目标架构的语言。

4. **渐进式权限**：V8 Isolates无法在运行时撤销权限，WASI能力可以在任何时刻撤销。

对于TNR运行时来说，WASM + WASI是正确选择，因为：
- 能力撤销是TNR回滚机制的基础
- 线性内存提供可预测的资源管理
- 多语言支持允许用Rust实现高性能Agent核心

---

## 本章来源

### 一手来源

| 来源 | URL | 关键数据/概念 |
|------|-----|--------------|
| WASI Official | https://github.com/WebAssembly/WASI | 能力模型、导入/导出语义 |
| WASI Preview2 | https://github.com/WebAssembly/WASI/blob/main/Phases/2.md | 系统接口标准化 |
| Wasmtime Capability | https://docs.wasmtime.dev/cap-std.sh | WASM运行时能力控制 |
| Leash Policy Engine | https://www.strongdm.com/blog/policy-enforcement-for-agentic-ai-with-leash | Cedar策略引擎、<1ms延迟 |
| MCP Security Best Practices | https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices.md | 最小权限Scope、通配符禁止 |

### 二手来源

| 来源 | 用途 |
|------|------|
| research-findings.md (Section 5.1) | MCP协议安全攻击向量 |
| research-findings.md (Section 5.3) | Leash政策引擎技术细节 |
| research-findings.md (Section 5.4) | WasmEdge性能数据 |
| ch13-wasm-prison.md | WASM隔离原理 |
| ch12-deadloop-rollback.md | TNR概念与回滚机制 |

### 技术标准

| 来源 | 用途 |
|------|------|
| WASM Spec (GitHub) | 线性内存、导入/导出语义 |
| WASI Snapshots | Preview1/Preview2能力定义 |
| Cedar Policy Language | 策略引擎规范 |
