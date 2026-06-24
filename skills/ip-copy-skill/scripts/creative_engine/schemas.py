from typing import Any, Dict, List


SCENE_CARD_REQUIRED_FIELDS = ["visual", "voiceover", "duration_sec", "asset_goal"]
SCRIPT_SCENE_REQUIRED_FIELDS = ["visual", "voiceover", "dialogue", "start_sec", "end_sec"]


def validate_required_fields(item: Dict[str, Any], required_fields: List[str], label: str = "item") -> List[str]:
    errors = []
    if not isinstance(item, dict):
        return [f"{label} must be an object"]
    for field in required_fields:
        if field not in item or item.get(field) in (None, "", []):
            errors.append(f"{label} missing required field: {field}")
    return errors


def validate_scene_cards(cards: Any) -> List[str]:
    if not isinstance(cards, list) or not cards:
        return ["scene_cards must be a non-empty list"]
    errors = []
    for index, card in enumerate(cards, start=1):
        errors.extend(validate_required_fields(card, SCENE_CARD_REQUIRED_FIELDS, f"scene_card[{index}]"))
    return errors


def validate_script_scenes(scenes: Any) -> List[str]:
    if not isinstance(scenes, list) or not scenes:
        return ["script scenes must be a non-empty list"]
    errors = []
    for index, scene in enumerate(scenes, start=1):
        errors.extend(validate_required_fields(scene, SCRIPT_SCENE_REQUIRED_FIELDS, f"script_scene[{index}]"))
    return errors