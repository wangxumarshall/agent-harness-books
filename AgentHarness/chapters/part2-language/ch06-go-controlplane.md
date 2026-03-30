# 第二部分：语言层契约 — Go控制平面与高并发网关

## 本章Q

为什么Go适合控制平面而非Agent逻辑？

## 魔法时刻

Go的Goroutine不是为AI设计的，但是为AI的控制平面而生的。1995年Rob Pike在贝尔实验室设计Go时，绝不会想到20年后会有人用它调度数万个AI Agent。他设计Goroutine只是为了解决C++ threading的重量级问题——数万个线程的上下文切换成本。但正是这个设计，让Go成为了AI控制平面的完美语言：当一个Goroutine需要等待HTTP响应时，它不阻塞OS线程，它只是让出时间片给其他Goroutine继续执行。这意味着你可以在单台机器上用几千个Goroutine同时维持与AI模型的长连接，而每个连接只占用几KB内存。不是AI需要Go，而是Go刚好解决了AI控制平面的核心矛盾——大量长连接与有限资源的冲突。

## 五分钟摘要

第五章展示了Rust类型状态模式如何让状态机的非法跃迁变成编译期错误。但类型状态解决的是单Agent的静态约束——它无法解决多Agent系统的动态问题：数千个Agent同时运行、请求的负载均衡、优雅的取消传播、跨服务边界的超时控制。这些是编排层的问题，不是核心层的问题。Go的设计哲学恰好为此而生：Goroutine处理高并发、Channel处理通信、Context处理取消和超时。Stripe Minions用Go构建了每周处理1300+ PR的控制平面，证明了Go在高并发场景的工程可行性。本章用三个完整代码示例回答"Go如何在控制平面层编排大量Agent"：Goroutine池实现Agent路由、长连接队列实现请求缓冲、Context传播实现优雅取消。

---

## Go的生态位：控制平面而非Agent核心

### 为什么不是Go写Agent逻辑

Rust和Go的选择不是性能对比，而是职责边界的划分。

Rust的所有权模型和类型状态模式，让Agent的核心逻辑——状态机跃迁、工具调用、prompt构建——在编译时就被严格约束。这些约束需要精确的类型系统和编译期计算，Go无法提供。

但Go的三个设计恰好满足控制平面的核心需求：

**1. Goroutine：轻量级并发，适合大量Agent调度**

一个Goroutine的初始栈大小是2KB，而一个OS线程是1MB。创建10万个Goroutine只需要200MB内存，而创建1万个OS线程需要10GB。这意味着你可以在单台机器上同时调度数万个AI Agent的请求。

**2. Context传播：优雅的取消和超时**

Go的`context.Context`是控制平面不可或缺的设计。它可以从调用栈顶层传播到底层，中途绑定超时和取消信号。当上游请求取消时，所有下游的Goroutine都会收到信号，不需要手动遍历关闭。

**3. 标准库：HTTP/JSON/gRPC开箱即用**

Go的标准库包含了控制平面需要的所有基础能力：net/http提供HTTP服务端、encoding/json提供高性能JSON解析、google.golang.org/grpc提供多语言通信。这减少了外部依赖，降低了运维复杂度。

### GRT栈中的Go生态位

| 层级 | 语言 | 职责 | 核心能力 |
|------|------|------|---------|
| TypeScript | 应用层 | 用户界面、API适配 | Zod验证、Mastra工作流 |
| Rust | 核心层 | Agent逻辑、工具执行 | 所有权、类型状态、WASM |
| **Go** | **控制层** | **Agent路由、负载均衡、限流** | **Goroutine、Context、Channel** |

---

## 代码1：Goroutine池与Agent路由

### 核心架构

```
                    ┌─────────────────────────────────────────────┐
                    │           AgentGateway (Go Control Plane)   │
                    │                                             │
  HTTP Request ───►  │  ┌─────────┐    ┌─────────────────────┐   │
                    │  │ Router  │───►│  Goroutine Pool      │   │
                    │  └─────────┘    │  ┌───┬───┬───┬───┐  │   │
                    │                 │  │ G │ G │ G │ G │  │   │
                    │                 │  └───┴───┴───┴───┘  │   │
                    │                 │   Agent A   Agent B  │   │
                    │                 └─────────────────────┘   │
                    └─────────────────────────────────────────────┘
```

### 完整代码实现

```go
// ============================================================
// AgentGateway: 高并发Agent路由网关
// 来源：基于Stripe Minions架构实践
// ============================================================

package gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"sync/atomic"
	"time"

	"github.com/google/uuid"
)

// ============================================================
// Part 1: Agent请求与响应结构
// ============================================================

// AgentRequest 代表转发给Agent处理的请求
type AgentRequest struct {
	RequestID    string                 `json:"request_id"`
	AgentID      string                 `json:"agent_id"`
	Prompt       string                 `json:"prompt"`
	Tools        []ToolDefinition       `json:"tools,omitempty"`
	MaxRetries   int                    `json:"max_retries"`
	Timeout      time.Duration          `json:"timeout"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}

// ToolDefinition 定义Agent可用的工具
type ToolDefinition struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema json.RawMessage `json:"input_schema"`
}

// AgentResponse 代表Agent的响应
type AgentResponse struct {
	RequestID   string      `json:"request_id"`
	AgentID     string      `json:"agent_id"`
	Output      string      `json:"output"`
	Error       string      `json:"error,omitempty"`
	DurationMs  int64       `json:"duration_ms"`
	RetryCount  int         `json:"retry_count"`
	CompletedAt time.Time   `json:"completed_at"`
}

// ============================================================
// Part 2: Goroutine Pool —— Agent执行器池
// ============================================================

// AgentExecutor 代表一个Agent执行单元
type AgentExecutor struct {
	id         int
	agentID    string
	busy       atomic.Bool
	currentReq atomic.Value // 存储当前请求的RequestID
}

// WorkerPool 管理工作中的Goroutine池
type WorkerPool struct {
	workers    []*AgentExecutor
	register   chan *AgentExecutor
	jobQueue   chan *AgentRequest
	resultChan chan *AgentResponse
	done       chan struct{}

	// 指标
	activeWorkers atomic.Int64
	totalJobs     atomic.Int64
	queuedJobs    atomic.Int64

	// 配置
	poolSize     int
	maxQueueLen  int
	agentFactory func(id int) *AgentExecutor
}

// NewWorkerPool 创建一个新的Goroutine池
func NewWorkerPool(poolSize, maxQueueLen int) *WorkerPool {
	wp := &WorkerPool{
		workers:    make([]*AgentExecutor, poolSize),
		register:   make(chan *AgentExecutor, poolSize),
		jobQueue:  make(chan *AgentRequest, maxQueueLen),
		resultChan: make(chan *AgentResponse, maxQueueLen),
		done:       make(chan struct{}),
		poolSize:   poolSize,
		maxQueueLen: maxQueueLen,
	}

	// 创建worker
	for i := 0; i < poolSize; i++ {
		executor := &AgentExecutor{
			id:      i,
			agentID: fmt.Sprintf("agent-%d", i),
		}
		wp.workers[i] = executor
	}

	return wp
}

// Start 启动所有Goroutine worker
func (wp *WorkerPool) Start(ctx context.Context) {
	// 启动固定数量的worker
	for i := 0; i < wp.poolSize; i++ {
		go wp.worker(ctx, wp.workers[i])
	}

	// 启动调度器
	go wp.scheduler()
}

// worker 是单个Goroutine执行单元
func (wp *WorkerPool) worker(ctx context.Context, executor *AgentExecutor) {
	for {
		select {
		case <-ctx.Done():
			log.Printf("Worker %d shutting down", executor.id)
			return
		case req, ok := <-wp.jobQueue:
			if !ok {
				return
			}
			executor.busy.Store(true)
			executor.currentReq.Store(req.RequestID)
			wp.activeWorkers.Add(1)

			// 执行Agent请求
			response := wp.executeAgent(ctx, req, executor)

			// 发送结果
			select {
			case wp.resultChan <- response:
			case <-ctx.Done():
				wp.activeWorkers.Add(-1)
				return
			}

			executor.busy.Store(false)
			executor.currentReq.Store("")
			wp.activeWorkers.Add(-1)
		}
	}
}

// scheduler 调度器：worker直接从jobQueue自取任务
// 这是一个work-stealing模式，worker自我调度
// 调度器作为未来负载均衡策略的钩子点
// （例如：基于agent亲和性分配任务到特定worker）
func (wp *WorkerPool) scheduler() {
	for {
		select {
		case <-wp.done:
			return
		case req := <-wp.jobQueue:
			// 任务提交到jobQueue；worker自行获取
			// 此函数是未来负载均衡逻辑的占位符
			_ = req // worker直接从jobQueue获取（见worker()）
		}
	}
}

// executeAgent 执行单个Agent请求
func (wp *WorkerPool) executeAgent(ctx context.Context, req *AgentRequest, executor *AgentExecutor) *AgentResponse {
	start := time.Now()

	// 创建带超时的context
	reqCtx, cancel := context.WithTimeout(ctx, req.Timeout)
	defer cancel()

	// 这里是调用实际Agent的逻辑
	// 在真实实现中，这里会调用Rust核心或外部AI服务
	output, err := wp.callAgentCore(reqCtx, req)

	completedAt := time.Now()
	durationMs := completedAt.Sub(start).Milliseconds()

	response := &AgentResponse{
		RequestID:   req.RequestID,
		AgentID:     executor.agentID,
		DurationMs:  durationMs,
		RetryCount:  0,
		CompletedAt: completedAt,
	}

	if err != nil {
		response.Error = err.Error()
	} else {
		response.Output = output
	}

	return response
}

// callAgentCore 调用Agent核心逻辑（Placeholder）
func (wp *WorkerPool) callAgentCore(ctx context.Context, req *AgentRequest) (string, error) {
	// 模拟AI处理
	select {
	case <-time.After(100 * time.Millisecond):
		return fmt.Sprintf("Processed by %s: %s", req.AgentID, req.Prompt), nil
	case <-ctx.Done():
		return "", ctx.Err()
	}
}

// Submit 提交一个Agent请求
func (wp *WorkerPool) Submit(req *AgentRequest) error {
	select {
	case wp.jobQueue <- req:
		wp.totalJobs.Add(1)
		return nil
	default:
		return fmt.Errorf("job queue full (len=%d)", wp.maxQueueLen)
	}
}

// ResultChan 返回结果通道
func (wp *WorkerPool) ResultChan() <-chan *AgentResponse {
	return wp.resultChan
}

// Stats 返回当前池的统计信息
func (wp *WorkerPool) Stats() map[string]int64 {
	return map[string]int64{
		"active_workers": wp.activeWorkers.Load(),
		"total_jobs":     wp.totalJobs.Load(),
		"queued_jobs":    wp.queuedJobs.Load(),
		"pool_size":      int64(wp.poolSize),
	}
}
```

---

## 代码2：API Gateway与限流模式

### 核心架构

```
                    ┌─────────────────────────────────────────────┐
                    │              API Gateway                    │
                    │                                             │
  HTTP Request ───► │  ┌─────────┐  ┌─────────┐  ┌──────────┐   │
                    │  │ RateLimiter │ │  Router  │ │ LoadBalancer│ │
                    │  └─────────┘  └─────────┘  └──────────┘   │
                    │       │            │             │         │
                    │       ▼            ▼             ▼         │
                    │  ┌─────────────────────────────────────┐   │
                    │  │        WorkerPool (Goroutine池)      │   │
                    │  └─────────────────────────────────────┘   │
                    └─────────────────────────────────────────────┘
```

### 完整代码实现

```go
// ============================================================
// API Gateway: 高并发 × 低延迟 网关实现
// ============================================================

package gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/google/uuid"
	"golang.org/x/time/rate"
)

// ============================================================
// Part 1: 限流器 —— Token Bucket算法实现
// ============================================================

// RateLimiter 基于Token Bucket的限流器
type RateLimiter struct {
	limiters  map[string]*rate.Limiter
	mu        sync.RWMutex
	global    *rate.Limiter
	rate      rate.Limit
	burst     int
	cleanupInterval time.Duration
}

func NewRateLimiter(requestsPerSecond float64, burst int) *RateLimiter {
	rl := &RateLimiter{
		limiters:  make(map[string]*rate.Limiter),
		global:    rate.NewLimiter(rate.Limit(requestsPerSecond), burst),
		rate:      rate.Limit(requestsPerSecond),
		burst:     burst,
		cleanupInterval: 5 * time.Minute,
	}

	// 启动清理goroutine
	go rl.cleanup()

	return rl
}

// Allow 检查是否允许请求
func (rl *RateLimiter) Allow(key string) bool {
	limiter := rl.getLimiter(key)
	return limiter.Allow()
}

// AllowWithContext 检查是否允许，带context取消支持
func (rl *RateLimiter) AllowWithContext(ctx context.Context, key string) error {
	limiter := rl.getLimiter(key)
	return limiter.Wait(ctx)
}

func (rl *RateLimiter) getLimiter(key string) *rate.Limiter {
	rl.mu.RLock()
	limiter, exists := rl.limiters[key]
	rl.mu.RUnlock()

	if exists {
		return limiter
	}

	rl.mu.Lock()
	defer rl.mu.Unlock()

	// 双重检查
	if limiter, exists = rl.limiters[key]; exists {
		return limiter
	}

	limiter = rate.NewLimiter(rl.rate, rl.burst)
	rl.limiters[key] = limiter
	return limiter
}

func (rl *RateLimiter) cleanup() {
	ticker := time.NewTicker(rl.cleanupInterval)
	defer ticker.Stop()

	for range ticker.C {
		rl.mu.Lock()
		if len(rl.limiters) > 10000 {
			// 只保留前一半
			keys := make([]string, 0, len(rl.limiters)/2)
			for k := range rl.limiters {
				keys = append(keys, k)
			}
			for i, k := range keys[:len(keys)/2] {
				delete(rl.limiters, k)
				_ = i // 避免编译器警告
			}
			log.Printf("RateLimiter: cleaned up %d limiters", len(keys)/2)
		}
		rl.mu.Unlock()
	}
}

// ============================================================
// Part 2: Load Balancer —— 加权轮询
// ============================================================

// Backend 代表一个后端Agent服务
type Backend struct {
	ID         string
	URL        string
	Weight     int
	Active     atomic.Bool
	CurrentConns int64
	LatencyP50 time.Duration
	LatencyP99 time.Duration
}

// BackendPool 管理多个后端
type BackendPool struct {
	backends []*Backend
	mu       sync.RWMutex
	index    uint64 // 原子递增，用于轮询
}

func NewBackendPool() *BackendPool {
	return &BackendPool{
		backends: make([]*Backend, 0),
	}
}

func (bp *BackendPool) AddBackend(id, url string, weight int) {
	bp.mu.Lock()
	defer bp.mu.Unlock()

	backend := &Backend{
		ID:     id,
		URL:    url,
		Weight: weight,
	}
	backend.Active.Store(true)
	bp.backends = append(bp.backends, backend)
}

func (bp *BackendPool) NextBackend() *Backend {
	bp.mu.RLock()
	defer bp.mu.RUnlock()

	// 过滤活跃的backend
	active := make([]*Backend, 0, len(bp.backends))
	for _, b := range bp.backends {
		if b.Active.Load() {
			active = append(active, b)
		}
	}

	if len(active) == 0 {
		return nil
	}

	// 加权轮询
	totalWeight := 0
	for _, b := range active {
		totalWeight += b.Weight
	}

	idx := int(atomic.AddUint64(&bp.index, 1)-1) % totalWeight
	sum := 0
	for _, b := range active {
		sum += b.Weight
		if idx < sum {
			return b
		}
	}

	return active[0]
}

// ============================================================
// Part 3: HTTP Handler —— 完整网关实现
// ============================================================

// Gateway HTTP网关
type Gateway struct {
	pool       *WorkerPool
	limiter    *RateLimiter
	backends   *BackendPool
	httpServer *http.Server
	metrics    *GatewayMetrics
}

// GatewayMetrics 网关指标
type GatewayMetrics struct {
	RequestsTotal    atomic.Int64
	RequestsSuccess  atomic.Int64
	RequestsFailed   atomic.Int64
	RequestsLimited  atomic.Int64
	LatencyP50       atomic.Int64
	LatencyP99       atomic.Int64
}

func NewGateway(poolSize, maxQueueLen int, rateLimit float64) *Gateway {
	return &Gateway{
		pool:     NewWorkerPool(poolSize, maxQueueLen),
		limiter:  NewRateLimiter(rateLimit, int(rateLimit)*2),
		backends: NewBackendPool(),
		metrics:  &GatewayMetrics{},
	}
}

func (g *Gateway) Start(ctx context.Context, addr string) error {
	// 启动worker pool
	g.pool.Start(ctx)

	// 注册默认后端
	g.backends.AddBackend("agent-0", "http://localhost:8080", 100)
	g.backends.AddBackend("agent-1", "http://localhost:8081", 100)

	// 设置HTTP路由
	mux := http.NewServeMux()
	mux.HandleFunc("/v1/agent/execute", g.handleAgentExecute)
	mux.HandleFunc("/v1/agent/batch", g.handleBatchExecute)
	mux.HandleFunc("/health", g.handleHealth)
	mux.HandleFunc("/metrics", g.handleMetrics)

	g.httpServer = &http.Server{
		Addr:         addr,
		Handler:      mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 60 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	log.Printf("Gateway starting on %s", addr)
	return g.httpServer.ListenAndServe()
}

func (g *Gateway) handleAgentExecute(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// 1. 速率限制检查
	clientIP := strings.Split(r.RemoteAddr, ":")[0]
	if err := g.limiter.AllowWithContext(r.Context(), clientIP); err != nil {
		g.metrics.RequestsLimited.Add(1)
		http.Error(w, "Rate limit exceeded", http.StatusTooManyRequests)
		return
	}

	// 2. 解析请求
	var req AgentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// 3. 生成请求ID
	if req.RequestID == "" {
		req.RequestID = uuid.New().String()
	}

	// 4. 提交到worker pool
	if err := g.pool.Submit(&req); err != nil {
		http.Error(w, "Queue full", http.StatusServiceUnavailable)
		return
	}

	// 5. 等待结果（简化版，实际应该用channel）
	select {
	case resp := <-g.pool.ResultChan():
		g.metrics.RequestsSuccess.Add(1)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	case <-r.Context().Done():
		g.metrics.RequestsFailed.Add(1)
		http.Error(w, "Request cancelled", http.StatusRequestTimeout)
	}
}

func (g *Gateway) handleBatchExecute(w http.ResponseWriter, r *http.Request) {
	// 批量处理接口，支持更高的吞吐
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "not implemented"})
}

func (g *Gateway) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now().UTC(),
	})
}

func (g *Gateway) handleMetrics(w http.ResponseWriter, r *http.Request) {
	stats := g.pool.Stats()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"requests_total":   g.metrics.RequestsTotal.Load(),
		"requests_success": g.metrics.RequestsSuccess.Load(),
		"requests_failed":  g.metrics.RequestsFailed.Load(),
		"requests_limited": g.metrics.RequestsLimited.Load(),
		"pool_stats":       stats,
	})
}
```

---

## 代码3：Context传播与优雅取消

### 核心架构

```
Request
    │
    ▼
context.WithCancel ──────────────►  goroutine 1 (Agent A)
    │                                  │
    ├── context.WithTimeout ──────────► goroutine 2 (Agent B)
    │                                      │
    │    ┌──────────────────────────────┐  │
    │    │  All share same ctx          │  │
    │    │  Cancelling parent cancels all│  │
    │    └──────────────────────────────┘  │
    │                                      │
    └── context.WithValue("trace_id", id)──► goroutine 3 (Agent C)
```

### 完整代码实现

```go
// ============================================================
// Context传播与优雅取消
// 来源：Go标准库context设计模式
// ============================================================

package main

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"
)

// ============================================================
// Part 1: Agent任务结构
// ============================================================

type AgentTask struct {
	ID       string
	Prompt   string
	Tools    []string
	ParentCTX context.Context // 携带取消信号的context
}

type TaskResult struct {
	TaskID    string
	Output    string
	Error     error
	StartTime time.Time
	EndTime   time.Time
}

// ============================================================
// Part 2: 带超时的Agent执行器
// ============================================================

// AgentExecutorWithContext 使用context控制生命周期的执行器
type AgentExecutorWithContext struct {
	taskQueue  chan *AgentTask
	resultChan chan *TaskResult
	wg         sync.WaitGroup
	cancelFunc context.CancelFunc
}

func NewAgentExecutorWithContext(queueSize int) *AgentExecutorWithContext {
	return &AgentExecutorWithContext{
		taskQueue:  make(chan *AgentTask, queueSize),
		resultChan: make(chan *TaskResult, queueSize),
	}
}

// Start 启动执行器
func (e *AgentExecutorWithContext) Start(ctx context.Context) {
	e.wg.Add(1)
	go e.run(ctx)
}

// run 主循环
func (e *AgentExecutorWithContext) run(parentCtx context.Context) {
	defer e.wg.Done()

	for {
		select {
		case <-parentCtx.Done():
			log.Printf("Executor shutting down: %v", parentCtx.Err())
			return
		case task, ok := <-e.taskQueue:
			if !ok {
				return
			}
			e.executeTask(parentCtx, task)
		}
	}
}

// executeTask 执行单个任务，支持取消
func (e *AgentExecutorWithContext) executeTask(ctx context.Context, task *AgentTask) {
	// 创建任务级别的context，带超时
	taskCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	result := &TaskResult{
		TaskID:    task.ID,
		StartTime: time.Now(),
	}

	// 模拟Agent执行，支持取消
	done := make(chan struct{})
	go func() {
		result.Output = e.runAgent(taskCtx, task)
		close(done)
	}()

	select {
	case <-taskCtx.Done():
		// 超时或被取消
		result.Error = taskCtx.Err()
		result.EndTime = time.Now()
	case <-done:
		result.EndTime = time.Now()
	}

	select {
	case e.resultChan <- result:
	case <-ctx.Done():
	}
}

// runAgent 模拟Agent执行
func (e *AgentExecutorWithContext) runAgent(ctx context.Context, task *AgentTask) string {
	log.Printf("Agent %s starting: %s", task.ID, task.Prompt)

	for i := 0; i < 10; i++ {
		select {
		case <-ctx.Done():
			log.Printf("Agent %s cancelled at step %d", task.ID, i)
			return ""
		case <-time.After(100 * time.Millisecond):
			// 模拟逐步处理
		}
	}

	log.Printf("Agent %s completed", task.ID)
	return fmt.Sprintf("Processed: %s", task.Prompt)
}

// Submit 提交任务
func (e *AgentExecutorWithContext) Submit(task *AgentTask) error {
	select {
	case e.taskQueue <- task:
		return nil
	default:
		return fmt.Errorf("task queue full")
	}
}

// ResultChan 返回结果通道
func (e *AgentExecutorWithContext) ResultChan() <-chan *TaskResult {
	return e.resultChan
}

// Shutdown 优雅关闭
func (e *AgentExecutorWithContext) Shutdown() {
	close(e.taskQueue)
	e.wg.Wait()
	close(e.resultChan)
}

// ============================================================
// Part 3: 层级取消示例
// ============================================================

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	executor := NewAgentExecutorWithContext(100)
	executor.Start(ctx)

	// 提交任务
	tasks := []*AgentTask{
		{ID: "task-1", Prompt: "Process file A"},
		{ID: "task-2", Prompt: "Process file B"},
		{ID: "task-3", Prompt: "Process file C"},
	}

	for _, task := range tasks {
		task.ParentCTX = ctx
		if err := executor.Submit(task); err != nil {
			log.Printf("Failed to submit %s: %v", task.ID, err)
		}
	}

	// 模拟5秒后取消所有任务
	go func() {
		time.Sleep(5 * time.Second)
		log.Println("Cancelling all tasks...")
		cancel()
	}()

	// 收集结果
	go func() {
		for result := range executor.ResultChan() {
			duration := result.EndTime.Sub(result.StartTime)
			if result.Error != nil {
				log.Printf("Task %s failed: %v (duration: %v)", result.TaskID, result.Error, duration)
			} else {
				log.Printf("Task %s completed: %s (duration: %v)", result.TaskID, result.Output, duration)
			}
		}
	}()

	// 等待
	time.Sleep(10 * time.Second)
	executor.Shutdown()
}
```

---

## Go生态位分析：为什么是控制平面而非Agent逻辑

### Rust vs Go：职责分离

Rust和Go不是竞争关系，而是互补关系。它们的职责边界由语言特性决定：

| 特性 | Rust | Go |
|------|------|-----|
| 内存安全 | 编译时所有权 + 生命周期 | 垃圾回收 |
| 并发模型 | Send + Sync类型系统 | Goroutine + Channel |
| 错误处理 | `Result<T, E>` + `?` | 多返回值 + error类型 |
| 适用场景 | Agent核心逻辑、工具执行 | Agent路由、负载均衡、限流 |
| 编译速度 | 慢 | 快 |
| 二进制大小 | 小 | 中等 |

Rust的所有权模型在Agent核心层是必需的：当Agent调用工具时，需要编译期保证状态不会泄漏。Go没有这个能力——它的内存安全靠垃圾回收，这意味着某些类别的错误只能在运行时发现。

但Go在控制平面层有优势：Goroutine的创建成本极低，可以轻松创建数万个并发执行单元。Rust的async/tokio虽然也能处理高并发，但Goroutine的编程模型更简单。

### Stripe Minions的实践证明

Stripe用Go构建的Minions系统每周处理1300+ PR，完全无人值守。关键架构特点：

1. **Blueprint混合编排**：确定性节点 + Agentic节点混合
2. **工具精选子集**：~500个MCP工具，每个Agent只看到筛选后的子集
3. **CI两轮制**：第一轮失败自动修复再跑，还失败则转交人类

这证明了Go控制平面的工程可行性：高并发不是障碍，关键是架构设计。

### 并发吞吐指标

| 指标 | Go (Goroutine) | Java (Thread) | Python (asyncio) |
|------|---------------|----------------|------------------|
| 单机并发数 | 10万+ | 数千 | 10万+ |
| 内存/协程 | ~2KB | ~1MB | ~10KB |
| 创建成本 | 极低 | 高 | 低 |
| 取消传播 | Context原生 | 需手动传播 | 需手动传播 |
| 超时控制 | Context原生 | 需手动实现 | 需手动实现 |

---

## 桥接语

- **承上：** 第五章的Rust类型状态模式解决了单Agent状态机的编译期约束，但多Agent的调度、限流、取消传播需要另一个层级的抽象——这就是Go控制平面。

- **启下：** 当Go控制平面调度多个TypeScript/Rust Agent时，一个关键问题浮现：三个语言层的类型如何在跨服务边界时保持一致？类型状态模式在进程内有效，但跨gRPC/HTTP调用时，类型信息如何传递？

- **认知缺口：** 如果类型系统只存在于单进程内，那么多语言系统如何避免"类型漂移"——当Rust返回的`Result<T, HarnessError>`穿越网络边界到达TypeScript时，谁来保证类型的语义一致性？

---

## 本章来源

### 一手来源

| 来源 | URL | 关键数据 |
|------|-----|---------|
| Stripe Minions | https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents | 每周1300+ PR，Blueprint混合编排，500工具精选子集 |
| Martin Fowler Harness分析 | https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html | Harness工程化定义 |
| Go Context设计 | https://pkg.go.dev/context | 优雅取消传播 |
| Go Rate Limiter | https://github.com/uber-go/ratelimit | 令牌桶算法实现 |

### 二手来源

| 来源 | 用途 |
|------|-----|
| research-findings.md (Section 6) | GRT栈架构对照 |
| research-findings.md (Section 7) | Stripe Minions完整架构 |
