from typing import Dict, List, Optional, Tuple

try:
    from .clip_plan import PROVIDER_PROMPT_BUDGETS
    from .spatial_templates import high_risk_spatial_template_text
    from .video_handoff import build_video_handoff
    from .video_provider import PROMPT_PACKET_REQUIRED_SECTIONS
except ImportError:
    from clip_plan import PROVIDER_PROMPT_BUDGETS
    from spatial_templates import high_risk_spatial_template_text
    from video_handoff import build_video_handoff
    from video_provider import PROMPT_PACKET_REQUIRED_SECTIONS


PROMPT_FIELDS = {
    "clip_prompt": None,
    "i2v_prompt": "i2v",
    "seedance_prompt": "seedance",
    "t2v_prompt": "t2v",
}

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

FORBIDDEN_STORYBOARD_STYLE_COPY = [
    "禁止复制线稿风格",
    "line-art style",
    "table borders",
    "表格边框",
    "labels",
    "文字标签",
    "arrows",
    "箭头",
]

ALL_PURPOSE_POLICIES = {"all_purpose_reference", "all_purpose_reference_only"}


def build_prompt_architecture_audit(task: Dict) -> Dict:
    """Audit generated clip prompts without calling a video provider."""
    handoff = _ensure_handoff(task)
    clips = _select_clips(handoff.get("clip_plan") or [], task)
    checks: List[Dict] = []
    errors: List[str] = []
    warnings: List[str] = []
    clip_reports: List[Dict] = []

    if not clips:
        errors.append("prompt_architecture_audit requires video_handoff.clip_plan or source material that can build one")

    for clip in clips:
        clip_report, clip_checks, clip_errors, clip_warnings = _audit_clip(task, clip)
        clip_reports.append(clip_report)
        checks.extend(clip_checks)
        errors.extend(clip_errors)
        warnings.extend(clip_warnings)

    return {
        "prompt_architecture_audit_version": "1.0",
        "mode": "prompt_architecture_audit",
        "status": "pass" if not errors else "fail",
        "project_title": handoff.get("source_title") or task.get("title") or task.get("project_title") or "PROJECT_TITLE_HERE",
        "summary": {
            "clip_count": len(clips),
            "checked_prompt_count": sum(len(report.get("prompt_reports") or []) for report in clip_reports),
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "clip_reports": clip_reports,
        "action_items": _action_items(errors, warnings),
    }


def _ensure_handoff(task: Dict) -> Dict:
    handoff = task.get("video_handoff") or task.get("handoff")
    if handoff:
        if not isinstance(handoff, dict):
            raise ValueError("prompt_architecture_audit video_handoff must be an object")
        return handoff
    return build_video_handoff(task)


def _select_clips(clips: List[Dict], task: Dict) -> List[Dict]:
    clip_id = task.get("clip_id")
    if clip_id:
        return [clip for clip in clips if clip.get("clip_id") == clip_id]
    if task.get("clip_index") is not None:
        try:
            index = int(task.get("clip_index") or 1)
        except (TypeError, ValueError):
            return []
        return [clips[index - 1]] if 1 <= index <= len(clips) else []
    max_clips = task.get("max_clips")
    if max_clips is not None:
        try:
            return clips[: max(int(max_clips), 0)]
        except (TypeError, ValueError):
            return []
    return clips


def _audit_clip(task: Dict, clip: Dict) -> Tuple[Dict, List[Dict], List[str], List[str]]:
    clip_id = clip.get("clip_id") or "unknown_clip"
    checks: List[Dict] = []
    errors: List[str] = []
    warnings: List[str] = []
    prompt_reports = []

    for field, kind in PROMPT_FIELDS.items():
        prompt = str(clip.get(field) or "")
        report, prompt_checks, prompt_errors, prompt_warnings = _audit_prompt_field(clip_id, field, kind, prompt, clip)
        prompt_reports.append(report)
        checks.extend(prompt_checks)
        errors.extend(prompt_errors)
        warnings.extend(prompt_warnings)

    provider_ok = _provider_prompts_differ(clip)
    _add_check(checks, clip_id, "provider_prompt_differentiation", provider_ok, {
        "i2v_equals_seedance": clip.get("i2v_prompt") == clip.get("seedance_prompt"),
        "i2v_equals_t2v": clip.get("i2v_prompt") == clip.get("t2v_prompt"),
        "seedance_equals_t2v": clip.get("seedance_prompt") == clip.get("t2v_prompt"),
    })
    if not provider_ok:
        errors.append(f"{clip_id}: i2v_prompt, seedance_prompt, and t2v_prompt must be provider-specific, not identical")

    shot_ids = [item for item in clip.get("shot_ids") or [] if item]
    mapped_ids = [item.get("storyboard_shot_id") for item in clip.get("storyboard_execution_map") or [] if item.get("storyboard_shot_id")]
    storyboard_ok = bool(mapped_ids) and mapped_ids == shot_ids
    _add_check(checks, clip_id, "storyboard_execution_map_matches_clip", storyboard_ok, {"shot_ids": shot_ids, "mapped_ids": mapped_ids})
    if not storyboard_ok:
        errors.append(f"{clip_id}: storyboard_execution_map must exactly match clip.shot_ids")

    production_ok = str(clip.get("storyboard_mode") or "production").strip().lower() != "draft"
    _add_check(checks, clip_id, "storyboard_mode_production", production_ok, clip.get("storyboard_mode", "production"))
    if not production_ok:
        warnings.append(f"{clip_id}: storyboard_mode=draft is review-only; approve and rebuild before paid/live generation")

    all_purpose = _uses_all_purpose_reference(task, clip)
    if all_purpose:
        all_purpose_text_ok = _clip_contains_any(clip, ["reference_image_urls", "全能参考", "all-purpose reference"])
        _add_check(checks, clip_id, "all_purpose_reference_wording", all_purpose_text_ok, {"reference_policy": "all_purpose_reference"})
        if not all_purpose_text_ok:
            warnings.append(f"{clip_id}: all-purpose reference policy is set; provider request/preflight must add explicit reference_image_urls and @Image binding text")

    storyboard_ref_present = bool(clip.get("storyboard_panel_refs") or clip.get("storyboard_image_path") or task.get("storyboard_panel_refs") or task.get("storyboard_image_path"))
    if storyboard_ref_present:
        storyboard_copy_ok = _clip_contains_any(clip, FORBIDDEN_STORYBOARD_STYLE_COPY)
        _add_check(checks, clip_id, "storyboard_style_copy_forbidden", storyboard_copy_ok, {})
        if not storyboard_copy_ok:
            warnings.append(f"{clip_id}: storyboard panel refs are present but prompts do not clearly forbid copying line art, labels, borders, arrows, or sketch texture")

    return {
        "clip_id": clip_id,
        "shot_ids": shot_ids,
        "prompt_reports": prompt_reports,
        "status": "pass" if not [error for error in errors if error.startswith(f"{clip_id}:")] else "fail",
    }, checks, errors, warnings


def _audit_prompt_field(clip_id: str, field: str, kind: Optional[str], prompt: str, clip: Dict) -> Tuple[Dict, List[Dict], List[str], List[str]]:
    checks: List[Dict] = []
    errors: List[str] = []
    warnings: List[str] = []
    label = f"{clip_id}.{field}"

    nonempty = bool(prompt.strip())
    _add_prompt_check(checks, label, "nonempty", nonempty, {"length": len(prompt)})
    if not nonempty:
        errors.append(f"{label}: prompt is empty")
        return _prompt_report(field, kind, prompt, "fail"), checks, errors, warnings

    missing = [section for section in PROMPT_PACKET_REQUIRED_SECTIONS if section not in prompt]
    sections_ok = not missing
    _add_prompt_check(checks, label, "prompt_packet_sections", sections_ok, {"missing_sections": missing})
    if missing:
        errors.append(f"{label}: Prompt Packet V1 missing sections: {', '.join(missing)}")

    order_ok = _sections_in_order(prompt, PROMPT_PACKET_REQUIRED_SECTIONS)
    _add_prompt_check(checks, label, "prompt_packet_section_order", order_ok, {})
    if not order_ok:
        errors.append(f"{label}: Prompt Packet V1 sections are not in the fixed order")

    if kind:
        marker_ok = f"prompt_kind={kind}" in prompt
        _add_prompt_check(checks, label, "provider_kind_marker", marker_ok, {"expected": kind})
        if not marker_ok:
            errors.append(f"{label}: missing provider marker prompt_kind={kind}")

        budget = PROVIDER_PROMPT_BUDGETS.get(kind)
        budget_ok = budget is None or len(prompt) <= budget
        _add_prompt_check(checks, label, "provider_prompt_budget", budget_ok, {"length": len(prompt), "budget": budget})
        if not budget_ok:
            errors.append(f"{label}: prompt length {len(prompt)} exceeds {kind} budget {budget}")

    text_audio_ok = _contains_any(prompt, NO_TEXT_AUDIO_MARKERS)
    _add_prompt_check(checks, label, "text_audio_constraints", text_audio_ok, {})
    if not text_audio_ok:
        warnings.append(f"{label}: should explicitly forbid subtitles, watermarks, fake text, title cards, songs, and music beds")

    safe_layer_ok = "Internal Story Facts" in prompt and "Platform-Safe Surface Wording" in prompt
    _add_prompt_check(checks, label, "internal_vs_surface_layers", safe_layer_ok, {})
    if not safe_layer_ok:
        errors.append(f"{label}: internal facts and platform-safe surface wording layers must both be present")

    director_ok = _contains_any(prompt, ["导演设计", "director=", "director_plan"])
    _add_prompt_check(checks, label, "director_plan_visible", director_ok, {})
    if not director_ok:
        warnings.append(f"{label}: director_plan or director shot-design markers should be visible in the prompt timeline")
    timeline_ok = _timeline_covers_storyboard(prompt, clip)
    _add_prompt_check(checks, label, "timeline_mentions_storyboard_shots", timeline_ok, {"shot_ids": clip.get("shot_ids", [])})
    if not timeline_ok:
        warnings.append(f"{label}: 15s Timeline should mention each mapped shot_id so the model executes storyboard order")

    high_risk_text = "高风险空间模板" in prompt
    high_risk_required = _requires_high_risk_spatial_template(clip)
    high_risk_ok = not high_risk_required or high_risk_text
    _add_prompt_check(checks, label, "high_risk_spatial_template", high_risk_ok, {"required": high_risk_required})
    if not high_risk_ok:
        errors.append(f"{label}: high-risk chase/throw/door/window scene is missing 高风险空间模板")

    status = "pass" if not [error for error in errors if error.startswith(label)] else "fail"
    return _prompt_report(field, kind, prompt, status), checks, errors, warnings


def _prompt_report(field: str, kind: Optional[str], prompt: str, status: str) -> Dict:
    return {
        "field": field,
        "prompt_kind": kind or "full_packet",
        "status": status,
        "length": len(prompt),
        "budget": PROVIDER_PROMPT_BUDGETS.get(kind) if kind else None,
    }


def _sections_in_order(prompt: str, sections: List[str]) -> bool:
    cursor = -1
    for section in sections:
        position = prompt.find(section)
        if position < 0 or position <= cursor:
            return False
        cursor = position
    return True


def _timeline_covers_storyboard(prompt: str, clip: Dict) -> bool:
    shot_ids = [item for item in clip.get("shot_ids") or [] if item]
    if not shot_ids:
        return True
    return all(shot_id in prompt for shot_id in shot_ids)


def _requires_high_risk_spatial_template(clip: Dict) -> bool:
    sources = [{"visual": clip.get("visual", "")}]
    sources.extend({"visual": item.get("visual", "")} for item in clip.get("storyboard_execution_map") or [])
    return bool(high_risk_spatial_template_text(sources))


def _provider_prompts_differ(clip: Dict) -> bool:
    prompts = [clip.get("i2v_prompt"), clip.get("seedance_prompt"), clip.get("t2v_prompt")]
    return all(prompts) and len(set(prompts)) == len(prompts)


def _uses_all_purpose_reference(task: Dict, clip: Dict) -> bool:
    policy = str(task.get("reference_policy") or task.get("reference_mode") or "").strip()
    if policy in ALL_PURPOSE_POLICIES or task.get("all_purpose_reference") is True:
        return True
    binding = clip.get("reference_binding") or {}
    binding_policy = str(binding.get("reference_policy") or binding.get("reference_mode") or "").strip()
    return binding_policy in ALL_PURPOSE_POLICIES


def _clip_contains_any(clip: Dict, markers: List[str]) -> bool:
    text = "\n".join(str(clip.get(field) or "") for field in PROMPT_FIELDS)
    return _contains_any(text, markers)


def _contains_any(text: str, markers: List[str]) -> bool:
    lower = str(text or "").lower()
    return any(marker.lower() in lower for marker in markers)


def _add_check(checks: List[Dict], unit: str, name: str, passed: bool, detail) -> None:
    checks.append({"group": "clip", "unit": unit, "name": name, "status": "pass" if passed else "fail", "detail": detail})


def _add_prompt_check(checks: List[Dict], unit: str, name: str, passed: bool, detail) -> None:
    checks.append({"group": "prompt_field", "unit": unit, "name": name, "status": "pass" if passed else "fail", "detail": detail})


def _action_items(errors: List[str], warnings: List[str]) -> List[Dict]:
    items = []
    for error in errors:
        items.append({"priority": "blocker", "action": "regenerate_or_fix_prompt_packet", "message": error})
    for warning in warnings:
        items.append({"priority": "review", "action": "review_prompt_before_live_generation", "message": warning})
    return items
