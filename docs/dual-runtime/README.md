# Dual Runtime Design Docs

本目录用于设计 `ip-skills_CZ` 的双适配方案：同一套核心能力，同时支持本地代码型 agent 和云端托管型 agent。

## 目标

- 保留当前仓库对 `Codex`、`Claude Code`、`OpenClaw` 一类本地/代码型 agent 的适配能力
- 新增对云端平台 agent 的接入设计，例如 `Coze` 一类只能通过工具/API/工作流调用的运行时
- 避免复制两套业务逻辑；本地与云端共享一套核心 task、manifest、校验与流程约束

## 当前文档清单

1. `00-scope-and-goals.md`
   说明双适配的范围、目标、非目标、成功标准和阶段划分
2. `01-architecture-boundaries.md`
   说明核心层、适配层、存储层、执行层的边界和依赖方向
3. `02-task-and-manifest-contracts.md`
   待写。统一 task 输入、result/manifest 输出、错误结构、版本策略
4. `03-storage-and-artifact-model.md`
   待写。统一本地路径、URL、文件 ID、对象存储和产物目录模型
5. `04-runtime-execution-model.md`
   待写。定义同步/异步、job 状态机、幂等、取消、超时、重试
6. `05-local-adapter-design.md`
   待写。定义 `SKILL.md + Python + outputs/` 的本地适配模式
7. `06-cloud-api-design.md`
   待写。定义云端服务接口、鉴权、API schema、长任务策略
8. `07-platform-adapter-coze.md`
   待写。定义 Coze 的工具拆分、工作流节点、文件传递与上下文约束
9. `08-provider-execution-boundary.md`
   待写。定义 provider dry-run、live execution、审批和外部执行器边界
10. `09-observability-and-ops.md`
    待写。定义日志、审计、trace、故障排查和运维接口
11. `10-test-strategy.md`
    待写。定义本地测试、契约测试、云端集成测试和假 provider 策略
12. `11-migration-plan.md`
    待写。定义从当前本地优先仓库迁移到双适配架构的分阶段方案

## 建议编写顺序

1. 先写 `00` 和 `01`
2. 再写 `02`、`03`、`04`
3. 然后写 `05` 和 `06`
4. 最后写 `07` 到 `11`

顺序原因：

- 没有范围定义，后续 API 与平台适配容易失控
- 没有架构边界，后续文档会默认把业务逻辑复制两份
- 没有 task/manifest 契约，云端和本地会使用两套输入输出协议
- 没有运行时模型，长任务、产物交接和失败重试无法稳定落地

## 设计约束

- 核心业务逻辑只能保留一份，不允许派生“本地版脚本”和“云端版脚本”
- 现有 skill 的 deterministic 校验、流程约束、quality gate、manifest 结构优先保留
- provider live execution 不直接塞进 platform agent；默认仍由受控执行层负责
- 本地模式继续支持文件路径；云端模式必须支持 URL、文件 ID 或对象存储引用
- 任一新接口都必须能追溯到现有 `run_task(task_dict)` 或等价核心 entrypoint

## 与现有文档的关系

- [../agent_config.md](../agent_config.md)：保留 agent 接入说明，不承担双适配架构设计
- [../provider_setup.md](../provider_setup.md)：保留 provider 环境配置说明
- [../续接开发说明.md](../续接开发说明.md)：保留阶段性续作记录，不替代正式设计文档

## 下一步

当前版本先完成双适配的范围和架构边界。后续文档应以这两份为上游约束，不要先写 API 再反推架构。
