import json
import re
from typing import Any, Dict, List, Tuple

from .review import review_creative_output
from .schemas import validate_scene_cards, validate_script_scenes


PROVIDER_RESPONSE_PARSE_VERSION = "copy-provider-response-parse-v1"


def parse_provider_response(request, provider_response: Any) -> Dict[str, Any]:
    content, source_path = _extract_response_content(provider_response)
    parsed_data = None
    parse_errors: List[str] = []

    if isinstance(content, (list, dict)):
        parsed_data = content
    elif isinstance(content, str) and content.strip():
        parsed_data, parse_errors = _parse_json_content(content)
    else:
        parse_errors.append("provider_response_content_empty")

    schema_errors = _schema_errors(request.schema_name, parsed_data) if parsed_data is not None else []
    review_report = review_creative_output(request, parsed_data, schema_errors=schema_errors)
    errors = list(parse_errors)
    errors.extend(schema_errors)
    status = _status(parse_errors, review_report)

    return {
        "provider_response_parse_version": PROVIDER_RESPONSE_PARSE_VERSION,
        "status": status,
        "ready_for_creative_engine_result": status in {"pass", "warn"},
        "source_path": source_path,
        "parsed_data": parsed_data,
        "errors": errors,
        "warnings": review_report.get("warnings", []),
        "review_report": review_report,
        "content_summary": {
            "content_type": type(content).__name__,
            "content_chars": len(content) if isinstance(content, str) else len(json.dumps(content, ensure_ascii=False, sort_keys=True)) if content is not None else 0,
        },
    }


def _extract_response_content(provider_response: Any) -> Tuple[Any, str]:
    if isinstance(provider_response, str):
        return provider_response, "raw_string"
    if isinstance(provider_response, list):
        return provider_response, "raw_array"
    if not isinstance(provider_response, dict):
        return provider_response, "raw_value"

    choices = provider_response.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0] or {}
        message = first.get("message") if isinstance(first, dict) else {}
        if isinstance(message, dict) and message.get("content") not in (None, ""):
            return message.get("content"), "choices[0].message.content"
        if isinstance(first, dict) and first.get("text") not in (None, ""):
            return first.get("text"), "choices[0].text"

    for key in ("output_text", "content", "text", "response"):
        if provider_response.get(key) not in (None, ""):
            return provider_response.get(key), key

    if provider_response.get("data") not in (None, ""):
        return provider_response.get("data"), "data"

    return provider_response, "raw_object"


def _parse_json_content(content: str) -> Tuple[Any, List[str]]:
    text = _strip_code_fence(content)
    try:
        return json.loads(text), []
    except json.JSONDecodeError as exc:
        direct_error = f"json_decode_error: {exc.msg} at char {exc.pos}"

    candidate = _extract_first_json_candidate(text)
    if candidate and candidate != text:
        try:
            return json.loads(candidate), []
        except json.JSONDecodeError as exc:
            return None, [direct_error, f"json_candidate_decode_error: {exc.msg} at char {exc.pos}"]
    return None, [direct_error]


def _strip_code_fence(content: str) -> str:
    text = str(content or "").strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _extract_first_json_candidate(text: str) -> str:
    starts = [index for index in (text.find("["), text.find("{")) if index >= 0]
    if not starts:
        return ""
    start = min(starts)
    open_char = text[start]
    close_char = "]" if open_char == "[" else "}"
    end = text.rfind(close_char)
    if end <= start:
        return ""
    return text[start : end + 1].strip()


def _schema_errors(schema_name: str, data: Any) -> List[str]:
    if schema_name == "scene_cards":
        return validate_scene_cards(data)
    if schema_name == "script_scenes":
        return validate_script_scenes(data)
    return []


def _status(parse_errors: List[str], review_report: Dict[str, Any]) -> str:
    if parse_errors:
        return "parse_error"
    review_status = review_report.get("status")
    if review_status == "fail":
        return "schema_or_review_error"
    if review_status == "warn":
        return "warn"
    return "pass"