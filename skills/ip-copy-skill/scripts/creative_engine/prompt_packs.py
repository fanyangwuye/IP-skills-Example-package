import json
from typing import Any, Dict, List


PROMPT_PACK_VERSION = "copy-creative-prompt-pack-v1"


KIND_TASKS = {
    "source_analysis": "Analyze source material into structured story facts without inventing new plot.",
    "scene_cards": "Generate adaptation scene cards for downstream storyboard, image, and video planning.",
    "script_scenes": "Generate structured script scenes from locked scene cards and format constraints.",
    "polished_script_scenes": "Polish structured script scenes while preserving timing, scene order, characters, and plot facts.",
}


SCHEMA_CONTRACTS = {
    "scene_cards": {
        "root_type": "array",
        "item_required": ["visual", "voiceover", "duration_sec", "asset_goal"],
        "notes": [
            "visual must describe executable screen action, not abstract theme",
            "voiceover must be short enough for short-drama delivery",
            "asset_goal.type is required for downstream image tasks",
        ],
    },
    "script_scenes": {
        "root_type": "array",
        "item_required": ["visual", "voiceover", "dialogue", "start_sec", "end_sec"],
        "notes": [
            "dialogue must be a list of speaker/line objects",
            "do not change scene order or timing unless explicitly asked",
            "each scene needs one visible action result",
        ],
    },
    "source_analysis": {
        "root_type": "object",
        "item_required": ["characters", "world_rules", "plot_beats", "risk_notes"],
        "notes": ["only extract from source text", "mark uncertain facts as uncertain"],
    },
}


def build_prompt_pack(request) -> Dict[str, Any]:
    payload = request.payload or {}
    adapter_payload = payload.get("adapter") or {}
    schema_name = request.schema_name or request.kind
    contract = SCHEMA_CONTRACTS.get(schema_name, {"root_type": "object", "item_required": [], "notes": []})
    return {
        "prompt_pack_version": PROMPT_PACK_VERSION,
        "kind": request.kind,
        "format_name": request.format_name,
        "schema_name": schema_name,
        "task_goal": KIND_TASKS.get(request.kind, "Generate structured adaptation output."),
        "system_prompt": _system_prompt(request.kind, request.format_name),
        "user_prompt": _user_prompt(request, adapter_payload, contract),
        "response_contract": {
            "json_only": True,
            "schema_name": schema_name,
            "root_type": contract["root_type"],
            "item_required": contract["item_required"],
            "notes": contract["notes"],
        },
        "safety_constraints": _safety_constraints(),
        "quality_targets": _quality_targets(request.kind, adapter_payload),
        "metadata": {
            "source_text_chars": len(request.source_text or ""),
            "creative_brief_keys": sorted((request.creative_brief or {}).keys()),
            "payload_keys": sorted(payload.keys()),
            "allow_live_requested": bool(request.allow_live),
        },
    }


def _system_prompt(kind: str, format_name: str) -> str:
    return "\n".join(
        [
            "You are a professional screenwriting adaptation engine working under strict structure control.",
            f"Target format: {format_name}.",
            f"Task kind: {kind}.",
            "Use the source material as the authority. Do not invent unsupported plot facts.",
            "Return valid JSON only. Do not include markdown fences, commentary, or explanations.",
        ]
    )


def _user_prompt(request, adapter_payload: Dict[str, Any], contract: Dict[str, Any]) -> str:
    sections: List[str] = []
    sections.append(_section("Source Material", request.source_text or ""))
    sections.append(_section("Creative Brief", _json(request.creative_brief or {})))
    sections.append(_section("Format Constraints", _format_constraints(adapter_payload)))
    sections.append(_section("Task Payload", _json(_compact_payload(request.payload or {}))))
    sections.append(_section("Response Contract", _json(contract)))
    sections.append(
        _section(
            "Execution Rules",
            "\n".join(
                [
                    "Preserve locked character names and relationships.",
                    "Preserve source causality and do not add unsupported objects, powers, locations, or twists.",
                    "Write concrete visible actions that can become storyboard and video beats.",
                    "Keep platform-safe wording; avoid graphic gore, real-person names, and copyrighted franchise names.",
                    "If information is missing, use neutral placeholders inside JSON fields rather than inventing facts.",
                ]
            ),
        )
    )
    return "\n\n".join(sections)


def _format_constraints(adapter_payload: Dict[str, Any]) -> str:
    if not adapter_payload:
        return "No adapter payload supplied; follow the request schema strictly."
    fields = {
        "format_name": adapter_payload.get("format_name"),
        "structure_levels": adapter_payload.get("structure_levels"),
        "default_aspect_ratio": adapter_payload.get("default_aspect_ratio"),
        "rhythm_rules": adapter_payload.get("rhythm_rules"),
        "quality_checks": adapter_payload.get("quality_checks"),
        "handoff_requirements": adapter_payload.get("handoff_requirements"),
    }
    return _json(fields)


def _compact_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    compact = dict(payload)
    if "adapter" in compact:
        adapter = dict(compact["adapter"] or {})
        adapter.pop("task", None)
        adapter.pop("state", None)
        compact["adapter"] = adapter
    return compact


def _quality_targets(kind: str, adapter_payload: Dict[str, Any]) -> List[str]:
    targets = [
        "structure_fields_complete",
        "source_facts_preserved",
        "character_identity_consistent",
        "causality_clear",
        "downstream_image_video_handoff_ready",
    ]
    if kind in {"scene_cards", "script_scenes", "polished_script_scenes"}:
        targets.extend(
            [
                "opening_hook_or_pressure_visible",
                "each_10_to_15_seconds_has_new_information_or_pressure",
                "dialogue_short_and_playable",
            ]
        )
    for item in adapter_payload.get("quality_checks") or []:
        if item not in targets:
            targets.append(item)
    return targets


def _safety_constraints() -> List[str]:
    return [
        "no_unapproved_live_generation",
        "no_unapproved_new_plot_facts",
        "no_graphic_gore",
        "no_real_person_impersonation",
        "no_copyrighted_franchise_names_in_surface_output",
        "json_only_response",
    ]


def _section(title: str, body: str) -> str:
    return f"[{title}]\n{body}"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
