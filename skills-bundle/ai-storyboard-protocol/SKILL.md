---
name: ai-storyboard-protocol
description: Mandatory default storyboard protocol for ANY video/分镜/storyboard task with 2 or more characters on screen. Auto-applies axis line (轴线/180度规则), screen-direction lock, eyeline match (视线匹配), and blocking continuity WITHOUT the user having to ask. Also the middleware that standardizes cards across ip-adaptation-director, actor-audition-prompt, and seedance-action-director so dialogue and action scenes stitch into one continuous video without face drift, eyeline mismatch, axis jumps (越轴), or teleporting blocking. Trigger automatically whenever a scene has 2+ characters, or on 故事板, 分镜, 分镜卡, 多角色, 多人, 群戏, 对手戏, 走位, 越轴, 轴线, 视线, 机位关系, 跨镜头连续性. Treat 越轴/视线/站位 as basic film hygiene applied by default, never as opt-in features.
---

# AI Storyboard Protocol / AI分镜协议

This is a **middleware layer**, not another production skill. It defines one shared storyboard card + cross-shot continuity rules so that:

- `ip-adaptation-director` emits standard cards (direction/structure)
- `actor-audition-prompt` fills dialogue/performance fields
- `seedance-action-director` fills action/fight fields
- all of them obey the SAME continuity + multi-character staging rules

Without it, the three skills speak different formats and stitching breaks: face drift, eyeline mismatch, 越轴 (axis jump), teleporting blocking.

## Auto-Apply (MANDATORY — do NOT wait for the user to ask)

The instant a scene has **2 or more characters**, apply this protocol's axis / screen-direction / eyeline / blocking rules automatically. 越轴、视线匹配、站位连续性 are basic film hygiene, NOT optional features the user must request.

- Do NOT require keywords like "别越轴". If there are 2+ people, the line is set and locked by default.
- `actor-audition-prompt` (dialogue) and `seedance-action-director` (action) MUST run this protocol's multi-character backbone fields whenever 2+ characters are present.
- Single-character scenes: still apply continuity + reference-binding rules; axis/eyeline rules simply have nothing to lock yet.
- If the user never mentions staging, you STILL declare 轴线 + 屏幕方向 + 视线 in every multi-character card, and silently enforce the QA Gate.

## When to Use

- ANY 分镜/故事板 task with 2+ characters (automatic, default)
- "把这几个镜头统一成标准分镜卡"
- "多角色群戏，别越轴 / 视线别错"
- "对白戏和动作戏要拼成一条连续视频"
- "检查这组分镜有没有轴线/视线/站位问题"
- any time output from 2+ of the three skills must be combined

## Who Fills What

| Field group | Owner skill |
|---|---|
| 镜头号 / 剧情作用 / 画面骨架 | ip-adaptation-director |
| 表演 / 潜台词 / 微表情 / 对白音频 | actor-audition-prompt |
| 动作流 / 打斗连续性 / 武器道具状态 | seedance-action-director |
| 连续性规则 / 多角色站位 / 越轴防护 / 参考图绑定 / Seedance字段 | this protocol |

## Core Workflow

1. **Scene actor census**: list every character in the scene, assign a stable label (A/B/C) and a face/costume lock id.
2. **Set the line (轴线)**: define the action axis (line between the two key characters, or line of movement). Record camera side (default: stay one side).
3. **Assign screen direction**: each character gets a consistent on-screen side (A=left-facing-right, B=right-facing-left). This is the anti-越轴 anchor.
4. **Build cards**: one card per 15s node, using the unified card template.
5. **Continuity handoff**: each card's start state == previous card's end state (body, position, facing, eyeline, weapon, environment).
6. **Multi-character check**: run the axis / eyeline / blocking checklist before output.
7. **Emit Seedance fields**: per card, output copyable prompt + negative constraints + retry rule.

## Unified Storyboard Card (心脏)

Every skill emits THIS structure:

```markdown
### 镜头 N [00:00 - 00:15]
- **剧情作用**：为什么存在这一镜头
- **在场角色**：A=[标签/锁ID], B=[...], C=[...]
- **轴线**：A↔B 轴线方向 / 移动轴线方向（机位停在轴线哪一侧）
- **屏幕方向**：A 屏幕左·朝右；B 屏幕右·朝左（保持一致）
- **画面**：景别 / 机位 / 运动 / 主体位置
- **视线匹配**：谁看谁，视线高度（平视/俯视/仰视），是否对视
- **表演/动作**：起始姿态 → 动作 → 结束姿态（对白戏填表演，动作戏填动作流）
- **连续性**：上镜结束态 → 本镜起始态 → 本镜结束态 → 下镜交接
- **参考图绑定**：锁脸/锁衣/锁景/锁道具/锁风格 + 禁用项
- **声音字幕**：对白 / 旁白 / 环境声 / 字幕节奏
- **【Seedance字段】**：中文提示词 / 英文 / 负面约束 / 失败重抽建议
```

The three new fields the protocol ADDS on top of existing skill cards: **在场角色 / 轴线 / 屏幕方向 / 视线匹配**. These are the multi-character backbone.

## Multi-Character Hard Rules (必须兜住)

1. **一条轴线，机位守一侧**：除非用明确的过渡镜头（中性轴上镜头、运动越轴、插入空镜），机位不跳到轴线另一侧。
2. **屏幕方向锁定**：A 始终屏幕左、B 始终屏幕右，全场不乱；换镜不换边。
3. **视线匹配**：A 看 B 时视线方向、与 B 看 A 的方向必须互补（一个朝右下，一个朝左上）。
4. **站位可追踪**：每镜写清谁离谁多远、谁高谁低、谁在前景。
5. **三人以上分主轴**：群戏先定"当前主轴线"（焦点两人），其余角色围绕主轴，主轴切换要有过渡。
6. **新角色入画交代方向**：新人物从哪侧入画、面朝哪，必须写明，不许凭空出现在反侧。

## Reference Files

Load only when the step needs depth:

- `references/storyboard-card-template.md` — copyable blank card + a filled dialogue example and a filled action example.
- `references/multichar-axis-rules.md` — 越轴/轴线/180度规则/视线匹配/群戏走位 detailed patterns + how to legally cross the line.
- `references/shot-vocabulary.md` — unified 景别/机位/运动/视线 terminology shared by all three skills.
- `references/continuity-rules.md` — cross-shot handoff rules (dialogue + action unified) and common bugs.
- `references/seedance-generation-fields.md` — Seedance field spec, negative-constraint bank, failed-regeneration rules.

## QA Gate

Reject the storyboard if ANY of these high-severity issues exist:
- 越轴未交代（camera jumped the line with no transition）
- 屏幕方向翻转（A and B swap sides between shots）
- 视线错位（two characters appear to look the same direction in a conversation）
- 站位瞬移（teleport / distance reset）

Otherwise list medium/low fixes and proceed.
