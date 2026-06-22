import argparse
import json
import os
from typing import Dict

try:
    from .continuity import build_continuity_bible
    from .shot_plan import build_i2v_prompts, build_shot_plan, build_t2v_prompts
    from .video_handoff import build_edit_decision_list, build_video_handoff
except ImportError:
    from continuity import build_continuity_bible
    from shot_plan import build_i2v_prompts, build_shot_plan, build_t2v_prompts
    from video_handoff import build_edit_decision_list, build_video_handoff


def run_task(task: Dict) -> Dict:
    mode = task.get("mode", "build_video_handoff")
    output_dir = task.get("output_dir") or os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    if mode == "build_continuity_bible":
        bible = build_continuity_bible(task)
        path = os.path.join(output_dir, task.get("continuity_filename", "continuity_bible.json"))
        _write_json(path, bible)
        return _result(mode, {"continuity_bible": bible}, path, "continuity_bible")

    if mode == "build_video_handoff":
        handoff = build_video_handoff(task)
        path = os.path.join(output_dir, task.get("handoff_filename", "video_handoff.json"))
        _write_json(path, handoff)
        return _result(mode, {"video_handoff": handoff}, path, "video_handoff")

    if mode == "build_shot_plan":
        bible = build_continuity_bible(task)
        shots = build_shot_plan(task, bible)
        path = os.path.join(output_dir, task.get("shot_plan_filename", "shot_plan.json"))
        _write_json(path, {"continuity_bible": bible, "shots": shots})
        return _result(mode, {"continuity_bible": bible, "shots": shots}, path, "shot_plan")

    if mode == "build_i2v_prompts":
        bible = build_continuity_bible(task)
        shots = task.get("shots") or build_shot_plan(task, bible)
        prompts = build_i2v_prompts(shots)
        path = os.path.join(output_dir, task.get("i2v_filename", "i2v_prompts.json"))
        _write_json(path, {"i2v_prompts": prompts})
        return _result(mode, {"i2v_prompts": prompts}, path, "i2v_prompts")

    if mode == "build_t2v_prompts":
        bible = build_continuity_bible(task)
        shots = task.get("shots") or build_shot_plan(task, bible)
        prompts = build_t2v_prompts(shots)
        path = os.path.join(output_dir, task.get("t2v_filename", "t2v_prompts.json"))
        _write_json(path, {"t2v_prompts": prompts})
        return _result(mode, {"t2v_prompts": prompts}, path, "t2v_prompts")

    if mode == "build_edit_decision_list":
        bible = build_continuity_bible(task)
        shots = task.get("shots") or build_shot_plan(task, bible)
        edl = build_edit_decision_list(task, shots)
        path = os.path.join(output_dir, task.get("edl_filename", "edit_decision_list.json"))
        _write_json(path, edl)
        return _result(mode, {"edit_decision_list": edl}, path, "edit_decision_list")

    raise ValueError(
        "mode must be one of: build_continuity_bible, build_video_handoff, build_shot_plan, "
        "build_i2v_prompts, build_t2v_prompts, build_edit_decision_list"
    )


def _result(mode: str, handoff: Dict, path: str, kind: str) -> Dict:
    return {
        "status": "success",
        "skill": "ip-video-skill",
        "mode": mode,
        "artifacts": [{"type": "json", "path": path, "meta": {"kind": kind}}],
        "handoff": handoff,
        "logs": [f"{kind} written"],
    }


def _write_json(path: str, payload: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="Path to a task JSON file")
    args = parser.parse_args()
    with open(args.task, "r", encoding="utf-8") as fh:
        task = json.load(fh)
    print(json.dumps(run_task(task), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
