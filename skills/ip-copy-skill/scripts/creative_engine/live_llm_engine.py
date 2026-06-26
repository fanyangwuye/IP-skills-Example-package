import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict

from .base import CreativeEngine, CreativeEngineRequest, CreativeEngineResult, EngineBlockedError
from .prompt_packs import build_prompt_pack
from .provider_adapter import build_provider_request, summarize_provider_request
from .provider_transport import build_response_intake_handoff, build_transport_request
from .review import build_post_response_review_plan

# Default API base URLs for each provider
DEFAULT_API_BASES = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "generic": "https://api.openai.com/v1",
}

API_KEY_ENV_VARS = {
    "generic": "COPY_LLM_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
}


class LiveLLMEngine(CreativeEngine):
    engine_name = "live_llm"

    def __init__(self, provider: str = "", model: str = "", allow_live: bool = False):
        self.provider = provider or "unconfigured"
        self.model = model or ""
        self.allow_live = allow_live

    def generate(self, request: CreativeEngineRequest) -> CreativeEngineResult:
        if not (self.allow_live and request.allow_live):
            raise EngineBlockedError(
                "Live LLM generation is blocked by default. Set allow_live on both engine and request after explicit user approval."
            )
        prompt_pack = build_prompt_pack(request)
        provider_request = build_provider_request(
            prompt_pack,
            provider=self.provider,
            model=self.model,
            allow_live=self.allow_live,
            request_allow_live=request.allow_live,
        )
        review_plan = build_post_response_review_plan(request)

        # Check if network call is allowed — if yes, make the real API call
        if provider_request.get("network_call_allowed"):
            try:
                return self._make_live_call(request, provider_request, prompt_pack, review_plan)
            except Exception as exc:
                return CreativeEngineResult(
                    status="error",
                    generation_source="live_llm_engine",
                    data={},
                    warnings=[f"Live call failed: {exc}"],
                    raw_response={
                        "prompt_pack": prompt_pack,
                        "provider_request": provider_request,
                        "provider_request_summary": summarize_provider_request(provider_request),
                        "post_response_review_plan": review_plan,
                        "live_call_made": False,
                        "error": str(exc),
                    },
                    review_report=review_plan,
                )

        # Fallback to dry_run mode when network call is not allowed
        return CreativeEngineResult(
            status="provider_request_ready",
            generation_source="live_llm_engine_dry_run",
            data={},
            warnings=["Live LLM provider request was built for review; no provider call was made."],
            raw_response={
                "prompt_pack": prompt_pack,
                "provider_request": provider_request,
                "provider_request_summary": summarize_provider_request(provider_request),
                "transport_request": build_transport_request(provider_request),
                "response_intake_handoff": build_response_intake_handoff(provider_request),
                "post_response_review_plan": review_plan,
                "live_call_made": False,
            },
            review_report=review_plan,
        )

    def _make_live_call(
        self,
        request: CreativeEngineRequest,
        provider_request: Dict[str, Any],
        prompt_pack: Dict[str, Any],
        review_plan: Dict[str, Any],
    ) -> CreativeEngineResult:
        """Execute actual LLM API call using OpenAI Chat Completions compatible format."""
        provider_name = provider_request.get("provider", self.provider)
        model_name = provider_request.get("model", self.model)

        # Get API key and base URL
        api_key_env_var = API_KEY_ENV_VARS.get(provider_name, "COPY_LLM_API_KEY")
        api_key = os.environ.get(api_key_env_var, "")
        api_base = os.environ.get(
            f"{provider_name.upper()}_API_BASE",
            DEFAULT_API_BASES.get(provider_name, DEFAULT_API_BASES["generic"]),
        )

        # Build request body compatible with OpenAI Chat Completions format
        messages = provider_request.get("messages", [])
        request_body = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
        }

        # Prepare HTTP request
        url = f"{api_base.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(request_body).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                response_data = json.loads(response.read().decode("utf-8"))

            # Parse the response using provider_response module
            from .provider_response import parse_provider_response

            parse_result = parse_provider_response(request, response_data)

            if parse_result.get("ready_for_creative_engine_result"):
                return CreativeEngineResult(
                    status="success",
                    generation_source="live_llm_engine",
                    data=parse_result.get("parsed_data"),
                    warnings=parse_result.get("warnings", []),
                    raw_response={
                        "provider_request": provider_request,
                        "provider_request_summary": summarize_provider_request(provider_request),
                        "provider_raw_response": response_data,
                        "parse_result": parse_result,
                        "live_call_made": True,
                    },
                    review_report=parse_result.get("review_report", review_plan),
                )
            else:
                return CreativeEngineResult(
                    status="parse_error",
                    generation_source="live_llm_engine",
                    data=parse_result.get("parsed_data"),
                    warnings=parse_result.get("warnings", []),
                    errors=parse_result.get("errors", []),
                    raw_response={
                        "provider_request": provider_request,
                        "provider_request_summary": summarize_provider_request(provider_request),
                        "provider_raw_response": response_data,
                        "parse_result": parse_result,
                        "live_call_made": True,
                    },
                    review_report=parse_result.get("review_report", review_plan),
                )

        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8") if exc.fp else ""
            return CreativeEngineResult(
                status="error",
                generation_source="live_llm_engine",
                data={},
                warnings=[f"HTTP error {exc.code}: {error_body}"],
                raw_response={
                    "provider_request": provider_request,
                    "provider_request_summary": summarize_provider_request(provider_request),
                    "live_call_made": False,
                    "error": f"HTTPError {exc.code}",
                },
                review_report=review_plan,
            )
        except urllib.error.URLError as exc:
            return CreativeEngineResult(
                status="error",
                generation_source="live_llm_engine",
                data={},
                warnings=[f"URL error: {exc.reason}"],
                raw_response={
                    "provider_request": provider_request,
                    "provider_request_summary": summarize_provider_request(provider_request),
                    "live_call_made": False,
                    "error": f"URLError: {exc.reason}",
                },
                review_report=review_plan,
            )
        except json.JSONDecodeError as exc:
            return CreativeEngineResult(
                status="error",
                generation_source="live_llm_engine",
                data={},
                warnings=[f"JSON decode error: {exc}"],
                raw_response={
                    "provider_request": provider_request,
                    "provider_request_summary": summarize_provider_request(provider_request),
                    "live_call_made": False,
                    "error": f"JSONDecodeError: {exc}",
                },
                review_report=review_plan,
            )
