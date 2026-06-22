---
name: ip-copy-skill
description: "Build structured IP adaptation outputs for downstream agent skills. Use this skill when an agent needs to validate IP rights, organize adaptation direction, build a clip blueprint, or hand off character and asset directions to the image skill. This local version focuses on deterministic planning, validation, and handoff, not on pretending to fully rewrite prose with a hidden external model."
---

# IP Copy Skill

## When To Use

- Validate whether an IP adaptation request is allowed
- Turn structured scene cards into a downstream-safe blueprint
- Organize character, scene, and asset direction so the image skill can work from it
- Convert source copy into a multi-character `ip_asset_pack` for character sheets, props, and panorama scenes
- Run interactive adaptation planning across conversation turns
- Build adaptation scene cards for downstream blueprint creation
- Build a minimal content brain layer before image generation

## Tool Boundaries

- Allowed:
  - Read local license records
  - Build structured JSON outputs
  - Validate blueprints
  - Write results into `output_dir`
- Forbidden:
  - Bypass the license gate
  - Claim full AI prose adaptation when only deterministic planning is implemented

## Core Flows

### Flow A: License Check

1. Load a license record
2. Validate target, commercial usage, and expiry
3. Return pass/fail with reasons

### Flow B: Blueprint Build

1. Accept structured scene cards and adaptation direction
2. Normalize timeline durations
3. Build a validated blueprint
4. Return image-facing handoff data

### Flow B1: Interactive Adaptation State

1. Accept `source_text`, current `adaptation_state`, and `conversation_turns`
2. Extract user intent such as target format, tone, viewpoint, audience, constraints, characters, and scenes
3. Update a reusable `adaptation_state`
4. Return `next_questions` when key creative decisions are still missing

### Flow B2: Adaptation Scene Cards

1. Accept an `adaptation_state`
2. Build 3-8 short-drama-ready scene cards
3. Each card includes visual, voiceover, subtitle, music cue, duration, and image `asset_goal`
4. The result can be passed into `build_blueprint`

### Flow C: Character/Image Handoff

1. Accept a character sheet and optional asset bundle
2. Package them into a downstream handoff for the image skill

### Flow D: IP Asset Pack Build

1. Accept source copy plus optional explicit character and scene cards
2. Extract or preserve multiple important characters, not only the protagonist
3. Bind obvious props to matching characters
4. Extract scene candidates as 720 panorama environment references
5. Return a `mode=ip_asset_pack` JSON object for `ip-image-skill`

## Scripts

- `scripts/license_gate.py`: deterministic license validation
- `scripts/blueprint_validate.py`: deterministic blueprint validation
- `scripts/copy_skill.py`: task entrypoint, interactive adaptation state, scene card builder, blueprint builder, handoff builder, and IP asset pack builder

## References

- `references/licenses/`: local license records
- `references/adaptation_brief_template.json`: structured brief template

## Invocation

- Agent module usage: call `run_task(task_dict)` from `scripts/copy_skill.py`
- JSON task usage: `python copy_skill.py --task path/to/task.json`

## Multi-Character Rule

When building `ip_asset_pack`, do not collapse the cast into only the protagonist.
Preserve every explicit `characters` entry.
If only `source_text` is provided, extract multiple important named roles, title roles, creature roles, employees, allies, antagonists, and scene-driving figures when present.

## Adaptation Boundary

This version provides deterministic adaptation planning and scene-card drafting.
It does not claim final polished prose or full model-native rewriting.
For production writing, an agent should use this state and scene-card structure as the control layer, then call a writing model for richer dialogue and prose where needed.
