# IP Video Prompt Architecture

This file defines the fixed prompt packet used by `ip-video-skill` before any paid video generation.

The goal is to preserve the project's own IP flavor while making the execution structure stable. Do not replace this with ad hoc long prompts.

## Prompt Packet V1

Every clip-level video prompt must be organized in this order:

1. `Prompt Packet`
   - clip id
   - duration
   - shot ids
   - generation unit
2. `Global Context`
   - project/scene tone
   - visible environment
   - overall texture, light, palette, sound policy
3. `Internal Story Facts`
   - real character names or lock ids
   - real story action
   - storyboard shot order
   - continuity state
   - this section is for local planning and may use the project's original terms
4. `Reference Bindings`
   - character refs lock identity
   - scene refs lock space
   - storyboard refs lock composition, blocking, action phase, screen direction, and edit order
   - in `all_purpose_reference` mode, use `reference_image_urls` only and do not use `image_urls`
5. `Spatial Blocking`
   - present characters
   - axis
   - screen direction
   - eyeline
   - distance/blocking
   - doors, windows, thresholds, entries, exits, and danger side if relevant
6. `15s Timeline`
   - one continuous narrative unit, usually 5-15 seconds
   - each shot must include time range, shot id, framing/camera, start state, action transform, and end state
   - do not fill time with a single meaningless run or decorative move
7. `Continuation Contract`
   - for every clip boundary choose one mode:
     - `hard_first_frame`
     - `previous_reference_reframe`
     - `bridge_cutaway`
     - `sound_bridge_or_hard_cut`
   - single-frame extraction is continuity reference only unless `hard_first_frame` is explicitly selected
8. `Platform-Safe Surface Wording`
   - external prompt wording may soften risky nouns, but it must not change locked content
   - safe wording strengthens reference details; it does not add, remove, or replace characters, props, actions, or spaces
9. `Execution Constraints`
   - storyboard order cannot be deleted, merged away, reordered, or rewritten
   - prompt text may only strengthen existing references and storyboard details
   - ambient sound and foley only
   - no subtitles, fake text, title cards, watermarks, songs, or music beds

## Internal Facts vs Surface Wording

Keep two layers separate:

- Internal facts: the real project vocabulary used for planning, continuity, shot ids, and asset binding.
- Surface wording: the platform-facing wording submitted to the video model.

Surface wording can be safer, but it must remain visually equivalent.

Examples:

- Internal: `黑羊诡`
- Surface: `黑雾中的巨大追逐实体，红色眼部反光，压迫性轮廓`

- Internal: `牛头员工`
- Surface: `参考图锁定的非人化饭店侍者轮廓，宽厚身形，制服层次，标准服务姿态`

- Internal: `爆裂雷`
- Surface: `一次性抛掷装置，烟尘冲击，短促闷响，用于阻断追击`

Do not turn a locked character into a different character for moderation convenience. For example, do not change a non-human restaurant attendant into a gas-mask waiter unless the reference image actually shows that design.

## Storyboard Contract

Once a storyboard, shot table, or manga-line board exists, it is the execution blueprint.

Each provider request must carry `storyboard_execution_map`, and video shot order must match `clip.shot_ids` exactly.

Storyboard refs lock:

- composition
- camera side
- subject scale
- blocking
- action phase
- screen direction
- eyeline
- edit order

Storyboard refs do not lock final identity by themselves. Character identity comes from the locked character references.

## Multi-Character Spatial Contract

For 2+ characters, every clip must preserve:

- one declared axis or movement axis
- stable screen direction
- complementary eyelines
- trackable distance and blocking
- legal transition before any axis change

Door, window, threshold, or chase scenes must explicitly state:

- which side is safe/interior
- which side is danger/exterior
- who crosses the boundary
- when the boundary closes or blocks the threat
- where the pursuer remains after the cut

## Live Generation Gate

Before live generation:

- run dry-run/provider request preparation
- inspect prompt sections
- inspect `reference_image_urls` and confirm no unwanted `image_urls` in all-purpose mode
- inspect `storyboard_execution_map`
- inspect axis/screen direction/eyeline
- inspect model: paid/live default is `seedance-2`, not `seedance-2-fast`
- inspect sound and text constraints

Do not spend credits if any required section is missing.
