---
name: ip-image-skill
description: "Generate IP visual assets, split grid images into single tiles, and enhance each tile without overwriting the source image. Use this skill when an agent needs text-to-image generation, multi-grid splitting, or image-to-image enhancement while keeping composition stable. The provider is configurable through environment variables, so users can switch API channels without changing the workflow code."
---

# IP Image Skill

## When To Use

- Generate IP character, scene, or merchandise images from text
- Create characters and visual assets from novel or copy input
- Iteratively refine a single image through conversational interaction
- Generate a consistent starter asset bundle for one locked character
- Generate multi-character IP asset packs with clean character sheets, props, 720 panorama scene assets, and normal video scene references
- Generate storyboard content design sheets from video handoff tasks
- Split a 4 / 9 / 16 grid image into single images
- Enhance an existing image or split tiles while keeping the source file untouched

## Tool Boundaries

- Allowed:
  - Remote image generation API calls
  - Local image splitting
  - Local file download and output writing
- Forbidden:
  - Overwriting the user's source image
  - Hiding provider errors
  - Hardcoding secrets in code

## Language Defaults

- Character design sheets default to Simplified Chinese visible text (`visual_text_language=zh-CN`).
- Use Chinese headings and labels for character name, role, age, personality, aura, world context, props, color palette, and back view.
- Translate prop names and prop use notes into natural Chinese when source fields are English.
- Use English or another language only when the user or task explicitly sets `visual_text_language` / `visible_text_requirements`.

## Core Flows

### Flow A: Text To Image

1. Load provider config from environment variables
2. Build the prompt from style card + task fields
3. Submit generation task
4. Poll task status until `finished` or `failed`
5. Download the result into `output_dir`

Supported Flow A task styles:

- Direct prompt generation
- Novel or copy driven character creation
- Interactive single-image refinement with structured conversation cues
- Structured `character_create` tasks built from a reusable character sheet
- Structured `character_asset_bundle` tasks that expand one character sheet into multiple asset outputs
- Structured `ip_asset_pack` tasks that expand multiple characters, props, and scenes into production assets
- Structured `storyboard_content_design_sheet` tasks from video `storyboard_image_tasks`

### Flow C: Single Image Conversational Refinement

1. Load an existing local image
2. Build the refinement prompt from style card + interaction notes + conversation turns
3. Upload the source image
4. Submit a single-image edit task
5. Download the refined result into `output_dir`

### Flow D: Character Asset Bundle

1. Load one locked character sheet
2. Expand `asset_bundle` into multiple child character-create tasks
3. Generate each bundle item with the same identity anchors and continuity rules
4. Return all artifacts together for downstream use

Character identity must be defined by face geometry, not only hair and clothing. For production characters, include these fields under `character_profile.appearance`:

- `facial_proportions`: 三庭五眼、眼距、鼻口距离、下庭长短
- `face_shape`: 脸型、下颌线、下巴
- `brow_shape`: 眉型、眉峰、眉距
- `eye_shape`: 眼型、眼尾、眼窝、眼神
- `nose_shape`, `nose_bridge`, `nose_tip`: 鼻梁、鼻头、鼻翼
- `mouth_shape`, `lip_shape`: 口型、唇峰、唇厚薄、嘴角
- `cheekbones`, `facial_marks`: 颧骨、法令区、疤痕、痣、肤质特征

Preserve these fields in role cards, design sheets, keyframes, and video prompts.

### Flow E: IP Asset Pack

1. Load a structured list of characters, props, and scenes
2. Generate character assets as clean design sheets with plain backgrounds, not story-scene images
3. Include key props beside the matching character where useful
4. Generate scene assets as wide 720-style panorama references with seamless left-right edge instructions
5. Also generate a normal perspective `video_scene_reference` for video pipelines, keeping stable entrances, landmarks, light direction, and foreground/midground/background layers
6. Return the full asset pack for downstream image and video workflows

### Flow F: Storyboard Content Design Sheet

1. Load a `storyboard_image_tasks` item from `ip-video-skill`.
2. Generate either a 3-panel clip storyboard design sheet (start state, main action beat, end state) or a shot-table storyboard sheet when `asset_kind=shot_table_storyboard`.
3. Keep character, costume, props, scene layout, light direction, and palette consistent with the continuity bible.
4. Keep Chinese production labels short and outside the image panels.
5. Do not create dialogue subtitles, title cards, watermarks, fake UI, or decorative text inside panels.

For `shot_table_storyboard`, generate a production storyboard board, not loose keyframes:

- Use one complete landscape board image with clean table/grid layout.
- Include 3-5 shot rows unless the task explicitly requests another count.
- Keep columns such as shot number, picture/composition, camera movement, action/performance, dialogue/sound, and timing.
- Use grayscale manga line art or sketch panels only when requested; keep labels outside panel drawings.
- Preserve character and scene continuity from the task, but remember storyboard sheets are layout/planning assets only. Do not treat them as final identity references for live video.

### Flow B: Grid Split And Enhance

1. Load a local grid image
2. Split into regular tiles
3. Upload each tile to the provider
4. Submit image edit tasks for enhancement
5. Download enhanced results into `output_dir`
6. Keep the original grid and split tiles unchanged

## References

- `references/provider_poyo.md`: provider-specific API notes
- `references/ip_style_card_template.md`: IP style card template
- `references/style_presets/`: built-in visual style presets for common IP workflows
- `references/style_cards/`: concrete style card examples
- `assets/enhance_presets.json`: enhancement presets

## Scripts

- `scripts/config.py`: environment-driven config
- `scripts/poyo_client.py`: PoYo provider adapter
- `scripts/split_grid.py`: deterministic grid splitting
- `scripts/prompt_builder.py`: optional IP style-card prompt assembly
- `scripts/asset_pack.py`: multi-character asset pack expansion
- `scripts/character_sheet.py`: reusable character-sheet helper for interactive role creation
- `scripts/character_state.py`: deterministic turn-by-turn state update helper
- `scripts/doctor.py`: local configuration self-check
- `scripts/image_skill.py`: agent-facing task entrypoint

## Installation And Configuration

Install this skill directory where the host agent can read `SKILL.md`, `scripts/`, `assets/`, and `references/`.
The host agent must be able to run Python and call either:

- Agent module usage: `run_task(task_dict)` from `scripts/image_skill.py`
- JSON task usage: `python image_skill.py --task path/to/task.json`

Required environment variables for live generation:

- `IMAGE_PROVIDER=poyo`
- `IMAGE_API_KEY`: provider API key, never hardcoded
- `IMAGE_API_BASE=https://api.poyo.ai`
- `IMAGE_GEN_MODEL=gpt-image-2`
- `IMAGE_EDIT_MODEL=gpt-image-2-edit`
- `IMAGE_OUTPUT_ROOT`: output directory for generated files

Optional runtime tuning:

- `IMAGE_POLL_INTERVAL_SEC`
- `IMAGE_POLL_TIMEOUT_SEC`

## Invocation

- Agent module usage: call `run_task(task_dict)` from `scripts/image_skill.py`
- JSON task usage: `python image_skill.py --task path/to/task.json`

## Task Direction

Recommended task fields for richer image creation:

- `style_preset`
- `style_card_path`
- `style_reference_paths`
- `reference_image_urls`
- `asset_kind`
- `storyboard_profile`
- `creative_goal`
- `character_name`
- `character_brief`
- `source_text`
- `appearance_traits`
- `character_profile`
- `characters`
- `identity_anchors`
- `continuity_rules`
- `continuity_state`
- `reference_binding`
- `video_reference_images`
- `space_anchor_refs`
- `asset_target`
- `interaction_state`
- `asset_bundle`
- `props`
- `standalone_props`
- `scenes`
- `scene_profile`
- `prop_profile`
- `gpt_image_2_spec`
- `visual_text_language`
- `visible_text_requirements`
- `scene`
- `emotion`
- `pose`
- `camera`
- `composition`
- `lighting`
- `interaction_notes`
- `conversation_turns`
- `src_path`
- `refine_level`
- `preserve_identity`
