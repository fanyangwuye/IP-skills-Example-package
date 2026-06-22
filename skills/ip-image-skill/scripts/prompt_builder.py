import json
import os
from typing import Dict, List, Optional

try:
    from .config import skill_root
except ImportError:
    from config import skill_root


def default_style_card_path(ip_id: str) -> str:
    return os.path.join(skill_root(), "references", "style_cards", f"{ip_id}.json")


def default_style_preset_path(style_preset: str) -> str:
    return os.path.join(skill_root(), "references", "style_presets", f"{style_preset}.json")


def _merge_style_cards(base: Dict, override: Dict) -> Dict:
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, list):
            existing = merged.get(key)
            if not isinstance(existing, list):
                existing = []
            merged[key] = existing + [item for item in value if item not in existing]
        elif isinstance(value, dict):
            existing = merged.get(key)
            merged[key] = _merge_style_cards(existing if isinstance(existing, dict) else {}, value)
        elif value not in (None, ""):
            merged[key] = value
    return merged


def _load_json(path: str) -> Dict:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_style_card(
    ip_id: Optional[str] = None,
    style_card_path: Optional[str] = None,
    style_preset: Optional[str] = None,
) -> Dict:
    cards: List[Dict] = []
    if style_preset:
        cards.append(_load_json(default_style_preset_path(style_preset)))

    path = style_card_path
    if not path and ip_id and not style_preset:
        candidate = default_style_card_path(ip_id)
        if os.path.exists(candidate):
            path = candidate
    if path:
        cards.append(_load_json(path))

    merged: Dict = {}
    for card in cards:
        merged = _merge_style_cards(merged, card)
    return merged


def build_image_prompt(base_prompt: str, style_card: Optional[Dict] = None) -> str:
    style_card = style_card or {}
    parts: List[str] = []

    if style_card.get("style_direction"):
        parts.append(f"Style direction: {style_card['style_direction']}")
    if style_card.get("primary_palette"):
        parts.append(f"Primary palette: {style_card['primary_palette']}")
    if style_card.get("character_anchors"):
        parts.append("Character anchors: " + ", ".join(style_card["character_anchors"]))
    if style_card.get("positive_prompt_fragments"):
        parts.append("Positive prompt fragments: " + ", ".join(style_card["positive_prompt_fragments"]))
    if base_prompt.strip():
        parts.append(base_prompt.strip())
    if style_card.get("forbidden_elements"):
        parts.append("Avoid: " + ", ".join(style_card["forbidden_elements"]))
    if style_card.get("negative_prompt_fragments"):
        parts.append("Negative prompt fragments: " + ", ".join(style_card["negative_prompt_fragments"]))
    if style_card.get("realism_constraints"):
        parts.append("Realism constraints: " + ", ".join(style_card["realism_constraints"]))

    return " | ".join(part for part in parts if part)


def _has_content(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set)):
        return any(_has_content(item) for item in value)
    if isinstance(value, dict):
        return any(_has_content(item) for item in value.values())
    return True


def _format_structure(value) -> str:
    if isinstance(value, dict):
        chunks = []
        for key, item in value.items():
            if _has_content(item):
                chunks.append(f"{key}: {_format_structure(item)}")
        return "; ".join(chunks)
    if isinstance(value, (list, tuple, set)):
        chunks = [_format_structure(item) for item in value if _has_content(item)]
        return ", ".join(chunk for chunk in chunks if chunk)
    return str(value).strip()


def build_task_prompt(task: Dict, style_card: Optional[Dict] = None) -> str:
    style_card = style_card or {}
    parts: List[str] = []

    creation_stage = task.get("creation_stage")
    if creation_stage:
        parts.append(f"Creation stage: {creation_stage}")

    current_focus = task.get("current_focus")
    if current_focus:
        parts.append(f"Current focus: {current_focus}")

    asset_kind = task.get("asset_kind")
    if asset_kind:
        parts.append(f"Asset kind: {asset_kind}")

    creative_goal = task.get("creative_goal")
    if creative_goal:
        parts.append(f"Creative goal: {creative_goal}")

    character_name = task.get("character_name")
    if character_name:
        parts.append(f"Character name: {character_name}")

    character_brief = task.get("character_brief")
    if character_brief:
        parts.append(f"Character brief: {character_brief}")

    source_text = task.get("source_text")
    if source_text:
        parts.append(f"Source text for extraction and visual adaptation: {source_text}")

    appearance_traits = task.get("appearance_traits") or []
    if appearance_traits:
        parts.append("Appearance traits: " + ", ".join(appearance_traits))

    wardrobe = task.get("wardrobe")
    if wardrobe:
        parts.append(f"Wardrobe: {wardrobe}")

    scene = task.get("scene")
    if scene:
        parts.append(f"Scene: {scene}")

    emotion = task.get("emotion")
    if emotion:
        parts.append(f"Emotion: {emotion}")

    pose = task.get("pose")
    if pose:
        parts.append(f"Pose: {pose}")

    camera = task.get("camera")
    if camera:
        parts.append(f"Camera: {camera}")

    composition = task.get("composition")
    if composition:
        parts.append(f"Composition: {composition}")

    lighting = task.get("lighting")
    if lighting:
        parts.append(f"Lighting: {lighting}")

    asset_requirements = task.get("asset_requirements") or []
    if asset_requirements:
        parts.append("Asset requirements: " + ", ".join(asset_requirements))

    visual_text_language = task.get("visual_text_language")
    if visual_text_language:
        parts.append(f"Visible text language: {visual_text_language}")

    visible_text_requirements = task.get("visible_text_requirements") or []
    if visible_text_requirements:
        parts.append("Visible text requirements: " + ", ".join(visible_text_requirements))

    props = task.get("props") or []
    if _has_content(props):
        parts.append("Character props and callouts: " + _format_structure(props))

    prop_profile = task.get("prop_profile") or {}
    if _has_content(prop_profile):
        parts.append("Prop profile: " + _format_structure(prop_profile))

    scene_profile = task.get("scene_profile") or {}
    if _has_content(scene_profile):
        parts.append("Scene profile: " + _format_structure(scene_profile))

    gpt_image_2_spec = task.get("gpt_image_2_spec") or {}
    if _has_content(gpt_image_2_spec):
        parts.append("GPT Image 2 output spec: " + _format_structure(gpt_image_2_spec))

    character_profile = task.get("character_profile") or {}
    if _has_content(character_profile):
        parts.append("Character profile: " + _format_structure(character_profile))

    identity_anchors = task.get("identity_anchors") or []
    if _has_content(identity_anchors):
        parts.append("Identity anchors: " + _format_structure(identity_anchors))

    continuity_rules = task.get("continuity_rules") or []
    if _has_content(continuity_rules):
        parts.append("Continuity rules: " + _format_structure(continuity_rules))

    asset_target = task.get("asset_target") or {}
    if _has_content(asset_target):
        parts.append("Asset target: " + _format_structure(asset_target))

    asset_bundle = task.get("asset_bundle") or []
    if _has_content(asset_bundle):
        parts.append("Asset bundle: " + _format_structure(asset_bundle))

    interaction_state = task.get("interaction_state") or {}
    if _has_content(interaction_state):
        parts.append("Interaction state: " + _format_structure(interaction_state))

    interaction_notes = task.get("interaction_notes") or []
    if interaction_notes:
        parts.append("Interaction refinements: " + " | ".join(str(note).strip() for note in interaction_notes if str(note).strip()))

    conversation_turns = task.get("conversation_turns") or []
    if conversation_turns:
        normalized_turns = []
        for turn in conversation_turns:
            if isinstance(turn, dict):
                role = str(turn.get("role", "user")).strip() or "user"
                content = str(turn.get("content", "")).strip()
                if content:
                    normalized_turns.append(f"{role}: {content}")
            else:
                content = str(turn).strip()
                if content:
                    normalized_turns.append(content)
        if normalized_turns:
            parts.append("Conversation cues: " + " | ".join(normalized_turns))

    base_prompt = task.get("prompt", "")
    if base_prompt:
        parts.append(base_prompt)

    merged_prompt = " | ".join(part for part in parts if part)
    return build_image_prompt(merged_prompt, style_card)
