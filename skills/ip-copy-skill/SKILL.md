---
name: ip-copy-skill
description: "Build structured IP adaptation outputs for downstream agent skills. Use this skill when an agent needs to validate IP rights, organize adaptation direction, build scene cards/script scaffolds, run offline/mock CreativeEngine checks, apply the vertical short-drama adapter, or hand off character and asset directions to image/video/music skills. This local version focuses on controlled planning, validation, quality reports, and guarded creative-engine integration; live model writing is not enabled by default."
---

# IP Copy Skill

## When To Use

- Validate whether an IP adaptation request is allowed
- Turn structured scene cards into a downstream-safe blueprint
- Organize character, scene, and asset direction so the image skill can work from it
- Convert source copy into a multi-character `ip_asset_pack` for character sheets, props, and panorama scenes
- Run interactive adaptation planning across conversation turns
- Build adaptation scene cards for downstream blueprint creation
- Build structured short-drama script drafts from scene cards or adaptation state
- Polish script drafts with deterministic dialogue tightening and conflict notes
- Build viral short-video explainer scripts from source text or script drafts without confusing them with scene cards
- Build a minimal content brain layer before image generation
- Route scene-card, script-draft, and polish flows through the guarded CreativeEngine interface when configured
- Attach `generation_source` and `quality_report` fields so downstream agents know whether an output is fallback scaffold, mock engine output, or future live output
- Apply the `vertical_short_drama` FormatAdapter V1 for 9:16 short-drama structure, rhythm rules, and downstream handoff requirements
- Build CreativeEngine prompt packs and provider request dry-run JSON for review without making live calls
- Include creative diagnostics in prompt packs: genre profile, character voice contract, causality contract, rhythm contract, forbidden drift, and quality gate`r`n- Include deterministic creative-quality checks in `quality_report`: unsupported details, character consistency, dialogue voice, causality, hook density, and emotion curve

## Tool Boundaries

- Allowed:
  - Read local license records
  - Build structured JSON outputs
  - Validate blueprints
  - Write results into `output_dir`
  - Use offline/mock CreativeEngine modes for tests and structured handoff validation
  - Return quality reports for scene cards, script drafts, and polished scripts
  - Build `build_creative_prompt_pack` dry-run artifacts with `network_call_allowed=false`
- Forbidden:
  - Bypass the license gate
  - Claim full AI prose adaptation when only deterministic planning or mock output is implemented
  - Call live LLM/image/video/music providers unless the user explicitly confirms live generation and the task enables it
  - Treat a provider request dry-run artifact as evidence that a live call happened

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

### Flow B0: Creative Prompt Pack Dry Run

1. Accept `source_text`, `creative_brief`, `prompt_kind`, optional `scene_cards` / `script_draft`, and provider/model labels.
2. Build a `copy-creative-prompt-pack-v1` prompt pack with source material, format constraints, creative diagnostics, response contract, safety constraints, task instructions, and quality targets.
3. Build a `copy-live-provider-request-v1` provider request wrapper with `network_call_allowed=false`.
4. Write `creative_prompt_pack.json` and return `live_call_made=false`.
5. Use this mode for review, testing, and handoff before any explicit live provider integration.

### Flow B1: Interactive Adaptation State

1. Accept `source_text`, current `adaptation_state`, and `conversation_turns`
2. Extract user intent such as target format, tone, viewpoint, audience, constraints, characters, and scenes
3. Update a reusable `adaptation_state`
4. Return `next_questions` when key creative decisions are still missing

### Flow B2: Adaptation Scene Cards

1. Accept an `adaptation_state`
2. Select a FormatAdapter, defaulting to `vertical_short_drama`
3. Try the configured CreativeEngine path first; default offline mode returns `fallback_required` without spending quota
4. Use deterministic scene cards only as clearly marked fallback scaffold with `generation_source=fallback_scaffold`
5. Each card includes visual, voiceover, subtitle, music cue, duration, and image `asset_goal`
6. Attach `quality_report` so users can see scaffold warnings and deterministic creative-quality warnings before production

### Flow B3: Script Draft

1. Accept `scene_cards` or an `adaptation_state`
2. If scene cards are missing, build them from the adaptation state
3. Apply the `vertical_short_drama` adapter metadata: `format_adapter`, `aspect_ratio=9:16`, rhythm rules, quality checks, and downstream handoff requirements
4. Try CreativeEngine `script_scenes`; invalid explicit engine output is rejected instead of silently falling back
5. Return a structured `script_draft` with scenes, action, voiceover, dialogue, subtitles, music cues, timing, asset goals, `generation_source`, and `quality_report` with creative checks
6. Treat fallback output as scaffold, not final prose

### Flow B4: Script Polish

1. Accept a `script_draft`, or build one from the current task
2. Preserve scene order, timing, and asset goals
3. Try CreativeEngine `polished_script_scenes` when explicitly configured; reject bad explicit engine output
4. Keep original dialogue under `original_dialogue`
5. Write deterministic tightened Chinese short-drama dialogue into `polished_dialogue` and `dialogue` only as fallback scaffold
6. Add `conflict_notes`, `beat_function`, adapter metadata, `generation_source`, and `quality_report` with creative checks for downstream review

### Flow B5: Viral Explainer Script

1. Accept `source_text`, `script_draft`, or `polished_script`.
2. Split obvious episode markers such as `第一集` / `第2集` into episode blocks.
3. Build a short-video explainer layer with `opening_hook`, `narration_lines`, `cliffhanger`, `retention_devices`, and platform notes.
4. Keep the output as a deterministic explainer scaffold. Do not pretend scene cards are final viral narration, and do not invent new plot facts or replace locked characters.

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
- `scripts/copy_skill.py`: task entrypoint, interactive adaptation state, scene card builder, script draft builder, viral explainer builder, script polish helper, blueprint builder, handoff builder, and IP asset pack builder
- `scripts/creative_engine/`: CreativeEngine base types, offline engine, mock engine, live guard placeholder, and schema checks
- `scripts/format_adapters/`: FormatAdapter base and `vertical_short_drama` V1 adapter
- `scripts/quality_evaluator/`: structure, scaffold, and deterministic creative-quality checks for scene cards and scripts

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

This version provides controlled adaptation planning, CreativeEngine routing, vertical short-drama structure, scaffold fallback, and quality reports.
It still does not claim final polished prose or full model-native rewriting.
Offline mode never calls a provider and now returns a reviewable prompt pack under `raw_response`. Mock mode is for tests. The live LLM engine is guarded; after double approval it currently builds a dry-run provider request with `network_call_allowed=false` and still does not make provider calls. Prompt packs are stronger control artifacts, not proof that final creative prose has been generated.
For production writing, an agent should use this state, adapter metadata, and scene/script structure as the control layer, then call an explicitly approved writing model for richer dialogue and prose where needed.
