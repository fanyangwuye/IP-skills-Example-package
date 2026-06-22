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
        "martial_arts_layer": martial_arts_layer,
        "previous_clip_end_frame": _previous_clip_end_frame(task, index, clip_id),
        "continuity_state": continuity_state,
        "clip_prompt": _clip_prompt(clip_id, timing, shots, continuity_state, video_refs, space_refs, martial_arts_layer),
        "i2v_prompt": _clip_prompt(clip_id, timing, shots, continuity_state, video_refs, space_refs, martial_arts_layer),
        "seedance_prompt": _clip_prompt(clip_id, timing, shots, continuity_state, video_refs, space_refs, martial_arts_layer),
        "t2v_prompt": _clip_prompt(clip_id, timing, shots, continuity_state, video_refs, space_refs, martial_arts_layer),
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
        f"{_optional_sentence('武戏调度', martial_arts_text(martial_arts_layer))}"
        "保持同一角色脸、发型、服饰、道具、场景布局、光影色调和屏幕方向；片段内部动作连续，不要跳切、不要重置空间。"
        "声音只保留现场环境声与拟音，例如风声、雨声、脚步、衣料摩擦、呼吸、门响和道具轻响；禁止背景音乐、歌曲、音乐铺底。"
        "画面禁止字幕、伪文字、水印、片头片尾、标题卡和解释性文字。"
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
