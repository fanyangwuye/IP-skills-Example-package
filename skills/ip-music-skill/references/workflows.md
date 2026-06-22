# IP Music Workflows

Use this reference when a task needs a multi-step music chain or a mode choice.

## Mode Map

All live modes submit through `POST /api/generate/submit`. Music status uses `GET /api/generate/detail/music?task_id=...`.

| Skill mode | PoYo model | Required input | Output |
|---|---|---|---|
| `generate_music` | `generate-music` | `prompt`, optional `style`/`title` | song variants with `task_id` and `audio_id` |
| `add_instrumental` | `add-instrumental` | uploaded vocal/audio URL + `tags` | song with accompaniment |
| `add_vocals` | `add-vocals` | uploaded instrumental URL + lyrics prompt + style | complete song |
| `cover_audio` | `upload-and-cover-audio` | uploaded audio URL + prompt | restyled/remade song |
| `extend_music` | `extend-music` | upstream `audio_id` | extended song |
| `replace_section` | `replace-section` | upstream `task_id`, `audio_id`, start/end seconds | edited song |
| `stem_split` | `stem-split` | upstream `task_id`, `audio_id` | generated-song stems |
| `separate_vocals` | `separate-vocals` | upstream `task_id`, `audio_id` | generated-song vocal/instrumental split |
| `upload_separate_vocals` | `upload-and-separate-vocals` | uploaded external audio | external-audio split |

## Chaining Rules

- `stem_split`, `separate_vocals`, `replace_section`, and most `extend_music` work need upstream `task_id` and/or `audio_id`.
- `add_instrumental`, `add_vocals`, `cover_audio`, and `upload_separate_vocals` accept uploaded audio. Pass `audio_path` for local files or `audio_url` for existing URLs.
- Generated music result URLs can expire. Download useful results immediately.
- `generate_music` usually returns multiple variants. The scripts download the first one and keep all returned audio metadata in `handoff.audios`.

## Common Chains

Create theme and stems:

```text
build_music_handoff
  -> generate_music for the theme task
  -> stem_split with returned task_id/audio_id
```

Turn a vocal demo into a fuller track:

```text
add_instrumental with audio_path + tags
  -> optional cover_audio for restyling
```

Restyle a rough external recording:

```text
cover_audio with audio_weight around 0.7-0.9
```

Use `cover_audio` as a remake, not as deterministic audio restoration. If the melody is not recognizable, the generated version may drift.

## Prompt Style

- Use comma-separated style tags: genre, emotion, instruments, tempo, era, scene.
- Keep BGM prompts scene-specific and short-drama-oriented.
- Use `negative_tags` to exclude unwanted genres or textures.
- For lyrics, `prompt` can include sections such as `[Verse]`, `[Chorus]`, and `[Bridge]`.

## Model Version

- Default `mv` is `V5`.
- Use `V4` only when its shorter duration and voice behavior are intentional.
- Long tracks should avoid versions with shorter maximum duration.
