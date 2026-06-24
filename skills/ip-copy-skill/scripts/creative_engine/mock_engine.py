from typing import Any, Dict

from .base import CreativeEngine, CreativeEngineRequest, CreativeEngineResult
from .schemas import validate_scene_cards, validate_script_scenes
from .review import review_creative_output


class MockCreativeEngine(CreativeEngine):
    engine_name = "mock"

    def __init__(self, outputs: Dict[str, Any] = None):
        self.outputs = outputs or {}

    def generate(self, request: CreativeEngineRequest) -> CreativeEngineResult:
        if request.kind not in self.outputs:
            return CreativeEngineResult(
                status="missing_mock_output",
                generation_source="mock_engine",
                errors=[f"missing mock output for kind: {request.kind}"],
            )
        data = self.outputs[request.kind]
        errors = _validate_by_schema(request.schema_name, data)
        review_report = review_creative_output(request, data, schema_errors=errors)
        return CreativeEngineResult(
            status="success" if not errors else "schema_error",
            generation_source="mock_engine",
            data=data,
            errors=errors,
            warnings=review_report.get("warnings", []),
            raw_response={"review_report": review_report},
            review_report=review_report,
        )


def _validate_by_schema(schema_name: str, data: Any):
    if schema_name == "scene_cards":
        return validate_scene_cards(data)
    if schema_name == "script_scenes":
        return validate_script_scenes(data)
    return []