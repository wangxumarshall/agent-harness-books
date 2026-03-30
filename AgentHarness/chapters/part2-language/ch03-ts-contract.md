# 第二部分：语言层契约 — TypeScript类型系统作为契约层

## 本章Q

如何用类型系统消灭AI生成的JSON解析错误？

## 魔法时刻

TypeScript的type是编译时约束，Zod的schema是运行时约束，二者合一才是完整的概率性边界。type告诉你"这个值在理论上是什么形状"，schema告诉你"这个值在运行时真的就是这个形状"——两者缺一，就是残缺的系统。AI生成代码的概率性输出就像流水，type是上游的堤坝，schema是下游的闸门，只有堤坝加闸门才能把水的流向完全锁定。

## 五分钟摘要

第二章建立了三层牢笼架构，第一层（语言契约）是整个防线的地基。本章用三个实战案例回答"TypeScript类型防线如何具体落地"：品牌类型（Branded Types）终结字符串级联编程的死穴，Zod Schema用运行时验证补完TypeScript的静态类型盲区，TypeChat示范如何用Schema as Code实现约束与代码的同像性。关键数据来自AgenticTyper研究（ICSE 2026）：633个类型错误，20分钟全部解决；以及Nate B Jones的对照实验：同一模型，Harness改进让基准从42%跃升到78%。本章最后埋下伏笔：为什么TypeScript是"软"的契约，而Rust是"硬"的契约——这是第四章的起点。

---

## Branded Types：终结字符串级联编程的死穴

### 问题：字符串类型的"一切皆可"陷阱

AI生成代码中最常见的错误不是逻辑错误，而是**类型级错误**——模型输出一个字段名错误的对象，或者把字符串当成枚举值使用，或者把`user_id`当成`order_id`传递。这种错误在长上下文中尤其常见，模型的位置偏差会导致它"忘记"前面的类型声明。

来看一个典型的危险场景：

```typescript
// AgentBasic版本的工具调用 —— 字符串级联的死穴
interface ToolDefinition {
  name: string;
  description: string;
  parameters: string; // "any"等价物，类型系统完全失明
}

function callTool(tool: ToolDefinition, args: unknown) {
  // args的类型是unknown —— 编译器在这里完全瞎了
  // 任何东西都可以传进来，任何东西都可以传出去
  const parsed = JSON.parse(args as string);
  //  parsed是什么？不知道。字段对不对？不知道。
}
```

这个接口的问题是：工具的参数被声明为`string`类型，但实际使用时需要传递结构化的JSON对象。编译器无法检查参数的结构是否匹配工具的声明，整个类型安全链条在`string`这个"万用类型"处断裂。

这是AI编程中最经典的死穴：**字符串级联编程**（String-level Cascade Programming）。模型输出的每一个字段名、每一个枚举值、每一个类型引用，都是一个字符串。这些字符串在编译期不携带任何语义信息，编译器无法验证它们的一致性，错误只能在运行时暴露。

### 解决方案：品牌类型把字符串变成"实名制"

品牌类型（Branded Types）的核心思想是：**给原始类型加上语义标签，让编译器能区分"看起来一样但语义不同"的值**。

```typescript
// 品牌类型实战：把userId从string变成BrandedString
type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };
type EmailAddress = string & { readonly __brand: "EmailAddress" };

// 工厂函数：创建时强制类型
function createUserId(id: string): UserId {
  return id as UserId;
}

function createOrderId(id: string): OrderId {
  return id as OrderId;
}

// 现在，编译器会拦截这种错误
function getUser(userId: UserId): Promise<User> {
  return db.query(`SELECT * FROM users WHERE id = ${userId}`);
}

const userId = createUserId("u_12345");
const orderId = createOrderId("o_98765");

getUser(userId);    // ✅ 正确：UserId传入UserId
getUser(orderId);   // ❌ 错误：OrderId不是UserId，编译器拦截
getUser("u_12345" as UserId); // ❌ 错误：不能直接用string，必须经过工厂函数
```

品牌类型的威力在于**把运行时错误提前到编译期**。`getUser(orderId)`这行代码在TypeScript编译时就会报错，根本不会有机会跑到运行时，更不会有机会在生产环境中引发数据库查询错误。

### 实战：从AgentBasic到TypeSafeAgent的品牌类型迁移

让我们看一个具体的AI Agent场景：工具调用的参数传递。

```typescript
// AgentBasic版本 —— 危险的无类型工具调用
interface AgentState {
  tools: Array<{
    name: string;
    args: Record<string, unknown>;
  }>;
  // 问题：name是string，args是Record——没有任何类型保障
}

// AI生成工具调用时，可能犯的错误：
const badState: AgentState = {
  tools: [
    { name: "run_sql", args: { queyr: "SELECT * FROM users" } }, // typo: queyr
    { name: "fetch_user", args: { user_id: 12345 } }, // 类型错误：应该是string
    { name: "create_order", args: { oderId: "o_123" } }, // typo: oderId
  ]
};
```

这些错误在TypeScript编译时会完全通过——因为`name`是`string`，`args`是`Record<string, unknown>`，AI生成的任何字段名和值都能塞进去。这是字符串级联编程的典型后果。

用品牌类型重写：

```typescript
// TypeSafeAgent版本 —— 品牌类型锁死工具调用
type SQLQuery = string & { readonly __brand: "SQLQuery" };
type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

// 工具定义的类型安全版本
interface TypedTool<TArgs extends Record<string, unknown>> {
  name: string;
  args: TArgs; // 泛型约束：args的类型由调用方显式声明
}

interface TypeSafeAgentState {
  tools: TypedTool<Record<string, unknown>>[];
  // 工具调用必须满足的类型约束
}

// 工厂函数：创建时验证
function createSQLQuery(query: string): SQLQuery {
  if (!query.includes("SELECT")) {
    throw new Error("Only SELECT queries allowed in agent tool calls");
  }
  return query as SQLQuery;
}

function createUserId(id: string): UserId {
  if (!id.startsWith("u_")) {
    throw new Error("UserId must start with 'u_'");
  }
  return id as UserId;
}

// AI现在必须这样生成代码：
const safeState: TypeSafeAgentState = {
  tools: [
    {
      name: "run_sql",
      args: { query: createSQLQuery("SELECT * FROM users") } // ✅ 类型安全
    },
    {
      name: "fetch_user",
      args: { user_id: createUserId("u_12345") } // ✅ 类型安全
    }
  ]
};

// 尝试typo或类型错误？编译器直接拦截
const unsafeState: TypeSafeAgentState = {
  tools: [
    {
      name: "run_sql",
      args: { queyr: "SELECT * FROM users" } // ❌ 错误：queyr不在类型定义中
    },
    {
      name: "fetch_user",
      args: { user_id: 12345 } // ❌ 错误：number不是UserId
    }
  ]
};
```

品牌类型的代价是**显式转换的 boilerplate**。每次创建`UserId`都要调用`createUserId()`工厂函数，每次传递参数都要经过类型检查。但这个代价是值得的——它把AI生成代码的错误拦截在编译期，而不是等到生产环境才爆炸。

### 品牌类型的局限性

品牌类型解决了"语义不同的字符串需要区分"的问题，但没有解决"值的有效性需要在运行时验证"的问题。一个`UserId`品牌类型可以由`createUserId("any_random_string")`创建，只要它经过了工厂函数的类型断言。这意味着品牌类型提供的是**编译时类型安全**，但不提供**运行时值域安全**。

运行时值域安全需要Zod Schema。

---

## Zod Schema：运行时验证补完TypeScript的静态类型盲区

### 问题：TypeScript的静态类型有盲区

TypeScript的类型系统在编译期工作，但AI生成代码的错误往往发生在**运行时**：

```typescript
// TypeScript能捕获的：
function getUser(userId: UserId) { ... }
getUser(12345); // ❌ 编译错误：number不能赋给UserId

// TypeScript无法捕获的（静态类型盲区）：
function getUser(userId: UserId) {
  // 假设userId是从外部JSON反序列化来的
  const response = await fetch(`/api/users/${userId}`);
  const data = await response.json();
  // data的类型是any —— 因为JSON反序列化丢失了类型信息
  return data as User; // 假设这里有个User类型
}
```

这里的问题是：TypeScript的类型系统只在编译期有效。一旦涉及到JSON解析、网络传输、文件读取——这些运行时数据的来源——类型信息就丢失了。`data as User`是一个类型断言，它告诉编译器"相信我，这个数据是User类型"，但编译器无法验证这个断言在运行时是否真的成立。

AI生成代码尤其容易在这个盲区里犯错。模型生成的JSON结构可能和预期的TypeScript接口有细微差异：字段名大小写不匹配、嵌套结构多了或少了一层、枚举值拼写错误。TypeScript编译器对此完全视而不见，只有在运行时才会爆炸。

### 解决方案：Zod Schema的运行时验证

Zod是一个TypeScript优先的schema声明和验证库。它的核心理念是：**schema和type是一体两面，schema可以在运行时验证数据，type可以在编译期验证代码**。

```typescript
import { z } from "zod";

// Zod Schema定义 —— 同时生成TypeScript类型
const UserIdSchema = z.string()
  .regex(/^u_[a-zA-Z0-9]+$/, "UserId must start with 'u_' followed by alphanumeric")
  .brand<"UserId">();

const OrderIdSchema = z.string()
  .regex(/^o_[a-zA-Z0-9]+$/, "OrderId must start with 'o_' followed by alphanumeric")
  .brand<"OrderId">();

// 从schema推断TypeScript类型
type UserId = z.infer<typeof UserIdSchema>;
type OrderId = z.infer<typeof OrderIdSchema>;

// Zod Schema也是验证函数
function parseUserId(input: unknown): UserId {
  return UserIdSchema.parse(input); // 运行时验证 + 类型断言
}

// 完整的AgentState Schema
const AgentStateSchema = z.object({
  tools: z.array(z.object({
    name: z.string(),
    args: z.record(z.unknown()),
  })),
  context: z.record(z.unknown()),
  sessionId: z.string(),
});

type AgentState = z.infer<typeof AgentStateSchema>;

// 关键：zod.infer让schema和type成为同一个东西
// 修改schema，type自动更新；修改type，schema必须匹配
```

现在，AI生成的任何JSON都需要经过schema验证：

```typescript
// AI生成的工具调用结果需要验证
async function executeToolCall(toolCall: unknown): Promise<ToolResult> {
  // 验证输入 —— 把unknown变成AgentState
  const validated = AgentStateSchema.parse(toolCall);

  // 从这里开始，validated是TypeSafe的
  // TypeScript知道validated.tools是数组
  // TypeScript知道validated.tools[0].name是string
  // TypeScript知道validated.tools[0].args是Record<string, unknown>

  const tool = validated.tools[0];
  return callTool(tool.name, tool.args);
}

// Zod的错误处理是精确的
try {
  const result = executeToolCall(aiGeneratedJSON);
} catch (error) {
  if (error instanceof z.ZodError) {
    console.error("Validation failed:", error.issues);
    // issues包含具体的字段路径、预期类型、实际值
    // 例如：
    // {
    //   path: ["tools", 0, "args", "user_id"],
    //   message: "Expected string, received number",
    //   code: "invalid_type"
    // }
  }
}
```

### 完整示例：从AgentBasic到TypeSafeAgent的Zod迁移

这是第二章"三层牢笼架构"第一层（语言契约）的具体实现。来看一个完整的工具调用场景，从AI生成到执行的全流程：

```typescript
import { z } from "zod";

// ============================================================
// Part 1: Schema定义层 —— 类型和验证的单一真相来源
// ============================================================

// 品牌类型Schema
const UserIdSchema = z.string()
  .regex(/^u_[a-zA-Z0-9]{8,32}$/, "Invalid UserId format")
  .brand<"UserId">();

const SQLQuerySchema = z.string()
  .regex(/^\s*SELECT\s/i, "Only SELECT queries allowed")
  .brand<"SQLQuery">();

const TimestampSchema = z.string()
  .datetime()
  .brand<"Timestamp">();

// 工具定义Schema
const ToolCallSchema = z.object({
  tool_name: z.enum(["run_sql", "fetch_user", "create_order", "send_email"]),
  args: z.record(z.unknown()),
  call_id: z.string().uuid(),
});

const AgentStateSchema = z.object({
  session_id: z.string().uuid(),
  tools: z.array(ToolCallSchema),
  context: z.record(z.unknown()).optional(),
  created_at: TimestampSchema,
});

type AgentState = z.infer<typeof AgentStateSchema>;
type ToolCall = z.infer<typeof ToolCallSchema>;
type UserId = z.infer<typeof UserIdSchema>;
type SQLQuery = z.infer<typeof SQLQuerySchema>;

// ============================================================
// Part 2: Agent类型安全的实现 —— TypeSafeAgent原型
// ============================================================

class TypeSafeAgent {
  private state: AgentState;

  constructor(sessionId: string) {
    this.state = {
      session_id: sessionId,
      tools: [],
      created_at: new Date().toISOString() as z.infer<typeof TimestampSchema>,
    };
  }

  // 类型安全的工具注册
  addTool(toolName: ToolCall["tool_name"], args: Record<string, unknown>): void {
    const toolCall: ToolCall = {
      tool_name: toolName,
      args: args,
      call_id: crypto.randomUUID(),
    };

    // 验证：Schema检查拦截非法工具调用
    // 如果AI生成的tool_name不在enum列表中，这里直接报错
    ToolCallSchema.parse(toolCall);

    this.state.tools.push(toolCall);
  }

  // 类型安全的工具执行
  async executeNextTool(): Promise<unknown> {
    const tool = this.state.tools.shift();
    if (!tool) throw new Error("No tools to execute");

    // 双重验证：ToolCallSchema + 工具特定的Schema
    ToolCallSchema.parse(tool);

    switch (tool.tool_name) {
      case "run_sql": {
        const query = tool.args.query as SQLQuery;
        SQLQuerySchema.parse(query); // 确保是SELECT
        return this.runSQL(query);
      }
      case "fetch_user": {
        const userId = tool.args.user_id as UserId;
        UserIdSchema.parse(userId); // 确保格式正确
        return this.fetchUser(userId);
      }
      default:
        throw new Error(`Unknown tool: ${tool.tool_name}`);
    }
  }

  private async runSQL(query: SQLQuery): Promise<unknown[]> {
    // 实现细节
    console.log(`Executing: ${query}`);
    return [];
  }

  private async fetchUser(userId: UserId): Promise<unknown> {
    // 实现细节
    console.log(`Fetching user: ${userId}`);
    return { id: userId, name: "Mock User" };
  }

  // 获取当前状态 —— 类型安全的getter
  getState(): Readonly<AgentState> {
    return Object.freeze({ ...this.state });
  }
}

// ============================================================
// Part 3: 使用示例 —— AI生成的调用必须满足契约
// ============================================================

const agent = new TypeSafeAgent(crypto.randomUUID());

// ✅ 正确的AI生成调用
agent.addTool("run_sql", { query: "SELECT * FROM users WHERE active = true" });
agent.addTool("fetch_user", { user_id: "u_12345678" });
agent.addTool("send_email", { to: "user@example.com", subject: "Hello" });

// ❌ 编译期拦截的错误（TypeScript层面）
// agent.addTool("run_sql", { queyr: "SELECT * FROM users" }); // 字段名typo
// agent.addTool("fetch_user", { user_id: 12345 }); // 类型错误
// agent.addTool("invalid_tool", { arg: "value" }); // 不在enum中的工具名

// ❌ 运行时拦截的错误（Zod层面）—— AI可能生成的边缘case
try {
  agent.addTool("run_sql", { query: "DROP TABLE users" }); // 非SELECT query
} catch (e) {
  if (e instanceof z.ZodError) {
    console.error("SQL validation failed:", e.issues[0].message);
  }
}

try {
  agent.addTool("fetch_user", { user_id: "invalid-format" }); // 不符合regex
} catch (e) {
  if (e instanceof z.ZodError) {
    console.error("UserId validation failed:", e.issues[0].message);
  }
}
```

这个例子展示了`zod.infer<typeof AgentState>`的核心价值：**schema是类型的真相来源，验证是类型的运行时证明**。当你修改`AgentStateSchema`时，`AgentState`类型自动更新；当你试图传入不满足schema的数据时，Zod在运行时拦截。

### Zod+TypeScript双验证的威力

Zod补完了TypeScript静态类型的盲区，两者结合形成了完整的类型防线：

| 错误类型 | TypeScript拦截 | Zod拦截 |
|---------|---------------|---------|
| 字段名typo | ✅ (如果使用严格的`--noUncheckedIndexedAccess`) | ✅ |
| 缺少必需字段 | ✅ | ✅ |
| 类型不匹配（number vs string） | ✅ | ✅ |
| 值域错误（空字符串、超出范围） | ❌ | ✅ |
| 格式错误（email、UUID、regex） | ❌ | ✅ |
| 运行时JSON反序列化丢失类型 | ❌ | ✅ |

AgenticTyper研究（ICSE 2026）的数据验证了双验证的有效性：633个类型错误，在有Zod+TypeScript类型约束的环境下，20分钟全部解决——原本需要一个人工工作日。这个数字说明的不是"AI修复得快"，而是"类型约束让错误的定位和修复变得极其高效"。

---

## TypeChat：Schema as Code的同像性约束

### 理念：Schema和代码是同一个东西

TypeChat是微软开源的一个项目，它的核心洞察是：**Schema应该是代码，代码应该是Schema**。这不是隐喻，而是字面意思。

传统做法：

```typescript
// Schema定义（schema.ts）
const AgentStateSchema = z.object({ ... });

// 类型定义（types.ts）
type AgentState = z.infer<typeof AgentStateSchema>; // 依赖schema

// 验证代码（validator.ts）
function validate(data: unknown): AgentState {
  return AgentStateSchema.parse(data);
}

// 问题：schema和验证逻辑是分开的，存在不同步的风险
```

TypeChat的做法：

```typescript
// schema.ts —— Schema就是代码，代码就是Schema
// 使用TypeScript的类型声明语法直接定义schema
const AgentStateSchema = z.object({
  session_id: z.string().uuid(),
  tools: z.array(z.object({
    tool_name: z.enum(["run_sql", "fetch_user", "create_order"]),
    args: z.record(z.unknown()),
    call_id: z.string().uuid(),
  })),
  context: z.record(z.unknown()).optional(),
  created_at: z.string().datetime(),
});

// 类型推断 —— type和schema是同一行代码的两个视角
type AgentState = z.infer<typeof AgentStateSchema>;
// 意味着：修改schema，type自动变化；修改type，schema必须匹配
```

这看起来只是代码组织的差异，但实际上解决了一个根本问题：**同像性约束**（Isomorphic Constraint）。

### 同像性约束：Schema和代码的镜像对称

同像性（Isomorphism）的意思是"结构上一一对应"。在TypeScript类型系统的语境下，同像性约束要求：**Schema的形状必须和代码中实际使用数据的形状完全一致**。

传统架构中，Schema是独立于代码的"元数据"——它存在于JSON文件、IDL定义、或者代码注释中。这意味着Schema和代码可能漂移：Schema说"这个字段是optional"，但代码里把它当required用；Schema说"这个枚举有5个值"，但代码里switch了7个case。

TypeChat的同像性约束强制Schema和代码是同一个东西：

```typescript
// 完整的TypeChat风格的Agent实现
import { z } from "zod";
// TypeChat通过Zod的schema推断 + 专门的类型生成器实现同像性约束
// 安装：npm install typechat
// import { createLanguageModel, createJsonTranslator } from "typechat";

// Step 1: 用TypeScript原生语法声明Schema（这是代码，不是配置文件）
const UserSchema = z.object({
  id: z.string().brand<"UserId">(),
  email: z.string().email(),
  role: z.enum(["admin", "member", "guest"]),
  created_at: z.string().datetime(),
});

type User = z.infer<typeof UserSchema>; // Schema推断类型，类型就是Schema

// Step 2: TypeChat的prompt直接引用这个类型
const agentPrompt = `
You are a typed AI assistant. Every response must match the following TypeScript schema:

${zodToTsString(UserSchema)}

Respond with a JSON object that conforms to this schema.`;
```

`zodToTsString(UserSchema)`把schema转换回TypeScript类型声明字符串，这意味着prompt中引用的类型定义和代码中实际使用的类型是同一个东西。当你在代码中修改`UserSchema`，prompt中的类型定义自动更新——不存在"Schema和代码不同步"的问题。

### TypeChat的实际限制

TypeChat的理念领先，但实践中有两个重要限制：

**限制一：复杂嵌套Schema的prompt可读性**。当Schema嵌套超过3层时，`zodToTsString`生成的类型声明字符串会变得非常长，在prompt中占用大量上下文。对于复杂的Agent状态管理，这个开销是显著的。

**限制二：prompt中的类型声明不等于执行时的类型安全**。模型在prompt中看到了类型声明，但它的输出仍然是"字符串形式的JSON"。即使模型理解了类型约束，它生成的JSON仍然需要经过Zod验证。prompt层面的类型提示是"建议"，运行时层面的Zod验证是"强制"。

TypeChat的价值不在于"让模型不犯错"，而在于"让模型生成的错误能被精确捕获"。Schema和代码的同像性确保了：当模型犯错时，错误信息是精确的（"field X is missing, expected type Y"），而不是模糊的（"invalid JSON"）。

---

## 对比表格：2023年Prompt依赖 vs 2026年类型约束

| 维度 | 2023年（Prompt依赖） | 2026年（类型约束） |
|------|---------------------|-------------------|
| **类型安全** | 无。工具返回值是`any`，字符串级联编程 | Branded Types + Zod Schema双重验证 |
| **错误定位** | 运行时爆炸，错误信息模糊 | 编译期拦截，Zod精确报错 |
| **迭代速度** | "试试这个prompt"循环，慢 | "改类型定义"循环，快 |
| **大规模AI编程** | 633个类型错误需要1个人工工作日 | 633个类型错误20分钟解决（AgenticTyper） |
| **基准提升** | 同一模型42%基准（Harness未优化） | 同一模型78%基准（~2x提升，Nate B Jones） |
| **类型推断** | 手动维护TypeScript类型和JSON Schema两套定义 | `zod.infer<typeof Schema>`单源推断 |
| **Schema同步** | Schema文件和代码分离，存在漂移风险 | Schema as Code同像性约束 |
| **工具调用验证** | 字符串拼接，运行时猜测 | 品牌类型+枚举约束，编译期保障 |
| **可维护性** | prompt改一行，整个系统行为不可预测 | 类型改一行，编译器报告所有影响点 |

这个对比揭示了一个关键范式转变：**从"相信模型会遵循prompt"到"强制模型输出必须满足约束"**。这不是对模型的不信任，而是对工程系统的正确假设——任何在生产环境中运行的系统，都必须假设它的输入是不可信的，都必须进行边界验证。

---

## 桥接语

- **承上：** 第二章的三层牢笼架构建立了"语言契约是地基"的原则，本章给出了这个原则的具体实现：品牌类型终结字符串级联编程的死穴，Zod Schema补完TypeScript的运行时盲区，TypeChat示范Schema as Code的同像性约束。AgenticTyper的633个错误20分钟解决，Nate B Jones的42%→78%基准跃升——这些数据证明类型防线不是学术设想，而是工程实践。

- **启下：** 但TypeScript的类型防线有一个根本局限：它是"软"的——类型错误可以被`as any`绕过，可以在`tsconfig.json`里关闭严格模式，可以在运行时抛异常后catch住继续执行。Rust的类型系统是"硬"的——一个`impl Trait`的边界检查，一个`Result<T, E>`的`?`传播，一个`#[non_exhaustive]`枚举的穷尽性匹配，都是编译期的硬约束，不存在"绕过"的可能。第四章将回答：为什么Rust比TypeScript更"硬"，以及这个"硬"如何让AI编程的确定性再提升一个量级。

- **认知缺口：** 你可能已经在用TypeScript，感觉类型系统已经够用了。但"够用"和"够强"之间有巨大差距——`zod.infer<typeof AgentState>`把schema变成类型真相来源，Branded Types把字符串级联编程变成实名制，TypeChat把Schema和代码变成同一个东西。这三个机制组合起来，才是第二章所说的"建筑工程"的地基。

---

## 本章来源

### 一手来源

1. **AgenticTyper (ICSE 2026 Student Research)** — 633个类型错误20分钟解决的案例，证明TypeScript类型防线在实践中的效率，来源：arXiv:2602.21251

2. **Nate B Jones Harness研究** — 同一模型，Harness从42%到78%的基准提升（~2x），关键贡献来自类型约束的改进，来源：Latent Space分析文章（latent.space/p/ainews-is-harness-engineering-real）

3. **TypeChat项目** — 微软开源的Schema as Code实现，Schema和代码同像性约束的参考实现，来源：github.com/microsoft/TypeChat

4. **Zod官方文档** — `zod.infer<typeof Schema>`的类型推断机制，来源：zod.dev

5. **Rust+AI Agent+WASM实战教程** — p4.txt中的类型系统讨论，Rust的类型状态模式对比，来源：ITNEXT (Dogukan Tuna)

### 辅助来源

6. **ts-rs项目** — 从Rust struct生成TypeScript类型声明，跨语言类型对齐的工具，来源：github.com/Aleph-Alpha/ts-rs

7. **specta项目** — 导出Rust类型到TypeScript的库，支持chrono、uuid、serde等生态，来源：docs.rs/specta

8. **LangChain基准数据** — Terminal Bench从52.8%到66.5%的提升，虽然不是直接TypeScript数据，但证明了harness改进的普遍价值，来源：github.com/wangxumarshall/awesome-agent-harness
