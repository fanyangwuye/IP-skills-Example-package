import os
from typing import Any, Dict, List


DEFAULT_MODELS = {
    "generic": "configured-live-llm-model",
    "openai": "configured-openai-model",
    "deepseek": "configured-deepseek-model",
    "qwen": "configured-qwen-model",
}

API_KEY_ENV_VARS = {
    "generic": "COPY_LLM_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
}

SUPPORTED_PROVIDERS = set(DEFAULT_MODELS)


def build_provider_request(
    prompt_pack: Dict[str, Any],
    provider: str = "",
    model: str = "",
    allow_live: bool = False,
    request_allow_live: bool = False,
    max_input_chars: int = 0,
    max_output_tokens: int = 0,
    max_cost_usd: float = 0.0,
) -> Dict[str, Any]:
    provider_name = (provider or "generic").strip().lower()
    model_name = model or DEFAULT_MODELS.get(provider_name, DEFAULT_MODELS["generic"])
    boundary = build_provider_boundary(
        prompt_pack,
        provider=provider_name,
        model=model_name,
        allow_live=allow_live,
        request_allow_live=request_allow_live,
        max_input_chars=max_input_chars,
        max_output_tokens=max_output_tokens,
        max_cost_usd=max_cost_usd,
    )
    return {
        "provider_request_version": "copy-live-provider-request-v1",
        "provider": provider_name,
        "model": model_name,
        "network_call_allowed": False,
        "mode": "dry_run_provider_request",
        "provider_boundary": boundary,
        "messages": [
            {"role": "system", "content": prompt_pack.get("system_prompt", "")},
            {"role": "user", "content": prompt_pack.get("user_prompt", "")},
        ],
        "response_format": {
            "type": "json_object_or_array",
            "schema_name": prompt_pack.get("schema_name", ""),
            "contract": prompt_pack.get("response_contract", {}),
        },
        "safety_constraints": prompt_pack.get("safety_constraints", []),
        "quality_targets": prompt_pack.get("quality_targets", []),
        "prompt_pack": prompt_pack,
    }


def build_provider_boundary(
    prompt_pack: Dict[str, Any],
    provider: str,
    model: str,
    allow_live: bool = False,
    request_allow_live: bool = False,
    max_input_chars: int = 0,
    max_output_tokens: int = 0,
    max_cost_usd: float = 0.0,
) -> Dict[str, Any]:
    provider_name = (provider or "generic").strip().lower()
    api_key_env_var = API_KEY_ENV_VARS.get(provider_name, "COPY_LLM_API_KEY")
    api_key_present = bool(os.environ.get(api_key_env_var))
    prompt_chars = len(str(prompt_pack.get("system_prompt", ""))) + len(str(prompt_pack.get("user_prompt", "")))
    supported_provider = provider_name in SUPPORTED_PROVIDERS
    blockers: List[str] = []
    if not supported_provider:
        blockers.append("unsupported_provider")
    if not allow_live:
        blockers.append("engine_live_not_approved")
    if not request_allow_live:
        blockers.append("request_live_not_approved")
    if not api_key_present:
        blockers.append("api_key_missing")
    if max_input_chars and prompt_chars > int(max_input_chars):
        blockers.append("prompt_exceeds_max_input_chars")
    if max_output_tokens and int(max_output_tokens) <= 0:
        blockers.append("invalid_max_output_tokens")
    if max_cost_usd and float(max_cost_usd) <= 0:
        blockers.append("invalid_max_cost_usd")
    blockers.append("network_adapter_not_implemented")
    return {
        "provider_boundary_version": "copy-provider-boundary-v1",
        "provider": provider_name,
        "model": model,
        "supported_provider": supported_provider,
        "api_key_env_var": api_key_env_var,
        "api_key_present": api_key_present,
        "engine_allow_live": bool(allow_live),
        "request_allow_live": bool(request_allow_live),
        "network_adapter_implemented": False,
        "network_call_allowed": False,
        "prompt_chars": prompt_chars,
        "budget": {
            "max_input_chars": int(max_input_chars or 0),
            "max_output_tokens": int(max_output_tokens or 0),
            "max_cost_usd": float(max_cost_usd or 0.0),
        },
        "blockers": blockers,
        "ready_for_live_call": False,
    }


def summarize_provider_request(provider_request: Dict[str, Any]) -> Dict[str, Any]:
    messages = provider_request.get("messages") or []
    boundary = provider_request.get("provider_boundary") or {}
    return {
        "provider": provider_request.get("provider"),
        "model": provider_request.get("model"),
        "mode": provider_request.get("mode"),
        "network_call_allowed": bool(provider_request.get("network_call_allowed")),
        "message_count": len(messages),
        "schema_name": (provider_request.get("response_format") or {}).get("schema_name"),
        "prompt_pack_version": (provider_request.get("prompt_pack") or {}).get("prompt_pack_version"),
        "provider_boundary_version": boundary.get("provider_boundary_version"),
        "api_key_env_var": boundary.get("api_key_env_var"),
        "api_key_present": bool(boundary.get("api_key_present")),
        "ready_for_live_call": bool(boundary.get("ready_for_live_call")),
        "blockers": boundary.get("blockers", []),
    }