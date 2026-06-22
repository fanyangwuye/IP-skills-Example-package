import argparse
import importlib.util
import json
import os
import sys
from typing import Dict, List


def _load_module(module_name: str, path: str):
    module_dir = os.path.dirname(path)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_copy_to_image(handoff_path: str, output_dir: str) -> Dict:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image_skill_path = os.path.join(
        repo_root, "skills", "ip-image-skill", "scripts", "image_skill.py"
    )
    image_module = _load_module("ip_image_skill_entry", image_skill_path)

    with open(handoff_path, "r", encoding="utf-8") as fh:
        handoff = json.load(fh)

    image_tasks = handoff.get("image_tasks") or []
    if not image_tasks:
        raise ValueError("image_handoff.json contains no image_tasks")

    os.makedirs(output_dir, exist_ok=True)

    results: List[Dict] = []
    for index, task in enumerate(image_tasks, start=1):
        filename = f"image_task_{index:02d}.jpg"
        enriched = dict(task)
        enriched["output_dir"] = output_dir
        enriched["filename"] = filename
        result = image_module.run_task(enriched)
        results.append(result)

    manifest = {
        "status": "success",
        "handoff_path": handoff_path,
        "n_image_tasks": len(image_tasks),
        "results": results,
    }
    manifest_path = os.path.join(output_dir, "copy_to_image_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return manifest


def _cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", required=True, help="Path to image_handoff.json")
    parser.add_argument("--out", required=True, help="Output directory for generated images")
    args = parser.parse_args()

    result = run_copy_to_image(args.handoff, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
