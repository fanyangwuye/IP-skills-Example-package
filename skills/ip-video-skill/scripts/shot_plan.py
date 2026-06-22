from typing import Dict, List

try:
    from .continuity import choose_scene_id, find_character_ids_in_text
    from .martial_arts import is_martial_arts_scene
    from .prompt_quality import (
        build_negative_prompt,
        build_prompt_profile,
        build_retry_advice,
        compose_i2v_prompt,
        compose_seedance_prompt,
        compose_t2v_prompt,
    )
except ImportError:
    from continuity import choose_scene_id, find_character_ids_in_text
    from martial_arts import is_martial_arts_scene
    from prompt_quality import (
        build_negative_prompt,
        build_prompt_profile,
        build_retry_advice,
        compose_i2v_prompt,
        compose_seedance_prompt,
        compose_t2v_prompt,
    )


def build_shot_plan(task: Dict, continuity_bible: Dict) -> List[Dict]:
    segments = _source_segments(task)
    if not segments:
        segments = [{"index": 1, "start_sec": 0, "end_sec": 6, "visual": task.get("source_text", "核心场景")}]

    shots: List[Dict] = []
    previous_end_state = task.get("initial_state", "开场前角色和场景处于连续性圣经定义的初始状态")
    for idx, segment in enumerate(segments, start=1):
        shot = _build_shot(idx, segment, continuity_bible, previous_end_state)
        shots.append(shot)
        previous_end_state = shot["continuity_state"]["current_end_state"]
    return shots


def build_i2v_prompts(shots: List[Dict]) -> List[Dict]:
    return [
        {
            "shot_id": shot["shot_id"],
            "prompt": shot["i2v_prompt"],
            "seedance_prompt": shot["seedance_prompt"],
            "negative_prompt": shot["negative_prompt"],
            "reference_binding": shot["reference_binding"],
            "retry_advice": shot["retry_advice"],
        }
        for shot in shots
    ]


def build_t2v_prompts(shots: List[Dict]) -> List[Dict]:
    return [
        {
            "shot_id": shot["shot_id"],
            "prompt": shot["t2v_prompt"],
            "seedance_prompt": shot["seedance_prompt"],
            "negative_prompt": shot["negative_prompt"],
            "visual_lock": shot["visual_lock"],
            "retry_advice": shot["retry_advice"],
        }
        for shot in shots
    ]


def _build_shot(index: int, segment: Dict, bible: Dict, previous_end_state: str) -> Dict:
    visual = segment.get("visual") or segment.get("action") or segment.get("scene") or ""
    spoken = segment.get("voiceover") or segment.get("subtitle") or ""
    text = " ".join([visual, spoken, str(segment.get("asset_goal") or "")])
    character_ids = find_character_ids_in_text(text, bible.get("character_locks") or {})
    scene_id = choose_scene_id(text, bible.get("scene_locks") or {})
    duration = _duration(segment)
    timing = {
        "start_sec": float(segment.get("start_sec", max(index - 1, 0) * duration)),
        "end_sec": float(segment.get("end_sec", max(index, 1) * duration)),
        "duration_sec": duration,
    }

    axis = _axis(character_ids)
    screen_direction = _screen_direction(character_ids)
    eyeline = _eyeline(character_ids)
    end_state = _end_state(index, visual, character_ids, scene_id)
    continuity_state = {
        "previous_end_state": previous_end_state,
        "current_start_state": previous_end_state,
        "main_action_transition": _main_action(visual),
        "current_end_state": end_state,
        "next_handoff": end_state,
    }
    visual_lock = _visual_lock(character_ids, scene_id, bible)
    reference_binding = _reference_binding(character_ids, scene_id, bible)
    storyboard_card = {
        "story_function": segment.get("beat_function") or segment.get("purpose") or segment.get("asset_goal", {}).get("purpose", "推进剧情"),
        "characters_present": character_ids,
        "axis": axis,
        "screen_direction": screen_direction,
        "framing": _framing(index, len(character_ids)),
        "camera_motion": _camera_motion(index, visual),
        "eyeline": eyeline,
        "performance_action": f"{previous_end_state} -> {_main_action(visual)} -> {end_state}",
        "sound_subtitle": {
            "voiceover": segment.get("voiceover", ""),
            "dialogue": segment.get("dialogue", []),
            "subtitle": segment.get("subtitle", segment.get("voiceover", "")),
            "music_cue": segment.get("music_cue", ""),
        },
        "timing": timing,
    }
    action_scene = _is_action_scene(visual)
    storyboard_card["action_scene_type"] = "martial_arts" if is_martial_arts_scene(visual) else ("action" if action_scene else "")
    prompt_profile = build_prompt_profile(index, visual, storyboard_card, continuity_state, visual_lock)

    return {
        "shot_id": segment.get("shot_id") or f"shot_{index:03d}",
        "source_ref": segment.get("index", segment.get("scene_no", index)),
        "timing": timing,
        "visual": visual,
        "characters": character_ids,
        "scene_id": scene_id,
        "visual_lock": visual_lock,
        "reference_binding": reference_binding,
        "continuity_state": continuity_state,
        "axis": axis,
        "screen_direction": screen_direction,
        "eyeline": eyeline,
        "blocking_distance": _blocking_distance(character_ids),
        "storyboard_card": storyboard_card,
        "prompt_profile": prompt_profile,
        "i2v_prompt": compose_i2v_prompt(visual, prompt_profile, reference_binding),
        "t2v_prompt": compose_t2v_prompt(visual, prompt_profile, visual_lock),
        "seedance_prompt": compose_seedance_prompt(visual, prompt_profile, reference_binding),
        "negative_prompt": build_negative_prompt(len(character_ids) >= 2, action_scene=action_scene),
        "retry_advice": build_retry_advice(prompt_profile, len(character_ids) >= 2),
        "quality_checks": _quality_checks(len(character_ids) >= 2),
    }


def _source_segments(task: Dict) -> List[Dict]:
    blueprint = task.get("blueprint") or {}
    if blueprint.get("segments"):
        return blueprint["segments"]
    polished = task.get("polished_script") or {}
    if polished.get("scenes"):
        return polished["scenes"]
    draft = task.get("script_draft") or {}
    if draft.get("scenes"):
        return draft["scenes"]
    return task.get("scene_cards") or []


def _duration(segment: Dict) -> float:
    if segment.get("duration_sec"):
        return float(segment["duration_sec"])
    if segment.get("start_sec") is not None and segment.get("end_sec") is not None:
        return max(float(segment["end_sec"]) - float(segment["start_sec"]), 1.0)
    return 6.0


def _axis(character_ids: List[str]) -> Dict:
    if len(character_ids) >= 2:
        return {
            "type": "character_axis",
            "line": f"{character_ids[0]} <-> {character_ids[1]}",
            "camera_side": "固定在主轴同一侧，除非用中性镜头或可见运镜换侧",
            "cross_axis_rule": "禁止无过渡越轴",
        }
    return {
        "type": "movement_axis",
        "line": "主体运动方向",
        "camera_side": "保持运动方向一致",
        "cross_axis_rule": "如需折返，先用正面/背面中性镜头过渡",
    }


def _screen_direction(character_ids: List[str]) -> Dict:
    if len(character_ids) >= 2:
        return {
            character_ids[0]: "屏幕左，面朝右",
            character_ids[1]: "屏幕右，面朝左",
            "others": "围绕主轴站位，不突然换边",
        }
    if character_ids:
        return {character_ids[0]: "保持上一镜屏幕方向，运动方向不跳变"}
    return {"environment": "空镜保持空间方向清楚"}


def _eyeline(character_ids: List[str]) -> Dict:
    if len(character_ids) >= 2:
        return {
            character_ids[0]: f"朝右看 {character_ids[1]}，视线高度匹配",
            character_ids[1]: f"朝左看 {character_ids[0]}，视线互补",
        }
    if character_ids:
        return {character_ids[0]: "视线落点与动作目标一致"}
    return {"environment": "无角色视线，使用地标引导视线"}


def _visual_lock(character_ids: List[str], scene_id: str, bible: Dict) -> Dict:
    character_locks = bible.get("character_locks") or {}
    scene_locks = bible.get("scene_locks") or {}
    return {
        "characters": {char_id: character_locks.get(char_id, {}) for char_id in character_ids},
        "scene": scene_locks.get(scene_id, {}),
        "style": bible.get("global_visual_lock", {}),
    }


def _reference_binding(character_ids: List[str], scene_id: str, bible: Dict) -> Dict:
    character_locks = bible.get("character_locks") or {}
    scene_locks = bible.get("scene_locks") or {}
    return {
        "face_locks": {char_id: character_locks.get(char_id, {}).get("reference_binding", {}).get("face", "") for char_id in character_ids},
        "costume_locks": {char_id: character_locks.get(char_id, {}).get("reference_binding", {}).get("costume", "") for char_id in character_ids},
        "prop_locks": {
            char_id: character_locks.get(char_id, {}).get("reference_binding", {}).get("props", [])
            for char_id in character_ids
        },
        "scene_lock": scene_locks.get(scene_id, {}).get("reference_binding", {}).get("scene", ""),
        "style_lock": "global:style",
        "forbidden_bleed": [
            "角色参考图不复制背景",
            "服装参考图不复制模特脸",
            "场景参考图不复制路人",
            "风格参考图不复制具体内容",
        ],
    }


def _main_action(visual: str) -> str:
    text = visual.strip()
    return text if len(text) <= 90 else text[:89].rstrip() + "..."


def _end_state(index: int, visual: str, character_ids: List[str], scene_id: str) -> str:
    subject = "、".join(character_ids) if character_ids else "镜头主体"
    scene = scene_id or "当前场景"
    action = _main_action(visual) or "完成本镜主要动作"
    return f"镜头{index}结束：{subject}在{scene}保持可追踪站位，动作结果为：{action}"


def _framing(index: int, n_characters: int) -> str:
    if index == 1:
        return "WS/LS 建立空间和人物站位"
    if n_characters >= 2:
        return "MS 双人关系镜头，必要时 OTS 近景"
    return "MS/CU 主体表演清楚"


def _camera_motion(index: int, visual: str) -> str:
    if any(word in visual for word in ["跑", "追", "冲", "打", "逃"]):
        return "handheld track，速度跟随动作但保持主体清楚"
    if index == 1:
        return "slow dolly in，先交代空间再靠近主体"
    return "static or slow push，优先保持表演和连续性"


def _blocking_distance(character_ids: List[str]) -> str:
    if len(character_ids) >= 2:
        return "两人距离、前后景和高低关系必须从上一镜继承；如改变距离，镜头内拍出移动过程"
    return "主体与关键地标距离必须可追踪"


def _is_action_scene(visual: str) -> bool:
    return is_martial_arts_scene(visual) or any(word in visual for word in ["打", "冲", "追", "逃", "撞", "压制", "反击"])


def _quality_checks(multichar: bool) -> List[str]:
    checks = [
        "角色脸、发型、年龄感和体型气质是否与 continuity_bible 一致",
        "服饰款式、材质、颜色和状态是否跨镜一致",
        "道具所在手、材质和状态是否连续",
        "场景布局、地标、天气和光源方向是否连续",
        "本镜起始态是否继承上一镜结束态",
    ]
    if multichar:
        checks.extend(["轴线是否固定", "屏幕方向是否固定", "双方视线是否互补", "距离变化是否在镜头内交代"])
    return checks
