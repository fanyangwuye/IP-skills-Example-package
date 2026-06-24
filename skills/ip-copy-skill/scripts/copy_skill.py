import argparse
import json
import os
import re
from datetime import date
from typing import Dict, List, Optional

try:
    from .blueprint_validate import validate_blueprint
    from .creative_engine import CreativeEngineRequest, EngineBlockedError, LiveLLMEngine, MockCreativeEngine, OfflineCreativeEngine, build_prompt_pack, build_provider_request, summarize_provider_request
    from .format_adapters import FeatureFilmAdapter, InteractiveFilmGameAdapter, LongSeriesAdapter, MurderMysteryAdapter, OverseasShortDramaAdapter, VerticalShortDramaAdapter
    from .license_gate import check_license, gate
    from .quality_evaluator import evaluate_scene_cards_quality, evaluate_script_quality
except ImportError:
    from blueprint_validate import validate_blueprint
    from creative_engine import CreativeEngineRequest, EngineBlockedError, LiveLLMEngine, MockCreativeEngine, OfflineCreativeEngine, build_prompt_pack, build_provider_request, summarize_provider_request
    from format_adapters import FeatureFilmAdapter, InteractiveFilmGameAdapter, LongSeriesAdapter, MurderMysteryAdapter, OverseasShortDramaAdapter, VerticalShortDramaAdapter
    from license_gate import check_license, gate
    from quality_evaluator import evaluate_scene_cards_quality, evaluate_script_quality


def run_task(task: Dict) -> Dict:
    mode = task.get("mode", "build_blueprint")
    output_dir = task.get("output_dir") or os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    if mode == "check_license":
        return _run_check_license(task)
    if mode == "update_adaptation_state":
        return _run_update_adaptation_state(task, output_dir)
    if mode == "build_creative_prompt_pack":
        return _run_build_creative_prompt_pack(task, output_dir)
    if mode == "build_adaptation_scene_cards":
        return _run_build_adaptation_scene_cards(task, output_dir)
    if mode == "build_script_draft":
        return _run_build_script_draft(task, output_dir)
    if mode == "polish_script_draft":
        return _run_polish_script_draft(task, output_dir)
    if mode == "build_viral_explainer_script":
        return _run_build_viral_explainer_script(task, output_dir)
    if mode == "build_ip_asset_pack":
        return _run_build_ip_asset_pack(task, output_dir)
    if mode == "build_character_handoff":
        return _run_build_character_handoff(task, output_dir)
    if mode == "build_blueprint":
        return _run_build_blueprint(task, output_dir)
    raise ValueError("mode must be one of: check_license, build_blueprint, build_character_handoff, build_ip_asset_pack, update_adaptation_state, build_creative_prompt_pack, build_adaptation_scene_cards, build_script_draft, polish_script_draft, build_viral_explainer_script")


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
    adapter = _format_adapter_from_task(task, state.get("creative_direction", {}))
    payload = {
        "title": state.get("title", task.get("title", "")),
        "source_text": state.get("source_text", task.get("source_text", "")),
        "creative_direction": state.get("creative_direction", {}),
        "format_adapter": adapter.spec().format_name,
        "scene_cards": scene_cards,
        "quality_report": evaluate_scene_cards_quality(scene_cards, adapter.spec(), context={"source_text": state.get("source_text", task.get("source_text", "")), "characters": state.get("characters", task.get("characters", []))}),
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


def _run_polish_script_draft(task: Dict, output_dir: str) -> Dict:
    script = task.get("script_draft") or {}
    if not script:
        draft_result = _run_build_script_draft(task, output_dir)
        script = draft_result["handoff"]["script_draft"]
    polished = _polish_script_draft(script, task)
    out_path = os.path.join(output_dir, task.get("polished_script_filename", "polished_script.json"))
    _write_json(out_path, polished)
    return {
        "status": "success",
        "skill": "ip-copy-skill",
        "mode": "polish_script_draft",
        "task_id": task.get("task_id", "polish_script_draft"),
        "artifacts": [
            {
                "type": "json",
                "path": out_path,
                "meta": {"kind": "polished_script"},
            }
        ],
        "handoff": {
            "polished_script": polished,
        },
        "logs": [f"polished script draft with {len(polished['scenes'])} scenes"],
    }



def _run_build_creative_prompt_pack(task: Dict, output_dir: str) -> Dict:
    request = _creative_prompt_request_from_task(task)
    prompt_pack = build_prompt_pack(request)
    provider_request = build_provider_request(
        prompt_pack,
        provider=str(task.get("llm_provider") or task.get("provider") or ""),
        model=str(task.get("llm_model") or task.get("model") or ""),
        allow_live=bool(task.get("allow_live_llm")),
        request_allow_live=bool(task.get("live_generation") or task.get("allow_live_llm")),
        max_input_chars=int(task.get("max_input_chars") or 0),
        max_output_tokens=int(task.get("max_output_tokens") or 0),
        max_cost_usd=float(task.get("max_cost_usd") or 0.0),
    )
    payload = {
        "prompt_pack": prompt_pack,
        "provider_request": provider_request,
        "provider_request_summary": summarize_provider_request(provider_request),
        "live_call_made": False,
    }
    out_path = os.path.join(output_dir, task.get("prompt_pack_filename", "creative_prompt_pack.json"))
    _write_json(out_path, payload)
    return {
        "status": "success",
        "skill": "ip-copy-skill",
        "mode": "build_creative_prompt_pack",
        "task_id": task.get("task_id", "build_creative_prompt_pack"),
        "artifacts": [
            {"type": "json", "path": out_path, "meta": {"kind": "creative_prompt_pack"}}
        ],
        "handoff": payload,
        "logs": ["creative prompt pack built in dry-run mode; no live provider call was made"],
    }


def _creative_prompt_request_from_task(task: Dict) -> CreativeEngineRequest:
    state = task.get("adaptation_state") or {}
    creative_brief = task.get("creative_brief") or state.get("creative_direction") or task.get("creative_direction") or {}
    adapter = _format_adapter_from_task(task, creative_brief)
    kind = str(task.get("prompt_kind") or task.get("creative_kind") or "scene_cards").strip()
    schema_name = task.get("schema_name") or _schema_for_creative_kind(kind)
    payload = dict(task.get("payload") or {})
    payload.setdefault("title", state.get("title", task.get("title", "")))
    payload.setdefault("characters", state.get("characters", task.get("characters", [])))
    payload.setdefault("scenes", state.get("scenes", task.get("scenes", [])))
    payload.setdefault("story_beats", state.get("story_beats", task.get("story_beats", [])))
    if task.get("scene_cards") is not None:
        payload.setdefault("scene_cards", task.get("scene_cards"))
    if task.get("script_draft") is not None:
        payload.setdefault("script", task.get("script_draft"))
    payload.setdefault("adapter", adapter.creative_engine_payload(state, task))
    return CreativeEngineRequest(
        kind=kind,
        source_text=state.get("source_text", task.get("source_text", "")),
        creative_brief=creative_brief,
        format_name=adapter.spec().format_name,
        schema_name=schema_name,
        payload=payload,
        allow_live=bool(task.get("allow_live_llm") or task.get("live_generation")),
    )


def _schema_for_creative_kind(kind: str) -> str:
    if kind == "scene_cards":
        return "scene_cards"
    if kind in {"script_scenes", "polished_script_scenes"}:
        return "script_scenes"
    if kind == "source_analysis":
        return "source_analysis"
    return kind


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



def _run_build_viral_explainer_script(task: Dict, output_dir: str) -> Dict:
    explainer = _build_viral_explainer_script(task)
    out_path = os.path.join(output_dir, task.get("viral_explainer_filename", "viral_explainer_script.json"))
    _write_json(out_path, explainer)
    return {
        "status": "success",
        "skill": "ip-copy-skill",
        "mode": "build_viral_explainer_script",
        "task_id": task.get("task_id", "build_viral_explainer_script"),
        "artifacts": [
            {"type": "json", "path": out_path, "meta": {"kind": "viral_explainer_script"}}
        ],
        "handoff": {"viral_explainer_script": explainer},
        "logs": [f"built viral explainer script for {len(explainer['episodes'])} episode(s)"],
    }


def _build_viral_explainer_script(task: Dict) -> Dict:
    source_text = task.get("source_text") or _source_text_from_script(task.get("script_draft") or task.get("polished_script") or {})
    if not source_text:
        raise ValueError("build_viral_explainer_script requires source_text, script_draft, or polished_script")
    title = task.get("title") or _infer_title(source_text) or "未命名IP"
    episodes = _extract_episode_blocks(source_text)
    max_episodes = int(task.get("max_episodes") or task.get("episode_count") or len(episodes) or 1)
    episodes = episodes[:max(1, max_episodes)]
    if not episodes:
        episodes = [{"episode_index": 1, "title": title, "body": source_text}]
    style = task.get("style_profile") or {}
    viewpoint = task.get("viewpoint") or style.get("viewpoint") or "第三人称解说"
    intensity = task.get("viral_intensity") or style.get("viral_intensity") or "爽感强、悬念强、节奏快"
    platform = task.get("target_platform") or style.get("target_platform") or "short_video"
    per_episode_duration = int(task.get("per_episode_duration_sec") or 90)
    built = [
        _build_explainer_episode(block, title, viewpoint, intensity, platform, per_episode_duration)
        for block in episodes
    ]
    return {
        "title": title,
        "mode": "viral_explainer_script",
        "target_platform": platform,
        "viewpoint": viewpoint,
        "style_profile": {
            "viral_intensity": intensity,
            "opening_policy": "first 3 seconds must state conflict, reversal, or survival pressure",
            "rewrite_boundary": "retell and compress story beats; do not invent new plot facts or replace locked characters",
        },
        "episodes": built,
        "quality_checks": [
            "每集开头是否有强钩子",
            "是否按原剧情顺序压缩爽点和反转",
            "是否保留真实角色和关键设定",
            "是否用口播文案承接下一集悬念",
            "是否避免把场景卡当成最终解说稿",
        ],
    }


def _build_explainer_episode(block: Dict, title: str, viewpoint: str, intensity: str, platform: str, duration_sec: int) -> Dict:
    body = block.get("body", "")
    sentences = _split_story_sentences(body)
    characters = _extract_character_candidates(body)[:5]
    names = "、".join(characters) if characters else "主角"
    core = sentences[0] if sentences else body
    twist = _select_twist_sentence(sentences)
    ending = sentences[-1] if sentences else core
    narration = _build_explainer_lines(sentences, names, viewpoint)
    hook = _build_explainer_hook(core, twist, names, intensity)
    cliffhanger = _build_explainer_cliffhanger(ending, twist, names)
    return {
        "episode_index": block.get("episode_index", 1),
        "episode_title": block.get("title") or f"{title} 第{block.get('episode_index', 1)}集",
        "duration_sec": duration_sec,
        "opening_hook": hook,
        "narration_lines": narration,
        "cliffhanger": cliffhanger,
        "retention_devices": [
            "开头直接抛出危机或反转，不铺设定",
            "每20-30秒补一次新信息或新压力",
            "结尾用未解决问题承接下一集",
        ],
        "platform_notes": {
            "target_platform": platform,
            "delivery": "短句、强停顿、适合口播剪辑",
            "boundary": "不新增角色、不改动原剧情因果、不把解说稿写成分镜场景卡",
        },
        "source_excerpt": _clip_text(body, 360),
    }


def _build_explainer_hook(core: str, twist: str, names: str, intensity: str) -> str:
    if twist and twist != core:
        return f"谁能想到，{names}刚卷进这件事，真正的反转就已经埋好了：{_trim_sentence(twist, 54)}"
    return f"一开场，{names}就遇上了最不该发生的事：{_trim_sentence(core, 58)}"


def _build_explainer_lines(sentences: List[str], names: str, viewpoint: str) -> List[str]:
    selected = sentences[:8] if sentences else []
    if not selected:
        return [f"故事从{names}的异常遭遇开始。"]
    lines = []
    for index, sentence in enumerate(selected):
        trimmed = _trim_sentence(sentence, 64)
        if index == 0:
            lines.append(f"故事一开始，{trimmed}")
        elif index == 1:
            lines.append(f"但问题很快不对劲，{trimmed}")
        elif index == len(selected) - 1:
            lines.append(f"等到这里，局面已经彻底变了，{trimmed}")
        else:
            lines.append(f"接着，{trimmed}")
    return lines


def _build_explainer_cliffhanger(ending: str, twist: str, names: str) -> str:
    base = twist or ending
    return f"可{names}还不知道，{_trim_sentence(base, 48)}，这才只是麻烦的开始。"


def _select_twist_sentence(sentences: List[str]) -> str:
    markers = ("突然", "没想到", "竟", "反而", "真正", "发现", "原来", "却", "危机", "规则", "系统", "死亡", "异常")
    for sentence in sentences:
        if any(marker in sentence for marker in markers):
            return sentence
    return sentences[-1] if sentences else ""


def _extract_episode_blocks(text: str) -> List[Dict]:
    blocks = []
    current_title = ""
    current_index = 0
    body_lines: List[str] = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^第\s*([一二三四五六七八九十百千万\d]+)\s*[集话回章](?:[：:：\s-]*(.*))?$", line)
        if match:
            if body_lines and current_index:
                blocks.append({"episode_index": current_index, "title": current_title, "body": "\n".join(body_lines)})
            current_index = _episode_number(match.group(1)) or len(blocks) + 1
            current_title = line
            body_lines = []
        else:
            body_lines.append(line)
    if body_lines:
        blocks.append({"episode_index": current_index or len(blocks) + 1, "title": current_title, "body": "\n".join(body_lines)})
    return blocks


def _episode_number(value: str) -> int:
    text = str(value or "").strip()
    if text.isdigit():
        return int(text)
    numerals = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    if text == "十":
        return 10
    if text.startswith("十"):
        return 10 + numerals.get(text[1:], 0)
    if "十" in text:
        left, _, right = text.partition("十")
        return numerals.get(left, 0) * 10 + numerals.get(right, 0)
    return numerals.get(text, 0)


def _split_story_sentences(text: str) -> List[str]:
    chunks = re.split(r"[。！？!?]\s*|\n+", str(text or ""))
    return [item.strip(" △\t") for item in chunks if item.strip(" △\t")]


def _trim_sentence(text: str, limit: int) -> str:
    return _clip_text(str(text or "").strip(), limit)


def _source_text_from_script(script: Dict) -> str:
    scenes = script.get("scenes") or []
    parts = []
    for scene in scenes:
        parts.extend(str(scene.get(key, "")) for key in ("visual", "voiceover", "action"))
        for dialogue in scene.get("dialogue") or []:
            parts.append(str(dialogue.get("line", "")))
    return "\n".join(part for part in parts if part)


def _infer_title(text: str) -> str:
    for line in str(text or "").splitlines():
        line = line.strip()
        if line and not line.startswith("第") and len(line) <= 24:
            return line
    return ""

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
    screenplay_cards = _build_screenplay_scene_cards(state, task)
    if screenplay_cards:
        return _mark_scene_card_generation(screenplay_cards, "screenplay_scaffold")

    engine_result = _try_creative_scene_cards(state, task)
    if engine_result and engine_result.ok:
        cards = _mark_scene_card_generation(_normalize_creative_scene_cards(engine_result.data, task), engine_result.generation_source)
        return _attach_scene_card_review(cards, engine_result.review_report)
    if engine_result and _creative_engine_explicit(task) and engine_result.status != "fallback_required":
        raise ValueError("CreativeEngine scene card generation failed: " + "；".join(engine_result.errors or engine_result.warnings))

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
    return _mark_scene_card_generation(cards, "fallback_scaffold")


def _try_creative_scene_cards(state: Dict, task: Dict):
    engine = _creative_engine_from_task(task)
    adapter = _format_adapter_from_task(task, state.get("creative_direction", {}))
    request = CreativeEngineRequest(
        kind="scene_cards",
        source_text=state.get("source_text", task.get("source_text", "")),
        creative_brief=state.get("creative_direction", task.get("creative_direction", {})),
        format_name=adapter.spec().format_name,
        schema_name="scene_cards",
        payload={
            "title": state.get("title", task.get("title", "")),
            "characters": state.get("characters", []),
            "scenes": state.get("scenes", []),
            "story_beats": state.get("story_beats", []),
            "n_scene_cards": task.get("n_scene_cards", state.get("n_scene_cards", 5)),
            "total_duration_sec": task.get("total_duration_sec", 30),
            "adapter": adapter.creative_engine_payload(state, task),
        },
        allow_live=bool(task.get("allow_live_llm") or task.get("live_generation")),
    )
    try:
        return engine.generate(request)
    except EngineBlockedError:
        raise


def _creative_engine_from_task(task: Dict):
    mode = str(task.get("creative_engine") or task.get("creative_engine_mode") or "offline").strip().lower()
    outputs = task.get("creative_engine_outputs") or task.get("mock_creative_outputs") or {}
    if mode == "mock" or outputs:
        return MockCreativeEngine(outputs)
    if mode in {"live", "live_llm", "llm"}:
        return LiveLLMEngine(provider=str(task.get("llm_provider") or task.get("provider") or ""), model=str(task.get("llm_model") or task.get("model") or ""), allow_live=bool(task.get("allow_live_llm")))
    return OfflineCreativeEngine()


def _creative_engine_explicit(task: Dict) -> bool:
    return bool(task.get("creative_engine") or task.get("creative_engine_mode") or task.get("creative_engine_outputs") or task.get("mock_creative_outputs"))


def _normalize_creative_scene_cards(cards: List[Dict], task: Dict) -> List[Dict]:
    normalized = []
    for card in cards:
        item = dict(card)
        item.setdefault("subtitle", item.get("voiceover", ""))
        item.setdefault("music_cue", "按场景情绪推进")
        item.setdefault("duration_sec", round(float(task.get("total_duration_sec", 30)) / max(len(cards), 1), 3))
        asset_goal = dict(item.get("asset_goal") or {})
        asset_goal.setdefault("type", "adapted scene key frame")
        asset_goal.setdefault("purpose", "creative engine scene beat")
        item["asset_goal"] = asset_goal
        normalized.append(item)
    return normalized


def _attach_scene_card_review(cards: List[Dict], review_report: Dict) -> List[Dict]:
    if not review_report:
        return cards
    attached = []
    for card in cards:
        item = dict(card)
        item.setdefault("creative_engine_review_status", review_report.get("status", ""))
        item.setdefault("creative_engine_review_warnings", review_report.get("warnings", []))
        attached.append(item)
    return attached

def _mark_scene_card_generation(cards: List[Dict], source: str) -> List[Dict]:
    marked = []
    for card in cards:
        item = dict(card)
        item.setdefault("generation_source", source)
        marked.append(item)
    return marked


def _build_screenplay_scene_cards(state: Dict, task: Dict) -> List[Dict]:
    sections = _extract_screenplay_sections(state.get("source_text", ""))
    if not sections:
        return []
    direction = state.get("creative_direction", {}) or {}
    tone = direction.get("tone", "强钩子、节奏清晰")
    viewpoint = direction.get("viewpoint", "主角视角")
    total_duration = float(task.get("total_duration_sec", 0) or state.get("duration_sec", 0) or max(len(sections) * 6, 6))
    duration = round(total_duration / max(len(sections), 1), 3)

    cards: List[Dict] = []
    for index, section in enumerate(sections):
        cast = section.get("cast") or []
        character_names = "、".join(cast) if cast else "本场角色"
        beat = section.get("summary") or section.get("body", "")
        visual = _scene_visual_from_beat(beat, {"name": section["header"], "description": section["header"]}, character_names, tone)
        voiceover = _voiceover_from_beat(beat, viewpoint, index, len(sections))
        cards.append(
            {
                "visual": visual,
                "voiceover": voiceover,
                "music_cue": _music_cue_for_index(index, len(sections), tone),
                "subtitle": voiceover,
                "duration_sec": duration,
                "characters": [{"name": name} for name in cast],
                "asset_goal": {
                    "type": "adapted scene key frame",
                    "purpose": "screenplay scene beat",
                    "expression": _expression_for_index(index, len(sections)),
                    "scene": section["header"],
                },
            }
        )
    return cards


def _extract_screenplay_sections(text: str) -> List[Dict]:
    sections: List[Dict] = []
    current: Optional[Dict] = None
    body_lines: List[str] = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^场\s*\d+(?:[-－]\d+)?\s+", line):
            if current:
                current["body"] = "\n".join(body_lines).strip()
                current["summary"] = _screenplay_section_summary(body_lines)
                sections.append(current)
            current = {"header": line, "cast": []}
            body_lines = []
            continue
        if current and line.startswith("出场人物"):
            current["cast"] = _extract_cast_line_characters(line)
            continue
        if current:
            body_lines.append(line)
    if current:
        current["body"] = "\n".join(body_lines).strip()
        current["summary"] = _screenplay_section_summary(body_lines)
        sections.append(current)
    return sections


def _screenplay_section_summary(lines: List[str]) -> str:
    meaningful = []
    for line in lines:
        text = str(line or "").strip()
        if not text or text in {"闪回：", "闪出。"}:
            continue
        meaningful.append(text)
        if len(meaningful) >= 3:
            break
    return " ".join(meaningful)

def _format_adapter_from_task(task: Dict, direction: Dict = None):
    direction = direction or {}
    name = str(task.get("format_adapter") or task.get("target_format") or direction.get("format_adapter") or direction.get("target") or "vertical_short_drama").strip().lower()
    if name in {"interactive_film_game", "interactive_film", "interactive_game", "branching_film", "choice_drama", "互动影游", "互动剧", "互动电影", "分支剧情", "互动影游剧本"}:
        return InteractiveFilmGameAdapter()
    if name in {"murder_mystery", "scripted_murder", "jubensha", "case_game", "detective_game", "剧本杀", "推理剧本", "案件本", "本格推理"}:
        return MurderMysteryAdapter()
    if name in {"long_series", "series", "tv_series", "drama_series", "long_drama", "tv_drama", "长剧", "长剧剧本", "剧集", "电视剧", "连续剧"}:
        return LongSeriesAdapter()
    if name in {"feature_film", "film", "movie", "feature", "cinema", "电影", "电影剧本", "大电影"}:
        return FeatureFilmAdapter()
    if name in {"overseas_short_drama", "overseas", "international_short_drama", "english_short_drama", "海外短剧", "海外短剧剧本"}:
        return OverseasShortDramaAdapter()
    if name in {"vertical_short_drama", "short_drama", "short_drama_script", "竖屏短剧", "短剧"}:
        return VerticalShortDramaAdapter()
    return VerticalShortDramaAdapter()

def _build_script_draft(scene_cards: List[Dict], state: Dict, task: Dict) -> Dict:
    title = task.get("title") or state.get("title", "")
    direction = state.get("creative_direction", task.get("creative_direction", {})) or {}
    total_duration = float(task.get("total_duration_sec", sum(float(card.get("duration_sec", 0) or 0) for card in scene_cards) or 30))
    characters = state.get("characters", task.get("characters", [])) or []
    constraints = state.get("constraints", task.get("constraints", [])) or []
    adapter = _format_adapter_from_task(task, direction)
    spec = adapter.spec()
    creative_engine_review = {}

    engine_result = _try_creative_script_scenes(scene_cards, state, task, total_duration, adapter)
    if engine_result and engine_result.ok:
        scenes = _normalize_creative_script_scenes(engine_result.data, total_duration, engine_result.generation_source)
        generation_source = engine_result.generation_source
        creative_engine_review = engine_result.review_report
    elif engine_result and _creative_engine_explicit(task) and engine_result.status != "fallback_required":
        raise ValueError("CreativeEngine script draft generation failed: " + "；".join(engine_result.errors or engine_result.warnings))
    else:
        scenes = _fallback_script_scenes(scene_cards, characters, total_duration)
        generation_source = "fallback_scaffold"

    return {
        "script_id": task.get("script_id", f"{_safe_label(title or 'adaptation')}_script_draft"),
        "title": title,
        "format": direction.get("format", task.get("format", "vertical short drama")),
        "target": direction.get("target", task.get("target", "short_drama")),
        "format_adapter": spec.format_name,
        "aspect_ratio": task.get("aspect_ratio") or spec.default_aspect_ratio,
        "rhythm_rules": spec.rhythm_rules,
        "quality_checks": spec.quality_checks,
        "generation_source": generation_source,
        "creative_engine_review": creative_engine_review,
        "tone": direction.get("tone", ""),
        "viewpoint": direction.get("viewpoint", ""),
        "audience": direction.get("audience", ""),
        "total_duration_sec": total_duration,
        "source_text": state.get("source_text", task.get("source_text", "")),
        "constraints": constraints,
        "characters": characters,
        "scenes": scenes,
        "quality_report": evaluate_script_quality({
            "scenes": scenes,
            "aspect_ratio": task.get("aspect_ratio") or spec.default_aspect_ratio,
            "source_text": state.get("source_text", task.get("source_text", "")),
            "characters": characters,
            "handoff": {
                "can_build_blueprint": True,
                "image_requirements": spec.handoff_requirements.get("image", []),
                "video_requirements": spec.handoff_requirements.get("video", []),
                "music_requirements": spec.handoff_requirements.get("music", []),
                "copy_requirements": spec.handoff_requirements.get("copy", []),
            },
        }, spec, context={"source_text": state.get("source_text", task.get("source_text", "")), "characters": characters}),
        "handoff": {
            "scene_cards": scene_cards,
            "can_build_blueprint": True,
            "format_adapter": spec.format_name,
            "image_requirements": spec.handoff_requirements.get("image", []),
            "video_requirements": spec.handoff_requirements.get("video", []),
            "music_requirements": spec.handoff_requirements.get("music", []),
            "copy_requirements": spec.handoff_requirements.get("copy", []),
        },
    }


def _try_creative_script_scenes(scene_cards: List[Dict], state: Dict, task: Dict, total_duration: float, adapter):
    engine = _creative_engine_from_task(task)
    request = CreativeEngineRequest(
        kind="script_scenes",
        source_text=state.get("source_text", task.get("source_text", "")),
        creative_brief=state.get("creative_direction", task.get("creative_direction", {})),
        format_name=adapter.spec().format_name,
        schema_name="script_scenes",
        payload={
            "scene_cards": scene_cards,
            "total_duration_sec": total_duration,
            "adapter": adapter.creative_engine_payload(state, task),
        },
        allow_live=bool(task.get("allow_live_llm") or task.get("live_generation")),
    )
    return engine.generate(request)


def _fallback_script_scenes(scene_cards: List[Dict], characters: List[Dict], total_duration: float) -> List[Dict]:
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
            "generation_source": "fallback_scaffold",
        }
        scenes.append(scene)
        start = end
    if scenes:
        scenes[-1]["end_sec"] = total_duration
    return scenes


def _normalize_creative_script_scenes(scenes: List[Dict], total_duration: float, source: str) -> List[Dict]:
    normalized = []
    for index, scene in enumerate(scenes, start=1):
        item = dict(scene)
        item.setdefault("scene_no", index)
        item.setdefault("title", f"第{index}场")
        item.setdefault("location", "")
        item.setdefault("action", _action_from_visual(item.get("visual", "")))
        item.setdefault("subtitle", _subtitle_from_dialogue_or_voiceover(item.get("dialogue", []), item.get("voiceover", "")))
        item.setdefault("music_cue", "按场景情绪推进")
        item.setdefault("transition", "cut")
        item.setdefault("asset_goal", {"type": "adapted scene key frame"})
        item.setdefault("generation_source", source)
        normalized.append(item)
    if normalized:
        normalized[-1]["end_sec"] = total_duration
    return normalized


def _polish_script_draft(script: Dict, task: Dict) -> Dict:
    polished = copy_dict(script)
    intensity = str(task.get("polish_intensity", "medium")).strip().lower()
    style = task.get("polish_style") or polished.get("tone") or "短剧强冲突"
    constraints = list(polished.get("constraints") or [])
    constraints.extend(task.get("constraints") or [])
    adapter = _format_adapter_from_task(task, {"target": polished.get("target", "short_drama")})
    spec = adapter.spec()
    creative_engine_review = {}

    engine_result = _try_creative_polished_scenes(polished, task, adapter)
    if engine_result and engine_result.ok:
        scenes = _normalize_polished_creative_scenes(engine_result.data, polished, engine_result.generation_source)
        generation_source = engine_result.generation_source
        creative_engine_review = engine_result.review_report
    elif engine_result and _creative_engine_explicit(task) and engine_result.status != "fallback_required":
        raise ValueError("CreativeEngine script polish failed: " + "；".join(engine_result.errors or engine_result.warnings))
    else:
        scenes = []
        for index, scene in enumerate(polished.get("scenes") or [], start=1):
            upgraded = copy_dict(scene)
            original_dialogue = scene.get("dialogue") or []
            upgraded["original_dialogue"] = original_dialogue
            upgraded["polished_dialogue"] = _polish_dialogue_lines(
                original_dialogue,
                scene,
                index,
                len(polished.get("scenes") or []),
                intensity,
            )
            upgraded["dialogue"] = upgraded["polished_dialogue"]
            upgraded["voiceover"] = _polish_voiceover(scene.get("voiceover", ""), index, len(polished.get("scenes") or []))
            upgraded["subtitle"] = _subtitle_from_dialogue_or_voiceover(upgraded["polished_dialogue"], upgraded["voiceover"])
            upgraded["conflict_notes"] = _conflict_notes(scene, index, len(polished.get("scenes") or []), style)
            upgraded["beat_function"] = _beat_function(index, len(polished.get("scenes") or []))
            upgraded["generation_source"] = "fallback_polish_scaffold"
            scenes.append(upgraded)
        generation_source = "fallback_polish_scaffold"

    polished["scenes"] = scenes
    polished["generation_source"] = generation_source
    polished["creative_engine_review"] = creative_engine_review
    polished["format_adapter"] = polished.get("format_adapter") or spec.format_name
    polished["aspect_ratio"] = polished.get("aspect_ratio") or spec.default_aspect_ratio
    polished["rhythm_rules"] = polished.get("rhythm_rules") or spec.rhythm_rules
    polished["quality_checks"] = polished.get("quality_checks") or spec.quality_checks
    polished["quality_report"] = evaluate_script_quality(polished, spec, polished=True, context={"source_text": polished.get("source_text", task.get("source_text", "")), "characters": polished.get("characters", [])})
    polished["polish"] = {
        "style": style,
        "intensity": intensity,
        "generation_source": generation_source,
        "rules": [
            "对白短句化",
            "每场至少保留一个压力点或反问",
            "结尾保留悬念钩子",
            "不改变原脚本场次、时间线和资产目标",
        ],
    }
    polished["constraints"] = _dedupe_list(constraints)
    polished["handoff"] = copy_dict(polished.get("handoff") or {})
    polished["handoff"]["can_build_blueprint"] = True
    polished["handoff"]["polished_for_script"] = True
    polished["handoff"]["format_adapter"] = spec.format_name
    polished["handoff"]["copy_requirements"] = spec.handoff_requirements.get("copy", [])
    return polished


def _try_creative_polished_scenes(script: Dict, task: Dict, adapter):
    engine = _creative_engine_from_task(task)
    request = CreativeEngineRequest(
        kind="polished_script_scenes",
        source_text=script.get("source_text", task.get("source_text", "")),
        creative_brief={"tone": script.get("tone", ""), "target": script.get("target", "short_drama")},
        format_name=adapter.spec().format_name,
        schema_name="script_scenes",
        payload={
            "script": script,
            "adapter": adapter.creative_engine_payload({"title": script.get("title", "")}, task),
        },
        allow_live=bool(task.get("allow_live_llm") or task.get("live_generation")),
    )
    return engine.generate(request)


def _normalize_polished_creative_scenes(scenes: List[Dict], original_script: Dict, source: str) -> List[Dict]:
    original_scenes = original_script.get("scenes") or []
    normalized = []
    for index, scene in enumerate(scenes, start=1):
        original = original_scenes[index - 1] if index - 1 < len(original_scenes) else {}
        item = dict(scene)
        item.setdefault("scene_no", original.get("scene_no", index))
        item.setdefault("original_dialogue", original.get("dialogue", []))
        item.setdefault("polished_dialogue", item.get("dialogue", []))
        item.setdefault("dialogue", item.get("polished_dialogue", []))
        item.setdefault("subtitle", _subtitle_from_dialogue_or_voiceover(item.get("dialogue", []), item.get("voiceover", "")))
        item.setdefault("conflict_notes", ["CreativeEngine polish output; review before final production"])
        item.setdefault("beat_function", _beat_function(index, len(scenes)))
        item.setdefault("asset_goal", original.get("asset_goal", {}))
        item.setdefault("generation_source", source)
        normalized.append(item)
    return normalized


def _polish_dialogue_lines(dialogue: List[Dict], scene: Dict, index: int, total: int, intensity: str) -> List[Dict]:
    if not dialogue:
        dialogue = [{"speaker": "主角", "line": scene.get("voiceover", "继续。")}]
    polished = []
    for line_index, item in enumerate(dialogue):
        speaker = item.get("speaker", "角色")
        line = _tighten_line(item.get("line", ""))
        line = _add_pressure_if_needed(line, index, total, intensity, line_index)
        polished.append({"speaker": speaker, "line": line})

    if index == 1 and len(polished) == 1:
        polished.append({"speaker": "对手", "line": "你已经进来了。"})
    if index == total and not any("？" in item["line"] or "还没" in item["line"] for item in polished):
        polished.append({"speaker": polished[0]["speaker"], "line": "真正的客人，还没到。"})
    return polished[:3]


def _tighten_line(line: str) -> str:
    text = str(line or "").strip()
    replacements = {
        "一开始，": "",
        "无法解释的危机": "不该出现的东西",
        "现在才发现，已经晚了。": "晚了。",
        "你到底是谁？": "你不是普通人。",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.strip(" ，。；")
    if len(text) > 22:
        text = text[:22].rstrip("，。；、 ") + "。"
    if text and text[-1] not in "。！？":
        text += "。"
    return text or "继续。"


def _add_pressure_if_needed(line: str, index: int, total: int, intensity: str, line_index: int) -> str:
    if "？" in line or "!" in line or "！" in line:
        return line
    if intensity == "low":
        return line
    if "晚了" in line or "已经" in line:
        return line
    if index == 1 and line_index == 0 and len(line) <= 12:
        return line.rstrip("。") + "，你听见了吗？"
    if index == total and line_index == 0:
        return line.rstrip("。") + "，还没结束。"
    return line


def _polish_voiceover(voiceover: str, index: int, total: int) -> str:
    text = str(voiceover or "").strip()
    if index == 1 and "开场" not in text:
        text = "开场三秒，危机先到。 " + text
    if index == total and "真正" not in text and "还没有" not in text:
        text = text.rstrip("。") + "，真正的危机还没有露面。"
    return text


def _subtitle_from_dialogue_or_voiceover(dialogue: List[Dict], voiceover: str) -> str:
    if dialogue:
        return " / ".join(item.get("line", "") for item in dialogue[:2] if item.get("line"))
    return voiceover


def _conflict_notes(scene: Dict, index: int, total: int, style: str) -> List[str]:
    notes = []
    if index == 1:
        notes.append("开场先给危机，不先解释世界观")
    if scene.get("dialogue"):
        notes.append("对白保持短句，优先制造压力和反问")
    if "规则" in scene.get("voiceover", "") or "改变" in scene.get("voiceover", ""):
        notes.append("强化主角掌控规则的反转感")
    if index == total:
        notes.append("结尾留未解悬念，驱动下一集")
    notes.append(f"风格基准：{style}")
    return notes


def _beat_function(index: int, total: int) -> str:
    if index == 1:
        return "hook"
    if index == total:
        return "cliffhanger"
    if index >= max(total - 1, 1):
        return "reversal"
    return "escalation"


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
        "后续所有资产保持同一五官比例、脸型、眉型、眼型、鼻型、口型、发型轮廓和服装身份",
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

    candidates.extend(_extract_cast_line_characters(text))
    candidates.extend(_extract_dialogue_speakers(text))

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
        "指尖",
        "脑袋",
        "太阳穴",
        "眼睛",
        "目光",
        "然后",
        "窗外",
        "桌上",
        "屏幕",
    }
    if name in blocked_exact:
        return False
    blocked_parts = (
        "手里",
        "柜台",
        "背包",
        "菜单",
        "账本",
        "探测",
        "异常",
        "能量",
        "指尖",
        "脑袋",
        "太阳穴",
        "目光",
    )
    return not any(part in name for part in blocked_parts)


def _extract_cast_line_characters(text: str) -> List[str]:
    names: List[str] = []
    for line in str(text or "").splitlines():
        line = line.strip()
        if not line.startswith("出场人物"):
            continue
        _, _, tail = line.partition("：")
        if not tail:
            _, _, tail = line.partition(":")
        for item in re.split(r"[、,，/／\s]+", tail):
            cleaned = _clean_speaker_name(item)
            if cleaned:
                names.append(cleaned)
    return names


def _extract_dialogue_speakers(text: str) -> List[str]:
    names: List[str] = []
    for line in str(text or "").splitlines():
        line = line.strip()
        match = re.match(r"^([\u4e00-\u9fffA-Za-z0-9_]{1,12})(?:（[^）]*）|\([^)]*\)|VO|OS)?[：:]", line)
        if not match:
            continue
        cleaned = _clean_speaker_name(match.group(1))
        if cleaned:
            names.append(cleaned)
    return names


def _clean_speaker_name(value: str) -> str:
    text = str(value or "").strip(" \t，。！？,.!?:;；")
    text = re.sub(r"(?:VO|OS)$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"[（(].*?[）)]", "", text).strip()
    blocked = {"闪回", "闪出", "特写", "屏幕", "旁白", "内心", "场", "第一集", "出场人物"}
    if text in blocked:
        return ""
    return text


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
    script_headers = _extract_script_scene_headers(text)
    if script_headers:
        return _dedupe_list(script_headers)
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


def _extract_script_scene_headers(text: str) -> List[str]:
    scenes: List[str] = []
    for line in str(text or "").splitlines():
        line = line.strip()
        if re.match(r"^场\s*\d+(?:[-－]\d+)?\s+", line):
            scenes.append(line)
    return scenes


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
