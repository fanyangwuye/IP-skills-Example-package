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
8. After generating a storyboard board image, pass its path as `storyboard_image_path` or `storyboard_image_paths` when preparing or running video generation.
9. Create `i2v_prompt`, `t2v_prompt`, `seedance_prompt`, and `clip_prompts` using the fixed Prompt Packet architecture in `prompt_architecture.md`.
10. Create an EDL for later ffmpeg/provider assembly.

## Prompt Packet Rules

- Clip prompts must use the fixed sections from `prompt_architecture.md`: `Global Context`, `Internal Story Facts`, `Reference Bindings`, `Spatial Blocking`, `15s Timeline`, `Continuation Contract`, `Platform-Safe Surface Wording`, and `Execution Constraints`.
- Keep internal story facts separate from platform-facing safe wording. Safety rewrites may soften nouns, but must not change locked characters, props, actions, spaces, or storyboard order.
- For 2+ characters, the `Spatial Blocking` section is mandatory and must state axis, screen direction, eyeline, and trackable blocking.
- Door, window, threshold, and chase scenes must state safe side, danger side, crossing direction, boundary closure, and where the pursuer remains.
- The `15s Timeline` is a narrative editing unit, not a license to stretch one action for 15 seconds. If one clip cannot execute the mapped storyboard shots clearly, split the clip instead of rewriting the storyboard.
## High-Risk Spatial Template Rules

- Chase, throw-back, door/threshold, and window/glass scenes must carry the matching high-risk spatial template from `scripts/spatial_templates.py`.
- These templates lock movement axis, safe/danger side, crossing order, boundary close timing, and threat position.
- The template is a constraint layer only. It must not add new story actions, new props, new characters, or replace storyboard blocking.
- If the template exposes a conflict between the storyboard and the prompt, stop and revise the storyboard/prompt mapping before live generation.

## Storyboard Execution Rules

- Treat storyboard boards and shot tables as the video execution blueprint after they exist, not as loose visual inspiration.
- Each `clip_plan` entry must include `storyboard_execution_map` with one row per `shot_id`, preserving storyboard order exactly.
- Every paid/live clip request must expose that mapping and bind video shot order to storyboard shot IDs, for example `video shot 1 = storyboard shot_008`.
- Do not delete, merge away, reorder, or change storyboard shots without an approved storyboard revision.
- If a 15-second clip cannot accurately execute every mapped storyboard shot, split it into shorter generation units instead of changing the storyboard.
- Prompt text may only strengthen details that already exist in the reference images and storyboard. It must not add, modify, or reduce locked content.
- `storyboard_mode=production` is the default for executable video prompts and paid/live generation.
- `storyboard_mode=draft` may propose split, merge, or reorder notes for review, but the current `storyboard_execution_map` stays unchanged until the user approves and the storyboard is rebuilt.
- Preflight and live provider generation must block `storyboard_mode=draft`; draft artifacts are for planning, not spending credits.
- Review `storyboard_quality` before paid generation. `fail` blocks preflight; `warn` requires human review but does not change the storyboard by itself.
- Typical `storyboard_quality` failures include a 12-15 second single action shot, especially continuous running/chasing without reaction or result beats. Typical warnings include high shot density, vague visual beats, weak story function, and spatial actions needing review.

## Storyboard Boards And Panel References

- Use character design sheets to lock identity and normal scene references to lock the environment.
- Generate one storyboard board per clip when the user wants visual planning before video generation.
- Each board should map panels to shot beats and reference roles. If the project uses `reference_policy: all_purpose_reference`, panels are all-purpose layout references, not a requirement to create first/last-frame keyframes.
- Keep production labels short, Chinese by default, and outside panel image areas.
- Do not put dialogue subtitles, title cards, fake UI, decorative text, or watermarks inside panels.
- Treat the full storyboard board as a planning sheet, not a direct video frame.
- Crop storyboard panels into layout references for video generation. The crops lock composition, camera angle, subject scale, blocking, pose phase, screen direction, and scene anchors only.
- Do not copy line-art style, table borders, labels, arrows, handwritten marks, grayscale texture, or storyboard text into the generated video.

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
- Before clip 1, lock the project reference policy. If `reference_policy: all_purpose_reference` is set, use `reference_image_urls` only for character, scene, and storyboard refs; do not convert the workflow to first-frame/keyframe `image_urls`.
- For clip 2+, use the previous clip tail frame only when the selected continuation mode requires first-frame continuation. In all-purpose reference mode, do not map previous tail frames to `image_urls`; carry continuity through prompt constraints and allowed all-purpose references.
- Single-frame extraction serves only clip-to-clip continuity review/reference: light, color, motion residue, screen direction, character state, and emotion. It is not an identity lock, not the default first frame, and not a substitute for all-purpose references.
- If a provider disallows mixing `image_urls` with `reference_image_urls`, obey the locked project policy. For all-purpose reference mode, keep `reference_image_urls` and do not fall back to first/last-frame inputs.
- Character-bearing clips must pass `character_reference_bindings` preflight: required character ids from `visual_lock.characters` must be covered by character reference roles, and multi-character clips must not use unbound generic character refs.
- If a new angle or closer shot is needed for clip 2+, declare the new shot in the storyboard/shot table and lock screen direction, axis, and motion direction. In all-purpose reference mode, do not generate a replacement keyframe unless the user explicitly changes the reference policy.
- Split bridge/cutaway clips from character clips. A cutaway may hide a jump in axis, color, or camera size, but it must not be the first frame of a clip where the character later appears.
- Preserve 720 panorama assets as `space_anchor_refs`; do not discard them and do not default to feeding them as direct generation frames.
- Check every clip boundary for face, hairstyle, costume, prop hand, scene layout, light direction, and current_start_state/current_end_state continuity.
- Keep generated-video audio limited to ambient sound and foley. Background music, songs, music beds, on-screen subtitles, fake text, title cards, and watermarks are forbidden in video prompts.

## Bridge Clip Rules

- Use bridge clips only when they serve a concrete edit function: carry action momentum, mask a planned camera/scale change, unify color and exposure, introduce a story object, or set the next eyeline.
- Derive bridge visuals from the previous clip's end state and the next clip's start state. Do not write generic empty scenery such as unrelated cloud, stone, rain, or wall inserts.
- Keep bridge clips face-light: environment, prop, hand, sleeve, back, side edge, shadow, light, dust, wind, floor reflection, or object movement are safer than a new frontal face.
- Bridge audio should continue the same ambience and foley. It must not introduce BGM, songs, automatic dialogue, subtitles, title cards, or fake text.

## Prompt Quality Layers

Each generated video prompt should include:

- timed shot duration
- narrative intent
- action flow from previous state to end state
- restrained performance and 1-2 micro-actions
- camera behavior tied to emotion, not decorative motion
- spatial continuity with axis, screen direction, and eyeline
- lighting logic, palette, material texture, and anti-AI realism anchors
- sound design limited to ambience and foley; no BGM, songs, voiceover, subtitles, title cards, fake text, or watermarks
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

1. Build `video_handoff` so the continuity bible, clip ids, shot ids, storyboard map, and reference needs are locked.
2. Run `build_asset_manifest_template`, or run `scan_asset_manifest_directory` when approved assets already exist in local folders. Replace every remaining `PATH_OR_URL` placeholder or missing path with approved local paths or public URLs.
3. Run `review_asset_manifest`; resolve blocker action items for missing or placeholder character, scene, storyboard, and space-anchor assets before preflight.
4. Build or generate any missing image assets: character design refs, normal perspective scene refs, storyboard boards, and 720 panoramas as space anchors. Record only approved assets in `asset_manifest_path`.
5. Apply the locked reference policy. If `reference_policy: all_purpose_reference` is set, load approved character, scene, and storyboard refs from `asset_manifest_path` or explicit `reference_image_urls`; verify every character ref has `character_id`, every scene ref has `scene_id`, every storyboard ref has `clip_id`, and the request has no `image_urls`.
6. If a storyboard board was generated, pass `storyboard_image_path` or `storyboard_image_paths`; the provider layer crops first/mid/last panel layout refs automatically.
7. Prefer one `clip_id` or `clip_index` for normal generation; use `shot_id` or `shot_index` only for troubleshooting.
8. Run `episode_readiness`; do not start paid/live generation while `status=blocked`.
9. Run `preflight_video_generation`; do not start paid/live generation while the report status is `fail`.
10. Run `prepare_video_generation`.
11. Inspect `provider_request.prompt`, including the fixed Prompt Packet sections, `image_urls`, `reference_images`, `reference_image_urls`, `storyboard_panel_refs`, `video_reference_images`, `space_anchor_refs`, `continuity_state`, and `transport`.
12. Confirm `@Image` bindings are explicit: in all-purpose reference mode, character refs are identity refs, scene refs are space refs, storyboard refs are layout/edit refs, and no first-frame/keyframe binding appears unless explicitly selected.
13. Confirm the prompt says storyboard panel refs only lock layout and forbids copying line art, labels, table borders, arrows, and text.
14. Confirm the prompt says ambient sound/foley only and forbids BGM, songs, subtitles, title cards, fake text, and watermarks.
15. For martial-arts clips, confirm the prompt includes `武戏调度` and only one readable attack-defense beat.
16. Generate only one short I2V test clip after the provider adapter is confirmed.

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
- Default paid/live model is `seedance-2`. Do not use `seedance-2-fast` unless the user explicitly asks for fast mode and the task sets `allow_fast_model=true`.
- `seedance-2-fast` downgrades `1080p` requests to `720p`.
- Default project resolution is `480p` for low-cost test clips. Use `720p` only when the shot needs review-quality detail.
- `image_urls` supports up to 2 first/last frame images.
- `image_urls` cannot be mixed with `reference_image_urls`, `reference_video_urls`, or `reference_audio_urls`.
- Reference assets must be public URLs or local paths that can be uploaded through PoYo upload stream.
- `reference_audio_urls` requires at least one reference image or reference video.
