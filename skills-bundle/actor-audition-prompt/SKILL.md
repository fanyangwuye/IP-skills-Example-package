---
name: actor-audition-prompt
description: Seedance 2.0 continuous-video production skill for actor audition, performance scenes, and script-to-video prompt packages. Use when the user asks for 试戏提示词, 演员试戏, 表演导演, 演技指导, 剧本拆解, 剧本元素拆解, 阵营, 伙伴, 对手, 角色关系, 角色一致性, 上传形象图生成连续视频, 参考图识别, 镜头策略, 声音字幕设计, 批量生成, 质检提示词, or wants to convert a script plus character/scene/prop/style references into duration-tiered 1-10 minute Seedance prompts with story asset extraction, reference-type recognition, visual consistency locks, camera strategy, audio/subtitle plan, batch generation plan, failed-regeneration rules, and continuity QA. Not for martial arts/action choreography; use seedance-action-director for fight/action scenes.
---

# Actor Audition Prompt V4 / 剧本资产拆解 + 表演导演 + 连续视频生产

Use this skill to turn a script, character image, scene reference, prop reference, or audition/performance idea into a **Seedance 2.0 continuous-video production package**.

V4 is not just “write prompts”. It builds a production pack:

1. script asset extraction
2. reference-image type recognition
3. character/faction/relationship map
4. visual/prop/scene/light consistency locks
5. acting spine and subtext
6. duration-tiered 15-second segmentation
7. camera strategy
8. dialogue/audio/subtitle plan
9. batch generation plan
10. failed-regeneration rules
11. continuity QA / reverse review

Keep output practical and copyable. Do not invent lore, characters, props, costumes, factions, or symbolic objects beyond the script unless explicitly marked as inference.

## When to Use

Use for requests like:

- “帮我写试戏提示词”
- “这个剧本拆成 Seedance 分段提示词”
- “上传形象图，保持角色一致性生成连续视频”
- “根据剧本拆角色、阵营、伙伴、对手”
- “1-10分钟不同档位生成不同标准内容”
- “帮我检查这组提示词会不会跑偏”
- “给我一个可批量生成的连续视频生产包”

Do not use for fight/action choreography; route action/fight scenes to `seedance-action-director`.

## Core Workflow

1. **Input scan**: script, target duration, aspect ratio, uploaded references, desired model/style.
2. **Reference type recognition**: identify whether each reference is character, costume, scene, prop, or style.
3. **Script asset extraction**: protagonist, partners, factions, opponents, props, location, off-screen forces.
4. **Relationship map**: who is with/against/testing/pressuring whom.
5. **Consistency locks**: visual, costume, prop, scene, lighting, relationship logic.
6. **Acting spine**: objective, obstacle, surface line, subtext, hidden emotion, leak behavior, emotional arc.
7. **Duration tier selection**: choose 1/2/3/4/5/10 minute standard.
8. **Camera/audio strategy**: shot density, movement limits, dialogue/subtitle/sound plan.
9. **Segment prompts**: 15-second nodes with continuity handoff.
10. **Batch plan**: for long outputs, split into generation batches.
11. **QA mode**: check drift, continuity breaks, overstuffing, and model-misreadable wording.

## Duration Tiers

| Duration | Nodes | Standard Deliverable |
|---|---:|---|
| 1 min | 4 × 15s | compact story asset map + acting spine + 4 full prompts |
| 2 min | 8 × 15s | relationship map + 8 prompts + continuity chain |
| 3 min | 12 × 15s | three-act micro-structure + emotional escalation + 12 prompts |
| 4 min | 16 × 15s | audition flow + director feedback/retry beats + 16 prompts |
| 5 min | 20 × 15s | short-scene package + visual/prop continuity audit + 20 prompts |
| 10 min | 40 × 15s | macro beat map + story bible + continuity bible + 5 prompt batches |

For 10 minutes, do not dump all 40 prompts by default. Output macro plan + Batch 1 first, then continue batch by batch unless user explicitly asks for all.

## Required Tables

### 1. Reference Type Recognition Table

Classify each uploaded/provided reference:

- **character reference**: lock face, hairstyle, age impression, body temperament; do not blindly copy background.
- **costume reference**: lock clothing silhouette/material/color; do not copy the model’s face.
- **scene reference**: lock location layout/light/color; do not copy unrelated people.
- **prop reference**: lock prop shape/material/state; do not add extra props.
- **style reference**: lock mood, lens, color, texture; do not copy literal content.

If the user says “只参考脸/五官/气质”, redesign costume/scene while preserving face and temperament.

### 2. Script Asset Map

Extract and label confidence:

- protagonist / main role
- scene partner(s)
- faction / organization / family / team
- allies / partners / mentors
- opponents / pressure source / judging side
- hidden relationship / betrayal risk
- character goal and conflict position
- important props / documents / weapons / tokens
- location and power relationship
- off-screen forces
- must-not-change information

Use labels:

- **明确写出**: directly stated.
- **合理推断**: inferred.
- **待确认**: unclear; ask only if blocking, otherwise use safe default.

### 3. Character / Faction Relationship Map

For each role:

- name or temporary label
- faction/camp
- relation to protagonist
- current attitude: trust / doubt / pressure / threat / dependency / test / concealment
- visible behavior cue
- continuity rule: in-frame / voice-only / off-screen pressure / background mention

Do not randomly add companions, guards, enemies, crowds, monsters, or symbolic figures unless required by the script.

### 4. Consistency Lock Tables

Always lock:

- character visual traits: face shape, eyes, nose, lips, hair, age impression, body temperament
- costume rule: fixed or redesigned
- prop state and hand position
- scene layout and background elements
- lighting direction and color style
- faction/relationship logic
- forbidden additions/removals

### 5. Acting Spine

Define:

- role objective
- obstacle/pressure
- surface line
- real subtext
- hidden emotion
- leak behavior: hand, breath, eyes, jaw, silence, voice
- emotional arc: start → trigger → leak → control/rupture → end state

Do not write abstract emotions only. Make performance visible.

### 6. Camera Strategy Table

Use duration-appropriate shot grammar:

- 1 min: close-up / medium close-up, minimal cuts, one emotional focus.
- 2-3 min: medium / close-up / insert shots, controlled alternation.
- 4-5 min: blocking, foreground/background, monitor POV, director POV when useful.
- 10 min: divide by macro sections; avoid repeating the same shot size for 40 nodes.

Rules:

- each 15s segment has at most one main camera movement.
- do not make every segment push/pull/pan.
- use static frame for fragile emotional beats.
- use slow push-in for realization/pressure.
- use insert shots only for meaningful props/actions.

### 7. Dialogue / Audio / Subtitle Plan

Specify when relevant:

- original dialogue
- keep / rewrite / voiceover / silence
- subtitle needed or not
- speech speed
- pause points
- emphasis words
- breath sound
- page turn / pen / footsteps / room tone
- director off-screen note
- silence duration

### 8. Segment Requirements

Every 15-second node must include:

- timecode
- story/action situation
- script asset reference: faction/ally/opponent/prop/relationship pressure
- performance objective
- subtext
- emotional turn
- continuity state: previous end / current start / current end / next handoff
- body action and blocking
- micro-expression and hand/breath/eye details
- dialogue/audio/subtitle note
- camera strategy
- director note
- consistency guardrails
- Seedance 2.0 copyable prompt

### 9. Batch Generation Plan

For long videos, output batches:

- Batch 1: 00:00-02:00
- Batch 2: 02:00-04:00
- Batch 3: 04:00-06:00
- Batch 4: 06:00-08:00
- Batch 5: 08:00-10:00

Each batch must include:

- batch purpose
- active roles/factions/props
- carried-over visual/scene/light locks
- previous batch end state
- next batch handoff state
- prompts to generate
- failed-regeneration rule

### 10. Failed-Regeneration Rules

If a generated clip drifts, fix only the failed dimension:

- face drift → strengthen face/age/hair/temperament lock.
- costume drift → repeat costume silhouette/material/color and forbid extras.
- prop drift → repeat prop state and hand contact.
- scene drift → repeat layout/background/light direction.
- emotion drift → rewrite action/breath/eye behavior, not abstract emotion.
- camera drift → reduce movement and specify one shot grammar.
- continuity break → restate previous end pose as current start pose.

Do not rewrite the whole prompt blindly.

### 11. QA / Reverse Review Mode

When user asks to check existing prompts/storyboards, inspect:

- script asset accuracy
- character/faction/relationship consistency
- face/hair/age drift
- costume drift
- prop state drift
- scene/light continuity
- action handoff
- emotional handoff
- camera continuity
- audio/subtitle consistency
- too many actions in one segment
- random added characters/props/symbols
- model-misreadable wording

Return:

- problem list
- severity: high / medium / low
- why it will fail
- exact replacement wording

## Output Skeleton

```markdown
# 🎭 Seedance连续视频生产包：[标题]

## 0. 时长档位与交付标准

## 1. 参考图类型识别表

## 2. 剧本资产拆解表

## 3. 角色关系与阵营图

## 4. 视觉/服装/道具/场景/光影锁定表

## 5. 表演内核分析

## 6. 镜头策略表

## 7. 对白/声音/字幕设计表

## 8. 批次生成计划

## 9. 15秒分段提示词

### 片段1 [00:00 - 00:15]
- **剧情动作**：...
- **剧本资产引用**：...
- **表演目标**：...
- **潜台词**：...
- **情绪转折**：...
- **连续性状态**：...
- **形体/微表情**：...
- **对白/声音/字幕**：...
- **镜头策略**：...
- **一致性护栏**：...
- **Seedance 2.0 一键复制提示词**：...

## 10. 失败重抽规则

## 11. 连续性质检表
```

## Evaluation Rubric

Score and normalize to /100:

- script asset extraction accuracy
- reference type recognition accuracy
- character/faction/relationship clarity
- role objective and subtext
- emotional turn visibility
- body/micro-expression credibility
- visual consistency
- prop/scene/light continuity
- camera strategy
- audio/subtitle usability
- batch generation practicality
- Seedance prompt executability

## Multi-Character = Auto-Apply Storyboard Protocol (MANDATORY)

Whenever a scene has **2+ characters**, you MUST automatically apply the `ai-storyboard-protocol` axis / screen-direction / eyeline / blocking rules. Do this by DEFAULT — do not wait for the user to say "别越轴" or "注意视线". 越轴、视线匹配、站位连续性 are basic film hygiene, not optional features.

In every multi-character segment, always declare: 在场角色 / 轴线 / 屏幕方向 / 视线匹配, and silently enforce the protocol QA Gate (越轴无过渡 / 屏幕方向翻转 / 视线错位 / 站位瞬移 = high-severity, reject). Read `ai-storyboard-protocol/references/multichar-axis-rules.md` for the rules.

## Reference Files

Load these only when the matching step needs depth (progressive disclosure):

- `references/v4-examples.md` — worked end-to-end V4 package examples. Read when you need a full sample output.
- `references/performance-beat-patterns.md` — beat patterns for 哭戏/爆发/克制/反派/古装/现代短剧/双人对手/审讯/告别/崩溃. Read when building the Acting Spine and segment performance beats.
- `references/reference-image-binding.md` — lock/forbid rules per reference type (锁脸/锁衣服/锁场景/锁道具/锁风格), multi-reference conflict resolution, anti cross-contamination lines. Read when references are uploaded/described.
- `references/dialogue-audio-design.md` — 台词节奏/停顿/气口/重音/字幕/旁白/画外音/环境声/沉默时长 patterns + Seedance audio wording examples. Read when filling the Dialogue/Audio/Subtitle plan.
- `references/continuity-qa-checklist.md` — drift checklist (脸漂/衣服变/道具凭空/段落衔接/情绪断/镜头乱跳/台词塞太满) with severity + exact replacement wording. Read in QA / Reverse Review mode or before delivering a multi-segment package.
