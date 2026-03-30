# 第五部分：生产部署层 — GRT+WASM生产部署实战

## 本章Q

**如何将Rust核心编译为.wasm并部署？**

## 魔法时刻

从TS到Rust到WASM，不是在构建不同功能，而是在构建不同的确定性保证。

TypeScript给你的是"运行时检查"。Rust给你的是"编译时证明"。WASM给你的是"沙箱内物理上不可能"。

三个层级，三种不同程度的确定性。当你把它们组合起来，你不是在增加功能，你是在构建一个**不可能出错的系统**。

第19章从零构建了最小Harness栈，验证了每个组件的行为。本章将此栈从本地开发环境迁移到生产环境：

1. **Rust核心**编译为WASM模块——用cargo-component实现WIT接口定义
2. **WasmEdge运行时**作为零信任沙箱——长周期任务的网络隔离执行
3. **Inngest事件驱动**架构——实现断点续传，保证长时任务不丢失进度

核心问题从"能不能验证"变成"能不能在生产环境持续运行"。答案是一套将Rust编译、WASM隔离、事件驱动断点续传整合的完整GRT生产栈。

---

## 魔法时刻

**从TS到Rust到WASM，不是在构建不同功能，而是在构建不同的确定性保证。**

TypeScript给你的是"运行时检查"。Rust给你的是"编译时证明"。WASM给你的是"沙箱内物理上不可能"。

三个层级，三种不同程度的确定性。当你把它们组合起来，你不是在增加功能，你是在构建一个**不可能出错的系统**。

---

## Step 1: cargo-component代码 — Rust核心逻辑编译为.wasm

### 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    TypeScript 控制平面                        │
│  (Inngest Step Functions / WasmEdge Runner)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    WASM 沙箱 (WasmEdge)                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  WIT 接口层 (cargo-component 生成的 bindings)          │  │
│  └───────────────────────────────────────────────────────┘  │
│                              │                               │
│                              ▼                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Rust 核心逻辑 (text-processing / calculation)          │  │
│  │  - 确定性保证：编译时所有权 + 运行时线性内存           │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 项目结构

```
grt-wasm-production/
├── src/                          # TypeScript 控制平面
│   ├── wasmedge-runner.ts        # WasmEdge 运行时封装
│   ├── inngest-steps.ts          # Inngest 步骤函数
│   └── checkpoint-store.ts       # 断点存储
├── wasm-core/                    # Rust WASM 核心
│   ├── Cargo.toml                # cargo-component 项目配置
│   ├── wit/
│   │   └── grt-core.wit          # WIT 接口定义
│   └── src/
│       └── lib.rs                # Rust 核心逻辑
├── wasm/                         # 编译产物
│   └── grt_core.wasm             # 编译后的 WASM 模块
└── package.json
```

### Cargo.toml — cargo-component 项目配置

```toml
# wasm-core/Cargo.toml
# cargo-component 是构建 WASM 组件的标准工具
# 它自动生成 WIT bindings，让我们可以用 Rust 实现 WIT 接口

[package]
name = "grt-core"
version = "0.1.0"
edition = "2021"

[dependencies]
# wit-bindgen 是 WIT 接口的 Rust 实现
wit-bindgen = "0.25"
# serde 用于序列化/反序列化
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
# 日志（编译进 WASM 后可用于调试）
log = "0.4"
env_logger = "0.11"

[lib]
# cargo-component 会将此 crate 编译为 WASM 组件
crate-type = ["cdylib"]

[profile.release]
# 生产构建优化
opt-level = "s"
lto = true
```

### wit/grt-core.wit — WIT 接口定义

```wit
// wasm-core/wit/grt-core.wit
// WIT (WebAssembly Interface Types) 是 WASM 组件之间的接口描述语言
// 定义了 Rust 核心对外暴露的接口

package grt:core@0.1.0;

interface text-processing {
  // 文本处理的错误类型
  variant processing-error {
    empty-input,
    invalid-unicode,
    length-exceeded(u32),
    internal(string),
  }

  // 文本分析结果
  record analysis-result {
    word-count: u32,
    char-count: u32,
    line-count: u32,
    avg-word-length: f32,
    most-common-word: option<string>,
  }

  // 分析文本，返回统计结果
  analyze-text: func(input: string) -> result<analysis-result, processing-error>;

  // 标准化文本（小写、去除标点、trim）
  normalize-text: func(input: string) -> result<string, processing-error>;

  // 计算文本相似度（基于单词集合Jaccard相似度）
  similarity: func(text_a: string, text_b: string) -> result<f32, processing-error>;
}

interface calculation {
  // 计算错误类型
  variant calc-error {
    division-by-zero,
    overflow,
    invalid-input(string),
  }

  // 批量计算请求
  record batch-request {
    operations: list<operation>,
    checkpoint-id: option<string>,
  }

  // 单个计算操作
  variant operation {
    add(u64, u64),
    subtract(u64, u64),
    multiply(u64, u64),
    divide(u64, u64),
  }

  // 批量计算响应（支持分页）
  record batch-response {
    results: list<result<u64, calc-error>>,
    next-checkpoint: option<string>,
    total-processed: u32,
  }

  // 执行批量计算（可中断）
  execute-batch: func(request: batch-request) -> batch-response;
}

world grt-core {
  export text-processing;
  export calculation;
}
```

### src/lib.rs — Rust 核心逻辑实现

```rust
// wasm-core/src/lib.rs
// Rust 核心逻辑：文本处理 + 批量计算
// 使用 wit-bindgen 生成 WASM 组件接口

use std::collections::HashMap;
use wit_bindgen::generate;

generate!( {
    world: "grt-core",
    exports: {
        "grt:core/text-processing": TextProcessing,
        "grt:core/calculation": Calculation,
    }
});

// ============================================================
// 文本处理实现
// ============================================================

struct TextProcessing;

impl exports::grt::core::text_processing::Guest for TextProcessing {
    fn analyze_text(input: String) -> Result<exports::grt::core::text_processing::AnalysisResult, exports::grt::core::text_processing::ProcessingError> {
        // 空输入检查
        if input.is_empty() {
            return Err(exports::grt::core::text_processing::ProcessingError::EmptyInput);
        }

        // Unicode 验证
        if !input.is_char_boundary(input.len()) {
            return Err(exports::grt::core::text_processing::ProcessingError::InvalidUnicode);
        }

        let words: Vec<&str> = input.split_whitespace().collect();
        let word_count = words.len() as u32;
        let char_count = input.chars().count() as u32;
        let line_count = input.lines().count() as u32;

        // 计算平均单词长度
        let total_word_length: u32 = words.iter().map(|w| w.chars().count() as u32).sum();
        let avg_word_length = if word_count > 0 {
            total_word_length as f32 / word_count as f32
        } else {
            0.0
        };

        // 统计最常见单词
        let mut word_frequencies = HashMap::new();
        for word in &words {
            let normalized = word.to_lowercase();
            *word_frequencies.entry(normalized).or_insert(0) += 1;
        }

        let most_common_word = word_frequencies
            .into_iter()
            .max_by_key(|(_, count)| *count)
            .map(|(word, _)| word);

        Ok(exports::grt::core::text_processing::AnalysisResult {
            word_count,
            char_count,
            line_count,
            avg_word_length,
            most_common_word,
        })
    }

    fn normalize_text(input: String) -> Result<String, exports::grt::core::text_processing::ProcessingError> {
        if input.is_empty() {
            return Err(exports::grt::core::text_processing::ProcessingError::EmptyInput);
        }

        // 标准化：转小写、去除标点、trim
        let normalized: String = input
            .chars()
            .filter(|c| c.is_alphanumeric() || c.is_whitespace())
            .map(|c| c.to_ascii_lowercase())
            .collect();

        let trimmed = normalized.trim().to_string();

        // 长度检查（防止缓冲区过大）
        if trimmed.len() > 1_000_000 {
            return Err(exports::grt::core::text_processing::ProcessingError::LengthExceeded(trimmed.len() as u32));
        }

        Ok(trimmed)
    }

    fn similarity(text_a: String, text_b: String) -> Result<f32, exports::grt::core::text_processing::ProcessingError> {
        if text_a.is_empty() || text_b.is_empty() {
            return Err(exports::grt::core::text_processing::ProcessingError::EmptyInput);
        }

        // Jaccard 相似度：基于单词集合
        let set_a: std::collections::HashSet<String> = text_a
            .split_whitespace()
            .map(|s| s.to_lowercase())
            .collect();

        let set_b: std::collections::HashSet<String> = text_b
            .split_whitespace()
            .map(|s| s.to_lowercase())
            .collect();

        let intersection = set_a.intersection(&set_b).count() as f32;
        let union = set_a.union(&set_b).count() as f32;

        if union == 0.0 {
            return Ok(0.0);
        }

        Ok(intersection / union)
    }
}

// ============================================================
// 批量计算实现（支持断点续传）
// ============================================================

struct Calculation;

impl exports::grt::core::calculation::Guest for Calculation {
    fn execute_batch(
        request: exports::grt::core::calculation::BatchRequest
    ) -> exports::grt::core::calculation::BatchResponse {
        let mut results: Vec<Result<u64, exports::grt::core::calculation::CalcError>> = Vec::new();
        let mut total-processed = 0u32;

        // 如果有 checkpoint-id，从指定位置继续处理
        let start-index = request.checkpoint-id
            .as_ref()
            .and_then(|id| id.parse::<usize>().ok())
            .unwrap_or(0);

        let operations = request.operations;

        for (i, op) in operations.iter().enumerate().skip(start-index) {
            let result = match op {
                exports::grt::core::calculation::Operation::Add(a, b) => {
                    // 检测溢出
                    a.checked_add(*b).map(|r| r as u64).ok_or_else(||
                        exports::grt::core::calculation::CalcError::Overflow
                    )
                }
                exports::grt::core::calculation::Operation::Subtract(a, b) => {
                    Ok(*a as u64 - *b as u64)
                }
                exports::grt::core::calculation::Operation::Multiply(a, b) => {
                    a.checked_mul(*b).map(|r| r as u64).ok_or_else(||
                        exports::grt::core::calculation::CalcError::Overflow
                    )
                }
                exports::grt::core::calculation::Operation::Divide(a, b) => {
                    if *b == 0 {
                        Err(exports::grt::core::calculation::CalcError::DivisionByZero)
                    } else {
                        Ok(*a as u64 / *b as u64)
                    }
                }
            };

            results.push(result);
            total-processed += 1;

            // 每处理 100 个操作生成一个 checkpoint
            // checkpoint-id 用于断点续传
            if (i + 1) % 100 == 0 {
                let checkpoint-id = (i + 1).to_string();
                return exports::grt::core::calculation::BatchResponse {
                    results,
                    next-checkpoint: Some(checkpoint-id),
                    total-processed,
                };
            }
        }

        // 处理完成，没有下一个 checkpoint
        exports::grt::core::calculation::BatchResponse {
            results,
            next-checkpoint: None,
            total-processed,
        }
    }
}
```

### 构建命令

```bash
# 安装 cargo-component（如果尚未安装）
cargo install cargo-component

# 在 wasm-core 目录下构建
cd wasm-core
cargo component build --release

# 产物位于 target/wasm32-wasip2/release/grt_core.wasm
```

---

## Step 2: WasmEdge部署 — 零信任环境长周期任务

### wasmedge-runner.ts — WasmEdge 运行时封装

```typescript
// src/wasmedge-runner.ts
// WasmEdge 运行时封装：处理长周期任务的零信任沙箱执行

import { WasmEdgeRuntime } from '@aspectos/wasmedge';
import * as fs from 'fs/promises';
import * as path from 'path';

// WASM 模块配置接口
interface WasmRunnerConfig {
  // WASM 文件路径
  wasmPath: string;
  // 是否启用 WASI（文件系统等系统接口）
  enableWASI: boolean;
  // 网络隔离配置
  networkIsolation: boolean;
  // 允许访问的主机列表（空 = 完全隔离）
  allowedHosts?: string[];
  // 内存限制（字节）
  memoryLimit?: number;
  // 执行超时（毫秒）
  timeout?: number;
}

// WASM 执行结果
interface WasmExecutionResult {
  // 标准输出
  stdout: string;
  // 标准错误
  stderr: string;
  // 退出码
  exitCode: number;
  // 执行时间（毫秒）
  executionTimeMs: number;
  // 内存峰值（KB）
  peakMemoryKb?: number;
}

// 断点状态
interface CheckpointState {
  // 最后一个 checkpoint 的 ID
  lastCheckpointId: string;
  // 已处理的操作数
  processedCount: number;
  // 下一次执行的起始索引
  nextStartIndex: number;
}

/**
 * WasmEdgeRunner — 零信任环境下的 WASM 执行器
 *
 * 设计原则：
 * 1. 网络隔离：WASM 模块无法发起网络请求
 * 2. 内存限制：防止恶意模块消耗过多内存
 * 3. 超时控制：防止无限循环
 * 4. 断点支持：支持长周期任务的中断和恢复
 */
export class WasmEdgeRunner {
  private runtime: WasmEdgeRuntime;
  private config: WasmRunnerConfig;
  private isInitialized: boolean = false;

  constructor(config: WasmRunnerConfig) {
    this.config = config;
    this.runtime = new WasmEdgeRuntime({
      // WASM 文件路径
      wasmPath: config.wasmPath,
      // WASI 配置：允许标准输入输出和一些文件系统操作
      wasi: config.enableWASI
        ? {
            preopens: ['/tmp'], // 允许访问 /tmp 目录
            args: [],
            env: {},
          }
        : undefined,
      // 网络隔离：完全禁止网络访问
      network: config.networkIsolation
        ? {
            // 零信任：默认禁止所有网络请求
            allowedHosts: config.allowedHosts ?? [],
            // 阻止访问敏感文件
            blockedPaths: [
              '/etc/passwd',
              '/etc/hosts',
              '/etc/shadow',
              '/root/.ssh',
            ],
          }
        : undefined,
      // 内存限制
      memory: {
        min: 16 * 1024 * 1024, // 16MB 最小
        max: config.memoryLimit ?? 256 * 1024 * 1024, // 256MB 最大
      },
    });
  }

  /**
   * 初始化运行时
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }
    await this.runtime.instantiate();
    this.isInitialized = true;
  }

  /**
   * 执行 WASM 模块（短时任务）
   */
  async execute(input: string): Promise<WasmExecutionResult> {
    await this.initialize();

    const startTime = Date.now();

    const result = await this.runtime.execute(input, {
      timeout: this.config.timeout ?? 30000, // 默认 30 秒超时
    });

    const executionTimeMs = Date.now() - startTime;

    return {
      stdout: result.stdout ?? '',
      stderr: result.stderr ?? '',
      exitCode: result.exitCode ?? 0,
      executionTimeMs,
      peakMemoryKb: result.peakMemoryKb,
    };
  }

  /**
   * 执行长周期任务（带断点续传）
   * 返回结果和下一个 checkpoint
   */
  async executeWithCheckpoint(
    input: string,
    checkpoint: CheckpointState | null
  ): Promise<{
    result: WasmExecutionResult;
    nextCheckpoint: CheckpointState | null;
  }> {
    await this.initialize();

    // 构造带 checkpoint 的输入
    const request = {
      input,
      checkpoint: checkpoint?.lastCheckpointId ?? null,
    };

    const startTime = Date.now();

    // 执行 WASM
    const execResult = await this.runtime.execute(JSON.stringify(request), {
      timeout: this.config.timeout ?? 60000, // 长任务 60 秒超时
    });

    const executionTimeMs = Date.now() - startTime;

    // 解析输出
    let output: {
      results?: unknown[];
      nextCheckpoint?: string;
      totalProcessed?: number;
    };

    try {
      output = JSON.parse(execResult.stdout);
    } catch {
      return {
        result: {
          stdout: execResult.stdout,
          stderr: execResult.stderr,
          exitCode: execResult.exitCode,
          executionTimeMs,
        },
        nextCheckpoint: null,
      };
    }

    // 计算下一个 checkpoint
    const nextCheckpoint: CheckpointState | null = output.nextCheckpoint
      ? {
          lastCheckpointId: output.nextCheckpoint,
          processedCount: output.totalProcessed ?? 0,
          nextStartIndex: parseInt(output.nextCheckpoint, 10),
        }
      : null;

    return {
      result: {
        stdout: execResult.stdout,
        stderr: execResult.stderr,
        exitCode: execResult.exitCode,
        executionTimeMs,
      },
      nextCheckpoint,
    };
  }

  /**
   * 终止运行时，释放资源
   */
  async terminate(): Promise<void> {
    await this.runtime.terminate();
    this.isInitialized = false;
  }

  /**
   * 获取运行时指标
   */
  getMetrics(): {
    isInitialized: boolean;
    memoryLimit: number;
    networkIsolated: boolean;
  } {
    return {
      isInitialized: this.isInitialized,
      memoryLimit: this.config.memoryLimit ?? 256 * 1024 * 1024,
      networkIsolated: this.config.networkIsolation,
    };
  }
}

/**
 * 创建 WasmEdgeRunner 的工厂函数
 */
export function createWasmEdgeRunner(
  wasmPath: string,
  options?: {
    enableWASI?: boolean;
    networkIsolation?: boolean;
    memoryLimit?: number;
    timeout?: number;
  }
): WasmEdgeRunner {
  return new WasmEdgeRunner({
    wasmPath,
    enableWASI: options?.enableWASI ?? false,
    networkIsolation: options?.networkIsolation ?? true,
    memoryLimit: options?.memoryLimit,
    timeout: options?.timeout,
  });
}
```

### WasmEdge 配置文件

```yaml
# wasmedge-config.yaml
# WasmEdge 运行时配置

# 全局选项
options:
  # 内存限制
  memory-limit: 256MiB
  # 线程数
  thread-count: 4

# WASI 配置
wasi:
  # 允许访问的目录
  preopens:
    - path: /tmp
      permissions: read,write
    - path: /var/tmp
      permissions: read,write

# 网络配置（零信任）
network:
  # 默认禁止所有网络访问
  default-policy: deny
  # 显式允许的地址
  allowed:
    # 不允许任何地址 = 完全隔离
    - host: "*"
      ports: []

# 沙箱策略
sandbox:
  # 禁止符号链接
  allow-symlinks: false
  # 禁止特殊文件
  allow-special-files: false
  # 最大文件大小
  max-file-size: 10MiB
```

---

## Step 3: Inngest集成 — 断点续传的完整实现

### 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                      Inngest 事件驱动平台                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Step Functions (DAG 步骤函数)                            │  │
│  │                                                           │  │
│  │   ┌──────────┐    ┌──────────┐    ┌──────────┐          │  │
│  │   │ Step 1   │───▶│ Step 2   │───▶│ Step 3   │          │  │
│  │   │ 文本分析  │    │ 批量计算  │    │ 结果聚合  │          │  │
│  │   └──────────┘    └──────────┘    └──────────┘          │  │
│  │         │              │              │                   │  │
│  │         ▼              ▼              ▼                   │  │
│  │   ┌──────────────────────────────────────────┐           │  │
│  │   │  Checkpoint Store (断点存储)             │           │  │
│  │   │  - Redis / Durable Object                │           │  │
│  │   └──────────────────────────────────────────┘           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WasmEdge 运行时集群                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Worker 1   │  │  Worker 2   │  │  Worker N   │             │
│  │ (WASM Core) │  │ (WASM Core) │  │ (WASM Core) │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### inngest-steps.ts — Inngest 步骤函数定义

```typescript
// src/inngest-steps.ts
// Inngest 事件驱动步骤函数：实现断点续传的完整逻辑

import { Inngest, Step, RetryConfig } from 'inngest';
import { WasmEdgeRunner } from './wasmedge-runner';

// 创建 Inngest 客户端
export const inngest = new Inngest({
  id: 'grt-production',
  eventKey: process.env.INNGEST_EVENT_KEY,
});

// ============================================================
// 断点存储接口
// ============================================================

interface CheckpointStore {
  // 保存 checkpoint
  save(id: string, state: CheckpointState): Promise<void>;
  // 读取 checkpoint
  load(id: string): Promise<CheckpointState | null>;
  // 删除 checkpoint
  delete(id: string): Promise<void>;
}

// Redis Checkpoint Store 实现
// 使用 Redis 存储断点状态，支持跨 worker 访问
export class RedisCheckpointStore implements CheckpointStore {
  private redisUrl: string;

  constructor(redisUrl: string) {
    this.redisUrl = redisUrl;
  }

  private getKey(id: string): string {
    return `checkpoint:${id}`;
  }

  async save(id: string, state: CheckpointState): Promise<void> {
    const response = await fetch(this.redisUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key: this.getKey(id),
        value: JSON.stringify(state),
        // 断点保留 7 天
        ex: 7 * 24 * 60 * 60,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to save checkpoint: ${response.statusText}`);
    }
  }

  async load(id: string): Promise<CheckpointState | null> {
    const response = await fetch(`${this.redisUrl}/${this.getKey(id)}`);

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      throw new Error(`Failed to load checkpoint: ${response.statusText}`);
    }

    const data = await response.json();
    return JSON.parse(data.value);
  }

  async delete(id: string): Promise<void> {
    const response = await fetch(`${this.redisUrl}/${this.getKey(id)}`, {
      method: 'DELETE',
    });

    if (!response.ok && response.status !== 404) {
      throw new Error(`Failed to delete checkpoint: ${response.statusText}`);
    }
  }
}

// 内存 Checkpoint Store（仅用于开发/测试）
export class MemoryCheckpointStore implements CheckpointStore {
  private store: Map<string, CheckpointState> = new Map();

  async save(id: string, state: CheckpointState): Promise<void> {
    this.store.set(id, state);
  }

  async load(id: string): Promise<CheckpointState | null> {
    return this.store.get(id) ?? null;
  }

  async delete(id: string): Promise<void> {
    this.store.delete(id);
  }
}

// ============================================================
// 断点续传状态
// ============================================================

interface BatchJobState {
  jobId: string;
  totalOperations: number;
  processedOperations: number;
  lastCheckpointId: string | null;
  status: 'running' | 'completed' | 'failed';
  results: Array<{ index: number; value: number | null; error: string | null }>;
}

// ============================================================
// Inngest Step Functions
// ============================================================

// 重试配置：指数退避
const retryConfig: RetryConfig = {
  times: 3,
  delay: '30s',
  backoff: 'exponential',
};

// Step 1: 初始化批量任务
export const initializeBatchJob = inngest.createStep(
  'initialize-batch-job',
  async ({ event, step }: { event: any; step: Step }) => {
    const { jobId, totalOperations } = event.data;

    const state: BatchJobState = {
      jobId,
      totalOperations,
      processedOperations: 0,
      lastCheckpointId: null,
      status: 'running',
      results: [],
    };

    // 保存初始状态
    await step.run('save-initial-state', async () => {
      const store = getCheckpointStore();
      await store.save(`job:${jobId}`, state);
      return state;
    });

    return {
      jobId,
      totalOperations,
      status: 'initialized',
    };
  },
  { retries: retryConfig }
);

// Step 2: 执行 WASM 批量计算（可中断）
export const executeBatchStep = inngest.createStep(
  'execute-batch-step',
  async ({ event, step }: { event: any; step: Step }) => {
    const { jobId, operations, checkpointId } = event.data;

    // 加载当前状态
    const state = await step.run('load-state', async () => {
      const store = getCheckpointStore();
      const saved = await store.load(`job:${jobId}`);
      return saved as BatchJobState;
    });

    // 创建 WasmEdge Runner
    const runner = await step.run('create-runner', async () => {
      return new WasmEdgeRunner({
        wasmPath: process.env.WASM_CORE_PATH ?? './wasm/grt_core.wasm',
        enableWASI: true,
        networkIsolation: true,
        memoryLimit: 256 * 1024 * 1024,
        timeout: 60000,
      });
    });

    // 构造请求（带 checkpoint）
    const request = {
      operations,
      checkpointId: checkpointId ?? state.lastCheckpointId,
    };

    // 执行 WASM
    const { result, nextCheckpoint } = await step.run(
      'execute-wasm',
      async () => {
        return runner.executeWithCheckpoint(
          JSON.stringify(request),
          nextCheckpoint
        );
      }
    );

    // 解析结果
    const wasmOutput = JSON.parse(result.stdout);

    // 更新状态
    const updatedState: BatchJobState = {
      ...state,
      processedOperations: state.processedOperations + wasmOutput.totalProcessed,
      lastCheckpointId: nextCheckpoint?.lastCheckpointId ?? state.lastCheckpointId,
      results: [
        ...state.results,
        ...wasmOutput.results.map((r: any, i: number) => ({
          index: state.processedOperations + i,
          value: r.Ok ?? null,
          error: r.Err ?? null,
        })),
      ],
    };

    // 保存新状态
    await step.run('save-state', async () => {
      const store = getCheckpointStore();
      await store.save(`job:${jobId}`, updatedState);
      return updatedState;
    });

    // 清理 runner
    await step.run('cleanup-runner', async () => {
      await runner.terminate();
    });

    return {
      jobId,
      processedOperations: updatedState.processedOperations,
      totalOperations: updatedState.totalOperations,
      nextCheckpoint: nextCheckpoint?.lastCheckpointId,
      hasMore: nextCheckpoint !== null,
    };
  },
  { retries: retryConfig }
);

// Step 3: 完成任务
export const completeBatchJob = inngest.createStep(
  'complete-batch-job',
  async ({ event, step }: { event: any; step: Step }) => {
    const { jobId } = event.data;

    // 加载最终状态
    const state = await step.run('load-final-state', async () => {
      const store = getCheckpointStore();
      const saved = await store.load(`job:${jobId}`);
      return saved as BatchJobState;
    });

    // 清理 checkpoint
    await step.run('cleanup-checkpoint', async () => {
      const store = getCheckpointStore();
      await store.delete(`job:${jobId}`);
    });

    // 计算统计
    const successCount = state.results.filter((r) => r.error === null).length;
    const failureCount = state.results.filter((r) => r.error !== null).length;

    return {
      jobId,
      status: 'completed',
      totalOperations: state.totalOperations,
      successCount,
      failureCount,
      results: state.results,
    };
  },
  { retries: retryConfig }
);

// ============================================================
// 主事件处理器（编排所有步骤）
// ============================================================

export const processBatchJob = inngest.createFunction(
  { id: 'process-batch-job', retries: 5 },
  { event: 'batch/job.requested' },
  async ({ event, step }) => {
    const { jobId, operations } = event.data;

    // Step 1: 初始化
    const initResult = await step.run('initialize', () =>
      initializeBatchJob({ event, step })
    );

    // Step 2: 循环执行直到完成
    let currentCheckpoint: string | null = null;
    let totalProcessed = 0;

    while (true) {
      const batchResult = await step.run('execute-batch', () =>
        executeBatchStep({
          event: {
            data: {
              jobId,
              operations,
              checkpointId: currentCheckpoint,
            },
          },
          step,
        })
      );

      totalProcessed = batchResult.processedOperations;

      if (!batchResult.hasMore) {
        break;
      }

      currentCheckpoint = batchResult.nextCheckpoint;
    }

    // Step 3: 完成
    const finalResult = await step.run('complete', () =>
      completeBatchJob({ event, step })
    );

    return {
      jobId,
      status: 'completed',
      totalProcessed,
      successCount: finalResult.successCount,
      failureCount: finalResult.failureCount,
    };
  }
);

// ============================================================
// 辅助函数
// ============================================================

function getCheckpointStore(): CheckpointStore {
  // 生产环境使用 Redis
  if (process.env.REDIS_URL) {
    return new RedisCheckpointStore(process.env.REDIS_URL);
  }
  // 开发环境使用内存存储
  return new MemoryCheckpointStore();
}

// ============================================================
// 事件发送示例
// ============================================================

/**
 * 触发批量任务
 */
export async function triggerBatchJob(
  operations: Array<{ type: string; a: number; b: number }>
): Promise<{ jobId: string }> {
  const jobId = `job-${Date.now()}-${Math.random().toString(36).slice(2)}`;

  await inngest.send({
    name: 'batch/job.requested',
    data: {
      jobId,
      operations,
    },
  });

  return { jobId };
}
```

### package.json 依赖

```json
{
  "name": "grt-production",
  "version": "0.1.0",
  "dependencies": {
    "inngest": "^3.14.0",
    "@aspectos/wasmedge": "^0.2.0",
    "wasmedge": "^0.14.0"
  }
}
```

---

## Step 4: 魔法时刻段落 — 确定性保证的层级

**三层技术，不是三重保险，而是三层过滤器。**

---

让我们做一个思想实验。

我给你三段代码，它们做的是完全相同的事情：计算文本中的单词数量。

**TypeScript 版本：**
```typescript
function countWords(text: string): number {
  return text.split(/\s+/).filter(w => w.length > 0).length;
}
```

**Rust 版本：**
```rust
fn count_words(text: &str) -> usize {
    text.split_whitespace().count()
}
```

**WASM 版本（Rust 编译）：**
```rust
// 编译为 WASM 的 Rust 代码
#[no_mangle]
pub extern "C" fn count_words(text_ptr: *const u8, text_len: usize) -> usize {
    let text = unsafe { std::slice::from_raw_parts(text_ptr, text_len) };
    let text = std::str::from_utf8(text).unwrap();
    text.split_whitespace().count()
}
```

它们功能完全相同。但它们提供的确定性保证完全不同。

**TypeScript 版本：**
- 如果 text 是 undefined，split 会报错
- 如果 text 不是字符串，split 可能返回意外结果
- 确定性保证：运行时检查

**Rust 版本：**
- 编译时保证 text 是 &str 类型
- 所有权规则保证没有数据竞争
- 确定性保证：编译时 + 运行时（无 GC 暂停）

**WASM 版本：**
- 编译时类型检查（Rust）
- 运行时隔离（WASM 沙箱）
- 系统调用能力完全被移除
- 确定性保证：编译时 + 运行时（沙箱）

**这就是为什么我们说"不是在构建不同功能，而是在构建不同的确定性保证"。**

每一层都在解决不同层次的问题：

| 层次 | 语言 | 确定性保证 | 解决的是 |
|------|------|-----------|---------|
| 接口层 | TypeScript | 编译时类型 | "我传错了参数" |
| 核心层 | Rust | 所有权 + 生命周期 | "我忘了释放内存" |
| 执行层 | WASM | 指令级隔离 | "这个代码能做什么" |

**GRT 栈的价值不是三个技术叠加。GRT 栈的价值是三层确定性保证叠加。**

当你需要解决"AI 生成代码的可信性"问题时，你需要的不是更多的测试，而是不同层次的确定性保证。TypeScript 解决接口层的问题，Rust 解决核心逻辑层的问题，WASM 解决执行环境层的问题。

这就是为什么从 TS 到 Rust 到 WASM，不是在构建不同的功能——而是在构建不同层次的确定性保证。

---

## Step 5: 桥接语

### 承上

本章完成了从本地最小栈到生产部署的完整路径：

```
本地栈 (ch19)
  → Rust 核心编译为 WASM (cargo-component)
  → WasmEdge 零信任执行环境
  → Inngest 事件驱动 + 断点续传
  = GRT 生产栈
```

关键收获：

1. **cargo-component** — Rust 代码编译为 WASM 组件的标准方式
2. **WasmEdge 零信任** — 网络隔离、内存限制、超时控制
3. **Inngest 断点续传** — 长周期任务不丢失进度

**这不是三个独立的技术叠加，而是一套完整的确定性保证体系。**

### 启下

单一 Agent 能做的事情有限。真正的价值在于多 Agent 协作。

ch21 将展示：

```
单一 Agent (ch20)
  → Agent 联邦拓扑
  → 消息总线与状态同步
  → 任务分发与结果聚合
  = Multi-Agent System (ch22)
```

关键问题从"单个 Agent 怎么跑"变成：

- Agent 之间如何通信？
- 谁对最终状态负责？
- 如何避免状态不一致？

### 认知缺口

**为什么生产部署必须有断点续传？**

因为生产环境的失败不是"会不会"的问题，而是"什么时候"的问题。

在本地开发时，你可以重启进程，可以重新运行。在生产环境，一个 10 分钟的任务执行到第 9 分钟时崩溃，如果没有断点续传，你就得从头开始。

断点续传不是容错机制，断点续传是**生产级系统的基本要求**。

---

## Step 6: 本章来源

### 一手来源

| 来源 | URL | 关键数据/概念 |
|------|-----|--------------|
| cargo-component 官方文档 | https://github.com/bytecodealliance/cargo-component | Rust 编译为 WASM 组件的标准工具 |
| WasmEdge 文档 | https://wasmedge.org/book/ | WASM 运行时、网络隔离、内存限制 |
| Inngest 文档 | https://www.inngest.com/docs | 事件驱动步骤函数、断点续传 |
| WIT 规范 | https://github.com/WebAssembly/component-model | WebAssembly Interface Types |
| WASI Preview 2 | https://github.com/WebAssembly/WASI | WebAssembly 系统接口标准 |

### 二手来源

| 来源 | 章节 | 用途 |
|------|------|------|
| ch19-min-stack.md | 本章前置 | 最小可用栈的完整结构 |
| ch13-wasm-prison.md | 第四部分 | WASM 隔离原理 |
| ch14-wasi-capability.md | 第四部分 | WASI 能力安全 |
| ch17-immutable-dag.md | 第四部分 | 状态持久化设计 |
| ch22-multi-agent.md | 下一章 | 多 Agent 联邦 |

### 技术标准

| 标准 | 来源 | 用途 |
|------|------|------|
| WIT (WebAssembly Interface Types) | W3C/Wasm CG | WASM 组件接口定义语言 |
| WASI Preview 2 | Bytecode Alliance | WASM 系统接口标准 |
| WASM Component Model | Bytecode Alliance | WASM 组件化模型 |
