from typing import Dict, List, Optional

try:
    from .asset_manifest import build_asset_manifest_review, scan_asset_manifest_directory
    from .config import VideoProviderConfig, load_video_provider_config
    from .preflight_video_episode import preflight_video_generation
    from .video_handoff import build_video_handoff
except ImportError:
    from asset_manifest import build_asset_manifest_review, scan_asset_manifest_directory
    from config import VideoProviderConfig, load_video_provider_config
    from preflight_video_episode import preflight_video_generation
    from video_handoff import build_video_handoff


ALL_PURPOSE_POLICIES = {"all_purpose_reference", "all_purpose_reference_only"}


def build_episode_readiness_report(task: Dict, config: Optional[VideoProviderConfig] = None) -> Dict:
    config = config or load_video_provider_config()
    handoff = _ensure_handoff(task)
    readiness_task = dict(task)
    readiness_task["video_handoff"] = handoff
    readiness_task.setdefault("reference_policy", _reference_policy(task, handoff))

    asset_review = _build_asset_review(readiness_task, handoff)
    if asset_review and not readiness_task.get("asset_manifest") and asset_review.get("scan_report"):
        # The detailed manifest is already represented by asset_review; preflight still uses explicit refs when present.
        pass

    preflight = preflight_video_generation(readiness_task, config)
    checks = [
        _check("video_handoff", bool(handoff.get("clip_plan")), _handoff_summary(handoff)),
        _check("storyboard_quality", _storyboard_gate_ok(handoff), _storyboard_summary(handoff)),
        _check("prompt_packet_v1", _named_preflight_ok(preflight, "prompt_packet_v1"), _named_preflight_summary(preflight, "prompt_packet_v1")),
        _check("reference_policy", _reference_policy_ok(readiness_task, preflight), _reference_policy_summary(readiness_task, preflight)),
        _check("asset_manifest", _asset_gate_ok(asset_review), _asset_summary(asset_review)),
        _check("model_policy", _model_policy_ok(readiness_task, config, preflight), _model_policy_summary(readiness_task, config, preflight)),
        _check("continuation_strategy", _continuation_ok(handoff), _continuation_summary(handoff)),
        _check("preflight_video_generation", preflight.get("status") == "pass", _preflight_summary(preflight)),
    ]
    blockers = _collect_blockers(checks, asset_review, preflight)
    warnings = _collect_warnings(asset_review, preflight)
    return {
        "episode_readiness_version": "1.0",
        "status": "ready_for_single_clip_test" if not blockers else "blocked",
        "project_title": handoff.get("source_title") or task.get("title") or task.get("project_title") or "PROJECT_TITLE_HERE",
        "provider": config.provider,
        "model": _selected_model(task, config),
        "reference_policy": readiness_task.get("reference_policy"),
        "summary": {
            "clip_count": len(handoff.get("clip_plan") or []),
            "shot_count": len(handoff.get("shots") or []),
            "check_count": len(checks),
            "failed_check_count": len([item for item in checks if item["status"] == "fail"]),
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
        },
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "asset_review": asset_review,
        "preflight_report": preflight,
    }


def _ensure_handoff(task: Dict) -> Dict:
    handoff = task.get("video_handoff") or task.get("handoff")
    if handoff:
        if not isinstance(handoff, dict):
            raise ValueError("episode readiness video_handoff must be an object")
        return handoff
    return build_video_handoff(task)


def _build_asset_review(task: Dict, handoff: Dict) -> Dict:
    review_task = dict(task)
    if not review_task.get("asset_manifest") and not review_task.get("asset_manifest_path") and (
        review_task.get("asset_dir") or review_task.get("asset_dirs") or review_task.get("asset_roots")
    ):
        review_task["asset_manifest"] = scan_asset_manifest_directory(review_task, continuity_bible=handoff.get("continuity_bible"), video_handoff=handoff)
        task["asset_manifest"] = review_task["asset_manifest"]
    if review_task.get("asset_manifest") or review_task.get("asset_manifest_path"):
        return build_asset_manifest_review(review_task)
    return {
        "status": "needs_assets",
        "summary": {"matched_count": 0, "missing_count": 0, "placeholder_count": 0, "fragile_path_count": 0, "unassigned_asset_count": 0, "error_count": 1, "warning_count": 0},
        "action_items": [{"priority": "blocker", "action": "provide_asset_manifest_or_asset_dir"}],
        "errors": ["asset manifest or asset_dir is required before paid/live generation"],
        "warnings": [],
    }


def _check(name: str, ok: bool, detail) -> Dict:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


def _handoff_summary(handoff: Dict) -> Dict:
    return {"clip_count": len(handoff.get("clip_plan") or []), "shot_count": len(handoff.get("shots") or [])}


def _storyboard_summary(handoff: Dict) -> Dict:
    quality = (handoff.get("quality_checks") or {}).get("storyboard_quality_summary") or {}
    clips = []
    for clip in handoff.get("clip_plan") or []:
        clips.append({"clip_id": clip.get("clip_id"), "status": (clip.get("storyboard_quality") or {}).get("status", "unknown")})
    return {"summary": quality, "clips": clips}


def _storyboard_gate_ok(handoff: Dict) -> bool:
    clips = handoff.get("clip_plan") or []
    return bool(clips) and all((clip.get("storyboard_quality") or {}).get("status") != "fail" for clip in clips)


def _named_preflight_ok(preflight: Dict, name: str) -> bool:
    checks = [item for item in preflight.get("checks") or [] if item.get("name") == name]
    return bool(checks) and all(item.get("status") == "pass" for item in checks)


def _named_preflight_summary(preflight: Dict, name: str) -> Dict:
    checks = [item for item in preflight.get("checks") or [] if item.get("name") == name]
    return {"pass_count": len([item for item in checks if item.get("status") == "pass"]), "fail_count": len([item for item in checks if item.get("status") != "pass"]), "checked_count": len(checks)}


def _reference_policy(task: Dict, handoff: Dict) -> str:
    policy = str(task.get("reference_policy") or task.get("reference_mode") or "").strip()
    if policy:
        return policy
    for clip in handoff.get("clip_plan") or []:
        binding = clip.get("reference_binding") or {}
        policy = str(binding.get("reference_policy") or binding.get("reference_mode") or "").strip()
        if policy:
            return policy
    return "all_purpose_reference"


def _reference_policy_ok(task: Dict, preflight: Dict) -> bool:
    policy = str(task.get("reference_policy") or "").strip()
    if policy in ALL_PURPOSE_POLICIES:
        return _named_preflight_ok(preflight, "all_purpose_reference_urls")
    return True


def _reference_policy_summary(task: Dict, preflight: Dict) -> Dict:
    return {"reference_policy": task.get("reference_policy"), "all_purpose_reference_urls": _named_preflight_summary(preflight, "all_purpose_reference_urls")}


def _asset_gate_ok(asset_review: Dict) -> bool:
    return bool(asset_review) and asset_review.get("status") == "ready_for_preflight"


def _asset_summary(asset_review: Dict) -> Dict:
    return asset_review.get("summary", {}) if asset_review else {}


def _selected_model(task: Dict, config: VideoProviderConfig) -> str:
    if task.get("model"):
        return str(task["model"])
    if config.default_model:
        return config.default_model
    return "seedance-2" if config.provider == "poyo_video" else "offline-preview"


def _model_policy_ok(task: Dict, config: VideoProviderConfig, preflight: Dict) -> bool:
    if config.provider == "poyo_video" or task.get("provider") == "poyo_video":
        return _named_preflight_ok(preflight, "paid_model_policy")
    return True


def _model_policy_summary(task: Dict, config: VideoProviderConfig, preflight: Dict) -> Dict:
    return {"provider": config.provider, "model": _selected_model(task, config), "allow_fast_model": bool(task.get("allow_fast_model")), "paid_model_policy": _named_preflight_summary(preflight, "paid_model_policy")}


def _continuation_ok(handoff: Dict) -> bool:
    clips = handoff.get("clip_plan") or []
    if len(clips) <= 1:
        return True
    return all((clip.get("continuity_state") or {}).get("previous_end_state") is not None for clip in clips[1:])


def _continuation_summary(handoff: Dict) -> Dict:
    clips = handoff.get("clip_plan") or []
    return {
        "clip_count": len(clips),
        "bridge_clip_count": len(handoff.get("bridge_clips") or []),
        "clips_with_previous_frame": len([clip for clip in clips if clip.get("previous_clip_end_frame")]),
        "handoffs": [
            {"clip_id": clip.get("clip_id"), "previous_end_state": (clip.get("continuity_state") or {}).get("previous_end_state"), "next_handoff": (clip.get("continuity_state") or {}).get("next_handoff")}
            for clip in clips
        ],
    }


def _preflight_summary(preflight: Dict) -> Dict:
    return {"status": preflight.get("status"), "checked_count": preflight.get("checked_count"), "error_count": len(preflight.get("errors") or []), "warning_count": len(preflight.get("warnings") or [])}


def _collect_blockers(checks: List[Dict], asset_review: Dict, preflight: Dict) -> List[Dict]:
    blockers = []
    for check in checks:
        if check.get("status") == "fail":
            blockers.append({"source": "readiness_check", "name": check.get("name"), "detail": check.get("detail")})
    for item in asset_review.get("action_items") or []:
        if item.get("priority") == "blocker":
            blockers.append({"source": "asset_review", **item})
    for error in preflight.get("errors") or []:
        blockers.append({"source": "preflight", "message": error})
    return blockers


def _collect_warnings(asset_review: Dict, preflight: Dict) -> List[Dict]:
    warnings = []
    for item in asset_review.get("action_items") or []:
        if item.get("priority") == "review":
            warnings.append({"source": "asset_review", **item})
    for warning in preflight.get("warnings") or []:
        warnings.append({"source": "preflight", "message": warning})
    return warnings