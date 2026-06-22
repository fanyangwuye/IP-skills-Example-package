---
name: ip-music-skill
description: "Build music handoff tasks from IP scripts or blueprints, and generate or remix music through PoYo.ai/Suno models. Use this skill when an agent needs theme songs, scene BGM, instrumental tracks, vocals, covers, extensions, section replacement, stem splitting, or vocal separation for IP video workflows."
---

# IP Music Skill

## When To Use

- Build music tasks from `polished_script`, `script_draft`, `scene_cards`, or `blueprint`
- Generate a theme song or instrumental BGM
- Generate scene-specific short drama background music
- Add instrumental backing to uploaded vocals
- Add vocals to an instrumental
- Cover or restyle an uploaded track
- Extend a generated song
- Replace a section of a generated song
- Split generated music into stems
- Separate vocals and instrumental
- Split or separate uploaded external audio

## Tool Boundaries

- Allowed:
  - Remote PoYo music API calls
  - Public audio URL remix inputs, MP4 audio proxy upload, and result download
  - Local JSON handoff writing
- Forbidden:
  - Hardcoding API keys
  - Claiming that deterministic handoff building has generated music
  - Submitting copyrighted melodies or third-party audio without user rights

## Configuration

Live generation requires:

- `MUSIC_PROVIDER=poyo`
- `MUSIC_API_KEY`: PoYo API key
- `MUSIC_API_BASE=https://api.poyo.ai`
- `MUSIC_OUTPUT_ROOT`: output directory

Compatibility aliases:

- `POYO_API_KEY` can be used if `MUSIC_API_KEY` is not set
- `POYO_BASE_URL` can be used if `MUSIC_API_BASE` is not set

Optional:

- `MUSIC_DEFAULT_MODEL_VERSION=V5`
- `MUSIC_POLL_INTERVAL_SEC=4`
- `MUSIC_POLL_TIMEOUT_SEC=600`
- `MUSIC_FFMPEG_BIN` or `FFMPEG_BIN`: ffmpeg path for automatic local WAV/MP3 to MP4 proxy wrapping

## Core Flows

### Flow A: Build Music Handoff

1. Accept `polished_script`, `script_draft`, `scene_cards`, or `blueprint`
2. Extract theme direction and scene music cues
3. Build `music_tasks`
4. Write `music_handoff.json`

This flow is local and does not spend API credits.

### Flow B: Generate Music

1. Load provider config
2. Build PoYo/Suno input
3. Submit `/api/generate/submit`
4. Poll `/api/generate/detail/music`
5. Download all returned audio variants into `output_dir` by default
6. Return audio IDs for downstream remixing

### Flow C: Remix / Edit / Split

Supported live modes:

- `generate_music`
- `add_instrumental`
- `add_vocals`
- `cover_audio`
- `extend_music`
- `upload_extend_audio`
- `replace_section`
- `stem_split`
- `separate_vocals`
- `upload_separate_vocals`

For multi-step remix chains and mode selection details, read `references/workflows.md`.

For uploaded/external audio remix modes, pass either `audio_url` or `audio_path`. If `audio_path` points to a pure audio file such as WAV/MP3, `poyo_music_client.py` automatically creates a short black-screen MP4 proxy with ffmpeg, uploads that MP4, then passes the returned `file_url` as `upload_url`.

## Scripts

- `scripts/config.py`: environment-driven config
- `scripts/poyo_music_client.py`: PoYo music adapter
- `scripts/music_skill.py`: agent-facing task entrypoint
- `scripts/music_cli.py`: small manual CLI wrapper
- `references/workflows.md`: mode map, chaining rules, and prompt style guidance
- `assets/example_build_music_handoff_task.json`: offline handoff example
- `assets/example_generate_music_task.json`: live generation template
- `assets/example_cover_local_audio_task.json`: local audio remix/rebuild template
- `assets/example_upload_extend_audio_task.json`: local audio extension template
- `assets/example_upload_separate_vocals_task.json`: external audio split template

## Invocation

- Agent module usage: call `run_task(task_dict)` from `scripts/music_skill.py`
- JSON task usage: `python music_skill.py --task path/to/task.json`
- Manual CLI sample: `python music_cli.py generate --prompt "..." --out demo.mp3`
- Generated-track stems: `python music_cli.py stems --task-id TASK --audio-id AUDIO --out-dir ./stems`
- External-audio split: call `run_task` with `audio_url` or local `audio_path`; local WAV/MP3 will be wrapped into an MP4 proxy automatically.
- Audio variants: live audio modes download every returned variant by default, using `_variant_02`, `_variant_03` suffixes. Set `download_all: false` to download only the first variant.

## Handoff Contract

`build_music_handoff` returns:

- `source_title`
- `creative_direction`
- `music_tasks`
- `source_summary`

Each music task can be passed back into `run_task` for live generation after setting API credentials.

## Notes

- Music query uses `/api/generate/detail/music`, not the image status endpoint.
- Generated music usually returns `task_id` plus one or more `audio_id` values.
- `extend_music`, `replace_section`, `stem_split`, and `separate_vocals` need upstream `audio_id`; some modes also need upstream `task_id`.
- `upload_extend_audio` extends external uploaded audio and needs `audio_path` or `audio_url`.
- `upload_separate_vocals` is for external user audio and needs `audio_path` or `audio_url`.
- Local WAV/MP3 upload requires ffmpeg. The generated MP4 proxy is kept in `output_dir` by default for traceability.
- Result URLs can expire; keep downloaded `local_paths` from the handoff.
