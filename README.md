# IP Skills

This repository contains agent-facing skills for IP creation workflows.

Current scope:

- `ip-image-skill`: image generation, character/storyboard design assets, grid splitting, and image enhancement
- `ip-copy-skill`: deterministic content planning, blueprint validation, and image handoff building
- `ip-music-skill`: music handoff building plus PoYo/Suno music generation, remixing, stems, and vocal separation
- `ip-video-skill`: offline continuity bible, shot/clip plan, storyboard image tasks, martial-arts action prompting, high-quality I2V/T2V/Seedance prompts, provider request preparation, video handoff, and EDL building

Design goals:

- No UI layer
- Agent-callable modules and scripts
- Provider-configurable via environment variables
- All generated outputs stored under the configured output root

## Copyright And Usage

This repository is all-rights-reserved by default. Public visibility does not grant commercial use, redistribution, resale, or sublicensing rights. See `LICENSE`, `COMMERCIAL_LICENSE.md`, and `NOTICE.md` before redistributing, publishing, or using the package or generated outputs commercially.

## Repository Layout

- `skills/ip-image-skill/`: image generation, character sheets, storyboard design sheets, asset packs, grid split/enhance
- `skills/ip-copy-skill/`: copy planning, blueprint validation, image handoff building
- `skills/ip-music-skill/`: theme/BGM handoff building, music generation, remix/edit/split workflows
- `skills/ip-video-skill/`: continuity-locked video handoff, shot/clip planning, prompt quality layers, provider request preparation, and EDL
- `scripts/`: cross-skill helper scripts
- `tests/`: repository-level integration tests
- `docs/`: workflow notes
- `outputs/`: local generated artifacts, ignored by Git
- `logs/`: local logs, ignored by Git

## Install

```bash
python -m pip install -r requirements.txt
```

See `docs/agent_config.md` for Codex, Claude Code, OpenClaw, and generic agent setup.

Install the skills once for Codex auto-discovery:

```bash
python scripts/install_agent_skills.py --force
```

By default this copies `skills/ip-*` into `CODEX_HOME/skills` or `~/.codex/skills`.
For another agent, pass its skills/tools directory explicitly:

```bash
python scripts/install_agent_skills.py --target "PATH_TO_AGENT_SKILLS" --force
```

After installation, a new agent window can be invoked with a short instruction such as:

```text
Use the installed IP skills to run the full IP workflow. Do not skip character sheets, scene refs, storyboard/shot table, reference policy, I2V, tail-frame handoff, or continuity checks.
```

Agents that do not support auto-discovered skills should be configured to read the relevant `SKILL.md` files under `skills/` and run the Python entrypoints described there.

## Setup Doctor

Check local provider setup without spending credits:

```bash
python scripts/setup_doctor.py
```

See `docs/provider_setup.md` for PoYo key setup, Dreamina CLI setup, and ffmpeg notes.

## Environment

Copy `.env.example` to your local environment manager or shell configuration. Do not commit real keys.

Required for live image generation:

```text
IMAGE_PROVIDER=poyo
IMAGE_API_KEY=your_provider_key
IMAGE_API_BASE=https://api.poyo.ai
IMAGE_GEN_MODEL=gpt-image-2
IMAGE_EDIT_MODEL=gpt-image-2-edit
IMAGE_OUTPUT_ROOT=<repo>\outputs
```

Required for live music generation:

```text
MUSIC_PROVIDER=poyo
MUSIC_API_KEY=your_provider_key
MUSIC_API_BASE=https://api.poyo.ai
MUSIC_OUTPUT_ROOT=<repo>\outputs
MUSIC_DEFAULT_MODEL_VERSION=V5
MUSIC_FFMPEG_BIN=optional_ffmpeg_path_for_local_audio_upload
```

Optional for video provider request preparation:

```text
VIDEO_PROVIDER=offline
VIDEO_API_KEY=optional_for_future_live_provider
VIDEO_API_BASE=optional_for_future_live_provider
VIDEO_OUTPUT_ROOT=<repo>\outputs
VIDEO_DEFAULT_MODEL=optional_provider_model
VIDEO_DEFAULT_ASPECT_RATIO=9:16
VIDEO_DEFAULT_RESOLUTION=480p
VIDEO_POLL_INTERVAL_SEC=4
VIDEO_POLL_TIMEOUT_SEC=600
```

`POYO_API_KEY` can be used as a shared key fallback for image, music, and future video providers.

Video defaults to `480p` to keep test clips low-cost. Set `VIDEO_DEFAULT_RESOLUTION=720p` for clearer review clips when needed.

Video generation is clip-first by default: `clip_plan` groups shots into 5-15 second continuity clips. Panorama scene images are preserved as `space_anchor_refs`; normal perspective scene references are used for video model input. `storyboard_image_tasks` can generate clip-level storyboard content design sheets before I2V, but storyboard panels must function as a shot blueprint: the first panel should match the intended video first-frame composition, camera angle, subject scale, screen direction, and scene anchors. Martial-arts clips get a dedicated action layer for stance, distance, attack-defense beats, footwork, weight shift, and safe impact feedback. Real IP video tests should start from generated image references and I2V; text-to-video is only a provider connectivity check.

Video prompts keep only ambient sound and foley for generated audio. Background music, songs, music beds, on-screen subtitles, title cards, fake text, and watermarks are forbidden; BGM and subtitles belong in post-production/EDL.

For live character video generation, obey the project reference policy exactly. If the project sets `reference_policy: all_purpose_reference`, the provider request must use `reference_image_urls` only and must not be rewritten into `image_urls`, first-frame, last-frame, previous-tail-frame, or keyframe I2V. Character refs, scene refs, and storyboard refs are all-purpose references in that mode. Use first/last-frame `image_urls` only when the project explicitly selects that policy.

## Quick Checks

Run local tests without spending image-generation credits:

```bash
python skills/ip-image-skill/tests/test_asset_pack.py
python skills/ip-image-skill/tests/test_prompt_builder.py
python skills/ip-image-skill/tests/test_split_grid.py
python skills/ip-copy-skill/tests/test_copy_skill.py
python skills/ip-music-skill/tests/test_music_skill.py
python skills/ip-video-skill/tests/test_video_skill.py
python tests/test_setup_doctor.py
python tests/test_copy_to_image_bridge.py
```
