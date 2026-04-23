# Agent Memory System 深度研究报告 - 任务规划

## 目标
完成三章深度研究报告：
1. 第1章：产业界 Agent Memory System 深度洞察（C.A.P.E 框架对比）
2. 第2章：学术论文全文检索与洞察
3. 第3章：面向通用 Agent 的 Memory 系统技术解决方案

## 研究对象清单（第1章）

### 第一梯队（需深度研究）
1. OpenViking + VikingBot - 虚拟文件系统范式
2. memsearch - Markdown-first + 向量影子索引
3. Hermes Agent - Markdown 持久记忆 + 闭环学习
4. Letta(memGPT) - 有状态 Agent 平台
5. mem0 - 通用记忆层
6. memos/MemOS - Memory OS 概念
7. EverOS/EverMemOS - 自组织记忆 OS

### 第二梯队（需中等深度研究）
8. claude-mem - Claude Code 插件
9. mem9 - OpenClaw 无限记忆
10. lossless-claw - 无损上下文管理
11. memU - 24/7 主动 Agent 记忆
12. Ori-Mnemos - RMH 递归记忆
13. langmem - LangChain 记忆
14. honcho - 有状态 Agent 记忆库

### 第三梯队（需基础研究）
15. ContextLoom - 多 Agent 共享大脑
16. eion - 多 Agent 共享记忆存储
17. mindforge - 向量+概念图+多层记忆
18. minecontext - 主动上下文感知
19. Memorizing Transformers - 模型原生记忆
20. memoryllm - 模型参数记忆
21. acontext - 技能即记忆层
22. ultraContext - 开源上下文基础设施
23. MemaryAI - 模拟人类记忆
24. MindOS - 人机协作心智系统

## 执行阶段

### Phase 1: 创建规划文件 + 初始化研究框架 `[complete]`
- 创建 task_plan.md, findings.md, progress.md
- 建立 C.A.P.E 对比框架模板

### Phase 2: 第一梯队深度研究（7个系统） `[complete]`
- 每个系统：访问 GitHub 仓库 + 官网/博客 + 论文
- 提取架构、存储、定位、进化、推理、Token效率、可观测性、场景、局限等维度
- 写入 findings.md

### Phase 3: 第二梯队中等深度研究（7个系统） `[complete]`
- 访问 GitHub 仓库 + 文档
- 提取关键维度
- 写入 findings.md

### Phase 4: 第三梯队基础研究（10个系统） `[complete]`
- 访问 GitHub 仓库
- 提取核心特征
- 写入 findings.md

### Phase 5: 第2章学术论文检索与洞察 `[complete]`
- 检索 arXiv/Google Scholar 相关论文
- 按业务场景、问题挑战、技术方案、效果、优劣势、演进

### Phase 6: 🆕 模型记忆范式重构 — 三大子范式批判性研究 `[complete]`
- 研究三种模型原生记忆范式：
  1. **传统KV缓存检索范式（推理前）**：从KV cache中检索向量 → 拼接提示词 → 模型推理
  2. **MSA端到端稀疏注意力范式（推理中）**：以 embedding 向量形式在推理过程中从 KV cache 实时获取 → 直接推理。上下文窗口限制优化。无状态 KV cache
  3. **MemoryLLM参数内化范式（权重融入）**：记忆内化到模型参数中，成为"永生记忆"
- 将分类名从"模型原生记忆"改为"模型记忆"
- 批判性审视：确保技术信息准确、科学、规范、逻辑严谨
- 基于 web-access 全网检索最新论文和技术细节
- 更新 findings.md 和报告第1章、第2章、附录

### Phase 7: 🆕 三稿融合整合与主文清洗 `[complete]`
- 深度比对 `agent_memory_system_insight_report.md`、`agent_memory_system_insight_report_v0.1.md`、`agent_memory_system_insight_report_v0.2.md`
- 提取 `v0.1` / `v0.2` 对主文仍有增量价值的技术观点、结构表达与关键数据
- 在“不无故删除主文内容”的约束下，补充九类 taxonomy、证据等级映射、双平面架构表达
- 修正主文中的结构污染、术语漂移、附录分类口径不一致和与主题无关示例

## 错误记录
| Error | Attempt | Resolution |
|-------|---------|------------|
| (暂无) | | |
