from typing import Any, Dict, List


REQUIRED_SCENE_CARD_FIELDS = ["visual", "voiceover", "duration_sec", "asset_goal"]
REQUIRED_SCRIPT_SCENE_FIELDS = ["visual", "voiceover", "dialogue", "start_sec", "end_sec"]


def evaluate_scene_cards_quality(scene_cards: List[Dict[str, Any]], adapter_spec=None) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    warnings: List[str] = []
    cards = scene_cards or []
    if not cards:
        issues.append(_issue("blocker", "scene_cards_empty", "scene_cards must be a non-empty list"))
    for index, card in enumerate(cards, start=1):
        _check_required_fields(card, REQUIRED_SCENE_CARD_FIELDS, f"scene_card[{index}]", issues)
        if _looks_like_template(card.get("visual", "")):
            warnings.append(f"scene_card[{index}] visual still looks like scaffold text")
        if card.get("generation_source") in {"fallback_scaffold", "screenplay_scaffold"}:
            warnings.append(f"scene_card[{index}] uses {card.get('generation_source')}; review or replace with CreativeEngine output before final production")
        if not (card.get("asset_goal") or {}).get("type"):
            issues.append(_issue("warning", "asset_goal_type_missing", f"scene_card[{index}] asset_goal.type missing"))
    status = _status(issues)
    return {
        "quality_report_version": "1.0",
        "target": "scene_cards",
        "status": status,
        "score": _score(status, issues, warnings),
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "issues": issues,
        "warnings": warnings,
        "recommendation": _recommendation(status, warnings),
    }


def evaluate_script_quality(script: Dict[str, Any], adapter_spec=None, polished: bool = False) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    warnings: List[str] = []
    scenes = script.get("scenes") or []
    if not scenes:
        issues.append(_issue("blocker", "script_scenes_empty", "script.scenes must be a non-empty list"))
    if adapter_spec and script.get("aspect_ratio") and script.get("aspect_ratio") != adapter_spec.default_aspect_ratio:
        issues.append(_issue("warning", "aspect_ratio_mismatch", f"expected {adapter_spec.default_aspect_ratio}, got {script.get('aspect_ratio')}"))
    for index, scene in enumerate(scenes, start=1):
        _check_required_fields(scene, REQUIRED_SCRIPT_SCENE_FIELDS, f"scene[{index}]", issues)
        if not scene.get("dialogue"):
            issues.append(_issue("warning", "dialogue_missing", f"scene[{index}] has no dialogue"))
        if scene.get("generation_source", "").startswith("fallback"):
            warnings.append(f"scene[{index}] uses {scene.get('generation_source')}; suitable as scaffold, not final creative output")
        if index == 1 and not _has_hook(scene):
            warnings.append("scene[1] may lack a clear opening hook or pressure point")
        if polished and not scene.get("conflict_notes"):
            issues.append(_issue("warning", "conflict_notes_missing", f"polished scene[{index}] missing conflict_notes"))
    handoff = script.get("handoff") or {}
    if not handoff.get("can_build_blueprint"):
        issues.append(_issue("warning", "handoff_blueprint_flag_missing", "handoff.can_build_blueprint should be true"))
    if adapter_spec:
        for key in ("image_requirements", "video_requirements", "music_requirements"):
            if key not in handoff:
                warnings.append(f"handoff.{key} missing; downstream checks may be weaker")
    status = _status(issues)
    return {
        "quality_report_version": "1.0",
        "target": "polished_script" if polished else "script_draft",
        "status": status,
        "score": _score(status, issues, warnings),
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "issues": issues,
        "warnings": warnings,
        "recommendation": _recommendation(status, warnings),
    }


def _check_required_fields(item: Dict[str, Any], fields: List[str], label: str, issues: List[Dict[str, Any]]) -> None:
    if not isinstance(item, dict):
        issues.append(_issue("blocker", "invalid_object", f"{label} must be an object"))
        return
    for field in fields:
        if item.get(field) in (None, "", []):
            issues.append(_issue("warning", "required_field_missing", f"{label} missing required field: {field}"))


def _looks_like_template(text: str) -> bool:
    return any(marker in str(text or "") for marker in ("围绕该剧情点行动", "推进第", "核心场景"))


def _has_hook(scene: Dict[str, Any]) -> bool:
    text = " ".join(str(scene.get(key, "")) for key in ("visual", "voiceover", "action"))
    return any(marker in text for marker in ("开场", "突然", "危机", "异常", "规则", "反转", "不对劲", "死亡", "不能"))


def _issue(severity: str, code: str, message: str) -> Dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def _status(issues: List[Dict[str, Any]]) -> str:
    if any(item.get("severity") == "blocker" for item in issues):
        return "fail"
    if issues:
        return "warn"
    return "pass"


def _score(status: str, issues: List[Dict[str, Any]], warnings: List[str]) -> int:
    base = {"pass": 100, "warn": 78, "fail": 40}.get(status, 70)
    return max(base - len(issues) * 3 - len(warnings) * 2, 0)


def _recommendation(status: str, warnings: List[str]) -> str:
    if status == "fail":
        return "Fix blocker issues before downstream image/video handoff."
    if warnings:
        return "Review scaffold warnings before treating the output as final creative writing."
    return "Ready for downstream structured handoff review."