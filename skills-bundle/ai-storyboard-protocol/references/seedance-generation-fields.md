# Seedance Generation Fields / Seedance字段规范

Read this when emitting the `【Seedance字段】` block of each card. Standardizes the prompt, negative constraints, and retry rules so dialogue and action cards both feed Seedance 2.0 cleanly.

---

## Field Spec (每张卡的 Seedance 块)

```markdown
- **中文提示词**：[场景][角色+屏幕方向+锁定特征][起始→动作→结束][镜头][环境/光][画质标签]
- **English prompt**：同结构英文版（i2v 友好）
- **负面约束**：从 negative bank 取相关项
- **失败重抽建议**：只针对失败维度，不整段重写
```

提示词写作顺序（固定）：

```text
环境/场景 → 角色与屏幕方向 → 锁定特征(脸/衣/道具) → 起始姿态 → 动作转化 → 结束姿态 → 镜头语言 → 光影 → 画质标签
```

## 画质标签 (通用尾部)

```text
[Seedance 2.0] [4K超写实] [35mm胶片质感] [Sequence consistency]
```
动作戏追加：`[Action sequence consistency]`
对白戏追加：`[Subtle performance] [Natural lighting]`

---

## Negative Constraint Bank（按需取）

通用：
```text
无AI磨皮，无塑胶感，无卡通特效，无肢体畸形，无多手指，无脸部扭曲
```
连续性：
```text
无越轴，无屏幕方向翻转，无站位瞬移，无视线错位
```
角色一致性：
```text
无换脸，无年龄漂移，无发型变化，无服装变色
```
动作：
```text
无武器凭空出现，无瞬移，无穿模，无重力错误
```
表演：
```text
无表情夸张，无口型错乱，无情绪跳变
```
道具/场景：
```text
无新增道具，无新增人物，无环境重置，无光线方向跳变
```

---

## Failed-Regeneration Rules（只修失败维度）

| 失败现象 | 重抽措辞 |
|---|---|
| 脸漂 | 强化"same face, same age, same hairstyle, lock face_id" |
| 服装变 | 重复服装款式/材质/颜色 + 禁新增配饰 |
| 道具乱 | 重复道具状态+手部接触位置 |
| 场景漂 | 重复布局/背景/光线方向 |
| 越轴/方向乱 | 重申屏幕方向+轴线一侧+视线互补 |
| 视线同向 | 明确"A朝右看B，B朝左看A，互补对视" |
| 情绪跳 | 改写可见行为(呼吸/眼神/手)，不写抽象情绪 |
| 镜头乱 | 减运镜，指定单一镜头语法 |
| 站位瞬移 | 复制上镜结束态作为本镜起始态 |
| 动作崩 | 拆成 起始→动作→结束 三段，限一个主动作 |

> 原则：失败时只改对应那一格，别整段重写，否则引入新漂移。

---

## Batch Output Rule

长视频（如10分钟/40节点）：先出宏观计划 + Batch 1，逐批推进，除非用户明确要全量。每批携带：上批结束态、延续的锁定项、本批提示词、重抽规则。
