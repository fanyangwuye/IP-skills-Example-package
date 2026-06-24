from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class EngineBlockedError(RuntimeError):
    """Raised when a creative engine would require an unapproved live call."""


@dataclass
class CreativeEngineRequest:
    kind: str
    source_text: str = ""
    creative_brief: Dict[str, Any] = field(default_factory=dict)
    format_name: str = "vertical_short_drama"
    schema_name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    allow_live: bool = False


@dataclass
class CreativeEngineResult:
    status: str
    generation_source: str
    data: Any = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    raw_response: Optional[Any] = None

    @property
    def ok(self) -> bool:
        return self.status == "success" and not self.errors


class CreativeEngine:
    engine_name = "base"

    def generate(self, request: CreativeEngineRequest) -> CreativeEngineResult:
        raise NotImplementedError