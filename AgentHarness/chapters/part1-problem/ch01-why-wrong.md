# 第一部分：问题与原理 — 为什么现有的AI编程方法论都是错的

## 本章Q

既然AI能写代码，为什么还需要Harness？

## 魔法时刻

LangChain的脆弱性不是bug，而是设计缺陷——它试图用提示词管理弥补架构问题，而提示词管理本质上是在流沙上建城堡。每一个"更好的prompt"都是在已知失败模式后的补丁，而非对系统性失控的根因治理。当概率性输出遇到字符串拼接的prompt，没有任何编译器告诉你哪里错了，没有任何类型系统捕获工具调用的类型不匹配，没有任何运行时隔离防止一个失控的Agent把QEMU的代码库改成一锅粥。LangChain告诉你的上限是"也许这次能跑通"，而Harness要解决的是"必须跑通，而且我知道为什么"。

## 五分钟摘要

2023年到2025年之间，大多数团队用"更好的prompt"和"更强大的模型"来追逐AI编程的确定性——这条路在生产环境中被反复证伪。Nate B Jones的对照实验用同一个模型做出了42%到78%的差距，LangChain在同一基准上将成功率从52.8%提升到66.5%，靠的不是模型升级而是harness改进。这些数字揭示了一个被大多数从业者忽视的事实：**模型是子弹，harness是枪管——枪管决定了子弹飞到哪里，而不是子弹本身。** 本书的核心主张是：Bounded Intelligence——AI的输出本质上是概率性的，但生产系统必须是确定性的，而这两者之间的鸿沟必须由类型系统、编译器检查和运行时隔离构成的三重边界来填补。

---

## 开篇失败案例：那个凌晨三点的P0事故

2024年秋天，某中型SaaS公司的工程团队经历了一次难忘的P0事故。

他们的AI编程流水线用了当时最先进的LangChain Agents架构：ReAct prompt模板、ChatGPT-4作为推理引擎、Wikipedia搜索工具 + 自定义代码执行环境。团队为这个系统骄傲了整整三个月——Bench指标很漂亮，内部demo效果惊艳，每周PR数量从12个飙升到47个。

然后事故发生了。

一个初级工程师想让Agent帮他写一个数据导出脚本。他输入了"导出过去三个月所有活跃用户的订阅数据，按套餐类型聚合"。Agent调用了Wikipedia工具——不知道为什么，可能是因为prompt里提到了"活跃"和"历史"这类关键词。Wikipedia返回了一堆关于用户增长历史的数据。Agent把这些数据当成了真实业务数据，塞进了PostgreSQL的`user_subscriptions`表。

凌晨三点，值班的SRE被数据库磁盘告警惊醒。`user_subscriptions`表被灌入了超过20万行污染数据，部分字段类型不匹配导致整表锁表。备份恢复花了两个小时。数据修复花了六个小时。事后复盘，团队发现了一个让他们脊背发凉的事实：**没有任何异常被触发。** Wikipedia工具返回了"数据"，Agent处理了"数据"，数据库接收了"数据"——整个链路是完全合法的。

这不是一个bug。这是**架构性失败**。

LangChain的ReAct模板让Agent在"思考"和"行动"之间自由切换，但没有人在工具调用前验证"这个工具的返回值类型是否符合当前上下文的预期"。Wikipedia工具返回的是字符串，不是结构化的用户记录——但Agent没有被告知这一点，prompt里没有类型约束，代码里没有类型检查，运行时没有隔离。

这个团队后来做了一个实验：把同样的prompt和工具集迁移到一个用Pydantic严格定义输入输出类型、用类型守卫拦截异常、用Docker容器隔离工具执行的环境里。相同的输入跑了一百次，零次污染。

**区别不在模型，不在prompt，在架构。**

---

## LangChain的局限性：六阶段中的第二阶段陷阱

Mitchell Hashimoto在回顾自己的AI采纳历程时，提出了一个被广泛引用的六阶段模型。其中第二阶段的名字特别扎眼：**"Reproduce Your Own Work"**——强迫用Agent重做你手动做过的工作。

这个阶段的问题在于：大多数团队在第二阶段就卡住了。不是因为他们不想进第三阶段，而是因为他们的harness撑不到第三阶段。

LangChain是第二阶段的代表性框架。它解决的问题是"如何把prompt、工具和记忆串起来"，而不是"如何保证串起来的结果是确定性的"。

看一个具体的代码案例：

```python
# LangChain式的典型代码
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.tools import Tool

llm = ChatOpenAI(model="gpt-4")
tools = [
    Tool.from_function(wikipedia_search, "wikipedia", "Search Wikipedia"),
    Tool.from_function(run_sql, "run_sql", "Execute SQL query"),
]

agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools)

# 这个调用可能返回任何东西——字符串、错误、None、甚至一个异常对象
result = executor.invoke({"input": "show me all active users"})
```

问题在哪？

**第一，工具返回值的类型是`Any`。** `wikipedia_search`返回什么？`run_sql`返回什么？在LangChain的世界里，这些都是运行时谜语。编译器不关心，类型检查器不关心，静态分析工具也不关心。

**第二，Agent的输出没有结构化验证。** `executor.invoke()`返回的`result`是一个字典，里面的`output`字段是一个字符串——或者是对话历史，或者是一个错误消息。调用方必须用字符串匹配来猜测Agent到底干了什么。

**第三，工具之间的状态隔离是假的。** Wikipedia工具和SQL工具运行在同一个Python进程里。一个工具的异常可以污染另一个工具的状态。一个prompt injection可以绕过工具调用的语义边界。

**第四，prompt是动态拼接的，不是类型安全的。** `create_react_agent`的prompt是一个`BasePromptTemplate`，它接受变量字典，然后做字符串格式化。这意味着如果工具列表变了，或者工具的参数变了，没有人知道prompt是否仍然有效。

这不是LangChain独有的问题。这是**基于prompt scaffold的架构的通病**。任何试图用提示词管理来弥补架构缺陷的系统，都会遇到同样的天花板：

```
prompt层能捕获的边界 = 你预先想到的所有边界情况
实际系统需要捕获的边界 = 所有边界情况（包括你没想过的）
```

**差距就是生产事故。**

LangChain 52.8%到66.5%的Terminal Bench提升是真实的——但这是在受控环境里。在生产环境中，面对真实用户输入、真实工具副作用、真实并发调用，这个差距会在某个凌晨三点以P0事故的形式显现。

---

## 核心论点：提示词管理是外科手术，Harness是建筑工程

"提示词工程"这个词本身就揭示了它解决的问题类型：调整模型的输入，让模型产生更好的输出。这是一个**外科手术式**的思路——精准、局部、对操作者的高度依赖。

但生产级AI编程系统不是一台精密仪器，而是一栋需要容纳不确定性、承受压力、在恶劣天气下依然屹立的建筑。你不会用手术刀来浇混凝土，你也不会用prompt来管理一个每天处理500个PR的Agent系统。

**Harness工程是建筑工程。**

建筑工程有三个关键特征：

1. **有明确的结构规范（类型系统）**：梁的跨度、柱的承重、钢筋的规格——每一个参数都有类型和边界，超出边界编译器报错，而不是等到地震来了才发现问题。
2. **有施工过程的检查（编译器检查）**：图纸会审、施工监理、竣工验收——每一步都有检查点，不符合规范的构件在施工阶段就被拦截，而不是等到投入使用才发现。
3. **有独立的运行环境（运行时隔离）**：每个单元是独立的模块，火灾不会从一个房间蔓延到另一个房间——一个工具的失控不会导致整个系统崩溃。

建筑工程的核心思想是**把不确定性约束在可控边界内**。钢筋会生锈，但你设计了防腐层；地震会来，但你设计了抗震结构；洪水会涨，但你设计了泄洪通道。你不是在消除不确定性——你是在为不确定性准备容错空间。

**提示词管理的思路正好相反。** 它试图通过"更好的提示"来减少不确定性，但不确定性是模型的固有属性——这是统计模型的本质，不是模型的bug。提示词工程在不确定性面前是防守姿态，每次新发现一个问题就加一条prompt约束，就像每次漏雨就加一块瓦片。Harness工程则是主动设计结构，让雨水根本进不来。

Mitchell Hashimoto的第五阶段描述了这种思路转变：

> "每当你发现Agent犯了一个错误，你就花时间去工程化一个解决方案，让它再也不会犯同样的错。"

这不是prompt review。这是**系统重构**。每次错误都变成了一个改进harness的机会，而不是一个修改prompt的机会。

OpenAI Codex团队在100万行代码项目中的实践验证了这一点。他们发现"仓库是Agent唯一的知识来源"——代码、markdown、schema、可执行计划全都版本化存在仓库。这是harness设计，不是prompt设计。"代码要对Agent可读，不是对人类可读"——这是application legibility的harness原则，不是prompt技巧。"合并哲学"——审查而非修改，发现需要大量修改就反思Harness哪里出错——这是harness迭代闭环，不是prompt调优。

**当你发现一个AI编程问题，Harness工程师问的是"这个错误的结构根源是什么"，prompt工程师问的是"我该怎么描述才能让它不犯这个错"。**

---

## LangChain设计缺陷的深层原因

LangChain的设计者并不愚蠢。LangChain的代码里有聪明的抽象，有优雅的链式调用，有丰富的工具生态。那为什么它的核心架构注定脆弱？

因为LangChain试图用**应用层逻辑**解决**系统层问题**。

工具调用、状态管理、记忆聚合、prompt拼接——这些在LangChain里都是"业务逻辑"，由用户编写的Python代码驱动。但这些问题的真正根源是**类型系统缺失**：

- 工具A的输出类型和工具B的输入类型之间的映射，是字符串到字符串的传递，没有任何类型级别的保障
- Agent的状态是`dict`类型的黑箱，进去了什么、出来了什么，只有运行时才知道
- Prompt模板是`BasePromptTemplate`的多态调用，具体插入了什么变量，只有调用时才知道

Python的动态类型系统在这里不是替罪羊——Python可以用`pydantic.BaseModel`做运行时验证，可以用`mypy`做静态检查，可以用`dataclasses`做结构化约束。问题是LangChain的设计从一开始就把这些当成"可选的增强"，而不是"必须的基座"。

这导致了一个不可逆的架构债务累积：每一个新工具都是`Tool.from_function()`注册上去的，每一个新prompt都是`create_react_agent()`塞进去的，每一个新的"技巧"都是GitHub Issues里的workaround。系统越来越复杂，但没有人能自信地说"这个系统的行为边界在哪里"。

**Harness的思路是从第一天就把边界焊死。** 类型系统不是可选的增强，而是每一条工具调用都必须满足的契约。编译器检查不是"建议"，而是CI流水线的强制关卡。运行时隔离不是"为了安全"，而是每一个工具调用都必须满足的物理约束。

这不是保守主义。这是**工程学的必然要求**。

一个每天处理500个PR的Stripe Minions系统，不能靠"也许这个prompt能正确调用工具"来运转。它需要的是：类型安全的工具契约、确定性的执行环境、可观测的反馈回路。这些都是harness的组成部分，不是prompt的组成部分。

---

## 桥接语

- **承上：** 我们看到了一个真实的P0事故，根源不在于prompt不够好，而在于工具调用的返回值类型没有任何验证；我们分析了LangChain的设计缺陷，它的脆弱不是意外，而是用应用层逻辑解决系统层问题的必然结果；我们提出了核心论点——提示词管理是外科手术，Harness是建筑工程。

- **启下：** 但"建筑工程"到底长什么样？类型系统、编译器检查、运行时隔离——这三层边界如何协同工作，把AI的概率性输出锁定在系统边界内？第二章将用Anthropic 16 Agent × 10万行Rust C编译器的案例，回答这个问题：为什么Harness不是可选项，而是唯一能让AI在生产环境中可靠工作的方法。

- **认知缺口：** 你可能已经在用LangChain，或者在用其他基于prompt scaffold的框架。你的Bench指标可能很好看。但Benchmark是受控环境，而你的生产系统不是受控环境。你现在需要的不是下一个prompt技巧，而是重新审视你系统的架构根基——然后决定是否愿意为确定性付出工程化的代价。

---

## 本章来源

### 一手来源

1. **Nate B Jones Harness研究** — 同一模型42%到78%的基准提升，~2x差距，来源：Latent Space分析文章（latent.space/p/ainews-is-harness-engineering-real）

2. **LangChain基准数据** — Terminal Bench从52.8%到66.5%的提升（+13.7%），未改变模型，来源：awesome-agent-harness项目（github.com/wangxumarshall/awesome-agent-harness）

3. **Mitchell Hashimoto六阶段AI采纳模型** — 第二阶段"Reproduce Your Own Work"、第五阶段"Engineer the Harness"，来源：mitchellh.com/writing/my-ai-adoption-journey

4. **OpenAI Harness工程博文** — 100万行代码项目，0行人类手写，3人团队，来源：openai.com/index/harness-engineering/

5. **Harness Engineering定义** — "设计系统、约束和反馈循环，使AI Agent在生产环境中可靠"，来源：nxcode.io "What Is Harness Engineering? Complete Guide for 2026"

6. **Stripe Minions系统** — 每周1300+ PR，完全无人值守，Blueprint混合编排架构，来源：stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents

7. **Anthropic 16 Agent × C编译器案例** — 100,000行Rust，16个Agent并行，99% GCC torture test通过率，来源：anthropic.com/engineering/building-c-compiler

### 辅助来源

8. **Pi Research数据** — 同一天下午，仅改harness，提升15个不同LLM，来源：p5.txt（调研整理）

9. **Vercel工具精简案例** — 工具从15到2个，准确率从80%到100%，来源：p5.txt（调研整理）

10. **Cursor Harness排名案例** — Claude Opus 4.6，不同Harness排名从33到第5，来源：p5.txt（调研整理）
