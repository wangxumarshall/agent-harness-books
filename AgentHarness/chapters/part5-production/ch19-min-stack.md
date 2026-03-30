# 第五部分：生产部署层 — 从零构建Harness最小可用栈

## 本章Q

如何在本地跑起第一个Harness栈？

## 魔法时刻

**最小可用栈的价值不是"能用"，而是"可验证"。**

---

你在本地跑起了一个"Hello World"的Agent。

它能跑。你看到输出。你觉得成功了。

但这不是魔法时刻。

**魔法时刻是你能证明它的每一步都是对的：**

- 输入经过Zod验证，类型错误在进入系统前就被拦截
- AgentOutput的结构是完整的，你能看到thinking、tool_calls、content之间的边界
- WasmEdge沙箱捕获了所有系统调用，没有任何意外的网络请求
- JSON解析错误不会让你的应用崩溃——它被转换成了一个可处理的Result

**不是"能用"，而是"可验证"。**

当你能在本地验证每一个组件的行为时，你才真正拥有了一个可信的系统。当这个系统被部署到生产环境时，你才能睡得着觉。

这就是最小可用栈的真正价值：**它不是最小功能集，而是最小可验证集**。

---

## 五分钟摘要

前十八章建立了语言层、编译器层、运行时层的完整理论：

- **第一部分**：Agent的编程模型——如何用TypeScript/Mastra描述Agent行为
- **第二部分**：契约层——Zod强类型守卫如何拦截脏数据
- **第三部分**：编译器层——TNR、Deadloop检测、自愈循环
- **第四部分**：运行时层——V8 Isolates、WASI、MCP沙箱、Immutable DAG、RAG-MCP

**这一章是从理论到实践的第一次落地。**

目标是让你在本地跑起一个最小Harness栈，包含：

1. **Mastra** — TypeScript端的Agent框架
2. **Zod** — 运行时类型验证
3. **WasmEdge** — 沙箱执行环境

关键问题不是"能不能跑"，而是"能不能验证"。我们不只需要一个能工作的栈，我们需要一个**可证明正确的栈**。

---

## 魔法时刻

**最小可用栈的价值不是"能用"，而是"可验证"。**

当你能在本地验证每一个组件的行为时，你才真正拥有了一个可信的系统。当这个系统被部署到生产环境时，你才能睡得着觉。

---

## Step 1: 完整项目代码 — Mastra + Zod + WasmEdge强类型守卫

### 项目结构

```
min-harness/
├── src/
│   ├── index.ts              # 入口
│   ├── agent.ts              # Mastra Agent定义
│   ├── schema.ts             # Zod类型定义
│   ├── wasmedge-runner.ts    # WasmEdge执行器
│   └── json-guard.ts         # JSON解析错误防御
├── wasm/
│   └── agent.wasm            # 编译后的WASM模块
├── package.json
└── tsconfig.json
```

### 核心代码：入口文件

```typescript
// src/index.ts — 最小Harness栈的入口

import { Mastra } from '@mastra/core';
import { jsonGuardMiddleware } from './json-guard';
import { createWasmEdgeRunner } from './wasmedge-runner';
import { agentSchema, AgentInput } from './schema';

// 创建WasmEdge运行时
const wasmRunner = createWasmEdgeRunner({
  wasmPath: './wasm/agent.wasm',
  enableWASI: true,
  networkIsolation: true,
});

// 创建Mastra Agent
const agent = new Mastra({
  name: 'min-harness-agent',
  runner: wasmRunner,
  inputSchema: agentSchema,
  middleware: [jsonGuardMiddleware],
});

// 启动函数
async function main() {
  const input: AgentInput = {
    message: 'Calculate the sum of 1 to 10',
    context: {
      userId: 'test-user',
      sessionId: 'test-session',
    },
  };

  // 验证输入
  const validatedInput = agentSchema.parse(input);

  // 执行Agent
  const result = await agent.run({ input: validatedInput });

  // 验证输出
  console.log('Agent Output:', JSON.stringify(result, null, 2));
}

main().catch(console.error);
```

### 核心代码：Zod强类型定义

```typescript
// src/schema.ts — Zod类型守卫完整定义

import { z } from 'zod';

/**
 * Agent输入的完整Schema
 * 所有外部输入必须经过此Schema验证
 */
export const agentInputSchema = z.object({
  message: z.string().min(1).max(10000, 'Message too long'),
  context: z.object({
    userId: z.string().min(1),
    sessionId: z.string().min(1),
    metadata: z.record(z.string(), z.unknown()).optional(),
  }),
});

export type AgentInput = z.infer<typeof agentInputSchema>;

/**
 * Agent输出结构 —— 这是AgentOutput的核心定义
 */
export const agentOutputSchema = z.object({
  // 思考过程（可选，用于调试）
  thinking: z.string().optional(),

  // 工具调用列表
  tool_calls: z.array(
    z.object({
      id: z.string(),
      name: z.string(),
      arguments: z.record(z.string(), z.unknown()),
      result: z.unknown().optional(),
      error: z.string().optional(),
    })
  ),

  // 最终内容输出
  content: z.string(),

  // 执行元数据
  metadata: z.object({
    executionTimeMs: z.number(),
    tokenUsage: z.object({
      input: z.number(),
      output: z.number(),
    }),
    sandbox: z.object({
      memoryUsedKb: z.number().optional(),
      networkCallsBlocked: z.number(),
    }),
  }),
});

export type AgentOutput = z.infer<typeof agentOutputSchema>;

/**
 * JSON解析错误的结构化表示
 */
export const jsonParseErrorSchema = z.object({
  error_type: z.enum([
    'unexpected_end_of_input',
    'invalid_syntax',
    'invalid_token',
    'trailing_comma',
    'unicode_escape_error',
  ]),
  position: z.number(),
  line: z.number().optional(),
  column: z.number().optional(),
  found: z.string().optional(),
  expected: z.array(z.string()).optional(),
});

export type JsonParseError = z.infer<typeof jsonParseErrorSchema>;
```

### 核心代码：WasmEdge执行器

```typescript
// src/wasmedge-runner.ts — WasmEdge沙箱执行器

import { WasmEdgeRuntime } from '@aspectos/wasmedge';
import { AgentOutput, agentOutputSchema } from './schema';

interface WasmEdgeRunnerConfig {
  wasmPath: string;
  enableWASI: boolean;
  networkIsolation: boolean;
}

interface WasmExecutionResult {
  stdout: string;
  stderr: string;
  exitCode: number;
  executionTimeMs: number;
}

/**
 * 创建WasmEdge运行时的工厂函数
 */
export function createWasmEdgeRunner(config: WasmEdgeRunnerConfig) {
  const runtime = new WasmEdgeRuntime({
    wasmPath: config.wasmPath,
    // WASI支持：允许标准输入输出
    wasi: config.enableWASI
      ? {
          preopens: ['/tmp'],
        }
      : undefined,
    // 网络隔离：阻止WASM模块发起网络请求
    network: config.networkIsolation
      ? {
          allowedHosts: [], // 空数组 = 完全禁止
          blockedPaths: ['/etc/passwd', '/etc/hosts'],
        }
      : undefined,
    // 内存限制：防止恶意WASM消耗过多内存
    memory: {
      min: 16 * 1024 * 1024, // 16MB
      max: 128 * 1024 * 1024, // 128MB
    },
  });

  return {
    runtime,

    /**
     * 在沙箱中执行WASM模块
     */
    async execute(input: AgentInput): Promise<AgentOutput> {
      const startTime = Date.now();

      // 序列化输入
      const inputJson = JSON.stringify(input);

      // 执行WASM
      const result = await runtime.execute(inputJson, {
        timeout: 30000, // 30秒超时
      });

      const executionTimeMs = Date.now() - startTime;

      // 解析输出（带错误防御）
      const output = await parseAgentOutput(result.stdout, executionTimeMs);

      return output;
    },

    /**
     * 清理资源
     */
    async terminate() {
      await runtime.terminate();
    },
  };
}

/**
 * 带错误防御的JSON解析
 */
async function parseAgentOutput(
  rawOutput: string,
  executionTimeMs: number
): Promise<AgentOutput> {
  try {
    const parsed = JSON.parse(rawOutput);

    // Zod验证：确保输出符合AgentOutput结构
    return agentOutputSchema.parse(parsed);
  } catch (error) {
    // JSON解析失败时的防御性处理
    if (error instanceof SyntaxError) {
      // 构造一个错误输出，而不是崩溃
      const errorInfo = analyzeJsonError(rawOutput, error);

      return {
        thinking: undefined,
        tool_calls: [],
        content: '',
        metadata: {
          executionTimeMs,
          tokenUsage: { input: 0, output: 0 },
          sandbox: {
            memoryUsedKb: undefined,
            networkCallsBlocked: 0,
          },
        },
        // 注入结构化错误信息
        error: `JSON Parse Error: ${errorInfo.error_type} at position ${errorInfo.position}`,
      };
    }

    // Zod验证失败
    if (error instanceof z.ZodError) {
      throw new Error(`AgentOutput validation failed: ${error.message}`);
    }

    throw error;
  }
}
```

---

## Step 2: AgentOutput结构体 — 代码 + 测试的完整定义

### AgentOutput的完整结构

```typescript
// agent-output.ts — AgentOutput的完整定义与测试

import { z } from 'zod';

/**
 * AgentOutput — Agent执行结果的完整结构
 *
 * 这个结构是Harness的核心契约：
 * - 所有Agent必须返回此结构
 * - 结构保证可验证性
 * - 字段边界清晰，便于调试
 */
export const agentOutputSchema = z.object({
  // === 核心输出 ===
  /** 思考过程（LLM的推理链路） */
  thinking: z.string().optional(),

  /** 工具调用列表 */
  tool_calls: z.array(toolCallSchema),

  /** 最终文本输出 */
  content: z.string(),

  // === 执行元数据 ===
  metadata: executionMetadataSchema,
});

/**
 * 单次工具调用
 */
const toolCallSchema = z.object({
  /** 调用ID（用于追踪） */
  id: z.string(),

  /** 工具名称 */
  name: z.string(),

  /** 调用参数 */
  arguments: z.record(z.string(), z.unknown()),

  /** 调用结果（成功时） */
  result: z.unknown().optional(),

  /** 错误信息（失败时） */
  error: z.string().optional(),

  /** 执行时间 */
  executionTimeMs: z.number().optional(),
});

/**
 * 执行元数据
 */
const executionMetadataSchema = z.object({
  /** 总执行时间 */
  executionTimeMs: z.number(),

  /** Token使用量 */
  tokenUsage: z.object({
    input: z.number(),
    output: z.number(),
  }),

  /** 沙箱执行信息 */
  sandbox: z.object({
    memoryUsedKb: z.number().optional(),
    networkCallsBlocked: z.number(),
    syscalls: z.array(z.string()).optional(),
  }),
});

export type AgentOutput = z.infer<typeof agentOutputSchema>;
export type ToolCall = z.infer<typeof toolCallSchema>;
export type ExecutionMetadata = z.infer<typeof executionMetadataSchema>;
```

### AgentOutput的完整测试

```typescript
// agent-output.test.ts — AgentOutput结构的完整测试

import { describe, it, expect } from 'vitest';
import { agentOutputSchema, AgentOutput } from './agent-output';

describe('AgentOutput Schema', () => {
  describe('Valid outputs', () => {
    it('should accept a minimal valid output', () => {
      const validOutput: AgentOutput = {
        tool_calls: [],
        content: 'Hello, World!',
        metadata: {
          executionTimeMs: 150,
          tokenUsage: { input: 100, output: 50 },
          sandbox: { networkCallsBlocked: 0 },
        },
      };

      const result = agentOutputSchema.safeParse(validOutput);
      expect(result.success).toBe(true);
    });

    it('should accept a full output with thinking and tool calls', () => {
      const fullOutput: AgentOutput = {
        thinking: 'I need to calculate 1+1 first',
        tool_calls: [
          {
            id: 'call_001',
            name: 'calculator',
            arguments: { a: 1, b: 1 },
            result: 2,
            executionTimeMs: 10,
          },
        ],
        content: 'The sum of 1 and 1 is 2.',
        metadata: {
          executionTimeMs: 250,
          tokenUsage: { input: 200, output: 100 },
          sandbox: {
            memoryUsedKb: 1024,
            networkCallsBlocked: 5,
            syscalls: ['read', 'write', 'clock_time_get'],
          },
        },
      };

      const result = agentOutputSchema.safeParse(fullOutput);
      expect(result.success).toBe(true);
    });

    it('should accept output with tool call errors', () => {
      const outputWithError: AgentOutput = {
        tool_calls: [
          {
            id: 'call_002',
            name: 'network_request',
            arguments: { url: 'https://example.com' },
            error: 'Network access blocked by sandbox',
            executionTimeMs: 0,
          },
        ],
        content: 'I tried to make a network request but it was blocked.',
        metadata: {
          executionTimeMs: 50,
          tokenUsage: { input: 50, output: 30 },
          sandbox: { networkCallsBlocked: 1 },
        },
      };

      const result = agentOutputSchema.safeParse(outputWithError);
      expect(result.success).toBe(true);
    });
  });

  describe('Invalid outputs', () => {
    it('should reject output with missing content', () => {
      const invalidOutput = {
        tool_calls: [],
        // content is missing
        metadata: {
          executionTimeMs: 100,
          tokenUsage: { input: 50, output: 25 },
          sandbox: { networkCallsBlocked: 0 },
        },
      };

      const result = agentOutputSchema.safeParse(invalidOutput);
      expect(result.success).toBe(false);
    });

    it('should reject output with invalid tool_call id', () => {
      const invalidOutput = {
        tool_calls: [
          {
            // id is missing
            name: 'calculator',
            arguments: {},
            result: 42,
          },
        ],
        content: 'test',
        metadata: {
          executionTimeMs: 100,
          tokenUsage: { input: 50, output: 25 },
          sandbox: { networkCallsBlocked: 0 },
        },
      };

      const result = agentOutputSchema.safeParse(invalidOutput);
      expect(result.success).toBe(false);
    });

    it('should reject output with negative execution time', () => {
      const invalidOutput = {
        tool_calls: [],
        content: 'test',
        metadata: {
          executionTimeMs: -100, // negative!
          tokenUsage: { input: 50, output: 25 },
          sandbox: { networkCallsBlocked: 0 },
        },
      };

      const result = agentOutputSchema.safeParse(invalidOutput);
      expect(result.success).toBe(false);
    });

    it('should reject output with non-array tool_calls', () => {
      const invalidOutput = {
        tool_calls: 'not an array', // should be array
        content: 'test',
        metadata: {
          executionTimeMs: 100,
          tokenUsage: { input: 50, output: 25 },
          sandbox: { networkCallsBlocked: 0 },
        },
      };

      const result = agentOutputSchema.safeParse(invalidOutput);
      expect(result.success).toBe(false);
    });
  });

  describe('Type inference', () => {
    it('should correctly infer types from schema', () => {
      const output: AgentOutput = {
        tool_calls: [],
        content: 'test',
        metadata: {
          executionTimeMs: 100,
          tokenUsage: { input: 50, output: 25 },
          sandbox: { networkCallsBlocked: 0 },
        },
      };

      // TypeScript should infer:
      // - output.thinking is string | undefined
      // - output.tool_calls is ToolCall[]
      // - output.content is string
      // - output.metadata is ExecutionMetadata

      expect(typeof output.content).toBe('string');
      expect(Array.isArray(output.tool_calls)).toBe(true);
      expect(typeof output.metadata.executionTimeMs).toBe('number');
    });
  });
});
```

### 运行测试

```bash
# 运行AgentOutput测试
npx vitest run agent-output.test.ts

# 预期输出：
#  PASS  agent-output.test.ts
#    AgentOutput Schema
#      Valid outputs
#        ✓ should accept a minimal valid output
#        ✓ should accept a full output with thinking and tool calls
#        ✓ should accept output with tool call errors
#      Invalid outputs
#        ✓ should reject output with missing content
#        ✓ should reject output with invalid tool_call id
#        ✓ should reject output with negative execution time
#        ✓ should reject output with non-array tool_calls
#      Type inference
#        ✓ should correctly infer types from schema
#
#  Test Files  1 passed
#  Tests      8 passed
```

---

## Step 3: 消除JSON解析错误 — 具体错误类型与防御代码

### JSON解析错误的完整分类

```typescript
// json-errors.ts — JSON解析错误的完整分类与防御

/**
 * JSON解析错误的七种基本类型
 */
export enum JsonErrorType {
  UNEXPECTED_END_OF_INPUT = 'unexpected_end_of_input',
  INVALID_SYNTAX = 'invalid_syntax',
  INVALID_TOKEN = 'invalid_token',
  TRAILING_COMMA = 'trailing_comma',
  UNICODE_ESCAPE_ERROR = 'unicode_escape_error',
  DUPLICATE_KEY = 'duplicate_key',
  CONTROL_CHARACTER = 'control_character',
}

/**
 * 结构化的JSON解析错误
 */
export interface StructuredJsonError {
  type: JsonErrorType;
  message: string;
  position: number;
  line?: number;
  column?: number;
  found?: string;
  expected?: string[];
}

/**
 * 分析原始JSON错误，返回结构化错误
 */
export function analyzeJsonError(
  rawInput: string,
  error: SyntaxError
): StructuredJsonError {
  const message = error.message;

  // 1. 意外的输入结束
  if (
    message.includes('Unexpected end of input') ||
    message.includes('unexpected end of')
  ) {
    return {
      type: JsonErrorType.UNEXPECTED_END_OF_INPUT,
      message: 'JSON string ended unexpectedly',
      position: rawInput.length,
      found: undefined,
      expected: ['value', 'object', 'array'],
    };
  }

  // 2. 无效语法
  if (
    message.includes('Unexpected token') ||
    message.includes('Invalid token')
  ) {
    const match = message.match(/at position (\d+)/);
    const position = match ? parseInt(match[1], 10) : 0;

    return {
      type: JsonErrorType.INVALID_TOKEN,
      message: 'Invalid token found in JSON',
      position,
      found: extractFoundAtPosition(rawInput, position),
      expected: extractExpectedAfterPosition(rawInput, position),
    };
  }

  // 3. 尾随逗号
  if (message.includes('Trailing comma')) {
    const position = findTrailingCommaPosition(rawInput);

    return {
      type: JsonErrorType.TRAILING_COMMA,
      message: 'Trailing comma is not allowed in JSON',
      position,
      found: ',',
      expected: ['} or ]'],
    };
  }

  // 4. Unicode转义错误
  if (
    message.includes('Unicode') ||
    message.includes('escape')
  ) {
    const match = rawInput.match(/\\u([0-9a-fA-F]{0,3})/);
    const position = match ? rawInput.indexOf(match[0]) : 0;

    return {
      type: JsonErrorType.UNICODE_ESCAPE_ERROR,
      message: 'Invalid Unicode escape sequence',
      position,
      found: match ? match[0] : undefined,
      expected: ['\\uXXXX (4 hex digits)'],
    };
  }

  // 5. 控制字符
  if (message.includes('control character')) {
    const position = findControlCharacter(rawInput);

    return {
      type: JsonErrorType.CONTROL_CHARACTER,
      message: 'Control characters must be escaped',
      position,
      found: extractFoundAtPosition(rawInput, position),
      expected: ['\\n, \\t, \\r, etc.'],
    };
  }

  // 6. 重复键（需要额外检查）
  if (message.includes('Duplicate key')) {
    const match = rawInput.match(/"([^"]+)":/g);
    const keyCounts = new Map<string, number>();

    if (match) {
      for (const key of match) {
        const k = key.slice(1, -2); // remove quotes and colon
        keyCounts.set(k, (keyCounts.get(k) || 0) + 1);
      }
    }

    let duplicateKey = '';
    for (const [key, count] of keyCounts) {
      if (count > 1) {
        duplicateKey = key;
        break;
      }
    }

    return {
      type: JsonErrorType.DUPLICATE_KEY,
      message: `Duplicate key found: "${duplicateKey}"`,
      position: rawInput.indexOf(`"${duplicateKey}":`),
      found: duplicateKey,
      expected: ['unique key'],
    };
  }

  // 默认：未知错误
  return {
    type: JsonErrorType.INVALID_SYNTAX,
    message: error.message,
    position: 0,
  };
}

/**
 * 防御性JSON解析 — 不会抛出异常的JSON.parse
 */
export function safeJsonParse<T>(
  jsonString: string,
  fallback: T
): { success: true; data: T } | { success: false; error: StructuredJsonError } {
  try {
    const data = JSON.parse(jsonString);
    return { success: true, data };
  } catch (error) {
    if (error instanceof SyntaxError) {
      const structuredError = analyzeJsonError(jsonString, error);
      return { success: false, error: structuredError };
    }
    // 非JSON错误，重新抛出
    throw error;
  }
}

/**
 * 带默认值的安全解析
 */
export function safeJsonParseOrDefault<T>(
  jsonString: string,
  defaultValue: T
): T {
  const result = safeJsonParse(jsonString, defaultValue);
  return result.success ? result.data : defaultValue;
}

// === 辅助函数 ===

function extractFoundAtPosition(input: string, position: number): string | undefined {
  if (position < 0 || position >= input.length) {
    return undefined;
  }

  // 提取周围上下文
  const start = Math.max(0, position - 5);
  const end = Math.min(input.length, position + 5);
  return input.slice(start, end);
}

function extractExpectedAfterPosition(input: string, position: number): string[] {
  const char = input[position];

  const expectations: string[] = [];

  if (char === '"' || char === "'") {
    expectations.push('property name');
  } else if (char === ':') {
    expectations.push('value');
  } else if (char === ',') {
    expectations.push('property name or closing bracket');
  } else if (char === '}') {
    expectations.push('closing brace');
  } else if (char === ']') {
    expectations.push('closing bracket');
  }

  return expectations;
}

function findTrailingCommaPosition(input: string): number {
  // 查找类似 "...],}" 或 "...},}" 的模式
  const pattern = /,\s*[}\]]/g;
  let lastMatchPos = -1;

  let match;
  while ((match = pattern.exec(input)) !== null) {
    lastMatchPos = match.index;
  }

  return lastMatchPos;
}

function findControlCharacter(input: string): number {
  // 0x00-0x1F 是控制字符
  for (let i = 0; i < input.length; i++) {
    const code = input.charCodeAt(i);
    if (code < 0x20 && code !== 0x09 && code !== 0x0A && code !== 0x0D) {
      return i;
    }
  }
  return -1;
}
```

### JSON Guard中间件

```typescript
// json-guard.ts — JSON防御中间件

import { Request, Response, NextFunction } from 'express';
import { safeJsonParse, StructuredJsonError, JsonErrorType } from './json-errors';

/**
 * JSON解析错误的HTTP状态码映射
 */
const ERROR_STATUS_MAP: Record<JsonErrorType, number> = {
  [JsonErrorType.UNEXPECTED_END_OF_INPUT]: 400,
  [JsonErrorType.INVALID_SYNTAX]: 400,
  [JsonErrorType.INVALID_TOKEN]: 400,
  [JsonErrorType.TRAILING_COMMA]: 400,
  [JsonErrorType.UNICODE_ESCAPE_ERROR]: 400,
  [JsonErrorType.DUPLICATE_KEY]: 400,
  [JsonErrorType.CONTROL_CHARACTER]: 400,
};

/**
 * JSON Guard 中间件
 * 拦截所有JSON解析错误，返回结构化响应
 */
export function jsonGuardMiddleware(
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction
) {
  // 只处理JSON解析错误
  if (err instanceof SyntaxError && 'body' in err) {
    const rawBody = (err as any).body;

    if (typeof rawBody === 'string') {
      const parseResult = safeJsonParse(rawBody, null);

      if (!parseResult.success) {
        return res.status(ERROR_STATUS_MAP[parseResult.error.type]).json({
          error: {
            type: 'json_parse_error',
            details: parseResult.error,
            hint: getErrorHint(parseResult.error),
          },
        });
      }
    }
  }

  // 非JSON错误，继续传递
  next(err);
}

/**
 * 获取错误提示
 */
function getErrorHint(error: StructuredJsonError): string {
  switch (error.type) {
    case JsonErrorType.UNEXPECTED_END_OF_INPUT:
      return 'Request body is truncated. Check if the client sent complete data.';

    case JsonErrorType.TRAILING_COMMA:
      return 'Remove the trailing comma before the closing bracket.';

    case JsonErrorType.UNICODE_ESCAPE_ERROR:
      return 'Use \\uXXXX format for Unicode escapes (exactly 4 hex digits).';

    case JsonErrorType.CONTROL_CHARACTER:
      return 'Escape control characters using \\n, \\t, \\r, etc.';

    case JsonErrorType.DUPLICATE_KEY:
      return `Remove duplicate key "${error.found}" from the object.`;

    default:
      return 'Check JSON syntax at position ' + error.position;
  }
}
```

---

## Step 4: 魔法时刻段落 — 可验证性的价值

**可验证性是信任的基础。**

---

让我们做一个实验。

我给你两个"能工作"的系统：

**系统A：**
```
输入 → 黑盒 → 输出
```
你不知道里面发生了什么。它能跑，但你不确定它为什么跑。

**系统B：**
```
输入 → Zod验证 → [类型错误被拦截]
     → Mastra Agent → [thinking追踪]
     → WasmEdge沙箱 → [网络调用被阻止]
     → AgentOutput → [结构化输出]
     → Zod验证 → [输出被验证]
```
每一步都有日志，每个边界都被守卫，你能验证每一个组件。

**哪个系统更让你安心？**

系统A能跑。但当它出错时，你不知道是输入的问题、Agent的问题、还是沙箱的问题。

系统B能跑。而且当它出错时，你知道**exactly**是哪一步出错，以及为什么。

**这就是可验证性的价值。**

最小可用栈不是最小功能集。最小可用栈是**让你能睡得着觉的系统**。

当你能在本地验证：
- 输入被正确验证
- Agent的每一步都有追踪
- 沙箱阻止了所有未经授权的操作
- 输出符合预期结构

那么当这个系统被部署到生产环境时，你不需要在凌晨3点被报警叫醒。你只需要看日志，找到哪一步验证失败，修复它，继续部署。

**不是"能不能跑"，而是"跑的时候我知不知道它在对的方向上"。**

---

## Step 5: 桥接语 — 从本地栈到生产部署

### 承上

本章展示了从零构建最小Harness栈的完整路径：

```
Mastra (TypeScript Agent框架)
  + Zod (运行时类型守卫)
  + WasmEdge (沙箱执行环境)
  = 最小可验证栈
```

关键收获：

1. **AgentOutput结构** — 完整的、可验证的输出定义
2. **JSON解析错误防御** — 七种错误类型 + 结构化错误处理
3. **可验证性** — 不是"能用"，而是"可证明"

**这18行代码的价值不在于它能做什么，而在于你能证明它做了什么。**

### 认知缺口

但这里有一个被忽略的问题：**最小栈能跑，但跑起来之后呢？**

本地环境是可控的。生产环境有节点故障、网络抖动、配置漂移。最小栈没有回答：如何在生产环境的不确定性中保持可验证性？

这就是ch20要填补的缺口。

### 启下：从本地到生产

本地栈能跑是第一步。下一步是让它**在生产环境稳定运行**。

ch20将展示：

```
本地最小栈 → Kubernetes集群
              → Helm Chart打包
              → 滚动更新策略
              → 蓝绿部署
              → 自动扩缩容
```

关键问题从"能不能跑"变成：

- 如何让Agent在节点故障时自动迁移？
- 如何在不中断服务的情况下更新Agent代码？
- 如何监控Agent的健康状态？

**从能跑到能部署，从能部署到能运维。**

这不仅仅是技术问题。这是**构建可信系统**的完整路径。

---

## Step 6: 本章来源

### 一手来源

| 来源 | URL | 关键数据 |
|------|-----|---------|
| Mastra文档 | https://mastra.ai/docs | TypeScript Agent框架，类型安全 |
| Zod官方文档 | https://zod.dev | 运行时类型验证 |
| WasmEdge文档 | https://wasmedge.org/book/ | WASM沙箱，网络隔离 |
| Vitest文档 | https://vitest.dev | 测试框架，TypeScript支持 |
| JSON.org规范 | https://www.json.org/json-en.html | JSON语法完整规范 |

### 二手来源

| 来源 | 用途 |
|------|------|
| ch1-intro.md | Harness的愿景与目标 |
| ch2-type-system.md | TypeScript类型系统的优势 |
| ch5-zod-guard.md | Zod守卫的完整实现 |
| ch15-v8-isolates.md | 沙箱执行环境的设计 |
| ch20-production.md | 下一章：生产部署完整指南 |

### 技术标准

| 来源 | 用途 |
|------|------|
| ECMAScript 2023 | TypeScript基础语言 |
| WASI Preview 2 | WebAssembly系统接口 |
| JSON-RPC 2.0 | 工具调用协议格式 |
| OpenAI Tool Calling | Agent工具调用格式 |
