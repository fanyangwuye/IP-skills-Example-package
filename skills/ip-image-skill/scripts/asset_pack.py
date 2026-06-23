import copy
from typing import Dict, List, Optional


DEFAULT_CHARACTER_DESIGN_REQUIREMENTS = [
    "character design sheet only",
    "plain neutral background",
    "no environment scene",
    "no cinematic background",
    "show clear face, full body silhouette, wardrobe details, and key handheld props",
    "include a face structure callout that locks facial proportions, face shape, brow shape, eye shape, eye spacing, nose bridge, nose tip, mouth shape, lip shape, jaw/chin, cheekbones, and any facial marks",
    "same character identity must be defined by stable facial geometry, not only hairstyle or costume",
    "production reference readability",
    "original actress-like face, not a celebrity face and not a generic influencer face",
    "preserve realistic skin texture, visible pores, tiny blemishes, natural nasolabial folds, slight under-eye shadow, and subtle facial asymmetry",
    "no plastic skin, no over-smoothing, no over-symmetry, no glassy doll eyes, no heavy false eyelashes, no over-sharpening, no influencer makeup, no Barbie-doll face, no studio glamour portrait look",
    "realistic suspense short-drama casting test close-up quality when face callouts are shown",
]


DEFAULT_CHARACTER_TEXT_REQUIREMENTS = [
    "图片内所有可见文字默认使用简体中文，除非用户明确要求其他语言",
    "设定板只使用少量清晰大字标签，不要生成密集小段落、长说明、小字号正文或装饰性假文字",
    "中文字段标题固定使用：角色名、身份、年龄、五官比例、脸型、眉眼、鼻型、口型、发型、服装、道具、色板、背面图",
    "道具名称和用途必须翻译成自然中文，避免英文标题和英文-only 标签",
    "所有中文标签必须横排、清晰、字号足够大，优先保证可读性而不是塞满信息",
    "如果文字无法清晰呈现，减少文字数量，保留角色名、身份、道具名这些核心标签",
]


DEFAULT_PANORAMA_REQUIREMENTS = [
    "720-degree equirectangular panorama environment concept",
    "left and right edges must connect seamlessly",
    "no visible seam at horizontal edges",
    "wide environment layout suitable for camera movement planning",
    "no main character blocking the view",
]

DEFAULT_VIDEO_SCENE_REQUIREMENTS = [
    "normal perspective environment reference for video generation",
    "stable spatial anchors: entrances, windows, counters, roads, landmarks, and light direction",
    "no 720 panorama projection",
    "no fisheye distortion",
    "no main character blocking the layout",
    "clear foreground, midground, and background layers for camera planning",
]


def build_ip_asset_pack_tasks(pack: Dict, output_dir: str) -> List[Dict]:
    tasks: List[Dict] = []
    common = _common_fields(pack)

    for character in pack.get("characters") or []:
        tasks.extend(_build_character_tasks(character, common, output_dir))

    for scene in pack.get("scenes") or []:
        tasks.extend(_build_scene_tasks(scene, common, output_dir))

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
            "composition": "single character, clean silhouette, prop callouts arranged beside the character, large readable Chinese labels only, no dense paragraphs",
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


def _build_scene_tasks(scene: Dict, common: Dict, output_dir: str) -> List[Dict]:
    tasks = [_build_scene_panorama_task(scene, common, output_dir)]
    if scene.get("include_video_reference", True):
        tasks.append(_build_video_scene_reference_task(scene, common, output_dir))
    return tasks


def _build_scene_panorama_task(scene: Dict, common: Dict, output_dir: str) -> Dict:
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


def _build_video_scene_reference_task(scene: Dict, common: Dict, output_dir: str) -> Dict:
    scene_id = _safe_label(scene.get("scene_id") or scene.get("name") or "scene")
    asset_requirements = list(DEFAULT_VIDEO_SCENE_REQUIREMENTS)
    asset_requirements.extend(scene.get("video_reference_requirements") or [])
    return {
        **copy.deepcopy(common),
        "mode": "text_to_image",
        "creation_stage": "scene_video_reference_asset_pack",
        "current_focus": f"generate normal video scene reference: {scene_id}",
        "asset_kind": "video_scene_reference",
        "scene_profile": copy.deepcopy(scene),
        "asset_target": {
            "type": "normal perspective video scene reference",
            "purpose": scene.get("video_reference_purpose", "video reference for spatial continuity and image-to-video generation"),
            "scene": scene.get("description", scene.get("name", "")),
        },
        "camera": scene.get("video_reference_camera", "normal cinematic wide establishing frame, 35mm lens feel, eye-level or slightly low angle"),
        "composition": scene.get(
            "video_reference_composition",
            "single coherent environment frame with stable spatial anchors, readable entrances and landmarks, no 720 panorama wrap",
        ),
        "lighting": scene.get("lighting", ""),
        "asset_requirements": asset_requirements,
        "gpt_image_2_spec": {
            "model": "gpt-image-2",
            "recommended_size": scene.get("video_reference_size", "16:9"),
            "recommended_resolution": scene.get("video_reference_resolution", common.get("resolution", "2K")),
            "note": "Use this normal perspective scene reference for video generation; keep panorama assets as separate space anchors.",
        },
        "quality": scene.get("video_reference_quality", scene.get("quality", common.get("quality", "high"))),
        "size": scene.get("video_reference_size", "16:9"),
        "resolution": scene.get("video_reference_resolution", common.get("resolution", "2K")),
        "filename": scene.get("video_reference_filename", f"{scene_id}_video_scene_reference.jpg"),
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
