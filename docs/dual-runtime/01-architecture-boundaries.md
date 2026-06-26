# 01 Architecture Boundaries

## 1. 设计目标

本文件定义 `ip-skills_CZ` 的双运行时边界，目标是：

- 让本地与云端共享一套核心业务逻辑
- 明确哪些能力属于核心层，哪些能力属于适配层
- 防止把平台差异写进 skill 核心逻辑
- 为后续 API、Coze 工作流、测试和迁移提供上游约束

## 2. 当前仓库观察

当前仓库的稳定价值主要在两类内容：

1. 业务与流程控制逻辑
   - `ip-copy-skill/scripts/*`
   - `ip-video-skill/scripts/*`
   - deterministic 校验、quality gate、prompt/manifest 构建、provider dry-run 边界
2. agent 运行时接入物
   - `SKILL.md`
   - 本地 JSON task
   - 本地路径、`output_dir`、`outputs/`
   - agent 安装脚本和配置说明

双适配的核心工作不是重写第 1 类，而是把第 2 类从“本地唯一入口”扩展为“本地入口 + 云端入口”。

## 3. 目标分层

目标架构分为 4 层：

1. `Core Engine`
2. `Adapter Layer`
3. `Storage And Artifact Layer`
4. `Provider Execution Layer`

其中：

- `Core Engine` 是唯一业务真相来源
- 本地和云端都只能通过 `Adapter Layer` 进入核心层
- 文件与产物通过 `Storage And Artifact Layer` 抽象
- provider 的 live 执行不直接侵入核心业务层

## 4. Core Engine

### 4.1 职责

`Core Engine` 负责：

- 接收结构化 task
- 运行业务逻辑
- 生成结构化 result/manifest
- 执行 deterministic 校验、质量门禁和流程约束
- 产出对下游可消费的结构化 handoff

### 4.2 不负责

`Core Engine` 不负责：

- 识别 Coze、Codex、Claude 等平台差异
- 直接处理 HTTP 请求或平台工具协议
- 假设输入一定来自本地路径
- 假设输出一定写入某个本地目录
- 把 provider live call 作为默认成功路径

### 4.3 设计约束

1. 核心逻辑只能保留一份
2. 核心 entrypoint 必须能被本地和云端共同复用
3. 核心层输出必须显式带版本、状态、错误和产物引用
4. 核心层默认保留现有离线优先、dry-run 优先的安全边界

## 5. Adapter Layer

`Adapter Layer` 分为两类：

- `Local Adapter`
- `Cloud Adapter`

### 5.1 Local Adapter

职责：

- 读取 `SKILL.md` 约束和本地 task JSON
- 解析本地路径、环境变量和 `output_dir`
- 调用 `Core Engine`
- 把结果写回本地文件系统

保留能力：

- 现有 `run_task(task_dict)` 和 CLI 入口
- 现有 agent 读取仓库和运行 Python 的模式

### 5.2 Cloud Adapter

职责：

- 接收 API/工具调用
- 处理鉴权、请求校验、文件引用解析、任务状态管理
- 调用 `Core Engine`
- 把结果转成平台可消费的 job/result/artifact 响应

限制：

- 不直接暴露仓库目录结构
- 不把平台特有字段渗透进核心业务 schema
- 不把平台工作流节点逻辑塞回核心脚本

## 6. Storage And Artifact Layer

### 6.1 存在原因

当前仓库大量依赖：

- 本地文件路径
- `output_dir`
- `outputs/`
- manifest JSON
- 参考图、故事板、clip 产物

这在本地模式可用，但云端模式不能把“本地绝对路径”当长期协议，因此必须加一层独立抽象。

### 6.2 统一抽象

后续文档应把所有输入输出文件统一抽象为 `ArtifactRef`，至少支持：

- `local_path`
- `url`
- `object_key`
- `file_id`
- `inline_json`

核心层只消费统一引用，不假设它一定是磁盘路径。

### 6.3 责任边界

- `Core Engine`：知道自己需要何种 artifact
- `Adapter Layer`：负责把平台输入转换为统一 artifact 引用
- `Storage Layer`：负责解析、下载、上传、持久化和回传

## 7. Provider Execution Layer

### 7.1 原则

provider 请求准备、结果审核和 provider live execution 必须分离。

### 7.2 核心层职责

核心层负责：

- prompt pack 构建
- provider request 构建
- dry-run manifest
- preflight 校验
- response review
- 结果 normalization

### 7.3 外部执行层职责

外部执行层负责：

- 真正发起 live provider 请求
- 轮询状态
- 下载产物
- 执行重试与超时控制
- 记录 provider 侧运行日志

### 7.4 边界要求

1. 没有经过审批和显式设计，不把 live provider execution 塞进平台 agent 节点
2. 平台适配先接核心层和 dry-run 能力，再决定是否加外部执行器
3. provider 结果必须回到核心层进行 review/normalization，而不是直接流入下游

## 8. 依赖方向

正确依赖方向只能是：

`Platform/Agent -> Adapter Layer -> Core Engine -> Storage/Provider helpers`

禁止出现：

- `Core Engine -> Coze SDK`
- `Core Engine -> HTTP request handler`
- `Core Engine -> 某平台 workflow 字段`
- `Core Engine -> 云端专属鉴权逻辑`

换句话说，平台感知只能存在于适配层，不能反向污染 skill 核心。

## 9. 推荐目录落点

本阶段不强制立即重构代码目录，但目标形态建议如下：

```text
core/
  copy/
  video/
adapters/
  local/
  cloud/
services/
  api/
storage/
  artifact_refs/
providers/
  executors/
```

如果短期不做大迁移，也至少应先在逻辑层遵守这些边界，再逐步调整目录。

## 10. 核心能力与适配能力的划分

### 10.1 应保留在核心层的能力

- `build_ip_asset_pack`
- `build_script_draft`
- `build_continuity_bible`
- `build_video_handoff`
- `build_clip_plan`
- `prepare_video_generation`
- `prompt_architecture_audit`
- `preflight_video_generation`
- provider response review/normalization

### 10.2 应放在适配层的能力

- 本地 CLI 参数解析
- HTTP request/response 映射
- 平台鉴权
- 文件上传下载
- 对象存储映射
- job 状态查询
- 平台专属 callback 或 webhook

## 11. 运行时数据流

### 11.1 本地模式

1. agent 读取 `SKILL.md`
2. agent 组装 task JSON
3. `Local Adapter` 解析本地路径与 `output_dir`
4. `Core Engine` 执行业务逻辑
5. 结果写入本地 manifest 和产物目录

### 11.2 云端模式

1. 平台工具/API 接收结构化请求
2. `Cloud Adapter` 解析文件引用、鉴权和任务配置
3. 任务进入同步执行或异步 job
4. `Core Engine` 执行业务逻辑
5. `Storage Layer` 保存产物并返回 artifact 引用
6. 平台收到结构化 result 或 job 状态

## 12. 阶段性实现建议

### Stage A

先不大改代码目录，只补文档与统一 schema 设计。

### Stage B

从 `ip-copy-skill`、`ip-video-skill` 中抽稳定核心 entrypoint，并减少脚本对绝对路径和本地落盘的硬耦合。

### Stage C

新增 `Cloud Adapter` 和最小 API 服务层，优先支持 dry-run、manifest、preflight 和 handoff 类任务。

### Stage D

再考虑 provider 外部执行器和 Coze 工作流接入。

## 13. 本文档结论

双适配的关键不是“把仓库搬到云端”，而是“让平台差异停留在适配层，让业务真相停留在核心层”。后续所有 API、Coze 节点、job 系统、文件系统和 provider 执行方案，都必须遵守这个边界。
