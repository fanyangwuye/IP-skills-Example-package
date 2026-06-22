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
5. Create both `i2v_prompt` and `t2v_prompt`.
6. Create an EDL for later ffmpeg/provider assembly.

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
