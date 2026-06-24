from .base import CreativeEngine, CreativeEngineRequest, CreativeEngineResult, EngineBlockedError


class LiveLLMEngine(CreativeEngine):
    engine_name = "live_llm"

    def __init__(self, provider: str = "", allow_live: bool = False):
        self.provider = provider or "unconfigured"
        self.allow_live = allow_live

    def generate(self, request: CreativeEngineRequest) -> CreativeEngineResult:
        if not (self.allow_live and request.allow_live):
            raise EngineBlockedError(
                "Live LLM generation is blocked by default. Set allow_live on both engine and request after explicit user approval."
            )
        return CreativeEngineResult(
            status="not_implemented",
            generation_source="live_llm_engine",
            errors=["Live LLM adapter is not implemented yet; no provider call was made."],
        )