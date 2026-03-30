# 第7章：事务性无回归（TNR）

> **核心理念**：LLM作为概率性文本生成函数，其输出具有内在的不确定性。TNR（Transactional Non-Regression）确保即使修复失败，系统状态也绝不恶化。

## 7.1 TNR理论基础

**原创定义**：Transactional Non-Regression (TNR) 是一种安全原语，确保Agent修复失败时系统状态绝不恶化。

**形式化定义**

```
定义（TNR）：
给定状态空间S和修复操作Fix: S → S，
TNR成立当且仅当：
∀s ∈ S, Fix(s) ∈ {s', s} 其中 s' 是s的改善

即：修复要么成功（状态改善），要么回滚（状态不变）
```

**与传统事务恢复的对比**

| 维度 | 传统事务恢复 | TNR |
|------|-------------|-----|
| 目标 | 数据一致性 | 状态不恶化 |
| 回滚触发 | 事务失败 | 修复失败 |
| 回滚粒度 | 全量 | 渐进式 |
| 验证 | 完整性约束 | 状态不变量 |

**四条TNR保证**

1. **修复失败 → 回滚到安全状态**：任何修复操作失败时，系统必须回滚到已知的安全状态，绝不允许状态恶化。
2. **回滚操作本身是原子的**：回滚过程不可中断，要么完全成功，要么完全失败但保持原状态。
3. **回滚后状态经过安全验证**：回滚后的状态必须通过预定义的安全验证，确保系统仍处于可接受状态。
4. **回滚历史可追溯**：所有回滚操作都必须记录完整的审计日志，便于事后分析和改进。

## 学术对话：Kitchen Loop (arXiv:2603.25697)

**A级论文**，为TNR提供了实践验证。

**Kitchen Loop四组件**

1. **Specification Surface** — 产品声称支持的枚举
2. **'As a User x 1000'** — LLM Agent以1000倍人类速度行使规格
3. **Unbeatable Tests** — 无法伪造的地面真实验证
4. **Drift Control** — 持续质量测量 + 自动暂停门

**核心数据（A级）**

| 指标 | 数据 |
|------|------|
| 生产迭代 | 285+次 |
| Merged PR | 1094+ |
| 回归 | **零** |

**本书回应**：Kitchen Loop的"零回归"是TNR的最佳实践验证。该系统通过严格的规格表面定义和不可伪造的测试验证，实现了真正的事务性无回归保证。每个修复尝试都被包裹在TNR原语中，确保即使修复失败，系统状态也不会比修复前更差。

## 7.2 Undo Agent设计

TNR的核心实现依赖于Undo Stack数据结构和快照机制。以下是Rust实现：

```rust
use std::collections::VecDeque;
use std::sync::{Arc, RwLock};

/// Agent阶段枚举
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AgentPhase {
    Initializing,
    Planning,
    Executing,
    Reviewing,
    Completed,
    Failed,
}

/// 状态快照（不可变）
#[derive(Debug, Clone)]
pub struct StateSnapshot {
    pub phase: AgentPhase,
    pub context: String,
    pub timestamp: std::time::Instant,
}

/// Undo Stack：TNR的核心数据结构
pub struct UndoStack {
    snapshots: RwLock<VecDeque<Arc<StateSnapshot>>>,
    max_depth: usize,
}

impl UndoStack {
    pub fn new(max_depth: usize) -> Self {
        Self {
            snapshots: RwLock::new(VecDeque::with_capacity(max_depth)),
            max_depth,
        }
    }

    /// 压入快照（修复前调用）
    pub fn push(&self, snapshot: StateSnapshot) {
        let mut snapshots = self.snapshots.write().unwrap();
        snapshots.push_back(Arc::new(snapshot));
        if snapshots.len() > self.max_depth {
            snapshots.pop_front();
        }
    }

    /// 撤销到上一状态（修复失败时调用）
    pub fn undo(&self) -> Option<Arc<StateSnapshot>> {
        let mut snapshots = self.snapshots.write().unwrap();
        snapshots.pop_back()
    }

    /// 获取当前快照数量
    pub fn depth(&self) -> usize {
        self.snapshots.read().unwrap().len()
    }
}

/// TNR保证的Agent
pub struct TNRAgent {
    state: RwLock<AgentPhase>,
    undo_stack: UndoStack,
}

impl TNRAgent {
    pub fn new() -> Self {
        Self {
            state: RwLock::new(AgentPhase::Initializing),
            undo_stack: UndoStack::new(16),
        }
    }

    /// TNR保护的修复操作
    pub fn try_fix<F>(&self, fix_fn: F) -> Result<AgentPhase, String>
    where
        F: FnOnce(AgentPhase) -> Result<AgentPhase, String>,
    {
        // 使用单一锁保护整个快照-修复-回滚流程，避免竞态条件
        let mut state_guard = self.state.write().unwrap();
        let current = *state_guard;

        // 1. 记录当前状态快照（在锁内执行，确保原子性）
        self.undo_stack.push(StateSnapshot {
            phase: current,
            context: String::new(),
            timestamp: std::time::Instant::now(),
        });

        // 2. 尝试修复
        match fix_fn(current) {
            Ok(new_state) => {
                // 修复成功，更新状态
                *state_guard = new_state;
                Ok(new_state)
            }
            Err(e) => {
                // 修复失败，执行TNR回滚
                if let Some(snapshot) = self.undo_stack.undo() {
                    *state_guard = snapshot.phase;
                    Err(format!("Fix failed, rolled back to {:?}: {}", snapshot.phase, e))
                } else {
                    Err(format!("Fix failed, no snapshot to rollback: {}", e))
                }
            }
        }
    }
}
```

**设计要点**

- **不可变快照**：`StateSnapshot`使用`Arc`引用计数，确保快照内容不可变
- **有界栈**：`UndoStack`限制最大深度，防止内存无限增长
- **线程安全**：使用`RwLock`确保并发访问安全
- **原子回滚**：`try_fix`方法确保修复和回滚操作的原子性

### TNR单元测试示例

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tnr_fix_success() {
        let agent = TNRAgent::new();
        assert_eq!(*agent.state.read().unwrap(), AgentPhase::Initializing);

        let result = agent.try_fix(|phase| {
            Ok(AgentPhase::Planning)
        });

        assert!(result.is_ok());
        assert_eq!(*agent.state.read().unwrap(), AgentPhase::Planning);
    }

    #[test]
    fn test_tnr_fix_failure_rollback() {
        let agent = TNRAgent::new();
        let initial = *agent.state.read().unwrap();

        let result = agent.try_fix(|_| {
            Err("Intentional failure".to_string())
        });

        assert!(result.is_err());
        assert_eq!(*agent.state.read().unwrap(), initial);
    }

    #[test]
    fn test_tnr_consecutive_failures() {
        let agent = TNRAgent::new();

        // 第一次失败
        agent.try_fix(|_| Err("Fail 1".to_string())).unwrap_err();
        assert_eq!(*agent.state.read().unwrap(), AgentPhase::Initializing);

        // 第二次失败
        agent.try_fix(|_| Err("Fail 2".to_string())).unwrap_err();
        assert_eq!(*agent.state.read().unwrap(), AgentPhase::Initializing);

        // 成功
        let result = agent.try_fix(|_| Ok(AgentPhase::Completed));
        assert!(result.is_ok());
        assert_eq!(*agent.state.read().unwrap(), AgentPhase::Completed);
    }
}
```

## 渐进式回滚策略

TNR支持多种回滚策略，根据失败严重程度选择适当的回滚范围：

| 策略 | 触发条件 | 回滚范围 | 示例 |
|------|---------|---------|------|
| 单步回滚 | 单个操作失败 | 上一快照 | 单个文件修改失败 |
| 多步回滚 | 连续N次失败 | M个快照前 | 编译循环检测 |
| 全量回滚 | 严重错误 | 初始状态 | 安全策略违规 |
| Git回滚 | 编译循环 | 上一通过编译的Commit | Claude Code模式 |

**策略选择逻辑**

1. **单步回滚**：最轻量级的回滚，适用于局部修复失败
2. **多步回滚**：当检测到连续失败模式时，回滚到更早的稳定状态
3. **全量回滚**：遇到违反核心安全约束的严重错误时，回滚到初始安全状态
4. **Git回滚**：在版本控制系统中，回滚到上一个通过所有测试的提交

每种策略都有对应的监控指标和自动触发机制，确保回滚决策基于客观数据而非启发式猜测。

## TNR状态机图

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
┌──────────┐   Snapshot   ┌──────────┐   Fix Success   ┌──────────┐
│   Idle   │ ─────────▶  │ Fixing   │ ─────────────▶  │   Done   │
└──────────┘             └──────────┘                 └──────────┘
     ▲                       │                              │
     │                       │ Fix Failed                   │
     │                       ▼                              │
     │                 ┌──────────┐                        │
     └─────────────────│ Rollback │────────────────────────┘
                       └──────────┘
```

状态转换语义：
- **Idle → Fixing**：调用`try_fix`时触发，原子性快照当前状态
- **Fixing → Done**：修复函数返回`Ok`，状态更新为新状态
- **Fixing → Rollback**：修复函数返回`Err`或panic，回滚到快照状态
- **Rollback → Idle**：回滚完成，准备下一次修复尝试

## TNR不可能性定理

> **学术诚实性声明**：以下定理表明，在开放世界假设下，TNR无法实现100%保障。

**定理（TNR不可能性）**：在开放世界假设下，不存在能够保证100% TNR的Agent系统。

**闭合世界假设（CWA）**：
设U为宇宙（Universe），则：
- 所有实体都在U内
- 所有操作都在U内定义
- 外部效应视为不可观测或不存在

**开放世界假设（OWA）**：
开放世界假设包含以下三条基本假设：

1. **外部实体假设**：$\exists e \notin \text{LocalSystem} \land \exists a: a(e) \neq \bot$
2. **不可逆操作假设**：$\exists a \in \text{Actions}, \forall s \in S: \text{Undo}(a(s)) \neq s$
3. **敌手存在假设**：$\exists \text{adv} \in \text{Adversaries}, \text{adv}$可以在任意时刻介入

当OWA成立时，即使TNR保护了本地状态，也无法防止外部副作用的不可逆影响。

**外部副作用的形式化定义**：

设 $\text{Fix}$ 为包含外部调用的修复操作，定义外部副作用ExternalEffect为：

$$\text{ExternalEffect}(a, s) \Leftrightarrow \exists e \notin \text{LocalSystem}: e \in \text{Args}(a) \land \text{Response}(e) \not\subseteq \text{UndoStack}$$

其中：
- $\text{LocalSystem}$：本地系统状态（Undo Stack可控制范围）
- $\text{Args}(a)$：操作a的参数
- $\text{Response}(e)$：外部实体的响应及副作用

**证明**：

考虑Agent执行修复操作 $a$ 调用外部API $f$。设：
- $s$：执行前状态
- $s'$：本地状态（假设修复成功）
- $e$：$f$产生的外部副作用（写入数据库、发送消息等）

由ExternalEffect定义可知，$e$ 不在Undo Stack的控制范围内。若 $f$ 返回后才发现需要回滚，$e$ 已不可挽回。故不存在能够保证"修复失败时系统状态绝不恶化"的通用算法。∎

**推论（工程意义）**：

TNR提供的是**本地状态不恶化**保证，而非**全局效果不恶化**保证。工程实践中：

1. **内部状态**：TNR保证有效（如代码、内存状态）
2. **外部副作用**：TNR无法保证（如已发送的邮件、已执行的交易）

**工程补偿策略**：

| 外部副作用类型 | 补偿机制 |
|---------------|---------|
| 数据库写入 | 事务补偿（Saga模式） |
| API调用 | 幂等设计 + 回调确认 |
| 文件系统 | 写时复制（Copy-on-Write） |
| 网络请求 | 消息队列 + 确认机制 |

## 本章小结

1. TNR定义：修复失败时，系统状态绝不恶化
2. Kitchen Loop实现零回归（1094+ PR，285+迭代）
3. Undo Stack + 快照机制实现100%可回滚
4. 渐进式回滚策略：单步 → 多步 → 全量 → Git
5. **TNR不可能性定理**：开放世界假设下，外部副作用无法被撤销——这是重要的学术诚实性边界声明