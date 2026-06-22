---
name: seedance-action-director
description: Generate Seedance 2.0-ready action / martial-arts / fight-scene prompts from scripts, novel excerpts, image references, or one-line action ideas. Use when the user asks for 动作戏导演, 动作分镜, 打斗分镜, 武侠动作, 动作戏提示词, Seedance动作戏, or wants long action sequences split into 15-second nodes with visual-gene consistency, start/end body positions, camera movement, and I2V-optimized prompts. Not for general non-action dialogue scenes; use actor-audition-prompt for performance/audition scenes.
---

# Seedance Action Director / 动作戏导演

Use this skill to create **Seedance 2.0** prompts for action scenes, martial arts, chases, fights, swordplay, gunfights, stunts, and dynamic physical sequences.

## Core Goal

Solve two recurring AI-video problems:

1. **Visual consistency** — character, weapon, costume, lighting, environment stay stable.
2. **Action continuity** — each 15-second node starts where the previous node physically ended.

Final output should be a structured action storyboard/prompt set optimized for Seedance 2.0 I2V or text-to-video.

## Real Use Cases

Trigger this skill for requests like:

- “帮我写一段武侠打斗 Seedance 提示词”
- “把这个动作剧本拆成每15秒节点”
- “根据这张角色图设计一场追逐/打斗/刀剑动作戏”
- “动作要连贯，上一段结束姿势要接下一段起始姿势”

## Workflow

### 1. Establish Visual Gene Lock

Before segmenting, define immutable visual constants.

Include:

- **Character constants**: face, hairstyle, hair color, costume material, texture, accessories, scars, makeup, body type.
- **Weapon/prop constants**: weapon type, length, material, scratches, color, special marks.
- **Environment constants**: location, light direction, weather, dust/fog/rain/sparks, ground material.
- **Image quality style**: 4K/8K cinematic realism, film grain, color palette, aspect ratio.

If the user provides an image, describe extracted constants. If no image is provided, define a consistent baseline.

### 2. Plan Rhythm and Physical Continuity

Split by 15-second nodes.

- 1 minute = 4 nodes
- 3 minutes = 12 nodes
- 5 minutes = 20 nodes

For every node, explicitly track:

- start body position
- action flow
- end body position
- next-node continuity note

No random teleporting. No new weapons appearing unless introduced and kept.

### 3. Generate Each Action Node

Each node must include:

1. **起始状态** — body position, spatial relation, weapon position.
2. **核心动作流** — action transformation across 15 seconds.
3. **结束状态** — where the body/weapon/camera ends.
4. **镜头语言** — shot size, tracking, push/pull, slow motion, handheld, whip pan, etc.
5. **环境交互** — dust, cloth, rain, debris, footprints, sparks, broken objects.
6. **Seedance 2.0 一致性提示词** — compact prompt with visual constants + action variables.


### 4. Lock the Four-Layer Combo (MANDATORY for every action node)

四层不是独立选项,是**一条出招链**,每个动作节点都要拧成一股绳。顺序固定:

```text
节奏意图 → 速度档位 → 大师运镜 → 打击感五要素
(rhythm)   (speed tier)  (camera)    (impact)
```

- **先定节奏意图**(慢/快/停/顶):这一节点在节奏曲线的哪个位置?(rhythm-pacing.md)
- **据节奏选速度档**:静速/常速/高速/超高速 (master-camera-speed.md Part 1)。
- **据速度配运镜**:查 speed×camera 配对表,选大师运镜八式中匹配的 (master-camera-speed.md Part 2-3)。
- **据运镜落打击感**:顿帧/受击形变/速度对比/音画卡点/环境反馈 (fight-choreography.md Part 2)。

**联动铁律**:
- 顶点节点 = 超高速 + 速度坡道/子弹时间 + 升格长镜 + 打击感五要素全开 + 静默卡点。
- 顶点前必有一个慢拍/留白节点垫底(静速+长镜),否则顶点不炸。
- 每个节点提示词必须同时带:**节奏词 + 速度词 + 运镜词 + 打击感词 + 安全尾巴**,缺一层就是半成品。
- 速度词(高速战斗/超高速战斗)不是孤立加,要和运镜+节奏匹配:超高速必配子弹时间/速度坡道+顶点节奏位。

联动示例(顶点节点):
```text
[节奏]被压制到谷底后骤然反弹,顶点绝杀;
[速度]超高速战斗,出手速度坡道升格;
[运镜]子弹时间360环绕+升格长镜拉长瞬间;
[打击感]触及顿帧,对手剧烈后仰踉跄撞墙,低频闷响静默卡点,碎屑悬停;
[安全]无血腥,风格化非写实,PG-13,stylized non-graphic hyper-speed master shot。
```

## Multi-Character = Auto-Apply Storyboard Protocol (MANDATORY)

Whenever an action scene has **2+ characters** (fighter vs fighter, pursuer vs pursued, group melee), you MUST automatically apply the `ai-storyboard-protocol` axis / screen-direction / eyeline / blocking rules BY DEFAULT — do not wait for the user to ask. 越轴、移动轴线、屏幕方向、视线 are basic film hygiene.

In every multi-character action node, always declare 在场角色 / 轴线(移动方向) / 屏幕方向 / 视线, and enforce the protocol QA Gate (越轴无过渡 / 方向翻转 / 视线错位 / 站位瞬移 = reject). Read `ai-storyboard-protocol/references/multichar-axis-rules.md` for the rules.

## Reference Files

Use bundled references only when the request needs that extra depth:

- `references/action-shot-patterns.md` — read when the user asks for richer action shot design, genre-specific camera grammar, wuxia/modern fight/chase/sword-duel patterns, or when the scene feels visually repetitive.
- `references/continuity-examples.md` — read when building multi-node sequences where every 15-second node must continue from the previous end pose, weapon state, spatial relation, and environment damage state.
- `references/seedance-i2v-guardrails.md` — read when the user provides images or asks for I2V / 图生视频, reference-image consistency, multi-image binding, or drift repair.
- `references/fight-choreography.md` — read when the scene needs real 打击感 (impact) and choreography quality: hit-stop/受击形变/速度对比/音画卡点/环境反馈, attack-defense rhythm, rhythm curve. CONTAINS the platform-safe impact principle (打击感靠镜头与物理，不靠血腥暴力).
- `references/combat-styles.md` — read when the scene has a specific style: 武侠/现代格斗/醉拳/枪战CQB/刀剑对决/追逐, each with its own move logic + camera grammar + safe impact flavor.
- `references/master-camera-speed.md` — read when the user wants 大师级镜头 / 高速战斗 / 超高速战斗 / speed-driven 武戏结构. Speed tiers (静速/常速/高速/超高速), 8 master camera grammars (拳随镜动/速度坡道/一镜到底/子弹时间/低机位仰冲/甩镜接位/推拉呼吸/主观冲击), speed×camera pairing, and a 4-node speed-tiered fight structure template.
- `references/rhythm-pacing.md` — read whenever pacing/节奏感 matters (almost always). Master controller tying together 攻防节奏 + 速度档位: 节奏五要素(快慢交替/卡点/留白/长短镜交错/情绪呼吸), 剪辑节奏(镜头时长表), 节奏曲线心电图, 卡点设计, 留白的艺术, 节奏×段落模板.

Keep `SKILL.md` as the operating workflow. Keep long examples, pattern banks, and I2V guardrails in `references/` so the skill does not become a giant junk drawer.

## Output Format

```markdown
# 🎬 强一致性动作剧本：[剧本标题/主题]

## 🧬 视觉基因锁定（全局一致性基准）

- **主体特征**：...
- **服饰/材质**：...
- **武器/道具**：...
- **环境基调**：...
- **光影/色调**：...
- **通用画质标签**：[Seedance 2.0] [4K超写实] [35mm胶片质感] [Action sequence consistency]
- **兜底禁令**：无AI磨皮、无塑胶感、无卡通特效、无武器凭空出现、无瞬移、无肢体畸形

---

## 🎞️ 连贯分镜列表（每15秒一节）

### 节点 1 [00:00 - 00:15]

- **起始状态**：...
- **核心动作流**：...
- **结束状态**：...
- **镜头语言**：...
- **环境交互**：...
- **衔接提示**：下一节点必须从“...”开始。
- **【Seedance 2.0 一致性提示词】**：...

### 节点 2 [00:15 - 00:30]
...
```

## Prompting Rules

- Consistency beats spectacle. Repeat the visual constants in every node prompt.
- Describe action as **transformation**: from start pose → movement → impact/reaction → end pose.
- Avoid abstract words like “激烈打斗” alone; specify limbs, weapons, direction, rhythm, impact, and recovery.
- Keep physics plausible unless the user explicitly asks for fantasy/wuxia exaggeration.
- For wuxia: specify wire-like movement, robe flow, weapon arcs, landing posture, and dust/leaf/water interaction.
- For modern action: specify cover, footwork, camera shake, impacts, obstacles, and spatial geography.
- For I2V: focus on how the reference image evolves, not on redrawing the whole scene.

## Safety / Boundaries

- This skill generates fictional choreography and visual prompts only.
- Do not provide real-world instructions for harming people, building weapons, or tactical violence.
- Keep action descriptions cinematic and non-instructional.
- **Platform-safe impact (默认)**: sell 打击感 through camera + physics (hit-stop, recoil, speed contrast, audio beat, environmental response), NOT blood/gore. Always append a safety tail to action prompts: `无血腥，无伤口特写，无暴力血浆，风格化非写实，PG-13，stylized non-graphic action`. For gunfights, also avoid real weapon-handling/tactical detail and graphic wounds. See `references/fight-choreography.md` Part 1.

## Quick Example

```markdown
### 节点 1 [00:00 - 00:15]
- **起始状态**：女侠立在雨夜石桥中央，右手长剑低垂，剑尖贴近湿石板，左肩披风被风吹起。
- **核心动作流**：她听见身后脚步，先侧身半步避开横劈，左手压住披风，右手剑从低位斜上挑起，剑锋划出雨水弧线，逼退黑衣人。
- **结束状态**：她落在桥栏旁，剑横在胸前，黑衣人退到三米外。
- **镜头语言**：低机位中景跟拍，闪电瞬间切到剑锋特写，再拉回全景。
- **环境交互**：雨水被剑锋甩开，湿石板溅起水花，披风边缘滴水。
- **衔接提示**：下一节点从“女侠背靠桥栏，剑横胸前，黑衣人三米外”开始。
- **【Seedance 2.0 一致性提示词】**：雨夜古石桥，黑发女侠，深青色湿润长袍，右手细长旧银剑，冷蓝月光与雨水反光，女侠从剑尖低垂姿态侧身闪避黑衣人横劈，低位斜上挑剑，雨水形成弧线，最后背靠桥栏剑横胸前，低机位跟拍，剑锋特写后拉回全景，[Seedance 2.0] [4K超写实] [35mm胶片质感] [Action sequence consistency]
```
