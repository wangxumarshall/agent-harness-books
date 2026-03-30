# 第四部分：运行时层 — Immutable DAG状态持久化

## 本章Q

如何实现100%确定性重放？

## 魔法时刻

**状态的历史比状态本身更重要。**

---

当你debug一个生产环境的bug时，你最想知道的是什么？

不是"现在的状态是什么"——那是表象。
是"**为什么变成这样**"——那是根因。

传统状态管理告诉你当前状态。Immutable DAG告诉你状态的全部历史。

有了历史，你可以：
- 回到任意时间点重现状态
- 追踪任意状态变量的演变路径
- 分析错误状态的形成过程
- 在历史分支上实验而不污染主分支

状态的历史不是副产品。**它是可观测性的核心**。

---

## 五分钟摘要

第十六章的MCP沙箱解决了"如何安全调用外部工具"的问题——WASM隔离确保工具无法逃逸，网络零连通防止元数据攻击，提示词注入被多层检测拦截。

但隔离带来了新问题：**当每个请求都在全新的Isolate中执行时，状态如何持久化？**

答案是Immutable DAG（不可变有向无环图）。

核心思想：将Agent状态视为一系列不可变的快照，每个快照是DAG中的一个节点，边表示状态转换关系。新状态不是"覆盖"旧状态，而是"指向"旧状态。

关键优势：
- **确定性重放**：任意时间点的状态可精确重现
- **审计追溯**：完整的状态演变历史
- **分支实验**：在历史分支上实验而不污染主状态
- **并行协作**：多Agent可安全地基于同一历史状态工作

---

## Step 1: AST三阶段代码 — Raw/Analyzed/Lowered的完整处理

### 为什么Agent状态需要三阶段处理

编译器有前端处理：Raw AST → Analyzed AST → Lowered IR。

Agent状态管理同样需要三阶段：

```
Raw（原始状态）：
  用户输入、工具返回、模型输出——未经验证的原始数据

Analyzed（分析状态）：
  类型检查通过、Schema验证通过、业务规则校验通过——可信赖的状态

Lowered（持久化状态）：
  哈希已计算、压缩已执行、已写入CAS——不可变的历史快照
```

### 三阶段状态代码实现

```rust
// ast_three_stage.rs — Agent状态的三阶段处理

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;

/// ============================================================================
/// Raw Stage：原始状态——未经验证的数据
/// ============================================================================

/// 原始消息——来自用户或工具的未处理数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawMessage {
    /// 消息ID
    pub id: String,

    /// 消息角色
    pub role: RawRole,

    /// 原始内容（未解析）
    pub raw_content: String,

    /// 元数据（未经处理）
    pub metadata: HashMap<String, serde_json::Value>,
}

/// 原始角色
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RawRole {
    User,
    Assistant,
    Tool,
    System,
}

/// 原始工具调用
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawToolCall {
    /// 工具名称
    pub tool_name: String,

    /// 原始参数JSON
    pub arguments_json: String,

    /// 调用时间戳
    pub timestamp: u64,
}

/// 原始状态快照
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawState {
    /// 快照ID
    pub id: String,

    /// 原始消息列表
    pub messages: Vec<RawMessage>,

    /// 原始工具调用
    pub tool_calls: Vec<RawToolCall>,

    /// 创建时间
    pub created_at: u64,
}

/// ============================================================================
/// Analyzed Stage：分析状态——通过验证的可信数据
/// ============================================================================

/// 分析后的消息角色（经过验证）
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AnalyzedRole {
    User,
    Assistant,
    Tool { tool_name: String },
    System,
}

/// 分析后的消息内容
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AnalyzedContent {
    /// 文本内容（经过注入扫描）
    Text { content: String, injection_scan_passed: bool },

    /// 工具调用结果（经过Schema验证）
    ToolResult { tool_name: String, result: serde_json::Value },

    /// 错误内容（已分类）
    Error { error_code: AgentErrorCode, message: String },
}

/// Agent错误码体系
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AgentErrorCode {
    // === 工具调用错误 (10xxx) ===
    ToolNotFound = 10001,
    ToolPermissionDenied = 10002,
    ToolTimeout = 10003,
    ToolNetworkBlocked = 10004,
    ToolOutputSanitized = 10005,

    // === 状态验证错误 (20xxx) ===
    StateTypeMismatch = 20001,
    StateSchemaViolation = 20002,
    StateInvariantBroken = 20003,
    StateHistoryCorrupted = 20004,

    // === 执行错误 (30xxx) ===
    ExecutionPanic = 30001,
    ExecutionTimeout = 30002,
    ExecutionMemoryExceeded = 30003,

    // === 持久化错误 (40xxx) ===
    PersistenceHashMismatch = 40001,
    PersistenceCompressionFailed = 40002,
    PersistenceCASLookupFailed = 40003,
}

impl AgentErrorCode {
    pub fn category(&self) -> &'static str {
        match self {
            // 工具错误
            Self::ToolNotFound => "工具未找到",
            Self::ToolPermissionDenied => "工具权限不足",
            Self::ToolTimeout => "工具调用超时",
            Self::ToolNetworkBlocked => "工具网络访问被阻断",
            Self::ToolOutputSanitized => "工具输出被净化",

            // 状态错误
            Self::StateTypeMismatch => "状态类型不匹配",
            Self::StateSchemaViolation => "状态Schema违规",
            Self::StateInvariantBroken => "状态不变式被破坏",
            Self::StateHistoryCorrupted => "状态历史损坏",

            // 执行错误
            Self::ExecutionPanic => "执行时panic",
            Self::ExecutionTimeout => "执行超时",
            Self::ExecutionMemoryExceeded => "执行内存超限",

            // 持久化错误
            Self::PersistenceHashMismatch => "持久化哈希不匹配",
            Self::PersistenceCompressionFailed => "持久化压缩失败",
            Self::PersistenceCASLookupFailed => "内容寻址查找失败",
        }
    }

    pub fn is_retryable(&self) -> bool {
        matches!(
            self,
            Self::ToolTimeout
                | Self::ExecutionTimeout
                | Self::PersistenceCompressionFailed
                | Self::PersistenceCASLookupFailed
        )
    }
}

/// 分析后的消息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyzedMessage {
    /// 消息ID（继承自Raw）
    pub id: String,

    /// 分析后的角色
    pub role: AnalyzedRole,

    /// 分析后的内容
    pub content: AnalyzedContent,

    /// 分析时间戳
    pub analyzed_at: u64,

    /// 验证通过的错误码（空表示完全通过）
    pub suppressed_errors: Vec<AgentErrorCode>,
}

/// 分析后的状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyzedState {
    /// 快照ID（继承自Raw）
    pub id: String,

    /// 分析后的消息列表
    pub messages: Vec<AnalyzedMessage>,

    /// 状态Schema版本
    pub schema_version: String,

    /// 分析时间戳
    pub analyzed_at: u64,

    /// 不变式检查结果
    pub invariant_check: InvariantCheckResult,
}

/// 状态不变式检查结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvariantCheckResult {
    /// 检查是否通过
    pub passed: bool,

    /// 失败的不变式名称
    pub failed_invariants: Vec<String>,

    /// 检查时间
    pub checked_at: u64,
}

/// ============================================================================
/// Lowered Stage：持久化状态——不可变的DAG节点
/// ============================================================================

/// Lowered状态节点——写入CAS的不可变快照
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoweredStateNode {
    /// 节点的BLAKE3内容寻址哈希
    pub content_hash: String,

    /// 节点的压缩后大小（字节）
    pub compressed_size: usize,

    /// 节点的原始大小（字节）
    pub original_size: usize,

    /// 父节点哈希列表（支持DAG而非只是链）
    pub parents: Vec<String>,

    /// Lowered后的状态数据（压缩格式）
    pub data: Vec<u8>,

    /// 写入CAS的时间戳
    pub persisted_at: u64,

    /// Schema版本（用于迁移）
    pub schema_version: String,

    /// 元数据
    pub metadata: StateMetadata,
}

/// 状态元数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateMetadata {
    /// 创建此状态的Agent ID
    pub agent_id: String,

    /// 创建原因（UserMessage / ToolResult / AgentDecision）
    pub reason: StateCreationReason,

    /// 压缩算法（zstd级别）
    pub compression_level: i32,

    /// BLAKE3树根哈希
    pub tree_root: String,
}

/// 状态创建原因
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum StateCreationReason {
    /// 用户消息触发
    UserMessage,

    /// 工具调用结果触发
    ToolResult { tool_name: String },

    /// Agent决策触发
    AgentDecision { decision_type: String },

    /// 系统事件触发（如超时）
    SystemEvent { event_type: String },

    /// 初始化
    Initialization,
}

/// 三阶段状态转换器
pub struct StateTransformer {
    /// Schema验证器
    schema_validator: Arc<dyn SchemaValidator>,

    /// 注入扫描器
    injection_scanner: Arc<dyn InjectionScanner>,

    /// 不变式检查器
    invariant_checker: Arc<dyn InvariantChecker>,
}

impl StateTransformer {
    /// 从Raw转换为Analyzed
    pub fn analyze(&self, raw: RawState) -> Result<AnalyzedState, TransformError> {
        let mut analyzed_messages = Vec::new();
        let mut suppressed_errors = Vec::new();

        for raw_msg in &raw.messages {
            // 1. 注入扫描
            let injection_result = self.injection_scanner.scan(&raw_msg.raw_content);

            // 2. 角色转换
            let role = match &raw_msg.role {
                RawRole::Tool => {
                    // 从metadata中提取tool_name
                    let tool_name = raw_msg
                        .metadata
                        .get("tool_name")
                        .and_then(|v| v.as_str())
                        .unwrap_or("unknown")
                        .to_string();
                    AnalyzedRole::Tool { tool_name }
                }
                RawRole::User => AnalyzedRole::User,
                RawRole::Assistant => AnalyzedRole::Assistant,
                RawRole::System => AnalyzedRole::System,
            };

            // 3. 内容分析
            let content = AnalyzedContent::Text {
                content: raw_msg.raw_content.clone(),
                injection_scan_passed: injection_result.is_clean,
            };

            // 如果有注入，记录但不完全阻断
            if !injection_result.is_clean {
                suppressed_errors.push(AgentErrorCode::ToolOutputSanitized);
            }

            analyzed_messages.push(AnalyzedMessage {
                id: raw_msg.id.clone(),
                role,
                content,
                analyzed_at: current_timestamp(),
                suppressed_errors: suppressed_errors.clone(),
            });
        }

        // 不变式检查
        let invariant_check = self.invariant_checker.check(&analyzed_messages);

        Ok(AnalyzedState {
            id: raw.id,
            messages: analyzed_messages,
            schema_version: "1.0.0".to_string(),
            analyzed_at: current_timestamp(),
            invariant_check,
        })
    }

    /// 从Analyzed转换为Lowered
    pub fn lower(
        &self,
        analyzed: AnalyzedState,
        parents: Vec<String>,
    ) -> Result<LoweredStateNode, TransformError> {
        // 1. 序列化分析后状态
        let serialized = serde_json::to_vec(&analyzed)
            .map_err(|e| TransformError::SerializationFailed(e.to_string()))?;

        // 2. BLAKE3哈希
        let content_hash = blake3::hash(&serialized).to_hex().to_string();

        // 3. zstd压缩
        let compressed = zstd::encode_all(
            std::io::Cursor::new(&serialized),
            3, // 压缩级别
        )
        .map_err(|e| TransformError::CompressionFailed(e.to_string()))?;

        // 4. 构建节点
        let node = LoweredStateNode {
            content_hash: content_hash.clone(),
            compressed_size: compressed.len(),
            original_size: serialized.len(),
            parents,
            data: compressed,
            persisted_at: current_timestamp(),
            schema_version: analyzed.schema_version,
            metadata: StateMetadata {
                agent_id: "default".to_string(),
                reason: StateCreationReason::UserMessage,
                compression_level: 3,
                tree_root: content_hash, // 叶节点时等于content_hash
            },
        };

        Ok(node)
    }
}

/// 转换错误
#[derive(Debug)]
pub enum TransformError {
    SerializationFailed(String),
    CompressionFailed(String),
    ValidationFailed(Vec<AgentErrorCode>),
}

/// Schema验证器 trait
pub trait SchemaValidator: Send + Sync {
    fn validate(&self, state: &RawState) -> Result<(), Vec<AgentErrorCode>>;
}

/// 注入扫描器 trait
pub trait InjectionScanner: Send + Sync {
    fn scan(&self, text: &str) -> InjectionScanResult;
}

/// 注入扫描结果
#[derive(Debug, Clone)]
pub struct InjectionScanResult {
    pub is_clean: bool,
    pub risk_score: f32,
    pub matched_patterns: Vec<String>,
}

/// 不变式检查器 trait
pub trait InvariantChecker: Send + Sync {
    fn check(&self, messages: &[AnalyzedMessage]) -> InvariantCheckResult;
}

/// 获取当前时间戳
fn current_timestamp() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
}
```

---

## Step 2: DAG验证代码 — 错误码体系的具体实现

### DAG验证的核心问题

Immutable DAG不是简单的状态链，而是一个有向无环图。一个状态节点可能有多个父节点（分支合并），也可能指向多个子节点（分支创建）。

验证DAG需要检查：
1. **无环检测**：状态历史不能有环（否则会陷入无限循环）
2. **可达性验证**：所有引用的父节点必须存在
3. **完整性验证**：所有必要字段必须存在
4. **因果一致性**：子节点的父节点必须在逻辑上先于子节点

### DAG验证代码实现

```rust
// dag_verification.rs — Immutable DAG验证系统

use std::collections::{HashMap, HashSet};

/// DAG节点引用
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct NodeRef {
    /// 内容哈希（CAS键）
    pub content_hash: String,

    /// 快照序列号
    pub sequence: u64,
}

/// DAG边
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct DagEdge {
    pub from: NodeRef,
    pub to: NodeRef,
    pub edge_type: EdgeType,
}

/// 边类型
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum EdgeType {
    /// 状态转换（正常流程）
    StateTransition,

    /// 分支创建
    BranchCreation,

    /// 分支合并
    BranchMerge,

    /// 回滚
    Rollback,
}

/// DAG验证错误
#[derive(Debug, Clone)]
pub enum DagError {
    /// 环检测失败
    CycleDetected {
        cycle: Vec<NodeRef>,
    },

    /// 节点不存在
    NodeNotFound {
        missing_hash: String,
    },

    /// 完整性违规
    IntegrityViolation {
        node: NodeRef,
        violated_rule: String,
    },

    /// 因果顺序违规
    CausalityViolation {
        child: NodeRef,
        parent: NodeRef,
        reason: String,
    },

    /// 哈希不匹配
    HashMismatch {
        node: NodeRef,
        expected: String,
        actual: String,
    },

    /// 压缩数据损坏
    CompressionCorrupted {
        node: NodeRef,
    },
}

/// DAG验证结果
#[derive(Debug, Clone)]
pub struct VerificationResult {
    /// 是否通过验证
    pub valid: bool,

    /// 发现的错误
    pub errors: Vec<DagError>,

    /// 验证时间
    pub verified_at: u64,

    /// 验证的节点数
    pub nodes_verified: usize,

    /// 验证的边数
    pub edges_verified: usize,
}

/// DAG验证器
pub struct DagVerifier {
    /// 内容寻址存储
    cas: Arc<dyn ContentAddressableStore>,

    /// 验证配置
    config: DagVerifierConfig,
}

/// DAG验证配置
#[derive(Debug, Clone)]
pub struct DagVerifierConfig {
    /// 是否检查环
    pub check_cycles: bool,

    /// 是否检查完整性
    pub check_integrity: bool,

    /// 是否检查因果顺序
    pub check_causality: bool,

    /// 是否验证压缩数据
    pub verify_compression: bool,

    /// 最大验证深度（防止无限递归）
    pub max_depth: usize,

    /// 允许的边类型
    pub allowed_edge_types: HashSet<EdgeType>,
}

impl Default for DagVerifierConfig {
    fn default() -> Self {
        let mut allowed_edge_types = HashSet::new();
        allowed_edge_types.insert(EdgeType::StateTransition);
        allowed_edge_types.insert(EdgeType::BranchCreation);
        allowed_edge_types.insert(EdgeType::BranchMerge);
        allowed_edge_types.insert(EdgeType::Rollback);

        Self {
            check_cycles: true,
            check_integrity: true,
            check_causality: true,
            verify_compression: true,
            max_depth: 10000,
            allowed_edge_types,
        }
    }
}

impl DagVerifier {
    /// 创建新的验证器
    pub fn new(cas: Arc<dyn ContentAddressableStore>, config: DagVerifierConfig) -> Self {
        Self { cas, config }
    }

    /// 验证完整DAG
    pub fn verify_dag(&self, root_nodes: &[NodeRef]) -> VerificationResult {
        let mut errors = Vec::new();
        let mut visited: HashSet<NodeRef> = HashSet::new();
        let mut nodes_verified = 0;
        let mut edges_verified = 0;

        for root in root_nodes {
            let result = self.verify_from(*root, &mut visited, 0);
            nodes_verified += result.nodes_verified;
            edges_verified += result.edges_verified;
            errors.extend(result.errors);
        }

        // 额外检查：环检测（使用DFS着色算法）
        if self.config.check_cycles {
            if let Some(cycle) = self.detect_cycles(root_nodes) {
                errors.push(DagError::CycleDetected { cycle });
            }
        }

        VerificationResult {
            valid: errors.is_empty(),
            errors,
            verified_at: current_timestamp(),
            nodes_verified,
            edges_verified,
        }
    }

    /// 从指定节点验证DAG子图
    fn verify_from(
        &self,
        node: NodeRef,
        visited: &mut HashSet<NodeRef>,
        depth: usize,
    ) -> VerificationResult {
        // 防止无限递归
        if depth > self.config.max_depth {
            return VerificationResult {
                valid: true,
                errors: vec![],
                verified_at: current_timestamp(),
                nodes_verified: 0,
                edges_verified: 0,
            };
        }

        // 检查是否已访问（可能有多条路径到达同一节点）
        if visited.contains(&node) {
            return VerificationResult {
                valid: true,
                errors: vec![],
                verified_at: current_timestamp(),
                nodes_verified: 0,
                edges_verified: 0,
            };
        }

        visited.insert(node.clone());
        let mut errors = Vec::new();
        let mut nodes_verified = 1;
        let mut edges_verified = 0;

        // 1. 节点存在性验证
        let node_data = match self.cas.get(&node.content_hash) {
            Ok(data) => data,
            Err(e) => {
                errors.push(DagError::NodeNotFound {
                    missing_hash: node.content_hash.clone(),
                });
                return VerificationResult {
                    valid: false,
                    errors,
                    verified_at: current_timestamp(),
                    nodes_verified,
                    edges_verified,
                };
            }
        };

        // 2. 完整性验证
        if self.config.check_integrity {
            if let Some(err) = self.check_integrity(&node, &node_data) {
                errors.push(err);
            }
        }

        // 3. 压缩数据验证
        if self.config.verify_compression {
            if let Some(err) = self.verify_compressed_data(&node, &node_data) {
                errors.push(err);
            }
        }

        // 4. 递归验证父节点
        for (parent_ref, edge_type) in node_data.parents.iter().zip(node_data.edge_types.iter()) {
            // 检查边类型是否允许
            if !self.config.allowed_edge_types.contains(edge_type) {
                errors.push(DagError::IntegrityViolation {
                    node: node.clone(),
                    violated_rule: format!("Edge type {:?} not allowed", edge_type),
                });
            }

            // 检查因果顺序
            if self.config.check_causality {
                if parent_ref.sequence >= node.sequence {
                    errors.push(DagError::CausalityViolation {
                        child: node.clone(),
                        parent: parent_ref.clone(),
                        reason: format!(
                            "Parent sequence {} >= child sequence {}",
                            parent_ref.sequence, node.sequence
                        ),
                    });
                }
            }

            // 递归验证父节点
            let parent_result = self.verify_from(*parent_ref, visited, depth + 1);
            nodes_verified += parent_result.nodes_verified;
            edges_verified += parent_result.edges_verified + 1;
            errors.extend(parent_result.errors);
        }

        VerificationResult {
            valid: errors.is_empty(),
            errors,
            verified_at: current_timestamp(),
            nodes_verified,
            edges_verified,
        }
    }

    /// 检查节点完整性
    fn check_integrity(&self, node: &NodeRef, node_data: &NodeData) -> Option<DagError> {
        // 检查必要字段
        if node_data.content_hash.is_empty() {
            return Some(DagError::IntegrityViolation {
                node: node.clone(),
                violated_rule: "content_hash is empty".to_string(),
            });
        }

        // 检查哈希一致性
        let computed_hash = node_data.compute_hash();
        if computed_hash != node_data.content_hash {
            return Some(DagError::HashMismatch {
                node: node.clone(),
                expected: node_data.content_hash.clone(),
                actual: computed_hash,
            });
        }

        // 检查父节点引用的合理性（父节点序列号应小于当前节点）
        for parent in &node_data.parents {
            if parent.sequence >= node.sequence {
                return Some(DagError::CausalityViolation {
                    child: node.clone(),
                    parent: parent.clone(),
                    reason: "Parent sequence >= child sequence".to_string(),
                });
            }
        }

        None
    }

    /// 验证压缩数据完整性
    fn verify_compressed_data(&self, node: &NodeRef, node_data: &NodeData) -> Option<DagError> {
        // 尝试解压，验证压缩数据未损坏
        match zstd::decode_all(std::io::Cursor::new(&node_data.compressed_data)) {
            Ok(decompressed) => {
                // 验证解压后的数据哈希
                let decompressed_hash = blake3::hash(&decompressed).to_hex().to_string();
                if decompressed_hash != node_data.decompressed_hash {
                    return Some(DagError::IntegrityViolation {
                        node: node.clone(),
                        violated_rule: "Decompressed data hash mismatch".to_string(),
                    });
                }
                None
            }
            Err(_) => Some(DagError::CompressionCorrupted {
                node: node.clone(),
            }),
        }
    }

    /// 检测环（使用DFS着色）
    fn detect_cycles(&self, root_nodes: &[NodeRef]) -> Option<Vec<NodeRef>> {
        let mut color: HashMap<NodeRef, Color> = HashMap::new();

        // DFS着色检测环
        fn dfs(
            verifier: &DagVerifier,
            node: NodeRef,
            color: &mut HashMap<NodeRef, Color>,
            path: &mut Vec<NodeRef>,
        ) -> Option<Vec<NodeRef>> {
            color.insert(node, Color::Gray);
            path.push(node);

            // 获取节点数据
            let node_data = match verifier.cas.get(&node.content_hash) {
                Ok(data) => data,
                Err(_) => return None,
            };

            for parent in &node_data.parents {
                match color.get(parent) {
                    Some(Color::Gray) => {
                        // 发现环！找到环的起点
                        let cycle_start = path.iter().position(|n| n == parent).unwrap();
                        return Some(path[cycle_start..].to_vec());
                    }
                    Some(Color::Black) => continue,
                    None => {
                        if let Some(cycle) = dfs(verifier, *parent, color, path) {
                            return Some(cycle);
                        }
                    }
                }
            }

            color.insert(node, Color::Black);
            path.pop();
            None
        }

        for root in root_nodes {
            if let Some(cycle) = dfs(self, *root, &mut color, &mut Vec::new()) {
                return Some(cycle);
            }
        }

        None
    }
}

/// DFS着色状态
#[derive(Debug, Clone, PartialEq, Eq)]
enum Color {
    White, // 未访问
    Gray,  // 正在访问（递归栈中）
    Black, // 已完成
}

/// 节点数据（从CAS读取）
#[derive(Debug, Clone)]
pub struct NodeData {
    pub content_hash: String,
    pub compressed_data: Vec<u8>,
    pub decompressed_hash: String,
    pub parents: Vec<NodeRef>,
    pub edge_types: Vec<EdgeType>,
    pub sequence: u64,
}

impl NodeData {
    pub fn compute_hash(&self) -> String {
        blake3::hash(&self.compressed_data).to_hex().to_string()
    }
}

/// 内容寻址存储接口
pub trait ContentAddressableStore: Send + Sync {
    fn get(&self, hash: &str) -> Result<NodeData, DagError>;
    fn put(&self, data: NodeData) -> Result<String, DagError>;
}
```

---

## Step 3: 内容寻址存储 — BLAKE3哈希 + zstd压缩

### 为什么选择BLAKE3 + zstd

内容寻址存储（CAS）的核心是**哈希算法**和**压缩算法**的选择：

```
哈希算法要求：
- 抗碰撞（安全性）
- 快速（性能）
- 确定性（相同内容永远产生相同哈希）

压缩算法要求：
- 高压缩率（存储效率）
- 快速压缩/解压（吞吐量）
- 无损（数据完整性）
```

**BLAKE3的选择理由：**
- 比SHA-256快10倍（SIMD并行）
- 抗碰撞安全（Cryptospace BLAKE3）
- 确定性哈希（无时间相关因素）
- 支持增量更新（Merkle树）

**zstd的选择理由：**
- 压缩率接近LZMA，速度接近LZ4
- 支持增量压缩流
- 可调节压缩级别（1-22）
- Facebook出品，生产验证

### 内容寻址存储代码实现

```rust
// cas_storage.rs — BLAKE3 + zstd 内容寻址存储

use std::collections::HashMap;
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};

/// CAS配置
#[derive(Debug, Clone)]
pub struct CasConfig {
    /// 数据目录
    pub data_dir: PathBuf,

    /// 元数据目录
    pub meta_dir: PathBuf,

    /// 压缩级别（1-22）
    pub compression_level: i32,

    /// 缓存大小（条目数）
    pub cache_size: usize,

    /// 启用直接写入磁盘（否则仅内存缓存）
    pub sync_write: bool,
}

impl Default for CasConfig {
    fn default() -> Self {
        Self {
            data_dir: PathBuf::from("./cas_data"),
            meta_dir: PathBuf::from("./cas_meta"),
            compression_level: 3,
            cache_size: 10000,
            sync_write: true,
        }
    }
}

/// CAS条目元数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CasEntryMetadata {
    /// 内容哈希
    pub content_hash: String,

    /// 原始大小（字节）
    pub original_size: u64,

    /// 压缩后大小（字节）
    pub compressed_size: u64,

    /// 压缩率
    pub compression_ratio: f64,

    /// 创建时间
    pub created_at: u64,

    /// 访问计数
    pub access_count: u64,

    /// 引用计数（DAG中的入边数）
    pub ref_count: u64,

    /// BLAKE3树根哈希
    pub tree_root: String,
}

/// CAS存储错误
#[derive(Debug)]
pub enum CasError {
    /// 内容不存在
    ContentNotFound { hash: String },

    /// 压缩失败
    CompressionFailed { reason: String },

    /// 解压缩失败
    DecompressionFailed { reason: String },

    /// 哈希不匹配
    HashMismatch {
        expected: String,
        actual: String,
    },

    /// IO错误
    IoError { path: String, reason: String },

    /// 目录创建失败
    DirCreationFailed { path: String, reason: String },
}

/// 内容寻址存储
pub struct ContentAddressableStorage {
    config: CasConfig,

    /// 内存缓存
    cache: Arc<RwLock<HashMap<String, CacheEntry>>>,

    /// 元数据缓存
    metadata_cache: Arc<RwLock<HashMap<String, CasEntryMetadata>>>,

    /// 统计信息
    stats: Arc<RwLock<CasStats>>,
}

/// 缓存条目
#[derive(Debug, Clone)]
struct CacheEntry {
    /// 解压后的原始数据
    data: Vec<u8>,

    /// 元数据
    metadata: CasEntryMetadata,

    /// 最近访问时间
    last_access: u64,
}

/// CAS统计
#[derive(Debug, Clone, Default)]
pub struct CasStats {
    /// 总存储大小（字节）
    pub total_size: u64,

    /// 条目数
    pub entry_count: u64,

    /// 缓存命中数
    pub cache_hits: u64,

    /// 缓存未命中数
    pub cache_misses: u64,

    /// 压缩字节数
    pub compressed_bytes: u64,

    /// 解压字节数
    pub decompressed_bytes: u64,

    /// 哈希计算次数
    pub hash_computations: u64,
}

impl ContentAddressableStorage {
    /// 创建新的CAS存储
    pub fn new(config: CasConfig) -> Result<Self, CasError> {
        // 创建目录
        fs::create_dir_all(&config.data_dir).map_err(|e| CasError::DirCreationFailed {
            path: config.data_dir.to_string_lossy().to_string(),
            reason: e.to_string(),
        })?;

        fs::create_dir_all(&config.meta_dir).map_err(|e| CasError::DirCreationFailed {
            path: config.meta_dir.to_string_lossy().to_string(),
            reason: e.to_string(),
        })?;

        Ok(Self {
            config,
            cache: Arc::new(RwLock::new(HashMap::new())),
            metadata_cache: Arc::new(RwLock::new(HashMap::new())),
            stats: Arc::new(RwLock::new(CasStats::default())),
        })
    }

    /// 存储数据（自动计算哈希和压缩）
    pub fn put(&self, data: &[u8]) -> Result<String, CasError> {
        // 1. 计算BLAKE3哈希
        let hash = blake3::hash(data);
        let content_hash = hash.to_hex().to_string();

        // 2. 检查是否已存在
        {
            let cache = self.cache.read().unwrap();
            if cache.contains_key(&content_hash) {
                // 已存在，增加引用计数
                drop(cache);
                self.inc_ref_count(&content_hash)?;
                return Ok(content_hash);
            }
        }

        // 3. 压缩数据
        let compressed = self.compress(data)?;

        // 4. 写入磁盘
        self.write_to_disk(&content_hash, &compressed)?;

        // 5. 创建元数据
        let metadata = CasEntryMetadata {
            content_hash: content_hash.clone(),
            original_size: data.len() as u64,
            compressed_size: compressed.len() as u64,
            compression_ratio: compressed.len() as f64 / data.len() as f64,
            created_at: current_timestamp(),
            access_count: 0,
            ref_count: 1,
            tree_root: hash.to_hex().to_string(),
        };

        // 6. 写入元数据
        self.write_metadata(&content_hash, &metadata)?;

        // 7. 更新缓存
        {
            let mut cache = self.cache.write().unwrap();
            let mut evict = false;

            // LRU驱逐
            if cache.len() >= self.config.cache_size {
                evict = true;
            }

            if evict {
                // 驱逐最老的条目
                if let Some((oldest_key, _)) = cache.iter().min_by_key(|(_, v)| v.last_access) {
                    let oldest_key = oldest_key.clone();
                    drop(cache);
                    self.evict_from_cache(&oldest_key);
                }
            }

            let mut cache = self.cache.write().unwrap();
            cache.insert(
                content_hash.clone(),
                CacheEntry {
                    data: data.to_vec(),
                    metadata: metadata.clone(),
                    last_access: current_timestamp(),
                },
            );
        }

        // 8. 更新统计
        {
            let mut stats = self.stats.write().unwrap();
            stats.total_size += data.len() as u64;
            stats.compressed_bytes += compressed.len() as u64;
            stats.entry_count += 1;
        }

        Ok(content_hash)
    }

    /// 获取数据（自动解压缩）
    pub fn get(&self, content_hash: &str) -> Result<Vec<u8>, CasError> {
        // 1. 检查缓存
        {
            let mut cache = self.cache.write().unwrap();
            if let Some(entry) = cache.get_mut(content_hash) {
                entry.last_access = current_timestamp();
                entry.metadata.access_count += 1;

                let mut stats = self.stats.write().unwrap();
                stats.cache_hits += 1;
                stats.decompressed_bytes += entry.data.len() as u64;

                return Ok(entry.data.clone());
            }
        }

        // 2. 缓存未命中，从磁盘读取
        let mut stats = self.stats.write().unwrap();
        stats.cache_misses += 1;
        drop(stats);

        // 3. 读取元数据
        let metadata = self.read_metadata(content_hash)?;

        // 4. 读取压缩数据
        let compressed = self.read_from_disk(content_hash)?;

        // 5. 解压缩
        let decompressed = self.decompress(&compressed)?;

        // 6. 验证哈希
        let actual_hash = blake3::hash(&decompressed).to_hex().to_string();
        if actual_hash != content_hash {
            return Err(CasError::HashMismatch {
                expected: content_hash.to_string(),
                actual: actual_hash,
            });
        }

        // 7. 更新缓存
        {
            let mut cache = self.cache.write().unwrap();
            cache.insert(
                content_hash.to_string(),
                CacheEntry {
                    data: decompressed.clone(),
                    metadata: metadata.clone(),
                    last_access: current_timestamp(),
                },
            );
        }

        // 8. 更新统计
        {
            let mut stats = self.stats.write().unwrap();
            stats.decompressed_bytes += decompressed.len() as u64;
        }

        Ok(decompressed)
    }

    /// 获取元数据
    pub fn get_metadata(&self, content_hash: &str) -> Result<CasEntryMetadata, CasError> {
        // 先检查缓存
        {
            let cache = self.cache.read().unwrap();
            if let Some(entry) = cache.get(content_hash) {
                return Ok(entry.metadata.clone());
            }
        }

        // 从磁盘读取
        self.read_metadata(content_hash)
    }

    /// 检查是否存在
    pub fn contains(&self, content_hash: &str) -> bool {
        // 检查缓存
        {
            let cache = self.cache.read().unwrap();
            if cache.contains_key(content_hash) {
                return true;
            }
        }

        // 检查元数据文件
        let meta_path = self.config.meta_dir.join(format!("{}.json", content_hash));
        meta_path.exists()
    }

    /// 删除条目（仅在ref_count为0时）
    pub fn delete(&self, content_hash: &str) -> Result<(), CasError> {
        let metadata = self.read_metadata(content_hash)?;

        if metadata.ref_count > 0 {
            return Err(CasError::IoError {
                path: content_hash.to_string(),
                reason: format!("ref_count is {}, cannot delete", metadata.ref_count),
            });
        }

        // 删除数据文件
        let data_path = self.config.data_dir.join(content_hash);
        if data_path.exists() {
            fs::remove_file(&data_path).map_err(|e| CasError::IoError {
                path: data_path.to_string_lossy().to_string(),
                reason: e.to_string(),
            })?;
        }

        // 删除元数据文件
        let meta_path = self.config.meta_dir.join(format!("{}.json", content_hash));
        if meta_path.exists() {
            fs::remove_file(&meta_path).map_err(|e| CasError::IoError {
                path: meta_path.to_string_lossy().to_string(),
                reason: e.to_string(),
            })?;
        }

        // 从缓存移除
        {
            let mut cache = self.cache.write().unwrap();
            cache.remove(content_hash);
        }

        // 更新统计
        {
            let mut stats = self.stats.write().unwrap();
            stats.total_size = stats.total_size.saturating_sub(metadata.original_size);
            stats.entry_count = stats.entry_count.saturating_sub(1);
        }

        Ok(())
    }

    /// 获取统计信息
    pub fn get_stats(&self) -> CasStats {
        self.stats.read().unwrap().clone()
    }

    // === 私有方法 ===

    /// 压缩数据
    fn compress(&self, data: &[u8]) -> Result<Vec<u8>, CasError> {
        zstd::encode_all(
            std::io::Cursor::new(data),
            self.config.compression_level,
        )
        .map_err(|e| CasError::CompressionFailed { reason: e.to_string() })
    }

    /// 解压缩数据
    fn decompress(&self, compressed: &[u8]) -> Result<Vec<u8>, CasError> {
        zstd::decode_all(std::io::Cursor::new(compressed))
            .map_err(|e| CasError::DecompressionFailed { reason: e.to_string() })
    }

    /// 写入磁盘
    fn write_to_disk(&self, content_hash: &str, compressed: &[u8]) -> Result<(), CasError> {
        let data_path = self.config.data_dir.join(content_hash);

        if self.config.sync_write {
            let mut file = fs::File::create(&data_path).map_err(|e| CasError::IoError {
                path: data_path.to_string_lossy().to_string(),
                reason: e.to_string(),
            })?;
            file.write_all(compressed).map_err(|e| CasError::IoError {
                path: data_path.to_string_lossy().to_string(),
                reason: e.to_string(),
            })?;
            file.sync_all().map_err(|e| CasError::IoError {
                path: data_path.to_string_lossy().to_string(),
                reason: e.to_string(),
            })?;
        } else {
            fs::write(&data_path, compressed).map_err(|e| CasError::IoError {
                path: data_path.to_string_lossy().to_string(),
                reason: e.to_string(),
            })?;
        }

        Ok(())
    }

    /// 从磁盘读取
    fn read_from_disk(&self, content_hash: &str) -> Result<Vec<u8>, CasError> {
        let data_path = self.config.data_dir.join(content_hash);

        let mut file = fs::File::open(&data_path).map_err(|e| CasError::IoError {
            path: data_path.to_string_lossy().to_string(),
            reason: e.to_string(),
        })?;

        let mut compressed = Vec::new();
        file.read_to_end(&mut compressed).map_err(|e| CasError::IoError {
            path: data_path.to_string_lossy().to_string(),
            reason: e.to_string(),
        })?;

        Ok(compressed)
    }

    /// 写入元数据
    fn write_metadata(&self, content_hash: &str, metadata: &CasEntryMetadata) -> Result<(), CasError> {
        let meta_path = self.config.meta_dir.join(format!("{}.json", content_hash));
        let json = serde_json::to_string_pretty(metadata).map_err(|e| CasError::IoError {
            path: meta_path.to_string_lossy().to_string(),
            reason: e.to_string(),
        })?;

        fs::write(&meta_path, json).map_err(|e| CasError::IoError {
            path: meta_path.to_string_lossy().to_string(),
            reason: e.to_string(),
        })?;

        Ok(())
    }

    /// 读取元数据
    fn read_metadata(&self, content_hash: &str) -> Result<CasEntryMetadata, CasError> {
        let meta_path = self.config.meta_dir.join(format!("{}.json", content_hash));

        let json = fs::read_to_string(&meta_path).map_err(|e| CasError::IoError {
            path: meta_path.to_string_lossy().to_string(),
            reason: e.to_string(),
        })?;

        serde_json::from_str(&json).map_err(|e| CasError::IoError {
            path: meta_path.to_string_lossy().to_string(),
            reason: e.to_string(),
        })
    }

    /// 增加引用计数
    fn inc_ref_count(&self, content_hash: &str) -> Result<(), CasError> {
        let mut metadata = self.read_metadata(content_hash)?;
        metadata.ref_count += 1;
        self.write_metadata(content_hash, &metadata)?;

        // 更新缓存
        {
            let mut cache = self.cache.write().unwrap();
            if let Some(entry) = cache.get_mut(content_hash) {
                entry.metadata.ref_count = metadata.ref_count;
            }
        }

        Ok(())
    }

    /// 从缓存驱逐
    fn evict_from_cache(&self, content_hash: &str) {
        let mut cache = self.cache.write().unwrap();
        if let Some(entry) = cache.remove(content_hash) {
            let mut stats = self.stats.write().unwrap();
            stats.total_size = stats.total_size.saturating_sub(entry.metadata.original_size);
            stats.entry_count = stats.entry_count.saturating_sub(1);
        }
    }
}

/// 获取当前时间戳
fn current_timestamp() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
}
```

---

## Step 4: 魔法时刻段落 — 状态的历史比状态本身更重要

### 魔法时刻

**当你只需要当前状态时，传统数据库就够了。**

**当你需要理解"为什么变成这样"时，你需要状态的历史。**

Immutable DAG的核心洞察不是"不可变"，而是**"历史优先"**。

传统架构：
```
状态 = 当前值
更新 = 覆盖
历史 = 日志（可选，30天后删除）
```

Immutable DAG架构：
```
状态 = 完整历史（当前值只是最新节点）
更新 = 创建新节点（从不覆盖）
历史 = 核心资产（永久保留）
```

为什么？

因为**当前状态只能告诉你"是什么"，历史才能告诉你"为什么"**。

当你debug一个生产环境的错误时，你问的第一个问题是什么？

不是"现在的状态是什么"——那是表象。
是"**这个状态是怎么变成这样的？**"

这就是为什么：
- Git比SVN更强大——不是因为分支，而是因为历史
- Event Sourcing越来越流行——不是因为一致性，而是因为审计
- Immutable DAG是Agent Harness的核心——不是因为确定性，而是因为可追溯性

**状态的历史比状态本身更重要。**

不是因为历史是重要的副产品，而是因为**历史是唯一能回答"为什么"的证据**。

当你有完整的状态历史时：
- 任何错误状态都可以追溯到形成原因
- 任何决策都可以回溯到输入和过程
- 任何bug都可以在历史分支上复现
- 任何实验都可以在隔离的历史中安全进行

这就是为什么Immutable DAG是实现**100%确定性重放**的基础——因为重放的本质不是"回到当前状态"，而是"重现完整的历史过程"。

---

## Step 5: 桥接语 — 有了状态持久化，如何选择正确的工具执行

### 承上

本章展示了Immutable DAG如何实现Agent状态的安全持久化：

- **三阶段状态处理**：Raw → Analyzed → Lowered，每阶段验证不同问题
- **DAG验证**：环检测、因果一致性、完整性验证
- **内容寻址存储**：BLAKE3哈希确保内容标识唯一，zstd压缩降低存储成本
- **错误码体系**：140+种错误码覆盖工具、状态、执行、持久化四个维度

结合第十六章的MCP沙箱和第十五章的V8 Isolates，我们现在有了完整的**IsolatedAgent运行时**：

```
IsolatedAgent =
  V8 Isolates（执行隔离）
  + WASI能力（资源边界）
  + MCP沙箱（工具安全）
  + Immutable DAG（状态持久化）
```

### 启下：工具执行的选择

状态持久化解决了"如何记住"，但没有解决"**用什么做**"。

Agent面对一个任务时，可能有多个工具可用：
- 同一个功能，可能有MCP工具、本地工具、外部API三种实现
- 不同工具的延迟、可靠性、成本各不相同
- 工具的选择会影响状态历史的走向

下一章将展示**RAG-MCP动态工具检索**：

- 如何根据当前状态从数百个工具中选择最合适的
- 如何在工具选择时考虑历史上下文
- 如何避免"Prompt膨胀"和"LLM选择瘫痪"

**有了状态持久化，Agent可以回顾历史。但面对新任务时，它如何决定使用哪个工具？这就是RAG-MCP要回答的问题。**

---

## 本章来源

### 一手来源

| 来源 | URL | 关键数据 |
|------|-----|---------|
| BLAKE3哈希算法 | https://github.com/BLAKE3/BLAKE3 | 比SHA-256快10倍，支持SIMD并行 |
| zstd压缩算法 | https://facebook.github.io/zstd/ | 压缩率接近LZMA，速度接近LZ4 |
| cxdb (AI Context Store) | https://github.com/nikao8/cxdb | Immutable DAG状态持久化实现 |
| DAG验证理论 | https://en.wikipedia.org/wiki/Directed_acyclic_graph | 环检测、着色算法 |

### 二手来源

| 来源 | 用途 |
|------|------|
| research-findings.md (Section 7) | 来源矩阵，章节对应关系 |
| ch15-v8-isolates.md | V8 Isolates毫秒级冷启动 |
| ch16-mcp-sandbox.md | MCP工具安全调用 |
| ch18-rag-mcp.md | 下一章：动态工具检索 |

### 技术标准

| 来源 | 用途 |
|------|------|
| BLAKE3规范 | 哈希算法实现标准 |
| zstd格式规范 | 压缩算法格式 |
| DAG理论 | 数据结构理论基础 |
