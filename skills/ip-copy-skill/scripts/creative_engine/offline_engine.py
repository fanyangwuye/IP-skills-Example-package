from .base import CreativeEngine, CreativeEngineRequest, CreativeEngineResult
from .prompt_packs import build_prompt_pack


class OfflineCreativeEngine(CreativeEngine):
    engine_name = "offline"

    def generate(self, request: CreativeEngineRequest) -> CreativeEngineResult:
        prompt_pack = build_prompt_pack(request)
        return CreativeEngineResult(
            status="fallback_required",
            generation_source="offline_engine",
            data={},
            warnings=[
                "OfflineCreativeEngine does not create final prose. Use deterministic scaffold or provide an approved live/mock engine."
            ],
            raw_response={"prompt_pack": prompt_pack, "live_call_made": False},
        )
