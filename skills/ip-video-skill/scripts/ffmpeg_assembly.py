"""Future local assembly helpers for EDL-to-video workflows.

Phase 1 intentionally does not assemble video. Keep this module as the stable
future boundary for ffmpeg concat, subtitle, voiceover, and BGM utilities.
"""


def assembly_not_implemented() -> str:
    return "ffmpeg assembly is planned for phase 3; build_edit_decision_list is available now."
