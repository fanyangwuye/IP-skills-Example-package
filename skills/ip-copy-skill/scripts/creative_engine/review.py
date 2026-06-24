import json
from typing import Any, Dict, List

from .schemas import validate_scene_cards, validate_script_scenes


REVIEW_VERSION = "copy-creative-engine-review-v1"

SUSPICIOUS_DETAIL_TERMS = (
    "手帕",
    "炸弹",
    "怪兽",
    "飞剑",
    "符箓",
    "丹炉",
    "枪",
    "手机",
    "红酒",
    "酒杯",
    "菜刀",
    "探测器",
    "托盘",
    "菜单",
    "账本",
)


def review_creative_output(request, data: Any, schema_errors: List[str] = None) -> Dict[str, Any]:
    schema_errors = list(schema_errors or _schema_errors(request.schema_name, data))
    output_text = _output_text(data)
    source_text = request.source_text or ""
    payload_text = _output_text(request.payload or {})
    locked_names = _locked_character_names(request.payload or {})

    blockers: List[str] = []
    warnings: List[str] = []
    if schema_errors:
        blockers.extend([f"schema_error: {error}" for error in schema_errors])
    if data in (None, "", [], {}):
        blockers.append("empty_output")
    if not source_text:
        warnings.append("source_text_missing; review cannot verify source-grounded facts")
    unsupported = _unsupported_details(output_text, source_text, payload_text)
    for term in unsupported:
        warnings.append(f"output may introduce unsupported detail: {term}")
    if locked_names and output_text and not any(name in output_text for name in locked_names):
        warnings.append("output does not visibly reference locked character names")

    status = "fail" if blockers else "warn" if warnings else "pass"
    return {
        "review_version": REVIEW_VERSION,
        "kind": request.kind,
        "schema_name": request.schema_name or request.kind,
        "format_name": request.format_name,
        "status": status,
        "ready_for_acceptance": status != "fail",
        "requires_retry": status == "fail",
        "blockers": blockers,
        "warnings": warnings,
        "checks": {
            "schema_valid": not schema_errors,
            "output_non_empty": data not in (None, "", [], {}),
            "source_text_present": bool(source_text),
            "locked_character_names": locked_names,
            "unsupported_details": unsupported,
        },
        "output_summary": _output_summary(data),
        "retry_advice": _retry_advice(blockers, warnings, request.kind),
    }


def build_post_response_review_plan(request) -> Dict[str, Any]:
    return {
        "review_version": REVIEW_VERSION,
        "kind": request.kind,
        "schema_name": request.schema_name or request.kind,
        "format_name": request.format_name,
        "when": "after_provider_json_response_before_accepting_creative_output",
        "required_stages": [
            "parse_provider_response_as_json",
            "validate_schema_required_fields",
            "reject_empty_output",
            "check_locked_character_visibility",
            "check_unsupported_detail_drift_against_source_and_payload",
            "attach_review_report_to_creative_engine_result",
            "only_then_normalize_into_scene_cards_or_script_scenes",
        ],
        "acceptance_policy": {
            "fail": "do not silently fall back when explicit CreativeEngine output was requested; return blockers or retry",
            "warn": "allow structured handoff only with review warnings attached",
            "pass": "safe to normalize for downstream scaffold review",
        },
    }


def _schema_errors(schema_name: str, data: Any) -> List[str]:
    if schema_name == "scene_cards":
        return validate_scene_cards(data)
    if schema_name == "script_scenes":
        return validate_script_scenes(data)
    return []


def _locked_character_names(payload: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for key in ("characters", "character_cards"):
        for item in payload.get(key) or []:
            name = _name_from_character(item)
            if name and name not in names:
                names.append(name)
    script = payload.get("script") or {}
    for item in script.get("characters") or [] if isinstance(script, dict) else []:
        name = _name_from_character(item)
        if name and name not in names:
            names.append(name)
    return names[:12]


def _name_from_character(item: Any) -> str:
    if isinstance(item, dict):
        profile = item.get("character_profile") or {}
        identity = profile.get("identity") or {}
        return str(item.get("name") or item.get("character_name") or identity.get("name") or "").strip()
    return str(item or "").strip()


def _unsupported_details(output_text: str, source_text: str, payload_text: str) -> List[str]:
    allowed_text = f"{source_text} {payload_text}"
    return [term for term in SUSPICIOUS_DETAIL_TERMS if term in output_text and term not in allowed_text]


def _output_summary(data: Any) -> Dict[str, Any]:
    if isinstance(data, list):
        return {"root_type": "array", "item_count": len(data), "text_chars": len(_output_text(data))}
    if isinstance(data, dict):
        return {"root_type": "object", "keys": sorted(data.keys()), "text_chars": len(_output_text(data))}
    return {"root_type": type(data).__name__, "text_chars": len(_output_text(data))}


def _retry_advice(blockers: List[str], warnings: List[str], kind: str) -> List[str]:
    advice: List[str] = []
    if any("schema_error" in item for item in blockers):
        advice.append(f"Regenerate {kind} as strict JSON matching the response contract required fields.")
    if "empty_output" in blockers:
        advice.append("Regenerate because the provider returned no usable structured content.")
    if any("unsupported detail" in item for item in warnings):
        advice.append("Remove or justify unsupported props, powers, locations, or characters using source text or locked payload.")
    if any("locked character" in item for item in warnings):
        advice.append("Rewrite with locked character names visible in the relevant scene/card fields.")
    if not advice:
        advice.append("Review warnings manually before treating this as final creative writing.")
    return advice


def _output_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)