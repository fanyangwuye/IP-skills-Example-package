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
3. Create one shot per segment in phase 1.
4. Carry `previous_end_state -> current_start_state -> current_end_state` through every shot.
5. Create `i2v_prompt`, `t2v_prompt`, and `seedance_prompt`.
6. Create an EDL for later ffmpeg/provider assembly.

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

Future provider adapters must consume `video_handoff.shots`. Do not rebuild prompts from scratch inside adapters.

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

1. Build `video_handoff`.
2. Pick one `shot_id` or `shot_index`.
3. Run `prepare_video_generation`.
4. Inspect `provider_request.prompt`, `reference_images`, `continuity_state`, and `transport`.
5. Generate only one short test shot after the provider adapter is confirmed.

Supported provider request shapes:

- `offline` / `dry_run`: returns request JSON only.
- `jimeng_cli`: returns a CLI transport placeholder with executable, args, and `stdin_json`.
- `poyo_video`: returns an HTTP transport placeholder with URL, headers shape, and JSON payload.

Do not run full-episode batches until single-shot face, costume, scene, lighting, axis, and eyeline consistency is verified.
