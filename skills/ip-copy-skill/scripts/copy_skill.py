import argparse
import json
import os
import re
from datetime import date
from typing import Dict, List, Optional

try:
    from .blueprint_validate import validate_blueprint
    from .license_gate import check_license, gate
except ImportError:
    from blueprint_validate import validate_blueprint
    from license_gate import check_license, gate


def run_task(task: Dict) -> Dict:
    mode = task.get("mode", "build_blueprint")
    output_dir = task.get("output_dir") or os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    if mode == "check_license":
        return _run_check_license(task)
    if mode == "update_adaptation_state":
        return _run_update_adaptation_state(task, output_dir)
    if mode == "build_adaptation_scene_cards":
        return _run_build_adaptation_scene_cards(task, output_dir)
    if mode == "build_script_draft":
        return _run_build_script_draft(task, output_dir)
    if mode == "build_ip_asset_pack":
        return _run_build_ip_asset_pack(task, output_dir)
    if mode == "build_character_handoff":
        return _run_build_character_handoff(task, output_dir)
    if mode == "build_blueprint":
        return _run_build_blueprint(task, output_dir)
    raise ValueError("mode must be one of: check_license, build_blueprint, build_character_handoff, build_ip_asset_pack, update_adaptation_state, build_adaptation_scene_cards, build_script_draft")


def _run_check_license(task: Dict) -> Dict:
    license_record = _load_license_record(task.get("ip_id"), task.get("license_path"))
    requested_target = task["target"]
    commercial_use = bool(task.get("commercial_use", False))
    today = _parse_today(task.get("today"))
    ok, reasons = check_license(
        license_record,
        requested_target=requested_target,
        commercial_use=commercial_use,
        today=today,
    )
    return {
        "status": "success" if ok else "blocked",
        "skill": "ip-copy-skill",
        "mode": "check_license",
        "task_id": task.get("task_id", "check_license"),
        "handoff": {
            "license_ok": ok,
            "license_record": license_record,
            "reasons": reasons,
        },
        "logs": ["license passed" if ok else "license blocked"],
    }


def _run_update_adaptation_state(task: Dict, output_dir: str) -> Dict:
    state = _update_adaptation_state(task)
    out_path = os.path.join(output_dir, task.get("state_filename", "adaptation_state.json"))
    _write_json(out_path, state)
    return {
        "status": "success",
        "skill": "ip-copy-skill",
        "mode": "update_adaptation_state",
        "task_id": task.get("task_id", "update_adaptation_state"),
        "artifacts": [
            {
                "type": "json",
                "path": out_path,
                "meta": {"kind": "adaptation_state"},
            }
        ],
        "handoff": {
            "adaptation_state": state,
        },
        "logs": ["adaptation state updated"],
    }


def _run_build_adaptation_scene_cards(task: Dict, output_dir: str) -> Dict:
    state = task.get("adaptation_state") or _update_adaptation_state(task)
    scene_cards = _build_adaptation_scene_cards(state, task)
    payload = {
        "title": state.get("title", task.get("title", "")),
        "source_text": state.get("source_text", task.get("source_text", "")),
        "creative_direction": state.get("creative_direction", {}),
        "scene_cards": scene_cards,
    }
    out_path = os.path.join(output_dir, task.get("scene_cards_filename", "adaptation_scene_cards.json"))
    _write_json(out_path, payload)
    return {
        "status": "success",
        "skill": "ip-copy-skill",
        "mode": "build_adaptation_scene_cards",
        "task_id": task.get("task_id", "build_adaptation_scene_cards"),
        "artifacts": [
            {
                "type": "json",
                "path": out_path,
                "meta": {"kind": "adaptation_scene_cards"},
            }
        ],
        "handoff": payload,
        "logs": [f"built {len(scene_cards)} adaptation scene cards"],
    }


def _run_build_script_draft(task: Dict, output_dir: str) -> Dict:
    scene_cards = task.get("scene_cards") or []
    state = task.get("adaptation_state") or {}
    if not scene_cards:
        if not state:
            state = _update_adaptation_state(task)
        scene_cards = _build_adaptation_scene_cards(state, task)
    script = _build_script_draft(scene_cards, state, task)
    out_path = os.path.join(output_dir, task.get("script_filename", "script_draft.json"))
    _write_json(out_path, script)
    return {
        "status": "success",
        "skill": "ip-copy-skill",
        "mode": "build_script_draft",
        "task_id": task.get("task_id", "build_script_draft"),
        "artifacts": [
            {
                "type": "json",
                "path": out_path,
                "meta": {"kind": "script_draft"},
            }
        ],
        "handoff": {
            "script_draft": script,
        },
        "logs": [f"built script draft with {len(script['scenes'])} scenes"],
    }


def _run_build_character_handoff(task: Dict, output_dir: str) -> Dict:
    handoff = _build_image_handoff(task)
    out_path = os.path.join(output_dir, task.get("handoff_filename", "character_handoff.json"))
    _write_json(out_path, handoff)
    return {
        "status": "success",
        "skill": "ip-copy-skill",
        "mode": "build_character_handoff",
        "task_id": task.get("task_id", "build_character_handoff"),
        "artifacts": [
            {
                "type": "json",
                "path": out_path,
                "meta": {"kind": "image_handoff"},
            }
        ],
        "handoff": handoff,
        "logs": ["character handoff written"],
    }


def _run_build_ip_asset_pack(task: Dict, output_dir: str) -> Dict:
    pack = _build_ip_asset_pack(task)
    out_path = os.path.join(output_dir, task.get("asset_pack_filename", "ip_asset_pack.json"))
    _write_json(out_path, pack)
    return {
        "status": "success",
        "skill": "ip-copy-skill",
        "mode": "build_ip_asset_pack",
        "task_id": task.get("task_id", "build_ip_asset_pack"),
        "artifacts": [
            {
                "type": "json",
                "path": out_path,
                "meta": {"kind": "ip_asset_pack"},
            }
        ],
        "handoff": {
            "ip_asset_pack": pack,
        },
        "logs": [
            f"ip asset pack built with {len(pack['characters'])} characters and {len(pack['scenes'])} scenes"
        ],
    }


def _run_build_blueprint(task: Dict, output_dir: str) -> Dict:
    license_record = _load_license_record(task.get("ip_id"), task.get("license_path"))
    target = task["target"]
    commercial_use = bool(task.get("commercial_use", False))
    gate(license_record, target, commercial_use, today=_parse_today(task.get("today")))

    scene_cards = task.get("scene_cards") or []
    if not scene_cards:
        raise ValueError("build_blueprint requires a non-empty scene_cards list")

    total_duration_sec = float(task["total_duration_sec"])
    segments = _build_segments(scene_cards, total_duration_sec)
    blueprint = {
        "blueprint_id": task.get("blueprint_id", f"{task['ip_id']}_blueprint"),
        "ip_id": task["ip_id"],
        "target": target,
        "title": task.get("title", ""),
        "source_text": task.get("source_text", ""),
        "total_duration_sec": total_duration_sec,
        "global_style": task.get("global_style", {}),
        "segments": segments,
        "license_ref": {
            "license_id": (license_record or {}).get("license_id", ""),
            "rights_holder": (license_record or {}).get("rights_holder", ""),
        },
    }

    ok, errors = validate_blueprint(blueprint)
    if not ok:
        raise RuntimeError("蓝图校验失败：" + "；".join(errors))

    image_handoff = _build_image_handoff(task, blueprint)
    result = {
        "blueprint": blueprint,
        "image_handoff": image_handoff,
    }

    blueprint_path = os.path.join(output_dir, task.get("blueprint_filename", "blueprint.json"))
    handoff_path = os.path.join(output_dir, task.get("handoff_filename", "image_handoff.json"))
    _write_json(blueprint_path, blueprint)
    _write_json(handoff_path, image_handoff)

    return {
        "status": "success",
        "skill": "ip-copy-skill",
        "mode": "build_blueprint",
        "task_id": task.get("task_id", blueprint["blueprint_id"]),
        "artifacts": [
            {"type": "json", "path": blueprint_path, "meta": {"kind": "blueprint"}},
            {"type": "json", "path": handoff_path, "meta": {"kind": "image_handoff"}},
        ],
        "handoff": result,
        "logs": ["blueprint built and validated", "image handoff built"],
    }


def _build_segments(scene_cards: List[Dict], total_duration_sec: float) -> List[Dict]:
    durations = _normalize_durations(scene_cards, total_duration_sec)
    start = 0.0
    segments: List[Dict] = []
    for index, (card, duration_sec) in enumerate(zip(scene_cards, durations), start=1):
        end = round(start + duration_sec, 3)
        segment = {
            "index": index,
            "start_sec": round(start, 3),
            "end_sec": end,
            "visual": card["visual"],
            "voiceover": card["voiceover"],
            "music_cue": card.get("music_cue", ""),
            "transition": card.get("transition", "cut"),
            "subtitle": card.get("subtitle", card["voiceover"]),
            "asset_goal": card.get("asset_goal", {}),
        }
        segments.append(segment)
        start = end

    if segments:
        segments[-1]["end_sec"] = total_duration_sec
    return segments


def _normalize_durations(scene_cards: List[Dict], total_duration_sec: float) -> List[float]:
    explicit = [float(card.get("duration_sec", 0) or 0) for card in scene_cards]
    missing_indexes = [index for index, value in enumerate(explicit) if value <= 0]
    used = sum(value for value in explicit if value > 0)
    remaining = max(total_duration_sec - used, 0.0)

    if missing_indexes:
        share = remaining / len(missing_indexes) if missing_indexes else 0.0
        for index in missing_indexes:
            explicit[index] = share

    total = sum(explicit)
    if total <= 0:
        share = total_duration_sec / len(scene_cards)
        return [share for _ in scene_cards]

    scale = total_duration_sec / total
    return [round(value * scale, 3) for value in explicit]


def _build_image_handoff(task: Dict, blueprint: Optional[Dict] = None) -> Dict:
    image_tasks = []
    if blueprint:
        for segment in blueprint["segments"]:
            image_tasks.append(
                {
                    "mode": "text_to_image",
                    "ip_id": task.get("ip_id"),
                    "asset_kind": segment.get("asset_goal", {}).get("type", "scene_image"),
                    "creative_goal": segment.get("asset_goal", {}).get("purpose", "blueprint scene generation"),
                    "character_profile": task.get("character_sheet", {}).get("character_profile", {}),
                    "identity_anchors": task.get("character_sheet", {}).get("identity_anchors", []),
                    "continuity_rules": task.get("character_sheet", {}).get("continuity_rules", []),
                    "interaction_state": task.get("character_sheet", {}).get("interaction_state", {}),
                    "asset_target": segment.get("asset_goal", {}),
                    "scene": segment["visual"],
                    "prompt": segment["visual"],
                    "emotion": segment.get("asset_goal", {}).get("expression", ""),
                    "output_dir": task.get("image_output_dir", ""),
                }
            )

    return {
        "character_sheet": task.get("character_sheet", {}),
        "asset_bundle": task.get("asset_bundle", []),
        "image_tasks": image_tasks,
        "source_summary": {
            "title": task.get("title", ""),
            "source_text": task.get("source_text", ""),
            "creative_direction": task.get("creative_direction", {}),
        },
    }


def _update_adaptation_state(task: Dict) -> Dict:
    state = copy_dict(task.get("adaptation_state") or {})
    source_text = task.get("source_text") or state.get("source_text", "")
    turns = _normalize_conversation_turns(task.get("conversation_turns") or [])
    user_text = "\n".join(turn["content"] for turn in turns if turn["role"] == "user")
    combined_text = "\n".join(part for part in [source_text, user_text] if part)

    state["title"] = task.get("title") or state.get("title", "")
    state["source_text"] = source_text
    state["conversation_turns"] = (state.get("conversation_turns") or []) + turns

    creative_direction = copy_dict(state.get("creative_direction") or {})
    creative_direction.update({k: v for k, v in (task.get("creative_direction") or {}).items() if v not in (None, "")})
    inferred_direction = _infer_adaptation_direction(combined_text)
    for key, value in inferred_direction.items():
        creative_direction.setdefault(key, value)
    state["creative_direction"] = creative_direction

    constraints = list(state.get("constraints") or [])
    constraints.extend(task.get("constraints") or [])
    constraints.extend(_infer_constraints(user_text))
    state["constraints"] = _dedupe_list(constraints)

    locked = copy_dict(state.get("locked_choices") or {})
    for key in ("target", "tone", "viewpoint", "audience", "format", "episode_count", "duration_sec"):
        if key in task and task[key] not in (None, ""):
            locked[key] = task[key]
        elif key in creative_direction and creative_direction[key] not in (None, ""):
            locked.setdefault(key, creative_direction[key])
    state["locked_choices"] = locked

    state["characters"] = task.get("characters") or state.get("characters") or [
        {"name": name, "role": _infer_role(name, combined_text)}
        for name in _extract_character_candidates(combined_text)[: int(task.get("max_characters", 6) or 6)]
    ]
    state["scenes"] = task.get("scenes") or state.get("scenes") or [
        {"name": scene, "description": scene}
        for scene in _extract_scene_candidates(combined_text)[: int(task.get("max_scenes", 6) or 6)]
    ]
    state["story_beats"] = _build_story_beats(combined_text, creative_direction)
    state["next_questions"] = _adaptation_next_questions(state)
    state["ready_for_scene_cards"] = len(state["next_questions"]) == 0 or bool(task.get("force_ready"))
    return state


def _build_adaptation_scene_cards(state: Dict, task: Dict) -> List[Dict]:
    total_cards = int(task.get("n_scene_cards", state.get("n_scene_cards", 5)) or 5)
    total_cards = max(3, min(total_cards, 8))
    beats = state.get("story_beats") or _build_story_beats(state.get("source_text", ""), state.get("creative_direction", {}))
    scenes = state.get("scenes") or []
    characters = state.get("characters") or []
    direction = state.get("creative_direction", {})
    tone = direction.get("tone", "强钩子、节奏清晰")
    viewpoint = direction.get("viewpoint", "主角视角")

    cards: List[Dict] = []
    for index in range(total_cards):
        beat = beats[index] if index < len(beats) else f"推进第{index + 1}个剧情转折"
        scene = scenes[index % len(scenes)] if scenes else {"name": "核心场景", "description": state.get("source_text", "")}
        character_names = "、".join(item.get("name", "角色") for item in characters[:3]) or "主要角色"
        visual = _scene_visual_from_beat(beat, scene, character_names, tone)
        voiceover = _voiceover_from_beat(beat, viewpoint, index, total_cards)
        cards.append(
            {
                "visual": visual,
                "voiceover": voiceover,
                "music_cue": _music_cue_for_index(index, total_cards, tone),
                "subtitle": voiceover,
                "duration_sec": round(float(task.get("total_duration_sec", 30)) / total_cards, 3),
                "asset_goal": {
                    "type": "adapted scene key frame",
                    "purpose": "short drama adaptation beat",
                    "expression": _expression_for_index(index, total_cards),
                    "scene": scene.get("name", scene.get("description", "")),
                },
            }
        )
    return cards


def _build_script_draft(scene_cards: List[Dict], state: Dict, task: Dict) -> Dict:
    title = task.get("title") or state.get("title", "")
    direction = state.get("creative_direction", task.get("creative_direction", {})) or {}
    total_duration = float(task.get("total_duration_sec", sum(float(card.get("duration_sec", 0) or 0) for card in scene_cards) or 30))
    characters = state.get("characters", task.get("characters", [])) or []
    constraints = state.get("constraints", task.get("constraints", [])) or []

    scenes = []
    start = 0.0
    for index, card in enumerate(scene_cards, start=1):
        duration = float(card.get("duration_sec", 0) or (total_duration / max(len(scene_cards), 1)))
        end = round(start + duration, 3)
        dialogue = _dialogue_from_card(card, characters, index)
        scene = {
            "scene_no": index,
            "title": card.get("asset_goal", {}).get("scene") or f"第{index}场",
            "start_sec": round(start, 3),
            "end_sec": end,
            "location": card.get("asset_goal", {}).get("scene", ""),
            "visual": card.get("visual", ""),
            "action": _action_from_visual(card.get("visual", "")),
            "voiceover": card.get("voiceover", ""),
            "dialogue": dialogue,
            "subtitle": card.get("subtitle", card.get("voiceover", "")),
            "music_cue": card.get("music_cue", ""),
            "transition": card.get("transition", "cut"),
            "asset_goal": card.get("asset_goal", {}),
        }
        scenes.append(scene)
        start = end

    if scenes:
        scenes[-1]["end_sec"] = total_duration

    return {
        "script_id": task.get("script_id", f"{_safe_label(title or 'adaptation')}_script_draft"),
        "title": title,
        "format": direction.get("format", task.get("format", "vertical short drama")),
        "target": direction.get("target", task.get("target", "short_drama")),
        "tone": direction.get("tone", ""),
        "viewpoint": direction.get("viewpoint", ""),
        "audience": direction.get("audience", ""),
        "total_duration_sec": total_duration,
        "source_text": state.get("source_text", task.get("source_text", "")),
        "constraints": constraints,
        "characters": characters,
        "scenes": scenes,
        "handoff": {
            "scene_cards": scene_cards,
            "can_build_blueprint": True,
        },
    }


def _dialogue_from_card(card: Dict, characters: List[Dict], index: int) -> List[Dict]:
    names = [item.get("name") for item in characters if item.get("name")]
    lead = names[0] if names else "主角"
    support = names[1] if len(names) > 1 else "对手"
    beat = card.get("voiceover") or card.get("visual", "")
    if index == 1:
        return [
            {"speaker": lead, "line": "这里不对劲。"},
            {"speaker": support, "line": "现在才发现，已经晚了。"},
        ]
    if "反转" in beat or "规则" in beat or "改变" in beat:
        return [
            {"speaker": lead, "line": "规则不是用来遵守的，是用来被我改写的。"},
            {"speaker": support, "line": "你到底是谁？"},
        ]
    return [
        {"speaker": lead, "line": _short_dialogue_line(beat)},
    ]


def _short_dialogue_line(text: str) -> str:
    cleaned = re.sub(r"^[一二三四五六七八九十]+开始，?", "", str(text or "").strip())
    cleaned = cleaned.replace("一开始，", "").strip()
    if not cleaned:
        return "继续。"
    if len(cleaned) > 24:
        cleaned = cleaned[:24].rstrip("，。；、 ") + "。"
    return cleaned


def _action_from_visual(visual: str) -> str:
    text = str(visual or "").strip()
    if len(text) <= 80:
        return text
    return text[:79].rstrip("，。；、 ") + "。"


def copy_dict(value: Dict) -> Dict:
    return json.loads(json.dumps(value or {}, ensure_ascii=False))


def _normalize_conversation_turns(turns: List) -> List[Dict]:
    normalized = []
    for turn in turns:
        if isinstance(turn, dict):
            role = str(turn.get("role", "user")).strip() or "user"
            content = str(turn.get("content", "")).strip()
        else:
            role = "user"
            content = str(turn).strip()
        if content:
            normalized.append({"role": role, "content": content})
    return normalized


def _infer_adaptation_direction(text: str) -> Dict:
    direction: Dict[str, object] = {}
    if any(word in text for word in ("短剧", "竖屏", "爽点", "反转", "钩子")):
        direction["target"] = "short_drama"
        direction["format"] = "vertical short drama"
    if any(word in text for word in ("悬疑", "诡异", "惊悚", "复苏", "地府", "黄泉")):
        direction["tone"] = "悬疑诡异、强钩子、短剧节奏"
    elif any(word in text for word in ("甜", "恋爱", "治愈")):
        direction["tone"] = "情感治愈、轻悬念、情绪推进"
    if "女主" in text:
        direction["viewpoint"] = "女主视角"
    elif "男主" in text or "老板" in text:
        direction["viewpoint"] = "男主视角"
    if any(word in text for word in ("年轻", "短视频", "抖音", "快手")):
        direction["audience"] = "短视频观众"
    direction.setdefault("adaptation_strength", "保留核心设定，强化短剧冲突和钩子")
    return direction


def _infer_constraints(text: str) -> List[str]:
    constraints = []
    if any(word in text for word in ("不要魔改", "别魔改", "忠实")):
        constraints.append("保留原文核心人物关系和世界观，不做大幅魔改")
    if any(word in text for word in ("不要太血腥", "不血腥", "少血腥")):
        constraints.append("避免血腥描写，用氛围和悬念替代直白暴力")
    if any(word in text for word in ("中文", "中文对白")):
        constraints.append("输出中文对白、旁白和字幕")
    return constraints


def _build_story_beats(text: str, direction: Dict) -> List[str]:
    sentences = [item.strip() for item in re.split(r"[。！？.!?]\s*", text or "") if item.strip()]
    if len(sentences) >= 3:
        beats = sentences[:6]
    else:
        beats = []
    if not beats:
        beats = [
            "开场用异常事件或强视觉制造钩子",
            "主角进入核心场景并发现规则不对劲",
            "重要配角或对手出现，冲突升级",
            "主角用关键道具或身份反转局面",
            "结尾留下更大的世界观悬念",
        ]
    if direction.get("target") == "short_drama" and "开场" not in beats[0]:
        beats.insert(0, "开场前三秒给出高压钩子和明确危机")
    return _dedupe_list(beats)[:8]


def _adaptation_next_questions(state: Dict) -> List[str]:
    questions = []
    direction = state.get("creative_direction", {})
    if not state.get("source_text"):
        questions.append("请提供需要二创改编的原始文案或剧情梗概。")
    if not direction.get("target"):
        questions.append("这次要改成什么形式：短剧、分镜脚本、视频口播，还是图文剧情？")
    if not direction.get("tone"):
        questions.append("希望整体风格是什么：悬疑、爽感、甜宠、治愈、热血，还是暗黑？")
    if not state.get("characters"):
        questions.append("有哪些必须保留的重要角色？")
    if not state.get("constraints"):
        questions.append("有没有不能改的设定、禁区或平台尺度要求？")
    return questions[:4]


def _scene_visual_from_beat(beat: str, scene: Dict, character_names: str, tone: str) -> str:
    scene_text = scene.get("description") or scene.get("name") or "核心场景"
    return f"{scene_text}。{character_names}围绕该剧情点行动：{beat}。画面风格：{tone}。"


def _voiceover_from_beat(beat: str, viewpoint: str, index: int, total: int) -> str:
    if index == 0:
        return f"一开始，{viewpoint}就被卷进了无法解释的危机：{beat}"
    if index == total - 1:
        return f"可真正的答案还没有出现，{beat}"
    return f"{beat}"


def _music_cue_for_index(index: int, total: int, tone: str) -> str:
    if index == 0:
        return f"低频悬念起势，快速建立{tone}"
    if index == total - 1:
        return "悬念收束后留一个上扬尾音"
    return "节奏推进，保持紧张感"


def _expression_for_index(index: int, total: int) -> str:
    if index == 0:
        return "震惊、警觉、被迫进入事件"
    if index == total - 1:
        return "克制、反转后的余震、留下悬念"
    return "紧张、判断、情绪推进"


def _dedupe_list(items: List[str]) -> List[str]:
    result = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _build_ip_asset_pack(task: Dict) -> Dict:
    source_text = task.get("source_text", "")
    ip_id = task.get("ip_id") or _safe_label(task.get("title") or "ip_asset")
    characters = _normalize_asset_pack_characters(task, source_text)
    scenes = _normalize_asset_pack_scenes(task, source_text)
    pack = {
        "mode": "ip_asset_pack",
        "ip_id": ip_id,
        "title": task.get("title", ""),
        "style_preset": task.get("style_preset", "realistic_short_drama"),
        "quality": task.get("quality", "high"),
        "resolution": task.get("resolution", "2K"),
        "visual_text_language": task.get("visual_text_language", "zh-CN"),
        "characters": characters,
        "scenes": scenes,
        "standalone_props": task.get("standalone_props", []),
        "source_summary": {
            "source_text": source_text,
            "creative_direction": task.get("creative_direction", {}),
            "extraction_policy": "multi-character extraction; do not collapse the cast into only the protagonist",
        },
    }
    if task.get("output_dir_for_images"):
        pack["output_dir"] = task["output_dir_for_images"]
    return pack


def _normalize_asset_pack_characters(task: Dict, source_text: str) -> List[Dict]:
    explicit = task.get("characters") or task.get("character_cards") or []
    if explicit:
        return [_normalize_character_card(card, task, source_text) for card in explicit]

    candidates = _extract_character_candidates(source_text)
    if not candidates and task.get("character_sheet"):
        candidates = [
            task.get("character_sheet", {}).get("character_profile", {}).get("identity", {}).get("name", "主角")
        ]
    if not candidates:
        candidates = ["主角"]

    max_characters = int(task.get("max_characters", 6) or 6)
    candidates = candidates[:max_characters]
    return [
        _normalize_character_card({"name": name, "source_text": source_text}, task, source_text)
        for name in candidates
    ]


def _normalize_character_card(card: Dict, task: Dict, source_text: str) -> Dict:
    profile = card.get("character_profile") or {}
    identity = dict(profile.get("identity") or {})
    name = card.get("name") or card.get("character_name") or identity.get("name") or "角色"
    role = card.get("role") or identity.get("role") or _infer_role(name, source_text)
    identity["name"] = name
    identity["role"] = role
    if card.get("gender_presentation"):
        identity["gender_presentation"] = card["gender_presentation"]

    normalized_profile = dict(profile)
    normalized_profile["identity"] = identity
    if card.get("appearance") and "appearance" not in normalized_profile:
        normalized_profile["appearance"] = card["appearance"]
    if card.get("styling") and "styling" not in normalized_profile:
        normalized_profile["styling"] = card["styling"]
    if card.get("personality") and "personality" not in normalized_profile:
        normalized_profile["personality"] = card["personality"]
    if "world_context" not in normalized_profile:
        normalized_profile["world_context"] = {
            "setting": task.get("title", ""),
            "source_hint": _clip_text(source_text, 160),
        }

    props = card.get("props")
    if props is None:
        props = _infer_props_for_character(name, source_text)

    identity_anchors = card.get("identity_anchors") or [
        f"保持{name}的同一人物识别",
        "后续所有资产保持同一脸型、发型轮廓和服装身份",
    ]
    continuity_rules = card.get("continuity_rules") or [
        "不要把该角色和其他角色混合",
        "后续图像必须保持角色身份连续",
    ]

    return {
        "character_id": card.get("character_id") or _safe_label(name),
        "character_profile": normalized_profile,
        "identity_anchors": identity_anchors,
        "continuity_rules": continuity_rules,
        "props": props,
    }


def _normalize_asset_pack_scenes(task: Dict, source_text: str) -> List[Dict]:
    explicit = task.get("scenes") or task.get("scene_cards") or []
    if explicit:
        return [_normalize_scene_card(scene, index) for index, scene in enumerate(explicit, start=1)]

    candidates = _extract_scene_candidates(source_text)
    if not candidates:
        candidates = [task.get("title") or "核心场景"]
    max_scenes = int(task.get("max_scenes", 4) or 4)
    return [
        _normalize_scene_card({"name": scene, "description": scene}, index)
        for index, scene in enumerate(candidates[:max_scenes], start=1)
    ]


def _normalize_scene_card(scene: Dict, index: int) -> Dict:
    name = scene.get("name") or scene.get("scene") or scene.get("visual") or scene.get("description") or f"场景{index}"
    description = scene.get("description") or scene.get("visual") or scene.get("scene") or name
    return {
        "scene_id": scene.get("scene_id") or f"{_safe_label(name)}_720",
        "name": name,
        "description": description,
        "purpose": scene.get("purpose", "720 panorama environment reference for camera movement and scene generation"),
        "lighting": scene.get("lighting", _infer_lighting(description)),
        "size": scene.get("size", "21:9"),
        "resolution": scene.get("resolution", "4K"),
    }


def _extract_character_candidates(source_text: str) -> List[str]:
    text = source_text or ""
    candidates: List[str] = []

    quoted = re.findall(r"[《「“\"]([^《》「」“”\"]{1,12})[》」”\"]", text)
    candidates.extend(_looks_like_character_name(item) for item in quoted)

    cjk_titles = [
        "老板",
        "店主",
        "掌柜",
        "女主",
        "男主",
        "少女",
        "少年",
        "男人",
        "女人",
        "母亲",
        "父亲",
        "警察",
        "医生",
        "员工",
        "客人",
        "怪物",
        "鬼差",
        "牛头",
        "马面",
        "阎王",
    ]
    for title in cjk_titles:
        if title in text:
            candidates.append(title)

    name_patterns = re.findall(
        r"(?<![\u4e00-\u9fff])([\u4e00-\u9fff]{2,3})(?=(?:在|用|走|看|说|拿|拿着|背着|端着|站|坐|冲|推|递|握|发现|确认|显示|进入|离开|来到|回到|盯着|望向))",
        text,
    )
    candidates.extend(name_patterns)

    latin_names = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", text)
    candidates.extend(name for name in latin_names if name.lower() not in {"the", "a", "an"})

    normalized: List[str] = []
    seen = set()
    for item in candidates:
        name = str(item or "").strip(" ，。！？,.!?:;；")
        if not _is_valid_character_candidate(name):
            continue
        if name not in seen:
            normalized.append(name)
            seen.add(name)
    return normalized


def _is_valid_character_candidate(name: str) -> bool:
    if not name or len(name) > 24:
        return False
    blocked_exact = {
        "手里还",
        "柜台上",
        "生存",
        "背包",
        "菜单",
        "账本",
        "托盘",
        "菜刀",
        "探测器",
        "酒店",
        "饭店",
        "大厅",
        "厨房",
        "门口",
    }
    if name in blocked_exact:
        return False
    blocked_parts = ("手里", "柜台", "背包", "菜单", "账本", "探测", "异常", "能量")
    return not any(part in name for part in blocked_parts)


def _looks_like_character_name(value: str) -> str:
    return str(value or "").strip()


def _extract_scene_candidates(source_text: str) -> List[str]:
    text = source_text or ""
    scene_keywords = [
        "酒店",
        "饭店",
        "便利店",
        "街道",
        "雨夜",
        "大厅",
        "办公室",
        "厨房",
        "废墟",
        "基地",
        "车站",
        "学校",
        "医院",
        "门口",
        "走廊",
        "餐厅",
        "仓库",
        "荒原",
    ]
    scenes: List[str] = []
    for keyword in scene_keywords:
        if keyword in text:
            scenes.append(_scene_description_for_keyword(keyword, text))

    sentence_scenes = re.split(r"[。！？.!?]\s*", text)
    for sentence in sentence_scenes:
        if any(marker in sentence for marker in ("在", "来到", "进入", "外", "内", "门口", "大厅")):
            clipped = _clip_text(sentence, 80)
            if clipped:
                scenes.append(clipped)

    deduped: List[str] = []
    seen = set()
    for scene in scenes:
        if scene not in seen:
            deduped.append(scene)
            seen.add(scene)
    return deduped


def _scene_description_for_keyword(keyword: str, source_text: str) -> str:
    if keyword in {"雨夜", "街道", "门口"}:
        return f"{keyword}环境，来自原文氛围：{_clip_text(source_text, 80)}"
    return f"{keyword}环境参考，来自原文核心场景"


def _infer_props_for_character(name: str, source_text: str) -> List[Dict]:
    context = _character_context(name, source_text) or source_text
    prop_keywords = {
        "菜单": "经营身份道具",
        "账本": "经营或记录身份道具",
        "手帕": "人物动作细节道具",
        "红酒": "餐桌和身份氛围道具",
        "酒杯": "餐桌和身份氛围道具",
        "菜刀": "厨房或威慑身份道具",
        "托盘": "服务身份道具",
        "背包": "行动和生存装备",
        "探测器": "探测异常能量或线索",
        "手机": "现代沟通道具",
        "伞": "雨景动作道具",
        "钥匙": "空间进入和悬念道具",
    }
    props = []
    for keyword, use in prop_keywords.items():
        if keyword in context:
            props.append({"name": keyword, "use": use})
    return props[:4]


def _infer_role(name: str, source_text: str) -> str:
    role_hints = {
        "老板": "经营者 / 店主",
        "店主": "经营者 / 店主",
        "掌柜": "经营者 / 掌柜",
        "女主": "主要女性角色",
        "男主": "主要男性角色",
        "员工": "服务人员 / 员工",
        "客人": "顾客 / 外来者",
        "鬼差": "超自然执法者",
        "牛头": "地府执行者 / 怪物员工",
        "马面": "地府执行者 / 怪物员工",
        "阎王": "地府权力角色",
    }
    for key, role in role_hints.items():
        if key in name:
            return role

    context = _character_context(name, source_text)
    if _context_has_near(context, name, "探测器") or _context_has_near(context, name, "异常能量"):
        return "调查者 / 异常能量探测者"
    if _context_has_near(context, name, "背包") or _context_has_near(context, name, "基地"):
        return "行动小队成员 / 生存者"
    for key, role in role_hints.items():
        if _context_has_role_phrase(context, name, key):
            return role
    return "重要角色 / 待细化"


def _context_has_role_phrase(context: str, name: str, keyword: str) -> bool:
    if not context or not name or not keyword:
        return False
    patterns = (
        f"{name}{keyword}",
        f"{keyword}{name}",
        f"{name}是{keyword}",
        f"{name}作为{keyword}",
        f"{name}这个{keyword}",
        f"{keyword}，{name}",
        f"{keyword}{name}",
    )
    return any(pattern in context for pattern in patterns)


def _context_has_near(context: str, name: str, keyword: str, window: int = 12) -> bool:
    if not context or not name or not keyword:
        return False
    for match in re.finditer(re.escape(name), context):
        start = max(match.start() - window, 0)
        end = min(match.end() + window, len(context))
        if keyword in context[start:end]:
            return True
    return False


def _character_context(name: str, source_text: str) -> str:
    if not name or not source_text:
        return ""
    sentences = re.split(r"(?<=[。！？.!?])\s*", source_text)
    for sentence in sentences:
        if name in sentence:
            return sentence
    index = source_text.find(name)
    if index < 0:
        return ""
    start = max(index - 40, 0)
    end = min(index + len(name) + 80, len(source_text))
    return source_text[start:end]


def _infer_lighting(description: str) -> str:
    if any(word in description for word in ("夜", "雨", "霓虹", "黑", "暗")):
        return "night or low-key cinematic lighting"
    if any(word in description for word in ("大厅", "酒店", "饭店", "餐厅")):
        return "interior practical lighting with cinematic contrast"
    return "cinematic environment lighting"


def _clip_text(value: str, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _safe_label(value: Optional[str]) -> str:
    text = str(value or "asset").strip().lower()
    keep = []
    for char in text:
        if char.isalnum():
            keep.append(char)
        elif char in ("-", "_", " "):
            keep.append("_")
    label = "".join(keep).strip("_")
    while "__" in label:
        label = label.replace("__", "_")
    return (label or "asset")[:48].strip("_") or "asset"


def _load_license_record(ip_id: Optional[str], license_path: Optional[str]) -> Optional[Dict]:
    if license_path:
        if not os.path.exists(license_path):
            raise FileNotFoundError(license_path)
        with open(license_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    if not ip_id:
        return None
    default_path = os.path.join(os.path.dirname(__file__), "..", "references", "licenses", f"{ip_id}.json")
    if not os.path.exists(default_path):
        return None
    with open(default_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: str, payload: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _parse_today(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    year, month, day = (int(part) for part in value.split("-"))
    return date(year, month, day)


def _cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="Path to a task JSON file")
    args = parser.parse_args()

    with open(args.task, "r", encoding="utf-8") as fh:
        task = json.load(fh)

    result = run_task(task)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
