import argparse
import json
import os
from typing import Dict

try:
    from .clip_plan import build_clip_plan, build_clip_prompts
    from .config import load_video_provider_config
    from .continuity import build_continuity_bible
    from .episode_readiness import build_episode_readiness_report
    from .asset_manifest import build_asset_manifest_review, build_asset_manifest_template, scan_asset_manifest_directory
    from .shot_plan import build_i2v_prompts, build_shot_plan, build_t2v_prompts
    from .video_provider import prepare_video_generation_request, run_video_generation
    from .preflight_video_episode import preflight_video_generation
    from .video_sequence import run_video_sequence
    from .video_handoff import build_edit_decision_list, build_video_handoff
except ImportError:
    from clip_plan import build_clip_plan, build_clip_prompts
    from config import load_video_provider_config
    from continuity import build_continuity_bible
    from episode_readiness import build_episode_readiness_report
    from asset_manifest import build_asset_manifest_review, build_asset_manifest_template, scan_asset_manifest_directory
    from shot_plan import build_i2v_prompts, build_shot_plan, build_t2v_prompts
    from video_provider import prepare_video_generation_request, run_video_generation
    from preflight_video_episode import preflight_video_generation
    from video_sequence import run_video_sequence
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

    if mode == "build_asset_manifest_template":
        handoff = task.get("video_handoff") or task.get("handoff")
        bible = task.get("continuity_bible")
        if not handoff:
            handoff = build_video_handoff(task)
        if not bible:
            bible = handoff.get("continuity_bible") or build_continuity_bible(task)
        manifest = build_asset_manifest_template(task, continuity_bible=bible, video_handoff=handoff)
        path = os.path.join(output_dir, task.get("asset_manifest_template_filename", "asset_manifest_template.json"))
        _write_json(path, manifest)
        return _result(mode, {"asset_manifest_template": manifest}, path, "asset_manifest_template")

    if mode == "scan_asset_manifest_directory":
        handoff = task.get("video_handoff") or task.get("handoff")
        bible = task.get("continuity_bible")
        if not handoff:
            handoff = build_video_handoff(task)
        if not bible:
            bible = handoff.get("continuity_bible") or build_continuity_bible(task)
        manifest = scan_asset_manifest_directory(task, continuity_bible=bible, video_handoff=handoff)
        path = os.path.join(output_dir, task.get("asset_manifest_scan_filename", "asset_manifest_scan.json"))
        _write_json(path, manifest)
        return _result(mode, {"asset_manifest": manifest}, path, "asset_manifest_scan")

    if mode == "review_asset_manifest":
        review_task = dict(task)
        if not review_task.get("asset_manifest") and not review_task.get("asset_manifest_path") and (
            review_task.get("asset_dir") or review_task.get("asset_dirs") or review_task.get("asset_roots")
        ):
            handoff = review_task.get("video_handoff") or review_task.get("handoff") or build_video_handoff(review_task)
            bible = review_task.get("continuity_bible") or handoff.get("continuity_bible") or build_continuity_bible(review_task)
            review_task["asset_manifest"] = scan_asset_manifest_directory(review_task, continuity_bible=bible, video_handoff=handoff)
        review = build_asset_manifest_review(review_task)
        path = os.path.join(output_dir, task.get("asset_manifest_review_filename", "asset_manifest_review.json"))
        _write_json(path, review)
        return _result(mode, {"asset_manifest_review": review}, path, "asset_manifest_review")

    if mode == "build_shot_plan":
        bible = build_continuity_bible(task)
        shots = build_shot_plan(task, bible)
        path = os.path.join(output_dir, task.get("shot_plan_filename", "shot_plan.json"))
        _write_json(path, {"continuity_bible": bible, "shots": shots})
        return _result(mode, {"continuity_bible": bible, "shots": shots}, path, "shot_plan")

    if mode == "build_clip_plan":
        bible = build_continuity_bible(task)
        shots = task.get("shots") or build_shot_plan(task, bible)
        clips = build_clip_plan(task, shots, bible)
        path = os.path.join(output_dir, task.get("clip_plan_filename", "clip_plan.json"))
        _write_json(path, {"continuity_bible": bible, "clip_plan": clips, "clip_prompts": build_clip_prompts(clips)})
        return _result(mode, {"continuity_bible": bible, "clip_plan": clips}, path, "clip_plan")

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

    if mode == "episode_readiness":
        config = load_video_provider_config()
        report = build_episode_readiness_report(task, config)
        path = os.path.join(output_dir, task.get("episode_readiness_filename", "episode_readiness_report.json"))
        _write_json(path, report)
        return _result(mode, {"episode_readiness_report": report}, path, "episode_readiness_report")

    if mode == "preflight_video_generation":
        config = load_video_provider_config()
        report = preflight_video_generation(task, config)
        path = os.path.join(output_dir, task.get("preflight_filename", "video_preflight_report.json"))
        _write_json(path, report)
        return _result(mode, {"preflight_report": report}, path, "video_preflight_report")
    if mode == "prepare_video_generation":
        config = load_video_provider_config()
        request = prepare_video_generation_request(task, config)
        path = os.path.join(output_dir, task.get("provider_request_filename", "video_provider_request.json"))
        _write_json(path, request)
        return _result(mode, {"provider_request": request}, path, "video_provider_request")

    if mode == "run_video_generation":
        config = load_video_provider_config()
        result = run_video_generation(task, config)
        path = os.path.join(output_dir, task.get("provider_manifest_filename", "video_provider_manifest.json"))
        _write_json(path, result)
        response = _result(mode, {"provider_result": result}, path, "video_provider_manifest")
        response["artifacts"] = list(result.get("artifacts", [])) + response["artifacts"]
        return response

    if mode == "run_video_sequence":
        config = load_video_provider_config()
        result = run_video_sequence(task, config)
        path = os.path.join(output_dir, task.get("sequence_manifest_filename", "video_sequence_manifest.json"))
        _write_json(path, result)
        response = _result(mode, {"sequence_result": result}, path, "video_sequence_manifest")
        response["artifacts"] = [
            {"type": "video", "path": path, "meta": {"kind": "sequence_clip"}}
            for path in result.get("generated_paths", [])
        ] + response["artifacts"]
        return response

    raise ValueError(
        "mode must be one of: build_continuity_bible, build_video_handoff, build_shot_plan, build_clip_plan, "
        "build_asset_manifest_template, scan_asset_manifest_directory, review_asset_manifest, episode_readiness, build_i2v_prompts, build_t2v_prompts, build_edit_decision_list, "
        "preflight_video_generation, prepare_video_generation, run_video_generation, run_video_sequence"
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
