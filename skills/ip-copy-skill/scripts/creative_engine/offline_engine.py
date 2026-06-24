from .base import CreativeEngine, CreativeEngineRequest, CreativeEngineResult


class OfflineCreativeEngine(CreativeEngine):
    engine_name = "offline"

    def generate(self, request: CreativeEngineRequest) -> CreativeEngineResult:
        return CreativeEngineResult(
            status="fallback_required",
            generation_source="offline_engine",
            data={},
            warnings=[
                "OfflineCreativeEngine does not create final prose. Use deterministic scaffold or provide an approved live/mock engine."
            ],
        )