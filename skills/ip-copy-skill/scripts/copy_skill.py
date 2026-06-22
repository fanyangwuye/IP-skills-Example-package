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
    if mode == "build_ip_asset_pack":
        return _run_build_ip_asset_pack(task, output_dir)
    if mode == "build_character_handoff":
        return _run_build_character_handoff(task, output_dir)
    if mode == "build_blueprint":
        return _run_build_blueprint(task, output_dir)
    raise ValueError("mode must be one of: check_license, build_blueprint, build_character_handoff, build_ip_asset_pack")


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
        r"(?<![\u4e00-\u9fff])([\u4e00-\u9fff]{2,3})(?=(?:在|走|看|说|拿|拿着|背着|端着|站|坐|冲|推|递|握|发现|进入|离开|来到|回到|盯着|望向))",
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
    for key, role in role_hints.items():
        if key in context:
            return role
    if "探测器" in context or "异常能量" in context:
        return "调查者 / 异常能量探测者"
    if "背包" in context or "基地" in context:
        return "行动小队成员 / 生存者"
    return "重要角色 / 待细化"


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
