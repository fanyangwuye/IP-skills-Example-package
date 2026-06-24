from .base import CreativeEngine, CreativeEngineRequest, CreativeEngineResult, EngineBlockedError
from .prompt_packs import build_prompt_pack
from .provider_adapter import build_provider_request, summarize_provider_request


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
        provider_request = build_provider_request(prompt_pack, provider=self.provider, model=self.model)
        return CreativeEngineResult(
            status="provider_request_ready",
            generation_source="live_llm_engine_dry_run",
            data={},
            warnings=["Live LLM provider request was built for review; no provider call was made."],
            raw_response={
                "prompt_pack": prompt_pack,
                "provider_request": provider_request,
                "provider_request_summary": summarize_provider_request(provider_request),
                "live_call_made": False,
            },
        )
