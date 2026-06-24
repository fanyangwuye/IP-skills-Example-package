from typing import Any, Dict


DEFAULT_MODELS = {
    "generic": "configured-live-llm-model",
    "openai": "configured-openai-model",
    "deepseek": "configured-deepseek-model",
    "qwen": "configured-qwen-model",
}


def build_provider_request(prompt_pack: Dict[str, Any], provider: str = "", model: str = "") -> Dict[str, Any]:
    provider_name = (provider or "generic").strip().lower()
    model_name = model or DEFAULT_MODELS.get(provider_name, DEFAULT_MODELS["generic"])
    return {
        "provider_request_version": "copy-live-provider-request-v1",
        "provider": provider_name,
        "model": model_name,
        "network_call_allowed": False,
        "mode": "dry_run_provider_request",
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


def summarize_provider_request(provider_request: Dict[str, Any]) -> Dict[str, Any]:
    messages = provider_request.get("messages") or []
    return {
        "provider": provider_request.get("provider"),
        "model": provider_request.get("model"),
        "mode": provider_request.get("mode"),
        "network_call_allowed": bool(provider_request.get("network_call_allowed")),
        "message_count": len(messages),
        "schema_name": (provider_request.get("response_format") or {}).get("schema_name"),
        "prompt_pack_version": (provider_request.get("prompt_pack") or {}).get("prompt_pack_version"),
    }
