# Continuity QA Checklist / 连续性质检清单

Read this when running QA / Reverse Review mode, or before delivering a multi-segment package. Catch drift and continuity breaks before generation wastes credits.

> Output format per issue: **问题** → **严重度 (high/medium/low)** → **为什么会跑偏** → **精确替换措辞**.

---

## Checklist

### 1. 脸漂 (Face Drift)
- Same face shape, eyebrows, eyes, nose, lips across all segments?
- Age impression stable (no sudden younger/older)?
- Hairstyle & color consistent?
- **Fix**: repeat exact face/age/hair lock line in every prompt; forbid face swap/aging.

### 2. 衣服变 (Costume Drift)
- Same outfit silhouette/material/color unless script changes it?
- No new accessories appearing/disappearing?
- **Fix**: restate costume lock + `禁止新增服饰/配饰`.

### 3. 道具凭空出现/消失 (Prop Pop / Vanish)
- Props only appear when script introduces them?
- Prop state consistent (a torn letter stays torn)?
- Hand holding the prop consistent?
- **Fix**: restate prop state + hand position; `禁止新增道具`.

### 4. 段落衔接 (Segment Handoff)
- Current segment start pose == previous segment end pose?
- Spatial position continuous (not teleporting across the room)?
- **Fix**: copy previous end state verbatim into current start state.

### 5. 情绪断层 (Emotional Break)
- Emotional arc continuous across segments (no sudden calm→rage with no trigger)?
- Each shift has a visible trigger?
- **Fix**: insert/clarify the trigger; describe leak behavior, not abstract emotion.

### 6. 镜头乱跳 (Camera Chaos)
- Not every segment using push/pull/pan?
- Shot sizes varied meaningfully, not random?
- 180-degree / eyeline consistency in two-handers?
- **Fix**: limit to one main movement per 15s; assign shot grammar by section.

### 7. 台词塞太满 (Overstuffed Dialogue/Action)
- Each 15s has at most one main action + breathing room?
- Dialogue fits naturally in 15s at human pace?
- **Fix**: split into more segments or cut lines; add pauses.

### 8. 场景/光影漂移 (Scene/Light Drift)
- Same location layout and background?
- Light direction and color mood stable within a scene?
- **Fix**: restate scene layout + light direction/color.

### 9. 阵营/关系逻辑 (Faction/Relationship Logic)
- Roles' attitudes consistent with the relationship map?
- No random added companions/enemies/crowds?
- **Fix**: reference relationship map; `禁止新增无关人物`.

### 10. 模型易误读措辞 (Model-Misreadable Wording)
- Any vague metaphor the model can't render ("眼神里有故事")?
- Any contradictory instruction in one prompt?
- **Fix**: convert to concrete visible behavior; remove contradictions.

---

## Severity Guide

- **high**: breaks character identity or story logic (face swap, faction flip, teleport). Must fix before generating.
- **medium**: noticeable but recoverable (costume detail, prop state, camera repetition).
- **low**: polish (subtitle timing, minor ambient sound).

## Quick Pass/Fail Gate

Reject the batch if ANY high-severity issue exists. Otherwise list medium/low fixes and proceed.
