# 03 Storage And Artifact Model

## 1. 目的

本文件定义双运行时的存储与 artifact 模型，目标是：

- 保留当前本地路径工作流
- 让云端运行时不再依赖本地绝对路径
- 统一输入引用、输出引用、manifest 持久化与产物命名
- 让 `ip-copy-skill` 与 `ip-video-skill` 在本地/云端都能使用同一套 artifact 语义

## 2. 当前代码事实

### 2.1 当前主输出以本地 JSON 文件为中心

现有 `ip-copy-skill` 和 `ip-video-skill` 都会：

- 接收 `output_dir`
- 在该目录下写 JSON 主结果
- 在结果 envelope 中返回：
  - `artifacts[].path`
  - `meta.kind`

这说明当前仓库已经有“artifact”概念，但它默认绑定到本地文件系统。

### 2.2 当前输入引用不统一

现有代码里同时存在以下几种输入表达：

1. 直接内联对象
   - `blueprint`
   - `scene_cards`
   - `video_handoff`
   - `continuity_bible`

2. 本地路径字段
   - `license_path`
   - `asset_manifest_path`
   - `storyboard_image_path`
   - `output_dir`

3. 路径/URL 混用字段
   - `asset_manifest.py` 里的 `path` 实际表示 `PATH_OR_URL`
   - `path` / `url` / 字符串混用

4. 列表型参考输入
   - `image_urls`
   - `reference_image_urls`
   - `reference_video_urls`
   - `reference_audio_urls`

### 2.3 当前存在的关键问题

1. 同一个字段可能同时表示路径和 URL
2. 有些逻辑通过 `os.path.exists()` 猜字符串是 path 还是 URL
3. 云端运行时无法直接消费本地绝对路径
4. artifact 没有稳定的统一引用协议
5. 产物目录、临时目录、对象存储和平台文件 ID 还没有统一模型

## 3. 设计原则

1. 本地路径是实现方式，不是长期外部协议
2. artifact 必须显式标明引用类型
3. core 层只认统一 `ArtifactRef`，不认平台私有存储语义
4. 所有持久化输出都必须能被 manifest 追踪
5. 临时文件和正式产物必须区分

## 4. 统一概念

本设计统一使用以下概念：

### 4.1 Artifact

Artifact 指任务输入或输出涉及的文件/对象/结构化载荷，例如：

- JSON manifest
- 图片
- 视频
- 音频
- 文本文件
- 可内联 JSON

### 4.2 ArtifactRef

ArtifactRef 是 artifact 的统一引用协议，不关心底层是本地磁盘、对象存储还是平台文件系统。

### 4.3 ArtifactManifest

ArtifactManifest 用于描述：

- 本次任务生成了哪些 artifact
- 这些 artifact 的角色是什么
- 它们如何被下游消费

### 4.4 Storage Backend

Storage Backend 是 artifact 的底层实现载体，例如：

- 本地文件系统
- 对象存储
- 平台文件仓库
- 临时工作目录

## 5. ArtifactRef V1

### 5.1 统一结构

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
  "display_name": "video_handoff.json",
  "content_type": "application/json",
  "size_bytes": null,
  "checksum": null,
  "meta": {}
}
```

### 5.2 字段定义

- `artifact_id`
  artifact 唯一标识
- `type`
  粗粒度资源类型，例如 `json`、`image`、`video`、`audio`
- `kind`
  领域语义，例如 `ip_asset_pack`、`video_handoff`、`provider_request`
- `role`
  使用角色，例如 `primary`、`supporting`、`reference_input`、`generated_clip`
- `ref`
  底层引用方式
- `display_name`
  用户可读文件名
- `content_type`
  MIME 类型
- `size_bytes`
  可选，文件大小
- `checksum`
  可选，完整性校验值
- `meta`
  扩展元数据

## 6. `ref.scheme` 枚举

首批统一支持以下 scheme：

### 6.1 `local_path`

适用于本地模式：

```json
{
  "scheme": "local_path",
  "value": "E:/Plans for 2026/ip-skills_CZ/outputs/video_handoff.json"
}
```

### 6.2 `url`

适用于公网或受控可访问 URL：

```json
{
  "scheme": "url",
  "value": "https://cdn.example.com/project/video_handoff.json"
}
```

### 6.3 `object_key`

适用于对象存储：

```json
{
  "scheme": "object_key",
  "value": "projects/ip-skills/task_001/video_handoff.json",
  "backend": "s3"
}
```

### 6.4 `file_id`

适用于平台托管文件仓库：

```json
{
  "scheme": "file_id",
  "value": "coze_file_123456"
}
```

### 6.5 `inline_json`

适用于无需落盘的轻量结构化对象：

```json
{
  "scheme": "inline_json",
  "value": {
    "title": "黄泉饭店"
  }
}
```

## 7. Local Storage Model

### 7.1 本地运行时保留能力

本地模式继续支持：

- `output_dir`
- 绝对路径
- 相对路径
- 本地参考图目录扫描
- 本地 manifest 文件

### 7.2 本地 artifact 规范

本地运行时中：

- 主输出仍可落盘为 JSON
- `ref.scheme` 固定为 `local_path`
- `value` 必须使用规范化绝对路径

### 7.3 本地目录分类

建议统一分为：

1. `workspace output`
   用户明确指定的项目输出目录
2. `runtime temp`
   单次执行的临时目录
3. `cache`
   可重用中间产物
4. `logs`
   日志与调试文件

### 7.4 本地路径规则

1. 写入路径必须在允许工作区内
2. 输出路径由适配层规范化成绝对路径后再注入 core
3. 不在业务字段中传播临时系统目录路径，除非它本身就是 artifact 引用

## 8. Cloud Storage Model

### 8.1 云端运行时约束

云端运行时默认不能假设：

- 本地磁盘路径对调用方可见
- 进程工作目录长期存在
- 下游平台能访问服务器临时目录

### 8.2 云端 artifact 推荐策略

云端模式中：

- 输入文件优先转成 `file_id` 或 `object_key`
- 输出文件优先写入对象存储或平台文件仓库
- 返回给平台时使用：
  - `url`
  - `file_id`
  - `object_key`

### 8.3 云端临时文件

云端执行期间允许存在临时本地文件，但：

1. 临时文件不是外部协议
2. 临时文件必须在上传/转换后变成正式 artifact 引用
3. 临时文件路径不得直接返回给平台调用方

## 9. Artifact Lifecycle

每个 artifact 在逻辑上都经历以下生命周期：

1. `declared`
   任务声明需要该 artifact
2. `resolved`
   输入引用已解析，或输出位置已分配
3. `materialized`
   文件或对象已真正生成
4. `published`
   已成为下游可访问引用
5. `retired`
   已过期或被清理

### 9.1 输入 artifact

输入 artifact 的关键步骤是：

- 引用解析
- 权限校验
- 下载/挂载/读取
- 转换为 core 可消费引用

### 9.2 输出 artifact

输出 artifact 的关键步骤是：

- 生成
- 落盘或上传
- 生成统一 `ArtifactRef`
- 写入 result/manifest

## 10. Artifact Role 分类

为了让本地和云端下游都能稳定消费，建议统一以下角色：

- `primary`
  当前任务主结果
- `supporting`
  辅助结果
- `reference_input`
  上游输入参考
- `generated_clip`
  生成视频片段
- `review_report`
  预检/审核/质量报告
- `provider_request`
  provider 请求 manifest
- `provider_response`
  provider 原始或审核后结果

## 11. 产物命名模型

### 11.1 问题

当前仓库主要用：

- `handoff_filename`
- `provider_request_filename`
- `asset_manifest_template_filename`

这是可用的，但它还是“脚本参数思维”，不够适合云端批处理与对象存储。

### 11.2 建议命名模板

建议统一命名元素：

- `project_or_ip_id`
- `task_id`
- `mode`
- `artifact_kind`
- `sequence_or_clip_id`
- `timestamp`

示例：

```text
huangquan_fandian/task_20260626_001/build_video_handoff/video_handoff.json
huangquan_fandian/task_20260626_001/prepare_video_generation/provider_request_clip_001.json
huangquan_fandian/task_20260626_001/run_video_sequence/generated/clip_001.mp4
```

### 11.3 本地命名与云端命名

- 本地模式可以继续用现有短文件名
- 云端模式建议总是补完整命名空间
- manifest 中始终保留 `kind` 和 `artifact_id`，避免只靠文件名识别

## 12. Asset Manifest 模型收口

### 12.1 当前现状

`asset_manifest.py` 和 `example_asset_manifest.json` 里，当前主要用：

- `path`
- `url`
- 占位字符串 `PATH_OR_URL_*`

这说明仓库已经意识到路径/URL 双形态，但还没把它正式抽象出来。

### 12.2 收口方案

后续应把 asset manifest 中的每个引用都迁移为显式二选一：

1. 简化兼容格式

```json
{
  "path_or_url": "..."
}
```

2. 标准格式

```json
{
  "artifact_ref": {
    "scheme": "local_path",
    "value": "E:/..."
  }
}
```

建议：

- 对外长期协议使用 `artifact_ref`
- 为兼容现有资产模板，短期允许 `path` / `url` / `path_or_url`
- 适配层负责把旧字段统一归一化为 `ArtifactRef`

### 12.3 反对继续使用“猜测”

禁止继续依赖以下推断逻辑作为长期协议：

- `os.path.exists()` 判断字符串是不是路径
- 通过文件名猜角色或引用种类
- 通过平台节点上下文猜这个文件来自哪里

这些只能作为迁移期兼容逻辑，不能成为正式合同。

## 13. 读写职责划分

### 13.1 Core Engine

只负责：

- 声明自己需要/生成哪些 artifact
- 返回结构化 artifact 描述

不负责：

- 直接做对象存储上传
- 直接依赖 Coze 文件 API
- 直接管理云端下载 URL 生命周期

### 13.2 Adapter Layer

负责：

- 把外部输入变成 `ArtifactRef`
- 选择本地或云端 backend
- 把 core 输出 artifact 发布成平台可消费引用

### 13.3 Storage Backend

负责：

- 存储
- 读取
- 上传
- 下载
- 清理临时文件
- 生成公开或受控访问引用

## 14. 安全与权限

### 14.1 本地模式

- 限制写入工作区或显式允许目录
- 不把敏感本地路径暴露给非本地调用方

### 14.2 云端模式

- 不默认暴露内部磁盘路径
- URL 需要有访问策略
- 对象存储 key 不应泄露无关租户命名空间
- 平台 `file_id` 必须能追溯到任务上下文

## 15. 首批迁移要求

为了从当前仓库平滑迁到统一存储模型，首批代码改造至少要做到：

1. 所有输出 artifact 从 `path` 升级到 `ref.scheme + ref.value`
2. `asset_manifest` 引用支持显式 `artifact_ref`
3. 适配层统一把旧的 `path` / `url` / 字符串列表归一化为 `ArtifactRef`
4. `video_provider.py` 不再把“字符串存在于本地”作为长期判断依据
5. 本地模式和云端模式都通过同一个 artifact 发布流程返回结果

## 16. 与后续文档的关系

- 本文档解决“文件和产物怎么表达”
- `04-runtime-execution-model.md` 继续解决“artifact 在同步/异步任务中如何流转”
- `06-cloud-api-design.md` 继续解决“API 如何上传、下载和返回 artifact”
- `07-platform-adapter-coze.md` 继续解决“Coze 文件输入输出如何映射到 ArtifactRef`

## 17. 本文档结论

双适配的存储问题，本质不是“本地还能不能写文件”，而是“能不能把文件系统实现细节从长期协议里抽离出来”。当前仓库已经有 artifact 和 manifest 雏形；下一步要做的，是把 `path`、`url`、`file_id`、`object_key` 统一纳入 `ArtifactRef`，让本地和云端共享同一套引用模型。
