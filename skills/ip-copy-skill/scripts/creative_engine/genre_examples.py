import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


GENRE_EXAMPLE_PACK_VERSION = "copy-genre-example-pack-v1"

_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _SCRIPT_DIR.parents[1]
GENRE_EXAMPLES_DIR = _SKILL_DIR / "references" / "genre_examples"

_REQUIRED_FIELDS = [
    "pack_id",
    "version",
    "display_name",
    "applies_to",
    "purpose",
    "source_priority_rules",
    "genre_boundary",
    "scene_card_examples",
    "script_scene_examples",
    "dialogue_style_examples",
    "negative_examples",
    "forbidden_drift",
    "handoff_notes",
]

_SCENE_CARD_REQUIRED_FIELDS = ["visual", "voiceover", "duration_sec", "emotional_turn", "asset_goal"]
_SCRIPT_SCENE_REQUIRED_FIELDS = ["visual", "voiceover", "dialogue", "action_result"]
_NEGATIVE_EXAMPLE_REQUIRED_FIELDS = ["bad", "why_bad"]
_HANDOFF_REQUIRED_KEYS = ["image", "video"]

_FORBIDDEN_DRIFT_CATEGORIES = {
    "character_or_role": ["character", "角色", "speaker", "role", "identity", "lead", "host", "suspect", "companion", "worker", "official", "monster"],
    "props_or_objects": ["prop", "object", "artifact", "weapon", "inventory", "tool", "clue", "resource", "menu", "ledger", "道具", "物件"],
    "space_or_blocking": ["space", "location", "room", "route", "door", "threshold", "scene", "spatial", "blocking", "position", "场景", "空间", "路线"],
    "relationship_or_state": ["relationship", "status", "ownership", "knowledge state", "public", "private", "alliance", "pov", "choice", "state", "关系", "身份", "地位", "视角"],
    "causality_or_source": ["cause", "effect", "causal", "source", "unsupported", "setup", "transition", "without explanation", "without source", "source-grounded", "因果", "依据"],
}

_IMAGE_HANDOFF_HINTS = ["anchor", "anchors", "identity", "layout", "wardrobe", "prop", "motif", "lock", "reference", "锚点", "构图"]
_VIDEO_HANDOFF_HINTS = ["continuity", "bridge", "transition", "state", "blocking", "connect", "match", "later", "衔接", "连续", "状态", "转场"]

_UNSAFE_TEXT_MARKERS = {
    "local_path_windows": ["c:\\", "d:\\", "e:\\", "\\users\\", "\\downloads\\"],
    "local_path_posix": ["/users/", "/home/", "file://"],
    "url": ["http://", "https://", "www."],
    "secret": ["sk-", "api_key", "apikey", "bearer ", "authorization:"],
    "realworld_ip_or_person": ["harry potter", "spider-man", "batman", "superman", "marvel", "dc comics", "star wars", "disney", "taylor swift", "elon musk"],
}


def load_genre_example_pack(primary_genre: str, examples_dir: Path | None = None) -> Dict[str, Any]:
    genre = (primary_genre or "general_short_drama").strip() or "general_short_drama"
    base_dir = examples_dir or GENRE_EXAMPLES_DIR
    selected_path = base_dir / f"{genre}.json"
    fallback_used = False
    if not selected_path.exists():
        selected_path = base_dir / "general_short_drama.json"
        fallback_used = True
    pack = _load_json(selected_path)
    errors = validate_genre_example_pack(pack)
    if errors:
        raise ValueError(f"Invalid genre example pack {selected_path}: {'; '.join(errors)}")
    return _compact_pack(pack, selected_path, requested_genre=genre, fallback_used=fallback_used)


def validate_genre_example_pack(pack: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(pack, dict):
        return ["pack must be a JSON object"]
    for field in _REQUIRED_FIELDS:
        if field not in pack:
            errors.append(f"missing required field: {field}")
    if errors:
        return errors
    if pack.get("version") != GENRE_EXAMPLE_PACK_VERSION:
        errors.append(f"version must be {GENRE_EXAMPLE_PACK_VERSION}")
    if not _is_non_empty_string(pack.get("pack_id")):
        errors.append("pack_id must be a non-empty string")
    if not _is_non_empty_string(pack.get("display_name")):
        errors.append("display_name must be a non-empty string")
    if not _is_non_empty_string(pack.get("purpose")):
        errors.append("purpose must be a non-empty string")
    if not _is_non_empty_list(pack.get("applies_to")):
        errors.append("applies_to must be a non-empty list")
    elif not _all_non_empty_strings(pack.get("applies_to")):
        errors.append("applies_to entries must be non-empty strings")

    for field in ["source_priority_rules", "genre_boundary", "dialogue_style_examples", "forbidden_drift"]:
        if not _is_non_empty_list(pack.get(field)):
            errors.append(f"{field} must be a non-empty list")
        elif not _all_non_empty_strings(pack.get(field)):
            errors.append(f"{field} entries must be non-empty strings")

    errors.extend(_validate_scene_card_examples(pack.get("scene_card_examples")))
    errors.extend(_validate_script_scene_examples(pack.get("script_scene_examples")))
    errors.extend(_validate_negative_examples(pack.get("negative_examples")))
    errors.extend(_validate_handoff_notes(pack.get("handoff_notes")))
    errors.extend(_validate_forbidden_drift_coverage(pack.get("forbidden_drift")))
    errors.extend(_validate_text_boundaries(pack))
    return errors


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"genre example pack not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"genre example pack must be an object: {path}")
    return data


def _compact_pack(pack: Dict[str, Any], path: Path, requested_genre: str, fallback_used: bool) -> Dict[str, Any]:
    return {
        "pack_id": pack["pack_id"],
        "version": pack["version"],
        "display_name": pack.get("display_name", ""),
        "applies_to": pack.get("applies_to", []),
        "requested_genre": requested_genre,
        "fallback_used": fallback_used,
        "source_path": _safe_source_path(path),
        "purpose": pack.get("purpose", ""),
        "source_priority_rules": pack.get("source_priority_rules", []),
        "genre_boundary": pack.get("genre_boundary", []),
        "scene_card_examples": pack.get("scene_card_examples", [])[:2],
        "script_scene_examples": pack.get("script_scene_examples", [])[:2],
        "dialogue_style_examples": pack.get("dialogue_style_examples", [])[:4],
        "negative_examples": pack.get("negative_examples", [])[:3],
        "forbidden_drift": pack.get("forbidden_drift", [])[:8],
        "handoff_notes": pack.get("handoff_notes", {}),
        "example_policy": "Craft examples only; source_text and locked payload remain authoritative.",
    }


def _validate_scene_card_examples(value: Any) -> List[str]:
    errors: List[str] = []
    if not _is_non_empty_list(value):
        return ["scene_card_examples must be a non-empty list"]
    for index, item in enumerate(value):
        prefix = f"scene_card_examples[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in _SCENE_CARD_REQUIRED_FIELDS:
            if field not in item:
                errors.append(f"{prefix} missing required field: {field}")
        for field in ["visual", "voiceover", "emotional_turn"]:
            if field in item and not _is_non_empty_string(item.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        if "duration_sec" in item and not _is_positive_number(item.get("duration_sec")):
            errors.append(f"{prefix}.duration_sec must be a positive number")
        asset_goal = item.get("asset_goal")
        if "asset_goal" in item and not isinstance(asset_goal, dict):
            errors.append(f"{prefix}.asset_goal must be an object")
        elif isinstance(asset_goal, dict) and not _is_non_empty_string(asset_goal.get("type")):
            errors.append(f"{prefix}.asset_goal.type must be a non-empty string")
    return errors


def _validate_script_scene_examples(value: Any) -> List[str]:
    errors: List[str] = []
    if not _is_non_empty_list(value):
        return ["script_scene_examples must be a non-empty list"]
    for index, item in enumerate(value):
        prefix = f"script_scene_examples[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in _SCRIPT_SCENE_REQUIRED_FIELDS:
            if field not in item:
                errors.append(f"{prefix} missing required field: {field}")
        for field in ["visual", "voiceover", "action_result"]:
            if field in item and not _is_non_empty_string(item.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        dialogue = item.get("dialogue")
        if "dialogue" in item and not _is_non_empty_list(dialogue):
            errors.append(f"{prefix}.dialogue must be a non-empty list")
        elif isinstance(dialogue, list):
            for line_index, line in enumerate(dialogue):
                line_prefix = f"{prefix}.dialogue[{line_index}]"
                if not isinstance(line, dict):
                    errors.append(f"{line_prefix} must be an object")
                    continue
                if not _is_non_empty_string(line.get("speaker")):
                    errors.append(f"{line_prefix}.speaker must be a non-empty string")
                if not _is_non_empty_string(line.get("line")):
                    errors.append(f"{line_prefix}.line must be a non-empty string")
    return errors


def _validate_negative_examples(value: Any) -> List[str]:
    errors: List[str] = []
    if not _is_non_empty_list(value):
        return ["negative_examples must be a non-empty list"]
    for index, item in enumerate(value):
        prefix = f"negative_examples[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in _NEGATIVE_EXAMPLE_REQUIRED_FIELDS:
            if field not in item:
                errors.append(f"{prefix} missing required field: {field}")
            elif not _is_non_empty_string(item.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
    return errors


def _validate_handoff_notes(value: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(value, dict):
        return ["handoff_notes must be an object"]
    for key in _HANDOFF_REQUIRED_KEYS:
        entries = value.get(key)
        if not _is_non_empty_list(entries):
            errors.append(f"handoff_notes.{key} must be a non-empty list")
        elif not _all_non_empty_strings(entries):
            errors.append(f"handoff_notes.{key} entries must be non-empty strings")
    if isinstance(value.get("image"), list) and not _contains_any_marker(value.get("image", []), _IMAGE_HANDOFF_HINTS):
        errors.append("handoff_notes.image must mention an image anchor, identity lock, layout, prop, motif, or equivalent reference cue")
    if isinstance(value.get("video"), list) and not _contains_any_marker(value.get("video", []), _VIDEO_HANDOFF_HINTS):
        errors.append("handoff_notes.video must mention continuity, bridge, transition, state, blocking, or equivalent motion continuity cue")
    return errors


def _validate_forbidden_drift_coverage(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    text = "\n".join(str(item).lower() for item in value)
    errors: List[str] = []
    for category, markers in _FORBIDDEN_DRIFT_CATEGORIES.items():
        if not any(marker in text for marker in markers):
            errors.append(f"forbidden_drift must cover {category}")
    return errors


def _validate_text_boundaries(pack: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for path, text in _iter_string_fields(pack):
        lowered = text.lower()
        for category, markers in _UNSAFE_TEXT_MARKERS.items():
            for marker in markers:
                if marker in lowered:
                    errors.append(f"{path} contains disallowed {category} marker: {marker}")
                    break
    return errors


def _iter_string_fields(value: Any, path: str = "pack") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_string_fields(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_string_fields(item, f"{path}.{key}")


def _contains_any_marker(items: List[str], markers: List[str]) -> bool:
    text = "\n".join(items).lower()
    return any(marker in text for marker in markers)


def _safe_source_path(path: Path) -> str:
    try:
        return path.relative_to(_SKILL_DIR).as_posix()
    except ValueError:
        return path.name


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _all_non_empty_strings(items: List[Any]) -> bool:
    return all(_is_non_empty_string(item) for item in items)


def _is_positive_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float)) and value > 0