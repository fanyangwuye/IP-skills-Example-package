from typing import Any, Dict, List


TRANSPORT_ADAPTER_VERSION = "copy-provider-transport-v1"
RESPONSE_INTAKE_VERSION = "copy-provider-response-intake-v1"

API_BASE_ENV_VARS = {
    "generic": "COPY_LLM_API_BASE",
    "openai": "OPENAI_API_BASE",
    "deepseek": "DEEPSEEK_API_BASE",
    "qwen": "QWEN_API_BASE",
}

ENDPOINT_PATH_HINTS = {
    "generic": "/v1/chat/completions",
    "openai": "/v1/chat/completions",
    "deepseek": "/v1/chat/completions",
    "qwen": "/compatible-mode/v1/chat/completions",
}

TIMEOUT_ENV_VARS = {
    "generic": "COPY_LLM_TIMEOUT_SEC",
    "openai": "OPENAI_TIMEOUT_SEC",
    "deepseek": "DEEPSEEK_TIMEOUT_SEC",
    "qwen": "QWEN_TIMEOUT_SEC",
}

DEFAULT_TIMEOUT_SEC = 120


def load_provider_transport_config(provider: str, model: str, provider_boundary: Dict[str, Any]) -> Dict[str, Any]:
    provider_name = (provider or "generic").strip().lower()
    api_base_env_var = API_BASE_ENV_VARS.get(provider_name, API_BASE_ENV_VARS["generic"])
    timeout_env_var = TIMEOUT_ENV_VARS.get(provider_name, TIMEOUT_ENV_VARS["generic"])
    api_base = _read_env(api_base_env_var)
    endpoint_path_hint = ENDPOINT_PATH_HINTS.get(provider_name, ENDPOINT_PATH_HINTS["generic"])
    timeout_sec = _parse_int(_read_env(timeout_env_var), DEFAULT_TIMEOUT_SEC)
    return {
        "transport_adapter_version": TRANSPORT_ADAPTER_VERSION,
        "provider": provider_name,
        "model": model,
        "api_base_env_var": api_base_env_var,
        "api_base_present": bool(api_base),
        "api_base_value_preview": _mask_url(api_base),
        "endpoint_path_hint": endpoint_path_hint,
        "timeout_env_var": timeout_env_var,
        "timeout_sec": timeout_sec,
        "header_auth_env_var": provider_boundary.get("api_key_env_var", "COPY_LLM_API_KEY"),
        "header_auth_present": bool(provider_boundary.get("api_key_present")),
        "transport_enabled": bool(provider_boundary.get("transport_adapter_implemented")),
        "network_call_allowed": False,
    }


def build_transport_request(provider_request: Dict[str, Any]) -> Dict[str, Any]:
    provider = provider_request.get("provider", "generic")
    model = provider_request.get("model", "")
    boundary = provider_request.get("provider_boundary") or {}
    transport_config = load_provider_transport_config(provider, model, boundary)
    request_options = provider_request.get("request_options") or {}
    body = {
        "model": model,
        "messages": provider_request.get("messages", []),
        "response_format": provider_request.get("response_format", {}),
        "temperature": request_options.get("temperature"),
        "max_output_tokens": request_options.get("max_output_tokens"),
    }
    return {
        "transport_adapter_version": TRANSPORT_ADAPTER_VERSION,
        "provider": provider,
        "model": model,
        "execution_mode": "prepared_but_not_executed",
        "network_call_allowed": False,
        "transport_config": transport_config,
        "request": {
            "method": "POST",
            "url_hint": _join_url_hint(
                transport_config.get("api_base_value_preview", ""),
                transport_config.get("endpoint_path_hint", ""),
            ),
            "headers": _masked_headers(transport_config),
            "body": body,
        },
        "blocked_by": list((boundary.get("blockers") or [])),
    }


def build_response_intake_handoff(provider_request: Dict[str, Any]) -> Dict[str, Any]:
    schema_name = (provider_request.get("response_format") or {}).get("schema_name", "")
    return {
        "response_intake_version": RESPONSE_INTAKE_VERSION,
        "provider": provider_request.get("provider", "generic"),
        "schema_name": schema_name,
        "expected_response_paths": [
            "choices[0].message.content",
            "choices[0].text",
            "output_text",
            "content",
            "text",
            "response",
            "data",
        ],
        "acceptance_flow": [
            "capture_raw_provider_response",
            "parse_provider_response_as_json",
            "run_review_creative_output",
            "reject_fail_accept_warn_or_pass",
        ],
        "network_call_allowed": False,
    }


def summarize_transport_request(transport_request: Dict[str, Any]) -> Dict[str, Any]:
    config = transport_request.get("transport_config") or {}
    request = transport_request.get("request") or {}
    body = request.get("body") or {}
    return {
        "provider": transport_request.get("provider"),
        "execution_mode": transport_request.get("execution_mode"),
        "network_call_allowed": bool(transport_request.get("network_call_allowed")),
        "api_base_present": bool(config.get("api_base_present")),
        "endpoint_path_hint": config.get("endpoint_path_hint"),
        "timeout_sec": config.get("timeout_sec"),
        "message_count": len(body.get("messages") or []),
        "has_response_format": bool(body.get("response_format")),
        "blocked_by": transport_request.get("blocked_by", []),
    }


def _masked_headers(transport_config: Dict[str, Any]) -> Dict[str, str]:
    auth_env = transport_config.get("header_auth_env_var", "COPY_LLM_API_KEY")
    return {
        "Authorization": f"Bearer $ENV:{auth_env}",
        "Content-Type": "application/json",
    }


def _join_url_hint(api_base_preview: str, endpoint_path_hint: str) -> str:
    if not api_base_preview:
        return endpoint_path_hint or ""
    return api_base_preview.rstrip("/") + "/" + endpoint_path_hint.lstrip("/")


def _mask_url(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "://" not in text:
        return text
    scheme, rest = text.split("://", 1)
    host = rest.split("/", 1)[0]
    return f"{scheme}://{host}"


def _read_env(name: str) -> str:
    import os
    return str(os.environ.get(name, "")).strip()


def _parse_int(value: str, default: int) -> int:
    try:
        return int(str(value or "").strip() or default)
    except (TypeError, ValueError):
        return default
