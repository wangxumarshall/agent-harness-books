# 第三部分：编译器层 — TNR事务性无回归的形式化定义

## 本章Q

当AI修复引入新bug时，如何保证状态不恶化？

## 魔法时刻

TNR的核心洞察只有一句话：**修复失败时，系统状态应该等价于"从未尝试修复"**。

这不是比喻。数据库有ACID——原子性（Atomicity）、一致性（Consistency）、隔离性（Isolation）、持久性（Durability）。TNR借鉴了其中的"A"和"I"：一个修复要么完全成功，要么完全不留痕迹地失败。没有"部分修复"导致的部分状态恶化。

当你在Git里提交一个破坏性变更，你可以`git revert`撤销。TNR是AI修复的`git revert`：如果修复引入的新错误比它解决的更多，系统自动回滚到修复前的状态——仿佛这次修复从未发生。

**魔法在于：失败必须是无痛的。**

## 五分钟摘要

第九章的反馈回路解决了"如何驱动AI修复"的问题。但它有一个根本性缺陷：**修复可能引入新错误**。一个修复可能解决了一个type error，却引入了一个logic error。反馈回路不知道如何比较"修复前"和"修复后"的总错误量。

TNR（Transactional Non-Regression，事务性无回归）解决的是这个问题。TNR的保证是：**如果修复失败，系统状态必须等价于修复前的状态**。这意味着：

1. 修复前对系统状态做快照
2. AI执行修复
3. 验证修复是否真正改善了系统（不只是解决了编译器错误，还引入了运行时错误）
4. 如果验证失败，回滚到快照

TNR的理论基础是软件事务内存（STM）。STM是并发编程中的一个概念——多个线程可以安全地并发修改共享内存，因为每个事务要么完全成功，要么完全失败。本章展示如何在AI修复场景中借用STM的思想实现TNR。

---

## Step 1: TNR形式化定义 — Precondition × Postcondition × Invariant

### TNR的三元组

TNR保证可以用经典的霍尔逻辑（Hoare Logic）描述：

```
{Precondition} 修复操作 {Postcondition × Invariant}
```

| 组件 | 含义 | AI修复场景 |
|------|------|-----------|
| **Precondition** | 执行修复前必须满足的条件 | 编译通过或已知错误列表 |
| **Postcondition** | 修复成功后必须满足的条件 | 新增错误数为0，原错误被解决 |
| **Invariant** | 修复前后都必须保持不变的条件 | 系统核心功能未被破坏 |

### 形式化定义

```typescript
// tnr-types.ts — TNR形式化定义

/**
 * TNR事务状态
 */
interface TNRState<S> {
    /** 快照的系统状态 */
    snapshot: S;

    /** 事务是否已提交 */
    committed: boolean;

    /** 事务是否已回滚 */
    rolledBack: boolean;

    /** 修复尝试的次数 */
    attempts: number;
}

/**
 * TNR前置条件
 * 修复执行前必须满足的条件
 */
interface TNRPrecondition<S> {
    /**
     * 检查系统状态是否满足修复前提
     * @returns true if the system is in a state where the fix can be attempted
     */
    check(state: S): boolean;

    /** 前提条件的描述 */
    description: string;
}

/**
 * TNR后置条件
 * 修复成功后必须满足的条件
 */
interface TNRPostcondition<S> {
    /**
     * 检查修复是否真正成功
     * @param before 修复前的状态
     * @param after 修复后的状态
     * @returns true if the fix genuinely improved the system
     */
    check(before: S, after: S): boolean;

    /** 后置条件的描述 */
    description: string;
}

/**
 * TNR不变量
 * 修复前后都必须保持不变的条件
 */
interface TNRInvariant<S> {
    /**
     * 检查系统状态是否满足不变量
     * @param state 系统状态
     * @returns true if the invariant holds
     */
    check(state: S): boolean;

    /** 不变量的描述 */
    description: string;
}

/**
 * TNR验证结果
 */
interface TNRValidationResult<S> {
    /** 验证是否通过 */
    passed: boolean;

    /** 修复前状态 */
    beforeState: S;

    /** 修复后状态 */
    afterState: S;

    /** 错误比较：新增了多少错误 */
    newErrorsIntroduced: number;

    /** 错误比较：解决了多少错误 */
    errorsFixed: number;

    /** 净改善量 */
    netImprovement: number;

    /** 失败原因（如果验证失败） */
    failureReason?: string;
}

/**
 * TNR事务
 * 一个修复尝试的完整生命周期
 */
class TNRTransaction<S> {
    private state: TNRState<S>;
    private preconditions: TNRPrecondition<S>[];
    private postconditions: TNRPostcondition<S>[];
    private invariants: TNRInvariant<S>[];

    constructor(
        initialState: S,
        preconditions: TNRPrecondition<S>[] = [],
        postconditions: TNRPostcondition<S>[] = [],
        invariants: TNRInvariant<S>[] = []
    ) {
        this.state = {
            snapshot: initialState,
            committed: false,
            rolledBack: false,
            attempts: 0,
        };
        this.preconditions = preconditions;
        this.postconditions = postconditions;
        this.invariants = invariants;
    }

    /**
     * 检查前置条件
     */
    canAttemptFix(currentState: S): boolean {
        return this.preconditions.every(p => p.check(currentState));
    }

    /**
     * 检查不变量（修复前后都要满足）
     */
    checkInvariants(state: S): { ok: boolean; violations: string[] } {
        const violations: string[] = [];
        for (const inv of this.invariants) {
            if (!inv.check(state)) {
                violations.push(inv.description);
            }
        }
        return { ok: violations.length === 0, violations };
    }

    /**
     * 验证修复结果
     */
    validateFix(before: S, after: S): TNRValidationResult<S> {
        // 首先检查所有后置条件
        const postChecks = this.postconditions.map(p => ({
            condition: p,
            passed: p.check(before, after),
        }));

        const allPostPassed = postChecks.every(r => r.passed);

        // 计算错误变化
        const newErrorsIntroduced = this.countNewErrors(before, after);
        const errorsFixed = this.countErrorsFixed(before, after);
        const netImprovement = errorsFixed - newErrorsIntroduced;

        if (!allPostPassed || netImprovement <= 0) {
            return {
                passed: false,
                beforeState: before,
                afterState: after,
                newErrorsIntroduced,
                errorsFixed,
                netImprovement,
                failureReason: !allPostPassed
                    ? `Postconditions failed: ${postChecks.filter(r => !r.passed).map(r => r.condition.description).join(', ')}`
                    : `Net improvement not positive: ${netImprovement}`,
            };
        }

        return {
            passed: true,
            beforeState: before,
            afterState: after,
            newErrorsIntroduced,
            errorsFixed,
            netImprovement,
        };
    }

    /**
     * 回滚到快照状态
     */
    rollback(): S {
        if (this.state.rolledBack) {
            throw new Error('Transaction already rolled back');
        }
        this.state.rolledBack = true;
        return this.state.snapshot;
    }

    /**
     * 提交事务
     */
    commit(newState: S): void {
        if (this.state.rolledBack) {
            throw new Error('Cannot commit a rolled-back transaction');
        }
        this.state.snapshot = newState;
        this.state.committed = true;
    }

    /**
     * 获取当前快照
     */
    getSnapshot(): S {
        return this.state.snapshot;
    }

    private countNewErrors(before: S, after: S): number {
        // 子类实现
        return 0;
    }

    private countErrorsFixed(before: S, after: S): number {
        // 子类实现
        return 0;
    }
}
```

### TNR的正确性证明思路

TNR的正确性建立在三个不变量上：

1. **快照一致性**：快照状态必须与实际系统状态一致
2. **验证充分性**：后置条件必须能检测到所有类型的退化
3. **回滚完整性**：回滚操作必须完全恢复快照状态

```
定理：TNR保证系统状态不恶化

证明：
设 S_before 为修复前系统状态，S_after 为修复后系统状态，S_snapshot 为快照状态

1. 如果修复成功（postcondition满足）:
   - S_after 满足所有postcondition
   - S_after 满足所有invariant
   - net_improvement > 0
   - 提交: S_snapshot' = S_after
   - 系统状态改善

2. 如果修复失败（postcondition不满足）:
   - 回滚: S_current = S_snapshot
   - S_current = S_before（快照一致性）
   - 系统状态恢复到修复前

3. 无论哪种情况:
   - S_current ≠ 任意比 S_before 更差的状态
   - 即：系统状态不恶化

QED
```

---

## Step 2: 编译器层TNR实现 — 编译单元原子性回滚

### 编译单元事务边界

编译器层的TNR实现需要解决一个关键问题：**编译单元的原子性**。当AI修复一个类型错误时，修复可能影响多个文件。我们需要确保：

1. 这些文件的修改是原子的——要么全部成功，要么全部回滚
2. 编译器检查是验证手段——通过编译器检查不等于修复成功
3. 运行时验证是最终裁判——编译器通过但运行时崩溃，必须回滚

```typescript
// compiler-tnr-transaction.ts — 编译器层TNR实现

import { promises as fs } from 'fs';
import path from 'path';

/**
 * 编译单元快照
 * 记录修复前每个文件的状态
 */
interface CompilationUnitSnapshot {
    /** 文件路径 → 文件内容 */
    files: Map<string, string>;

    /** 快照时间戳 */
    timestamp: number;

    /** 快照ID */
    id: string;
}

/**
 * 编译检查结果
 */
interface CompilationResult {
    /** 是否通过编译 */
    passed: boolean;

    /** 错误列表 */
    errors: CompilerError[];

    /** 警告列表 */
    warnings: CompilerWarning[];

    /** 编译输出 */
    output: string;
}

/**
 * 编译器错误
 */
interface CompilerError {
    code: string;
    message: string;
    file: string;
    line: number;
    column: number;
    severity: 'error' | 'warning';
}

/**
 * 编译器警告
 */
interface CompilerWarning {
    code: string;
    message: string;
    file: string;
    line: number;
    severity: 'warning';
}

/**
 * 修复验证结果
 */
interface FixVerification {
    /** 编译器检查是否通过 */
    compilerPass: boolean;

    /** 运行时测试是否通过 */
    runtimePass: boolean;

    /** 新增的运行时错误（如果有） */
    newRuntimeErrors: string[];

    /** 净改善量 */
    netImprovement: number;
}

/**
 * 编译单元TNR事务
 * 包装一个编译单元的修复尝试
 */
export class CompilationUnitTransaction {
    private snapshot: CompilationUnitSnapshot;
    private workingDir: string;
    private modifiedFiles: Set<string> = new Set();
    private originalContents: Map<string, string> = new Map();
    /** 快照时的错误数量，用于verifyFix计算净改善量 */
    private preSnapshotErrors: number = 0;

    constructor(workingDir: string) {
        this.workingDir = workingDir;
        this.snapshot = this.createEmptySnapshot();
    }

    /**
     * 创建空快照
     */
    private createEmptySnapshot(): CompilationUnitSnapshot {
        return {
            files: new Map(),
            timestamp: Date.now(),
            id: `snap-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        };
    }

    /**
     * 快照当前编译单元状态
     * @param filePaths 要快照的文件路径列表
     */
    async snapshotFiles(filePaths: string[]): Promise<void> {
        const files = new Map<string, string>();

        for (const filePath of filePaths) {
            try {
                const fullPath = path.resolve(this.workingDir, filePath);
                const content = await fs.readFile(fullPath, 'utf-8');
                files.set(filePath, content);
            } catch (e) {
                // 文件不存在，跳过
                if ((e as NodeJS.ErrnoException).code !== 'ENOENT') {
                    throw e;
                }
            }
        }

        this.snapshot = {
            files,
            timestamp: Date.now(),
            id: `snap-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        };
    }

    /**
     * 记录文件修改（用于回滚跟踪）
     */
    async recordFileChange(filePath: string, newContent: string): Promise<void> {
        const fullPath = path.resolve(this.workingDir, filePath);

        // 如果还没有记录原始内容，现在记录
        if (!this.originalContents.has(filePath) && this.snapshot.files.has(filePath)) {
            this.originalContents.set(filePath, this.snapshot.files.get(filePath)!);
        } else if (!this.originalContents.has(filePath)) {
            try {
                this.originalContents.set(filePath, await fs.readFile(fullPath, 'utf-8'));
            } catch (e) {
                if ((e as NodeJS.ErrnoException).code !== 'ENOENT') {
                    throw e;
                }
            }
        }

        this.modifiedFiles.add(filePath);

        // 写入新内容
        await fs.mkdir(path.dirname(fullPath), { recursive: true });
        await fs.writeFile(fullPath, newContent, 'utf-8');
    }

    /**
     * 验证修复结果
     * @param preFixErrors 修复前的错误数量
     * @param compilerCheck 编译器检查函数
     * @param runtimeCheck 运行时检查函数（可选）
     */
    async verifyFix(
        preFixErrors: number,
        compilerCheck: () => Promise<CompilationResult>,
        runtimeCheck?: () => Promise<{ passed: boolean; errors: string[] }>
    ): Promise<FixVerification> {
        // 第一层：编译器检查
        const compilerResult = await compilerCheck();
        const compilerPass = compilerResult.passed;

        // 第二层：运行时检查（可选）
        let runtimePass = true;
        let newRuntimeErrors: string[] = [];

        if (runtimeCheck && compilerPass) {
            try {
                const runtimeResult = await runtimeCheck();
                runtimePass = runtimeResult.passed;
                newRuntimeErrors = runtimeResult.errors;
            } catch (e) {
                // 运行时检查失败视为修复失败
                runtimePass = false;
                newRuntimeErrors = [(e as Error).message];
            }
        }

        // 计算净改善量：修复前错误数 - 修复后错误数
        // 正数表示改善（错误减少），负数表示恶化（错误增加）
        const postFixErrors = compilerResult.errors.filter(e => e.severity === 'error').length;
        const netImprovement = preFixErrors - postFixErrors;

        return {
            compilerPass,
            runtimePass,
            newRuntimeErrors,
            netImprovement,
        };
    }

    /**
     * 回滚所有修改
     */
    async rollback(): Promise<void> {
        for (const filePath of this.modifiedFiles) {
            const fullPath = path.resolve(this.workingDir, filePath);
            const originalContent = this.originalContents.get(filePath);

            if (originalContent !== undefined) {
                // 恢复到原始内容
                await fs.writeFile(fullPath, originalContent, 'utf-8');
            } else if (this.snapshot.files.has(filePath)) {
                // 快照中有原始内容，恢复到快照版本
                await fs.writeFile(fullPath, this.snapshot.files.get(filePath)!, 'utf-8');
            } else {
                // 文件在修改中被删除，恢复它
                if (this.snapshot.files.has(filePath)) {
                    await fs.mkdir(path.dirname(fullPath), { recursive: true });
                    await fs.writeFile(fullPath, this.snapshot.files.get(filePath)!, 'utf-8');
                }
            }
        }

        this.modifiedFiles.clear();
        this.originalContents.clear();
    }

    /**
     * 提交修复（清除回滚记录）
     */
    async commit(): Promise<void> {
        // 提交后不再需要回滚记录
        this.originalContents.clear();
        this.modifiedFiles.clear();

        // 更新快照为当前状态
        await this.refreshSnapshot();
    }

    /**
     * 刷新快照为当前状态
     */
    private async refreshSnapshot(): Promise<void> {
        const filePaths = Array.from(this.snapshot.files.keys());
        await this.snapshotFiles(filePaths);
    }

    /**
     * 获取快照
     */
    getSnapshot(): CompilationUnitSnapshot {
        return this.snapshot;
    }

    /**
     * 检查是否已修改
     */
    isModified(): boolean {
        return this.modifiedFiles.size > 0;
    }
}

/**
 * TNR修复循环
 * 完整的修复-验证-回滚循环
 */
export class TNRFixLoop {
    private transaction: CompilationUnitTransaction;
    private maxAttempts: number;
    private compilerCheckFn: () => Promise<CompilationResult>;
    private runtimeCheckFn?: () => Promise<{ passed: boolean; errors: string[] }>;

    constructor(
        workingDir: string,
        compilerCheck: () => Promise<CompilationResult>,
        runtimeCheck?: () => Promise<{ passed: boolean; errors: string[] }>,
        maxAttempts: number = 3
    ) {
        this.transaction = new CompilationUnitTransaction(workingDir);
        this.compilerCheckFn = compilerCheck;
        this.runtimeCheckFn = runtimeCheck;
        this.maxAttempts = maxAttempts;
    }

    /**
     * 执行TNR修复循环
     * @param filesToSnapshot 需要快照的文件列表
     * @param fixFn 修复函数，接收当前系统状态，返回修复后的文件修改
     */
    async executeFix(
        filesToSnapshot: string[],
        fixFn: (state: CompilationUnitSnapshot) => Promise<Map<string, string>>
    ): Promise<{ success: boolean; attempts: number }> {
        // Step 1: 快照
        await this.transaction.snapshotFiles(filesToSnapshot);

        // Step 1b: 捕获快照时的错误数量（用于计算净改善量）
        const preFixResult = await this.compilerCheckFn();
        const preFixErrors = preFixResult.errors.filter(e => e.severity === 'error').length;

        let attempts = 0;

        while (attempts < this.maxAttempts) {
            attempts++;

            try {
                // Step 2: 应用修复
                const modifications = await fixFn(this.transaction.getSnapshot());

                for (const [filePath, content] of modifications) {
                    await this.transaction.recordFileChange(filePath, content);
                }

                // Step 3: 验证（传入修复前的错误数）
                const verification = await this.transaction.verifyFix(
                    preFixErrors,
                    this.compilerCheckFn,
                    this.runtimeCheckFn
                );

                // Step 4: 判断
                if (verification.compilerPass && verification.runtimePass) {
                    // 修复成功，提交
                    await this.transaction.commit();
                    return { success: true, attempts };
                } else {
                    // 修复失败，回滚
                    await this.transaction.rollback();

                    // 如果是最后一轮，不再重试
                    if (attempts >= this.maxAttempts) {
                        return { success: false, attempts };
                    }
                }
            } catch (e) {
                // 修复过程出错，回滚
                await this.transaction.rollback();

                if (attempts >= this.maxAttempts) {
                    return { success: false, attempts };
                }
            }
        }

        return { success: false, attempts };
    }

    /**
     * 获取当前事务实例
     */
    getTransaction(): CompilationUnitTransaction {
        return this.transaction;
    }
}
```

### 编译器检查作为第一层验证

编译器检查是第一层验证，但它不是充分的。考虑这个场景：

```typescript
// AI修复前
function divide(a: number, b: number): number {
    return a / b;  // TypeScript: OK, 运行时: 如果 b=0 会出错
}

// AI修复后（错误地）
function divide(a: number, b: number): number {
    if (b === 0) {
        return 0;  // 编译器: OK, 但语义错误：0不是数学上正确的答案
    }
    return a / b;
}
```

编译器通过了，但AI的修复引入了语义错误。这就需要运行时验证作为第二层。

---

## Step 3: TNR ↔ STM — 软件事务内存理论关联

### STM基础回顾

软件事务内存（Software Transactional Memory，STM）起源于并发编程。传统的并发控制使用锁（locks），但锁有以下问题：

1. **死锁**：多个线程互相等待对方释放锁
2. **活锁**：多个线程不断尝试获取锁但都无法成功
3. **复杂性**：锁的层次和顺序难以管理
4. **性能**：锁竞争导致串行化

STM的解决方案是**乐观并发控制**：

```
事务执行：
1. 读取共享内存（记录到本地事务缓冲区）
2. 执行计算
3. 尝试写入（验证是否有冲突）
4. 如果验证通过，写入生效
5. 如果验证失败，整个事务回滚，重试
```

### TNR与STM的对应关系

| STM概念 | TNR概念 | 对应关系 |
|--------|---------|---------|
| 共享内存 | 系统状态 | 被修复的代码/配置 |
| 线程 | AI修复尝试 | 一次修复操作 |
| 事务 | TNR事务 | 一次完整的修复-验证-回滚循环 |
| 读集（Read Set） | 修复前快照 | 修复前的系统状态 |
| 写集（Write Set） | 修复后变更 | AI生成的修复代码 |
| 验证（Validate） | 后置条件检查 | 检查修复是否真正改善 |
| 回滚（Rollback） | 回滚到快照 | 修复失败时恢复原状 |
| 重试（Retry） | 重新修复 | 再次尝试修复 |

### TNR的STM语义

```typescript
// tnr-stm-equivalence.ts — TNR与STM的语义对比

/**
 * STM事务接口
 */
interface STMTransaction<T> {
    read(key: string): T;
    write(key: string, value: T): void;
    validate(): boolean;
    commit(): void;
    rollback(): void;
}

/**
 * TNR事务接口（对应STM）
 */
interface TNRTransaction<S> {
    // 等价于STM的read
    snapshot(): S;

    // 等价于STM的write
    applyFix(fix: Fix): void;

    // 等价于STM的validate
    verify(): TNRVerificationResult;

    // 等价于STM的commit
    commit(): void;

    // 等价于STM的rollback
    rollback(): S;
}

/**
 * STM的核心性质：AITO
 * Atomicity（原子性）、Isolation（隔离性）、TNR也满足
 * Consistency（一致性）、Durability（持久性）—— TNR不保证，需要外部存储
 */
class STMTransaction<T> {
    private readSet: Map<string, T> = new Map();
    private writeSet: Map<string, T> = new Map();
    private sharedState: Map<string, T>;

    constructor(sharedState: Map<string, T>) {
        this.sharedState = sharedState;
    }

    read(key: string): T {
        if (this.writeSet.has(key)) {
            return this.writeSet.get(key)!;
        }
        if (this.readSet.has(key)) {
            return this.readSet.get(key)!;
        }
        const value = this.sharedState.get(key)!;
        this.readSet.set(key, value);
        return value;
    }

    write(key: string, value: T): void {
        this.writeSet.set(key, value);
    }

    validate(): boolean {
        // 验证读集中的所有值仍然与共享状态一致
        for (const [key, readValue] of this.readSet) {
            if (this.sharedState.get(key) !== readValue) {
                return false; // 发生了冲突
            }
        }
        return true;
    }

    commit(): void {
        if (!this.validate()) {
            throw new Error('Transaction validation failed');
        }
        // 原子性地应用所有写操作
        for (const [key, value] of this.writeSet) {
            this.sharedState.set(key, value);
        }
        this.readSet.clear();
        this.writeSet.clear();
    }

    rollback(): void {
        this.readSet.clear();
        this.writeSet.clear();
        // 没有修改共享状态
    }
}

/**
 * TNR的完整性保证
 *
 * STM保证：事务要么完全成功，要么完全不留痕迹地失败
 * TNR保证：修复要么完全成功（系统改善），要么完全不留痕迹地失败（恢复到修复前）
 *
 * 关键区别：
 * - STM通常有重试机制（optimistic的乐观锁）
 * - TNR也有重试机制，但每次重试前会先分析上次失败的原因
 */
class TNRTransaction<S> {
    private state: S;
    private fix: Fix | null = null;
    private verified: boolean = false;

    constructor(initialState: S) {
        this.state = initialState;
    }

    /**
     * 快照 = STM的read
     */
    snapshot(): S {
        return this.state;
    }

    /**
     * 应用修复 = STM的write
     */
    applyFix(fix: Fix): void {
        this.fix = fix;
        this.verified = false;
    }

    /**
     * 验证 = STM的validate
     */
    verify(): TNRVerificationResult {
        if (!this.fix) {
            return { valid: false, reason: 'No fix applied' };
        }

        const result = this.fix.verify(this.state);
        this.verified = result.valid;
        return result;
    }

    /**
     * 提交 = STM的commit
     */
    commit(newState: S): void {
        if (!this.verified) {
            throw new Error('Cannot commit unverified fix');
        }
        this.state = newState;
        this.fix = null;
    }

    /**
     * 回滚 = STM的rollback
     */
    rollback(): S {
        this.fix = null;
        this.verified = false;
        return this.state; // 返回原始状态
    }
}
```

### 为什么TNR需要STM的思想

传统的事务概念（数据库）假设：
1. **状态是持久化的**——事务提交后数据不会丢失
2. **操作是确定性的**——同样的输入总是产生同样的输出
3. **冲突是可以检测的**——并发事务会互相冲突

AI修复场景下：
1. **状态是临时的**——AI修复在内存中进行，需要主动保存快照
2. **操作是概率性的**——同样的错误提示，AI可能生成不同的修复
3. **冲突是语义级的**——编译器通过不代表运行时正确

因此，TNR借鉴了STM的**乐观并发控制**思想：先尝试，验证失败就回滚，而不是预先加锁。这比悲观的事务模型更适合AI修复的不确定性。

---

## Step 4: 魔法时刻段落 — 等价于"从未尝试修复"

### 魔法时刻

**TNR的魔法时刻只有一瞬间的领悟：失败必须是无痛的。**

当你用Git提交代码，CI跑了一晚上，测试发现这个commit引入了一个微妙的竞态条件。你执行`git revert`，CI的红色变成绿色，代码库里仿佛这个commit从未存在。这就是TNR要实现的感觉。

但Git revert是有局限的——它只能撤销已经被提交到仓库的变更。在AI修复的场景里，变更还没有进入仓库，甚至可能只存在于内存中。更糟糕的是，AI的修复可能跨越多个文件，每个文件的修改都需要协调回滚。

**TNR要解决的核心问题是：如果AI修复引入的新错误比它解决的更多，怎么办？**

答案是：**回滚，而不是修补。**

想象一个具体的场景：

```
修复前系统状态：
  - 编译器错误: 3个（type error × 2, import error × 1）
  - 运行时错误: 0个

AI修复尝试：
  - 修复了 type error × 2
  - 引入了新的 runtime error × 1（空指针解引用）

修复后系统状态：
  - 编译器错误: 1个（import error）
  - 运行时错误: 1个（新增）
```

如果用传统的方法，我们会说"修复成功了——编译器错误从3个减少到1个"。但这是错误的判断。真正的系统健康度没有提升——我们只是把一个错误换成了另一个错误。

**TNR的定义是：净改善量必须 > 0。**

```
净改善量 = 解决的错误数 - 新增的错误数

TNR成功条件：净改善量 > 0
TNR失败条件：净改善量 ≤ 0
```

在这个例子里：
```
净改善量 = 2 - 1 = 1 > 0
```

等等，这似乎满足TNR成功条件。但我们还有另一层检查：**运行时错误比编译器错误更严重**。运行时崩溃意味着用户直接受影响，编译器错误只是开发阶段的问题。

所以更精确的TNR定义应该是：

```
TNR成功条件：
  1. 净改善量 > 0
  2. 没有引入新的运行时错误
  3. 所有不变量仍然满足
```

在这个场景里，条件2失败了——我们引入了运行时错误。所以TNR会判定为失败，回滚到修复前的状态。

**这就是"等价于从未尝试修复"的真正含义。**

回滚后，系统状态完全恢复到修复前：编译器错误仍然是3个，运行时错误仍然是0个。仿佛这次修复从未发生。

唯一不同的是：AI获得了这次失败的记录，下次修复会避开这个方向。

---

## Step 5: 桥接语

- **承上：** 第九章建立了完整的反馈回路——编译器报错 → AI分析 → AI修复 → 编译器重新校验。但反馈回路有一个盲点：如果修复引入的新错误比它解决的更多，系统会悄悄恶化。TNR填补了这个盲点。

- **启下：** TNR在编译器层实现了原子性回滚。但这只是故事的一半——如果AI的修复不仅破坏了编译正确性，还破坏了运行时行为（比如死循环、资源泄露、甚至安全漏洞），编译器层的回滚就不够用了。下一章将回答：如何将TNR从编译器层扩展到运行时层？

- **认知缺口：** 编译器层的TNR依赖于编译器的确定性——给定相同的输入，编译器总是产生相同的输出。但AI模型的输出不是确定性的。同样的错误提示，两次调用可能产生不同的修复代码。这意味着TNR在编译器层是完备的，但在AI生成层是概率的。如何将概率的AI生成纳入确定性的TNR框架？这是ch11要探索的核心问题。

---

## 本章来源

### 一手来源

| 来源 | URL | 关键数据 |
|------|-----|---------|
| "Self-Healing Software Systems: Lessons from Nature, Powered by AI" (arXiv:2504.20093) | https://arxiv.org/2504.20093 | 自愈系统的三组件框架：Sensory Inputs、Cognitive Core、Healing Agents；为TNR提供理论基础 |
| "Agentic Testing: Multi-Agent Systems for Software Quality" (arXiv:2601.02454) | https://arxiv.org/2601.02454 | 三Agent闭环系统的验证框架，与TNR的验证机制高度相关 |
| "The Kitchen Loop: User-Spec-Driven Self-Evolving Codebase" (arXiv:2603.25697) | https://arxiv.org/2603.25697 | 1094+ merged PRs，零回归——TNR保证的实际效果证明 |

### 二手来源

| 来源 | 用途 |
|------|------|
| research-findings.md (Section 3.3) | 自愈系统三组件框架，为TNR提供概念基础 |
| research-findings.md (Section 3.1) | llvm-autofix研究，编译器层TNR的实践案例 |
| ch09-feedback-loop.md | 反馈回路架构，TNR的上下文 |

### 理论来源

| 来源 | 用途 |
|------|------|
| 软件事务内存（STM）理论 | TNR的形式化框架，AITO特性的理论来源 |
| 霍尔逻辑（Hoare Logic） | Precondition × Postcondition × Invariant的形式化表示 |
