from typing import Any, Dict, List


REQUIRED_SCENE_CARD_FIELDS = ["visual", "voiceover", "duration_sec", "asset_goal"]
REQUIRED_SCRIPT_SCENE_FIELDS = ["visual", "voiceover", "dialogue", "start_sec", "end_sec"]

PRESSURE_MARKERS = ("开场", "突然", "危机", "异常", "规则", "反转", "不对劲", "死亡", "不能", "逼", "挡", "追", "逃", "发现", "暴涨", "倒计时")
EMOTION_MARKERS = ("震惊", "警觉", "恐惧", "犹豫", "愤怒", "克制", "紧张", "压迫", "缓和", "反转", "决心", "怀疑")
SUSPICIOUS_DETAIL_TERMS = (
    "手帕",
    "炸弹",
    "怪兽",
    "飞剑",
    "符箓",
    "丹炉",
    "枪",
    "手机",
    "红酒",
    "酒杯",
    "菜刀",
    "探测器",
    "托盘",
    "菜单",
    "账本",
)
COMMON_NON_NAMES = {"开场", "突然", "规则", "异常", "危机", "真正", "这里", "现在", "客人", "大厅", "饭店", "酒店", "菜单", "账本"}


def evaluate_scene_cards_quality(scene_cards: List[Dict[str, Any]], adapter_spec=None, context: Dict[str, Any] = None) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    warnings: List[str] = []
    cards = scene_cards or []
    context = context or {}
    if not cards:
        issues.append(_issue("blocker", "scene_cards_empty", "scene_cards must be a non-empty list"))
    for index, card in enumerate(cards, start=1):
        _check_required_fields(card, REQUIRED_SCENE_CARD_FIELDS, f"scene_card[{index}]", issues)
        if _looks_like_template(card.get("visual", "")):
            warnings.append(f"scene_card[{index}] visual still looks like scaffold text")
        if card.get("generation_source") in {"fallback_scaffold", "screenplay_scaffold"}:
            warnings.append(f"scene_card[{index}] uses {card.get('generation_source')}; review or replace with CreativeEngine output before final production")
        if not (card.get("asset_goal") or {}).get("type"):
            issues.append(_issue("warning", "asset_goal_type_missing", f"scene_card[{index}] asset_goal.type missing"))
    creative_checks = _evaluate_creative_cards(cards, context)
    warnings.extend(creative_checks.get("warnings", []))
    status = _status(issues)
    return {
        "quality_report_version": "1.1",
        "target": "scene_cards",
        "status": status,
        "score": _score(status, issues, warnings),
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "issues": issues,
        "warnings": warnings,
        "creative_checks": creative_checks,
        "recommendation": _recommendation(status, warnings),
    }


def evaluate_script_quality(script: Dict[str, Any], adapter_spec=None, polished: bool = False, context: Dict[str, Any] = None) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    warnings: List[str] = []
    context = _merge_context(script, context or {})
    scenes = script.get("scenes") or []
    if not scenes:
        issues.append(_issue("blocker", "script_scenes_empty", "script.scenes must be a non-empty list"))
    if adapter_spec and script.get("aspect_ratio") and script.get("aspect_ratio") != adapter_spec.default_aspect_ratio:
        issues.append(_issue("warning", "aspect_ratio_mismatch", f"expected {adapter_spec.default_aspect_ratio}, got {script.get('aspect_ratio')}"))
    for index, scene in enumerate(scenes, start=1):
        _check_required_fields(scene, REQUIRED_SCRIPT_SCENE_FIELDS, f"scene[{index}]", issues)
        if not scene.get("dialogue"):
            issues.append(_issue("warning", "dialogue_missing", f"scene[{index}] has no dialogue"))
        if scene.get("generation_source", "").startswith("fallback"):
            warnings.append(f"scene[{index}] uses {scene.get('generation_source')}; suitable as scaffold, not final creative output")
        if index == 1 and not _has_hook(scene):
            warnings.append("scene[1] may lack a clear opening hook or pressure point")
        if polished and not scene.get("conflict_notes"):
            issues.append(_issue("warning", "conflict_notes_missing", f"polished scene[{index}] missing conflict_notes"))
    handoff = script.get("handoff") or {}
    if not handoff.get("can_build_blueprint"):
        issues.append(_issue("warning", "handoff_blueprint_flag_missing", "handoff.can_build_blueprint should be true"))
    if adapter_spec:
        for key in ("image_requirements", "video_requirements", "music_requirements"):
            if key not in handoff:
                warnings.append(f"handoff.{key} missing; downstream checks may be weaker")
    creative_checks = _evaluate_creative_script(script, context, polished=polished)
    warnings.extend(creative_checks.get("warnings", []))
    status = _status(issues)
    return {
        "quality_report_version": "1.1",
        "target": "polished_script" if polished else "script_draft",
        "status": status,
        "score": _score(status, issues, warnings),
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "issues": issues,
        "warnings": warnings,
        "creative_checks": creative_checks,
        "recommendation": _recommendation(status, warnings),
    }


def _evaluate_creative_cards(cards: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
    source_text = str(context.get("source_text") or "")
    locked_names = _locked_character_names(context)
    combined_texts = [_card_text(card) for card in cards]
    warnings: List[str] = []
    warnings.extend(_unsupported_detail_warnings(combined_texts, source_text, "scene_card"))
    warnings.extend(_character_reference_warnings(combined_texts, locked_names, "scene_card"))
    hook_density = _hook_density(combined_texts)
    if cards and hook_density["pressure_ratio"] < 0.34:
        warnings.append("scene_cards may have weak hook density; fewer than one third of cards show clear pressure/new information")
    emotion_curve = _emotion_curve(combined_texts, cards)
    if cards and not emotion_curve["has_emotional_progression"]:
        warnings.append("scene_cards may lack a visible emotion curve or emotional turns")
    return {
        "check_version": "creative-quality-v1",
        "unsupported_details": _unsupported_details(combined_texts, source_text),
        "character_consistency": {
            "locked_names": locked_names,
            "unexpected_name_candidates": _unexpected_names(combined_texts, locked_names),
        },
        "hook_density": hook_density,
        "emotion_curve": emotion_curve,
        "warnings": warnings,
    }


def _evaluate_creative_script(script: Dict[str, Any], context: Dict[str, Any], polished: bool = False) -> Dict[str, Any]:
    source_text = str(context.get("source_text") or "")
    locked_names = _locked_character_names(context)
    scenes = script.get("scenes") or []
    scene_texts = [_scene_text(scene) for scene in scenes]
    warnings: List[str] = []
    warnings.extend(_unsupported_detail_warnings(scene_texts, source_text, "scene"))
    warnings.extend(_speaker_warnings(scenes, locked_names))
    warnings.extend(_character_reference_warnings(scene_texts, locked_names, "scene"))
    causality = _causality_signal(scene_texts)
    if scenes and causality["weak_transition_count"] >= max(2, len(scenes) // 2):
        warnings.append("script may have weak causal handoff between scenes; review action results and transitions")
    hook_density = _hook_density(scene_texts)
    if scenes and hook_density["pressure_ratio"] < 0.34:
        warnings.append("script may have weak hook density for short-drama pacing")
    emotion_curve = _emotion_curve(scene_texts, scenes)
    if scenes and not emotion_curve["has_emotional_progression"]:
        warnings.append("script may lack a trackable emotion curve")
    dialogue_voice = _dialogue_voice_check(scenes, locked_names)
    warnings.extend(dialogue_voice.get("warnings", []))
    return {
        "check_version": "creative-quality-v1",
        "unsupported_details": _unsupported_details(scene_texts, source_text),
        "character_consistency": {
            "locked_names": locked_names,
            "unexpected_name_candidates": _unexpected_names(scene_texts, locked_names),
        },
        "dialogue_voice": dialogue_voice,
        "causality": causality,
        "hook_density": hook_density,
        "emotion_curve": emotion_curve,
        "polished": polished,
        "warnings": warnings,
    }


def _merge_context(script: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(context or {})
    for key in ("source_text", "characters"):
        if key not in merged and script.get(key) not in (None, "", []):
            merged[key] = script.get(key)
    return merged


def _locked_character_names(context: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for item in context.get("characters") or []:
        if isinstance(item, dict):
            name = item.get("name") or item.get("character_name") or ((item.get("character_profile") or {}).get("identity") or {}).get("name")
        else:
            name = str(item)
        name = str(name or "").strip()
        if name and name not in names:
            names.append(name)
    return names[:12]


def _unsupported_details(texts: List[str], source_text: str) -> List[str]:
    unsupported = []
    for term in SUSPICIOUS_DETAIL_TERMS:
        if any(term in text for text in texts) and term not in source_text:
            unsupported.append(term)
    return unsupported


def _unsupported_detail_warnings(texts: List[str], source_text: str, label: str) -> List[str]:
    return [f"{label} introduces detail not found in source_text: {term}" for term in _unsupported_details(texts, source_text)]


def _unexpected_names(texts: List[str], locked_names: List[str]) -> List[str]:
    if not locked_names:
        return []
    unexpected: List[str] = []
    for text in texts:
        for candidate in _name_candidates(text):
            if candidate in COMMON_NON_NAMES or candidate in locked_names:
                continue
            if candidate not in unexpected:
                unexpected.append(candidate)
    return unexpected[:8]


def _character_reference_warnings(texts: List[str], locked_names: List[str], label: str) -> List[str]:
    warnings = []
    unexpected = _unexpected_names(texts, locked_names)
    if unexpected:
        warnings.append(f"{label} may reference unlocked character names: {', '.join(unexpected)}")
    if locked_names and texts and not any(name in " ".join(texts) for name in locked_names):
        warnings.append(f"{label} does not visibly reference any locked character names")
    return warnings


def _speaker_warnings(scenes: List[Dict[str, Any]], locked_names: List[str]) -> List[str]:
    warnings = []
    if not locked_names:
        return warnings
    for index, scene in enumerate(scenes, start=1):
        for line in scene.get("dialogue") or []:
            speaker = str((line or {}).get("speaker") or "").strip()
            if speaker and speaker not in locked_names:
                warnings.append(f"scene[{index}] dialogue speaker not in locked characters: {speaker}")
    return warnings


def _dialogue_voice_check(scenes: List[Dict[str, Any]], locked_names: List[str]) -> Dict[str, Any]:
    speaker_lines: Dict[str, List[str]] = {}
    generic_lines = []
    for scene in scenes:
        for line in scene.get("dialogue") or []:
            speaker = str((line or {}).get("speaker") or "").strip() or "unknown"
            text = str((line or {}).get("line") or "").strip()
            if text:
                speaker_lines.setdefault(speaker, []).append(text)
                if text in {"这里不对劲。", "你到底是谁？", "现在才发现，已经晚了。"}:
                    generic_lines.append(text)
    warnings = []
    if len(speaker_lines) > 1:
        fingerprints = {speaker: {_voice_fingerprint(line) for line in lines[:3]} for speaker, lines in speaker_lines.items()}
        flattened = [tuple(sorted(values)) for values in fingerprints.values()]
        if len(set(flattened)) < len(flattened):
            warnings.append("dialogue voice may be too similar across multiple speakers")
    if generic_lines:
        warnings.append("dialogue contains generic fallback-style lines; review character voice")
    return {
        "speakers": sorted(speaker_lines.keys()),
        "locked_names": locked_names,
        "generic_line_count": len(generic_lines),
        "warnings": warnings,
    }


def _voice_fingerprint(line: str) -> str:
    text = str(line or "")
    if any(mark in text for mark in ("？", "?")):
        return "question"
    if any(mark in text for mark in ("！", "!")):
        return "exclaim"
    if len(text) <= 8:
        return "short"
    return "statement"


def _causality_signal(texts: List[str]) -> Dict[str, Any]:
    transition_markers = ("因为", "所以", "发现", "于是", "转身", "进入", "离开", "挡住", "打开", "关上", "结果", "导致", "随后", "接着", "却")
    weak = 0
    for text in texts:
        if not any(marker in text for marker in transition_markers):
            weak += 1
    return {
        "scene_count": len(texts),
        "weak_transition_count": weak,
        "has_causal_language": weak < len(texts) if texts else False,
    }


def _hook_density(texts: List[str]) -> Dict[str, Any]:
    if not texts:
        return {"pressure_count": 0, "total": 0, "pressure_ratio": 0.0}
    pressure_count = sum(1 for text in texts if any(marker in text for marker in PRESSURE_MARKERS))
    return {
        "pressure_count": pressure_count,
        "total": len(texts),
        "pressure_ratio": round(pressure_count / max(len(texts), 1), 3),
    }


def _emotion_curve(texts: List[str], items: List[Dict[str, Any]]) -> Dict[str, Any]:
    markers = []
    for text in texts:
        for marker in EMOTION_MARKERS:
            if marker in text and marker not in markers:
                markers.append(marker)
    explicit_turns = []
    for item in items:
        for key in ("emotional_turn", "beat_function", "conflict_notes", "music_cue"):
            value = item.get(key)
            if value:
                explicit_turns.append(str(value))
    return {
        "emotion_markers": markers[:8],
        "explicit_turn_count": len(explicit_turns),
        "has_emotional_progression": bool(markers) or len(explicit_turns) >= 2,
    }


def _card_text(card: Dict[str, Any]) -> str:
    if not isinstance(card, dict):
        return ""
    parts = [card.get("visual", ""), card.get("voiceover", ""), card.get("subtitle", ""), card.get("music_cue", "")]
    asset_goal = card.get("asset_goal") or {}
    parts.extend(str(asset_goal.get(key, "")) for key in ("scene", "purpose", "expression"))
    return " ".join(str(part or "") for part in parts)


def _scene_text(scene: Dict[str, Any]) -> str:
    if not isinstance(scene, dict):
        return ""
    parts = [scene.get("visual", ""), scene.get("voiceover", ""), scene.get("action", ""), scene.get("subtitle", ""), scene.get("music_cue", "")]
    for note in scene.get("conflict_notes") or []:
        parts.append(str(note))
    for line in scene.get("dialogue") or []:
        parts.append(str((line or {}).get("speaker", "")))
        parts.append(str((line or {}).get("line", "")))
    return " ".join(str(part or "") for part in parts)


def _name_candidates(text: str) -> List[str]:
    import re

    candidates = re.findall(r"(?<![\u4e00-\u9fff])([\u4e00-\u9fff]{2,3})(?=(?:在|用|走|看|说|拿|背|端|站|坐|冲|推|发现|进入|离开|回到|盯着|望向|问|答))", text or "")
    return [item for item in candidates if item not in COMMON_NON_NAMES]


def _check_required_fields(item: Dict[str, Any], fields: List[str], label: str, issues: List[Dict[str, Any]]) -> None:
    if not isinstance(item, dict):
        issues.append(_issue("blocker", "invalid_object", f"{label} must be an object"))
        return
    for field in fields:
        if item.get(field) in (None, "", []):
            issues.append(_issue("warning", "required_field_missing", f"{label} missing required field: {field}"))


def _looks_like_template(text: str) -> bool:
    return any(marker in str(text or "") for marker in ("围绕该剧情点行动", "推进第", "核心场景"))


def _has_hook(scene: Dict[str, Any]) -> bool:
    text = " ".join(str(scene.get(key, "")) for key in ("visual", "voiceover", "action"))
    return any(marker in text for marker in PRESSURE_MARKERS)


def _issue(severity: str, code: str, message: str) -> Dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def _status(issues: List[Dict[str, Any]]) -> str:
    if any(item.get("severity") == "blocker" for item in issues):
        return "fail"
    if issues:
        return "warn"
    return "pass"


def _score(status: str, issues: List[Dict[str, Any]], warnings: List[str]) -> int:
    base = {"pass": 100, "warn": 78, "fail": 40}.get(status, 70)
    return max(base - len(issues) * 3 - len(warnings) * 2, 0)


def _recommendation(status: str, warnings: List[str]) -> str:
    if status == "fail":
        return "Fix blocker issues before downstream image/video handoff."
    if warnings:
        return "Review scaffold and creative-quality warnings before treating the output as final creative writing."
    return "Ready for downstream structured handoff review."
