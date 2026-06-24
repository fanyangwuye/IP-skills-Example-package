import json
from typing import Any, Dict, List


PROMPT_PACK_VERSION = "copy-creative-prompt-pack-v1"


KIND_TASKS = {
    "source_analysis": "Analyze source material into structured story facts without inventing new plot.",
    "scene_cards": "Generate adaptation scene cards for downstream storyboard, image, and video planning.",
    "script_scenes": "Generate structured script scenes from locked scene cards and format constraints.",
    "polished_script_scenes": "Polish structured script scenes while preserving timing, scene order, characters, and plot facts.",
}


TASK_INSTRUCTIONS = {
    "source_analysis": [
        "Extract characters, role functions, relationship facts, world rules, plot beats, unanswered questions, and risk notes.",
        "Separate confirmed facts from uncertain interpretation.",
        "Do not summarize away causality; preserve why each major event happens.",
    ],
    "scene_cards": [
        "Turn plot beats into executable visual scene cards for storyboard planning.",
        "Each card needs one visible action, one emotional turn, one source-grounded conflict, and one downstream asset goal.",
        "Do not add unsupported props, locations, monsters, powers, character relationships, or plot reversals.",
    ],
    "script_scenes": [
        "Expand locked scene cards into playable scenes while preserving order, duration, character set, and plot causality.",
        "Dialogue must reveal pressure, decision, or relationship change; avoid generic filler lines.",
        "Every scene should end with an action result or new information that hands off to the next scene.",
    ],
    "polished_script_scenes": [
        "Polish dialogue rhythm and conflict without changing scene order, timing, asset goals, or source facts.",
        "Keep original speaker intent and character status; tighten wording instead of replacing the scene.",
        "Add conflict notes only when they are supported by existing scene facts.",
    ],
}


SCHEMA_CONTRACTS = {
    "scene_cards": {
        "root_type": "array",
        "item_required": ["visual", "voiceover", "duration_sec", "asset_goal"],
        "notes": [
            "visual must describe executable screen action, not abstract theme",
            "voiceover must be short enough for short-drama delivery",
            "asset_goal.type is required for downstream image tasks",
            "each card should identify the scene, involved characters, and visible emotional turn when possible",
        ],
    },
    "script_scenes": {
        "root_type": "array",
        "item_required": ["visual", "voiceover", "dialogue", "start_sec", "end_sec"],
        "notes": [
            "dialogue must be a list of speaker/line objects",
            "do not change scene order or timing unless explicitly asked",
            "each scene needs one visible action result",
            "speaker voice must match the character voice contract",
        ],
    },
    "source_analysis": {
        "root_type": "object",
        "item_required": ["characters", "world_rules", "plot_beats", "risk_notes"],
        "notes": [
            "only extract from source text",
            "mark uncertain facts as uncertain",
            "include causality links and unanswered questions",
        ],
    },
}


GENRE_SIGNALS = [
    ("underworld_supernatural", ["黄泉", "阎王", "牛头", "马面", "鬼差", "地府", "冥", "阴间"]),
    ("xianxia_fantasy", ["修仙", "灵力", "飞剑", "渡劫", "宗门", "丹炉", "符箓", "仙"]),
    ("wasteland_survival", ["废土", "避难所", "荒原", "基地", "辐射", "生存"]),
    ("urban_suspense", ["探测器", "异常", "酒店", "饭店", "雨夜", "规则", "门口"]),
    ("romance_drama", ["甜宠", "婚约", "重逢", "心动", "误会", "情感"]),
    ("martial_action", ["追", "冲", "打", "刀", "剑", "拳", "爆炸", "投掷"]),
]


VOICE_HINTS = {
    "老板": ["calm authority", "businesslike control", "short decisions under pressure"],
    "店主": ["calm authority", "guarded confidence"],
    "员工": ["service posture", "brief operational replies"],
    "调查者": ["observant", "evidence-focused", "controlled urgency"],
    "主角": ["active decision-maker", "clear pressure response"],
    "怪物": ["threat presence", "minimal verbal complexity"],
}


def build_prompt_pack(request) -> Dict[str, Any]:
    payload = request.payload or {}
    adapter_payload = payload.get("adapter") or {}
    schema_name = request.schema_name or request.kind
    contract = SCHEMA_CONTRACTS.get(schema_name, {"root_type": "object", "item_required": [], "notes": []})
    diagnostics = _creative_diagnostics(request, adapter_payload)
    return {
        "prompt_pack_version": PROMPT_PACK_VERSION,
        "kind": request.kind,
        "format_name": request.format_name,
        "schema_name": schema_name,
        "task_goal": KIND_TASKS.get(request.kind, "Generate structured adaptation output."),
        "system_prompt": _system_prompt(request.kind, request.format_name),
        "user_prompt": _user_prompt(request, adapter_payload, contract, diagnostics),
        "response_contract": {
            "json_only": True,
            "schema_name": schema_name,
            "root_type": contract["root_type"],
            "item_required": contract["item_required"],
            "notes": contract["notes"],
        },
        "creative_diagnostics": diagnostics,
        "task_instructions": TASK_INSTRUCTIONS.get(request.kind, ["Generate structured adaptation output under the response contract."]),
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
            "Follow the character voice, causality, rhythm, and quality gate contracts before writing any output field.",
            "Return valid JSON only. Do not include markdown fences, commentary, or explanations.",
        ]
    )


def _user_prompt(request, adapter_payload: Dict[str, Any], contract: Dict[str, Any], diagnostics: Dict[str, Any]) -> str:
    sections: List[str] = []
    sections.append(_section("Source Material", request.source_text or ""))
    sections.append(_section("Creative Brief", _json(request.creative_brief or {})))
    sections.append(_section("Detected Creative Diagnostics", _json(diagnostics)))
    sections.append(_section("Format Constraints", _format_constraints(adapter_payload)))
    sections.append(_section("Task Payload", _json(_compact_payload(request.payload or {}))))
    sections.append(_section("Task Instructions", _json(TASK_INSTRUCTIONS.get(request.kind, []))))
    sections.append(_section("Response Contract", _json(contract)))
    sections.append(_section("Quality Gate Before Final JSON", _json(_quality_gate(request.kind))))
    sections.append(
        _section(
            "Execution Rules",
            "\n".join(
                [
                    "Preserve locked character names and relationships.",
                    "Preserve source causality and do not add unsupported objects, powers, locations, or twists.",
                    "Write concrete visible actions that can become storyboard and video beats.",
                    "Use the character voice contract; do not give all characters the same generic tone.",
                    "Keep platform-safe wording; avoid graphic gore, real-person names, and copyrighted franchise names.",
                    "If information is missing, use neutral placeholders inside JSON fields rather than inventing facts.",
                ]
            ),
        )
    )
    return "\n\n".join(sections)


def _creative_diagnostics(request, adapter_payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = request.payload or {}
    source_text = request.source_text or ""
    creative_brief = request.creative_brief or {}
    characters = _characters_from_payload(payload)
    scene_cards = payload.get("scene_cards") or []
    script = payload.get("script") or {}
    story_beats = payload.get("story_beats") or []
    return {
        "genre_profile": _genre_profile(source_text, creative_brief),
        "character_voice_contract": _character_voice_contract(characters, source_text),
        "causality_contract": _causality_contract(source_text, story_beats, scene_cards, script),
        "rhythm_contract": _rhythm_contract(request.kind, adapter_payload, payload),
        "forbidden_drift": _forbidden_drift(request.kind),
    }


def _genre_profile(source_text: str, creative_brief: Dict[str, Any]) -> Dict[str, Any]:
    combined = f"{source_text} {_json(creative_brief)}"
    matched = []
    for label, terms in GENRE_SIGNALS:
        score = sum(1 for term in terms if term in combined)
        if score:
            matched.append({"label": label, "score": score})
    matched.sort(key=lambda item: (-item["score"], item["label"]))
    primary = matched[0]["label"] if matched else "general_short_drama"
    return {
        "primary": primary,
        "signals": matched[:4],
        "tone_request": creative_brief.get("tone", ""),
        "viewpoint": creative_brief.get("viewpoint", ""),
        "adaptation_boundary": "use genre signals only to guide tone and visual logic; do not add unsupported lore",
    }


def _characters_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    characters = payload.get("characters") or []
    if not characters and isinstance(payload.get("script"), dict):
        characters = payload.get("script", {}).get("characters") or []
    normalized = []
    for item in characters:
        if isinstance(item, dict):
            normalized.append(item)
        elif item:
            normalized.append({"name": str(item)})
    return normalized[:8]


def _character_voice_contract(characters: List[Dict[str, Any]], source_text: str) -> List[Dict[str, Any]]:
    contracts = []
    for character in characters:
        name = str(character.get("name") or character.get("character_name") or "角色").strip() or "角色"
        role = str(character.get("role") or character.get("identity", {}).get("role") or "").strip()
        hints = []
        for key, values in VOICE_HINTS.items():
            if key in name or key in role or key in source_text:
                hints.extend(values)
        if not hints:
            hints = ["source-grounded", "distinct from other speakers", "short playable lines"]
        contracts.append(
            {
                "name": name,
                "role": role or "unspecified; infer only from source evidence",
                "voice_rules": _dedupe_list(hints),
                "dialogue_limits": [
                    "avoid generic catchphrases",
                    "line should expose pressure, decision, evidence, or relationship change",
                    "do not mention facts this character cannot know",
                ],
            }
        )
    if not contracts:
        contracts.append(
            {
                "name": "source_characters",
                "role": "extract from source before writing",
                "voice_rules": ["separate each speaker by role and knowledge state"],
                "dialogue_limits": ["do not invent new named characters"],
            }
        )
    return contracts


def _causality_contract(source_text: str, story_beats: List[Any], scene_cards: List[Any], script: Dict[str, Any]) -> Dict[str, Any]:
    beat_texts = [str(item) for item in story_beats if item]
    for card in scene_cards if isinstance(scene_cards, list) else []:
        if isinstance(card, dict):
            beat_texts.append(str(card.get("visual") or card.get("voiceover") or ""))
    for scene in script.get("scenes") or [] if isinstance(script, dict) else []:
        if isinstance(scene, dict):
            beat_texts.append(str(scene.get("visual") or scene.get("action") or scene.get("voiceover") or ""))
    return {
        "source_authority": "source_text and locked payload outrank inferred genre pattern",
        "known_sequence": [item for item in beat_texts[:10] if item],
        "cause_effect_rules": [
            "every new action must have a source-grounded setup or visible motivation",
            "do not reverse spatial direction, chase direction, entry/exit state, or object ownership without explanation",
            "do not introduce a prop unless it appears in source, locked payload, or is required by adapter handoff",
            "if a beat cannot be causally connected, mark it as uncertain instead of forcing it",
        ],
        "source_excerpt_for_fact_check": source_text[:500],
    }


def _rhythm_contract(kind: str, adapter_payload: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    duration = payload.get("total_duration_sec") or payload.get("duration_sec") or adapter_payload.get("default_episode_duration_sec") or 90
    return {
        "target_duration_sec": duration,
        "beat_interval_sec": "10-15" if kind in {"scene_cards", "script_scenes", "polished_script_scenes"} else "analysis_only",
        "opening_rule": "first 3 seconds must expose conflict, reversal, abnormal rule, danger, or decision pressure",
        "midpoint_rule": "add new information or pressure before action becomes repetitive",
        "ending_rule": "end with an unresolved question, action handoff, or emotionally charged decision",
        "adapter_rhythm_rules": adapter_payload.get("rhythm_rules") or [],
    }


def _forbidden_drift(kind: str) -> List[str]:
    base = [
        "do not add unsupported plot facts",
        "do not merge characters",
        "do not rename locked characters",
        "do not change role relationships",
        "do not replace source setting with a generic setting",
        "do not add random props such as handkerchiefs, weapons, monsters, or devices unless source-grounded",
        "do not create action that contradicts spatial direction or entry/exit state",
    ]
    if kind == "polished_script_scenes":
        base.extend(["do not rewrite the whole scene", "do not change scene timing", "do not remove asset goals"])
    return base


def _quality_gate(kind: str) -> Dict[str, Any]:
    return {
        "before_returning_json_check": [
            "all required fields are present",
            "every invented-looking detail is supported by source or locked payload",
            "character dialogue follows character_voice_contract",
            "scene order and timing match locked payload unless explicitly instructed",
            "visual actions are storyboardable and video-executable",
            "opening/midpoint/ending rhythm contract is visible when applicable",
        ],
        "reject_or_mark_uncertain_when": [
            "source facts are missing",
            "causality between beats is unclear",
            "a character's knowledge state is unsupported",
        ],
        "kind": kind,
    }


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
        "character_voice_distinct",
        "causality_clear",
        "no_unsupported_plot_drift",
        "downstream_image_video_handoff_ready",
    ]
    if kind in {"scene_cards", "script_scenes", "polished_script_scenes"}:
        targets.extend(
            [
                "opening_hook_or_pressure_visible",
                "each_10_to_15_seconds_has_new_information_or_pressure",
                "dialogue_short_and_playable",
                "visible_action_result_per_scene",
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


def _dedupe_list(items: List[str]) -> List[str]:
    result = []
    seen = set()
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result
