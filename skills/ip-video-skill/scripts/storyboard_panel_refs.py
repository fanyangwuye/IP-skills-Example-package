import os
from typing import Dict, List, Tuple

from PIL import Image


PANEL_REF_ROLES = {
    "first_frame_layout_ref",
    "mid_frame_layout_ref",
    "last_frame_layout_ref",
    "storyboard_layout_reference",
}


def build_storyboard_panel_refs(task: Dict, clip: Dict) -> List[Dict]:
    storyboard_path = _storyboard_path(task, clip)
    if not storyboard_path:
        return []
    if not os.path.exists(storyboard_path):
        raise FileNotFoundError(storyboard_path)

    output_dir = task.get("storyboard_panel_ref_output_dir") or task.get("output_dir") or os.path.dirname(storyboard_path)
    panel_count = int(task.get("storyboard_panel_count") or _panel_count_from_clip(clip))
    boxes = _panel_boxes(storyboard_path, panel_count, task)
    stem = os.path.splitext(os.path.basename(storyboard_path))[0]
    os.makedirs(output_dir, exist_ok=True)

    result = []
    for role, index, frame_spec_key in _selected_panels(panel_count):
        box = boxes[index]
        out_path = os.path.join(output_dir, f"{stem}_{role}.png")
        _crop(storyboard_path, box, out_path)
        result.append(
            {
                "path": out_path,
                "role": role,
                "asset_kind": "storyboard_panel_layout_reference",
                "source_storyboard_path": storyboard_path,
                "source_panel_index": index + 1,
                "frame_spec": frame_spec_key,
                "clip_id": clip.get("clip_id", ""),
                "use": (
                    "composition, camera angle, subject scale, blocking, pose phase, and screen-direction reference only; "
                    "do not copy storyboard line-art style, panel borders, table text, labels, grayscale texture, or handwritten marks"
                ),
            }
        )
    return result


def attach_storyboard_panel_refs(task: Dict, unit: Dict) -> Dict:
    refs = list(task.get("storyboard_panel_refs") or [])
    refs.extend(unit.get("storyboard_panel_refs") or [])
    if refs:
        unit = dict(unit)
        unit["storyboard_panel_refs"] = refs
    return unit


def _storyboard_path(task: Dict, clip: Dict) -> str:
    explicit = task.get("storyboard_panel_source_path") or task.get("storyboard_image_path")
    if explicit:
        return explicit
    paths = task.get("storyboard_image_paths") or {}
    if isinstance(paths, dict):
        return paths.get(clip.get("clip_id", "")) or paths.get(str(clip.get("order", ""))) or paths.get("default", "")
    if isinstance(paths, list) and paths:
        index = int(clip.get("order") or 1) - 1
        return paths[index] if 0 <= index < len(paths) else paths[0]
    return ""


def _panel_count_from_clip(clip: Dict) -> int:
    profile = clip.get("storyboard_profile") or {}
    if profile.get("panel_count"):
        return int(profile["panel_count"])
    duration = float((clip.get("timing") or {}).get("duration_sec") or 0)
    if duration <= 6:
        return 3
    if duration <= 15:
        return 5
    return 6


def _selected_panels(panel_count: int) -> List[Tuple[str, int, str]]:
    if panel_count <= 1:
        return [("first_frame_layout_ref", 0, "first_frame_spec")]
    return [
        ("first_frame_layout_ref", 0, "first_frame_spec"),
        ("mid_frame_layout_ref", panel_count // 2, "mid_frame_spec"),
        ("last_frame_layout_ref", panel_count - 1, "last_frame_spec"),
    ]


def _panel_boxes(storyboard_path: str, panel_count: int, task: Dict) -> List[Tuple[int, int, int, int]]:
    with Image.open(storyboard_path) as img:
        width, height = img.size
    if task.get("storyboard_panel_boxes"):
        boxes = [tuple(int(v) for v in box) for box in task["storyboard_panel_boxes"]]
        if len(boxes) < panel_count:
            raise ValueError("storyboard_panel_boxes must include at least storyboard_panel_count boxes")
        return boxes[:panel_count]

    top_ratio = float(task.get("storyboard_panel_top_ratio", 0.11))
    bottom_ratio = float(task.get("storyboard_panel_bottom_ratio", 0.49))
    left_ratio = float(task.get("storyboard_panel_left_ratio", 0.08))
    right_ratio = float(task.get("storyboard_panel_right_ratio", 0.995))

    top = _clamp_int(height * top_ratio, 0, height - 1)
    bottom = _clamp_int(height * bottom_ratio, top + 1, height)
    left = _clamp_int(width * left_ratio, 0, width - 1)
    right = _clamp_int(width * right_ratio, left + 1, width)
    content_width = right - left

    boxes = []
    for index in range(panel_count):
        panel_left = left + content_width * index // panel_count
        panel_right = left + content_width * (index + 1) // panel_count if index < panel_count - 1 else right
        inset_x = max(0, int((panel_right - panel_left) * float(task.get("storyboard_panel_inset_x_ratio", 0.006))))
        inset_y = max(0, int((bottom - top) * float(task.get("storyboard_panel_inset_y_ratio", 0.035))))
        boxes.append((panel_left + inset_x, top + inset_y, panel_right - inset_x, bottom - inset_y))
    return boxes


def _crop(src_path: str, box: Tuple[int, int, int, int], out_path: str) -> None:
    with Image.open(src_path) as img:
        cropped = img.crop(box)
        cropped.save(out_path)


def _clamp_int(value: float, low: int, high: int) -> int:
    return max(low, min(int(round(value)), high))

