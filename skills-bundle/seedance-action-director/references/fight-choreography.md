# Fight Choreography & Impact / 打斗设计与打击感（平台安全版）

Read this when an action scene needs to FEEL good (not just be continuous). Goal: maximize visual impact (打击感) through camera, timing, and physical reaction — NOT through blood/gore/violence wording that triggers platform moderation.

> Core formula: 打击感 = 镜头顿帧 + 受击形变 + 速度对比 + 音画卡点 + 环境反馈。
> 打击感 ≠ 血腥暴力. Sell the hit with cinematography and physics, not with gore.

---

## Part 1 — Platform-Safe Principle (先读这条)

AI video platforms reject blood, gore, graphic injury, and tactical-harm wording. So we render impact through SAFE channels:

| 想要的效果 | 安全做法（用） | 危险做法（避） |
|---|---|---|
| 这一击很重 | 受击者踉跄后退、镜头微震、顿帧、尘土飞起 | 喷血、骨裂、伤口特写 |
| 打中了 | 速度骤停、衣料形变、头部轻甩、音效卡点 | 血溅、流血、淤青描写 |
| 很痛/受伤 | 捂处、单膝跪地、呼吸急促、动作变慢 | 伤口、血迹、残肢、痛苦惨叫细节 |
| 激烈对抗 | 攻防节奏、压制感、环境破坏 | 杀戮、虐打、血腥词 |

写提示词时统一加安全尾巴：`无血腥，无伤口特写，无暴力血浆，风格化动作，PG-13 戏剧化呈现，stylized non-graphic action`。

> 原则：**疼痛靠表演和镜头传达，不靠血。** 受击者的反应 (reaction) 比攻击本身更能卖出打击感。

---

## Part 2 — 打击感五要素（Impact = 5 Layers）

### 1. 镜头顿帧 (Hit Stop / Impact Freeze)
命中瞬间，画面极短停顿（0.1-0.2s）再继续，制造"实"的重量感。
```text
提示词：拳触及瞬间画面极短顿帧，随即恢复动态；impact freeze on contact, brief hit-stop then motion resumes
```

### 2. 受击形变 (Hit Reaction / Deformation)
被击者的身体反应是打击感的真正来源：
```text
头部轻甩、上身后仰、肩膀旋转、踉跄半步、单膝触地、扶墙稳住、武器脱手滑出
提示词：opponent's head snaps with momentum, upper body recoils, staggers back half a step, braces against wall
```

### 3. 速度对比 (Speed Contrast)
慢-快-停。蓄力慢、出手快、命中停。匀速 = 没爽感。
```text
提示词：slow wind-up, explosive fast strike, sudden stop on impact, slight slow-motion on the hit frame
```

### 4. 音画卡点 (Audio Sync Beat)
命中点对齐一个声音节拍（闷响/破风声/环境物碎裂声），无需血腥。
```text
提示词：低频闷响与命中帧对齐，破风声在出手时拉满；deep thud synced to impact frame, whoosh on the swing
```

### 5. 环境反馈 (Environmental Response)
打击的力通过环境外化：尘土、水花、碎木、晃动的灯、飘起的布、震落的灰。
```text
提示词：dust bursts on impact, water splashes, loose papers scatter, hanging lamp swings, debris falls
```

---

## Part 3 — 攻防节奏 (Attack / Defense Rhythm)

不要单方面输出。好打斗是**一来一回的对话**：

```text
试探 (probe) → 交火 (exchange) → 压制 (pressure) → 反转 (reversal) → 收招 (resolve)
```

节奏模式：

- **一来一回 (trade)**：A攻 B挡 B反击 A闪 — 对等博弈。
- **压制流 (pressure)**：A连续进攻把B逼到角落 — 用于力量差或反派得势。
- **反击流 (counter)**：B一直防守，抓一个破绽一击反转 — 用于主角逆袭爽点。
- **缠斗 (grapple)**：贴身、夺武器、卡位 — 用于势均力敌的胶着。

每场打斗至少有一次**节奏转折**（被压制→反转），否则平。

---

## Part 4 — 节奏曲线 (Rhythm Curve / 打斗的呼吸)

整场打斗要有起伏，不能从头满到尾：

```text
低(对峙蓄势) → 升(第一次交火) → 短暂回落(拉开距离/喘息) → 高(压制) → 顶点(反转一击) → 收(定格/喘息/收招)
```

- 蓄势和喘息镜头是**必要的留白**，让爽点更爽。
- 顶点那一击给足五要素（顿帧+形变+速度+音画+环境）。
- 收招要有"余韵"：喘息、对视、武器归位、尘埃落定。

---

## Part 5 — 配合镜头感设计 (Impact × Camera)

打击感必须和镜头绑定，不同击打配不同镜头：

| 击打类型 | 镜头设计 |
|---|---|
| 重拳/重击 | 低机位 + 命中顿帧 + 轻微镜头震动(controlled shake) |
| 快速连击 | 中景跟拍 + 速度模糊(motion blur)，命中点短暂清晰 |
| 反转一击 | 命中瞬间切近景或微升格(slow-mo)，强调受击形变 |
| 收招/定格 | 拉远成中景/全景，环境尘埃落定，喘息 |
| 武器交击 | 近景接触点 + 火花/水花，再拉回中景看姿态 |
| 倒地/被逼退 | 跟摇 + 受击者退入背景物(墙/门/桌) |

镜头铁律（沿用 action-shot-patterns）：每15秒最多1-2个主运镜；顿帧/升格只给顶点击，不滥用。

---

## Part 6 — 受击反馈提示词模板 (copyable)

```text
[出手]角色A蓄力后爆发出拳，速度骤起；
[命中]触及瞬间画面极短顿帧，低频闷响卡点；
[反馈]角色B头部随冲击轻甩、上身后仰、踉跄后退半步撞到木桌，桌上灰尘震起；
[镜头]低机位中景，命中瞬间轻微镜头震动后回稳；
[安全]无血腥无伤口特写，风格化非写实动作，PG-13戏剧化呈现，stylized non-graphic action。
```

---

## Common Mistakes

- 只写攻击不写受击反应 → 打击感全失（reaction 才是关键）。
- 匀速动作 → 没有速度对比就没有"打中"的瞬间。
- 滥用慢动作 → 升格只留给顶点击，否则廉价。
- 靠血浆找刺激 → 平台直接拒，且低级；用顿帧+形变+环境更高级也更安全。
- 从头打到尾一个力度 → 缺节奏曲线，观众疲劳。
- 镜头乱晃当激烈 → handheld 要可控，脸和动作得看得清。
