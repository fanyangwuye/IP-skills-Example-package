import argparse
import json
import os
from datetime import date
from typing import Dict, List, Optional

try:
    from .blueprint_validate import validate_blueprint
    from .license_gate import check_license, gate
except ImportError:
    from blueprint_validate import validate_blueprint
    from license_gate import check_license, gate


def run_task(task: Dict) -> Dict:
    mode = task.get("mode", "build_blueprint")
    output_dir = task.get("output_dir") or os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    if mode == "check_license":
        return _run_check_license(task)
    if mode == "build_character_handoff":
        return _run_build_character_handoff(task, output_dir)
    if mode == "build_blueprint":
        return _run_build_blueprint(task, output_dir)
    raise ValueError("mode must be one of: check_license, build_blueprint, build_character_handoff")


def _run_check_license(task: Dict) -> Dict:
    license_record = _load_license_record(task.get("ip_id"), task.get("license_path"))
    requested_target = task["target"]
    commercial_use = bool(task.get("commercial_use", False))
    today = _parse_today(task.get("today"))
    ok, reasons = check_license(
        license_record,
        requested_target=requested_target,
        commercial_use=commercial_use,
        today=today,
    )
    return {
        "status": "success" if ok else "blocked",
        "skill": "ip-copy-skill",
        "mode": "check_license",
        "task_id": task.get("task_id", "check_license"),
        "handoff": {
            "license_ok": ok,
            "license_record": license_record,
            "reasons": reasons,
        },
        "logs": ["license passed" if ok else "license blocked"],
    }


def _run_build_character_handoff(task: Dict, output_dir: str) -> Dict:
    handoff = _build_image_handoff(task)
    out_path = os.path.join(output_dir, task.get("handoff_filename", "character_handoff.json"))
    _write_json(out_path, handoff)
    return {
        "status": "success",
        "skill": "ip-copy-skill",
        "mode": "build_character_handoff",
        "task_id": task.get("task_id", "build_character_handoff"),
        "artifacts": [
            {
                "type": "json",
                "path": out_path,
                "meta": {"kind": "image_handoff"},
            }
        ],
        "handoff": handoff,
        "logs": ["character handoff written"],
    }


def _run_build_blueprint(task: Dict, output_dir: str) -> Dict:
    license_record = _load_license_record(task.get("ip_id"), task.get("license_path"))
    target = task["target"]
    commercial_use = bool(task.get("commercial_use", False))
    gate(license_record, target, commercial_use, today=_parse_today(task.get("today")))

    scene_cards = task.get("scene_cards") or []
    if not scene_cards:
        raise ValueError("build_blueprint requires a non-empty scene_cards list")

    total_duration_sec = float(task["total_duration_sec"])
    segments = _build_segments(scene_cards, total_duration_sec)
    blueprint = {
        "blueprint_id": task.get("blueprint_id", f"{task['ip_id']}_blueprint"),
        "ip_id": task["ip_id"],
        "target": target,
        "title": task.get("title", ""),
        "source_text": task.get("source_text", ""),
        "total_duration_sec": total_duration_sec,
        "global_style": task.get("global_style", {}),
        "segments": segments,
        "license_ref": {
            "license_id": (license_record or {}).get("license_id", ""),
            "rights_holder": (license_record or {}).get("rights_holder", ""),
        },
    }

    ok, errors = validate_blueprint(blueprint)
    if not ok:
        raise RuntimeError("蓝图校验失败：" + "；".join(errors))

    image_handoff = _build_image_handoff(task, blueprint)
    result = {
        "blueprint": blueprint,
        "image_handoff": image_handoff,
    }

    blueprint_path = os.path.join(output_dir, task.get("blueprint_filename", "blueprint.json"))
    handoff_path = os.path.join(output_dir, task.get("handoff_filename", "image_handoff.json"))
    _write_json(blueprint_path, blueprint)
    _write_json(handoff_path, image_handoff)

    return {
        "status": "success",
        "skill": "ip-copy-skill",
        "mode": "build_blueprint",
        "task_id": task.get("task_id", blueprint["blueprint_id"]),
        "artifacts": [
            {"type": "json", "path": blueprint_path, "meta": {"kind": "blueprint"}},
            {"type": "json", "path": handoff_path, "meta": {"kind": "image_handoff"}},
        ],
        "handoff": result,
        "logs": ["blueprint built and validated", "image handoff built"],
    }


def _build_segments(scene_cards: List[Dict], total_duration_sec: float) -> List[Dict]:
    durations = _normalize_durations(scene_cards, total_duration_sec)
    start = 0.0
    segments: List[Dict] = []
    for index, (card, duration_sec) in enumerate(zip(scene_cards, durations), start=1):
        end = round(start + duration_sec, 3)
        segment = {
            "index": index,
            "start_sec": round(start, 3),
            "end_sec": end,
            "visual": card["visual"],
            "voiceover": card["voiceover"],
            "music_cue": card.get("music_cue", ""),
            "transition": card.get("transition", "cut"),
            "subtitle": card.get("subtitle", card["voiceover"]),
            "asset_goal": card.get("asset_goal", {}),
        }
        segments.append(segment)
        start = end

    if segments:
        segments[-1]["end_sec"] = total_duration_sec
    return segments


def _normalize_durations(scene_cards: List[Dict], total_duration_sec: float) -> List[float]:
    explicit = [float(card.get("duration_sec", 0) or 0) for card in scene_cards]
    missing_indexes = [index for index, value in enumerate(explicit) if value <= 0]
    used = sum(value for value in explicit if value > 0)
    remaining = max(total_duration_sec - used, 0.0)

    if missing_indexes:
        share = remaining / len(missing_indexes) if missing_indexes else 0.0
        for index in missing_indexes:
            explicit[index] = share

    total = sum(explicit)
    if total <= 0:
        share = total_duration_sec / len(scene_cards)
        return [share for _ in scene_cards]

    scale = total_duration_sec / total
    return [round(value * scale, 3) for value in explicit]


def _build_image_handoff(task: Dict, blueprint: Optional[Dict] = None) -> Dict:
    image_tasks = []
    if blueprint:
        for segment in blueprint["segments"]:
            image_tasks.append(
                {
                    "mode": "text_to_image",
                    "ip_id": task.get("ip_id"),
                    "asset_kind": segment.get("asset_goal", {}).get("type", "scene_image"),
                    "creative_goal": segment.get("asset_goal", {}).get("purpose", "blueprint scene generation"),
                    "character_profile": task.get("character_sheet", {}).get("character_profile", {}),
                    "identity_anchors": task.get("character_sheet", {}).get("identity_anchors", []),
                    "continuity_rules": task.get("character_sheet", {}).get("continuity_rules", []),
                    "interaction_state": task.get("character_sheet", {}).get("interaction_state", {}),
                    "asset_target": segment.get("asset_goal", {}),
                    "scene": segment["visual"],
                    "prompt": segment["visual"],
                    "emotion": segment.get("asset_goal", {}).get("expression", ""),
                    "output_dir": task.get("image_output_dir", ""),
                }
            )

    return {
        "character_sheet": task.get("character_sheet", {}),
        "asset_bundle": task.get("asset_bundle", []),
        "image_tasks": image_tasks,
        "source_summary": {
            "title": task.get("title", ""),
            "source_text": task.get("source_text", ""),
            "creative_direction": task.get("creative_direction", {}),
        },
    }


def _load_license_record(ip_id: Optional[str], license_path: Optional[str]) -> Optional[Dict]:
    if license_path:
        if not os.path.exists(license_path):
            raise FileNotFoundError(license_path)
        with open(license_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    if not ip_id:
        return None
    default_path = os.path.join(os.path.dirname(__file__), "..", "references", "licenses", f"{ip_id}.json")
    if not os.path.exists(default_path):
        return None
    with open(default_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: str, payload: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _parse_today(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    year, month, day = (int(part) for part in value.split("-"))
    return date(year, month, day)


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

