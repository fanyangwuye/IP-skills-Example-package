# 02 Task And Manifest Contracts

## 1. 目的

本文件定义双运行时共享的 task、result 和 artifact/manifest 合同。

目标是：

- 让本地与云端使用同一套输入输出语义
- 避免平台接入方直接猜 `run_task(task_dict)` 的隐式字段
- 在不立即重写全部脚本的前提下，为现有 skill 增加稳定外部协议

## 2. 当前代码事实

### 2.1 `ip-copy-skill`

当前 [copy_skill.py](../../skills/ip-copy-skill/scripts/copy_skill.py) 主要特点：

- 统一入口是 `run_task(task: Dict) -> Dict`
- 由 `mode` 决定任务类型
- 大多数返回都包含：
  - `status`
  - `skill`
  - `mode`
  - `task_id`
  - `artifacts`
  - `handoff`
  - `logs`
- 但并不完全一致：
  - `check_license` 没有 `artifacts`
  - `check_license.status` 可能是 `success` 或 `blocked`
  - provider 相关 mode 额外携带 `live_call_made=false`

### 2.2 `ip-video-skill`

当前 [video_skill.py](../../skills/ip-video-skill/scripts/video_skill.py) 主要特点：

- 统一入口也是 `run_task(task: Dict) -> Dict`
- 由 `mode` 决定任务类型
- 大多数返回都包含：
  - `status`
  - `skill`
  - `mode`
  - `artifacts`
  - `handoff`
  - `logs`
- 当前不统一的点：
  - 默认 `_result()` 不带 `task_id`
  - `run_video_generation` 和 `run_video_sequence` 会在默认 JSON artifact 外追加视频 artifact

### 2.3 当前共同点

两个 skill 已经天然接近同一协议：

- 统一 `mode`
- 统一 `handoff`
- 统一 `artifacts`
- 统一 `logs`
- 统一以 JSON 文件作为主输出

因此双适配合同不需要推翻重写，只需要：

1. 补一层显式 envelope
2. 统一 artifact 引用方式
3. 补齐错误与状态模型
4. 定义本地和云端共同的最小必填字段

## 3. 设计原则

1. 向后兼容现有 `run_task(task_dict)` 模式
2. 外部协议显式化，内部核心逻辑尽量少改
3. 云端协议不能依赖本地绝对路径
4. 所有任务都必须有稳定的 `task_id`
5. 所有结果都必须能追溯到产生它的 artifact 和 manifest

## 4. 合同层次

双适配需要定义 3 层合同：

1. `External Task Envelope`
   本地适配器或云端 API/平台提交的外部任务协议
2. `Normalized Core Task`
   适配层转换后，传入现有 core entrypoint 的规范化任务对象
3. `External Result Envelope`
   core 执行后返回给本地 agent 或云端平台的统一结果协议

其中：

- 外部协议对平台稳定
- 内部规范化对象对当前脚本兼容

## 5. External Task Envelope V1

### 5.1 顶层结构

```json
{
  "contract_version": "task-envelope-v1",
  "task_id": "task_20260626_001",
  "skill": "ip-copy-skill",
  "mode": "build_script_draft",
  "runtime": {
    "channel": "local_agent",
    "execution_mode": "sync",
    "dry_run": true
  },
  "input": {
    "inline": {},
    "artifacts": []
  },
  "output": {
    "emit_artifacts": true,
    "preferred_local_dir": "./outputs/example"
  },
  "options": {}
}
```

### 5.2 必填字段

- `contract_version`
- `task_id`
- `skill`
- `mode`

### 5.3 可选字段

- `runtime`
- `input`
- `output`
- `options`

### 5.4 字段说明

#### `contract_version`

固定为外部协议版本，例如：

- `task-envelope-v1`

#### `task_id`

任务唯一标识。规则：

- 由适配层生成或接收
- 本地和云端都必须有
- 后续所有 manifest、日志、job 状态、artifact 都能追溯到它

#### `skill`

当前只允许：

- `ip-copy-skill`
- `ip-video-skill`
- 后续可扩展到 `ip-image-skill`
- 后续可扩展到 `ip-music-skill`

#### `mode`

必须是目标 skill 已实现的 mode。

首批重点 mode：

- `ip-copy-skill`
  - `build_ip_asset_pack`
  - `build_adaptation_scene_cards`
  - `build_script_draft`
  - `polish_script_draft`
  - `build_creative_prompt_pack`
  - `prepare_live_provider_execution`
  - `intake_provider_response`
  - `normalize_provider_response`
- `ip-video-skill`
  - `build_continuity_bible`
  - `build_video_handoff`
  - `build_clip_plan`
  - `episode_readiness`
  - `prompt_architecture_audit`
  - `preflight_video_generation`
  - `prepare_video_generation`

#### `runtime`

描述任务来自哪个运行时，以及执行期望。

建议字段：

```json
{
  "channel": "local_agent|cloud_api|coze_workflow",
  "execution_mode": "sync|async",
  "dry_run": true
}
```

#### `input.inline`

承载当前 task 中的主体业务字段，例如：

- `source_text`
- `blueprint`
- `scene_cards`
- `script_draft`
- `continuity_bible`
- `video_handoff`

#### `input.artifacts`

承载文件型输入，而不是把文件路径散落在业务字段里。

详见第 8 节 `ArtifactRef`。

#### `output`

承载输出偏好，但不改变业务语义。

建议字段：

- `emit_artifacts`
- `preferred_local_dir`
- `preferred_namespace`
- `return_inline_handoff`

#### `options`

承载非业务主数据的附加执行选项，例如：

- `filename_overrides`
- `allow_fallback`
- `validation_level`

## 6. Normalized Core Task V1

### 6.1 存在原因

当前 core entrypoint 还接受平铺的 `task: Dict`。因此适配层需要把外部 envelope 归一化成当前脚本更容易消费的结构。

### 6.2 规范

`Normalized Core Task` 仍然是一个字典，但必须满足：

1. 保留当前核心脚本已经依赖的平铺字段
2. 必须补齐 `_meta`
3. `output_dir` 由适配层显式注入
4. 所有文件型输入应已经完成从外部 `ArtifactRef` 到内部可读取引用的转换

建议结构：

```json
{
  "mode": "build_script_draft",
  "task_id": "task_20260626_001",
  "output_dir": "E:/Plans for 2026/ip-skills_CZ/outputs/tmp_run_001",
  "source_text": "...",
  "scene_cards": [],
  "_meta": {
    "contract_version": "task-envelope-v1",
    "runtime_channel": "local_agent",
    "execution_mode": "sync"
  }
}
```

### 6.3 归一化规则

1. `External Task Envelope.mode` -> `Normalized Core Task.mode`
2. `External Task Envelope.task_id` -> `Normalized Core Task.task_id`
3. `External Task Envelope.input.inline.*` -> 平铺到 core task
4. `External Task Envelope.output.preferred_local_dir` -> `output_dir`
5. `External Task Envelope.runtime.*` -> `_meta`

### 6.4 兼容策略

短期内允许两种输入并存：

1. 旧模式：直接传平铺 `task_dict`
2. 新模式：传 `task-envelope-v1`

适配层负责把两者统一成 `Normalized Core Task`，核心业务代码不直接判断平台类型。

## 7. External Result Envelope V1

### 7.1 顶层结构

```json
{
  "contract_version": "result-envelope-v1",
  "task_id": "task_20260626_001",
  "run_id": "run_20260626_001",
  "skill": "ip-video-skill",
  "mode": "build_video_handoff",
  "status": "success",
  "terminal": true,
  "handoff": {},
  "artifacts": [],
  "warnings": [],
  "errors": [],
  "logs": []
}
```

### 7.2 必填字段

- `contract_version`
- `task_id`
- `skill`
- `mode`
- `status`
- `terminal`
- `handoff`
- `artifacts`
- `logs`

### 7.3 推荐字段

- `run_id`
- `warnings`
- `errors`
- `metrics`
- `debug`

### 7.4 状态枚举

统一定义以下状态：

- `success`
  任务成功完成，结果可继续下游使用
- `blocked`
  任务被业务规则、审批规则或安全规则阻断
- `invalid_input`
  输入不合法，调用方应修正请求
- `failed`
  执行失败，但不是业务阻断
- `queued`
  已接受，等待异步执行
- `running`
  正在执行
- `partial_success`
  主结果存在，但部分 artifact 或子步骤失败
- `cancelled`
  任务被取消

### 7.5 `terminal`

用于统一本地同步任务和云端异步任务：

- `true`：任务已结束
- `false`：任务仍在继续，例如 `queued` 或 `running`

### 7.6 `handoff`

`handoff` 继续作为领域层主输出容器，保持与当前仓库风格一致。

约束：

1. `handoff` 只放结构化领域结果
2. 不在 `handoff` 中混入平台鉴权信息
3. 不在 `handoff` 中混入 HTTP 状态语义
4. 同类结果使用稳定 key

示例：

- `{"script_draft": {...}}`
- `{"video_handoff": {...}}`
- `{"provider_request": {...}}`
- `{"episode_readiness_report": {...}}`

### 7.7 `warnings`

用于承载“结果可用但需要注意”的结构化提示。

示例项：

```json
{
  "code": "dialogue_density_high",
  "message": "对白长度可能超出时长容量",
  "retryable": false
}
```

### 7.8 `errors`

用于结构化错误，而不是只依赖抛异常字符串。

示例项：

```json
{
  "code": "provider_response_missing",
  "message": "normalize_provider_response requires provider_response",
  "field": "provider_response",
  "retryable": true
}
```

## 8. ArtifactRef Contract

### 8.1 目的

当前仓库的 `artifacts` 主要是：

```json
{
  "type": "json",
  "path": "E:/.../video_handoff.json",
  "meta": { "kind": "video_handoff" }
}
```

这对本地模式够用，但对云端模式不够，因为：

- `path` 不是通用协议
- 没有 artifact 唯一标识
- 没有统一引用类型

### 8.2 新结构

统一定义：

```json
{
  "artifact_id": "artifact_001",
  "type": "json",
  "kind": "video_handoff",
  "role": "primary",
  "ref": {
    "scheme": "local_path",
    "value": "E:/Plans for 2026/ip-skills_CZ/outputs/video_handoff.json"
  },
  "content_type": "application/json",
  "meta": {}
}
```

### 8.3 字段说明

- `artifact_id`
  artifact 唯一标识
- `type`
  粗粒度类型，例如 `json`、`video`、`image`、`audio`
- `kind`
  领域含义，例如 `script_draft`、`video_handoff`、`provider_request`
- `role`
  建议取值：`primary`、`supporting`、`generated_clip`、`review_report`
- `ref`
  实际引用方式
- `content_type`
  MIME 类型
- `meta`
  扩展信息

### 8.4 `ref.scheme` 枚举

- `local_path`
- `url`
- `object_key`
- `file_id`
- `inline_json`

### 8.5 向后兼容映射

现有 artifact：

```json
{
  "type": "json",
  "path": "E:/x.json",
  "meta": { "kind": "video_handoff" }
}
```

映射到新结构时应变为：

```json
{
  "artifact_id": "auto_generated",
  "type": "json",
  "kind": "video_handoff",
  "role": "primary",
  "ref": {
    "scheme": "local_path",
    "value": "E:/x.json"
  },
  "content_type": "application/json",
  "meta": { "kind": "video_handoff" }
}
```

## 9. Manifest Contract

### 9.1 定义

Manifest 是对任务输出、产物和状态的结构化落盘表示。不是所有结果都要单独叫 manifest，但凡用于：

- 续接流程
- 跨运行时交接
- 异步任务查询
- provider 准备或回放

都应满足 manifest 合同。

### 9.2 最小字段

```json
{
  "manifest_version": "generic-manifest-v1",
  "task_id": "task_20260626_001",
  "run_id": "run_20260626_001",
  "skill": "ip-video-skill",
  "mode": "prepare_video_generation",
  "status": "success",
  "generated_at": "2026-06-26T14:10:00+08:00",
  "handoff": {},
  "artifacts": []
}
```

### 9.3 规则

1. 任何持久化 JSON 主输出都应可被视为 manifest
2. manifest 必须包含 `task_id`
3. manifest 必须包含版本号
4. manifest 中的 artifact 只能使用 `ArtifactRef` 结构

## 10. 错误合同

### 10.1 原则

异常可以继续抛，但适配层最终返回给平台时必须结构化。

### 10.2 ErrorItem 结构

```json
{
  "code": "invalid_mode",
  "message": "mode must be one of ...",
  "field": "mode",
  "retryable": false,
  "details": {}
}
```

### 10.3 错误来源分类

- `business_rule`
- `validation`
- `system`
- `provider_boundary`
- `storage`
- `platform_adapter`

## 11. 首批迁移要求

为了尽快形成双适配合同，首批代码改造至少要做到：

1. `ip-video-skill` 返回补齐 `task_id`
2. 两个 skill 的所有 mode 都统一返回 `contract_version`
3. 所有 `artifacts[].path` 逐步迁移为 `ArtifactRef.ref`
4. `check_license` 一类无文件输出任务，也必须返回空 `artifacts`
5. 所有结果都显式带 `warnings` 和 `errors`，即使为空数组

## 12. 与后续文档的关系

- 本文档定义“传什么、回什么”
- `03-storage-and-artifact-model.md` 继续定义 artifact 如何存、如何取
- `04-runtime-execution-model.md` 继续定义同步/异步 job 状态流转
- `06-cloud-api-design.md` 继续定义 API 如何承载本合同
- `07-platform-adapter-coze.md` 继续定义 Coze 工具和工作流如何映射到本合同

## 13. 本文档结论

当前仓库已经接近统一结果协议，但还停留在“本地脚本友好”的阶段。双适配的第一步不是发明全新接口，而是把现有 `mode + handoff + artifacts + logs` 这套事实协议正式化、补齐版本与状态模型，并把本地路径提升为通用 artifact 引用合同。
