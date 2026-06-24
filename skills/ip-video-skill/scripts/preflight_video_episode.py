import argparse
import json
from typing import Dict, List, Optional, Tuple

try:
    from .asset_manifest import validate_asset_manifest
    from .config import VideoProviderConfig, load_video_provider_config
    from .spatial_templates import high_risk_spatial_template_text
    from .video_provider import PROMPT_PACKET_REQUIRED_SECTIONS, prepare_video_generation_request
except ImportError:
    from asset_manifest import validate_asset_manifest
    from config import VideoProviderConfig, load_video_provider_config
    from spatial_templates import high_risk_spatial_template_text
    from video_provider import PROMPT_PACKET_REQUIRED_SECTIONS, prepare_video_generation_request


FORBIDDEN_DRIFT_PHRASES = [
    "BGM cue",
    "key subtitle",
    "music bed",
    "背景音乐响起",
    "字幕显示",
    "出现字幕",
    "title card appears",
]

NO_TEXT_AUDIO_MARKERS = [
    "无字幕",
    "no subtitles",
    "禁止字幕",
    "无水印",
    "no watermark",
    "无标题卡",
    "no title card",
    "无假文字",
    "no fake text",
    "无歌曲",
    "no songs",
    "无音乐铺底",
    "no music beds",
]

ALL_PURPOSE_POLICIES = {"all_purpose_reference", "all_purpose_reference_only"}


def preflight_video_generation(task: Dict, config: Optional[VideoProviderConfig] = None) -> Dict:
    """Build dry provider requests and report blockers before any paid video call."""
    config = config or load_video_provider_config()
    manifest_errors, manifest_warnings = validate_asset_manifest(task)
    requests, build_errors = _build_requests(task, config)
    checks = []
    errors = list(manifest_errors) + list(build_errors)
    warnings = list(manifest_warnings)

    for index, request in enumerate(requests, start=1):
        unit_label = request.get("clip_id") or request.get("shot_id") or request.get("unit_id") or f"unit_{index}"
        unit_checks, unit_errors, unit_warnings = _check_request(task, request, unit_label)
        checks.extend(unit_checks)
        errors.extend(unit_errors)
        warnings.extend(unit_warnings)

    return {
        "status": "pass" if not errors else "fail",
        "mode": "preflight_video_generation",
        "checked_count": len(requests),
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def _build_requests(task: Dict, config: VideoProviderConfig) -> Tuple[List[Dict], List[str]]:
    if task.get("provider_request"):
        return [task["provider_request"]], []
    if task.get("provider_requests"):
        return list(task["provider_requests"]), []

    handoff = task.get("video_handoff") or task.get("handoff") or {}
    if task.get("clip"):
        clips = [task["clip"]]
    elif not isinstance(handoff, dict):
        return [], ["preflight video_handoff must be an object with clip_plan, not a placeholder string"]
    else:
        clips = _select_clips(handoff.get("clip_plan") or [], task)
    if not clips:
        return [], ["preflight requires provider_request, provider_requests, clip, or video_handoff.clip_plan"]

    max_clips = int(task.get("max_clips") or len(clips))
    requests = []
    errors = []
    for clip in clips[:max_clips]:
        request_task = dict(task)
        request_task.pop("provider_request", None)
        request_task.pop("provider_requests", None)
        request_task["clip"] = clip
        request_task["dry_run"] = True
        try:
            requests.append(prepare_video_generation_request(request_task, config))
        except Exception as exc:  # noqa: BLE001 - preflight must report all blockers, not stop at the first one.
            label = clip.get("clip_id") or ",".join(clip.get("shot_ids") or []) or "unknown_clip"
            errors.append(f"{label}: provider request build failed: {exc}")
    return requests, errors

def _select_clips(clips: List[Dict], task: Dict) -> List[Dict]:
    clip_id = task.get("clip_id")
    if clip_id:
        for clip in clips:
            if clip.get("clip_id") == clip_id:
                return [clip]
        return []
    if task.get("clip_index") is not None:
        try:
            index = int(task.get("clip_index") or 1)
        except (TypeError, ValueError):
            return []
        if index < 1 or index > len(clips):
            return []
        return [clips[index - 1]]
    return clips

def _check_request(task: Dict, request: Dict, unit_label: str) -> Tuple[List[Dict], List[str], List[str]]:
    checks = []
    errors = []
    warnings = []

    prompt = str(request.get("prompt") or "")
    provider = request.get("provider") or task.get("provider")
    model = str(request.get("model") or task.get("model") or "")

    missing_sections = [section for section in PROMPT_PACKET_REQUIRED_SECTIONS if section not in prompt]
    _add_check(checks, unit_label, "prompt_packet_v1", not missing_sections, missing_sections)
    if missing_sections:
        errors.append(f"{unit_label}: Prompt Packet V1 missing sections: {', '.join(missing_sections)}")

    shot_ids = [item for item in request.get("shot_ids") or [] if item]
    execution_map = request.get("storyboard_execution_map") or []
    mapped_ids = [item.get("storyboard_shot_id") for item in execution_map if item.get("storyboard_shot_id")]
    storyboard_ok = bool(execution_map) and (not shot_ids or mapped_ids == shot_ids)
    _add_check(checks, unit_label, "storyboard_execution_map", storyboard_ok, {"shot_ids": shot_ids, "mapped_ids": mapped_ids})
    if not execution_map:
        errors.append(f"{unit_label}: storyboard_execution_map is missing")
    elif shot_ids and mapped_ids != shot_ids:
        errors.append(f"{unit_label}: storyboard_execution_map does not exactly match shot_ids")

    storyboard_mode = str(request.get("storyboard_mode") or "production").strip().lower()
    draft_ok = storyboard_mode != "draft"
    _add_check(checks, unit_label, "storyboard_mode_production", draft_ok, storyboard_mode)
    if not draft_ok:
        errors.append(f"{unit_label}: storyboard_mode=draft is planning-only; approve and rebuild production storyboard mapping before paid generation")

    storyboard_quality = request.get("storyboard_quality") or {}
    quality_status = str(storyboard_quality.get("status") or "unknown")
    quality_ok = quality_status != "fail"
    _add_check(checks, unit_label, "storyboard_quality", quality_ok, storyboard_quality)
    if quality_status == "fail":
        issue_codes = ", ".join(item.get("code", "") for item in storyboard_quality.get("issues") or [])
        errors.append(f"{unit_label}: storyboard_quality failed before paid generation: {issue_codes}")
    elif quality_status == "warn":
        issue_codes = ", ".join(item.get("code", "") for item in storyboard_quality.get("issues") or [])
        warnings.append(f"{unit_label}: storyboard_quality warning requires human review: {issue_codes}")
    elif quality_status == "unknown":
        warnings.append(f"{unit_label}: storyboard_quality report is missing; rebuild handoff with current ip-video-skill before paid generation")

    all_purpose = _uses_all_purpose_reference(task, request)
    if all_purpose:
        image_urls = request.get("image_urls") or []
        reference_image_urls = request.get("reference_image_urls") or []
        ok = not image_urls and bool(reference_image_urls)
        _add_check(checks, unit_label, "all_purpose_reference_urls", ok, {"image_urls": len(image_urls), "reference_image_urls": len(reference_image_urls)})
        if image_urls:
            errors.append(f"{unit_label}: all-purpose reference mode must not include image_urls")
        if not reference_image_urls:
            errors.append(f"{unit_label}: all-purpose reference mode requires reference_image_urls")
        if "全能参考模式已锁定" not in prompt:
            errors.append(f"{unit_label}: prompt is missing explicit all-purpose reference binding text")

    if provider == "poyo_video":
        fast_allowed = bool(task.get("allow_fast_model"))
        model_ok = model != "seedance-2-fast" or fast_allowed
        _add_check(checks, unit_label, "paid_model_policy", model_ok, {"model": model, "allow_fast_model": fast_allowed})
        if not model_ok:
            errors.append(f"{unit_label}: seedance-2-fast is not allowed unless allow_fast_model=true")
        elif model and model != "seedance-2" and not fast_allowed:
            warnings.append(f"{unit_label}: non-default paid model selected: {model}")

    duration = request.get("duration_sec")
    if duration is not None:
        try:
            duration_value = float(duration)
        except (TypeError, ValueError):
            duration_value = -1
        duration_ok = 0 < duration_value <= 15
        _add_check(checks, unit_label, "duration_limit", duration_ok, duration)
        if not duration_ok:
            errors.append(f"{unit_label}: duration must be greater than 0 and no more than 15 seconds")

    spatial_ok = _has_required_spatial_fields(request)
    _add_check(checks, unit_label, "spatial_fields", spatial_ok, {"axis": bool(request.get("axis")), "screen_direction": bool(request.get("screen_direction")), "eyeline": bool(request.get("eyeline"))})
    if not spatial_ok:
        warnings.append(f"{unit_label}: axis, screen_direction, or eyeline is missing; inspect spatial blocking before live generation")

    high_risk_required = _requires_high_risk_template(request)
    high_risk_ok = not high_risk_required or "高风险空间模板" in prompt
    _add_check(checks, unit_label, "high_risk_spatial_template", high_risk_ok, {"required": high_risk_required})
    if not high_risk_ok:
        errors.append(f"{unit_label}: high-risk chase/throw/door/window scene is missing 高风险空间模板")

    unsafe_phrases = [phrase for phrase in FORBIDDEN_DRIFT_PHRASES if phrase in prompt]
    text_audio_ok = not unsafe_phrases and _has_no_text_audio_constraint(prompt)
    _add_check(checks, unit_label, "text_audio_constraints", text_audio_ok, {"unsafe_phrases": unsafe_phrases})
    if unsafe_phrases:
        errors.append(f"{unit_label}: prompt contains unsafe audio/text drift phrase(s): {', '.join(unsafe_phrases)}")
    if not _has_no_text_audio_constraint(prompt):
        warnings.append(f"{unit_label}: prompt should explicitly forbid subtitles, watermarks, title cards, fake text, songs, and music beds")

    if request.get("reference_image_urls") and "@Image1" not in prompt:
        errors.append(f"{unit_label}: prompt is missing @Image reference bindings")
        _add_check(checks, unit_label, "image_reference_bindings", False, {})
    elif request.get("reference_image_urls") or request.get("image_urls"):
        _add_check(checks, unit_label, "image_reference_bindings", True, {})

    return checks, errors, warnings


def _uses_all_purpose_reference(task: Dict, request: Dict) -> bool:
    policy = str(task.get("reference_policy") or task.get("reference_mode") or "").strip()
    if policy in ALL_PURPOSE_POLICIES or task.get("all_purpose_reference") is True:
        return True
    binding = request.get("reference_binding") or {}
    binding_policy = str(binding.get("reference_mode") or binding.get("reference_policy") or "").strip()
    return binding_policy in ALL_PURPOSE_POLICIES


def _has_required_spatial_fields(request: Dict) -> bool:
    characters = ((request.get("visual_lock") or {}).get("characters") or {})
    if len(characters) < 2:
        return True
    return bool(request.get("axis")) and bool(request.get("screen_direction")) and bool(request.get("eyeline"))


def _requires_high_risk_template(request: Dict) -> bool:
    sources = []
    for item in request.get("storyboard_execution_map") or []:
        sources.append({"visual": item.get("visual", "")})
    return bool(high_risk_spatial_template_text(sources))


def _has_no_text_audio_constraint(prompt: str) -> bool:
    lower_prompt = prompt.lower()
    return any(marker.lower() in lower_prompt for marker in NO_TEXT_AUDIO_MARKERS)


def _add_check(checks: List[Dict], unit_label: str, name: str, passed: bool, detail) -> None:
    checks.append({"unit": unit_label, "name": name, "status": "pass" if passed else "fail", "detail": detail})


def _cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="Path to a video preflight task JSON file")
    args = parser.parse_args()
    with open(args.task, "r", encoding="utf-8") as fh:
        task = json.load(fh)
    print(json.dumps(preflight_video_generation(task), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
