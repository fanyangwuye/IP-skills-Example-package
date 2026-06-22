---
name: trailer-blueprint-director
description: "Turn ANY script, scene, episode, story outline, or IP doc into a PROFESSIONAL EDITING BLUEPRINT (剪辑蓝图) — a director-grade, shot-by-shot cut plan a real editor can execute. Use when the user gives a script and wants 剪辑蓝图, 剪辑脚本, 剪辑设计, 逐镜剪辑表, 分镜剪辑, 镜头表, 卡点剪辑, 节奏设计, 配乐/字幕/音效设计, or 'design the edit for this script'. Output FORMAT/architecture follows the 《档案局·柒》golden template: an info-unit/anchor breakdown (段落锚点法, each unit = 1 core info), a per-shot edit table (镜号/时间/景别/画面/对白/音乐参考/剪辑参考·感受), a dialogue/voiceover timeline, subtitle+poster typography specs, a segmented music+SFX reference plan with 留白/卡点 execution, and a shortened-cut fallback. Works for trailers/teasers (先导片/预告片) AND full scenes, episodes, openings, or any cut needing a structured blueprint — length is flexible. This is a FINISHED-CUT editing director, NOT a single-shot AI prompt generator — for AI video prompts use seedance-action-director or actor-audition-prompt; for IP adaptation strategy use ip-adaptation-director."
---

# Editing Blueprint Director / 剪辑蓝图导演

把一份**剧本 / 场景 / 分集 / 故事大纲**，变成一份**可直接交给剪辑师施工的专业剪辑蓝图**。

核心不是"写提示词"，是**当剪辑总导演**：把每一镜的景别、画面、台词、配乐、字幕、音效、节奏锚点全部排好。**输出的格式架构对齐 `references/golden-example-dangju-qi.md`（《档案局·柒》范本）**——那是格式标杆，不是题材限制。

## When to Use

- 用户有剧本/场景/分集/大纲，要**设计剪辑**（怎么切、怎么排节奏、配乐字幕音效怎么走）。
- 要逐镜剪辑表、对白时间轴、字幕/海报规范、配乐/音效参考、删减预案。
- 载体不限：预告片/先导片是一种用法，整场戏、单集、开场、混剪同样适用。**时长灵活**，按剧本规模定。

不适用：单镜 AI 视频提示词（用 seedance-action-director / actor-audition-prompt）；IP改编商业策略（用 ip-adaptation-director）。

## Quality Bar — 对齐黄金范本 (MANDATORY)

本 skill 有一份满分**格式范本** `references/golden-example-dangju-qi.md`（《档案局·柒》完整剪辑蓝图）。**它是格式与颗粒度的标杆，不是题材限制**——不管输入是预告片还是整场戏，都对齐它的精细度：信息单元/锚点拆分、逐镜7列表、对白时间轴、字幕/海报规范、配乐+留白+音效分层+删减预案。产出前回看范本末尾的「产出对齐清单」，缺项=降级，不允许偷工。

## Core Method — 段落锚点法 (MANDATORY)

剪辑不是把镜头堆起来，是**用节奏讲清楚**。铁律：

1. **切成信息单元**，每个单元**只让观众接收 1 个核心信息**（预告片5-7个；整场戏/单集按戏剧节拍切，单元数随时长定）。
2. 单元**内部**可快切炫技；单元**之间**用一个**锚点**（音乐重音／一句台词／一次黑场／一个定格）让观众消化。
3. 观众最终记住 N 个清晰故事点，而非一堆乱闪镜头。
4. **一句台词配一人 + 一画面，绝不叠**。台词密度按载体定，密但听得清。

详见 `references/anchor-method.md`。

## Workflow

### 1. 读剧本，抽信息单元

通读剧本，提炼故事主线，切成 5-7 个信息单元。为每个单元定：
- 观众接收的**唯一信息**（一句话）
- **锚点**（用什么让观众换气：片名砸入/定格/黑场/台词/音乐重拍）
- 时间占比（总时长 60-120s 内分配）

先产出**单元表**给用户确认，再往下展开逐镜。

### 2. 排登场人物 & 钩子

列预告片里出场的人物：出场时机/时长、在预告片里干什么、台词或钩子。
**控制信息量**：只正式埋 1-2 条主线势力，其余留彩蛋或留正片。

### 3. 逐镜超详表（核心施工图）

按 15 秒一单元节奏，逐镜展开。每镜必含 7 列：

```text
镜号 | 时间 | 景别 | 画面 | 对白/旁白 | 音乐参考 | 剪辑参考·感受
```

景别缩写：远=大远景 全=全景 中=中景 近=近景 特=特写 微=大特写。〔虚〕=梦境/心理空间。
"剪辑参考·感受"列写**参考片例 + 这一刀想让观众产生的感觉**（这是蓝图的灵魂，不是写"切一下"）。

模板与范例见 `references/shot-table-template.md`。

### 4. 对白/旁白时间轴

把所有台词按时间轴汇总：时间 | 说话者 | 台词。确认"一句一人一画面、不叠"。

### 5. 字幕 & 海报规范

输出文字设计规范（字体/字号/颜色/位置/入场动画）+ 海报排版规范。
规范模板见 `references/subtitle-poster-spec.md`。

### 6. 配乐 + 音效 + 删减预案

- 分单元配乐参考方向（找替代曲用，**不直接用版权曲**）。
- 标 2-3 处**音乐留白**（最关键，比音效更有力）。
- 卡点执行：以 BGM 段落重拍对齐单元锚点即可，不必逐帧卡。
- 音效分层 + 一个更短版本（如 90s）的删减点。
模板见 `references/music-sfx-cutdown.md`。

## Output Format

按固定顺序输出（缺一不可）：

```text
〇 方法论简述（本片用几个单元、各自核心信息）
一 登场人物表
二 逐镜超详表（7列）
三 对白/旁白时间轴
四 字幕/海报规范
五 配乐/音效/删减预案
```

时长按载体定：预告片 60-120s；整场戏/单集/混剪按实际剧本规模。用户没说时长先问一句或按剧本体量估，并附一个更短版删减点。字幕/海报那两节是可选项（预告片/完整成片才需要，纯剧情剪辑可略）。

## Rules

- 段落锚点法是底层铁律：先单元、后逐镜；每单元一个核心信息 + 一个锚点。
- 台词一句一人一画面，不叠；全片 12-16 句封顶。
- "剪辑参考·感受"列必须有参考片例 + 目标感受，不能空写动作。
- 配乐只给"找什么感觉"的参考方向，明确提示用商用授权/无版权曲替代。
- 画面内尽量无成片汉字（牌匾/字幕后期叠加），保持跨语言传播力。
- 多角色镜头默认遵守越轴/视线/站位（参 ai-storyboard-protocol，若可用）。
- SKILL.md 保持精简；长模板/范例放 references/。

## Reference Files

- `references/anchor-method.md` — 段落锚点法详解：如何切单元、选锚点、控制信息密度，含正/反例。
- `references/shot-table-template.md` — 逐镜超详表 7列模板 + 填写规范 + 一段完整范例（含景别缩写、剪辑参考写法）。
- `references/subtitle-poster-spec.md` — 字幕文字设计规范 + 入场动画选择逻辑 + 海报排版规范（竖版）。
- `references/music-sfx-cutdown.md` — 分段配乐参考方向 + 音乐留白 + 卡点执行 + 音效分层 + 90秒删减预案模板。
- `references/golden-example-dangju-qi.md` — 满分**格式范本**《档案局·柒》完整剪辑蓝图（40镜7列表+16句对白+字幕/海报/配乐/音效/删减全套）。**只参考格式架构与颗粒度，不是题材限制**。末尾附「产出对齐清单」。
