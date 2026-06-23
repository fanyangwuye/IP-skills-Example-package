---
name: ip-video-skill
description: "Build continuity-locked video handoffs for IP adaptation workflows. Use this skill when an agent needs a continuity bible, shot plan, image-to-video prompts, text-to-video prompts, or an edit decision list from scripts, blueprints, image asset packs, or music handoffs before calling a video model such as Seedance, Jimeng, Kling, or PoYo video."
---

# IP Video Skill

## Scope

Build the offline video structure layer for IP workflows:

- `build_continuity_bible`: lock characters, costumes, props, scenes, lighting, style, and reference roles.
- `build_video_handoff`: turn `blueprint`, `polished_script`, `ip_asset_pack`, `image_handoff`, and `music_handoff` into executable video tasks.
- `build_shot_plan`: create continuity-aware storyboard cards.
- `build_clip_plan`: group shots into 5-15 second continuity clips so generation is not split into too many tiny fragments.
- `storyboard_image_tasks`: create image-generation tasks for clip-level storyboard boards, shot-table storyboards, and martial-arts action breakdown boards that share first/mid/last frame specs with video generation.
- `martial_arts_layer`: enhance martial-arts/action clips with readable combat beats, distance, footwork, weight shift, impact feedback, and safe visual constraints.
- `build_i2v_prompts`: create image-to-video prompts from locked references.
- `build_t2v_prompts`: create text-to-video prompts when no usable image reference exists.
- `seedance_prompts`: create timed Chinese prompts with performance, camera, light, sound, realism, and retry guidance.
- `build_edit_decision_list`: create a first-pass EDL for later assembly.
- `prepare_video_generation`: convert one locked clip or shot into a provider-specific request without calling the provider.
- `run_video_generation`: dry-run provider execution; live provider calls are intentionally blocked until an adapter is implemented and verified.

This phase is local only by default. Do not call live video APIs unless a provider adapter explicitly implements and tests that provider.

## Continuity First

Always build or load a `continuity_bible` before writing shot prompts. Each shot must carry:

- `visual_lock`: face, hair, body temperament, costume, props, scene, lighting, palette.
- `continuity_state`: previous end state, current start state, current end state, next handoff.
- `reference_binding`: which reference locks are used for face, costume, scene, props, and style.

For 2+ characters, each shot must also include:

- `axis`
- `screen_direction`
- `eyeline`
- `blocking_distance`

Do not write isolated video prompts that can drift across shots.

## Mandatory Storyboard Execution Gate

Storyboard is the execution blueprint, not optional inspiration. Once a storyboard, shot table, or manga-line board exists, every generated video clip must carry `storyboard_execution_map`.

- Every clip-level provider request must map `video shot 1 = storyboard shot_xxx`, `video shot 2 = storyboard shot_xxx`, and so on.
- Do not delete, merge away, reorder, or rewrite storyboard shots just to make a 15-second generation easier.
- If a 15-second clip cannot accurately execute all included storyboard shots, split it into shorter generated units instead of changing the storyboard.
- Storyboard refs lock shot design, composition, blocking, action phase, screen direction, and edit order; character identity still comes from the locked reference policy.
- Prompt text may only strengthen existing reference and storyboard details. It must not add, modify, or reduce the content established by the references and storyboard.
- For paid/live clip generation, stop if `storyboard_execution_map` is missing or does not exactly match the clip `shot_ids`.

## Mandatory Video Continuation Gate

Before proposing or preparing any multi-clip video workflow, read `references/workflows.md` and inspect the relevant provider/clip fields in `scripts/clip_plan.py` and `scripts/video_provider.py`. Do not reduce continuity to "use the previous clip tail frame as the next clip first frame." For every clip boundary, explicitly choose one continuation mode:

- `hard_first_frame`: use the previous clip final frame as the next clip's true first-frame input when the same action, space, camera side, and subject scale should continue directly.
- `previous_reference_reframe`: use the previous clip tail frame or another reviewed frame only as a continuity reference for color, light, costume, prop hand, character state, and action momentum; then rebuild the next composition as a new wide, full, medium, close, close-up, reverse, back-view, insert, or cutaway shot.
- `bridge_cutaway`: split off a face-light bridge clip, such as environment, prop, hand, sleeve, shadow, floor reflection, door movement, dust, wind, or light shift, to mask a planned camera/scale/axis change.
- `sound_bridge_or_hard_cut`: use sound, ambience, or a deliberate hard cut when the story moves to a different location or time state and visual tail-frame continuation would be misleading.

Each boundary decision must state why that mode is being used and which frame or reference carries the handoff. Storyboard boards and panel crops are layout references only; character identity must come from the project locked reference policy. If `reference_policy: all_purpose_reference` is set, character-bearing clips must use `reference_image_urls` as all-purpose references and must not be rewritten into `image_urls`, first-frame, last-frame, previous-tail-frame, or keyframe I2V.

Single-frame extraction is only a clip-to-clip continuity aid. It may inform light, color, action momentum, screen direction, character state, and emotional residue at a boundary, but it must not become a character identity lock, a default first-frame input, or a replacement for all-purpose references.

## Locked Reference Policy Gate

For any paid/live clip that contains named or locked characters, obey the project reference policy exactly. Do not silently substitute one reference mode for another.

- If `reference_policy: all_purpose_reference` is set, the provider request must use `reference_image_urls` only. Do not add `image_urls`, do not use first-frame or last-frame inputs, do not map `previous_clip_end_frame` into the first-frame slot, and do not regenerate a keyframe just to satisfy an older I2V habit.
- In all-purpose reference mode, character references lock identity, scene references lock space, and storyboard references lock shot design, composition, blocking, action phase, screen direction, and edit order. The prompt must explicitly bind every `@Image` role.
- Storyboard boards and panel crops remain layout references only. Do not copy line-art style, table borders, labels, arrows, captions, handwritten marks, or sketch texture into final video.
- Use `image_urls[0]` first-frame/keyframe only when the project explicitly selects first-frame/keyframe I2V. Never substitute first/last frames for all-purpose reference.
- If face, hairstyle, costume, screen direction, or story action drifts, stop live generation and fix the reference binding or shot prompt before spending another video call.

For actual video generation, prefer clip-level generation over tiny shot-level generation:

- Keep `shots` for storyboard, subtitles, and edit checks.
- Use `clip_plan` for provider calls; each clip should usually be 5-15 seconds and may contain multiple shots.
- Preserve panorama scene images as `space_anchor_refs` for spatial overview and human consistency checks.
- Use normal perspective scene references as `video_reference_images` for model input.
- Generate professional storyboard boards when visual planning is needed; each board should map to real clip keyframes and carry `first_frame_spec`, `mid_frame_spec`, and `last_frame_spec`.
- The first storyboard panel must match the intended video first frame: same composition, camera height, camera angle, subject scale, screen direction, scene anchors, and light direction.
- Supported storyboard asset kinds are `clip_storyboard_board`, `shot_table_storyboard`, and `martial_action_storyboard`.
- After generating a storyboard board, pass `storyboard_image_path` or `storyboard_image_paths` into `prepare_video_generation` / `run_video_generation`; the provider layer will crop first/mid/last panels into layout references automatically.
- Storyboard panel crops are composition references only. They lock framing, camera angle, subject scale, blocking, pose phase, screen direction, and scene anchors; they must not copy line-art style, table borders, labels, arrows, handwritten marks, or storyboard text into the generated video.
- For shot-table or manga-line storyboard sheets, treat the sheet as a planning board, not the final video style. The generated video must not inherit table grids, labels, sketch texture, line-art style, captions, arrows, or handwritten marks.
- For martial-arts clips, keep the action readable: starting stance, distance, one attack-defense beat, reaction pause, and ending pose. Do not hide action with chaotic camera motion.
- Test real IP video with image-to-video only after generating character and scene reference images; text-to-video is only useful for provider connectivity checks, not IP consistency.
- For clip 2+, pass the previous clip tail frame only when the selected continuation mode requires it. If `reference_policy: all_purpose_reference` is locked, do not map any previous tail frame into `image_urls`; carry continuity in the prompt and allowed all-purpose references instead.
- Do not discard panorama assets; they remain useful for layout, landmark, and light-direction anchoring.
- Keep generated video audio limited to ambient sound and foley. Forbid background music, songs, music beds, on-screen subtitles, fake text, title cards, and watermarks in video prompts.

## Inputs

Accept any combination of:

- `blueprint`
- `polished_script`
- `script_draft`
- `scene_cards`
- `ip_asset_pack`
- `image_handoff`
- `music_handoff`
- `continuity_bible`

Prefer `blueprint.segments` for timing. Fall back to `polished_script.scenes`, `script_draft.scenes`, then `scene_cards`.

## Invocation

- Agent module usage: call `run_task(task_dict)` from `scripts/video_skill.py`
- JSON task usage: `python video_skill.py --task path/to/task.json`

Example:

```python
from video_skill import run_task

result = run_task({
    "mode": "build_video_handoff",
    "blueprint": blueprint,
    "ip_asset_pack": ip_asset_pack,
    "music_handoff": music_handoff,
    "output_dir": "./outputs/video"
})
```

## Output Contract

`build_video_handoff` returns:

- `source_title`
- `continuity_bible`
- `shots`
- `clip_plan`
- `storyboard_image_tasks`
- `i2v_prompts`
- `t2v_prompts`
- `seedance_prompts`
- `clip_prompts`
- `edit_decision_list`
- `quality_checks`

Every shot and clip is safe to pass to a provider adapter later because continuity is already explicit.

## Provider Layer

`provider` means the concrete video service adapter. Examples:

- `offline` / `dry_run`: prepare requests only; no external call.
- `dreamina_cli`: prepare a CLI-shaped request for the official Dreamina/即梦 `dreamina` command.
- `jimeng_cli`: compatibility alias for `dreamina_cli`.
- `poyo_video`: submit Seedance 2 / Seedance 2 Fast video tasks through PoYo, poll task status, and download returned files when `dry_run=false`.

Use `prepare_video_generation` to inspect a single-shot or single-clip provider request before spending credits. Prefer `clip_index` for normal video generation and `shot_index` for troubleshooting. Provider requests preserve:

- prompt
- negative prompt
- reference images
- video reference images
- space anchor refs
- previous clip end frame
- first frame spec, mid frame spec, and last frame spec
- storyboard panel layout references when available
- reference binding
- continuity state
- visual lock
- axis, screen direction, and eyeline
- retry advice

Environment variables:

- `VIDEO_PROVIDER=offline|dry_run|dreamina_cli|jimeng_cli|poyo_video`
- `VIDEO_API_KEY`
- `VIDEO_API_BASE`
- `VIDEO_OUTPUT_ROOT`
- `VIDEO_DEFAULT_MODEL`
- `VIDEO_DEFAULT_ASPECT_RATIO=9:16`
- `VIDEO_DEFAULT_RESOLUTION=480p`
- `VIDEO_POLL_INTERVAL_SEC=4`
- `VIDEO_POLL_TIMEOUT_SEC=600`

Default video resolution is `480p` to keep test clips low-cost. Raise to `720p` only when a clearer review clip is needed.

## Resources

- `scripts/continuity.py`: continuity bible builder
- `scripts/shot_plan.py`: shot/storyboard/prompt builder
- `scripts/clip_plan.py`: clip grouping, clip prompts, video reference images, space anchors, and previous-frame handoff
- `scripts/storyboard_assets.py`: clip-level storyboard design sheet image task builder
- `scripts/storyboard_panel_refs.py`: local first/mid/last storyboard panel cropper for provider layout references
- `scripts/martial_arts.py`: martial-arts scene detector and combat prompt layer
- `scripts/prompt_quality.py`: prompt quality layers for performance, camera, light, sound, realism, constraints, and retry advice
- `scripts/video_provider.py`: provider request builder and dry-run execution boundary
- `scripts/poyo_video_client.py`: PoYo Seedance 2 submit, status polling, upload, and download client
- `scripts/video_handoff.py`: handoff and EDL builder
- `scripts/video_skill.py`: agent-facing task entrypoint
- `scripts/ffmpeg_assembly.py`: phase-3 placeholder for local assembly helpers
- `references/workflows.md`: provider-agnostic workflow and consistency rules
- `assets/example_build_video_handoff_task.json`: offline example
- `assets/example_prepare_video_generation_task.json`: single-shot provider request example
