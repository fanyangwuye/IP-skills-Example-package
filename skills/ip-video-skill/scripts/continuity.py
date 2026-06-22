import re
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
            "hair_lock": appearance.get("hair", "保持同一发型轮廓和发色"),
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
            "weather_atmosphere_lock": _infer_atmosphere(scene.get("description") or scene.get("lighting") or ""),
            "palette_lock": _infer_palette(scene.get("description") or scene.get("lighting") or ""),
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
    return {
        "style_preset": task.get("style_preset") or ip_asset_pack.get("style_preset") or "realistic_short_drama",
        "tone_lock": tone,
        "lens_language": task.get("lens_language", "短剧镜头语言，动作清楚，表演可读，避免过度炫技"),
        "color_grade": task.get("color_grade") or _infer_palette(str(tone)),
        "lighting_policy": "保持同一场景内光源方向、冷暖和对比度连续。",
        "forbidden_drift": [
            "no face drift",
            "no hairstyle drift",
            "no costume color change",
            "no scene layout reset",
            "no lighting direction flip",
            "no cross-axis cut without transition",
        ],
    }


def find_character_ids_in_text(text: str, character_locks: Dict) -> List[str]:
    found = []
    for char_id, lock in character_locks.items():
        name = str(lock.get("name") or "")
        role = str(lock.get("role") or "")
        if name and name in text:
            found.append(char_id)
        elif role and role in text:
            found.append(char_id)
    if found:
        return _dedupe(found)
    all_ids = list(character_locks.keys())
    return all_ids[: min(2, len(all_ids))]


def choose_scene_id(text: str, scene_locks: Dict) -> Optional[str]:
    for scene_id, lock in scene_locks.items():
        haystack = " ".join([str(lock.get("name", "")), str(lock.get("layout_lock", ""))])
        if any(token and token in text for token in _scene_tokens(haystack)):
            return scene_id
    return next(iter(scene_locks.keys()), None) if scene_locks else None


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
    if any(word in text for word in ["雾", "黑", "地府", "黄泉"]):
        return "黑雾、低饱和、诡异压迫"
    return "与上游场景描述一致"


def _infer_palette(text: str) -> str:
    if any(word in text for word in ["红", "地府", "黄泉"]):
        return "冷暗基调加克制红色幽光"
    if any(word in text for word in ["雨", "霓虹", "夜"]):
        return "冷蓝雨夜与少量霓虹暖色"
    return "自然电影色调，低漂移"


def _scene_tokens(text: str) -> List[str]:
    return [item for item in re.split(r"[\s,，。/、]+", text) if len(item) >= 2][:12]


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
