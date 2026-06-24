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


class AssetManifestError(ValueError):
    pass


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
        value = str(ref.get("path") or ref.get("url") or "")
        if not value:
            errors.append(f"asset_manifest reference missing path/url: {ref}")
        if value.startswith("C:\\Users\\") or "\\Downloads\\" in value:
            warnings.append(f"asset_manifest reference uses fragile local user/download path: {value}")
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
