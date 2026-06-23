# Claude Code Project Instructions

Use this repository as an agent-facing IP creation skills package.

Before executing an IP workflow, read the relevant skill files:

- `skills/ip-copy-skill/SKILL.md`
- `skills/ip-image-skill/SKILL.md`
- `skills/ip-music-skill/SKILL.md`
- `skills/ip-video-skill/SKILL.md`

For full video production, do not skip the standard chain:

```text
script/copy input
-> IP asset pack
-> character design sheet with facial-geometry lock
-> scene reference image
-> professional storyboard / shot table
-> reviewed first-frame or keyframe image
-> I2V clip
-> extracted tail frame
-> next clip or bridge clip
-> continuity check
```

Rules:

- Do not run live video from weak `reference_image_urls` only when a character is present.
- Character video clips must start from a reviewed character keyframe passed as `image_urls[0]`.
- Storyboard crops are layout references only; do not treat line-art storyboard style as final video style.
- Keep video model audio limited to ambient sound and foley. Do not generate background music, songs, subtitles, title cards, fake text, or watermarks.
- Never commit `.env`, `outputs/`, `logs/`, generated videos, generated images, or API keys.
- Use `python scripts/setup_doctor.py` for environment checks.
- Use `docs/agent_config.md` for Codex, Claude Code, OpenClaw, and generic agent setup.

Useful invocation:

```text
Use the IP skills in this repository to run the full workflow. Do not skip character sheets, scene refs, storyboard/shot table, keyframes, I2V, tail-frame handoff, or continuity checks.
```

