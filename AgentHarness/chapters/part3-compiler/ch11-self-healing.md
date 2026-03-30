# 第三部分：编译器层 — 自愈循环：CritiqueAgent与GeneratorAgent的对抗

## 本章Q

AI如何通过自我对抗实现自愈？

## 魔法时刻

**自愈不是AI在修复，而是系统在强制AI进行梯度下降。**

这不是诗意的比喻。这是字面意义上的反向传播。

GAN（生成对抗网络）之所以有效，不是因为生成器"学会了"画人脸，而是判别器提供了损失函数的梯度。生成器不需要理解人脸长什么样，只需要沿着判别器给出的梯度方向调整像素值。

CritiqueAgent与GeneratorAgent的关系与此完全相同：

- **GeneratorAgent** = GAN的生成器：生成候选代码
- **CritiqueAgent** = GAN的判别器：提供损失梯度
- **系统** = GAN的优化器：强制梯度下降

AI不会"自愈"。系统通过Critique强制AI进行梯度下降。这就是为什么ch09说"编译器反馈是梯度"——CritiqueAgent就是那个把梯度计算出来的东西。

---

## 五分钟摘要

第十章的TNR解决了"修复失败怎么办"——快照+回滚。但TNR有一个根本性缺陷：**回滚是事后的，滞后的**。如果CritiqueAgent和GeneratorAgent形成对抗循环，死循环怎么办？

自愈循环的真正机制不是"AI修bug"，而是**系统强制AI进行梯度下降**。CritiqueAgent作为判别器，计算每个修复的损失梯度；GeneratorAgent作为生成器，沿着梯度方向更新代码；系统在两者之间扮演优化器角色，用指数退避控制对抗节奏。

GAN的训练稳定性依赖于Wasserstein距离、梯度惩罚等技术。自愈循环的稳定性依赖于**快照、回滚和指数退避**。本章用三个代码示例展示自愈循环的完整实现。

---

## Step 1: CritiqueAgent/GeneratorAgent微秒级对抗 — GAN架构

### 自愈循环的GAN模型

传统观点认为"AI修复bug"是一个智能过程——AI理解了代码逻辑，发现了错误，生成了正确的修复。但这个理解是错误的。

真正发生的是对抗过程：

```
GeneratorAgent → 生成候选修复 → 送给CritiqueAgent
CritiqueAgent → 计算损失梯度 → 返回给GeneratorAgent
系统 → 强制梯度下降 → GeneratorAgent更新
重复...
```

CritiqueAgent不"理解"代码，它只计算损失。GeneratorAgent不"修复"bug，它只沿梯度方向移动。直到CritiqueAgent的损失降到零（或足够低），我们才说"自愈成功"。

### 完整实现

```typescript
// self-healing-loop.ts — CritiqueAgent与GeneratorAgent的对抗循环

import { CompilerError } from './compiler-errors';
import { CompilationUnitTransaction } from './ch10-tnr-formal';

/**
 * 损失信号 —— CritiqueAgent计算的结果
 */
interface LossSignal {
    /** 总损失值 [0, 1]，0表示完美 */
    totalLoss: number;

    /** 各维度损失分解 */
    dimensions: {
        /** 编译器错误损失 [0, 1] */
        compilerLoss: number;

        /** 类型正确性损失 [0, 1] */
        typeLoss: number;

        /** 运行时安全性损失 [0, 1] */
        safetyLoss: number;

        /** 语义一致性损失 [0, 1] */
        semanticLoss: number;
    };

    /** CritiqueAgent的具体反馈 */
    feedback: CritiqueFeedback[];

    /** 置信度 [0, 1] */
    confidence: number;

    /** 是否收敛（损失足够低） */
    converged: boolean;
}

/**
 * CritiqueAgent的反馈项
 */
interface CritiqueFeedback {
    /** 问题类型 */
    type: 'compiler-error' | 'type-mismatch' | 'runtime-error' | 'semantic-drift';

    /** 问题描述 */
    description: string;

    /** 位置 */
    location?: {
        file: string;
        line: number;
        column: number;
    };

    /** 建议的修复方向（梯度） */
    gradient: string;

    /** 损失权重 [0, 1] */
    weight: number;
}

/**
 * 生成器候选结果
 */
interface GeneratedCandidate {
    /** 候选ID */
    id: string;

    /** 生成的文件修改 */
    modifications: Map<string, string>;

    /** 候选的损失值（生成时估计） */
    estimatedLoss: number;

    /** 是否来自有效梯度方向 */
    fromValidGradient: boolean;

    /** 时间戳 */
    timestamp: number;
}

/**
 * CritiqueAgent —— 判别器，类比GAN的判别器
 *
 * 职责：
 * 1. 接收GeneratorAgent的候选修复
 * 2. 计算多维度损失信号
 * 3. 提供梯度方向反馈
 * 4. 判断是否收敛
 */
export class CritiqueAgent {
    private name: string;
    private strictness: number; // [0, 1]，严格度

    constructor(name: string = 'CritiqueAgent', strictness: number = 0.8) {
        this.name = name;
        this.strictness = strictness;
    }

    /**
     * 评估GeneratorAgent的修复候选
     * 计算多维度损失信号
     */
    async evaluate(
        originalCode: Map<string, string>,
        modifiedCode: Map<string, string>,
        compilerErrors: CompilerError[],
        previousLoss?: LossSignal
    ): Promise<LossSignal> {
        // 第一维度：编译器错误损失
        const compilerLoss = this.computeCompilerLoss(compilerErrors);

        // 第二维度：类型正确性损失（通过更严格的类型检查）
        const typeLoss = await this.computeTypeLoss(modifiedCode);

        // 第三维度：运行时安全性损失（通过静态分析）]
        const safetyLoss = await this.computeSafetyLoss(modifiedCode);

        // 第四维度：语义一致性损失（防止修复改变原有行为）
        const semanticLoss = this.computeSemanticLoss(originalCode, modifiedCode, previousLoss);

        // 综合损失（加权平均）
        const weights = { compiler: 0.4, type: 0.2, safety: 0.2, semantic: 0.2 };
        const totalLoss =
            weights.compiler * compilerLoss +
            weights.type * typeLoss +
            weights.safety * safetyLoss +
            weights.semantic * semanticLoss;

        // 生成具体反馈
        const feedback = this.generateFeedback(compilerErrors, typeLoss, safetyLoss, semanticLoss);

        // 判断收敛：损失低于阈值且各维度损失都较低
        const converged = totalLoss < 0.1 &&
            compilerLoss < 0.15 &&
            typeLoss < 0.15 &&
            safetyLoss < 0.15 &&
            semanticLoss < 0.15;

        // 置信度：基于历史一致性
        const confidence = this.computeConfidence(totalLoss, previousLoss);

        return {
            totalLoss,
            dimensions: { compilerLoss, typeLoss, safetyLoss, semanticLoss },
            feedback,
            confidence,
            converged,
        };
    }

    /**
     * 计算编译器错误损失
     */
    private computeCompilerLoss(errors: CompilerError[]): number {
        if (errors.length === 0) return 0;

        // 按严重度加权
        const weightedErrors = errors.map(e => {
            switch (e.severity) {
                case 'error': return 1.0;
                case 'warning': return 0.5;
                case 'info': return 0.2;
                case 'hint': return 0.1;
                default: return 0.5;
            }
        });

        // 归一化到 [0, 1]
        const totalWeight = weightedErrors.reduce((a, b) => a + b, 0);
        return Math.min(1.0, totalWeight / 10); // 10个error = 1.0 loss
    }

    /**
     * 计算类型正确性损失
     */
    private async computeTypeLoss(code: Map<string, string>): Promise<number> {
        // 实际实现中：运行更严格的类型检查
        // 这里用模拟值
        let typeErrorCount = 0;

        for (const [, content] of code) {
            // 检测类型相关的问题
            if (content.includes(': any')) typeErrorCount += 0.3;
            if (content.includes('as unknown')) typeErrorCount += 0.2;
            if (content.includes('!.')) typeErrorCount += 0.1;
        }

        return Math.min(1.0, typeErrorCount * 0.1);
    }

    /**
     * 计算运行时安全性损失
     */
    private async computeSafetyLoss(code: Map<string, string>): Promise<number> {
        let safetyIssues = 0;

        for (const [, content] of code) {
            // 检测常见运行时问题
            if (content.includes('eval(')) safetyIssues += 0.5;
            if (content.includes('innerHTML')) safetyIssues += 0.3;
            if (content.includes('dangerouslySetInnerHTML')) safetyIssues += 0.3;
            // 检查可能的空指针
            if (content.match(/\w+\.\w+\.(length|value)/) && !content.includes('?.')) {
                safetyIssues += 0.1;
            }
        }

        return Math.min(1.0, safetyIssues * 0.2);
    }

    /**
     * 计算语义一致性损失
     * 防止修复改变了原有行为
     */
    private computeSemanticLoss(
        original: Map<string, string>,
        modified: Map<string, string>,
        previousLoss?: LossSignal
    ): number {
        // 简单的启发式：函数签名变化太大 = 高损失
        let signatureChanges = 0;
        let totalFunctions = 0;

        for (const [file, origContent] of original) {
            const modContent = modified.get(file);
            if (!modContent) continue;

            // 提取函数签名（简化版）
            const origSigs = this.extractFunctionSignatures(origContent);
            const modSigs = this.extractFunctionSignatures(modContent);

            totalFunctions += origSigs.length;

            for (const origSig of origSigs) {
                if (!modSigs.includes(origSig)) {
                    signatureChanges += 1;
                }
            }
        }

        if (totalFunctions === 0) return 0;
        const changeRatio = signatureChanges / totalFunctions;

        // 如果变化太剧烈，给出惩罚
        if (changeRatio > 0.3 && previousLoss && previousLoss.dimensions.semanticLoss < 0.1) {
            // 之前语义损失很低，现在突然变高 = 可能引入了回归
            return 0.8;
        }

        return Math.min(1.0, changeRatio * 2);
    }

    /**
     * 提取函数签名
     */
    private extractFunctionSignatures(content: string): string[] {
        const sigRegex = /(?:function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\(|class\s+\w+)/g;
        const matches = content.match(sigRegex);
        return matches || [];
    }

    /**
     * 生成具体反馈
     */
    private generateFeedback(
        compilerErrors: CompilerError[],
        typeLoss: number,
        safetyLoss: number,
        semanticLoss: number
    ): CritiqueFeedback[] {
        const feedback: CritiqueFeedback[] = [];

        // 编译器错误反馈
        for (const error of compilerErrors.slice(0, 5)) { // 最多5个
            feedback.push({
                type: 'compiler-error',
                description: error.message,
                location: { file: error.file, line: error.line, column: error.column },
                gradient: this.errorToGradient(error),
                weight: error.severity === 'error' ? 1.0 : 0.5,
            });
        }

        // 类型问题反馈
        if (typeLoss > 0.2) {
            feedback.push({
                type: 'type-mismatch',
                description: `类型检查损失较高: ${typeLoss.toFixed(2)}`,
                gradient: '使用更严格的类型注解，消除所有 ": any" 和 "as unknown"',
                weight: typeLoss,
            });
        }

        // 安全性反馈
        if (safetyLoss > 0.2) {
            feedback.push({
                type: 'runtime-error',
                description: `运行时安全损失较高: ${safetyLoss.toFixed(2)}`,
                gradient: '避免使用 eval()、innerHTML，使用可选链 (?.) 防止空指针',
                weight: safetyLoss,
            });
        }

        // 语义一致性反馈
        if (semanticLoss > 0.2) {
            feedback.push({
                type: 'semantic-drift',
                description: `语义一致性损失较高: ${semanticLoss.toFixed(2)}`,
                gradient: '保持原有函数签名和公共API不变',
                weight: semanticLoss,
            });
        }

        return feedback;
    }

    /**
     * 将编译器错误转换为梯度方向
     */
    private errorToGradient(error: CompilerError): string {
        const code = error.code.toUpperCase();
        const message = error.message.toLowerCase();

        if (code.startsWith('TS7006') || message.includes('implicitly')) {
            return '添加显式类型注解';
        }
        if (code.startsWith('TS2531') || message.includes('null') || message.includes('undefined')) {
            return '添加空值检查（?. 或 if (x)）';
        }
        if (code.startsWith('TS2307') || message.includes('cannot find')) {
            return '检查导入路径是否正确';
        }
        if (code.startsWith('E0384') || message.includes('immutable')) {
            return '重新设计借用关系，使用可变引用或克隆';
        }
        if (message.includes('lifetime')) {
            return '添加显式生命周期注解';
        }

        return `修复编译器错误: ${error.message}`;
    }

    /**
     * 计算置信度
     */
    private computeConfidence(totalLoss: number, previousLoss?: LossSignal): number {
        if (!previousLoss) return 0.7; // 首次评估置信度中等

        // 如果损失在下降，置信度提高
        if (totalLoss < previousLoss.totalLoss) {
            return Math.min(1.0, previousLoss.confidence + 0.1);
        }

        // 如果损失在上升或震荡，置信度降低
        return Math.max(0.3, previousLoss.confidence - 0.15);
    }

    getName(): string {
        return this.name;
    }
}

/**
 * GeneratorAgent —— 生成器，类比GAN的生成器
 *
 * 职责：
 * 1. 接收CritiqueAgent的梯度反馈
 * 2. 生成候选修复代码
 * 3. 评估候选质量
 */
export class GeneratorAgent {
    private name: string;
    private creativity: number; // [0, 1]，创造性

    constructor(name: string = 'GeneratorAgent', creativity: number = 0.5) {
        this.name = name;
        this.creativity = creativity;
    }

    /**
     * 根据梯度反馈生成修复候选
     */
    async generate(
        currentCode: Map<string, string>,
        lossSignal: LossSignal,
        snapshot: Map<string, string>
    ): Promise<GeneratedCandidate> {
        const modifications = new Map<string, string>();
        const candidateId = `gen-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

        // 遍历每个文件的反馈
        for (const [file, content] of currentCode) {
            const fileModifications = this.applyGradients(content, lossSignal.feedback, file);
            if (fileModifications !== content) {
                modifications.set(file, fileModifications);
            }
        }

        // 估计损失（简化版：基于梯度应用后的静态分析）
        const estimatedLoss = this.estimateLoss(modifications, lossSignal);

        // 判断是否来自有效梯度
        const fromValidGradient = lossSignal.totalLoss < 0.5 || lossSignal.confidence > 0.5;

        return {
            id: candidateId,
            modifications,
            estimatedLoss,
            fromValidGradient,
            timestamp: Date.now(),
        };
    }

    /**
     * 将梯度反馈应用到代码
     */
    private applyGradients(
        content: string,
        feedback: CritiqueFeedback[],
        file: string
    ): string {
        let modified = content;

        for (const fb of feedback) {
            if (fb.location && !fb.location.file.includes(file)) continue;

            switch (fb.type) {
                case 'compiler-error':
                    modified = this.applyCompilerFix(modified, fb);
                    break;
                case 'type-mismatch':
                    modified = this.applyTypeFix(modified, fb);
                    break;
                case 'runtime-error':
                    modified = this.applySafetyFix(modified, fb);
                    break;
                case 'semantic-drift':
                    modified = this.applySemanticFix(modified, fb);
                    break;
            }
        }

        return modified;
    }

    /**
     * 应用编译器修复
     */
    private applyCompilerFix(content: string, feedback: CritiqueFeedback): string {
        const gradient = feedback.gradient;

        if (gradient.includes('类型注解')) {
            // 注意：这里需要 LLM 来推断实际类型
            // 错误的做法示例：直接用正则替换会产生 `const x: type =` 这样的语法错误
            // content = content.replace(/(\bconst\s+\w+)\s*=/g, '$1: type =');
            //
            // 正确的做法：调用 LLM 或类型推断工具生成实际类型
            // const inferredType = await llm.inferType(codeContext, variableName);
            // content = content.replace(variablePattern, `$1: ${inferredType} =`);
        }

        if (gradient.includes('空值检查')) {
            // 添加可选链
            content = content.replace(/\.(\w+)(?!\?)\b/g, '?.$1');
        }

        return content;
    }

    /**
     * 应用类型修复
     */
    private applyTypeFix(content: string, feedback: CritiqueFeedback): string {
        // 消除 `: any`
        content = content.replace(/:\s*any(?![^\(]*\?)/g, ': unknown');
        // 消除不必要的 `as unknown`
        content = content.replace(/as\s+unknown\s+as\s+/g, 'as ');
        return content;
    }

    /**
     * 应用安全性修复
     */
    private applySafetyFix(content: string, feedback: CritiqueFeedback): string {
        const gradient = feedback.gradient;

        if (gradient.includes('eval')) {
            content = content.replace(/eval\(/g, '/* SAFE: removed eval */ console.error(');
        }
        if (gradient.includes('innerHTML')) {
            content = content.replace(/innerHTML/g, 'textContent');
        }

        return content;
    }

    /**
     * 应用语义一致性修复
     */
    private applySemanticFix(content: string, feedback: CritiqueFeedback): string {
        // 语义修复：不改变函数签名
        // 这里只是记录警告，不做修改
        return content;
    }

    /**
     * 估计候选损失
     */
    private estimateLoss(modifications: Map<string, string>, previousLoss: LossSignal): number {
        if (modifications.size === 0) {
            return previousLoss.totalLoss; // 没有修改，损失不变
        }

        // 简化的损失估计：如果正确应用了梯度，损失应该下降
        // 但如果应用错误，损失可能上升
        return previousLoss.totalLoss * (0.5 + Math.random() * 0.3);
    }

    getName(): string {
        return this.name;
    }
}

/**
 * SelfHealingLoop —— 自愈循环主控制器
 *
 * 协调CritiqueAgent和GeneratorAgent的对抗过程
 */
export class SelfHealingLoop {
    private critiqueAgent: CritiqueAgent;
    private generatorAgent: GeneratorAgent;
    private maxIterations: number;
    private convergenceThreshold: number;
    private currentLoss?: LossSignal;
    private iterationCount: number;

    constructor(config: {
        critiqueAgent?: CritiqueAgent;
        generatorAgent?: GeneratorAgent;
        maxIterations?: number;
        convergenceThreshold?: number;
    } = {}) {
        this.critiqueAgent = config.critiqueAgent || new CritiqueAgent();
        this.generatorAgent = config.generatorAgent || new GeneratorAgent();
        this.maxIterations = config.maxIterations || 20;
        this.convergenceThreshold = config.convergenceThreshold || 0.1;
        this.iterationCount = 0;
    }

    /**
     * 执行自愈循环
     *
     * @param initialCode 初始代码（快照）
     * @param compilerErrors 当前编译器错误
     * @returns 修复后的代码和循环统计
     */
    async heal(
        initialCode: Map<string, string>,
        compilerErrors: CompilerError[]
    ): Promise<{
        success: boolean;
        finalCode: Map<string, string>;
        converged: boolean;
        iterations: number;
        finalLoss: number;
    }> {
        let currentCode = new Map(initialCode);
        const snapshot = new Map(initialCode);

        // 首次Critique评估
        this.currentLoss = await this.critiqueAgent.evaluate(
            snapshot,
            currentCode,
            compilerErrors
        );

        // 主循环
        while (this.iterationCount < this.maxIterations) {
            this.iterationCount++;

            // 检查收敛
            if (this.currentLoss.converged || this.currentLoss.totalLoss < this.convergenceThreshold) {
                return {
                    success: true,
                    finalCode: currentCode,
                    converged: true,
                    iterations: this.iterationCount,
                    finalLoss: this.currentLoss.totalLoss,
                };
            }

            // GeneratorAgent根据梯度生成修复候选
            const candidate = await this.generatorAgent.generate(
                currentCode,
                this.currentLoss,
                snapshot
            );

            // 如果有修改，应用修改
            if (candidate.modifications.size > 0) {
                for (const [file, content] of candidate.modifications) {
                    currentCode.set(file, content);
                }
            }

            // CritiqueAgent重新评估
            const previousLoss = this.currentLoss;
            this.currentLoss = await this.critiqueAgent.evaluate(
                snapshot,
                currentCode,
                compilerErrors,
                previousLoss
            );

            // 如果损失增加（修复变差），触发回滚
            if (this.currentLoss.totalLoss > previousLoss.totalLoss + 0.1) {
                // 损失增加超过阈值，回滚到快照
                currentCode = new Map(snapshot);
                this.currentLoss = previousLoss;

                // 重置快照为当前状态（放弃这次失败的尝试）
                // 实际实现中，这里应该实现指数退避
            }

            // 如果损失没有改善，退出
            if (Math.abs(this.currentLoss.totalLoss - previousLoss.totalLoss) < 0.01) {
                break;
            }
        }

        return {
            success: this.currentLoss.totalLoss < this.convergenceThreshold,
            finalCode: currentCode,
            converged: this.currentLoss.totalLoss < this.convergenceThreshold,
            iterations: this.iterationCount,
            finalLoss: this.currentLoss.totalLoss,
        };
    }

    /**
     * 获取当前损失信号
     */
    getCurrentLoss(): LossSignal | undefined {
        return this.currentLoss;
    }

    /**
     * 获取迭代次数
     */
    getIterationCount(): number {
        return this.iterationCount;
    }
}
```

### GAN vs 自愈循环的对应关系

| GAN组件 | 自愈循环组件 | 职责 |
|---------|-------------|------|
| 生成器 (Generator) | GeneratorAgent | 生成候选（代码/图像） |
| 判别器 (Discriminator) | CritiqueAgent | 计算损失，判断真假 |
| 损失函数 | 多维度损失信号 | 评估生成质量 |
| 优化器 | SelfHealingLoop | 强制梯度下降 |
| 训练目标 | 收敛条件 | 损失足够低 |

关键区别：

- **GAN生成图像**：像素值的连续空间，可以用梯度直接优化
- **自愈循环生成代码**：文本的离散空间，需要通过Critique反馈间接引导
- **GAN的梯度**：来自判别器的反向传播
- **自愈循环的梯度**：来自CritiqueAgent的多维度损失信号

---

## Step 2: 指数退避实现 — 状态快照与重试策略

### 为什么需要指数退避

对抗循环有一个根本性风险：**循环不收敛**。如果GeneratorAgent和CritiqueAgent陷入死循环，系统会无限生成候选、无限评估，永远不停止。

指数退避是解决这个问题的方法：

```
第1次失败 → 等待 1ms → 重试
第2次失败 → 等待 2ms → 重试
第3次失败 → 等待 4ms → 重试
第4次失败 → 等待 8ms → 重试
...
第N次失败 → 等待 2^(N-1) ms → 重试
```

但自愈循环的指数退避比网络重试更复杂——我们需要**快照状态**，因为退避后的重试可能需要从不同的起点开始。

### 完整实现

```typescript
// exponential-backoff-healing.ts — 指数退避自愈循环

/**
 * 快照状态 —— 用于回滚
 */
interface SnapshotState {
    /** 快照ID */
    id: string;

    /** 代码状态 */
    code: Map<string, string>;

    /** 损失信号 */
    loss: LossSignal;

    /** 时间戳 */
    timestamp: number;

    /** 快照原因 */
    reason: 'initial' | 'improvement' | 'plateau' | 'manual';
}

/**
 * 退避状态
 */
interface BackoffState {
    /** 当前退避级别 [0, maxBackoff] */
    level: number;

    /** 当前等待时间（毫秒） */
    waitTimeMs: number;

    /** 失败次数 */
    failureCount: number;

    /** 是否在退避中 */
    isBackingOff: boolean;

    /** 下次可执行时间 */
    nextRetryTime: number;
}

/**
 * 指数退避配置
 */
interface ExponentialBackoffConfig {
    /** 初始等待时间（毫秒） */
    initialWaitMs: number;

    /** 最大等待时间（毫秒） */
    maxWaitMs: number;

    /** 退避因子 */
    backoffFactor: number;

    /** 最大退避级别 */
    maxBackoffLevel: number;

    /** 抖动范围 [0, 1] */
    jitter: number;

    /** 连续改善次数阈值（提前退出） */
    improvementThreshold: number;

    /** 连续失败次数阈值（放弃） */
    giveupThreshold: number;
}

/**
 * 指数退避自愈循环
 *
 * 将指数退避算法与自愈循环结合，解决对抗循环不收敛的问题
 */
export class ExponentialBackoffHealingLoop {
    private selfHealingLoop: SelfHealingLoop;
    private config: ExponentialBackoffConfig;
    private snapshots: SnapshotState[] = [];
    private backoffState: BackoffState;
    private lastStableLoss: number;
    private consecutiveImprovements: number;
    private consecutiveFailures: number;

    constructor(
        selfHealingLoop: SelfHealingLoop,
        config: Partial<ExponentialBackoffConfig> = {}
    ) {
        this.selfHealingLoop = selfHealingLoop;

        // 默认配置
        this.config = {
            initialWaitMs: 1,
            maxWaitMs: 5000,
            backoffFactor: 2,
            maxBackoffLevel: 12,
            jitter: 0.1,
            improvementThreshold: 3,
            giveupThreshold: 5,
            ...config,
        };

        this.backoffState = {
            level: 0,
            waitTimeMs: this.config.initialWaitMs,
            failureCount: 0,
            isBackingOff: false,
            nextRetryTime: 0,
        };

        this.lastStableLoss = 1.0;
        this.consecutiveImprovements = 0;
        this.consecutiveFailures = 0;
    }

    /**
     * 执行带指数退避的自愈
     */
    async heal(
        initialCode: Map<string, string>,
        compilerErrors: CompilerError[]
    ): Promise<{
        success: boolean;
        finalCode: Map<string, string>;
        finalLoss: number;
        iterations: number;
        backoffEvents: BackoffEvent[];
        snapshotsTaken: number;
    }> {
        const backoffEvents: BackoffEvent[] = [];

        // 记录初始快照
        const initialSnapshot = this.createSnapshot('initial', initialCode, {
            totalLoss: 1.0,
            dimensions: { compilerLoss: 1.0, typeLoss: 1.0, safetyLoss: 1.0, semanticLoss: 1.0 },
            feedback: [],
            confidence: 0,
            converged: false,
        });
        this.snapshots.push(initialSnapshot);
        this.lastStableLoss = 1.0;

        let currentCode = new Map(initialCode);
        let currentLoss = 1.0;
        let totalIterations = 0;

        // 主循环
        while (true) {
            // 检查是否在退避中
            if (this.backoffState.isBackingOff) {
                const now = Date.now();
                if (now < this.backoffState.nextRetryTime) {
                    // 还在等待期
                    await this.sleep(this.backoffState.nextRetryTime - now);
                }
                this.backoffState.isBackingOff = false;
            }

            // 执行一次自愈迭代
            const result = await this.selfHealingLoop.heal(currentCode, compilerErrors);

            totalIterations += result.iterations;

            // 分析结果
            const previousLoss = currentLoss;
            currentLoss = result.finalLoss;
            currentCode = result.finalCode;

            if (result.converged) {
                // 收敛成功
                backoffEvents.push({
                    type: 'converged',
                    level: this.backoffState.level,
                    loss: currentLoss,
                    timestamp: Date.now(),
                });

                return {
                    success: true,
                    finalCode: currentCode,
                    finalLoss: currentLoss,
                    iterations: totalIterations,
                    backoffEvents,
                    snapshotsTaken: this.snapshots.length,
                };
            }

            // 判断改善还是恶化
            if (currentLoss < previousLoss - 0.01) {
                // 改善了
                this.consecutiveFailures = 0;
                this.consecutiveImprovements++;

                // 成功改善后，降低退避级别
                if (this.backoffState.level > 0) {
                    this.backoffState.level--;
                    this.backoffState.waitTimeMs = this.computeWaitTime();

                    backoffEvents.push({
                        type: 'decrease-backoff',
                        level: this.backoffState.level,
                        loss: currentLoss,
                        timestamp: Date.now(),
                    });
                }

                // 改善足够多次，提前退出
                if (this.consecutiveImprovements >= this.config.improvementThreshold) {
                    backoffEvents.push({
                        type: 'early-exit-improvement',
                        level: this.backoffState.level,
                        loss: currentLoss,
                        timestamp: Date.now(),
                    });

                    return {
                        success: true,
                        finalCode: currentCode,
                        finalLoss: currentLoss,
                        iterations: totalIterations,
                        backoffEvents,
                        snapshotsTaken: this.snapshots.length,
                    };
                }

                // 保存快照
                const snapshot = this.createSnapshot('improvement', currentCode, {
                    totalLoss: currentLoss,
                    dimensions: { compilerLoss: 0, typeLoss: 0, safetyLoss: 0, semanticLoss: 0 },
                    feedback: [],
                    confidence: 0.9,
                    converged: false,
                });
                this.snapshots.push(snapshot);
                this.lastStableLoss = currentLoss;
            } else if (currentLoss > previousLoss + 0.01) {
                // 恶化了
                this.consecutiveImprovements = 0;
                this.consecutiveFailures++;

                // 回滚到上一个稳定快照
                const stableSnapshot = this.findStableSnapshot();
                if (stableSnapshot) {
                    currentCode = new Map(stableSnapshot.code);
                    currentLoss = stableSnapshot.loss.totalLoss;

                    backoffEvents.push({
                        type: 'rollback',
                        level: this.backoffState.level,
                        loss: currentLoss,
                        timestamp: Date.now(),
                    });
                }

                // 失败增加，退避级别
                this.increaseBackoff();

                backoffEvents.push({
                    type: 'increase-backoff',
                    level: this.backoffState.level,
                    loss: currentLoss,
                    timestamp: Date.now(),
                });

                // 连续失败太多次，放弃
                if (this.consecutiveFailures >= this.config.giveupThreshold) {
                    backoffEvents.push({
                        type: 'giveup',
                        level: this.backoffState.level,
                        loss: currentLoss,
                        timestamp: Date.now(),
                    });

                    return {
                        success: false,
                        finalCode: currentCode,
                        finalLoss: currentLoss,
                        iterations: totalIterations,
                        backoffEvents,
                        snapshotsTaken: this.snapshots.length,
                    };
                }
            } else {
                // 没有明显变化（ plateau）
                this.consecutiveImprovements = 0;
                this.consecutiveFailures = 0;

                // 轻微增加退避
                if (this.backoffState.level < this.config.maxBackoffLevel) {
                    this.backoffState.level++;
                    this.backoffState.waitTimeMs = this.computeWaitTime();
                }

                backoffEvents.push({
                    type: 'plateau',
                    level: this.backoffState.level,
                    loss: currentLoss,
                    timestamp: Date.now(),
                });

                // 保存快照
                const snapshot = this.createSnapshot('plateau', currentCode, {
                    totalLoss: currentLoss,
                    dimensions: { compilerLoss: 0, typeLoss: 0, safetyLoss: 0, semanticLoss: 0 },
                    feedback: [],
                    confidence: 0.5,
                    converged: false,
                });
                this.snapshots.push(snapshot);

                // 连续plateau太多次，放弃
                if (this.snapshots.filter(s => s.reason === 'plateau').length >= 3) {
                    backoffEvents.push({
                        type: 'giveup-plateau',
                        level: this.backoffState.level,
                        loss: currentLoss,
                        timestamp: Date.now(),
                    });

                    return {
                        success: false,
                        finalCode: currentCode,
                        finalLoss: currentLoss,
                        iterations: totalIterations,
                        backoffEvents,
                        snapshotsTaken: this.snapshots.length,
                    };
                }
            }

            // 安全检查：快照太多，清理旧快照
            if (this.snapshots.length > 20) {
                this.snapshots = this.snapshots.slice(-10);
            }
        }
    }

    /**
     * 创建快照
     */
    private createSnapshot(
        reason: SnapshotState['reason'],
        code: Map<string, string>,
        loss: LossSignal
    ): SnapshotState {
        return {
            id: `snap-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
            code: new Map(code),
            loss,
            timestamp: Date.now(),
            reason,
        };
    }

    /**
     * 找到最近稳定快照
     */
    private findStableSnapshot(): SnapshotState | undefined {
        // 优先找 'improvement' 快照
        const improvements = this.snapshots.filter(s => s.reason === 'improvement');
        if (improvements.length > 0) {
            return improvements[improvements.length - 1];
        }

        // 否则找 'initial' 快照
        return this.snapshots.find(s => s.reason === 'initial');
    }

    /**
     * 增加退避级别
     */
    private increaseBackoff(): void {
        if (this.backoffState.level < this.config.maxBackoffLevel) {
            this.backoffState.level++;
            this.backoffState.waitTimeMs = this.computeWaitTime();
            this.backoffState.isBackingOff = true;
            this.backoffState.nextRetryTime = Date.now() + this.backoffState.waitTimeMs;
        }
    }

    /**
     * 计算当前退避等待时间（带抖动）
     */
    private computeWaitTime(): number {
        let waitTime = this.config.initialWaitMs * Math.pow(this.config.backoffFactor, this.backoffState.level);
        waitTime = Math.min(waitTime, this.config.maxWaitMs);

        // 添加抖动
        const jitterRange = waitTime * this.config.jitter;
        const jitter = (Math.random() - 0.5) * 2 * jitterRange;

        return Math.floor(waitTime + jitter);
    }

    /**
     * 睡眠辅助函数
     */
    private sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 获取退避统计
     */
    getBackoffStats(): {
        currentLevel: number;
        currentWaitMs: number;
        failureCount: number;
        snapshotsCount: number;
    } {
        return {
            currentLevel: this.backoffState.level,
            currentWaitMs: this.backoffState.waitTimeMs,
            failureCount: this.backoffState.failureCount,
            snapshotsCount: this.snapshots.length,
        };
    }
}

/**
 * 退避事件记录
 */
interface BackoffEvent {
    type: 'converged' | 'increase-backoff' | 'decrease-backoff' | 'rollback' | 'plateau' | 'giveup' | 'giveup-plateau' | 'early-exit-improvement';
    level: number;
    loss: number;
    timestamp: number;
}
```

### 指数退避的实际效果

```
退避过程示例：

初始: loss=0.85, level=0, wait=1ms
iter 1: loss=0.70 (改善) → level=0, wait=1ms
iter 2: loss=0.55 (改善) → level=0, wait=1ms
iter 3: loss=0.65 (恶化!) → rollback, level=1, wait=2ms
iter 4: loss=0.50 (改善) → level=0, wait=1ms
iter 5: loss=0.35 (改善) → level=0, wait=1ms, improvements=3 → early-exit!

最终: success=true, final_loss=0.35, iterations=5
```

---

## Step 3: PID控制器模型 — 编译器Error Log作为反馈信号

### 复用ch09的PID控制器

ch09已经实现了完整的PID控制器模型。本章复用它来控制自愈循环的节奏。

```typescript
// pid-controlled-healing.ts — PID控制的自愈循环

import { CompilerPIDController, FeedbackController, ErrorHistoryTracker } from './ch09-feedback-loop';

/**
 * PID控制的CritiqueAgent
 *
 * 在CritiqueAgent基础上增加PID控制
 * 根据历史追踪器判断是否收敛/发散
 */
export class PIDCritiqueAgent extends CritiqueAgent {
    private pidController: CompilerPIDController;
    private errorTracker: ErrorHistoryTracker;

    constructor(name: string = 'PIDCritiqueAgent') {
        super(name);
        this.pidController = new CompilerPIDController();
        this.errorTracker = new ErrorHistoryTracker();
    }

    /**
     * 重写过评估方法，加入PID控制逻辑
     */
    async evaluateWithPID(
        originalCode: Map<string, string>,
        modifiedCode: Map<string, string>,
        compilerErrors: CompilerError[],
        previousLoss?: LossSignal
    ): Promise<PIDEvaluationResult> {
        // 基础Critique评估
        const baseEvaluation = await this.evaluate(originalCode, modifiedCode, compilerErrors, previousLoss);

        // 用错误数量更新PID追踪器
        const errorCount = compilerErrors.filter(e => e.severity === 'error').length;
        this.errorTracker.record(errorCount);

        // PID控制器计算修正力度
        const correction = this.pidController.computeCorrection(0, errorCount);
        const action = this.pidController.decideAction(correction);

        // 用PID判断收敛/发散
        const isConverging = this.errorTracker.isConverging();
        const isDiverging = this.errorTracker.isDiverging();

        // 如果发散，强化Critique的严格度
        let adjustedEvaluation = { ...baseEvaluation };
        if (isDiverging) {
            // 发散时，提高损失估计
            adjustedEvaluation.totalLoss = Math.min(1.0, baseEvaluation.totalLoss * 1.3);
            adjustedEvaluation.dimensions.compilerLoss = Math.min(1.0, baseEvaluation.dimensions.compilerLoss * 1.3);
        }

        return {
            ...adjustedEvaluation,
            pidCorrection: correction,
            pidAction: action,
            isConverging,
            isDiverging,
            errorVelocity: this.errorTracker.getErrorVelocity(),
        };
    }

    /**
     * 重置PID状态
     */
    reset(): void {
        this.pidController.reset();
        this.errorTracker.clear();
    }
}

interface PIDEvaluationResult extends LossSignal {
    pidCorrection: number;
    pidAction: ControllerAction;
    isConverging: boolean;
    isDiverging: boolean;
    errorVelocity: number;
}

/**
 * 编译器错误历史记录器
 * 与ch09的ErrorHistoryTracker集成
 */
export class CompilerErrorHistory {
    private tracker: ErrorHistoryTracker;
    private entries: Array<{ timestamp: number; errors: CompilerError[] }> = [];

    constructor(maxEntries: number = 50) {
        this.tracker = new ErrorHistoryTracker(maxEntries);
    }

    /**
     * 记录一轮的错误
     */
    record(errors: CompilerError[]): void {
        this.entries.push({
            timestamp: Date.now(),
            errors,
        });

        const errorCount = errors.filter(e => e.severity === 'error').length;
        this.tracker.record(errorCount);
    }

    /**
     * 获取错误变化速度
     */
    getVelocity(): number {
        return this.tracker.getErrorVelocity();
    }

    /**
     * 判断是否收敛
     */
    isConverging(tolerance: number = 0.1): boolean {
        return this.tracker.isConverging(tolerance);
    }

    /**
     * 判断是否发散
     */
    isDiverging(): boolean {
        return this.tracker.isDiverging();
    }

    /**
     * 获取历史
     */
    getHistory(): Array<{ timestamp: number; errorCount: number }> {
        return this.entries.map(e => ({
            timestamp: e.timestamp,
            errorCount: e.errors.filter(err => err.severity === 'error').length,
        }));
    }
}
```

---

## Step 4: 魔法时刻段落 — 梯度下降的类比

### 魔法时刻

**自愈不是AI在修复，而是系统在强制AI进行梯度下降。**

GAN（生成对抗网络）的训练过程揭示了一个深刻的事实：生成器从来不需要"理解"它生成的内容。生成器只需要沿着判别器给出的梯度方向调整参数。真正的学习发生在判别器里——它计算损失，提供梯度。

这个事实在自愈循环中完全成立：

**GeneratorAgent不"理解"代码，它只沿梯度方向移动。CritiqueAgent计算梯度，但它也不"理解"代码。**

那谁在理解？没有人。或者说：**系统本身在理解**。

系统通过CritiqueAgent的计算和GeneratorAgent的梯度下降，实现了某种涌现的理解。这不是任何单个Agent的智能，而是两个Agent对抗产生的系统级智能。

类比神经网络的训练：

```
传统AI修复：
  AI读取错误 → AI理解代码 → AI生成修复 → 过程结束

自愈循环（GAN-like）：
  Generator生成候选 → Critique计算梯度 → 系统强制梯度下降
  → Generator更新参数 → 重复直到收敛
```

关键区别在于**没有显式的理解**。GeneratorAgent不知道自己在做什么，它只是沿着梯度移动。CritiqueAgent也不知道自己在做什么，它只是计算损失。但两者对抗的结果是：正确的代码被生成了。

这就是为什么ch09说"编译器反馈是梯度"——不是因为编译器理解了代码，而是因为编译器提供了一个可靠的损失信号。

**自愈循环是一个没有显式目标的优化过程。目标（正确的代码）是从对抗中涌现的。**

---

## Step 5: 桥接语

- **承上：** 第十章的TNR解决了修复失败后的回滚问题。但TNR是事后的、滞后的——它只在修复"提交"后才检查。自愈循环通过CritiqueAgent和GeneratorAgent的对抗，实现了**实时的、在线的梯度下降**，把回滚变成了不必要。

- **启下：** 如果对抗循环本身陷入死循环怎么办？CritiqueAgent和GeneratorAgent互相强化，走向极端怎么办？下一章将回答：如何给对抗循环加上约束，确保它不会失控？

- **认知缺口：** GAN的训练有一个已知问题：模式崩溃（mode collapse）——生成器学会生成少数"安全"的样本，而不是多样化的真实样本。自愈循环是否也会模式崩溃？GeneratorAgent是否会学会生成"讨好CritiqueAgent"但实际错误的修复？这个风险需要在架构设计中提前考虑。

---

## 本章来源

### 一手来源

| 来源 | URL | 关键数据 |
|------|-----|---------|
| "Self-Healing Software Systems: Lessons from Nature, Powered by AI" (arXiv:2504.20093) | https://arxiv.org/2504.20093 | 自愈系统三组件框架：Sensory Inputs、Cognitive Core、Healing Agents；为CritiqueAgent/GeneratorAgent的对抗模型提供理论基础 |
| "Agentic Testing: Multi-Agent Systems for Software Quality" (arXiv:2601.02454) | https://arxiv.org/2601.02454 | 三Agent闭环系统的验证框架，与自愈循环的CritiqueAgent验证机制高度相关 |
| "The Kitchen Loop: User-Spec-Driven Self-Evolving Codebase" (arXiv:2603.25697) | https://arxiv.org/2603.25697 | 1094+ merged PRs，零回归——自愈循环实际效果的证明 |
| "From LLMs to Agents in Programming" (arXiv:2601.12146) | https://arxiv.org/2601.12146 | 编译器集成提升编译成功率5.3到79.4个百分点；反馈回路将LLM从"被动生成器"转变为"主动Agent" |
| OpenAI Harness Engineering | https://openai.com/index/harness-engineering/ | 百万行代码、0行人类手写——自愈循环的实际工程案例 |

### 二手来源

| 来源 | 用途 |
|------|------|
| research-findings.md (Section 3.3) | 自愈系统三组件框架，为CritiqueAgent/GeneratorAgent提供概念基础 |
| research-findings.md (Section 3.1) | llvm-autofix研究，编译器反馈驱动自愈的关键论文 |
| ch09-feedback-loop.md | PID控制器模型，编译器Error Log作为反馈信号 |
| ch10-tnr-formal.md | TNR事务性无回归，回滚机制的理论基础 |
| GAN理论（Goodfellow et al.） | 生成对抗网络的梯度下降理论，映射到自愈循环 |

### 理论来源

| 来源 | 用途 |
|------|------|
| 生成对抗网络（GAN）理论 | CritiqueAgent/GeneratorAgent的对抗模型理论基础 |
| 指数退避算法 | 网络重试的经典算法，应用于自愈循环的收敛控制 |
| PID控制理论 | 反馈控制理论，编译器错误作为误差信号的来源 |
| 软件事务内存（STM） | TNR的理论基础，与自愈循环的回滚机制相关 |
