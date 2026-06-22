# Reference Image Binding / 参考图绑定规则

Read this when the user uploads or describes reference images, to decide what to lock and what to forbid. Goal: stop the model from cross-contaminating attributes (e.g. copying a costume model's face, or a scene reference's random bystanders).

> Core rule: each reference contributes ONLY its intended attribute. Everything else from that image is forbidden noise.

---

## Reference Type → Lock / Forbid

### 1. 角色参考图 (Character reference) — 锁脸

- **Lock**: face shape, eyebrows, eyes, nose, lips, hairstyle & color, age impression, body temperament/气质.
- **Forbid**: copying that image's clothing, background, lighting, pose, or props unless explicitly told to.
- **"只参考脸/五官/气质" rule**: if user says this, you MUST redesign costume/scene/lighting freshly while preserving only the locked facial + temperament traits. State this explicitly at the top of the prompt.

### 2. 服装参考图 (Costume reference) — 锁衣服

- **Lock**: silhouette, material, color, key details (collar, buttons, accessories that are part of the outfit).
- **Forbid**: copying the costume model's face, body, hairstyle, or pose. Never let the costume image's face leak into the character.

### 3. 场景参考图 (Scene reference) — 锁场景

- **Lock**: location layout, spatial relationship, background elements, light direction, color mood.
- **Forbid**: copying any people/bystanders in the scene image, unrelated props, or text/logos.

### 4. 道具参考图 (Prop reference) — 锁道具

- **Lock**: prop shape, material, size, color, current state (new/worn/broken/bloody).
- **Forbid**: adding extra props, changing prop state mid-sequence, copying the prop image's environment.

### 5. 风格参考图 (Style reference) — 锁风格

- **Lock**: mood, lens feel, color grade, grain/texture, contrast.
- **Forbid**: copying literal content (the actual person/object/scene shown). Style only, not subject.

---

## Multi-Reference Conflict Resolution

When several references are uploaded together:

1. **Assign each one role first** — declare in output: "图A=角色锁脸, 图B=服装, 图C=场景, 图D=风格".
2. **Resolve overlaps explicitly** — if character image and costume image disagree on clothing, costume image wins for clothing, character image wins for face.
3. **Forbid bleed** — write a line in every prompt: "Use 图A only for face/temperament, do not copy 图A clothing/background."

---

## Anti Cross-Contamination Lines (paste into prompts)

- `参考图仅用于锁定 [脸型/五官/气质]，不复制其服装、发型以外细节、背景、姿势、光线。`
- `服装参考仅锁定款式/材质/颜色，不复制该图人物的脸或身材。`
- `场景参考仅锁定空间布局与光线，不复制画面中任何人物或多余道具。`
- `风格参考仅锁定色调/质感/镜头感，不复制其具体内容。`

---

## Verification Before Generation

Confirm the lock table answers:

- Whose face? (one source only)
- Whose clothes? (fixed or redesigned)
- Which scene layout?
- Which props and what state?
- Which style mood?
- What is explicitly forbidden to copy?

If any answer is ambiguous and blocking, ask once; otherwise pick the safest interpretation and label it 合理推断.
