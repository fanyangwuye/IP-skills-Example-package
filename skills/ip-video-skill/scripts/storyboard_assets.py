from typing import Dict, List


STORYBOARD_DESIGN_REQUIREMENTS = [
    "professional production storyboard board for video planning, not a free manga draft",
    "each panel must map to a real video clip shot or key timepoint",
    "panel 1 must match the intended video first frame composition",
    "first frame composition alignment: same aspect ratio, camera height, camera angle, subject scale, screen direction, and room anchors",
    "camera angle lock: keep the same camera side and lens perspective unless a planned camera move changes it inside the clip",
    "subject scale lock: character size in the panel must match the intended generated video frame",
    "pose lock: panel 1 must show the first-frame body pose, not the mid-action pose",
    "blocking lock: furniture, doors, windows, lamps, wall signs, and character positions must match the frame spec",
    "action phase lock: panel 1 is the pre-action/action-start frame; do not advance it to the middle or ending beat",
    "screen direction lock: character left/right placement, movement direction, and eyeline must stay consistent",
    "mid and tail panels must preserve the same scene layout, light direction, and spatial anchors",
    "use clean production sketch linework with restrained grayscale shading; panels are planning frames, not final photoreal stills",
    "show enough panels to tell the clip story according to duration",
    "panel sequence must cover start state, action development, key turn, and end state",
    "keep the same characters, costume, props, scene layout, light direction, and color tone",
    "normal perspective cinematic frames, not 720 panorama projection",
    "multi-shot storyboard layout or shot table, not a final poster",
    "place production labels and notes outside panel image areas or in table cells",
    "no dialogue subtitles inside panels",
    "no title card, watermark, fake UI, or decorative text inside panels",
    "if production labels are needed, place only short Simplified Chinese labels outside the image panels",
]

MARTIAL_ARTS_STORYBOARD_REQUIREMENTS = [
    "martial_action_storyboard must use 8-12 action breakdown panels",
    "for martial arts clips, show clear starting stance, one readable attack-defense beat, reaction pause, and ending pose",
    "show distance, footwork, body weight shift, weapon or limb path, and reaction beat",
    "use red arrows for attack, eyeline, and movement paths; use blue arrows for camera move, footwork, and dodge paths",
    "arrows must be clean production direction marks, not comic speed effects",
    "no blood, gore, wound close-up, broken limb, speed lines, attack labels, technique names, numbers, or UI overlays",
]


def build_storyboard_image_tasks(task: Dict, clips: List[Dict], continuity_bible: Dict) -> List[Dict]:
    output_dir = task.get("storyboard_output_dir") or task.get("output_dir") or ""
    common = _common_fields(task)
    tasks = []
    for clip in clips:
        for storyboard_type in _storyboard_types(task, clip):
            tasks.append(_build_storyboard_task(clip, continuity_bible, output_dir, common, storyboard_type))
    return tasks


def _build_storyboard_task(clip: Dict, continuity_bible: Dict, output_dir: str, common: Dict, storyboard_type: str) -> Dict:
    clip_id = clip.get("clip_id", "clip")
    timing = clip.get("timing") or {}
    continuity_state = clip.get("continuity_state") or {}
    scene_locks = continuity_bible.get("scene_locks") or {}
    character_locks = continuity_bible.get("character_locks") or {}
    scene_summary = [_scene_text(scene_locks.get(scene_id, {})) for scene_id in (clip.get("scene_ids") or [])]
    character_summary = [_character_text(character_locks.get(char_id, {})) for char_id in (clip.get("characters") or [])]
    panel_count = _panel_count(timing.get("duration_sec"), storyboard_type)
    first_frame_spec = clip.get("first_frame_spec", {})
    mid_frame_spec = clip.get("mid_frame_spec", {})
    last_frame_spec = clip.get("last_frame_spec", {})

    return {
        **common,
        "mode": "text_to_image",
        "creation_stage": "video_storyboard_blueprint",
        "current_focus": f"generate {storyboard_type}: {clip_id}",
        "asset_kind": storyboard_type,
        "creative_goal": _creative_goal(storyboard_type),
        "storyboard_profile": {
            "clip_id": clip_id,
            "storyboard_type": storyboard_type,
            "duration_sec": timing.get("duration_sec"),
            "panel_count": panel_count,
            "shot_ids": clip.get("shot_ids", []),
            "characters": character_summary,
            "scenes": scene_summary,
            "first_frame_spec": first_frame_spec,
            "mid_frame_spec": mid_frame_spec,
            "last_frame_spec": last_frame_spec,
            "start_state": continuity_state.get("current_start_state", ""),
            "main_action": continuity_state.get("main_action_transition", ""),
            "end_state": continuity_state.get("current_end_state", ""),
            "visual": clip.get("visual", ""),
            "martial_arts_layer": clip.get("martial_arts_layer", {}),
        },
        "scene": clip.get("visual", ""),
        "camera": _camera_prompt(storyboard_type, panel_count, first_frame_spec, mid_frame_spec, last_frame_spec),
        "composition": _composition_prompt(storyboard_type, panel_count, first_frame_spec),
        "lighting": _lighting_text(scene_locks, clip.get("scene_ids") or []),
        "asset_target": {
            "type": storyboard_type,
            "purpose": "visual reference for clip-level image-to-video generation",
            "clip_id": clip_id,
            "duration_sec": timing.get("duration_sec"),
            "first_frame_spec": first_frame_spec,
            "mid_frame_spec": mid_frame_spec,
            "last_frame_spec": last_frame_spec,
        },
        "asset_requirements": _asset_requirements(clip, storyboard_type),
        "reference_binding": clip.get("reference_binding", {}),
        "video_reference_images": clip.get("video_reference_images", []),
        "space_anchor_refs": clip.get("space_anchor_refs", []),
        "continuity_state": continuity_state,
        "visual_text_language": common.get("visual_text_language", "zh-CN"),
        "visible_text_requirements": [
            "默认使用简体中文生产标签",
            "只允许短标签：起始、推进、转折、结束、角色、场景、光源",
            "不要生成对白字幕、剧情长段落、小字号说明、片名、标题卡或水印",
            "所有标签必须放在面板外侧边距或表格栏内，不要叠在视频画面主体区域里",
        ],
        "gpt_image_2_spec": {
            "model": "gpt-image-2",
            "recommended_size": task_size(common),
            "recommended_resolution": common.get("storyboard_resolution", common.get("resolution", "2K")),
            "note": "Storyboard board is a composition and action blueprint for I2V; panel 1 must align with the intended first frame.",
        },
        "quality": common.get("storyboard_quality", common.get("quality", "high")),
        "size": task_size(common),
        "resolution": common.get("storyboard_resolution", common.get("resolution", "2K")),
        "filename": f"{clip_id}_{storyboard_type}.jpg",
        "output_dir": output_dir,
    }


def task_size(common: Dict) -> str:
    return common.get("storyboard_size", "16:9")


def _panel_count(duration_sec, storyboard_type: str = "clip_storyboard_board") -> int:
    try:
        duration = float(duration_sec or 0)
    except (TypeError, ValueError):
        duration = 0
    if storyboard_type == "martial_action_storyboard":
        if duration <= 6:
            return 8
        if duration <= 10:
            return 10
        return 12
    if storyboard_type == "shot_table_storyboard":
        if duration <= 6:
            return 3
        return 5
    if duration <= 6:
        return 3
    if duration <= 15:
        return 5
    return 6


def _asset_requirements(clip: Dict, storyboard_type: str) -> List[str]:
    requirements = list(STORYBOARD_DESIGN_REQUIREMENTS)
    if storyboard_type == "clip_storyboard_board":
        requirements.extend(
            [
                "clip_storyboard_board: normal short-drama camera board with start, middle, and tail panels",
                "first panel must be the exact first-frame blueprint for the video provider",
                "普通短剧分镜要标清远景/中景/近景、机位方向、人物视线、空间锚点和情绪落点",
            ]
        )
    if storyboard_type == "shot_table_storyboard":
        requirements.extend(
            [
                "shot_table_storyboard: use a table format with columns for 镜头号, 画面/构图, 摄影机运动, 动作/表演, 台词/声音, 时长/时间点",
                "text notes must live in table cells outside the frame drawings",
                "each row must correspond to one real shot or key timepoint in the clip",
            ]
        )
    if storyboard_type == "martial_action_storyboard" or clip.get("martial_arts_layer"):
        requirements.extend(MARTIAL_ARTS_STORYBOARD_REQUIREMENTS)
    return requirements


def _storyboard_types(task: Dict, clip: Dict) -> List[str]:
    explicit = task.get("storyboard_types")
    if explicit:
        values = explicit if isinstance(explicit, list) else [explicit]
        return [_normalize_storyboard_type(value, clip) for value in values]
    if task.get("storyboard_type"):
        return [_normalize_storyboard_type(task["storyboard_type"], clip)]
    if clip.get("martial_arts_layer"):
        return ["martial_action_storyboard"]
    return ["clip_storyboard_board"]


def _normalize_storyboard_type(value, clip: Dict) -> str:
    value = str(value or "").strip()
    allowed = {"clip_storyboard_board", "shot_table_storyboard", "martial_action_storyboard"}
    if value in allowed:
        return value
    return "martial_action_storyboard" if clip.get("martial_arts_layer") else "clip_storyboard_board"


def _creative_goal(storyboard_type: str) -> str:
    if storyboard_type == "shot_table_storyboard":
        return "Create a professional shot-table storyboard that shares first/mid/last frame composition specs with video generation."
    if storyboard_type == "martial_action_storyboard":
        return "Create a martial-arts action storyboard that breaks down readable movement while aligning the first panel to the video first frame."
    return "Create a professional clip storyboard board that can directly guide image-to-video generation while preserving IP continuity."


def _camera_prompt(storyboard_type: str, panel_count: int, first: Dict, mid: Dict, last: Dict) -> str:
    if storyboard_type == "shot_table_storyboard":
        return (
            "shot table storyboard with camera columns; each row names camera height, camera angle lock, subject scale lock, "
            "screen direction lock, camera movement, and timepoint"
        )
    if storyboard_type == "martial_action_storyboard":
        return (
            f"{panel_count}-panel martial action breakdown; panel 1 must match first frame composition alignment; "
            "red arrows show attack/eyeline/movement, blue arrows show camera/footwork/dodge; "
            f"first={_frame_brief(first)}; mid={_frame_brief(mid)}; last={_frame_brief(last)}"
        )
    return (
        f"{panel_count}-panel production storyboard board; panel 1 must match intended video first frame; "
        f"first={_frame_brief(first)}; mid={_frame_brief(mid)}; last={_frame_brief(last)}"
    )


def _composition_prompt(storyboard_type: str, panel_count: int, first: Dict) -> str:
    base = (
        "panel 1 must match the intended video first frame composition: "
        f"camera angle lock={first.get('camera_angle_lock', '')}; "
        f"subject scale lock={first.get('subject_scale_lock', '')}; "
        f"pose lock={first.get('pose_lock', '')}; "
        f"blocking lock={first.get('blocking_lock', '')}; "
        f"action phase lock={first.get('action_phase_lock', '')}; "
        f"screen direction lock={first.get('screen_direction_lock', '')}; "
        f"scene anchor lock={first.get('scene_anchor_lock', '')}. "
        "Panel 1 must not skip ahead to the mid-action pose. All later panels keep the same space anchors and light direction."
    )
    if storyboard_type == "shot_table_storyboard":
        return (
            "professional storyboard shooting table; columns: 镜头号 / 画面与构图 / 摄影机运动 / 动作表演 / 台词声音 / 时长或时间点; "
            + base
        )
    if storyboard_type == "martial_action_storyboard":
        return (
            f"horizontal {panel_count}-panel martial action storyboard, readable production arrows, notes outside panels; "
            + base
        )
    return (
        f"horizontal {panel_count}-panel short-drama storyboard board; panels read left to right; each panel is one camera beat; "
        + base
    )


def _frame_brief(spec: Dict) -> str:
    return (
        f"{spec.get('kind', '')} {spec.get('time_sec', '')}s, shot={spec.get('source_shot_id', '')}, "
        f"framing={spec.get('framing', '')}, screen={spec.get('screen_direction_lock', '')}"
    )


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
