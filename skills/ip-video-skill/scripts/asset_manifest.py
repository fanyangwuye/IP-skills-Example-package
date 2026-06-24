import json
from typing import Dict, List, Tuple


REFERENCE_ROLE_ORDER = {
    "character_reference": 10,
    "character_design_sheet": 11,
    "identity": 12,
    "costume": 13,
    "video_scene_reference": 20,
    "scene": 21,
    "environment": 22,
    "storyboard_layout_reference": 30,
    "storyboard_panel_reference": 31,
    "space_anchor": 40,
}

CHARACTER_ROLES = {"character_reference", "character_design_sheet", "identity", "costume"}
SCENE_ROLES = {"video_scene_reference", "scene", "environment"}
STORYBOARD_ROLES = {"storyboard_layout_reference", "storyboard_panel_reference"}
MANIFEST_REQUIRED_KEYS = {
    "character_reference": ["character_id", "path_or_url"],
    "character_design_sheet": ["character_id", "path_or_url"],
    "identity": ["character_id", "path_or_url"],
    "costume": ["character_id", "path_or_url"],
    "video_scene_reference": ["scene_id", "path_or_url"],
    "scene": ["scene_id", "path_or_url"],
    "environment": ["scene_id", "path_or_url"],
    "storyboard_layout_reference": ["clip_id", "path_or_url"],
    "storyboard_panel_reference": ["clip_id", "path_or_url"],
    "space_anchor": ["scene_id", "path_or_url"],
}


class AssetManifestError(ValueError):
    pass


def build_asset_manifest_template(task: Dict, continuity_bible: Dict = None, video_handoff: Dict = None) -> Dict:
    bible = continuity_bible or (video_handoff or {}).get("continuity_bible") or {}
    handoff = video_handoff or task.get("video_handoff") or task.get("handoff") or {}
    character_locks = bible.get("character_locks") or {}
    scene_locks = bible.get("scene_locks") or {}
    clips = handoff.get("clip_plan") or []
    title = bible.get("source_title") or task.get("title") or task.get("project_title") or "PROJECT_TITLE_HERE"
    manifest = {
        "asset_manifest_version": "1.1",
        "project_title": title,
        "reference_policy": task.get("reference_policy") or task.get("reference_mode") or "all_purpose_reference",
        "character_references": [],
        "scene_references": [],
        "storyboard_references": [],
        "space_anchor_refs": [],
        "notes": [
            "Replace PATH_OR_URL placeholders with approved local paths or public URLs before preflight.",
            "Every character-bearing clip must have character_id-bound character references.",
            "Storyboard references lock layout/edit order only; character identity comes from character references.",
        ],
    }
    for char_id, lock in character_locks.items():
        manifest["character_references"].append(
            {
                "character_id": char_id,
                "name": lock.get("name") or char_id,
                "path": f"PATH_OR_URL_TO_{char_id}_character_reference.png",
                "role": "character_reference",
                "use": "identity, face, hair, body temperament, and costume silhouette lock",
            }
        )
    for scene_id, lock in scene_locks.items():
        manifest["scene_references"].append(
            {
                "scene_id": scene_id,
                "name": lock.get("name") or scene_id,
                "path": f"PATH_OR_URL_TO_{scene_id}_video_scene_reference.png",
                "role": "video_scene_reference",
                "use": "normal perspective scene reference for layout, materials, and light direction",
            }
        )
        manifest["space_anchor_refs"].append(
            {
                "scene_id": scene_id,
                "name": lock.get("name") or scene_id,
                "path": f"PATH_OR_URL_TO_{scene_id}_panorama_space_anchor.png",
                "role": "space_anchor",
                "use": "spatial overview only; not a default direct video generation frame",
            }
        )
    for clip in clips:
        clip_id = clip.get("clip_id")
        if not clip_id:
            continue
        manifest["storyboard_references"].append(
            {
                "clip_id": clip_id,
                "shot_ids": clip.get("shot_ids", []),
                "path": f"PATH_OR_URL_TO_{clip_id}_storyboard_board.png",
                "role": "storyboard_layout_reference",
                "use": "composition, blocking, action phase, screen direction, and edit order only",
            }
        )
    return manifest


def load_asset_manifest(task: Dict) -> Dict:
    manifest = task.get("asset_manifest")
    if manifest:
        if not isinstance(manifest, dict):
            raise AssetManifestError("asset_manifest must be an object")
        return manifest
    path = task.get("asset_manifest_path")
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        loaded = json.load(fh)
    if not isinstance(loaded, dict):
        raise AssetManifestError("asset_manifest_path must point to a JSON object")
    return loaded


def manifest_reference_image_urls(task: Dict) -> List[Dict]:
    manifest = load_asset_manifest(task)
    if not manifest:
        return []
    refs = []
    refs.extend(_collect_named(manifest, "reference_image_urls", None))
    refs.extend(_collect_named(manifest, "character_references", "character_reference"))
    refs.extend(_collect_named(manifest, "scene_references", "video_scene_reference"))
    refs.extend(_collect_named(manifest, "storyboard_references", "storyboard_layout_reference"))
    refs.extend(_collect_named(manifest, "storyboard_layout_references", "storyboard_layout_reference"))
    refs.extend(_collect_assets(manifest.get("assets") or [], include_space_anchor=False))
    return _dedupe_refs(sorted(refs, key=_reference_sort_key))


def validate_asset_manifest(task: Dict) -> Tuple[List[str], List[str]]:
    errors = []
    warnings = []
    try:
        manifest = load_asset_manifest(task)
    except Exception as exc:  # noqa: BLE001 - caller needs the exact preflight blocker.
        return [f"asset_manifest load failed: {exc}"], warnings
    if not manifest:
        return errors, warnings
    refs = manifest_reference_image_urls({"asset_manifest": manifest}) + manifest_space_anchor_refs({"asset_manifest": manifest})
    if not refs:
        errors.append("asset_manifest does not contain any usable reference assets")
        return errors, warnings
    roles = {_role(ref) for ref in refs}
    if not roles & CHARACTER_ROLES:
        warnings.append("asset_manifest has no character reference role")
    if not roles & SCENE_ROLES:
        warnings.append("asset_manifest has no scene reference role")
    if not roles & STORYBOARD_ROLES:
        warnings.append("asset_manifest has no storyboard layout reference role")
    for ref in refs:
        role = _role(ref)
        value = str(ref.get("path") or ref.get("url") or "")
        if not value and "path_or_url" not in MANIFEST_REQUIRED_KEYS.get(role, []):
            errors.append(f"asset_manifest reference missing path/url: {ref}")
        if value.startswith("C:\\Users\\") or "\\Downloads\\" in value:
            warnings.append(f"asset_manifest reference uses fragile local user/download path: {value}")
        required = MANIFEST_REQUIRED_KEYS.get(role, [])
        if "character_id" in required and not ref.get("character_id"):
            errors.append(f"asset_manifest {role} missing character_id: {ref}")
        if "scene_id" in required and not ref.get("scene_id"):
            errors.append(f"asset_manifest {role} missing scene_id: {ref}")
        if "clip_id" in required and not ref.get("clip_id"):
            errors.append(f"asset_manifest {role} missing clip_id: {ref}")
        if "path_or_url" in required and not value:
            errors.append(f"asset_manifest {role} missing path/url: {ref}")
    return errors, warnings


def _collect_named(manifest: Dict, key: str, default_role: str) -> List[Dict]:
    return [_normalize_reference(item, default_role) for item in manifest.get(key) or []]


def manifest_space_anchor_refs(task: Dict) -> List[Dict]:
    manifest = load_asset_manifest(task)
    if not manifest:
        return []
    refs = _collect_named(manifest, "space_anchor_refs", "space_anchor")
    refs.extend(_collect_assets(manifest.get("assets") or [], include_space_anchor=True, only_space_anchor=True))
    return _dedupe_refs(sorted(refs, key=_reference_sort_key))


def _collect_assets(items: List, include_space_anchor: bool = False, only_space_anchor: bool = False) -> List[Dict]:
    refs = []
    for item in items:
        ref = _normalize_reference(item, None)
        role = _role(ref)
        if only_space_anchor and role != "space_anchor":
            continue
        if not include_space_anchor and role == "space_anchor":
            continue
        if role in REFERENCE_ROLE_ORDER:
            refs.append(ref)
    return refs


def _normalize_reference(item, default_role: str) -> Dict:
    if isinstance(item, str):
        ref = {"path": item}
    elif isinstance(item, dict):
        ref = dict(item)
    else:
        raise AssetManifestError(f"unsupported asset manifest reference item: {item}")
    if default_role and not _role(ref):
        ref["role"] = default_role
    if ref.get("asset_kind") and not ref.get("role"):
        ref["role"] = ref["asset_kind"]
    return ref


def _dedupe_refs(refs: List[Dict]) -> List[Dict]:
    seen = set()
    unique = []
    for ref in refs:
        key = (_role(ref), ref.get("url") or ref.get("path") or ref.get("id") or ref.get("name"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(ref)
    return unique


def _reference_sort_key(ref: Dict):
    return (REFERENCE_ROLE_ORDER.get(_role(ref), 99), str(ref.get("character_id") or ref.get("scene_id") or ref.get("name") or ""))


def _role(ref: Dict) -> str:
    return str(ref.get("role") or ref.get("asset_kind") or "").strip()
