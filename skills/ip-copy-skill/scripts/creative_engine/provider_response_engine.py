from .base import CreativeEngine, CreativeEngineRequest, CreativeEngineResult
from .provider_execution import normalize_provider_response_to_result


class ProviderResponseEngine(CreativeEngine):
    engine_name = "provider_response"

    def __init__(self, provider_response, provider: str = "", model: str = ""):
        self.provider_response = provider_response
        self.provider = provider or "generic"
        self.model = model or ""

    def generate(self, request: CreativeEngineRequest) -> CreativeEngineResult:
        return normalize_provider_response_to_result(
            request,
            self.provider_response,
            provider_request={"provider": self.provider, "model": self.model},
        )
