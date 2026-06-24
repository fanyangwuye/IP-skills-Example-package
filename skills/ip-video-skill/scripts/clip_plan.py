from typing import Dict, List, Optional

try:
    from .martial_arts import build_martial_arts_layer, is_martial_arts_scene, martial_arts_text
    from .spatial_templates import high_risk_spatial_template_text
except ImportError:
    from martial_arts import build_martial_arts_layer, is_martial_arts_scene, martial_arts_text
    from spatial_templates import high_risk_spatial_template_text


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
            "storyboard_execution_map": clip.get("storyboard_execution_map", []),
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
    storyboard_execution_map = _storyboard_execution_map(shots)
    martial_arts_layer = build_martial_arts_layer(
        "；".join(shot.get("visual", "") for shot in shots),
        _clip_storyboard_card(shots),
        continuity_state,
    ) if any(is_martial_arts_scene(shot.get("visual", ""), shot.get("storyboard_card", {}).get("action_scene_type", "")) for shot in shots) else {}

    prompt_bundle = _clip_prompt_bundle(
        clip_id,
        timing,
        shots,
        continuity_state,
        video_refs,
        space_refs,
        martial_arts_layer,
        frame_specs,
        storyboard_execution_map,
    )

    return {
        "clip_id": clip_id,
        "order": index,
        "shot_ids": [shot.get("shot_id", "") for shot in shots],
        "storyboard_execution_map": storyboard_execution_map,
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
        "clip_prompt": prompt_bundle["clip_prompt"],
        "i2v_prompt": prompt_bundle["i2v_prompt"],
        "seedance_prompt": prompt_bundle["seedance_prompt"],
        "t2v_prompt": prompt_bundle["t2v_prompt"],
        "prompt_strategy": prompt_bundle["prompt_strategy"],
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



def _clip_prompt_bundle(
    clip_id: str,
    timing: Dict,
    shots: List[Dict],
    continuity_state: Dict,
    video_refs: List[Dict],
    space_refs: List[Dict],
    martial_arts_layer: Dict,
    frame_specs: Dict,
    storyboard_execution_map: List[Dict],
) -> Dict:
    full_packet = _clip_prompt(
        clip_id,
        timing,
        shots,
        continuity_state,
        video_refs,
        space_refs,
        martial_arts_layer,
        frame_specs,
        storyboard_execution_map,
    )
    return {
        "clip_prompt": full_packet,
        "i2v_prompt": _clip_provider_prompt(
            "i2v",
            clip_id,
            timing,
            shots,
            continuity_state,
            video_refs,
            space_refs,
            martial_arts_layer,
            storyboard_execution_map,
        ),
        "seedance_prompt": _clip_provider_prompt(
            "seedance",
            clip_id,
            timing,
            shots,
            continuity_state,
            video_refs,
            space_refs,
            martial_arts_layer,
            storyboard_execution_map,
        ),
        "t2v_prompt": _clip_provider_prompt(
            "t2v",
            clip_id,
            timing,
            shots,
            continuity_state,
            video_refs,
            space_refs,
            martial_arts_layer,
            storyboard_execution_map,
        ),
        "prompt_strategy": {
            "architecture": "Prompt Packet V1",
            "control_prompt": "clip_prompt keeps the full audit packet",
            "provider_prompts": "i2v/seedance/t2v are compact surface packets with all required sections",
            "length_policy": "provider prompts keep locked facts, references, spatial blocking, timeline, and hard constraints first",
        },
    }


def _clip_provider_prompt(
    kind: str,
    clip_id: str,
    timing: Dict,
    shots: List[Dict],
    continuity_state: Dict,
    video_refs: List[Dict],
    space_refs: List[Dict],
    martial_arts_layer: Dict,
    storyboard_execution_map: List[Dict],
) -> str:
    characters = _dedupe([char for shot in shots for char in (shot.get("characters") or [])])
    scene_ids = _dedupe([shot.get("scene_id") for shot in shots if shot.get("scene_id")])
    shot_ids = [shot.get("shot_id", "") for shot in shots if shot.get("shot_id")]
    visual = _clip_text("; ".join(shot.get("visual", "") for shot in shots if shot.get("visual")), 260)
    action = _clip_text(continuity_state.get("main_action_transition", ""), 220)
    spatial = _compact_spatial_text(shots)
    timeline = _compact_timeline_text(shots)
    refs = _compact_reference_text(video_refs, space_refs)
    martial = _clip_text(martial_arts_text(martial_arts_layer), 180)
    storyboard = _compact_storyboard_text(storyboard_execution_map)

    if kind == "i2v":
        mode_line = "Image-to-video. Use reference images as the identity, costume, scene, storyboard-composition and motion anchors."
        surface = _english_surface_line(visual, action)
        execution = "Execute the storyboard order exactly; keep one clear main action per shot; no subtitles, no fake text, no watermark, no title card, no songs, 无音乐铺底。"
    elif kind == "t2v":
        mode_line = "Text-to-video preview only. Do not treat this as final IP identity validation without character and scene references."
        surface = _english_surface_line(visual, action)
        execution = "Preview camera, blocking and action rhythm; do not invent new characters, props, spaces, dialogue text, subtitles or logos."
    else:
        mode_line = "Seedance clip prompt. 使用参考图锁定角色身份、服装、场景与故事板构图；动作短、清楚、可剪辑。"
        surface = _chinese_surface_line(visual, action)
        execution = "严格按故事板顺序执行；每个分镜只保留一个主动作和一个情绪落点；禁止字幕、伪文字、水印、片头片尾、歌曲和背景音乐。"

    parts = [
        f"Prompt Packet V1: {clip_id}; duration={timing.get('duration_sec')}s; generation_unit=clip; prompt_kind={kind}; shot_ids={shot_ids}.",
        f"Global Context: {mode_line} Realistic cinematic short-drama texture; stable face, hair, costume, props, layout, light direction and screen direction.",
        f"Internal Story Facts: characters={characters or ['empty/cutaway']}; scenes={scene_ids or ['unspecified']}; start={_clip_text(continuity_state.get('current_start_state', ''), 120)}; action={action}; end={_clip_text(continuity_state.get('current_end_state', ''), 120)}.",
        f"Reference Bindings: {refs}; character refs lock identity and costume; scene refs lock layout and light; storyboard refs lock composition, blocking, action phase, screen direction and edit order.",
        f"Spatial Blocking: {spatial}",
        f"15s Timeline: {timeline}",
        "Continuation Contract: Do not copy the previous clip composition unless hard_first_frame is explicitly selected; use reframed medium, close, wide, reverse, insert or cutaway shots only when continuity state, light, costume, prop hand and screen direction remain traceable.",
        f"Platform-Safe Surface Wording: {surface} Surface wording must stay visually equivalent to the locked references and storyboard; do not replace locked characters with strangers, masks, machines, celebrities, animals or unrelated creatures.",
        f"Execution Constraints: {storyboard} {martial} {execution}",
    ]
    return "\n".join(part.strip() for part in parts if part.strip())


def _compact_reference_text(video_refs: List[Dict], space_refs: List[Dict]) -> str:
    video = ", ".join(_ref_label(ref) for ref in video_refs[:4]) or "locked character/normal scene references"
    space = ", ".join(_ref_label(ref) for ref in space_refs[:3]) or "panorama anchors for layout only"
    return f"video_refs={video}; space_anchor_refs={space}"


def _compact_spatial_text(shots: List[Dict]) -> str:
    rows = []
    for order, shot in enumerate(shots[:4], start=1):
        card = shot.get("storyboard_card") or {}
        axis = card.get("axis") or shot.get("axis", {})
        screen = card.get("screen_direction") or shot.get("screen_direction", {})
        eyeline = card.get("eyeline") or shot.get("eyeline", {})
        rows.append(
            f"shot{order}/{shot.get('shot_id', '')}: axis={_clip_text(axis, 90)}; screen={_clip_text(screen, 90)}; eyeline={_clip_text(eyeline, 70)}"
        )
    suffix = " Keep doors, windows, entrances, exits, foreground/background and danger side from teleporting."
    high_risk = _clip_text(high_risk_spatial_template_text(shots), 220)
    return _clip_text(" | ".join(rows) + suffix + (" " + high_risk if high_risk else ""), 520)


def _compact_timeline_text(shots: List[Dict]) -> str:
    rows = []
    for order, shot in enumerate(shots[:5], start=1):
        timing = shot.get("timing") or {}
        card = shot.get("storyboard_card") or {}
        state = shot.get("continuity_state") or {}
        rows.append(
            f"[{timing.get('start_sec')}-{timing.get('end_sec')}s] shot{order}={shot.get('shot_id', '')}: "
            f"{_clip_text(shot.get('visual', ''), 120)}; camera={_clip_text(card.get('camera_motion', '') or 'follow storyboard camera', 60)}; "
            f"start={_clip_text(state.get('current_start_state', ''), 70)}; end={_clip_text(state.get('current_end_state', ''), 70)}"
        )
    return _clip_text(" ".join(rows), 760)


def _compact_storyboard_text(storyboard_execution_map: List[Dict]) -> str:
    if not storyboard_execution_map:
        return "Storyboard map required before live generation."
    rows = []
    for item in storyboard_execution_map[:5]:
        rows.append(f"video shot {item.get('video_shot_order')} = storyboard {item.get('storyboard_shot_id')}")
    return "Storyboard execution map: " + "; ".join(rows) + ". Do not delete, merge, reorder or rewrite storyboard shots."


def _english_surface_line(visual: str, action: str) -> str:
    return _clip_text(
        "Create a visually equivalent cinematic clip from the locked references: "
        + visual
        + ". Main action: "
        + action
        + ". Keep named IP facts internal; use neutral visible descriptions while preserving the exact characters, props, space and action.",
        420,
    )


def _chinese_surface_line(visual: str, action: str) -> str:
    return _clip_text(
        "按参考图和故事板生成视觉等价片段："
        + visual
        + "。主动作："
        + action
        + "。外部措辞可中性化，但不得增删角色、道具、空间和动作。",
        420,
    )


def _clip_text(value, limit: int) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)].rstrip(" ，。；,.;") + "..."
def _clip_prompt(
    clip_id: str,
    timing: Dict,
    shots: List[Dict],
    continuity_state: Dict,
    video_refs: List[Dict],
    space_refs: List[Dict],
    martial_arts_layer: Dict,
    frame_specs: Dict,
    storyboard_execution_map: List[Dict],
) -> str:
    video_ref_note = "；".join(_ref_label(ref) for ref in video_refs) or "使用已锁定角色图和正常场景参考图"
    space_ref_note = "；".join(_ref_label(ref) for ref in space_refs) or "全景图仅作为空间锚点"
    characters = _dedupe([char for shot in shots for char in (shot.get("characters") or [])])
    scene_ids = _dedupe([shot.get("scene_id") for shot in shots if shot.get("scene_id")])
    shot_ids = [shot.get("shot_id", "") for shot in shots if shot.get("shot_id")]
    return (
        f"Prompt Packet V1：{clip_id} 连续视频片段，时长约 {timing.get('duration_sec')} 秒；"
        f"generation_unit=clip；shot_ids={shot_ids}。\n\n"
        "Global Context："
        "写实短剧质感，镜头服务叙事和人物状态，不做无意义炫技；"
        "保持同一角色脸、发型、服饰、道具、场景布局、光影色调和屏幕方向；"
        f"视频生成参考={video_ref_note}；空间锚点={space_ref_note}；"
        "全景图用于校准空间布局、地标和光源方向，默认不要作为直接生成画面。\n\n"
        "Internal Story Facts："
        f"在场角色={characters or ['无角色/空镜']}；场景={scene_ids or ['未指定场景']}；"
        f"起始状态={continuity_state.get('current_start_state')}；"
        f"动作目标={continuity_state.get('main_action_transition')}；"
        f"结束状态={continuity_state.get('current_end_state')}；"
        f"下段交接={continuity_state.get('next_handoff')}。\n\n"
        "Reference Bindings："
        "角色参考锁身份、脸型、发型、年龄感、体型气质和服装轮廓；"
        "场景参考锁空间布局、可见地标、材质状态、光源方向和整体色调；"
        "故事板参考只锁构图、景别、机位、动作相位、走位、屏幕方向和剪辑顺序。"
        "如果任务锁定 reference_policy=all_purpose_reference，则只能使用 reference_image_urls，禁止改写为 image_urls、首帧、尾帧、上一段尾帧或关键帧 I2V。\n\n"
        f"Spatial Blocking：{_spatial_blocking_text(shots)}{high_risk_spatial_template_text(shots)}\n\n"
        f"15s Timeline：{_timeline_text(shots)}\n\n"
        "Continuation Contract："
        "跨 clip 衔接不等于每段都复制上一段构图；除非明确使用 hard_first_frame，否则允许用近景、特写、全景、远景、背影、反打、空镜、道具插入或手部局部来承接。"
        "单帧截取只服务连续性参考，可继承光色、服装、动作余势、屏幕方向、角色状态和情绪残留；不能自动变成角色身份锁、默认首帧或全能参考替代品。"
        "换景别时必须继承上一段的人物状态、服饰、道具所在手、动作余势、光源方向、曝光、白平衡和色彩，不要把切镜头误生成换场景。\n\n"
        "Platform-Safe Surface Wording："
        "外部提交文本可以使用更中性的安全表达，但必须保持视觉等价；"
        "安全表达只强化参考图和故事板既有内容，不能把锁定角色改成普通人、面罩人、机械体、陌生演员或无关生物，不能新增、删除或替换道具与剧情动作。\n\n"
        "Execution Constraints："
        f"{_storyboard_execution_text(storyboard_execution_map)}"
        f"{_frame_specs_text(frame_specs)}"
        f"{_optional_sentence('武戏调度', martial_arts_text(martial_arts_layer))}"
        "片段内部动作连续，不要跳切、不要重置空间；"
        "声音只保留现场环境声与拟音，例如风声、雨声、脚步、衣料摩擦、呼吸、门响和道具轻响；禁止背景音乐、歌曲、音乐铺底。"
        "画面禁止字幕、伪文字、水印、片头片尾、标题卡和解释性文字。"
    )


def _spatial_blocking_text(shots: List[Dict]) -> str:
    rows = []
    for order, shot in enumerate(shots, start=1):
        card = shot.get("storyboard_card") or {}
        axis = card.get("axis") or shot.get("axis", {})
        screen = card.get("screen_direction") or shot.get("screen_direction", {})
        eyeline = card.get("eyeline") or shot.get("eyeline", {})
        characters = shot.get("characters") or []
        rows.append(
            f"镜头{order}/{shot.get('shot_id', '')}：在场角色={characters or ['无角色/空镜']}；"
            f"轴线={axis or '单角色/环境轴线'}；屏幕方向={screen or '保持上一镜方向'}；"
            f"视线={eyeline or '按画面目标保持清楚'}；"
            "站位必须能从上一镜追踪到本镜，门、窗、入口、出口、前景/后景和危险侧不能跳位"
        )
    return "；".join(rows) + "。多角色镜头必须自动执行轴线、屏幕方向、视线匹配和站位连续性；如需换轴，先用中性轴上镜头、运动过渡、空镜或桥接镜头交代。"


def _timeline_text(shots: List[Dict]) -> str:
    rows = []
    for order, shot in enumerate(shots, start=1):
        timing = shot.get("timing") or {}
        card = shot.get("storyboard_card") or {}
        state = shot.get("continuity_state") or {}
        rows.append(
            f"[{timing.get('start_sec')}-{timing.get('end_sec')}s] 镜头{order}={shot.get('shot_id', '')}："
            f"画面={shot.get('visual', '')}；"
            f"镜头控制={card.get('camera_motion', '') or '按故事板机位执行'}；"
            f"起始={state.get('current_start_state', '')}；"
            f"动作转化={state.get('main_action_transition', '') or shot.get('visual', '')}；"
            f"结束={state.get('current_end_state', '')}"
        )
    return " ".join(rows) + "。每个时间段必须是清楚的叙事动作，不要为了填满时长让角色原地重复奔跑、重复转身或做无因果的装饰动作。"

def _storyboard_execution_map(shots: List[Dict]) -> List[Dict]:
    rows = []
    for order, shot in enumerate(shots, start=1):
        card = shot.get("storyboard_card") or {}
        rows.append(
            {
                "video_shot_order": order,
                "storyboard_shot_id": shot.get("shot_id", ""),
                "start_sec": shot.get("timing", {}).get("start_sec"),
                "end_sec": shot.get("timing", {}).get("end_sec"),
                "visual": shot.get("visual", ""),
                "framing": card.get("framing", ""),
                "camera_motion": card.get("camera_motion", ""),
                "execution_rule": "must_execute_in_order; do_not_delete; do_not_merge_away; do_not_reorder; revise_storyboard_first_if_needed",
            }
        )
    return rows


def _storyboard_execution_text(storyboard_execution_map: List[Dict]) -> str:
    if not storyboard_execution_map:
        return ""
    rows = []
    for item in storyboard_execution_map:
        rows.append(
            f"视频镜头{item.get('video_shot_order')} = 故事板分镜 {item.get('storyboard_shot_id')}，"
            f"时间 {item.get('start_sec')}-{item.get('end_sec')} 秒，"
            f"景别={item.get('framing')}，运镜={item.get('camera_motion')}，画面={item.get('visual')}"
        )
    return (
        "故事板执行映射（强制）："
        + "；".join(rows)
        + "。必须按故事板顺序执行每个分镜；不得为了凑 15 秒长镜头而删除、合并掉、改顺序或改动作。"
        "如果一个 15 秒 clip 无法准确执行全部分镜，必须拆成更短生成单元，而不是改故事板。"
        "提示词只能强化参考图和故事板已有内容细节，不能新增、修改或减少画面内容。"
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
        "clip_prompt 是否使用 Prompt Packet V1 固定结构：Global Context / Internal Story Facts / Reference Bindings / Spatial Blocking / 15s Timeline / Continuation Contract / Platform-Safe Surface Wording / Execution Constraints",
        "clip 内所有 shot 是否被合并为连续动作，而不是互相断裂的小镜头",
        "如果存在 previous_clip_end_frame，当前 clip 第一帧是否继承上一 clip 尾帧",
        "正常场景参考图是否进入 video_reference_images",
        "720 全景图是否保留在 space_anchor_refs，且未被默认当作直接生成画面",
        "视频声音是否只保留环境声和拟音，且没有背景音乐或歌曲",
        "画面是否没有字幕、伪文字、水印、片头片尾和标题卡",
        "storyboard_execution_map 是否覆盖 clip 内每个 shot_id，且视频执行顺序未删除、未合并掉、未改顺序",
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
