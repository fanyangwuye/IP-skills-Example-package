# Provider Setup

This project separates Skill logic from third-party provider setup.

## Recommended Policy

- PoYo providers should be key-driven: users configure keys, then the Skills submit/query/download.
- Dreamina/即梦 CLI should be user-installed: the Skills can detect and prepare requests, but should not silently install or login.
- Paid generation should start with a single small test, not a full batch.
- Never commit real API keys.

## PoYo

PoYo is the default API provider for live image and music flows.

Configure one shared key:

```powershell
$env:POYO_API_KEY="your_key"
```

Or configure separate keys:

```powershell
$env:IMAGE_PROVIDER="poyo"
$env:IMAGE_API_KEY="your_key"
$env:IMAGE_API_BASE="https://api.poyo.ai"

$env:MUSIC_PROVIDER="poyo"
$env:MUSIC_API_KEY="your_key"
$env:MUSIC_API_BASE="https://api.poyo.ai"
```

For future PoYo video:

```powershell
$env:VIDEO_PROVIDER="poyo_video"
$env:VIDEO_API_KEY="your_key"
$env:VIDEO_API_BASE="https://api.poyo.ai"
$env:VIDEO_DEFAULT_MODEL="seedance-2"
```

Current `poyo_video` support can submit Seedance 2 / Seedance 2 Fast tasks, poll status, and download returned files. It still defaults to dry-run unless the task explicitly sets `dry_run: false`.

## Dreamina / 即梦 CLI

Dreamina CLI is installed by the user, not automatically by the Skills.

Install:

```bash
curl -fsSL https://jimeng.jianying.com/cli | bash
```

Check:

```bash
dreamina -h
dreamina image2video -h
dreamina text2video -h
dreamina multiframe2video -h
```

Login:

```bash
dreamina login
```

Configure this project:

```powershell
$env:VIDEO_PROVIDER="dreamina_cli"
```

The Skill prepares a single-shot request and includes a `help_command`. Run the help command before mapping intended parameters to real CLI flags.

## ffmpeg

ffmpeg is needed when local WAV/MP3 files must be wrapped into an MP4 upload proxy for PoYo music upload flows.

Either put `ffmpeg` on PATH or set:

```powershell
$env:MUSIC_FFMPEG_BIN="E:\path\to\ffmpeg.exe"
$env:MUSIC_FFPROBE_BIN="E:\path\to\ffprobe.exe"
```

## Setup Doctor

Run:

```powershell
python scripts\setup_doctor.py
```

JSON report:

```powershell
python scripts\setup_doctor.py --json --output outputs\setup_doctor.json
```

This check is local only. It does not verify whether keys are valid, does not call paid APIs, and does not install Dreamina CLI.
