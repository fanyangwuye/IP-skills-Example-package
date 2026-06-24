from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class FormatAdapterSpec:
    format_name: str
    structure_levels: List[str]
    default_aspect_ratio: str
    default_episode_duration_sec: int
    required_scene_card_fields: List[str]
    required_script_scene_fields: List[str]
    rhythm_rules: List[str]
    quality_checks: List[str]
    handoff_requirements: Dict[str, List[str]] = field(default_factory=dict)


class FormatAdapter:
    format_name = "base"

    def spec(self) -> FormatAdapterSpec:
        raise NotImplementedError

    def validate_scene_cards(self, scene_cards: List[Dict[str, Any]]) -> List[str]:
        spec = self.spec()
        errors: List[str] = []
        if not isinstance(scene_cards, list) or not scene_cards:
            return ["scene_cards must be a non-empty list"]
        for index, card in enumerate(scene_cards, start=1):
            if not isinstance(card, dict):
                errors.append(f"scene_card[{index}] must be an object")
                continue
            for field_name in spec.required_scene_card_fields:
                if card.get(field_name) in (None, "", []):
                    errors.append(f"scene_card[{index}] missing required field: {field_name}")
        return errors

    def creative_engine_payload(self, state: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        spec = self.spec()
        return {
            "format_name": spec.format_name,
            "structure_levels": spec.structure_levels,
            "default_aspect_ratio": spec.default_aspect_ratio,
            "rhythm_rules": spec.rhythm_rules,
            "quality_checks": spec.quality_checks,
            "handoff_requirements": spec.handoff_requirements,
            "state": state,
            "task": task,
        }