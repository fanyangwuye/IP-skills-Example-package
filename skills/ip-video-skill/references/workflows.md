# IP Video Skill Workflows

## Flow A: Continuity Bible

1. Read `ip_asset_pack`, `image_handoff`, `blueprint`, or `polished_script`.
2. Build `character_locks` for face, hair, body temperament, costume, palette, and props.
3. Build `scene_locks` for layout, landmarks, lighting, atmosphere, and panorama constraints.
4. Build `global_visual_lock` for lens language, tone, color grade, and forbidden drift.

Use this before any prompt writing.

## Flow B: Video Handoff

1. Prefer `blueprint.segments` for timing and scene order.
2. Fall back to `polished_script.scenes`, `script_draft.scenes`, then `scene_cards`.
3. Create one shot per segment for storyboard, subtitles, and edit checking.
4. Carry `previous_end_state -> current_start_state -> current_end_state` through every shot.
5. Group shots into `clip_plan` entries, usually 5-15 seconds each, so video generation is not split into too many tiny fragments.
6. Keep panorama scene images in `space_anchor_refs` for spatial overview; use normal perspective scene images in `video_reference_images` for model generation.
7. Create `storyboard_image_tasks` when clip-level visual planning images are needed.
8. Create `i2v_prompt`, `t2v_prompt`, `seedance_prompt`, and `clip_prompts`.
9. Create an EDL for later ffmpeg/provider assembly.

## Storyboard Content Design Sheets

- Use character design sheets to lock identity and normal scene references to lock the environment.
- Generate one storyboard content design sheet per clip when the user wants visual planning before video generation.
- Each sheet should contain three panels: start state, main action beat, end state.
- Keep production labels short, Chinese by default, and outside panel image areas.
- Do not put dialogue subtitles, title cards, fake UI, decorative text, or watermarks inside panels.
- Treat storyboard sheets as planning references, not final video frames.

## Martial-Arts Enhancement

- Trigger this layer when a clip clearly contains martial-arts language such as 武戏, 武侠, 剑, 刀光, 拔刀, 格挡, 轻功, 招式, 交手, or 缠斗.
- Structure the action as: starting stance -> clear distance -> one attack-defense beat -> reaction pause -> ending pose.
- Make footwork, body weight shift, weapon/limb path, and opponent reaction visible.
- Prefer stable wide/medium framing before close action; do not use chaotic shake or fast cuts to hide unclear movement.
- Use impact feedback such as cloth movement, footsteps, water splash, dust, weapon sound, breath pause, and body recoil.
- Keep it safe and publishable: no blood, gore, wound close-up, broken limb, realistic injury display, attack labels, arrows, speed lines, UI overlays, subtitles, or title cards.
- In storyboard design sheets, use three panels for martial-arts clips: 起势, 交锋, 收势.

## Clip Continuity Rules

- Generate video at the `clip_plan` level by default; use shot-level requests only for troubleshooting.
- For clip 1, use locked character refs and normal scene refs. Do not use text-to-video as an IP consistency test.
- For clip 2+, extract the previous clip's final frame and pass it as `previous_clip_end_frame`; provider requests should map it to the first-frame slot when supported.
- If a provider disallows first-frame input together with reference images, prefer the previous final frame for clip continuation and keep the normal refs in metadata/prompt checks.
- Preserve 720 panorama assets as `space_anchor_refs`; do not discard them and do not default to feeding them as direct generation frames.
- Check every clip boundary for face, hairstyle, costume, prop hand, scene layout, light direction, and current_start_state/current_end_state continuity.
- Keep generated-video audio limited to ambient sound and foley. Background music, songs, music beds, on-screen subtitles, fake text, title cards, and watermarks are forbidden in video prompts.

## Prompt Quality Layers

Each generated video prompt should include:

- timed shot duration
- narrative intent
- action flow from previous state to end state
- restrained performance and 1-2 micro-actions
- camera behavior tied to emotion, not decorative motion
- spatial continuity with axis, screen direction, and eyeline
- lighting logic, palette, material texture, and anti-AI realism anchors
- sound design, including ambience, BGM cue, voiceover, and key subtitle
- execution constraints that prevent drift, overacting, text clutter, and unsupported additions
- retry advice for face drift, costume drift, scene reset, axis errors, or overdone camera motion

## Multi-Character Rules

- Pick a main axis for every shot.
- Keep A screen-left facing right and B screen-right facing left unless a legal transition is written.
- Eyelines must be complementary.
- If a third character enters, describe entry side and relation to the current axis.
- Do not let generated prompts change face, hairstyle, costume, scene layout, light direction, or prop state between shots.

## Provider Adapter Boundary

Future provider adapters must consume `video_handoff.clip_plan` for normal generation and `video_handoff.shots` for troubleshooting. Do not rebuild prompts from scratch inside adapters.

Provider adapters may add:

- provider model name
- aspect ratio
- duration limits
- reference image upload IDs
- callback or polling metadata

Provider adapters must preserve:

- `visual_lock`
- `reference_binding`
- `continuity_state`
- `axis`
- `screen_direction`
- `eyeline`

## Provider Request Flow

Use this flow before any paid video generation:

1. Build or generate the image assets first: character design refs and normal perspective scene refs. Keep 720 panoramas as space anchors.
2. Build `video_handoff`.
3. Optionally run image generation on `storyboard_image_tasks[0]` to create a clip storyboard content design sheet.
4. Prefer one `clip_id` or `clip_index` for normal generation; use `shot_id` or `shot_index` only for troubleshooting.
5. Run `prepare_video_generation`.
6. Inspect `provider_request.prompt`, `reference_images`, `video_reference_images`, `space_anchor_refs`, `continuity_state`, and `transport`.
7. Confirm the prompt says ambient sound/foley only and forbids BGM, songs, subtitles, title cards, fake text, and watermarks.
8. For martial-arts clips, confirm the prompt includes `武戏调度` and only one readable attack-defense beat.
9. Generate only one short I2V test clip after the provider adapter is confirmed.

Supported provider request shapes:

- `offline` / `dry_run`: returns request JSON only.
- `dreamina_cli`: returns a CLI transport placeholder for the official `dreamina` executable, with `subcommand`, `help_command`, intended parameters, and `stdin_json`.
- `jimeng_cli`: compatibility alias for `dreamina_cli`.
- `poyo_video`: returns a Seedance 2 HTTP payload in dry-run mode; with `dry_run=false`, submits to `/api/generate/submit`, polls `/api/generate/status/{task_id}`, and downloads returned `files`.

Do not run full-episode batches until single-clip face, costume, scene, lighting, axis, and eyeline consistency is verified.

## PoYo Seedance 2 Notes

Supported models:

- `seedance-2`
- `seedance-2-fast`

Request rules:

- `prompt` is required.
- `duration` is clamped to 4-15 seconds.
- `seedance-2-fast` downgrades `1080p` requests to `720p`.
- Default project resolution is `480p` for low-cost test clips. Use `720p` only when the shot needs review-quality detail.
- `image_urls` supports up to 2 first/last frame images.
- `image_urls` cannot be mixed with `reference_image_urls`, `reference_video_urls`, or `reference_audio_urls`.
- Reference assets must be public URLs or local paths that can be uploaded through PoYo upload stream.
- `reference_audio_urls` requires at least one reference image or reference video.
