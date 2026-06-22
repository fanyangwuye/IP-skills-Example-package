from typing import Dict, List


STORYBOARD_DESIGN_REQUIREMENTS = [
    "storyboard content design sheet for video planning",
    "show three key panels: start state, main action beat, end state",
    "keep the same characters, costume, props, scene layout, light direction, and color tone",
    "normal perspective cinematic frames, not 720 panorama projection",
    "clean production reference layout, not a final poster",
    "no dialogue subtitles inside panels",
    "no title card, watermark, fake UI, or decorative text inside panels",
    "if production labels are needed, place only short Simplified Chinese labels outside the image panels",
]

MARTIAL_ARTS_STORYBOARD_REQUIREMENTS = [
    "for martial arts clips, show clear starting stance, one readable attack-defense beat, and ending pose",
    "show distance, footwork, body weight shift, weapon or limb path, and reaction beat",
    "no blood, gore, wound close-up, broken limb, speed lines, attack labels, arrows, numbers, or UI overlays",
]


def build_storyboard_image_tasks(task: Dict, clips: List[Dict], continuity_bible: Dict) -> List[Dict]:
    output_dir = task.get("storyboard_output_dir") or task.get("output_dir") or ""
    common = _common_fields(task)
    return [_build_storyboard_task(clip, continuity_bible, output_dir, common) for clip in clips]


def _build_storyboard_task(clip: Dict, continuity_bible: Dict, output_dir: str, common: Dict) -> Dict:
    clip_id = clip.get("clip_id", "clip")
    timing = clip.get("timing") or {}
    continuity_state = clip.get("continuity_state") or {}
    scene_locks = continuity_bible.get("scene_locks") or {}
    character_locks = continuity_bible.get("character_locks") or {}
    scene_summary = [_scene_text(scene_locks.get(scene_id, {})) for scene_id in (clip.get("scene_ids") or [])]
    character_summary = [_character_text(character_locks.get(char_id, {})) for char_id in (clip.get("characters") or [])]

    return {
        **common,
        "mode": "text_to_image",
        "creation_stage": "storyboard_content_design",
        "current_focus": f"generate storyboard content design sheet: {clip_id}",
        "asset_kind": "storyboard_content_design_sheet",
        "creative_goal": "Create a production storyboard image that can guide image-to-video generation while preserving IP continuity.",
        "storyboard_profile": {
            "clip_id": clip_id,
            "duration_sec": timing.get("duration_sec"),
            "shot_ids": clip.get("shot_ids", []),
            "characters": character_summary,
            "scenes": scene_summary,
            "start_state": continuity_state.get("current_start_state", ""),
            "main_action": continuity_state.get("main_action_transition", ""),
            "end_state": continuity_state.get("current_end_state", ""),
            "visual": clip.get("visual", ""),
            "martial_arts_layer": clip.get("martial_arts_layer", {}),
        },
        "scene": clip.get("visual", ""),
        "camera": "three-panel storyboard sheet: start frame, main action frame, end frame; stable cinematic perspective",
        "composition": (
            "horizontal 3-panel production storyboard, panel 1 start state, panel 2 main action beat, "
            "panel 3 end state; consistent character placement and scene anchors across panels"
        ),
        "lighting": _lighting_text(scene_locks, clip.get("scene_ids") or []),
        "asset_target": {
            "type": "storyboard content design sheet",
            "purpose": "visual reference for clip-level image-to-video generation",
            "clip_id": clip_id,
            "duration_sec": timing.get("duration_sec"),
        },
        "asset_requirements": _asset_requirements(clip),
        "reference_binding": clip.get("reference_binding", {}),
        "video_reference_images": clip.get("video_reference_images", []),
        "space_anchor_refs": clip.get("space_anchor_refs", []),
        "continuity_state": continuity_state,
        "visual_text_language": common.get("visual_text_language", "zh-CN"),
        "visible_text_requirements": [
            "默认使用简体中文生产标签",
            "只允许短标签：起始、动作、结束、角色、场景、光源",
            "不要生成对白字幕、剧情长段落、小字号说明、片名、标题卡或水印",
            "所有标签必须放在面板外侧边距，不要叠在视频画面区域里",
        ],
        "gpt_image_2_spec": {
            "model": "gpt-image-2",
            "recommended_size": task_size(common),
            "recommended_resolution": common.get("storyboard_resolution", common.get("resolution", "2K")),
            "note": "Storyboard design sheet is a planning reference for I2V, not the final video frame.",
        },
        "quality": common.get("storyboard_quality", common.get("quality", "high")),
        "size": task_size(common),
        "resolution": common.get("storyboard_resolution", common.get("resolution", "2K")),
        "filename": f"{clip_id}_storyboard_design_sheet.jpg",
        "output_dir": output_dir,
    }


def task_size(common: Dict) -> str:
    return common.get("storyboard_size", "16:9")


def _asset_requirements(clip: Dict) -> List[str]:
    requirements = list(STORYBOARD_DESIGN_REQUIREMENTS)
    if clip.get("martial_arts_layer"):
        requirements.extend(MARTIAL_ARTS_STORYBOARD_REQUIREMENTS)
    return requirements


def _common_fields(task: Dict) -> Dict:
    return {
        key: task[key]
        for key in (
            "ip_id",
            "style_preset",
            "style_card_path",
            "reference_image_urls",
            "style_reference_paths",
            "quality",
            "resolution",
            "visual_text_language",
            "storyboard_size",
            "storyboard_resolution",
            "storyboard_quality",
        )
        if key in task
    }


def _character_text(lock: Dict) -> str:
    if not lock:
        return ""
    return (
        f"{lock.get('name', '')}: face={lock.get('face_lock', '')}, hair={lock.get('hair_lock', '')}, "
        f"costume={lock.get('costume_lock', '')}, props={lock.get('prop_locks', [])}"
    )


def _scene_text(lock: Dict) -> str:
    if not lock:
        return ""
    return (
        f"{lock.get('name', '')}: layout={lock.get('layout_lock', '')}, landmarks={lock.get('landmark_lock', [])}, "
        f"lighting={lock.get('lighting_lock', '')}, palette={lock.get('palette_lock', '')}"
    )


def _lighting_text(scene_locks: Dict, scene_ids: List[str]) -> str:
    parts = []
    for scene_id in scene_ids:
        lock = scene_locks.get(scene_id, {})
        if lock.get("lighting_lock"):
            parts.append(str(lock["lighting_lock"]))
    return "；".join(parts)
