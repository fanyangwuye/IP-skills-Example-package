# Continuity Examples / 动作连续性示例

Use this reference when building multi-node action scenes, especially 1-5 minute sequences where each 15-second node must physically continue from the previous one.

## Core Continuity Chain

Every node should preserve this chain:

```text
previous end state → current start state → action transformation → current end state → next start instruction
```

If the chain breaks, the video will feel like unrelated clips glued together.

## Required Continuity Anchors

Track at least these anchors:

1. **Body position**: standing, crouching, kneeling, falling, rolling, back against wall.
2. **Facing direction**: facing camera, facing opponent, back to door, left side toward enemy.
3. **Spatial relation**: distance between characters, who is higher/lower, near which object.
4. **Weapon / prop state**: blade low/high, gun holstered/dropped, staff broken, shield raised.
5. **Costume / damage state**: wet robe, torn sleeve, dust on coat, bloodless scratch mark if stylistic.
6. **Environment state**: broken table, open door, rain intensity, scattered papers, smoke position.
7. **Emotional/action tempo**: calm standoff, defensive retreat, sudden counterattack, exhausted recovery.

## Example A: Wuxia Duel, 3 Nodes

### Node 1 End State

```text
女侠背靠石桥栏杆，右手长剑横在胸前，黑衣人站在三米外，雨水从剑尖滴落。
```

### Node 2 Start State

Must match:

```text
从“女侠背靠石桥栏杆，剑横胸前，黑衣人三米外”开始。
```

Node 2 action:

```text
黑衣人压步前冲，女侠借桥栏反蹬跃起半身高度，剑从胸前横挡变成向下斜切，逼迫黑衣人低头闪避。
```

Node 2 End State:

```text
女侠落到桥中央，左脚前踏，剑尖斜指地面；黑衣人半跪在桥栏旁。
```

### Node 3 Start State

Must match:

```text
从“女侠落在桥中央，左脚前踏，剑尖斜指地面；黑衣人半跪桥栏旁”开始。
```

Bad continuation:

```text
女侠突然出现在屋顶上。
```

Why bad: teleport, environment reset, body state broken.

## Example B: Modern Alley Chase, 4 Nodes

### Node 1 End

```text
男主冲到狭窄巷口，前方是一辆倒地自行车，追兵距离他约五米。
```

### Node 2 Start

```text
从“男主在狭窄巷口，自行车挡在前方，追兵五米外”开始。
```

### Node 2 End

```text
男主越过自行车后滑到铁门前，右手抓住门把，发现门锁住。
```

### Node 3 Start

```text
从“男主右手抓住锁住的铁门门把，追兵逼近”开始。
```

### Node 3 End

```text
男主侧身钻进铁门旁半开的窄窗，外套被窗框勾住，追兵扑空撞到铁门。
```

### Node 4 Start

```text
从“男主半个身体钻过窄窗，外套被窗框勾住，追兵撞到铁门”开始。
```

## Common Continuity Bugs

### 1. Weapon Teleport

Bad:

```text
节点1结束：角色双手空着。
节点2开始：角色挥舞长枪。
```

Fix:

```text
节点1结束必须交代长枪靠在墙边，节点2开始角色伸手抓起长枪。
```

### 2. Environment Reset

Bad:

```text
节点1桌子被打碎。
节点2桌子完好无损。
```

Fix:

```text
节点2继续保留碎桌板、散落木屑和角色绕过障碍。
```

### 3. Costume Drift

Bad:

```text
湿黑风衣突然变成白色长袍。
```

Fix:

```text
每个节点提示词重复：same wet black coat, same torn left sleeve, no costume change.
```

### 4. Direction Confusion

Bad:

```text
上一节点敌人在左侧，下一节点没有交代就从右侧攻击。
```

Fix:

```text
写清楚敌人绕到右侧，或保持从左侧压迫。
```

## Continuity QA Checklist

Before final output, check:

- Does every node start from the previous node's exact end state?
- Are weapon positions consistent?
- Are character distances and directions trackable?
- Does the environment keep damage/water/dust/debris states?
- Are new props/enemies introduced intentionally?
- Does each node have one primary action idea?
- Does each node end with a usable next-node starting pose?
