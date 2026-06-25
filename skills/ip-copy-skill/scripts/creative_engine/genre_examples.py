import json
from pathlib import Path
from typing import Any, Dict, List


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
    if pack.get("version") != GENRE_EXAMPLE_PACK_VERSION:
        errors.append(f"version must be {GENRE_EXAMPLE_PACK_VERSION}")
    if not _is_non_empty_string(pack.get("pack_id")):
        errors.append("pack_id must be a non-empty string")
    if not _is_non_empty_list(pack.get("applies_to")):
        errors.append("applies_to must be a non-empty list")
    for field in [
        "source_priority_rules",
        "genre_boundary",
        "scene_card_examples",
        "script_scene_examples",
        "dialogue_style_examples",
        "negative_examples",
        "forbidden_drift",
    ]:
        if field in pack and not _is_non_empty_list(pack.get(field)):
            errors.append(f"{field} must be a non-empty list")
    handoff_notes = pack.get("handoff_notes")
    if "handoff_notes" in pack and not isinstance(handoff_notes, dict):
        errors.append("handoff_notes must be an object")
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


def _safe_source_path(path: Path) -> str:
    try:
        return path.relative_to(_SKILL_DIR).as_posix()
    except ValueError:
        return path.name


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)