from typing import Dict, List

try:
    from .bridge_clips import build_bridge_clips
    from .clip_plan import build_clip_plan, build_clip_prompts
    from .continuity import build_continuity_bible
    from .shot_plan import build_i2v_prompts, build_shot_plan, build_t2v_prompts
    from .storyboard_assets import build_storyboard_image_tasks
except ImportError:
    from bridge_clips import build_bridge_clips
    from clip_plan import build_clip_plan, build_clip_prompts
    from continuity import build_continuity_bible
    from shot_plan import build_i2v_prompts, build_shot_plan, build_t2v_prompts
    from storyboard_assets import build_storyboard_image_tasks


def build_video_handoff(task: Dict) -> Dict:
    bible = build_continuity_bible(task)
    shots = build_shot_plan(task, bible)
    clips = build_clip_plan(task, shots, bible)
    bridge_clips = build_bridge_clips(task, clips)
    storyboard_image_tasks = build_storyboard_image_tasks(task, clips, bible)
    return {
        "source_title": bible.get("source_title", task.get("title", "")),
        "continuity_bible": bible,
        "shots": shots,
        "clip_plan": clips,
        "bridge_clips": bridge_clips,
        "storyboard_image_tasks": storyboard_image_tasks,
        "i2v_prompts": build_i2v_prompts(shots),
        "t2v_prompts": build_t2v_prompts(shots),
        "seedance_prompts": build_seedance_prompts(shots),
        "clip_prompts": build_clip_prompts(clips),
        "edit_decision_list": build_edit_decision_list(task, shots, clips, bridge_clips),
        "quality_checks": build_global_quality_checks(shots, clips, bridge_clips),
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


def build_edit_decision_list(task: Dict, shots: List[Dict], clips: List[Dict] = None, bridge_clips: List[Dict] = None) -> Dict:
    music_handoff = task.get("music_handoff") or {}
    music_tasks = music_handoff.get("music_tasks") or []
    shot_to_clip = {}
    for clip in clips or []:
        for shot_id in clip.get("shot_ids") or []:
            shot_to_clip[shot_id] = clip.get("clip_id")
    rows = []
    for index, shot in enumerate(shots, start=1):
        storyboard = shot.get("storyboard_card") or {}
        sound = storyboard.get("sound_subtitle") or {}
        rows.append(
            {
                "order": index,
                "shot_id": shot["shot_id"],
                "clip_id": shot_to_clip.get(shot["shot_id"], ""),
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
        "clip_timeline": [
            {
                "order": clip.get("order"),
                "clip_id": clip.get("clip_id"),
                "shot_ids": clip.get("shot_ids"),
                "storyboard_execution_map": clip.get("storyboard_execution_map", []),
                "start_sec": clip.get("timing", {}).get("start_sec"),
                "end_sec": clip.get("timing", {}).get("end_sec"),
                "duration_sec": clip.get("timing", {}).get("duration_sec"),
                "previous_clip_end_frame": clip.get("previous_clip_end_frame"),
                "first_frame_spec": clip.get("first_frame_spec", {}),
                "mid_frame_spec": clip.get("mid_frame_spec", {}),
                "last_frame_spec": clip.get("last_frame_spec", {}),
                "continuity_start": clip.get("continuity_state", {}).get("current_start_state"),
                "continuity_end": clip.get("continuity_state", {}).get("current_end_state"),
            }
            for clip in clips or []
        ],
        "bridge_timeline": [
            {
                "clip_id": bridge.get("clip_id"),
                "after_clip_id": bridge.get("after_clip_id"),
                "before_clip_id": bridge.get("before_clip_id"),
                "bridge_type": bridge.get("bridge_type"),
                "duration_sec": bridge.get("timing", {}).get("duration_sec"),
                "visual": bridge.get("visual"),
                "purpose": "遮挡跳切、统一色调、缓冲换机位或换景别",
            }
            for bridge in bridge_clips or []
        ],
        "assembly_notes": [
            "先按 EDL 顺序拼接生成片段。",
            "视频生成优先按 clip_timeline 生成 5-15 秒连续片段；shot timeline 用于内部分镜和剪辑检查。",
            "字幕和旁白使用每镜 sound_subtitle 字段。",
            "BGM 优先使用 music_ref；缺失时使用主题曲或场景 BGM fallback。",
            "拼接前检查每个片段首尾状态是否符合 continuity_start/continuity_end。",
            "每个 clip 的 storyboard_execution_map 必须完整覆盖 clip_timeline.shot_ids，视频镜头顺序必须等于故事板顺序。",
            "不得为了凑 15 秒长镜头而删除、合并掉、改顺序或改动作；需要调整时先修订故事板并获得确认。",
            "每个 clip 的首帧、中段、尾帧应同时对齐 first_frame_spec、mid_frame_spec、last_frame_spec。",
            "如 bridge_timeline 存在，先用桥接空镜/道具特写缓冲上下镜头，再切入下一人物镜头。",
            "跨 clip 续接时先声明 continuation_mode；单帧截取只服务连续性参考，除 hard_first_frame 外不得自动变成下一段首帧。",
        ],
    }


def build_global_quality_checks(shots: List[Dict], clips: List[Dict] = None, bridge_clips: List[Dict] = None) -> Dict:
    return {
        "shots": [
        {
            "shot_id": shot["shot_id"],
            "must_pass": shot.get("quality_checks", []),
        }
        for shot in shots
        ],
        "clips": [
            {
                "clip_id": clip.get("clip_id"),
                "shot_ids": clip.get("shot_ids", []),
                "must_pass": clip.get("quality_checks", []),
            }
            for clip in clips or []
        ],
        "bridges": [
            {
                "clip_id": bridge.get("clip_id"),
                "after_clip_id": bridge.get("after_clip_id"),
                "before_clip_id": bridge.get("before_clip_id"),
                "must_pass": bridge.get("quality_checks", []),
            }
            for bridge in bridge_clips or []
        ],
    }


def _music_ref_for_shot(index: int, music_tasks: List[Dict]) -> Dict:
    scene_tasks = [task for task in music_tasks if task.get("role") == "scene_bgm"]
    if scene_tasks:
        task = scene_tasks[min(index - 1, len(scene_tasks) - 1)]
        return {"role": "scene_bgm", "task_ref": task.get("task_id") or task.get("scene_ref") or index}
    theme = next((task for task in music_tasks if task.get("role") == "theme"), None)
    if theme:
        return {"role": "theme", "task_ref": theme.get("task_id") or "theme"}
    return {"role": "pending", "task_ref": ""}
