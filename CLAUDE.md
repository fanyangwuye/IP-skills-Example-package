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
-> locked reference policy: all-purpose reference or explicitly approved keyframe image
-> I2V clip
-> extracted tail frame
-> next clip or bridge clip
-> continuity check
```

Rules:

- Obey the locked project reference policy. If `reference_policy: all_purpose_reference` is set, live video must use `reference_image_urls` only and must not be rewritten into `image_urls`, first-frame, last-frame, previous-tail-frame, or keyframe I2V.
- Use `image_urls[0]` first-frame/keyframe only when the project explicitly selects that policy; never substitute it for all-purpose reference.
- Treat extracted single frames only as clip-boundary continuity references; never use them as identity locks, default first frames, or replacements for all-purpose references.
- Storyboard crops are layout references only; do not treat line-art storyboard style as final video style.
- Storyboard is the execution blueprint once it exists. Every live clip must carry `storyboard_execution_map`, and video shot order must exactly match storyboard `shot_ids`.
- Do not delete, merge away, reorder, or rewrite storyboard shots to fit a 15-second clip. Split into shorter generated units or revise the storyboard with user approval.
- Prompt text may only strengthen details already present in references and storyboard; it must not add, modify, or reduce locked content.
- Paid/live PoYo video must default to `seedance-2`, not `seedance-2-fast`. Use `seedance-2-fast` only if the user explicitly asks for fast mode and the task sets `allow_fast_model=true`.
- Keep video model audio limited to ambient sound and foley. Do not generate background music, songs, subtitles, title cards, fake text, or watermarks.
- Do not place new project assets, generated videos, task JSON, or review frames under `C:\Users` by default. Prefer `IP_SKILLS_OUTPUT_ROOT` on a non-C drive, such as `E:\Plans for 2026\ip-skills\outputs`; ask before moving existing assets.
- Never commit `.env`, `outputs/`, `logs/`, generated videos, generated images, or API keys.
- Use `python scripts/setup_doctor.py` for environment checks.
- Use `docs/agent_config.md` for Codex, Claude Code, OpenClaw, and generic agent setup.

Useful invocation:

```text
Use the IP skills in this repository to run the full workflow. Do not skip character sheets, scene refs, storyboard/shot table, reference policy, I2V, tail-frame handoff, or continuity checks.
```