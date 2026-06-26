from typing import Any, Dict, List

from .base import CreativeEngineResult
from .provider_adapter import summarize_provider_request
from .provider_response import parse_provider_response
from .review import build_post_response_review_plan


EXECUTION_MANIFEST_VERSION = "copy-provider-execution-v1"
RESPONSE_REVIEW_VERSION = "copy-provider-response-review-v1"


def prepare_provider_execution(request, provider_request: Dict[str, Any]) -> Dict[str, Any]:
    boundary = provider_request.get("provider_boundary") or {}
    blockers = list(boundary.get("blockers") or [])
    return {
        "execution_manifest_version": EXECUTION_MANIFEST_VERSION,
        "execution_state": "prepared_but_not_executed",
        "network_call_allowed": False,
        "provider": provider_request.get("provider", "generic"),
        "model": provider_request.get("model", ""),
        "kind": request.kind,
        "schema_name": request.schema_name or request.kind,
        "format_name": request.format_name,
        "provider_request_summary": summarize_provider_request(provider_request),
        "transport_request_summary": provider_request.get("transport_request_summary", {}),
        "response_intake_handoff": provider_request.get("response_intake_handoff", {}),
        "post_response_review_plan": build_post_response_review_plan(request),
        "readiness": {
            "ready_for_live_call": bool(boundary.get("ready_for_live_call")),
            "blockers": blockers,
            "operator_action_required": True,
            "missing_requirements": _missing_requirements(blockers),
        },
        "next_actions": _prepare_next_actions(blockers),
    }


def intake_provider_response(request, provider_response: Any, provider_request: Dict[str, Any] | None = None) -> Dict[str, Any]:
    provider_request = provider_request or {}
    parsed = parse_provider_response(request, provider_response)
    accepted = bool(parsed.get("ready_for_creative_engine_result"))
    review_report = parsed.get("review_report") or {}
    review_status = parsed.get("status", "")
    acceptance_status = "accepted"
    if review_status == "warn":
        acceptance_status = "accepted_with_warnings"
    elif review_status not in {"pass", "warn"}:
        acceptance_status = "rejected"
    return {
        "response_review_version": RESPONSE_REVIEW_VERSION,
        "execution_state": "response_reviewed_offline",
        "network_call_allowed": False,
        "provider": provider_request.get("provider", "generic"),
        "model": provider_request.get("model", ""),
        "kind": request.kind,
        "schema_name": request.schema_name or request.kind,
        "format_name": request.format_name,
        "accepted_for_normalization": accepted,
        "acceptance_status": acceptance_status,
        "parsed_response": parsed,
        "review_report": review_report,
        "next_actions": _response_next_actions(accepted, review_report),
    }


def _missing_requirements(blockers: List[str]) -> List[str]:
    mapping = {
        "engine_live_not_approved": "engine allow_live must be explicitly approved",
        "request_live_not_approved": "task/request allow_live must be explicitly approved",
        "api_key_missing": "provider API key environment variable must be present",
        "prompt_exceeds_max_input_chars": "prompt surface must fit within configured input budget",
        "invalid_max_output_tokens": "max_output_tokens must be a positive integer when configured",
        "invalid_max_cost_usd": "max_cost_usd must be a positive number when configured",
        "provider_shape_not_implemented": "provider request shape must be implemented",
        "provider_transport_not_implemented": "provider transport adapter must be implemented",
        "live_execution_not_requested": "explicit execute_live confirmation is still missing",
        "unsupported_provider": "provider must be one of the supported guarded adapters",
    }
    missing: List[str] = []
    for blocker in blockers:
        item = mapping.get(blocker)
        if item and item not in missing:
            missing.append(item)
    return missing


def _prepare_next_actions(blockers: List[str]) -> List[str]:
    if not blockers:
        return [
            "Operator may execute the prepared transport request outside this dry-run layer.",
            "Capture the raw provider JSON response before any normalization.",
            "Send the raw provider response into intake_provider_response for schema and drift review.",
        ]
    actions = ["This manifest is still dry-run only; do not treat it as a live call."]
    for item in _missing_requirements(blockers):
        actions.append(f"Resolve: {item}.")
    actions.append("After manual provider execution, feed the raw response into intake_provider_response before accepting output.")
    return actions


def _response_next_actions(accepted: bool, review_report: Dict[str, Any]) -> List[str]:
    warnings = list(review_report.get("warnings") or [])
    blockers = list(review_report.get("blockers") or [])
    if blockers:
        return ["Reject this provider output and regenerate with the same locked schema and source-grounded constraints."] + blockers
    if warnings:
        return ["Output may continue only with review warnings attached.", "Human review should confirm every warning before downstream normalization."] + warnings
    if accepted:
        return ["Output is ready for downstream normalization into scene_cards or script_scenes.", "Keep the review report attached in downstream handoff artifacts."]
    return ["Review the raw provider response manually; acceptance could not be determined."]


def normalize_provider_response_to_result(request, provider_response: Any, provider_request: Dict[str, Any] | None = None) -> CreativeEngineResult:
    response_review = intake_provider_response(request, provider_response, provider_request=provider_request)
    parsed = response_review.get("parsed_response") or {}
    review_report = response_review.get("review_report") or {}
    if response_review.get("accepted_for_normalization"):
        return CreativeEngineResult(
            status="success",
            generation_source="provider_response_normalized",
            data=parsed.get("parsed_data", {}),
            warnings=list(parsed.get("warnings") or []),
            raw_response={
                "provider_response_review": response_review,
                "live_call_made": False,
            },
            review_report=review_report,
        )
    errors = list(parsed.get("errors") or [])
    for blocker in review_report.get("blockers") or []:
        if blocker not in errors:
            errors.append(blocker)
    return CreativeEngineResult(
        status="provider_response_rejected",
        generation_source="provider_response_normalized",
        data={},
        errors=errors,
        warnings=list(parsed.get("warnings") or []),
        raw_response={
            "provider_response_review": response_review,
            "live_call_made": False,
        },
        review_report=review_report,
    )


def build_double_confirm_live_execution_ticket(
    request,
    provider_request: Dict[str, Any],
    confirm_primary: bool = False,
    confirm_secondary: bool = False,
) -> Dict[str, Any]:
    manifest = prepare_provider_execution(request, provider_request)
    confirmed = bool(confirm_primary and confirm_secondary)
    ready_for_live_call = bool(manifest.get("readiness", {}).get("ready_for_live_call"))
    blockers = list(manifest.get("readiness", {}).get("blockers") or [])
    if not confirm_primary:
        blockers.append("primary_confirmation_missing")
    if not confirm_secondary:
        blockers.append("secondary_confirmation_missing")
    can_dispatch = ready_for_live_call and confirmed
    return {
        "execution_manifest_version": EXECUTION_MANIFEST_VERSION,
        "execution_state": "live_execution_double_confirmed_ready" if can_dispatch else "live_execution_double_confirmed_blocked",
        "network_call_allowed": False,
        "provider": provider_request.get("provider", "generic"),
        "model": provider_request.get("model", ""),
        "kind": request.kind,
        "schema_name": request.schema_name or request.kind,
        "format_name": request.format_name,
        "ready_for_live_call": ready_for_live_call,
        "double_confirmed": confirmed,
        "confirmations": {
            "primary": bool(confirm_primary),
            "secondary": bool(confirm_secondary),
        },
        "dispatch_ready": can_dispatch,
        "provider_request_summary": manifest.get("provider_request_summary", {}),
        "transport_request_summary": manifest.get("transport_request_summary", {}),
        "response_intake_handoff": manifest.get("response_intake_handoff", {}),
        "post_response_review_plan": manifest.get("post_response_review_plan", {}),
        "blockers": blockers,
        "next_actions": [
            "Do not execute a live provider call from this skill unless a separate external executor is explicitly built and approved.",
            "Keep network_call_allowed false in the skill layer.",
        ] if can_dispatch else [
            "Resolve the listed blockers and collect both confirmations before any external executor is considered.",
        ],
    }
