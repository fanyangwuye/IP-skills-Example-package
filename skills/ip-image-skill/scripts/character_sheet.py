import copy
from typing import Dict, List, Optional


RECOMMENDED_FIELD_QUESTIONS = {
    "character_profile.identity.name": "这个角色叫什么名字？",
    "character_profile.identity.role": "这个角色在故事里是什么身份或定位？",
    "character_profile.appearance.ethnicity": "角色大致是什么外形人种或气质方向？",
    "character_profile.appearance.hair": "角色头发最核心的特征是什么？",
    "character_profile.appearance.face_shape": "角色脸型或面部辨识点是什么？",
    "character_profile.styling.wardrobe": "角色当前主服装方向是什么？",
    "character_profile.personality.aura": "角色给人的核心气场是什么？",
    "character_profile.world_context.genre": "这个角色所在作品是什么类型？",
    "character_profile.world_context.setting": "这个角色主要处在什么世界或场景背景里？",
    "asset_target.type": "这一轮你想先生成什么资产？例如头像、半身、全身、服装图。",
    "asset_target.purpose": "这张图的用途是什么？例如主视觉、设定图、封面、素材图。",
}


def empty_character_sheet(name: str = "") -> Dict:
    return {
        "character_profile": {
            "identity": {
                "name": name,
            },
            "appearance": {},
            "styling": {},
            "personality": {},
            "world_context": {},
        },
        "identity_anchors": [],
        "continuity_rules": [],
        "interaction_state": {
            "locked_traits": [],
            "pending_questions": [],
            "latest_user_direction": "",
            "decision_log": [],
        },
        "asset_target": {},
    }


def merge_character_sheet(base: Dict, update: Dict) -> Dict:
    merged = copy.deepcopy(base)
    _merge_into(merged, update)
    return merged


def build_task_from_character_sheet(
    sheet: Dict,
    output_dir: str,
    mode: str = "character_create",
    filename: Optional[str] = None,
    extra_task_fields: Optional[Dict] = None,
) -> Dict:
    task = {
        "mode": mode,
        "creation_stage": "character_creation",
        "current_focus": "locked identity plus current asset target",
        "character_profile": copy.deepcopy(sheet.get("character_profile", {})),
        "identity_anchors": copy.deepcopy(sheet.get("identity_anchors", [])),
        "continuity_rules": copy.deepcopy(sheet.get("continuity_rules", [])),
        "interaction_state": copy.deepcopy(sheet.get("interaction_state", {})),
        "asset_target": copy.deepcopy(sheet.get("asset_target", {})),
        "output_dir": output_dir,
    }

    if filename:
        task["filename"] = filename

    if extra_task_fields:
        _merge_into(task, extra_task_fields)
    return task


def build_asset_bundle_tasks(
    sheet: Dict,
    output_dir: str,
    asset_bundle: List[Dict],
    common_fields: Optional[Dict] = None,
) -> List[Dict]:
    tasks: List[Dict] = []
    common_fields = common_fields or {}

    for index, item in enumerate(asset_bundle, start=1):
        item = copy.deepcopy(item)
        label = item.get("label", f"asset_{index:02d}")
        asset_target = item.get("asset_target", {})

        extra_fields = copy.deepcopy(common_fields)
        extra_fields["mode"] = "character_create"
        extra_fields["asset_target"] = asset_target
        extra_fields["current_focus"] = item.get(
            "current_focus",
            f"generate bundle asset: {label}",
        )

        for key in (
            "prompt",
            "scene",
            "emotion",
            "pose",
            "camera",
            "composition",
            "lighting",
            "interaction_notes",
            "conversation_turns",
            "asset_kind",
            "asset_requirements",
        ):
            if key in item:
                extra_fields[key] = item[key]

        filename = item.get("filename", f"{label}.jpg")
        task = build_task_from_character_sheet(
            sheet,
            output_dir=output_dir,
            mode="character_create",
            filename=filename,
            extra_task_fields=extra_fields,
        )
        task["bundle_item_label"] = label
        tasks.append(task)

    return tasks


def apply_character_turn(sheet: Dict, turn_update: Dict) -> Dict:
    updated = copy.deepcopy(sheet)

    profile_update = turn_update.get("character_profile")
    if isinstance(profile_update, dict):
        _merge_into(updated.setdefault("character_profile", {}), profile_update)

    asset_target_update = turn_update.get("asset_target")
    if isinstance(asset_target_update, dict):
        _merge_into(updated.setdefault("asset_target", {}), asset_target_update)

    for list_key in ("identity_anchors", "continuity_rules"):
        additions = turn_update.get(list_key) or []
        if additions:
            updated.setdefault(list_key, [])
            for item in additions:
                if item not in updated[list_key]:
                    updated[list_key].append(item)

    state = updated.setdefault(
        "interaction_state",
        {
            "locked_traits": [],
            "pending_questions": [],
            "latest_user_direction": "",
            "decision_log": [],
        },
    )

    for item in turn_update.get("locked_traits", []) or []:
        if item not in state.setdefault("locked_traits", []):
            state["locked_traits"].append(item)

    latest_user_direction = str(turn_update.get("latest_user_direction", "")).strip()
    if latest_user_direction:
        state["latest_user_direction"] = latest_user_direction

    for note in turn_update.get("decision_log", []) or []:
        if note not in state.setdefault("decision_log", []):
            state["decision_log"].append(note)

    pending = list(state.get("pending_questions", []))
    for question in turn_update.get("pending_questions", []) or []:
        if question not in pending:
            pending.append(question)
    for resolved in turn_update.get("resolved_questions", []) or []:
        if resolved in pending:
            pending.remove(resolved)
    state["pending_questions"] = pending

    return updated


def collect_missing_fields(sheet: Dict) -> List[str]:
    missing: List[str] = []
    for dotted_path in RECOMMENDED_FIELD_QUESTIONS:
        value = _get_dotted(sheet, dotted_path)
        if not _has_meaningful_value(value):
            missing.append(dotted_path)
    return missing


def suggest_next_questions(sheet: Dict, max_questions: int = 3) -> List[str]:
    questions: List[str] = []
    for dotted_path in collect_missing_fields(sheet):
        question = RECOMMENDED_FIELD_QUESTIONS.get(dotted_path)
        if question and question not in questions:
            questions.append(question)
        if len(questions) >= max_questions:
            break
    return questions


def summarize_character_sheet(sheet: Dict) -> Dict:
    return {
        "identity": copy.deepcopy(sheet.get("character_profile", {}).get("identity", {})),
        "appearance": copy.deepcopy(sheet.get("character_profile", {}).get("appearance", {})),
        "styling": copy.deepcopy(sheet.get("character_profile", {}).get("styling", {})),
        "personality": copy.deepcopy(sheet.get("character_profile", {}).get("personality", {})),
        "world_context": copy.deepcopy(sheet.get("character_profile", {}).get("world_context", {})),
        "identity_anchors": copy.deepcopy(sheet.get("identity_anchors", [])),
        "continuity_rules": copy.deepcopy(sheet.get("continuity_rules", [])),
        "asset_target": copy.deepcopy(sheet.get("asset_target", {})),
        "interaction_state": copy.deepcopy(sheet.get("interaction_state", {})),
        "missing_fields": collect_missing_fields(sheet),
        "next_questions": suggest_next_questions(sheet),
    }


def _merge_into(target: Dict, update: Dict) -> None:
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_into(target[key], value)
        elif isinstance(value, list) and isinstance(target.get(key), list):
            existing = target[key]
            for item in value:
                if item not in existing:
                    existing.append(item)
        else:
            target[key] = copy.deepcopy(value)


def _get_dotted(payload: Dict, dotted_path: str):
    current = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _has_meaningful_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_has_meaningful_value(item) for item in value)
    if isinstance(value, dict):
        return any(_has_meaningful_value(item) for item in value.values())
    return True
