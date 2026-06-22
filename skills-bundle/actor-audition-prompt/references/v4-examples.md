# Actor Audition Prompt V4 Examples

Use this file only when detailed examples are needed. Keep SKILL.md focused on workflow.

## Compact Segment Example

```markdown
### 片段 [00:00 - 00:15]
- **剧情动作**：演员站在试镜房胶带标记处，导演刚提醒她“别哭出来”，她重演分手台词。
- **剧本资产引用**：导演是审视方；剧本页是核心道具；演员与角色都处在被判断的位置。
- **表演目标**：证明自己能把痛苦压住，而不是靠哭取胜。
- **潜台词**：嘴上说“我没事”，真正意思是“我快撑不住了，但我不能输”。
- **情绪转折**：强撑平静 → 听见导演翻页声后压力上来 → 手指暴露紧张 → 抬眼把情绪压回去。
- **连续性状态**：上一段结束：无 / 本段起始：站在地面胶带标记处，右手捏着剧本下角 / 本段结束：视线落到导演红笔上 / 下一段衔接：从红笔慢慢抬眼看向导演。
- **形体/微表情**：肩膀不动，拇指摩擦剧本边缘，吞咽一次，眼眶微红但不落泪。
- **对白/声音/字幕**：第一句轻声，停半秒，第二句声线压低；保留同期声，可加字幕。
- **镜头策略**：中近景固定镜头，最后3秒轻微推进，不要复杂运动。
- **一致性护栏**：同一演员脸型、眉眼、鼻唇、发型、年龄感；同一剧本页、试镜房、暖色主光；不新增人物和道具。
- **Seedance 2.0 一键复制提示词**：真实小型试镜房，同一位年轻女演员保持固定脸型、眉眼、鼻子、嘴唇、发型发色、年龄感和克制气质，站在地面胶带标记处，右手捏着同一份翻皱剧本下角，导演作为审视方在冷蓝灰暗部低头批注，不新增伙伴、对手、群众或随机人物，暖色试镜灯照亮脸部，她强撑平静说出分手台词，右手拇指反复摩擦剧本边缘，吞咽一次后抬眼，眼眶微红但不落泪，第一句轻声、停半秒、第二句声线压低，中近景固定镜头，最后3秒轻微推进，表演克制真实，35mm胶片质感，浅景深。禁止新增帽子、眼镜、首饰、额外人物、随机道具；禁止改变发型、服装规则、脸型、年龄感、场景布局和光影方向。[Seedance 2.0] [4K超写实] [表演一致性] [视觉一致性]
```

## QA Replacement Example

Problem:

> Prompt says “a mysterious man appears behind her” but no such character exists in the script.

Severity: high.

Why it fails:

- Adds a new character.
- Breaks faction/relationship logic.
- Creates continuity burden for later segments.

Replacement:

> Remove the mysterious man. Use off-screen pressure instead: “she hears the director stop writing; the room becomes silent; her hand tightens around the same script page.”

## Batch Handoff Example

```markdown
### Batch 1 End State [01:45 - 02:00]
- Character: standing at tape mark, shoulders held still, right hand holding script page.
- Prop: script folded at lower-right corner, red note visible.
- Emotion: anger controlled into silence.
- Camera: medium close-up, static.
- Handoff: Batch 2 must start from the same hand position and silence, then let her raise her eyes before speaking.
```
