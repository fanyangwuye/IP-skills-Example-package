# 文案 Skill 开发说明

## 目标

交付一个面向 agent 的文案 skill 最小结构，不假装已经具备完整大模型二创写作能力，而是先把确定性内容大脑搭起来：

1. 授权校验
2. 结构化蓝图生成
3. 面向图片 skill 的 handoff 组织

## 当前范围

当前版本重点是“结构整理”和“下游对接”，不是完整自动改写小说正文。

已实现：

- 本地授权关卡
- 蓝图校验
- scene cards → blueprint
- character_sheet / asset_bundle / image_tasks handoff

未实现：

- 高质量全文案改写模型接入
- 复杂互动式文案对话收集

## 与图片 Skill 的衔接

文案 skill 当前最重要的职责，是把上游想法整理成图片 skill 能直接吃的结构：

- `character_sheet`
- `asset_bundle`
- `image_tasks`

这样后面即使文案 skill 还没完全 AI 化，也已经能作为图片 skill 的前置结构层使用。

