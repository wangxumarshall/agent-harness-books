# 第三部分：编译器层 — 死循环检测与强制回滚

## 本章Q

如何防止AI在错误中无限循环？

## 魔法时刻

**死循环的真正问题不是AI停不下来，而是系统如何在AI停不下来时保持可用。**

这不是一个技术问题，这是一个哲学问题。

传统观点认为，死循环是"AI犯错"的结果——AI卡在某个错误的修复方向上，不断重试。但这个理解是错的。死循环不是AI的问题，死循环是**系统设计**的问题。

想象一下：如果你在写一个Web服务，某个请求触发了死循环，你会怎么做？你不会去"修复那个请求"。你会去"重启那个服务"。为什么？因为你知道死循环是系统层面的问题，不是请求层面的问题。

AI修复的死循环也一样。GeneratorAgent和CritiqueAgent互相强化，走向极端——这不是AI的bug，这是**反馈回路缺少截止机制**。解决方案不是让AI更聪明，而是让系统在AI不停止时保持可用。

怎么做到？用Git Commit作为断点。每一轮成功的修复都是一个Git Commit。当系统检测到死循环倾向时，回滚到上一个Commit——不是回滚到上一个快照，而是回滚到一个**经过验证的、确实能工作的状态**。

**这就是死循环检测的魔法：与其防止AI犯错，不如确保AI犯错后系统仍然可用。**

---

## 五分钟摘要

第十一章的自愈循环解决了"AI如何通过对抗实现自愈"的问题。但对抗循环有一个致命缺陷：**没有截止机制**。如果CritiqueAgent和GeneratorAgent互相强化，走向极端，系统会陷入死循环，永远不停止。

死循环检测不是防止AI犯错。死循环检测是**在AI犯错后防止系统崩溃**。

具体来说，我们解决了三个问题：

1. **检测问题**：如何检测到"同一编译错误"的循环？
2. **救援问题**：如何在死循环发生时保持系统可用？
3. **介入问题**：何时触发人类介入？

答案分别是：哈希计数器（Hash Counter）、Git Commit断点、人工介入阈值。

---

## Step 1: 死循环检测算法 — 同一编译错误循环的检测

### 哈希计数器：检测"同一错误"的循环

死循环检测的核心问题是：**什么构成"同一个错误"？**

编译器每次报错都是不同的文本，但可能是同一个错误原因。考虑这个场景：

```
第1轮修复：
  Error: TS2531: Object is possibly 'null'. at src/utils.ts:42:15
  ↓ AI修复
第2轮修复：
  Error: TS2531: Object is possibly 'null'. at src/utils.ts:42:15
  ↓ AI修复（换了个写法）
第3轮修复：
  Error: TS2531: Object is possibly 'null'. at src/utils.ts:42:15
```

编译器错误信息完全相同，但AI以为自己在解决不同问题。这是经典的死循环。

解决方案是**哈希计数器**——对错误模式进行哈希，而不是对错误文本进行哈希。

```typescript
// deadloop-detector.ts — 死循环检测器

import { createHash } from 'crypto';

/**
 * 错误模式 —— 错误信息的抽象表示
 */
interface ErrorPattern {
    /** 错误代码（去除了具体行号、列号） */
    code: string;

    /** 错误类型 */
    type: 'type-error' | 'import-error' | 'syntax-error' | 'runtime-error';

    /** 涉及的文件（不含具体路径） */
    files: string[];

    /** 错误关键词（去重后） */
    keywords: string[];

    /** 错误哈希 */
    hash: string;
}

/**
 * 循环状态
 */
interface LoopState {
    /** 已检测到的错误模式序列 */
    patternHistory: ErrorPattern[];

    /** 每个模式的重复次数 */
    patternCounts: Map<string, number>;

    /** 连续未改善次数 */
    noImprovementCount: number;

    /** 上一次的损失值 */
    lastLoss: number;

    /** 是否检测到循环 */
    loopDetected: boolean;

    /** 循环类型 */
    loopType?: 'exact' | 'semantic' | 'plateau';
}

/**
 * 错误模式提取器
 * 将具体的编译器错误转换为抽象的错误模式
 */
export class ErrorPatternExtractor {
    /**
     * 从编译器错误提取模式
     */
    extractPattern(error: CompilerError): ErrorPattern {
        // 提取错误关键词（去噪）
        const keywords = this.extractKeywords(error.message);

        // 生成错误模式哈希
        const patternString = JSON.stringify({
            code: error.code,
            type: this.categorizeError(error),
            files: [this.normalizeFilePath(error.file)],
            keywords: keywords.sort(),
        });

        const hash = createHash('sha256').update(patternString).digest('hex').slice(0, 16);

        return {
            code: error.code,
            type: this.categorizeError(error),
            files: [this.normalizeFilePath(error.file)],
            keywords,
            hash,
        };
    }

    /**
     * 提取错误关键词
     */
    private extractKeywords(message: string): string[] {
        // 去除具体值（数字、字符串字面量）
        const cleaned = message
            .replace(/\d+/g, 'N')
            .replace(/'[^']*'/g, "'X'")
            .replace(/"[^"]*"/g, '"X"')
            .replace(/`[^`]*`/g, '`X`');

        // 提取单词
        const words = cleaned.split(/\s+/)
            .filter(w => w.length > 3)
            .filter(w => !['undefined', 'possibly', 'cannot', 'expected'].includes(w.toLowerCase()));

        // 去重
        return [...new Set(words.map(w => w.toLowerCase()))];
    }

    /**
     * 归一化文件路径（去除具体目录）
     */
    private normalizeFilePath(file: string): string {
        // 只保留最后两个路径段
        const parts = file.replace(/\\/g, '/').split('/');
        return parts.slice(-2).join('/');
    }

    /**
     * 分类错误类型
     */
    private categorizeError(error: CompilerError): ErrorPattern['type'] {
        const code = error.code.toUpperCase();
        const message = error.message.toLowerCase();

        if (code.startsWith('TS2307') || message.includes('cannot find')) {
            return 'import-error';
        }
        if (code.startsWith('TS7006') || code.startsWith('TS2531') || message.includes('null') || message.includes('undefined')) {
            return 'type-error';
        }
        if (code.startsWith('TS1005') || code.startsWith('TS1107')) {
            return 'syntax-error';
        }
        return 'runtime-error';
    }
}

/**
 * 死循环检测器
 *
 * 检测三种类型的死循环：
 * 1. 精确循环：同一个错误模式重复出现
 * 2. 语义循环：不同错误文本但同一错误原因
 * 3.  plateau（ plateau）：损失值不再下降
 */
export class DeadLoopDetector {
    private extractor: ErrorPatternExtractor;
    private state: LoopState;
    private config: {
        /** 同一模式最大重复次数 */
        maxPatternRepeat: number;

        /** plateau检测阈值（损失变化小于此值视为plateau） */
        plateauThreshold: number;

        /** plateau最大连续次数 */
        maxPlateauCount: number;

        /** 最大历史记录长度 */
        maxHistoryLength: number;
    };

    constructor(config: Partial<DeadLoopDetector['config']> = {}) {
        this.extractor = new ErrorPatternExtractor();
        this.state = this.createInitialState();
        this.config = {
            maxPatternRepeat: 3,
            plateauThreshold: 0.01,
            maxPlateauCount: 5,
            maxHistoryLength: 50,
            ...config,
        };
    }

    /**
     * 创建初始状态
     */
    private createInitialState(): LoopState {
        return {
            patternHistory: [],
            patternCounts: new Map(),
            noImprovementCount: 0,
            lastLoss: 1.0,
            loopDetected: false,
        };
    }

    /**
     * 检测死循环
     *
     * @param currentErrors 当前编译器错误
     * @param currentLoss 当前损失值
     * @returns 是否检测到死循环
     */
    detect(currentErrors: CompilerError[], currentLoss: number): {
        loopDetected: boolean;
        loopType?: 'exact' | 'semantic' | 'plateau';
        pattern?: ErrorPattern;
        message: string;
    } {
        // 提取当前错误模式
        const currentPatterns = currentErrors.map(e => this.extractor.extractPattern(e));

        // 检查精确循环
        for (const pattern of currentPatterns) {
            const count = (this.state.patternCounts.get(pattern.hash) || 0) + 1;
            this.state.patternCounts.set(pattern.hash, count);

            if (count >= this.config.maxPatternRepeat) {
                this.state.loopDetected = true;
                this.state.loopType = 'exact';
                return {
                    loopDetected: true,
                    loopType: 'exact',
                    pattern,
                    message: `检测到精确循环：错误模式 "${pattern.code}" 已重复 ${count} 次`,
                };
            }
        }

        // 检查plateau（损失不再下降）
        const lossDelta = this.state.lastLoss - currentLoss;
        if (lossDelta < this.config.plateauThreshold) {
            this.state.noImprovementCount++;
        } else {
            this.state.noImprovementCount = 0;
        }

        this.state.lastLoss = currentLoss;

        if (this.state.noImprovementCount >= this.config.maxPlateauCount) {
            this.state.loopDetected = true;
            this.state.loopType = 'plateau';
            return {
                loopDetected: true,
                loopType: 'plateau',
                message: `检测到plateau：损失值连续 ${this.state.noImprovementCount} 次未改善（变化 < ${this.config.plateauThreshold}）`,
            };
        }

        // 更新历史记录
        this.state.patternHistory.push(...currentPatterns);
        if (this.state.patternHistory.length > this.config.maxHistoryLength) {
            this.state.patternHistory = this.state.patternHistory.slice(-this.config.maxHistoryLength);
        }

        return {
            loopDetected: false,
            message: '未检测到死循环',
        };
    }

    /**
     * 重置检测状态
     */
    reset(): void {
        this.state = this.createInitialState();
    }

    /**
     * 获取当前状态
     */
    getState(): Readonly<LoopState> {
        return { ...this.state };
    }
}

/**
 * 编译错误接口（与ch10保持一致）
 */
interface CompilerError {
    code: string;
    message: string;
    file: string;
    line: number;
    column: number;
    severity: 'error' | 'warning';
}
```

### 哈希计数器的检测逻辑

哈希计数器的工作原理是**模式抽象**：

```
具体错误 → 模式抽象 → 哈希 → 计数

Error: TS2531: Object is possibly 'null' at src/utils.ts:42:15
  ↓ 模式抽象（去除具体值和路径）
{ code: TS2531, type: type-error, files: [utils.ts], keywords: [object, possibly, null] }
  ↓ 哈希
hash: a3f2b8c1d4e5
  ↓ 计数
TS2531模式: 第1次出现

Error: TS2531: Object is possibly 'null' at src/helpers.ts:10:20
  ↓ 模式抽象
{ code: TS2531, type: type-error, files: [helpers.ts], keywords: [object, possibly, null] }
  ↓ 哈希
hash: a3f2b8c1d4e5  ← 相同哈希！
  ↓ 计数
TS2531模式: 第2次出现 ← 触发死循环检测
```

关键洞察是：**错误文本不同，但错误模式相同 = 同一错误**。

---

## Step 2: Git Commit断点救援 — 回滚至上个通过节点

### Git Commit作为断点

传统的TNR回滚是回滚到**快照**——修复前的某个时间点。但快照的问题是：快照可能已经过时了。如果快照是在错误发生之前创建的，那个快照可能已经包含了一个不完整的功能。

更好的方法是回滚到**上一个Git Commit**——一个经过验证的、确实能工作的状态。

Git Commit有快照没有的特性：

1. **可验证**：每个Commit都有CI验证
2. **可追溯**：每个Commit都有作者、时间、消息
3. **可对比**：可以用`git diff`查看变更
4. **可分支**：可以在不同分支尝试不同修复

```typescript
// git-breakpoint-rescue.ts — Git Commit断点救援

import { execSync } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';

/**
 * Git Commit信息
 */
interface GitCommit {
    /** Commit hash（短） */
    hash: string;

    /** 完整hash */
    fullHash: string;

    /** 提交消息 */
    message: string;

    /** 作者 */
    author: string;

    /** 提交时间 */
    timestamp: number;

    /** 是否通过CI */
    ciPassed?: boolean;

    /** 验证状态 */
    verificationStatus: 'unverified' | 'passing' | 'failing';
}

/**
 * 断点状态
 */
interface BreakpointState {
    /** 当前HEAD Commit */
    currentCommit?: GitCommit;

    /** 上一个稳定Commit（最后通过的CI） */
    lastStableCommit?: GitCommit;

    /** 断点历史 */
    breakpointHistory: GitCommit[];

    /** 是否处于死循环状态 */
    inDeadLoop: boolean;

    /** 死循环开始时的Commit */
    deadLoopStartCommit?: GitCommit;
}

/**
 * Git Commit断点救援器
 *
 * 使用Git Commit作为断点，在死循环发生时回滚到上一个稳定状态
 */
export class GitBreakpointRescuer {
    private repoPath: string;
    private state: BreakpointState;
    private config: {
        /** CI检查命令 */
        ciCheckCommand: string;

        /** 两次Commit之间的最小时间间隔（毫秒） */
        minCommitInterval: number;

        /** 最大回滚深度 */
        maxRollbackDepth: number;
    };

    constructor(
        repoPath: string,
        config: Partial<GitBreakpointRescuer['config']> = {}
    ) {
        this.repoPath = repoPath;
        this.state = {
            breakpointHistory: [],
            inDeadLoop: false,
        };
        this.config = {
            ciCheckCommand: 'npm test',
            minCommitInterval: 60000, // 1分钟
            maxRollbackDepth: 10,
            ...config,
        };
    }

    /**
     * 获取当前HEAD Commit信息
     */
    getCurrentCommit(): GitCommit {
        const fullHash = execSync('git rev-parse HEAD', { cwd: this.repoPath })
            .toString().trim();
        const shortHash = fullHash.slice(0, 6);
        const message = execSync('git log -1 --pretty=%B', { cwd: this.repoPath })
            .toString().trim().split('\n')[0];
        const author = execSync('git log -1 --pretty=%an', { cwd: this.repoPath })
            .toString().trim();
        const timestamp = parseInt(
            execSync('git log -1 --pretty=%ct', { cwd: this.repoPath }).toString().trim()
        ) * 1000;

        return {
            hash: shortHash,
            fullHash,
            message,
            author,
            timestamp,
            verificationStatus: 'unverified',
        };
    }

    /**
     * 查找上一个稳定Commit
     *
     * 稳定Commit = CI通过的Commit
     */
    findLastStableCommit(maxDepth: number = 10): GitCommit | undefined {
        try {
            // 获取最近的N个Commits
            const log = execSync(
                `git log --oneline -${maxDepth}`,
                { cwd: this.repoPath }
            ).toString().trim();

            const commits = log.split('\n').map(line => {
                const [hash, ...msgParts] = line.split(' ');
                return {
                    hash,
                    fullHash: execSync(`git rev-parse ${hash}`, { cwd: this.repoPath })
                        .toString().trim(),
                    message: msgParts.join(' '),
                    author: '',
                    timestamp: 0,
                    verificationStatus: 'unverified' as const,
                };
            });

            // 逐个检查CI状态
            for (const commit of commits) {
                // 获取作者和时间
                const info = execSync(
                    `git log -1 --format="%an|%ct" ${commit.hash}`,
                    { cwd: this.repoPath }
                ).toString().trim().split('|');
                commit.author = info[0];
                commit.timestamp = parseInt(info[1]) * 1000;

                // 检查CI状态
                const ciStatus = this.checkCIStatus(commit.fullHash);
                commit.verificationStatus = ciStatus ? 'passing' : 'failing';

                if (ciStatus) {
                    return commit;
                }
            }
        } catch (e) {
            console.error('查找稳定Commit失败:', e);
        }

        return undefined;
    }

    /**
     * 检查指定Commit的CI状态
     *
     * 使用git commit作为检查点，而非git stash，避免崩溃导致工作区修改丢失
     */
    private checkCIStatus(commitHash: string): boolean {
        const backupRef = `refs/backups/checkci-${Date.now()}`;
        try {
            // 创建安全检查点（使用git commit而非stash，避免数据丢失风险）
            execSync(`git branch ${backupRef}`, { cwd: this.repoPath });

            // 切换到目标Commit
            execSync(`git checkout ${commitHash}`, { cwd: this.repoPath });

            // 运行CI检查
            const result = execSync(this.config.ciCheckCommand, {
                cwd: this.repoPath,
                stdio: 'pipe',
                timeout: 120000,
            });

            // 恢复原始HEAD
            execSync('git checkout -', { cwd: this.repoPath });

            // 清理检查点分支
            execSync(`git branch -D ${backupRef}`, { cwd: this.repoPath });

            return result.status === 0;
        } catch (e) {
            // 尝试恢复到检查点
            try {
                execSync('git checkout -', { cwd: this.repoPath });
                // 检查点仍然存在，可以直接使用
            } catch (e2) {
                // 如果无法通过checkout -恢复，尝试从备份ref恢复
                try {
                    execSync(`git stash`, { cwd: this.repoPath });
                    execSync(`git checkout ${backupRef}`, { cwd: this.repoPath });
                    execSync(`git branch -d ${backupRef}`, { cwd: this.repoPath });
                } catch (e3) {
                    console.error('恢复HEAD失败:', e3);
                }
            }
            // 尝试清理可能残留的备份分支
            try {
                execSync(`git branch -D ${backupRef}`, { cwd: this.repoPath });
            } catch (e4) {
                // 忽略清理失败
            }
            return false;
        }
    }

    /**
     * 执行断点救援
     *
     * @param reason 救援原因
     * @returns 救援结果
     */
    async rescue(reason: 'deadloop' | 'divergence' | 'manual'): Promise<{
        success: boolean;
        rolledBackTo?: GitCommit;
        message: string;
    }> {
        const current = this.getCurrentCommit();

        // 如果已经有上次稳定Commit，使用它
        if (this.state.lastStableCommit) {
            const success = await this.rollbackTo(this.state.lastStableCommit);
            return {
                success,
                rolledBackTo: this.state.lastStableCommit,
                message: `断点救援成功：回滚到 ${this.state.lastStableCommit.hash} "${this.state.lastStableCommit.message}"`,
            };
        }

        // 否则查找上一个稳定Commit
        const stableCommit = this.findLastStableCommit(this.config.maxRollbackDepth);

        if (!stableCommit) {
            return {
                success: false,
                message: '断点救援失败：未找到稳定Commit',
            };
        }

        const success = await this.rollbackTo(stableCommit);
        return {
            success,
            rolledBackTo: stableCommit,
            message: success
                ? `断点救援成功：回滚到 ${stableCommit.hash} "${stableCommit.message}"`
                : '断点救援失败：回滚操作失败',
        };
    }

    /**
     * 回滚到指定Commit
     */
    private async rollbackTo(target: GitCommit): Promise<boolean> {
        try {
            // 记录当前状态到历史
            const current = this.getCurrentCommit();
            this.state.breakpointHistory.push(current);

            // 执行回滚（软重置，保留工作区修改）
            execSync(`git reset --soft ${target.fullHash}`, { cwd: this.repoPath });

            // 更新状态
            this.state.lastStableCommit = target;
            this.state.inDeadLoop = false;

            return true;
        } catch (e) {
            console.error('回滚失败:', e);
            return false;
        }
    }

    /**
     * 标记当前Commit为稳定
     */
    markCurrentAsStable(): void {
        const current = this.getCurrentCommit();
        current.verificationStatus = 'passing';
        this.state.lastStableCommit = current;
        this.state.breakpointHistory.push(current);
    }

    /**
     * 获取状态
     */
    getState(): Readonly<BreakpointState> {
        return { ...this.state };
    }
}
```

### 断点救援的流程

```
检测到死循环
  ↓
GitBreakpointRescuer.rescue()
  ↓
检查是否有上次稳定Commit
  ├── 有 → 直接回滚到上次稳定Commit
  └── 没有 → 查找上一个CI通过的Commit
                ↓
            找到 → 回滚到该Commit
                ↓
            未找到 → 救援失败，需要人工介入
```

---

## Step 3: 人类介入触发条件 — 强制人工审核的判定逻辑

### 人工介入不是失败，是设计决策

传统观点认为人工介入是"系统不行了"的结果。但这是错误的观点。

人工介入是**系统的正常状态**，不是异常状态。当系统检测到以下情况时，触发人工介入：

1. **死循环无法通过自动回滚解决**
2. **连续多次回滚后仍然失败**
3. **损失值在多次尝试后没有改善**
4. **人类介入被明确请求**

人工介入的触发条件需要精心设计。太敏感会导致大量噪音，太迟钝会导致系统崩溃。

```typescript
// human-intervention-trigger.ts — 人类介入触发器

/**
 * 人工介入原因
 */
type InterventionReason =
    | 'deadloop_unresolvable'      // 死循环无法通过自动回滚解决
    | 'rollback_exhausted'         // 连续多次回滚后仍然失败
    | 'loss_plateau'               // 损失值长期无改善
    | 'explicit_request'           // 人类明确请求介入
    | 'unsafe_operation'           // 检测到不安全操作
    | 'semantic_drift'             // 语义漂移超出阈值
    | 'bootstrap_failure';         // Harness自身启动失败

/**
 * 人工介入请求
 */
interface InterventionRequest {
    /** 请求ID */
    id: string;

    /** 触发原因 */
    reason: InterventionReason;

    /** 详细描述 */
    description: string;

    /** 当前系统状态摘要 */
    systemState: {
        currentLoss: number;
        iterationCount: number;
        rollbackCount: number;
        errorCount: number;
        lastCommit?: string;
    };

    /** 建议的人类行动 */
    suggestedAction: string;

    /** 优先级 */
    priority: 'low' | 'medium' | 'high' | 'critical';

    /** 创建时间 */
    createdAt: number;
}

/**
 * 人工介入配置
 */
interface InterventionConfig {
    /** 连续回滚次数阈值 */
    maxRollbackCount: number;

    /** 最大迭代次数 */
    maxIterationCount: number;

    /** 损失值改善阈值 */
    lossImprovementThreshold: number;

    /** 损失值 plateau 最大持续次数 */
    maxPlateauCount: number;

    /** 连续失败最大次数 */
    maxConsecutiveFailures: number;

    /** 是否有未处理的干预请求 */
    pendingIntervention?: InterventionRequest;
}

/**
 * 人工介入触发器
 *
 * 根据系统状态决定是否触发人工介入
 */
export class HumanInterventionTrigger {
    private config: InterventionConfig;
    private state: {
        rollbackCount: number;
        consecutiveFailures: number;
        plateauCount: number;
        lastLossValues: number[];
        interventionHistory: InterventionRequest[];
    };

    constructor(config: Partial<InterventionConfig> = {}) {
        this.config = {
            maxRollbackCount: 3,
            maxIterationCount: 50,
            lossImprovementThreshold: 0.05,
            maxPlateauCount: 10,
            maxConsecutiveFailures: 5,
            ...config,
        };

        this.state = {
            rollbackCount: 0,
            consecutiveFailures: 0,
            plateauCount: 0,
            lastLossValues: [],
            interventionHistory: [],
        };
    }

    /**
     * 评估是否需要人工介入
     */
    evaluate(params: {
        currentLoss: number;
        previousLoss?: number;
        iterationCount: number;
        rollbackCount: number;
        errorPatterns: string[];
        detectedUnsafeOps?: string[];
        semanticDriftScore?: number;
    }): InterventionRequest | null {
        const {
            currentLoss,
            previousLoss,
            iterationCount,
            rollbackCount,
            errorPatterns,
            detectedUnsafeOps,
            semanticDriftScore,
        } = params;

        // 更新状态
        this.updateState(currentLoss, previousLoss, rollbackCount);

        // 检查各种触发条件
        const triggers: Array<{
            condition: boolean;
            reason: InterventionReason;
            priority: InterventionRequest['priority'];
            description: string;
            suggestedAction: string;
        }> = [
            // 条件1：连续回滚次数超限
            {
                condition: rollbackCount >= this.config.maxRollbackCount,
                reason: 'rollback_exhausted',
                priority: 'critical',
                description: `连续回滚 ${rollbackCount} 次后仍然失败，自动修复已耗尽`,
                suggestedAction: '人工审查错误模式，确定是否有架构性问题需要解决',
            },

            // 条件2：最大迭代次数
            {
                condition: iterationCount >= this.config.maxIterationCount,
                reason: 'deadloop_unresolvable',
                priority: 'high',
                description: `已达到最大迭代次数 ${this.config.maxIterationCount}，未达到收敛条件`,
                suggestedAction: '人工审查当前状态，决定是否继续或回滚',
            },

            // 条件3：损失值长期无改善（plateau）
            {
                condition: this.state.plateauCount >= this.config.maxPlateauCount,
                reason: 'loss_plateau',
                priority: 'high',
                description: `损失值连续 ${this.state.plateauCount} 次改善不足 ${this.config.lossImprovementThreshold}`,
                suggestedAction: '人工审查是否为错误模式本身的问题',
            },

            // 条件4：连续失败
            {
                condition: this.state.consecutiveFailures >= this.config.maxConsecutiveFailures,
                reason: 'deadloop_unresolvable',
                priority: 'critical',
                description: `连续失败 ${this.state.consecutiveFailures} 次，系统处于不稳定状态`,
                suggestedAction: '立即人工介入，系统可能处于危险状态',
            },

            // 条件5：检测到不安全操作
            {
                condition: (detectedUnsafeOps?.length ?? 0) > 0,
                reason: 'unsafe_operation',
                priority: 'critical',
                description: `检测到不安全操作: ${detectedUnsafeOps?.join(', ')}`,
                suggestedAction: '立即人工介入，停止当前操作',
            },

            // 条件6：语义漂移
            {
                condition: (semanticDriftScore ?? 0) > 0.8,
                reason: 'semantic_drift',
                priority: 'high',
                description: `语义漂移分数 ${(semanticDriftScore ?? 0).toFixed(2)} 超过阈值 0.8`,
                suggestedAction: '人工审查修复是否改变了预期行为',
            },

            // 条件7：同样的错误模式重复出现
            {
                condition: this.isSamePatternRepeating(errorPatterns),
                reason: 'deadloop_unresolvable',
                priority: 'medium',
                description: `同样的错误模式 "${errorPatterns[0]}" 重复出现，可能需要不同的修复策略`,
                suggestedAction: '人工提供修复提示或改变修复策略',
            },
        ];

        // 返回第一个满足条件的触发器
        for (const trigger of triggers) {
            if (trigger.condition) {
                const request = this.createInterventionRequest(trigger);
                this.state.interventionHistory.push(request);
                this.config.pendingIntervention = request;
                return request;
            }
        }

        return null;
    }

    /**
     * 更新内部状态
     */
    private updateState(currentLoss: number, previousLoss?: number, rollbackCount?: number): void {
        // 更新回滚计数
        if (rollbackCount !== undefined) {
            this.state.rollbackCount = rollbackCount;
        }

        // 更新连续失败计数
        if (previousLoss !== undefined) {
            if (currentLoss >= previousLoss) {
                this.state.consecutiveFailures++;
            } else {
                this.state.consecutiveFailures = 0;
            }
        }

        // 更新plateau计数
        this.state.lastLossValues.push(currentLoss);
        if (this.state.lastLossValues.length > this.config.maxPlateauCount) {
            this.state.lastLossValues.shift();
        }

        if (this.state.lastLossValues.length >= 2) {
            const recent = this.state.lastLossValues.slice(-this.config.maxPlateauCount);
            const hasImprovement = recent.some((v, i) => i > 0 && v < recent[i - 1] - this.config.lossImprovementThreshold);
            if (!hasImprovement) {
                this.state.plateauCount++;
            } else {
                this.state.plateauCount = 0;
            }
        }
    }

    /**
     * 检查同样的错误模式是否重复出现
     */
    private isSamePatternRepeating(errorPatterns: string[]): boolean {
        if (errorPatterns.length < 2) return false;
        const first = errorPatterns[0];
        return errorPatterns.every(p => p === first);
    }

    /**
     * 创建干预请求
     */
    private createInterventionRequest(trigger: {
        reason: InterventionReason;
        priority: InterventionRequest['priority'];
        description: string;
        suggestedAction: string;
    }): InterventionRequest {
        return {
            id: `intervention-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
            reason: trigger.reason,
            description: trigger.description,
            systemState: {
                currentLoss: this.state.lastLossValues[this.state.lastLossValues.length - 1] ?? 1.0,
                iterationCount: 0, // 由调用方提供
                rollbackCount: this.state.rollbackCount,
                errorCount: 0, // 由调用方提供
            },
            suggestedAction: trigger.suggestedAction,
            priority: trigger.priority,
            createdAt: Date.now(),
        };
    }

    /**
     * 清除待处理的干预请求
     */
    clearPendingIntervention(): void {
        this.config.pendingIntervention = undefined;
    }

    /**
     * 获取干预历史
     */
    getInterventionHistory(): InterventionRequest[] {
        return [...this.state.interventionHistory];
    }
}
```

### 触发条件的设计原则

人工介入触发条件的设计有几个关键原则：

1. **分层触发**：不同严重程度对应不同优先级
2. **可配置**：不同场景可以调整阈值
3. **可追溯**：每次触发都有完整记录
4. **可撤销**：人类可以拒绝介入请求

---

## Step 4: 魔法时刻段落 — 停不下来的可用性保证

### 魔法时刻

死循环的真正问题不是AI停不下来。

你有过这样的经历吗？你的笔记本电脑死机了，你长按电源键强制关机。关机的那一刻，你心里想的是什么？

不是"这台电脑真烂"。你想的是：**我的文件还在吗？**

然后你重新按下电源键，系统启动，一切如常。你的文件，你的代码，你的工作——全部完好无损。

这就是死循环检测要实现的**用户体验**。

当你意识到AI陷入了死循环，你不应该慌张。你应该像强制关机一样——按下一个按钮，系统回到上一个稳定状态，你的工作全部完好。然后你可以重新开始。

**死循环检测不是让AI不犯错。死循环检测是确保AI犯错后，你的工作不会丢失。**

传统的Harness设计试图让AI"不犯错"。这是一个错误的目标。因为AI必然会犯错——这是概率的必然。

正确的目标是：**让AI犯错后系统仍然可用**。

怎么做到？答案是Git Commit作为断点。

```
AI修复 → Git Commit → CI验证 → 通过？
  ↓                              ↓
继续修复                    失败 → 触发回滚
                              ↓
                         回滚到上一个CI通过的Commit
                              ↓
                         AI从那个状态重新开始
```

这就是死循环检测的魔法时刻：**不是防止AI掉进坑里，而是确保AI掉进坑里后，你有能力把它拉出来。**

当系统检测到死循环，它不会慌张地尝试各种修复。它会冷静地执行Git回滚，回到上一个稳定状态。然后它会告诉你："嘿，我遇到了问题，你需要帮我看看。"

这不是失败。这是**系统的成熟**。

---

## Step 5: 开放问题 — Harness的自身脆弱性

### Bootstrap问题：谁验证验证者？

我们建立了一个完整的死循环检测系统：哈希计数器检测错误模式，Git Commit作为断点，人工介入作为最后防线。

但有一个根本性的问题我们没有回答：**如果Harness本身出错怎么办？**

考虑这个场景：

```
Harness的检测逻辑有bug
  ↓
错误地认为系统陷入死循环
  ↓
触发不必要的回滚
  ↓
丢失了有效的修复
```

或者更糟糕的场景：

```
Harness的回滚逻辑有bug
  ↓
回滚到错误的状态
  ↓
系统进入未知状态
  ↓
无法恢复
```

这是一个经典的**自举问题（Bootstrap Problem）**：谁来验证验证者？

我们有几个可能的答案：

1. **外部验证**：用一个独立的系统验证Harness的行为
2. **形式化方法**：用TLA+或Coq证明Harness的正确性
3. **冗余设计**：多个独立的检测机制，互相验证
4. **人类监督**：始终保留人工审查作为最后防线

但每个方案都有问题：

1. **外部验证**：外部系统本身也需要验证
2. **形式化方法**：成本高昂，难以应用于实际系统
3. **冗余设计**：增加复杂度，可能引入新的bug
4. **人类监督**：不可扩展

这是一个**开放问题**，我们没有完美的答案。

### 其他开放问题

**问题1：回滚的粒度**

Git Commit是原子性的——你回滚到整个Commit，而不是Commit中的某个部分。但有时候你只需要回滚某个文件的修改，而不是整个Commit。

如何实现更细粒度的回滚？

**问题2：死循环的预防**

我们讨论的是死循环的检测和恢复。但能否在死循环发生之前就预防它？

一个可能的方向是用机器学习预测死循环——在损失值还没有开始plateau之前就提前介入。

**问题3：人工介入的自动化**

人工介入是最后的防线，但人工介入的问题是**慢**。一个工程师可能需要几小时甚至几天来审查一个问题。

能否让AI辅助人工介入？例如，自动生成问题摘要、提供可能的解决方案？

---

## Step 6: 桥接语

- **承上：** 第十一章的自愈循环通过CritiqueAgent和GeneratorAgent的对抗实现了自愈。但对抗循环缺少截止机制——如果对抗无限持续，系统会死循环。死循环检测和强制回滚填补了这个空白。

- **启下：** 第三部分（ch08-ch12）建立了CompiledAgent——一个编译检查、TNR和自愈的完整系统。但CompiledAgent只在**编译时**工作。运行时呢？如果代码通过了编译，但在运行时崩溃了呢？下一部分将回答：如何将Harness从编译时扩展到运行时？

- **认知缺口：** 死循环检测依赖哈希计数器——对错误模式进行抽象。但如果AI的修复方向完全错误，产生的错误模式也是新的——哈希计数器检测不到。这是一种"未知的未知"错误。如何检测"产生新错误"的死循环？这需要超越模式匹配的检测方法。

---

## 本章来源

### 一手来源

| 来源 | URL | 关键数据 |
|------|-----|---------|
| "The Kitchen Loop: User-Spec-Driven Self-Evolving Codebase" (arXiv:2603.25697) | https://arxiv.org/2603.25697 | 漂移控制（Drift Control）+自动暂停门（Automatic Pause Gate）；死循环预防的实际工程案例 |
| Stripe Minions | https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents | CI最多跑两轮；第一轮失败→自动修复再跑，还失败→转交人类 |
| OpenDev 5层安全架构 | https://arxiv.org/html/2603.05344v1 | 第五层安全机制，人工介入作为最后防线 |
| OpenAI Harness Engineering | https://openai.com/index/harness-engineering/ | 合并哲学（Merge Philosophy）；审查，而非修改；发现需要大量修改→反思Harness哪里出错 |

### 二手来源

| 来源 | 用途 |
|------|------|
| research-findings.md (Section 3.1) | llvm-autofix研究，死循环检测的实践背景 |
| research-findings.md (Section 3.3) | Self-Healing Software Systems，自愈系统的三组件框架 |
| ch09-feedback-loop.md | PID控制器模型，反馈回路的理论基础 |
| ch10-tnr-formal.md | TNR事务性无回归，回滚机制的理论基础 |
| ch11-self-healing.md | 自愈循环，GeneratorAgent/CritiqueAgent对抗模型 |

### 理论来源

| 来源 | 用途 |
|------|------|
| 指数退避算法（Exponential Backoff） | 死循环检测的重试策略理论基础 |
| Git版本控制 | 断点救援的工程实践 |
| 混沌工程（Chaos Engineering） | 系统韧性设计，Netflix的猴子军团 |
