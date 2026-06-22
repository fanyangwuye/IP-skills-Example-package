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
- 互动式二创状态沉淀
- adaptation_state → scene_cards
- scene_cards / adaptation_state → script_draft
- script_draft → polished_script
- scene cards → blueprint
- character_sheet / asset_bundle / image_tasks handoff
- source_text / characters / scenes → ip_asset_pack

未实现：

- 高质量全文案改写模型接入
- 完整对白润色和最终剧本文学化输出

## 与图片 Skill 的衔接

文案 skill 当前最重要的职责，是把上游想法整理成图片 skill 能直接吃的结构：

- `character_sheet`
- `asset_bundle`
- `image_tasks`
- `ip_asset_pack`

这样后面即使文案 skill 还没完全 AI 化，也已经能作为图片 skill 的前置结构层使用。

## IP 资产包生成

`build_ip_asset_pack` 用来把文案整理成图片 Skill 可直接展开的资产包：

- 保留显式传入的所有角色，不只分析主角
- 只有 `source_text` 时，尽量抽取多个重要角色、称谓角色、怪物角色、员工、盟友、对手
- 为角色绑定明显道具
- 抽取核心场景，默认作为 720 全景环境参考
- 输出 `mode=ip_asset_pack`

这一步是确定性结构整理，不冒充完整大模型阅读理解；后续可以在同一输出格式上接更强的模型解析器。

## 互动式二创状态

`update_adaptation_state` 用来承接用户一轮轮聊天里的创作要求：

- 原始文案 `source_text`
- 用户每轮要求 `conversation_turns`
- 当前二创状态 `adaptation_state`
- 目标形式、风格、视角、受众、限制
- 角色、场景、剧情节拍
- 下一轮建议问题 `next_questions`

`build_adaptation_scene_cards` 会把状态转成可下游使用的场景卡：

- `visual`
- `voiceover`
- `subtitle`
- `music_cue`
- `duration_sec`
- `asset_goal`

场景卡可以继续传给 `build_blueprint`，形成：

`聊天式二创 → adaptation_state → scene_cards → blueprint → image_handoff`

当前版本重点是结构控制和稳定交接，不冒充最终文学化剧本。后续可以在这个结构上接入大模型进行对白润色、冲突强化和完整剧本生成。

## 剧本草稿

`build_script_draft` 用来从 `scene_cards` 或 `adaptation_state` 生成结构化短剧草稿：

- 场次编号
- 起止时间
- 场景地点
- 画面描述
- 动作描述
- 旁白
- 角色对白
- 字幕
- 音乐提示
- 转场
- 图片资产目标

它的定位是“可控剧本骨架”，不是最终文学化对白。
后续如果接写作模型，应基于 `script_draft` 做对白润色、冲突强化、节奏压缩，而不是绕过结构直接自由发挥。

## 对白润色与冲突强化

`polish_script_draft` 用来在结构不变的前提下优化脚本草稿：

- 保留原始场次、时间线、资产目标
- 保留原对白到 `original_dialogue`
- 生成更短剧化的 `polished_dialogue`
- 用短句、反问、压力点增强对白
- 为每场增加 `conflict_notes`
- 标注 `beat_function`，例如 `hook`、`escalation`、`reversal`、`cliffhanger`

这一步仍然是确定性润色，不替代大模型精修。它的价值是给后续写作模型一个稳定的修改方向，避免模型随意改结构、改场次、改资产目标。
