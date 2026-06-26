# 04 Runtime Execution Model

## 1. 目的

本文件定义双运行时的执行模型，目标是：

- 保留当前本地同步调用体验
- 为云端运行时补齐异步 job 模型
- 统一 dry-run、live execution、长任务轮询、取消、重试和幂等语义
- 让本地与云端在“同一任务”上共享一致的状态机

## 2. 当前代码事实

### 2.1 当前以同步函数为主

现有 `ip-copy-skill` 和 `ip-video-skill` 的主入口都是：

- `run_task(task: Dict) -> Dict`

当前主要模式是：

1. 进入 `run_task`
2. 立即执行目标 mode
3. 写本地 JSON
4. 直接返回结果 envelope

这说明当前仓库天然偏向本地同步执行。

### 2.2 provider dry-run 已经是明确边界

当前仓库已经有较明确的 dry-run 语义：

- `ip-copy-skill`
  - `build_creative_prompt_pack`
  - `prepare_live_provider_execution`
  - `intake_provider_response`
  - `normalize_provider_response`
- `ip-video-skill`
  - `prepare_video_generation`
  - `run_video_generation` 在 `dry_run=true` 时只生成请求而不真正执行

这说明“先准备、再执行”的模型已经存在，只是还没有统一成完整 job 语义。

### 2.3 当前 live video 是“同步提交 + 阻塞轮询”

`poyo_video_client.py` 当前模式是：

1. 提交任务
2. 轮询 provider 状态
3. 下载结果
4. 一次性返回

因此：

- 它不是纯异步外发
- 也不是平台化 job 系统
- 更像“单进程阻塞式远程任务执行”

### 2.4 当前没有统一 job 状态机

虽然 provider 端已有自己的任务状态，但仓库自身还没有统一的：

- `queued`
- `running`
- `partial_success`
- `cancelled`

因此云端适配必须补这一层。

## 3. 设计原则

1. 本地模式默认同步
2. 云端模式必须支持异步
3. 不是所有 mode 都要异步化
4. dry-run 和 live execution 必须共享同一任务合同
5. provider 状态不等于平台任务状态

## 4. 任务类别

从执行模型上，双适配任务分 4 类：

### 4.1 Instant Task

特点：

- 纯内存计算或轻量 JSON 生成
- 不依赖外部长轮询
- 通常在数秒内完成

示例：

- `check_license`
- `build_ip_asset_pack`
- `build_continuity_bible`
- `prompt_architecture_audit`

建议执行模式：

- 本地：同步
- 云端：同步或短异步

### 4.2 Materialization Task

特点：

- 需要写文件/manifest
- 可能依赖本地目录扫描或图片清单整理
- 不一定调用外部 provider

示例：

- `build_video_handoff`
- `build_clip_plan`
- `build_asset_manifest_template`
- `scan_asset_manifest_directory`

建议执行模式：

- 本地：同步
- 云端：可同步；平台超时敏感时改异步

### 4.3 Guarded Provider Preparation Task

特点：

- 负责生成 provider 请求、preflight、review、normalization
- 原则上不花费或不直接触发 live provider 调用

示例：

- `build_creative_prompt_pack`
- `prepare_live_provider_execution`
- `prepare_video_generation`
- `preflight_video_generation`
- `intake_provider_response`
- `normalize_provider_response`

建议执行模式：

- 本地：同步
- 云端：同步优先

### 4.4 Live Remote Execution Task

特点：

- 真正发起远程 provider 调用
- 可能等待几十秒到数分钟
- 可能需要下载文件
- 失败重试和取消更复杂

示例：

- `run_video_generation`
- `run_video_sequence`
- 未来显式放开的 live LLM executor

建议执行模式：

- 本地：可同步阻塞，也可异步
- 云端：默认异步

## 5. 统一执行模式字段

所有外部任务都建议携带：

```json
{
  "runtime": {
    "execution_mode": "sync|async",
    "dry_run": true,
    "wait_strategy": "inline|submit_only|poll_until_terminal"
  }
}
```

### 5.1 `execution_mode`

- `sync`
  本次调用必须尽量直接返回终态
- `async`
  本次调用只负责接收任务并返回 job 信息

### 5.2 `dry_run`

- `true`
  只做准备、校验、manifest 生成，不做真实 live 执行
- `false`
  允许进入真实执行阶段，但仍要受 provider boundary、审批和平台能力约束

### 5.3 `wait_strategy`

- `inline`
  在当前调用里尽量跑到终态
- `submit_only`
  提交后立即返回 job
- `poll_until_terminal`
  平台或服务层负责轮询直到终态

## 6. Job Model V1

### 6.1 目的

云端运行时必须引入统一 `Job`，否则：

- 长任务无法稳定返回
- 轮询与取消没有对象
- 本地同步和云端异步无法共存

### 6.2 Job 顶层结构

```json
{
  "job_version": "job-v1",
  "job_id": "job_20260626_001",
  "task_id": "task_20260626_001",
  "skill": "ip-video-skill",
  "mode": "run_video_sequence",
  "status": "queued",
  "terminal": false,
  "created_at": "2026-06-26T15:00:00+08:00",
  "updated_at": "2026-06-26T15:00:00+08:00",
  "result_ref": null,
  "progress": {
    "current_step": "accepted",
    "percent": 0
  }
}
```

### 6.3 Job 状态枚举

- `queued`
- `running`
- `success`
- `partial_success`
- `blocked`
- `failed`
- `cancelled`

### 6.4 `result_ref`

当任务完成后，`result_ref` 指向最终 `External Result Envelope` 或其 manifest 引用。

## 7. 统一状态机

推荐统一状态流如下：

### 7.1 同步模式

`accepted -> running -> success|blocked|failed|partial_success`

### 7.2 异步模式

`accepted -> queued -> running -> success|blocked|failed|partial_success|cancelled`

### 7.3 dry-run 模式

dry-run 不是单独状态，而是执行属性。

例如：

- `status=success` + `dry_run=true`
- `status=blocked` + `dry_run=false`

不能把 dry-run 当成成功或失败本身。

## 8. Local Execution Model

### 8.1 默认策略

本地模式默认：

- `execution_mode=sync`
- `wait_strategy=inline`

### 8.2 原因

因为当前仓库的主要使用者是：

- 可读仓库的 agent
- 能直接拿到本地文件输出的调用者
- 不一定需要额外 job 服务

### 8.3 本地长任务例外

对于本地 live provider 执行，允许两种模式：

1. 继续阻塞式同步
2. 外层 agent/脚本自己异步化

但仓库核心合同仍建议把它纳入统一 `Job` 语义，哪怕 job 只在当前进程内存在。

## 9. Cloud Execution Model

### 9.1 默认策略

云端模式建议：

- Instant Task：可同步
- Materialization Task：按平台超时决定
- Live Remote Execution Task：默认异步

### 9.2 云端接入要求

云端服务或平台适配层必须支持：

- `submit job`
- `get job`
- `cancel job`
- `fetch result`

### 9.3 平台节点与 job 的关系

对于 `Coze` 这类平台：

- 工具节点不应假设所有任务都能在单次调用里完成
- 长任务必须返回 `job_id`
- 后续节点通过查询 job 或读取 result manifest 继续流程

## 10. Step Model

为了可观测性和更细粒度失败定位，建议每个 job 记录步骤。

### 10.1 通用步骤

- `accepted`
- `input_normalized`
- `core_execution_started`
- `artifact_materialized`
- `provider_request_prepared`
- `remote_submitted`
- `remote_polling`
- `remote_downloaded`
- `result_published`
- `completed`

### 10.2 适配到具体任务

不是每个任务都必须走完所有步骤。示例：

- `build_ip_asset_pack`
  - `accepted`
  - `input_normalized`
  - `core_execution_started`
  - `artifact_materialized`
  - `result_published`
  - `completed`
- `run_video_sequence`
  - `accepted`
  - `input_normalized`
  - `core_execution_started`
  - `provider_request_prepared`
  - `remote_submitted`
  - `remote_polling`
  - `remote_downloaded`
  - `artifact_materialized`
  - `result_published`
  - `completed`

## 11. 幂等与重试

### 11.1 幂等键

云端模式建议支持：

- `idempotency_key`

用于避免重复提交同一个长任务。

### 11.2 幂等语义

对于以下任务，建议优先支持幂等：

- `prepare_video_generation`
- `run_video_generation`
- `run_video_sequence`
- 未来 live LLM 执行任务

### 11.3 重试分类

应区分：

1. 输入错误
   - 不自动重试
2. 业务阻断
   - 不自动重试
3. provider 临时错误
   - 可自动重试
4. 下载/上传失败
   - 可有限重试

## 12. 取消语义

### 12.1 可取消任务

只有异步 job 和远程长任务必须支持取消语义。

### 12.2 取消状态

取消请求后，job 应进入：

- `cancelling`（可选中间态）
- `cancelled`

### 12.3 取消边界

取消应尽量做到：

- 停止本地轮询
- 停止后续下载
- 尝试调用 provider 取消接口（若 provider 支持）

如果 provider 不支持取消，也必须在 job 记录中明确标注。

## 13. partial_success 语义

以下场景应考虑 `partial_success`：

1. 主 JSON manifest 已生成，但部分下载的视频文件失败
2. sequence 中部分 clip 成功、部分 clip 失败
3. 主 handoff 可用，但某些 supporting artifact 没生成

`partial_success` 不能和 `success` 混用；必须在结果中显式列出失败部分。

## 14. Provider 状态与平台状态解耦

### 14.1 原则

provider 返回的状态不能直接等于平台 job 状态。

示例：

- provider `finished`
  不一定等于平台 `success`
  因为还可能下载失败、校验失败、manifest 发布失败

- provider `failed`
  可能映射为平台 `failed`
  也可能映射为 `partial_success`

### 14.2 推荐映射

- provider `queued` -> job `running` 或 `queued`
- provider `processing` -> job `running`
- provider `finished` -> job 继续进入 `artifact_materialized` / `result_published`
- provider `failed` -> job `failed`

## 15. Result 发布规则

任务进入终态后，必须有稳定结果发布规则：

1. `success`
   发布完整 result envelope
2. `blocked`
   发布带结构化阻断原因的 result envelope
3. `failed`
   发布错误结果 envelope
4. `partial_success`
   发布部分成功 envelope，并列出缺失 artifact
5. `cancelled`
   发布最小结果 envelope，说明取消点和已生成内容

## 16. 首批迁移要求

为了把当前同步脚本仓库提升为双运行时执行模型，首批至少要做到：

1. 所有结果补齐 `terminal`
2. 云端适配层引入 `job_id`
3. `run_video_generation` 和 `run_video_sequence` 支持异步外层执行
4. provider dry-run 与 live 执行共享统一 result envelope
5. 支持 `partial_success`
6. 明确 provider 状态到 job 状态的映射表

## 17. 与后续文档的关系

- 本文档定义“任务怎么跑、怎么结束”
- `05-local-adapter-design.md` 继续定义本地如何承载同步执行
- `06-cloud-api-design.md` 继续定义 job 提交、查询和取消 API
- `08-provider-execution-boundary.md` 继续定义哪些 live 执行在核心层之外完成
- `10-test-strategy.md` 继续定义同步/异步、dry-run/live 的测试矩阵

## 18. 本文档结论

当前仓库已经有清晰的同步执行与 dry-run 习惯，但还没有完整的双运行时 job 语义。下一步不是推翻同步调用，而是在其上层补一个统一状态机：本地默认同步，云端长任务默认异步，dry-run 与 live 共享同一任务合同，provider 轮询只是 job 生命周期中的一个阶段，不是整个执行模型本身。
