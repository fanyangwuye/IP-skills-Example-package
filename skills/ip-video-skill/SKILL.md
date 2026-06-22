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
- `build_i2v_prompts`: create image-to-video prompts from locked references.
- `build_t2v_prompts`: create text-to-video prompts when no usable image reference exists.
- `seedance_prompts`: create timed Chinese prompts with performance, camera, light, sound, realism, and retry guidance.
- `build_edit_decision_list`: create a first-pass EDL for later assembly.
- `prepare_video_generation`: convert one locked shot into a provider-specific request without calling the provider.
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
- `i2v_prompts`
- `t2v_prompts`
- `seedance_prompts`
- `edit_decision_list`
- `quality_checks`

Every shot is safe to pass to a provider adapter later because continuity is already explicit.

## Provider Layer

`provider` means the concrete video service adapter. Examples:

- `offline` / `dry_run`: prepare requests only; no external call.
- `dreamina_cli`: prepare a CLI-shaped request for the official Dreamina/即梦 `dreamina` command.
- `jimeng_cli`: compatibility alias for `dreamina_cli`.
- `poyo_video`: submit Seedance 2 / Seedance 2 Fast video tasks through PoYo, poll task status, and download returned files when `dry_run=false`.

Use `prepare_video_generation` to inspect a single-shot provider request before spending credits. Provider requests preserve:

- prompt
- negative prompt
- reference images
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
- `VIDEO_DEFAULT_RESOLUTION=1080p`
- `VIDEO_POLL_INTERVAL_SEC=4`
- `VIDEO_POLL_TIMEOUT_SEC=600`

## Resources

- `scripts/continuity.py`: continuity bible builder
- `scripts/shot_plan.py`: shot/storyboard/prompt builder
- `scripts/prompt_quality.py`: prompt quality layers for performance, camera, light, sound, realism, constraints, and retry advice
- `scripts/video_provider.py`: provider request builder and dry-run execution boundary
- `scripts/poyo_video_client.py`: PoYo Seedance 2 submit, status polling, upload, and download client
- `scripts/video_handoff.py`: handoff and EDL builder
- `scripts/video_skill.py`: agent-facing task entrypoint
- `scripts/ffmpeg_assembly.py`: phase-3 placeholder for local assembly helpers
- `references/workflows.md`: provider-agnostic workflow and consistency rules
- `assets/example_build_video_handoff_task.json`: offline example
- `assets/example_prepare_video_generation_task.json`: single-shot provider request example
