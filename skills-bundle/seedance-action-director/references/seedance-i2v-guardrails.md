# Seedance I2V Guardrails / Seedance 图生视频护栏

Use this reference when the user provides one or more images and wants Seedance 2.0 action video prompts while preserving character, costume, weapon, scene, and style consistency.

## First Principle

For I2V, do not describe a totally new image. Describe how the reference image evolves over time.

Good:

```text
保持参考图中角色的脸型、发型、服装、武器和雨夜石桥环境不变；角色从静止持剑姿态开始，右脚后撤半步，剑尖从低位抬到胸前，雨水沿剑身甩出。
```

Bad:

```text
一个全新的女侠在森林大战十个敌人。
```

## Reference Type Recognition

When images are provided, classify each image before prompting:

| Reference Type | Lock These | Do Not Lock These Unless User Says |
|---|---|---|
| Character reference | face, hairstyle, body type, age impression, key costume traits | exact background, random pose, accidental objects |
| Costume reference | fabric, silhouette, color, texture, accessories | model face, background, lighting |
| Weapon/prop reference | shape, material, size, marks, damage state | holder identity, unrelated scene |
| Scene reference | spatial layout, architecture, weather, light direction | characters in reference, incidental clutter |
| Style reference | color palette, lens, texture, mood | exact character, exact composition |

If uncertain, state the assumption briefly and proceed.

## I2V Prompt Structure

Each final prompt should include:

```text
[Reference lock]
保持参考图中的主体身份/服装/武器/环境/光影不变。

[Start state]
从参考图当前姿态或上一节点结束姿态开始。

[Action transformation]
15秒内只做一个核心动作变化。

[End state]
结束在可衔接下一段的明确姿态。

[Camera]
镜头如何跟随，而不是疯狂乱飞。

[Negative guardrails]
禁止换脸、换衣服、换武器、添加无关角色、环境重置、肢体畸形、卡通化。
```

## Action Amount Control

Seedance I2V works better when each 15-second node contains:

- 1 primary movement
- 1 clear reaction/impact
- 1 final pose
- 1 camera strategy

Avoid:

```text
起跳、翻滚、拔剑、砍三个人、爆炸、落地、回忆、转场、说台词
```

Better:

```text
从低位持剑姿态开始，角色向左侧滑步避开攻击，剑从右下向左上挑起，雨水沿剑锋甩出，最后停在半蹲防守姿态。
```

## Consistency Negative Prompts

Use as needed:

```text
no face change, no hairstyle change, no costume change, no new accessories, no weapon replacement, no extra characters, no environment reset, no sudden time-of-day change, no cartoon effect, no plastic skin, no distorted limbs, no floating without landing, no teleportation
```

Chinese version:

```text
禁止换脸、禁止改发型、禁止换服装、禁止新增饰品、禁止替换武器、禁止新增无关角色、禁止场景重置、禁止突然改变时间和光线、禁止卡通化、禁止塑胶皮肤、禁止肢体畸形、禁止无落点漂浮、禁止瞬移。
```

## Multi-Image Inputs

If multiple images are provided, produce a binding table:

| Image | Role | Lock Rule | Ignore Rule |
|---|---|---|---|
| Image A | character | face, hair, body type | background |
| Image B | costume | robe shape/color/material | model face |
| Image C | weapon | sword length/material/marks | hand pose |
| Image D | scene | bridge layout/rain/light | random people |

Then every prompt should mention only the intended locked attributes.

## Failure Recovery Rules

If generation drifts, repair one variable at a time:

1. Face drift → strengthen face/hair/age lock; reduce action complexity.
2. Costume drift → repeat exact clothing traits; remove style synonyms that conflict.
3. Weapon drift → specify weapon length, hand, material, and end position.
4. Scene drift → repeat layout, ground, weather, and light direction.
5. Motion chaos → reduce to one action transformation.
6. Floating problem → add takeoff force, mid-air duration, landing pose, ground reaction.

## Wuxia Special Guardrail

Fantasy movement can be stylized, but must still have readable physics:

```text
蹬地起势 → 衣摆/尘土响应 → 空中轨迹 → 明确落点 → 膝盖缓冲/脚步落地
```

Do not write:

```text
角色在空中无限旋转大战。
```

Write:

```text
角色右脚蹬地跃起半身高度，衣摆向后扬起，剑锋划出半圆轨迹，2秒后左脚落在湿石板上，膝盖微屈缓冲，水花溅起。
```
