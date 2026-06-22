from typing import Dict, List

try:
    from .continuity import build_continuity_bible
    from .shot_plan import build_i2v_prompts, build_shot_plan, build_t2v_prompts
except ImportError:
    from continuity import build_continuity_bible
    from shot_plan import build_i2v_prompts, build_shot_plan, build_t2v_prompts


def build_video_handoff(task: Dict) -> Dict:
    bible = build_continuity_bible(task)
    shots = build_shot_plan(task, bible)
    return {
        "source_title": bible.get("source_title", task.get("title", "")),
        "continuity_bible": bible,
        "shots": shots,
        "i2v_prompts": build_i2v_prompts(shots),
        "t2v_prompts": build_t2v_prompts(shots),
        "seedance_prompts": build_seedance_prompts(shots),
        "edit_decision_list": build_edit_decision_list(task, shots),
        "quality_checks": build_global_quality_checks(shots),
    }


def build_seedance_prompts(shots: List[Dict]) -> List[Dict]:
    return [
        {
            "shot_id": shot["shot_id"],
            "prompt": shot["seedance_prompt"],
            "negative_prompt": shot["negative_prompt"],
            "reference_binding": shot["reference_binding"],
            "retry_advice": shot["retry_advice"],
        }
        for shot in shots
    ]


def build_edit_decision_list(task: Dict, shots: List[Dict]) -> Dict:
    music_handoff = task.get("music_handoff") or {}
    music_tasks = music_handoff.get("music_tasks") or []
    rows = []
    for index, shot in enumerate(shots, start=1):
        storyboard = shot.get("storyboard_card") or {}
        sound = storyboard.get("sound_subtitle") or {}
        rows.append(
            {
                "order": index,
                "shot_id": shot["shot_id"],
                "start_sec": shot["timing"]["start_sec"],
                "end_sec": shot["timing"]["end_sec"],
                "transition": "cut",
                "video_source": "pending_video_generation",
                "subtitle": sound.get("subtitle", ""),
                "voiceover": sound.get("voiceover", ""),
                "music_ref": _music_ref_for_shot(index, music_tasks),
                "continuity_start": shot["continuity_state"]["current_start_state"],
                "continuity_end": shot["continuity_state"]["current_end_state"],
            }
        )
    return {
        "format": task.get("target_format", "short_drama_video"),
        "timeline": rows,
        "assembly_notes": [
            "先按 EDL 顺序拼接生成片段。",
            "字幕和旁白使用每镜 sound_subtitle 字段。",
            "BGM 优先使用 music_ref；缺失时使用主题曲或场景 BGM fallback。",
            "拼接前检查每个片段首尾状态是否符合 continuity_start/continuity_end。",
        ],
    }


def build_global_quality_checks(shots: List[Dict]) -> List[Dict]:
    return [
        {
            "shot_id": shot["shot_id"],
            "must_pass": shot.get("quality_checks", []),
        }
        for shot in shots
    ]


def _music_ref_for_shot(index: int, music_tasks: List[Dict]) -> Dict:
    scene_tasks = [task for task in music_tasks if task.get("role") == "scene_bgm"]
    if scene_tasks:
        task = scene_tasks[min(index - 1, len(scene_tasks) - 1)]
        return {"role": "scene_bgm", "task_ref": task.get("task_id") or task.get("scene_ref") or index}
    theme = next((task for task in music_tasks if task.get("role") == "theme"), None)
    if theme:
        return {"role": "theme", "task_ref": theme.get("task_id") or "theme"}
    return {"role": "pending", "task_ref": ""}
