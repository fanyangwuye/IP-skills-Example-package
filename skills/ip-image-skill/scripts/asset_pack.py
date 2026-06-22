import copy
from typing import Dict, List, Optional


DEFAULT_CHARACTER_DESIGN_REQUIREMENTS = [
    "character design sheet only",
    "plain neutral background",
    "no environment scene",
    "no cinematic background",
    "show clear face, full body silhouette, wardrobe details, and key handheld props",
    "production reference readability",
]


DEFAULT_CHARACTER_TEXT_REQUIREMENTS = [
    "all visible text on the character design sheet must be Simplified Chinese unless the task explicitly requests another language",
    "use Chinese headings for character name, role, age, personality, aura, world context, props, color palette, and back view",
    "translate prop names and prop use notes into natural Chinese when source fields are English",
    "avoid English headings or English-only labels on the image unless the user explicitly requests English",
]


DEFAULT_PANORAMA_REQUIREMENTS = [
    "720-degree equirectangular panorama environment concept",
    "left and right edges must connect seamlessly",
    "no visible seam at horizontal edges",
    "wide environment layout suitable for camera movement planning",
    "no main character blocking the view",
]


def build_ip_asset_pack_tasks(pack: Dict, output_dir: str) -> List[Dict]:
    tasks: List[Dict] = []
    common = _common_fields(pack)

    for character in pack.get("characters") or []:
        tasks.extend(_build_character_tasks(character, common, output_dir))

    for scene in pack.get("scenes") or []:
        tasks.append(_build_scene_task(scene, common, output_dir))

    for prop in pack.get("standalone_props") or []:
        tasks.append(_build_prop_task(prop, common, output_dir))

    return tasks


def _common_fields(pack: Dict) -> Dict:
    return {
        key: copy.deepcopy(pack[key])
        for key in (
            "ip_id",
            "style_preset",
            "style_card_path",
            "reference_image_urls",
            "style_reference_paths",
            "quality",
            "resolution",
            "visual_text_language",
            "visible_text_requirements",
        )
        if key in pack
    }


def _build_character_tasks(character: Dict, common: Dict, output_dir: str) -> List[Dict]:
    character_id = character.get("character_id") or _safe_label(
        character.get("character_profile", {}).get("identity", {}).get("name", "character")
    )
    filename_prefix = _safe_label(character_id)
    props = character.get("props") or []
    asset_bundle = character.get("asset_bundle") or [
        {
            "label": "design_sheet",
            "filename": f"{filename_prefix}_design_sheet.jpg",
            "asset_target": {
                "type": "character design sheet",
                "purpose": "clean production reference for this character and props",
                "framing": "full body front three-quarter view with face callout and prop callouts",
                "scene": "plain neutral background",
            },
            "camera": "front three-quarter full body design sheet",
            "composition": "single character, clean silhouette, prop callouts arranged beside the character",
            "asset_requirements": DEFAULT_CHARACTER_DESIGN_REQUIREMENTS,
        }
    ]

    tasks: List[Dict] = []
    for item in asset_bundle:
        task = {
            **copy.deepcopy(common),
            "mode": "character_create",
            "creation_stage": "multi_character_asset_pack",
            "current_focus": item.get("current_focus", f"generate character asset: {character_id} / {item.get('label', 'asset')}"),
            "character_profile": copy.deepcopy(character.get("character_profile", {})),
            "identity_anchors": copy.deepcopy(character.get("identity_anchors", [])),
            "continuity_rules": copy.deepcopy(character.get("continuity_rules", [])),
            "asset_target": copy.deepcopy(item.get("asset_target", {})),
            "interaction_state": copy.deepcopy(character.get("interaction_state", {})),
            "props": copy.deepcopy(props),
            "visual_text_language": item.get(
                "visual_text_language",
                character.get("visual_text_language", common.get("visual_text_language", "zh-CN")),
            ),
            "visible_text_requirements": copy.deepcopy(
                item.get(
                    "visible_text_requirements",
                    character.get(
                        "visible_text_requirements",
                        common.get("visible_text_requirements", DEFAULT_CHARACTER_TEXT_REQUIREMENTS),
                    ),
                )
            ),
            "output_dir": output_dir,
            "filename": item.get("filename", f"{filename_prefix}_{item.get('label', 'asset')}.jpg"),
            "size": item.get("size", character.get("size", "3:4")),
            "resolution": item.get("resolution", character.get("resolution", common.get("resolution", "2K"))),
            "quality": item.get("quality", character.get("quality", common.get("quality", "high"))),
        }
        for key in (
            "prompt",
            "scene",
            "emotion",
            "pose",
            "camera",
            "composition",
            "lighting",
            "asset_requirements",
            "gpt_image_2_spec",
        ):
            if key in item:
                task[key] = copy.deepcopy(item[key])
        tasks.append(task)
    return tasks


def _build_scene_task(scene: Dict, common: Dict, output_dir: str) -> Dict:
    scene_id = _safe_label(scene.get("scene_id") or scene.get("name") or "scene")
    asset_requirements = list(DEFAULT_PANORAMA_REQUIREMENTS)
    asset_requirements.extend(scene.get("asset_requirements") or [])
    return {
        **copy.deepcopy(common),
        "mode": "text_to_image",
        "creation_stage": "scene_panorama_asset_pack",
        "current_focus": f"generate 720 seamless panorama scene: {scene_id}",
        "asset_kind": "720_seamless_panorama_scene",
        "scene_profile": copy.deepcopy(scene),
        "asset_target": {
            "type": "720 seamless panorama",
            "purpose": scene.get("purpose", "environment reference and camera movement planning"),
            "scene": scene.get("description", scene.get("name", "")),
        },
        "camera": "equirectangular 720-degree panorama, horizon centered",
        "composition": "continuous environment wrapping horizontally, no foreground character occlusion",
        "lighting": scene.get("lighting", ""),
        "asset_requirements": asset_requirements,
        "gpt_image_2_spec": {
            "model": "gpt-image-2",
            "recommended_size": scene.get("size", "21:9"),
            "recommended_resolution": scene.get("resolution", "4K"),
            "note": "Use 21:9 or custom wide size for panorama-style output; prompt requires seamless left-right edges.",
        },
        "quality": scene.get("quality", common.get("quality", "high")),
        "size": scene.get("size", "21:9"),
        "resolution": scene.get("resolution", common.get("resolution", "4K")),
        "filename": scene.get("filename", f"{scene_id}_720_panorama.jpg"),
        "output_dir": output_dir,
    }


def _build_prop_task(prop: Dict, common: Dict, output_dir: str) -> Dict:
    prop_id = _safe_label(prop.get("prop_id") or prop.get("name") or "prop")
    return {
        **copy.deepcopy(common),
        "mode": "text_to_image",
        "creation_stage": "prop_asset_pack",
        "current_focus": f"generate standalone prop design: {prop_id}",
        "asset_kind": "prop_design_sheet",
        "prop_profile": copy.deepcopy(prop),
        "asset_target": {
            "type": "prop design sheet",
            "purpose": prop.get("purpose", "production prop reference"),
            "scene": "plain neutral background",
        },
        "composition": "single prop design sheet, front view and detail callout, no environment background",
        "asset_requirements": [
            "prop design sheet only",
            "plain neutral background",
            "no environment scene",
            "clear material and scale details",
        ],
        "quality": prop.get("quality", common.get("quality", "high")),
        "size": prop.get("size", "1:1"),
        "resolution": prop.get("resolution", common.get("resolution", "2K")),
        "filename": prop.get("filename", f"{prop_id}_prop_sheet.jpg"),
        "output_dir": output_dir,
    }


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
    return label or "asset"
