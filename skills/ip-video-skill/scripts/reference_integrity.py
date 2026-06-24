from typing import Dict, List


CHARACTER_REFERENCE_ROLES = {"character_reference", "character_design_sheet", "identity", "costume", "face"}
FRAME_REFERENCE_ROLES = {"first_frame", "last_frame", "previous_clip_end_frame"}
CHARACTER_ID_FIELDS = ["character_id", "character", "char_id", "name"]


def character_reference_binding_report(request: Dict) -> Dict:
    required = _required_character_ids(request)
    refs = _all_reference_inputs(request)
    character_refs = [ref for ref in refs if _role(ref) in CHARACTER_REFERENCE_ROLES]
    frame_refs = [ref for ref in refs if _role(ref) in FRAME_REFERENCE_ROLES]
    matched = _matched_character_ids(required, character_refs)
    missing = [char_id for char_id in required if char_id not in matched]
    ambiguous_refs = [ref for ref in character_refs if not _ref_character_id(ref)]

    status = "pass"
    messages = []
    if required and not character_refs and not frame_refs:
        status = "fail"
        messages.append("character-bearing clip has no character reference or reviewed first-frame input")
    elif len(required) >= 2 and ambiguous_refs:
        status = "fail"
        messages.append("multi-character clip has character reference(s) without character_id binding")
    elif missing:
        status = "fail"
        messages.append("missing character reference binding for: " + ", ".join(missing))
    elif required and not character_refs and frame_refs:
        status = "warn"
        messages.append("character identity relies on reviewed frame input; no direct character reference role was provided")

    return {
        "status": status,
        "required_character_ids": required,
        "matched_character_ids": matched,
        "missing_character_ids": missing,
        "character_reference_count": len(character_refs),
        "frame_reference_count": len(frame_refs),
        "ambiguous_character_reference_count": len(ambiguous_refs),
        "messages": messages,
    }


def _required_character_ids(request: Dict) -> List[str]:
    characters = ((request.get("visual_lock") or {}).get("characters") or {})
    if isinstance(characters, dict):
        return [str(char_id) for char_id in characters.keys() if str(char_id).strip()]
    if isinstance(characters, list):
        return [str(char_id) for char_id in characters if str(char_id).strip()]
    return []


def _all_reference_inputs(request: Dict) -> List[Dict]:
    refs = []
    for key in ("reference_image_urls", "image_urls", "reference_images"):
        for item in request.get(key) or []:
            refs.append(_normalize_ref(item))
    return refs


def _matched_character_ids(required: List[str], refs: List[Dict]) -> List[str]:
    matched = []
    if len(required) == 1 and refs:
        matched.append(required[0])
    for ref in refs:
        ref_char = _ref_character_id(ref)
        if ref_char and ref_char in required and ref_char not in matched:
            matched.append(ref_char)
    return matched


def _normalize_ref(item) -> Dict:
    if isinstance(item, dict):
        return dict(item)
    return {"url": str(item), "role": "general"}


def _ref_character_id(ref: Dict) -> str:
    for field in CHARACTER_ID_FIELDS:
        value = str(ref.get(field) or "").strip()
        if value:
            return value
    return ""


def _role(ref: Dict) -> str:
    return str(ref.get("role") or ref.get("asset_kind") or "").strip()