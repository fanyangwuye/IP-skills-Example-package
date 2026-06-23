from typing import Dict, List, Optional

try:
    from .martial_arts import build_martial_arts_layer, is_martial_arts_scene, martial_arts_text
except ImportError:
    from martial_arts import build_martial_arts_layer, is_martial_arts_scene, martial_arts_text


def build_clip_plan(task: Dict, shots: List[Dict], continuity_bible: Dict) -> List[Dict]:
    target_duration = _positive_float(task.get("target_clip_duration_sec") or task.get("clip_duration_sec"), 15.0)
    max_duration = _positive_float(task.get("max_clip_duration_sec"), 15.0)
    target_duration = min(target_duration, max_duration)

    clips: List[Dict] = []
    current: List[Dict] = []
    current_duration = 0.0

    for shot in shots:
        shot_duration = _shot_duration(shot)
        if current and current_duration + shot_duration > target_duration:
            clips.append(_build_clip(len(clips) + 1, current, task, continuity_bible))
            current = []
            current_duration = 0.0
        current.append(shot)
        current_duration += shot_duration

    if current:
        clips.append(_build_clip(len(clips) + 1, current, task, continuity_bible))
    return clips


def build_clip_prompts(clips: List[Dict]) -> List[Dict]:
    return [
        {
            "clip_id": clip["clip_id"],
            "shot_ids": clip["shot_ids"],
            "prompt": clip["clip_prompt"],
            "negative_prompt": clip["negative_prompt"],
            "reference_binding": clip["reference_binding"],
            "video_reference_images": clip["video_reference_images"],
            "space_anchor_refs": clip["space_anchor_refs"],
            "first_frame_spec": clip.get("first_frame_spec", {}),
            "mid_frame_spec": clip.get("mid_frame_spec", {}),
            "last_frame_spec": clip.get("last_frame_spec", {}),
            "martial_arts_layer": clip.get("martial_arts_layer", {}),
            "previous_clip_end_frame": clip.get("previous_clip_end_frame"),
            "continuity_state": clip["continuity_state"],
            "retry_advice": clip["retry_advice"],
        }
        for clip in clips
    ]


def _build_clip(index: int, shots: List[Dict], task: Dict, bible: Dict) -> Dict:
    clip_id = f"clip_{index:03d}"
    first = shots[0]
    last = shots[-1]
    timing = _clip_timing(shots)
    scene_ids = _dedupe([shot.get("scene_id") for shot in shots if shot.get("scene_id")])
    characters = _dedupe([char for shot in shots for char in (shot.get("characters") or [])])
    continuity_state = {
        "previous_end_state": first.get("continuity_state", {}).get("previous_end_state", ""),
        "current_start_state": first.get("continuity_state", {}).get("current_start_state", ""),
        "main_action_transition": " / ".join(_shot_action(shot) for shot in shots),
        "current_end_state": last.get("continuity_state", {}).get("current_end_state", ""),
        "next_handoff": last.get("continuity_state", {}).get("next_handoff", ""),
    }
    reference_binding = _merge_reference_binding(shots)
    video_refs = _video_reference_images(task, scene_ids, characters)
    space_refs = _space_anchor_refs(task, scene_ids, bible)
    frame_specs = _frame_specs(shots, bible, timing)
    martial_arts_layer = build_martial_arts_layer(
        "；".join(shot.get("visual", "") for shot in shots),
        _clip_storyboard_card(shots),
        continuity_state,
    ) if any(is_martial_arts_scene(shot.get("visual", ""), shot.get("storyboard_card", {}).get("action_scene_type", "")) for shot in shots) else {}

    return {
        "clip_id": clip_id,
        "order": index,
        "shot_ids": [shot.get("shot_id", "") for shot in shots],
        "timing": timing,
        "visual": "；".join(shot.get("visual", "") for shot in shots if shot.get("visual")),
        "characters": characters,
        "scene_ids": scene_ids,
        "visual_lock": _merge_visual_lock(shots, bible),
        "reference_binding": reference_binding,
        "video_reference_images": video_refs,
        "space_anchor_refs": space_refs,
        "first_frame_spec": frame_specs["first_frame_spec"],
        "mid_frame_spec": frame_specs["mid_frame_spec"],
        "last_frame_spec": frame_specs["last_frame_spec"],
        "martial_arts_layer": martial_arts_layer,
        "previous_clip_end_frame": _previous_clip_end_frame(task, index, clip_id),
        "continuity_state": continuity_state,
        "clip_prompt": _clip_prompt(clip_id, timing, shots, continuity_state, video_refs, space_refs, martial_arts_layer, frame_specs),
        "i2v_prompt": _clip_prompt(clip_id, timing, shots, continuity_state, video_refs, space_refs, martial_arts_layer, frame_specs),
        "seedance_prompt": _clip_prompt(clip_id, timing, shots, continuity_state, video_refs, space_refs, martial_arts_layer, frame_specs),
        "t2v_prompt": _clip_prompt(clip_id, timing, shots, continuity_state, video_refs, space_refs, martial_arts_layer, frame_specs),
        "negative_prompt": _merge_negative_prompt(shots),
        "retry_advice": _dedupe([item for shot in shots for item in (shot.get("retry_advice") or [])]),
        "quality_checks": _clip_quality_checks(),
    }


def _clip_timing(shots: List[Dict]) -> Dict:
    start = float(shots[0].get("timing", {}).get("start_sec", 0))
    end = float(shots[-1].get("timing", {}).get("end_sec", start + sum(_shot_duration(shot) for shot in shots)))
    return {"start_sec": start, "end_sec": end, "duration_sec": max(end - start, 1.0)}


def _shot_duration(shot: Dict) -> float:
    timing = shot.get("timing") or {}
    if timing.get("duration_sec"):
        return float(timing["duration_sec"])
    return max(float(timing.get("end_sec", 1)) - float(timing.get("start_sec", 0)), 1.0)


def _shot_action(shot: Dict) -> str:
    return shot.get("continuity_state", {}).get("main_action_transition") or shot.get("visual", "")


def _clip_prompt(
    clip_id: str,
    timing: Dict,
    shots: List[Dict],
    continuity_state: Dict,
    video_refs: List[Dict],
    space_refs: List[Dict],
    martial_arts_layer: Dict,
    frame_specs: Dict,
) -> str:
    shot_lines = []
    for order, shot in enumerate(shots, start=1):
        shot_lines.append(f"{order}. {shot.get('visual', '')}；镜头控制：{shot.get('storyboard_card', {}).get('camera_motion', '')}")
    video_ref_note = "；".join(_ref_label(ref) for ref in video_refs) or "使用已锁定角色图和正常场景参考图"
    space_ref_note = "；".join(_ref_label(ref) for ref in space_refs) or "全景图仅作为空间锚点"
    return (
        f"{clip_id} 连续视频片段，时长约 {timing.get('duration_sec')} 秒。"
        f"起始状态：{continuity_state.get('current_start_state')}。"
        f"动作段落：{' '.join(shot_lines)}。"
        f"结束状态：{continuity_state.get('current_end_state')}。"
        f"视频生成参考：{video_ref_note}。"
        f"空间锚点：{space_ref_note}；全景图用于校准空间布局、地标和光源方向，默认不要作为直接生成画面。"
        f"{_frame_specs_text(frame_specs)}"
        f"{_optional_sentence('武戏调度', martial_arts_text(martial_arts_layer))}"
        "保持同一角色脸、发型、服饰、道具、场景布局、光影色调和屏幕方向；片段内部动作连续，不要跳切、不要重置空间。"
        "跨 clip 衔接不等于每段都复制上一段构图；除非明确使用 hard_first_frame，否则允许用近景、特写、全景、远景、背影、反打、空镜、道具插入或手部局部来承接。"
        "换景别时必须继承上一段的人物状态、服饰、道具所在手、动作余势、光源方向、曝光、白平衡和色彩，不要把切镜头误生成换场景。"
        "声音只保留现场环境声与拟音，例如风声、雨声、脚步、衣料摩擦、呼吸、门响和道具轻响；禁止背景音乐、歌曲、音乐铺底。"
        "画面禁止字幕、伪文字、水印、片头片尾、标题卡和解释性文字。"
    )


def _frame_specs(shots: List[Dict], bible: Dict, timing: Dict) -> Dict:
    first = shots[0]
    mid = shots[len(shots) // 2]
    last = shots[-1]
    start = float(timing.get("start_sec", 0))
    end = float(timing.get("end_sec", start + timing.get("duration_sec", 1)))
    mid_time = start + max(end - start, 1.0) / 2
    return {
        "first_frame_spec": _frame_spec("first_frame", start, first, bible, "video first frame; storyboard panel 1 must match this composition"),
        "mid_frame_spec": _frame_spec("mid_frame", mid_time, mid, bible, "video middle frame; keep the same camera side and space anchors"),
        "last_frame_spec": _frame_spec("last_frame", end, last, bible, "video tail frame; becomes continuity handoff for the next clip"),
    }


def _frame_spec(kind: str, time_sec: float, shot: Dict, bible: Dict, purpose: str) -> Dict:
    card = shot.get("storyboard_card") or {}
    scene_id = shot.get("scene_id", "")
    scene_lock = (bible.get("scene_locks") or {}).get(scene_id) or {}
    characters = shot.get("characters") or []
    return {
        "kind": kind,
        "time_sec": round(float(time_sec), 2),
        "source_shot_id": shot.get("shot_id", ""),
        "purpose": purpose,
        "composition": shot.get("visual", ""),
        "framing": card.get("framing", ""),
        "camera_motion_context": card.get("camera_motion", ""),
        "camera_angle_lock": _camera_angle_lock(card),
        "camera_height_lock": "same camera height across storyboard panel and generated video frame",
        "subject_scale_lock": _subject_scale_lock(card, characters),
        "pose_lock": _pose_lock(kind, shot, characters),
        "blocking_lock": _blocking_lock(shot, characters),
        "action_phase_lock": _action_phase_lock(kind),
        "screen_direction_lock": card.get("screen_direction") or shot.get("screen_direction", {}),
        "eyeline_lock": card.get("eyeline") or shot.get("eyeline", {}),
        "axis_lock": card.get("axis") or shot.get("axis", {}),
        "scene_anchor_lock": {
            "scene_id": scene_id,
            "layout": scene_lock.get("layout_lock", ""),
            "landmarks": scene_lock.get("landmark_lock", []),
            "lighting": scene_lock.get("lighting_lock", ""),
            "palette": scene_lock.get("palette_lock", ""),
        },
        "continuity_state": {
            "start": (shot.get("continuity_state") or {}).get("current_start_state", ""),
            "action": (shot.get("continuity_state") or {}).get("main_action_transition", ""),
            "end": (shot.get("continuity_state") or {}).get("current_end_state", ""),
        },
        "alignment_checks": [
            "first frame composition alignment" if kind == "first_frame" else f"{kind} composition alignment",
            "camera angle lock",
            "subject scale lock",
            "screen direction lock",
            "scene anchor lock",
            "lighting direction lock",
        ],
    }


def _camera_angle_lock(card: Dict) -> str:
    framing = card.get("framing", "")
    camera_motion = card.get("camera_motion", "")
    return f"{framing}; maintain one camera side and angle while allowing only the planned motion: {camera_motion}".strip("; ")


def _subject_scale_lock(card: Dict, characters: List[str]) -> str:
    subject = "、".join(characters) if characters else "主要环境主体"
    return f"{subject} size in frame follows {card.get('framing', 'planned framing')}; do not suddenly zoom wider or tighter than the frame spec"


def _pose_lock(kind: str, shot: Dict, characters: List[str]) -> str:
    visual = shot.get("visual", "")
    primary = characters[0] if characters else "主体"
    secondary = characters[1] if len(characters) >= 2 else "另一角色"
    if kind == "first_frame" and any(word in visual for word in ["猛然睁眼", "惊醒", "醒来"]) and "床" in visual:
        return (
            f"{primary} is on the bed at the first instant of waking, lying or half-lying with eyes just opening; "
            f"do not show {primary} already fully sitting upright. {secondary} stays in the established opposite/right-side position."
        )
    if kind == "first_frame":
        return "show the start pose before the main action completes; do not skip ahead to the middle or ending pose"
    if kind == "mid_frame":
        return "show the main action in progress, after the first pose but before the ending pose"
    return "show the ending pose and result of the action, ready for the next continuity handoff"


def _blocking_lock(shot: Dict, characters: List[str]) -> str:
    visual = shot.get("visual", "")
    card = shot.get("storyboard_card") or {}
    screen = card.get("screen_direction") or shot.get("screen_direction", {})
    subject = "、".join(characters) if characters else "主体"
    bed_note = " bed remains the primary foreground anchor;" if "床" in visual else ""
    return (
        f"{subject} blocking follows screen_direction_lock and eyeline_lock;{bed_note} "
        "keep furniture, doors, windows, desk, lamps, and wall signs in stable positions across first/mid/last frames"
        f"; screen_direction={screen}"
    )


def _action_phase_lock(kind: str) -> str:
    if kind == "first_frame":
        return "first frame is the pre-action or action-start frame; storyboard panel 1 must not depict the mid-frame or tail-frame result"
    if kind == "mid_frame":
        return "middle frame is the action-development frame; keep the same camera side and spatial layout"
    return "last frame is the action-result frame; it must preserve continuity for the next clip"


def _frame_specs_text(frame_specs: Dict) -> str:
    first = frame_specs.get("first_frame_spec") or {}
    mid = frame_specs.get("mid_frame_spec") or {}
    last = frame_specs.get("last_frame_spec") or {}
    return (
        "关键帧构图规格："
        f"首帧必须执行 first frame composition alignment，画面={first.get('composition', '')}，"
        f"机位={first.get('camera_angle_lock', '')}，主体尺度={first.get('subject_scale_lock', '')}，"
        f"姿态={first.get('pose_lock', '')}，调度={first.get('blocking_lock', '')}，动作相位={first.get('action_phase_lock', '')}，"
        f"屏幕方向={first.get('screen_direction_lock', '')}；"
        f"中段保持同一空间锚点和光源方向，画面={mid.get('composition', '')}；"
        f"尾帧用于下一段续接，画面={last.get('composition', '')}。"
    )


def _merge_reference_binding(shots: List[Dict]) -> Dict:
    result = {"face_locks": {}, "costume_locks": {}, "prop_locks": {}, "scene_locks": [], "style_lock": "global:style"}
    forbidden = []
    for shot in shots:
        binding = shot.get("reference_binding") or {}
        result["face_locks"].update(binding.get("face_locks") or {})
        result["costume_locks"].update(binding.get("costume_locks") or {})
        result["prop_locks"].update(binding.get("prop_locks") or {})
        if binding.get("scene_lock"):
            result["scene_locks"].append(binding["scene_lock"])
        forbidden.extend(binding.get("forbidden_bleed") or [])
    result["scene_locks"] = _dedupe(result["scene_locks"])
    result["scene_lock"] = result["scene_locks"][0] if result["scene_locks"] else ""
    result["forbidden_bleed"] = _dedupe(forbidden)
    return result


def _merge_visual_lock(shots: List[Dict], bible: Dict) -> Dict:
    characters = {}
    scenes = {}
    for shot in shots:
        lock = shot.get("visual_lock") or {}
        characters.update(lock.get("characters") or {})
        scene = lock.get("scene") or {}
        if scene.get("lock_id"):
            scenes[scene["lock_id"]] = scene
    return {"characters": characters, "scenes": scenes, "style": bible.get("global_visual_lock", {})}


def _merge_negative_prompt(shots: List[Dict]) -> str:
    parts = []
    for shot in shots:
        parts.extend(str(shot.get("negative_prompt", "")).split("，"))
    return "，".join(_dedupe([part.strip() for part in parts if part.strip()]))


def _video_reference_images(task: Dict, scene_ids: List[str], characters: List[str]) -> List[Dict]:
    explicit = _filter_refs(
        (task.get("video_reference_images") or task.get("scene_reference_images") or task.get("normal_scene_refs") or []),
        scene_ids,
        characters,
    )
    if explicit:
        return explicit

    refs = []
    for scene in (task.get("ip_asset_pack") or {}).get("scenes") or []:
        scene_id = scene.get("scene_id") or scene.get("name")
        if scene_ids and scene_id not in scene_ids:
            continue
        refs.append(
            {
                "role": "video_scene_reference",
                "scene_id": scene_id,
                "filename": scene.get("video_reference_filename") or f"{scene_id}_video_scene_reference.jpg",
                "asset_kind": "video_scene_reference",
                "use": "direct video reference for layout, light direction, and environment continuity",
            }
        )
    return refs


def _space_anchor_refs(task: Dict, scene_ids: List[str], bible: Dict) -> List[Dict]:
    explicit = _filter_refs(task.get("space_anchor_refs") or task.get("panorama_refs") or [], scene_ids, [])
    refs = list(explicit)
    for scene_id in scene_ids:
        scene_lock = (bible.get("scene_locks") or {}).get(scene_id) or {}
        if scene_lock.get("panorama_rule"):
            refs.append(
                {
                    "role": "space_anchor",
                    "scene_id": scene_id,
                    "lock": scene_lock.get("reference_binding", {}).get("scene", f"{scene_id}:scene"),
                    "asset_kind": "720_seamless_panorama_scene",
                    "use": "spatial overview and human layout anchor; not default direct model input",
                }
            )
    return refs


def _previous_clip_end_frame(task: Dict, index: int, clip_id: str) -> Optional[Dict]:
    frames = task.get("previous_clip_end_frames") or {}
    previous_id = f"clip_{index - 1:03d}"
    if isinstance(frames, list):
        return frames[index - 2] if index >= 2 and index - 2 < len(frames) else None
    if isinstance(frames, dict):
        return frames.get(clip_id) or frames.get(str(index)) or frames.get(index) or frames.get(previous_id)
    return None


def _filter_refs(refs: List, scene_ids: List[str], characters: List[str]) -> List[Dict]:
    result = []
    for item in refs:
        ref = {"url": item, "role": "general"} if isinstance(item, str) else dict(item)
        scene_id = ref.get("scene_id")
        character_id = ref.get("character_id") or ref.get("character")
        if scene_id and scene_ids and scene_id not in scene_ids:
            continue
        if character_id and characters and character_id not in characters:
            continue
        result.append(ref)
    return result


def _ref_label(ref: Dict) -> str:
    return str(ref.get("scene_id") or ref.get("character_id") or ref.get("role") or ref.get("filename") or ref.get("url") or ref)


def _clip_quality_checks() -> List[str]:
    return [
        "clip 内所有 shot 是否被合并为连续动作，而不是互相断裂的小镜头",
        "如果存在 previous_clip_end_frame，当前 clip 第一帧是否继承上一 clip 尾帧",
        "正常场景参考图是否进入 video_reference_images",
        "720 全景图是否保留在 space_anchor_refs，且未被默认当作直接生成画面",
        "视频声音是否只保留环境声和拟音，且没有背景音乐或歌曲",
        "画面是否没有字幕、伪文字、水印、片头片尾和标题卡",
        "武戏段落是否看清起势、距离、一次攻防、重心变化和收势落点",
        "角色脸、发型、服饰、道具、空间布局和光源方向是否跨 clip 一致",
    ]


def _positive_float(value, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed > 0 else default


def _dedupe(items: List) -> List:
    seen = set()
    result = []
    for item in items:
        key = str(item)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def _clip_storyboard_card(shots: List[Dict]) -> Dict:
    first_card = shots[0].get("storyboard_card") or {}
    characters = []
    for shot in shots:
        characters.extend(shot.get("characters") or [])
    return {
        "characters_present": _dedupe(characters),
        "axis": first_card.get("axis", {}),
        "screen_direction": first_card.get("screen_direction", {}),
        "eyeline": first_card.get("eyeline", {}),
    }


def _optional_sentence(label: str, value: str) -> str:
    return f"{label}：{value}。" if value else ""
