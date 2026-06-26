import re
import json
import os
from typing import Dict, Iterable, List, Optional


def build_continuity_bible(task: Dict) -> Dict:
    """Build a provider-neutral continuity bible from available upstream handoffs."""
    if task.get("continuity_bible"):
        return task["continuity_bible"]

    ip_asset_pack = task.get("ip_asset_pack") or {}
    image_handoff = task.get("image_handoff") or {}
    blueprint = task.get("blueprint") or {}
    polished_script = task.get("polished_script") or task.get("script_draft") or {}

    title = (
        task.get("title")
        or ip_asset_pack.get("title")
        or blueprint.get("title")
        or polished_script.get("title")
        or "untitled_ip_video"
    )

    character_locks = _build_character_locks(ip_asset_pack, image_handoff)
    scene_locks = _build_scene_locks(ip_asset_pack, image_handoff, blueprint, polished_script)
    style_lock = _build_style_lock(task, ip_asset_pack, blueprint, polished_script)

    return {
        "bible_id": task.get("bible_id") or f"{_safe_id(title)}_continuity_bible",
        "source_title": title,
        "global_visual_lock": style_lock,
        "character_locks": character_locks,
        "scene_locks": scene_locks,
        "reference_policy": {
            "character_reference_rule": "角色参考只锁脸、发型、年龄感、体型气质；不复制背景和无关姿势。",
            "costume_reference_rule": "服装锁款式、材质、颜色和状态；不让服装图人物脸污染角色脸。",
            "scene_reference_rule": "场景锁空间布局、地标、光线方向和色调；不复制无关路人和文字标识。",
            "style_reference_rule": "风格只锁镜头感、色调、颗粒、对比度；不复制具体人物或物件。",
        },
        "continuity_rules": [
            "每镜起始态必须继承上一镜结束态。",
            "角色脸、发型、年龄感、体型气质、服饰状态不得跨镜漂移。",
            "道具必须保持所在手、材质、状态和出现逻辑。",
            "场景布局、主要地标、天气和光源方向必须连续。",
            "多角色镜头必须锁定轴线、屏幕方向、视线和距离。",
        ],
    }


def _build_character_locks(ip_asset_pack: Dict, image_handoff: Dict) -> Dict:
    locks: Dict[str, Dict] = {}
    for index, character in enumerate(ip_asset_pack.get("characters") or [], start=1):
        profile = character.get("character_profile") or {}
        identity = profile.get("identity") or {}
        appearance = profile.get("appearance") or {}
        styling = profile.get("styling") or {}
        personality = profile.get("personality") or {}
        char_id = character.get("character_id") or _safe_id(identity.get("name") or f"character_{index}")
        props = _normalize_props(character.get("props") or [])
        locks[char_id] = {
            "lock_id": f"char_lock_{char_id}",
            "name": identity.get("name") or char_id,
            "role": identity.get("role", ""),
            "face_lock": _join_parts(
                appearance.get("ethnicity"),
                appearance.get("face_shape"),
                appearance.get("eyes"),
                identity.get("age_range"),
                identity.get("gender_presentation"),
            ),
            "hair_lock": styling.get("hair") or appearance.get("hair") or "保持同一发型轮廓和发色",
            "body_temperament_lock": _join_parts(appearance.get("body_type"), personality.get("temperament"), personality.get("aura")),
            "costume_lock": _join_parts(styling.get("wardrobe"), styling.get("materials")),
            "palette_lock": styling.get("palette", ""),
            "prop_locks": props,
            "identity_anchors": list(character.get("identity_anchors") or []),
            "continuity_rules": list(character.get("continuity_rules") or []),
            "reference_binding": {
                "face": f"{char_id}:face",
                "costume": f"{char_id}:costume",
                "props": [prop["prop_id"] for prop in props],
            },
        }

    for task in image_handoff.get("image_tasks") or []:
        profile = task.get("character_profile") or {}
        identity = profile.get("identity") or {}
        if not identity.get("name"):
            continue
        char_id = _safe_id(identity.get("name"))
        locks.setdefault(
            char_id,
            {
                "lock_id": f"char_lock_{char_id}",
                "name": identity.get("name"),
                "role": identity.get("role", ""),
                "face_lock": "来自 image_handoff 的角色图，锁脸、发型、年龄感和体型气质",
                "hair_lock": "来自 image_handoff 的同一发型",
                "body_temperament_lock": "来自 image_handoff 的体型气质",
                "costume_lock": "来自 image_handoff 的服装身份",
                "palette_lock": "",
                "prop_locks": _normalize_props(task.get("props") or []),
                "identity_anchors": list(task.get("identity_anchors") or []),
                "continuity_rules": list(task.get("continuity_rules") or []),
                "reference_binding": {
                    "face": f"{char_id}:face",
                    "costume": f"{char_id}:costume",
                    "props": [],
                },
            },
        )

    if not locks:
        locks["main_character"] = {
            "lock_id": "char_lock_main_character",
            "name": "主角",
            "role": "主要角色",
            "face_lock": "保持同一人物脸型、五官、年龄感和表演气质",
            "hair_lock": "保持同一发型和发色",
            "body_temperament_lock": "保持同一体型与气质",
            "costume_lock": "保持同一服饰款式、材质、颜色和状态",
            "palette_lock": "",
            "prop_locks": [],
            "identity_anchors": ["same identity across all shots"],
            "continuity_rules": ["do not mix with other characters"],
            "reference_binding": {"face": "main_character:face", "costume": "main_character:costume", "props": []},
        }
    return locks


def _build_scene_locks(ip_asset_pack: Dict, image_handoff: Dict, blueprint: Dict, polished_script: Dict) -> Dict:
    locks: Dict[str, Dict] = {}
    for index, scene in enumerate(ip_asset_pack.get("scenes") or [], start=1):
        scene_id = scene.get("scene_id") or _safe_id(scene.get("name") or f"scene_{index}")
        locks[scene_id] = {
            "lock_id": f"scene_lock_{scene_id}",
            "name": scene.get("name") or scene_id,
            "layout_lock": scene.get("description") or scene.get("name") or "",
            "landmark_lock": _infer_landmarks(scene.get("description") or scene.get("name") or ""),
            "lighting_lock": scene.get("lighting", ""),
            "weather_atmosphere_lock": scene.get("atmosphere") or scene.get("weather") or _infer_atmosphere(scene.get("description") or scene.get("lighting") or ""),
            "palette_lock": scene.get("palette") or _infer_palette(scene.get("description") or scene.get("lighting") or ""),
            "panorama_rule": "如果使用全景参考，左右边缘必须无缝衔接，不出现明显接缝。",
            "reference_binding": {"scene": f"{scene_id}:scene", "style": "global:style"},
        }

    for task in image_handoff.get("image_tasks") or []:
        scene_text = task.get("scene") or task.get("prompt") or ""
        if not scene_text:
            continue
        scene_id = _safe_id(task.get("asset_kind") or task.get("filename") or scene_text[:24])
        locks.setdefault(
            scene_id,
            {
                "lock_id": f"scene_lock_{scene_id}",
                "name": task.get("asset_kind") or scene_id,
                "layout_lock": scene_text,
                "landmark_lock": _infer_landmarks(scene_text),
                "lighting_lock": task.get("lighting", ""),
                "weather_atmosphere_lock": _infer_atmosphere(scene_text),
                "palette_lock": _infer_palette(scene_text),
                "panorama_rule": "",
                "reference_binding": {"scene": f"{scene_id}:scene", "style": "global:style"},
            },
        )

    if not locks:
        for index, item in enumerate(_iter_source_segments(blueprint, polished_script), start=1):
            visual = item.get("visual") or item.get("scene") or item.get("location") or f"scene_{index}"
            scene_id = f"scene_{index:02d}"
            locks[scene_id] = {
                "lock_id": f"scene_lock_{scene_id}",
                "name": item.get("location") or f"场景{index}",
                "layout_lock": visual,
                "landmark_lock": _infer_landmarks(visual),
                "lighting_lock": _infer_lighting(visual),
                "weather_atmosphere_lock": _infer_atmosphere(visual),
                "palette_lock": _infer_palette(visual),
                "panorama_rule": "",
                "reference_binding": {"scene": f"{scene_id}:scene", "style": "global:style"},
            }
    return locks


def _build_style_lock(task: Dict, ip_asset_pack: Dict, blueprint: Dict, polished_script: Dict) -> Dict:
    direction = task.get("creative_direction") or ip_asset_pack.get("creative_direction") or blueprint.get("global_style") or {}
    tone = direction.get("tone") or polished_script.get("tone") or task.get("tone") or "cinematic IP adaptation"
    style_preset = task.get("style_preset") or ip_asset_pack.get("style_preset") or "realistic_short_drama"
    style_card = _load_video_style_card(task.get("style_card_path"), style_preset)

    # 加载视频风格预设（如果指定），合并到 style_card（视频预设优先级更高）
    video_preset_name = task.get("video_style_preset") or ""
    video_preset = _load_video_style_preset(video_preset_name) if video_preset_name else {}
    if video_preset:
        style_card = _merge_style_card_dicts(style_card, video_preset)

    forbidden = [
        "no face drift",
        "no hairstyle drift",
        "no costume color change",
        "no scene layout reset",
        "no lighting direction flip",
        "no cross-axis cut without transition",
    ]
    forbidden.extend(style_card.get("forbidden_elements") or [])
    forbidden.extend(style_card.get("negative_prompt_fragments") or [])

    result = {
        "style_preset": style_preset,
        "video_style_preset": video_preset_name,
        "style_card_source": style_card.get("_source", ""),
        "style_direction": style_card.get("style_direction", ""),
        "style_positive_fragments": list(style_card.get("positive_prompt_fragments") or [])[:8],
        "style_realism_constraints": list(style_card.get("realism_constraints") or [])[:8],
        "tone_lock": tone,
        "lens_language": task.get("lens_language") or style_card.get("camera_language", {}).get("movement_preference", "") or "短剧镜头语言，动作清楚，表演可读，避免过度炫技",
        "color_grade": task.get("color_grade") or style_card.get("primary_palette") or _infer_palette(str(tone)),
        "lighting_policy": style_card.get("lighting_policy") or "保持同一场景内光源方向、冷暖和对比度连续。",
        "forbidden_drift": _dedupe(forbidden),
    }

    # 注入视频专用字段（来自视频风格预设）
    if video_preset:
        result["camera_language"] = video_preset.get("camera_language", {})
        result["rhythm"] = video_preset.get("rhythm", {})
        result["prompt_rules"] = video_preset.get("prompt_rules", {})
        result["pipeline_config"] = video_preset.get("pipeline_config", {})
        result["audio_direction"] = video_preset.get("audio_direction", {})

    return result


def _load_video_style_card(style_card_path: Optional[str], style_preset: str) -> Dict:
    paths = []
    if style_preset:
        paths.append(_image_style_preset_path(style_preset))
    if style_card_path:
        paths.append(style_card_path)
    merged: Dict = {}
    sources = []
    for path in paths:
        if not path or not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            card = json.load(fh)
        merged = _merge_style_card_dicts(merged, card)
        sources.append(path)
    if sources:
        merged["_source"] = ";".join(sources)
    return merged


def _image_style_preset_path(style_preset: str) -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(project_root, "skills", "ip-image-skill", "references", "style_presets", f"{style_preset}.json")


def _video_style_preset_path(video_style_preset: str) -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "video_style_presets", f"{video_style_preset}.json")


def _load_video_style_preset(video_style_preset: str) -> Dict:
    path = _video_style_preset_path(video_style_preset)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        preset = json.load(fh)
    # 如果有 linked_image_preset，加载并合并（视频预设优先级更高）
    linked = preset.pop("linked_image_preset", None)
    if linked:
        image_card = _load_video_style_card(None, linked)
        # 视频预设字段覆盖图片预设同名字段
        preset = _merge_style_card_dicts(image_card, preset)
    return preset


def _merge_style_card_dicts(base: Dict, override: Dict) -> Dict:
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, list):
            existing = merged.get(key)
            if not isinstance(existing, list):
                existing = []
            merged[key] = existing + [item for item in value if item not in existing]
        elif isinstance(value, dict):
            existing = merged.get(key)
            merged[key] = _merge_style_card_dicts(existing if isinstance(existing, dict) else {}, value)
        elif value not in (None, ""):
            merged[key] = value
    return merged
def find_character_ids_in_text(text: str, character_locks: Dict) -> List[str]:
    text = str(text or "")
    scored: List[tuple] = []
    for order, (char_id, lock) in enumerate(character_locks.items()):
        aliases = _character_aliases(char_id, lock)
        score = 0
        for alias in aliases:
            if alias and alias in text:
                score += 4 if len(alias) >= 2 else 1
        for prop in lock.get("prop_locks") or []:
            prop_name = str(prop.get("name") or prop.get("prop_id") or "").strip()
            if prop_name and prop_name in text:
                score += 2
        if score > 0:
            scored.append((score, order, char_id))
    if scored:
        scored.sort(key=lambda item: (-item[0], item[1]))
        return _dedupe([char_id for _, _, char_id in scored])[:2]
    all_ids = list(character_locks.keys())
    return all_ids[: min(2, len(all_ids))]


def choose_scene_id(text: str, scene_locks: Dict) -> Optional[str]:
    text = str(text or "")
    best_id = None
    best_score = 0
    for order, (scene_id, lock) in enumerate(scene_locks.items()):
        score = _scene_match_score(text, scene_id, lock)
        if score > best_score:
            best_score = score
            best_id = scene_id
    return best_id or (next(iter(scene_locks.keys()), None) if scene_locks else None)


def _iter_source_segments(blueprint: Dict, polished_script: Dict) -> Iterable[Dict]:
    if blueprint.get("segments"):
        return blueprint["segments"]
    return polished_script.get("scenes") or []


def _normalize_props(props: List) -> List[Dict]:
    normalized = []
    for index, prop in enumerate(props, start=1):
        if isinstance(prop, dict):
            name = prop.get("name") or prop.get("prop_id") or f"prop_{index}"
            use = prop.get("use") or prop.get("purpose") or ""
        else:
            name = str(prop)
            use = ""
        normalized.append({"prop_id": _safe_id(name), "name": name, "state_lock": use or "保持同一道具形状、材质和状态"})
    return normalized


def _infer_landmarks(text: str) -> List[str]:
    keywords = ["门口", "柜台", "桌", "椅", "窗", "走廊", "厨房", "大厅", "街道", "霓虹", "石柱", "锁链", "道路"]
    return [word for word in keywords if word in text] or ["主要空间地标保持一致"]


def _infer_lighting(text: str) -> str:
    if any(word in text for word in ["夜", "雨", "暗", "黑", "霓虹"]):
        return "低照度电影光，保持冷暖关系和光源方向"
    return "电影化自然光或室内实用光，保持光源方向连续"


def _infer_atmosphere(text: str) -> str:
    if "雨" in text:
        return "雨水、湿地反光、空气潮湿"
    if any(word in text for word in ["云雾", "云海", "仙鹤", "修仙", "仙侠", "宗门"]):
        return "云海、山风、轻雾、仙侠日外空气感"
    if "烟尘" in text or "战后" in text:
        return "战后烟尘、低空尘粒、受损宗门压迫感"
    if any(word in text for word in ["黑", "地府", "黄泉"]):
        return "黑雾、低饱和、诡异压迫"
    if "雾" in text:
        return "轻雾、空气颗粒、低饱和环境氛围"
    return "与上游场景描述一致"


def _infer_palette(text: str) -> str:
    if any(word in text for word in ["红", "地府", "黄泉"]):
        return "冷暗基调加克制红色幽光"
    if any(word in text for word in ["云海", "云雾", "修仙", "仙侠", "宗门", "石阶"]):
        return "冷白天光、淡金侧逆光、云雾蓝灰、低饱和仙侠写实色调"
    if any(word in text for word in ["雨", "霓虹", "夜"]):
        return "冷蓝雨夜与少量霓虹暖色"
    return "自然电影色调，低漂移"


def _character_aliases(char_id: str, lock: Dict) -> List[str]:
    aliases = [str(char_id or "")]
    for key in ("name", "role"):
        value = str(lock.get(key) or "").strip()
        if value:
            aliases.append(value)
            aliases.extend(_role_aliases(value))
    aliases.extend(str(item).strip() for item in lock.get("identity_anchors") or [] if str(item).strip())
    aliases.extend(_name_short_aliases(str(lock.get("name") or "")))
    return _dedupe([alias for alias in aliases if alias])


def _role_aliases(value: str) -> List[str]:
    known = [
        "老板", "员工", "侍者", "服务员", "调查者", "主角", "男主", "女主", "师尊", "师父", "徒弟",
        "剑客", "宗主", "长老", "弟子", "反派", "对手", "客人", "巡捕", "系统",
    ]
    return [item for item in known if item in value]


def _name_short_aliases(name: str) -> List[str]:
    if not name or len(name) < 2:
        return []
    aliases = []
    if len(name) == 2:
        aliases.append(name[0])
    if len(name) >= 3:
        aliases.append(name[-2:])
    return aliases


def _scene_match_score(text: str, scene_id: str, lock: Dict) -> int:
    score = 0
    name = str(lock.get("name") or "")
    layout = str(lock.get("layout_lock") or "")
    if name and name in text:
        score += 8
    if scene_id and str(scene_id) in text:
        score += 6
    for token in _scene_tokens(" ".join([name, layout])):
        if token in text:
            score += 3 if len(token) >= 4 else 1
    for landmark in lock.get("landmark_lock") or []:
        landmark = str(landmark or "")
        if landmark and landmark in text:
            score += 2
    return score


def _scene_tokens(text: str) -> List[str]:
    weak = {"场", "景", "夜", "日", "内", "外", "场景", "环境", "参考", "夜内", "夜外", "日内", "日外"}
    tokens = []
    for item in re.split(r"[\s,，。/、:：;；()（）\-－]+", str(text or "")):
        item = item.strip()
        if len(item) < 2 or item in weak or item.isdigit():
            continue
        tokens.append(item)
    return _dedupe(tokens)[:16]


def _join_parts(*parts: Optional[str]) -> str:
    return "；".join(str(part).strip() for part in parts if part)


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _safe_id(value: Optional[str]) -> str:
    text = str(value or "item").strip().lower()
    keep = []
    for char in text:
        if char.isalnum():
            keep.append(char)
        elif char in (" ", "-", "_"):
            keep.append("_")
    label = "".join(keep).strip("_")
    while "__" in label:
        label = label.replace("__", "_")
    return (label or "item")[:64]
