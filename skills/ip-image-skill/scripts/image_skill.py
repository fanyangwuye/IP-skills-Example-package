import json
import os
import argparse
from typing import Dict, List

try:
    from .asset_pack import build_ip_asset_pack_tasks
    from .config import load_image_provider_config
    from .character_sheet import build_asset_bundle_tasks
    from .poyo_client import PoYoClient
    from .prompt_builder import build_task_prompt, load_style_card
    from .split_grid import grid_to_rows_cols, save_tiles, split_image
except ImportError:
    from asset_pack import build_ip_asset_pack_tasks
    from config import load_image_provider_config
    from character_sheet import build_asset_bundle_tasks
    from poyo_client import PoYoClient
    from prompt_builder import build_task_prompt, load_style_card
    from split_grid import grid_to_rows_cols, save_tiles, split_image


def _artifact(path: str, artifact_type: str, meta: Dict) -> Dict:
    return {
        "type": artifact_type,
        "path": path,
        "meta": meta,
    }


def run_task(task: Dict) -> Dict:
    mode = task.get("mode")
    if mode not in {"text_to_image", "grid_enhance", "single_image_refine", "character_create", "character_refine", "character_asset_bundle", "ip_asset_pack"}:
        raise ValueError("mode must be one of: text_to_image, grid_enhance, single_image_refine, character_create, character_refine, character_asset_bundle, ip_asset_pack")

    config = load_image_provider_config()
    if config.provider != "poyo":
        raise RuntimeError(f"Unsupported IMAGE_PROVIDER: {config.provider}")

    client = PoYoClient(config)
    output_dir = task.get("output_dir") or config.output_root
    os.makedirs(output_dir, exist_ok=True)

    if mode in {"text_to_image", "character_create"}:
        return _run_text_to_image(task, output_dir, client)
    if mode in {"single_image_refine", "character_refine"}:
        return _run_single_image_refine(task, output_dir, client)
    if mode == "character_asset_bundle":
        return _run_character_asset_bundle(task, output_dir, client)
    if mode == "ip_asset_pack":
        return _run_ip_asset_pack(task, output_dir, client)
    return _run_grid_enhance(task, output_dir, client)


def _run_text_to_image(task: Dict, output_dir: str, client: PoYoClient) -> Dict:
    result_mode = task.get("mode", "text_to_image")
    style_card = load_style_card(
        task.get("ip_id"),
        task.get("style_card_path"),
        task.get("style_preset"),
    )
    prompt = build_task_prompt(task, style_card)
    quality = task.get("quality", "high")
    size = task.get("size", "1:1")
    resolution = task.get("resolution", "2K")
    filename = task.get("filename", "generated_image.jpg")
    reference_image_urls = _collect_reference_image_urls(task, client)

    task_id = client.submit_text_to_image(
        prompt=prompt,
        quality=quality,
        size=size,
        resolution=resolution,
        image_urls=reference_image_urls,
    )
    result = client.wait_for_task(task_id)
    files = result.get("files", [])
    if not files:
        raise RuntimeError(f"No files returned for task {task_id}")

    final_path = os.path.join(output_dir, filename)
    client.download_file(files[0]["file_url"], final_path)

    return {
        "status": "success",
        "skill": "ip-image-skill",
        "mode": result_mode,
        "task_id": task_id,
        "artifacts": [
            _artifact(
                final_path,
                "image",
                {
                    "provider": "poyo",
                    "remote_url": files[0]["file_url"],
                    "prompt_used": prompt,
                    "style_preset": task.get("style_preset", ""),
                    "reference_image_urls": reference_image_urls,
                },
            )
        ],
        "logs": [f"Completed text_to_image task {task_id}"],
    }


def _run_grid_enhance(task: Dict, output_dir: str, client: PoYoClient) -> Dict:
    result_mode = task.get("mode", "grid_enhance")
    src_path = task["src_path"]
    if not os.path.exists(src_path):
        raise FileNotFoundError(src_path)

    grid = int(task.get("grid", 4))
    rows, cols = grid_to_rows_cols(grid)
    stem = os.path.splitext(os.path.basename(src_path))[0]
    split_dir = os.path.join(output_dir, f"{stem}_tiles")
    enhance_dir = os.path.join(output_dir, f"{stem}_enhanced")
    os.makedirs(split_dir, exist_ok=True)
    os.makedirs(enhance_dir, exist_ok=True)

    tiles = split_image(src_path, rows, cols)
    split_paths = save_tiles(tiles, split_dir, stem)

    presets = _load_presets()
    enhance_level = task.get("enhance_level", "low")
    if enhance_level not in presets:
        raise ValueError(f"Unsupported enhance_level: {enhance_level}")
    preset = presets[enhance_level]

    style_card = load_style_card(
        task.get("ip_id"),
        task.get("style_card_path"),
        task.get("style_preset"),
    )
    base_prompt = build_task_prompt(task, style_card)
    artifacts: List[Dict] = []
    logs: List[str] = []

    for index, split_path in enumerate(split_paths, start=1):
        upload = client.upload_file_stream(
            split_path,
            upload_path="image-skill/tiles",
            file_name=os.path.basename(split_path),
        )
        edit_prompt = " ".join(
            part for part in [base_prompt.strip(), preset["prompt_suffix"].strip()] if part
        ).strip()
        task_id = client.submit_image_edit(
            prompt=edit_prompt,
            image_urls=[upload["file_url"]],
            quality=preset["quality"],
            size=task.get("size", "1:1"),
            resolution=preset["resolution"],
        )
        result = client.wait_for_task(task_id)
        files = result.get("files", [])
        if not files:
            raise RuntimeError(f"No files returned for edit task {task_id}")
        enhanced_path = os.path.join(enhance_dir, f"{stem}_enhanced_{index:02d}.jpg")
        client.download_file(files[0]["file_url"], enhanced_path)
        artifacts.append(
            _artifact(
                enhanced_path,
                "image",
                {
                    "provider": "poyo",
                    "source_tile": split_path,
                    "remote_url": files[0]["file_url"],
                    "enhance_level": enhance_level,
                },
            )
        )
        logs.append(f"Enhanced tile {index}/{len(split_paths)} with task {task_id}")

    return {
        "status": "success",
        "skill": "ip-image-skill",
        "mode": result_mode,
        "task_id": f"{stem}_grid_enhance",
        "artifacts": artifacts,
        "logs": logs,
        "handoff": {
            "source_grid": src_path,
            "split_tiles": split_paths,
        },
    }


def _run_single_image_refine(task: Dict, output_dir: str, client: PoYoClient) -> Dict:
    result_mode = task.get("mode", "single_image_refine")
    src_path = task["src_path"]
    if not os.path.exists(src_path):
        raise FileNotFoundError(src_path)

    presets = _load_presets()
    refine_level = task.get("refine_level", task.get("enhance_level", "low"))
    if refine_level not in presets:
        raise ValueError(f"Unsupported refine_level: {refine_level}")
    preset = presets[refine_level]

    style_card = load_style_card(
        task.get("ip_id"),
        task.get("style_card_path"),
        task.get("style_preset"),
    )
    base_prompt = build_task_prompt(task, style_card)
    preserve_identity = task.get("preserve_identity", True)
    preserve_line = (
        "Preserve the exact identity, face, core composition, and subject continuity from the source image."
        if preserve_identity
        else ""
    )
    edit_prompt = " ".join(
        part
        for part in [base_prompt.strip(), preserve_line.strip(), preset["prompt_suffix"].strip()]
        if part
    ).strip()

    upload = client.upload_file_stream(
        src_path,
        upload_path="image-skill/refine",
        file_name=os.path.basename(src_path),
    )
    task_id = client.submit_image_edit(
        prompt=edit_prompt,
        image_urls=[upload["file_url"]],
        quality=preset["quality"],
        size=task.get("size", "1:1"),
        resolution=preset["resolution"],
    )
    result = client.wait_for_task(task_id)
    files = result.get("files", [])
    if not files:
        raise RuntimeError(f"No files returned for refine task {task_id}")

    default_name = os.path.splitext(os.path.basename(src_path))[0] + "_refined.jpg"
    filename = task.get("filename", default_name)
    final_path = os.path.join(output_dir, filename)
    client.download_file(files[0]["file_url"], final_path)

    return {
        "status": "success",
        "skill": "ip-image-skill",
        "mode": result_mode,
        "task_id": task_id,
        "artifacts": [
            _artifact(
                final_path,
                "image",
                {
                    "provider": "poyo",
                    "source_image": src_path,
                    "remote_url": files[0]["file_url"],
                    "refine_level": refine_level,
                    "prompt_used": edit_prompt,
                },
            )
        ],
        "logs": [f"Completed single_image_refine task {task_id}"],
    }


def _run_character_asset_bundle(task: Dict, output_dir: str, client: PoYoClient) -> Dict:
    asset_bundle = task.get("asset_bundle") or []
    if not asset_bundle:
        raise ValueError("character_asset_bundle requires a non-empty asset_bundle")

    common_fields = {
        key: value
        for key, value in task.items()
        if key not in {"mode", "asset_bundle", "output_dir", "filename", "bundle_item_label"}
    }
    bundle_tasks = build_asset_bundle_tasks(
        sheet={
            "character_profile": task.get("character_profile", {}),
            "identity_anchors": task.get("identity_anchors", []),
            "continuity_rules": task.get("continuity_rules", []),
            "interaction_state": task.get("interaction_state", {}),
            "asset_target": task.get("asset_target", {}),
        },
        output_dir=output_dir,
        asset_bundle=asset_bundle,
        common_fields=common_fields,
    )

    artifacts: List[Dict] = []
    logs: List[str] = []
    child_tasks: List[Dict] = []

    for index, child_task in enumerate(bundle_tasks, start=1):
        child_result = _run_text_to_image(child_task, output_dir, client)
        child_label = child_task.get("bundle_item_label", f"asset_{index:02d}")
        child_tasks.append(
            {
                "label": child_label,
                "task_id": child_result["task_id"],
                "asset_target": child_task.get("asset_target", {}),
                "artifacts": child_result["artifacts"],
            }
        )
        for artifact in child_result["artifacts"]:
            artifact["meta"]["bundle_item_label"] = child_label
            artifact["meta"]["asset_target"] = child_task.get("asset_target", {})
            artifacts.append(artifact)
        logs.append(f"Generated bundle item {index}/{len(bundle_tasks)}: {child_label}")

    return {
        "status": "success",
        "skill": "ip-image-skill",
        "mode": "character_asset_bundle",
        "task_id": task.get("task_id", "character_asset_bundle"),
        "artifacts": artifacts,
        "logs": logs,
        "handoff": {
            "bundle_items": child_tasks,
        },
    }


def _run_ip_asset_pack(task: Dict, output_dir: str, client: PoYoClient) -> Dict:
    child_tasks = build_ip_asset_pack_tasks(task, output_dir)
    if not child_tasks:
        raise ValueError("ip_asset_pack requires at least one character, scene, or standalone prop")

    artifacts: List[Dict] = []
    logs: List[str] = []
    children: List[Dict] = []

    for index, child_task in enumerate(child_tasks, start=1):
        child_result = _run_text_to_image(child_task, output_dir, client)
        label = child_task.get("bundle_item_label") or os.path.splitext(child_task.get("filename", f"asset_{index:02d}.jpg"))[0]
        for artifact in child_result["artifacts"]:
            artifact["meta"]["asset_pack_label"] = label
            artifact["meta"]["asset_target"] = child_task.get("asset_target", {})
            artifacts.append(artifact)
        children.append(
            {
                "label": label,
                "mode": child_task.get("mode"),
                "filename": child_task.get("filename"),
                "task_id": child_result["task_id"],
                "asset_target": child_task.get("asset_target", {}),
            }
        )
        logs.append(f"Generated asset pack item {index}/{len(child_tasks)}: {label}")

    return {
        "status": "success",
        "skill": "ip-image-skill",
        "mode": "ip_asset_pack",
        "task_id": task.get("task_id", "ip_asset_pack"),
        "artifacts": artifacts,
        "logs": logs,
        "handoff": {
            "items": children,
        },
    }


def _load_presets() -> Dict[str, Dict]:
    assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    preset_path = os.path.join(assets_dir, "enhance_presets.json")
    with open(preset_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _collect_reference_image_urls(task: Dict, client: PoYoClient) -> List[str]:
    image_urls = list(task.get("reference_image_urls") or [])
    local_paths = list(task.get("style_reference_paths") or [])
    local_paths.extend(task.get("reference_image_paths") or [])
    for path in local_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        upload = client.upload_file_stream(
            path,
            upload_path="image-skill/references",
            file_name=os.path.basename(path),
        )
        image_urls.append(upload["file_url"])
    return image_urls


def _cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="Path to a task JSON file")
    args = parser.parse_args()

    with open(args.task, "r", encoding="utf-8") as fh:
        task = json.load(fh)

    result = run_task(task)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
