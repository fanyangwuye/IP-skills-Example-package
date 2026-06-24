from typing import Dict, List


ACTION_TERMS = ["跑", "奔", "追", "冲", "逃", "闪避", "格挡", "反击", "打", "撞", "扑", "扔", "抛", "投", "拔剑", "起势", "横刀", "出手", "攻防", "挥剑", "拔刀"]
INSERT_TERMS = ["特写", "超特写", "插入", "手部", "手指", "刀叉", "账本", "菜单", "符箓", "丹炉", "令牌", "探测器", "托盘"]
SPACE_TERMS = ["全景", "大厅", "街道", "荒原", "宗门", "大殿", "战场", "门口", "窗外", "走廊", "厨房", "饭店"]
RELATION_TERMS = ["对视", "隔着", "谈判", "争执", "逼近", "质问", "审视", "沉默"]
EMOTION_TERMS = ["表情", "眼神", "抬眼", "低声", "咬牙", "冷笑", "落泪", "凝视"]
DISCOVERY_TERMS = ["发现", "看见", "注意", "察觉", "异常", "原来", "规则", "系统", "探测器"]
REVERSAL_TERMS = ["反转", "变成", "揭示", "真相", "突然", "竟然", "不是", "真正"]
THRESHOLD_TERMS = ["门", "门槛", "入口", "出口", "进入", "走进", "穿过", "关门", "厨房门"]
XIANXIA_TERMS = ["渡劫", "天雷", "雷劫", "飞升", "顿悟", "心魔", "剑意", "灵力"]


def build_shot_director_plan(index: int, segment: Dict, visual: str, character_ids: List[str], scene_id: str, timing: Dict, continuity_state: Dict) -> Dict:
    """Build a structured, inspectable shot-design layer before prompt writing."""
    override = _normalize_override(segment.get("director_plan") or segment.get("shot_design") or {})
    beat_type = override.get("beat_type") or _beat_type(index, segment, visual)
    narrative_function = override.get("narrative_function") or segment.get("beat_function") or segment.get("purpose") or _narrative_function(beat_type)
    emotional_turn = _merge_emotional_turn(override.get("emotional_turn"), beat_type, visual)
    action_chain = _merge_action_chain(override.get("action_chain"), visual, continuity_state)
    framing = _merge_lens_field(override.get("framing"), _framing(index, len(character_ids), visual, beat_type), _framing_reason(visual, beat_type, character_ids))
    camera_motion = _merge_lens_field(override.get("camera_motion"), _camera_motion(index, visual, beat_type), _camera_reason(visual, beat_type))
    editing_intent = _merge_editing_intent(override.get("editing_intent"), beat_type, visual, timing)
    risks = _dedupe(_risk_flags(visual, timing, character_ids) + _as_list(override.get("continuity_risks")))
    quality_flags = _dedupe(_quality_flags(visual, timing, beat_type) + _as_list(override.get("quality_flags")))
    return {
        "director_plan_version": "1.0",
        "source": "segment_override" if override else "deterministic_fallback",
        "beat_type": beat_type,
        "narrative_function": narrative_function,
        "emotional_turn": emotional_turn,
        "action_chain": action_chain,
        "framing": framing,
        "camera_motion": camera_motion,
        "editing_intent": editing_intent,
        "continuity_risks": risks,
        "quality_flags": quality_flags,
        "scene_id": scene_id,
        "characters": character_ids,
    }


def director_plan_text(plan: Dict) -> str:
    if not plan:
        return ""
    framing = plan.get("framing") or {}
    camera = plan.get("camera_motion") or {}
    action = plan.get("action_chain") or {}
    emotion = plan.get("emotional_turn") or {}
    edit = plan.get("editing_intent") or {}
    return (
        f"节拍={plan.get('beat_type', '')}；功能={plan.get('narrative_function', '')}；"
        f"情绪={emotion.get('start', '')}->{emotion.get('turn', '')}->{emotion.get('end', '')}；"
        f"动作链=起点:{action.get('start', '')}，触发:{action.get('trigger', '')}，发展:{action.get('development', '')}，结果:{action.get('result', '')}；"
        f"景别={framing.get('value', '')}，理由={framing.get('reason', '')}；"
        f"运镜={camera.get('value', '')}，理由={camera.get('reason', '')}；"
        f"剪辑={edit.get('cut_reason', '')}，最少可读拍点={edit.get('minimum_readable_beats', '')}。"
    )


def _normalize_override(value) -> Dict:
    if not isinstance(value, dict):
        return {}
    return dict(value)


def _beat_type(index: int, segment: Dict, visual: str) -> str:
    explicit = str(segment.get("beat_type") or segment.get("story_function") or "").strip()
    if explicit:
        return explicit
    text = str(visual or "")
    if _has_any(text, INSERT_TERMS):
        return "insert_detail"
    if _has_any(text, XIANXIA_TERMS):
        return "spectacle_threshold"
    if _has_any(text, REVERSAL_TERMS):
        return "reversal"
    if _has_any(text, DISCOVERY_TERMS):
        return "discovery"
    if _has_any(text, ACTION_TERMS):
        return "action_pressure"
    if _has_any(text, RELATION_TERMS):
        return "confrontation"
    if _has_any(text, THRESHOLD_TERMS):
        return "threshold_transition"
    if index == 1:
        return "establishing_hook"
    return "story_progression"


def _narrative_function(beat_type: str) -> str:
    return {
        "establishing_hook": "开场建立主体、空间和第一个异常钩子",
        "discovery": "让角色发现可见异常并形成判断",
        "confrontation": "建立双方压力、眼线和关系冲突",
        "action_pressure": "用清楚动作推进危险和结果落点",
        "threshold_transition": "交代角色跨越边界、内外侧和威胁位置",
        "reversal": "揭示信息变化并给出情绪转折",
        "insert_detail": "用道具或局部细节交代剧情证据",
        "spectacle_threshold": "用大视觉事件表现临界状态和人物反应",
    }.get(beat_type, "推进剧情并保留明确动作结果")


def _merge_emotional_turn(value, beat_type: str, visual: str) -> Dict:
    fallback = _emotional_turn(beat_type, visual)
    if isinstance(value, dict):
        merged = dict(fallback)
        merged.update({k: v for k, v in value.items() if v})
        return merged
    return fallback


def _emotional_turn(beat_type: str, visual: str) -> Dict:
    if beat_type == "action_pressure":
        return {"start": "压迫逼近", "turn": "高度警觉、快速判断", "end": "求生或反击落点", "performance_note": "呼吸变浅，身体重心先动，眼神短促确认目标"}
    if beat_type == "confrontation":
        return {"start": "克制", "turn": "试探升级", "end": "压力停住", "performance_note": "眼神停顿、下颌收紧，不用夸张表情"}
    if beat_type == "discovery":
        return {"start": "正常动作", "turn": "发现异常", "end": "判断成形", "performance_note": "手上动作停半拍，视线转向异常点"}
    if beat_type == "reversal":
        return {"start": "已有判断", "turn": "信息被推翻", "end": "余震和新目标", "performance_note": "表情压住，只让眼神和呼吸变化"}
    if beat_type == "insert_detail":
        return {"start": "观察", "turn": "证据显露", "end": "观众读懂信息", "performance_note": "道具状态优先，人物反应可留到下一镜"}
    if beat_type == "spectacle_threshold":
        return {"start": "压抑", "turn": "临界爆发", "end": "震撼后停顿", "performance_note": "人物先承受光压或风压，再出现反应"}
    if _has_any(visual, ["雨", "夜", "暗", "黑", "雾", "黄泉", "诡异"]):
        return {"start": "不安", "turn": "气氛压低", "end": "悬疑推进", "performance_note": "动作放慢，听觉和视线寻找异常来源"}
    return {"start": "专注", "turn": "判断", "end": "推进", "performance_note": "动作真实克制，保留半拍反应"}


def _merge_action_chain(value, visual: str, continuity_state: Dict) -> Dict:
    fallback = _action_chain(visual, continuity_state)
    if isinstance(value, dict):
        merged = dict(fallback)
        merged.update({k: v for k, v in value.items() if v})
        merged["summary"] = _action_summary(merged)
        return merged
    return fallback


def _action_chain(visual: str, continuity_state: Dict) -> Dict:
    chain = {
        "start": continuity_state.get("current_start_state", "继承上一镜结束状态"),
        "trigger": _trigger_from_visual(visual),
        "development": continuity_state.get("main_action_transition") or visual,
        "result": continuity_state.get("current_end_state", "完成本镜动作结果"),
        "no_fill_rule": "不要用重复奔跑、重复转身或装饰运镜填满时长；必须有起点、触发、发展和结果落点。",
    }
    chain["summary"] = _action_summary(chain)
    return chain


def _action_summary(chain: Dict) -> str:
    return f"从{chain.get('start', '')}开始；因{chain.get('trigger', '')}触发；中段执行{chain.get('development', '')}；结束在{chain.get('result', '')}。{chain.get('no_fill_rule', '')}"


def _trigger_from_visual(visual: str) -> str:
    text = str(visual or "")
    if _has_any(text, DISCOVERY_TERMS):
        return "可见异常或新信息出现"
    if _has_any(text, ACTION_TERMS):
        return "危险压力或动作目标推动"
    if _has_any(text, THRESHOLD_TERMS):
        return "角色需要跨越空间边界"
    if _has_any(text, RELATION_TERMS):
        return "对方站位或视线形成压力"
    return "当前剧情节拍推进"


def _merge_lens_field(value, fallback_value: str, fallback_reason: str) -> Dict:
    if isinstance(value, dict):
        return {"value": value.get("value") or fallback_value, "reason": value.get("reason") or fallback_reason}
    if isinstance(value, str) and value.strip():
        return {"value": value.strip(), "reason": fallback_reason}
    return {"value": fallback_value, "reason": fallback_reason}


def _framing(index: int, n_characters: int, visual: str, beat_type: str) -> str:
    if beat_type == "insert_detail" or _has_any(visual, INSERT_TERMS):
        return "CU/ECU 道具或手部插入镜头，清楚交代关键物件状态"
    if beat_type in {"action_pressure", "spectacle_threshold"}:
        return "FS/MS 动作中景，能看清距离、脚步、方向和结果落点"
    if _has_any(visual, SPACE_TERMS) or beat_type == "establishing_hook":
        return "WS/MS 建立空间、主体和关键地标，不拉成无意义远景"
    if beat_type == "confrontation" or n_characters >= 2:
        return "MS/OTS 双人关系镜头，轴线、眼线和距离清楚"
    if _has_any(visual, EMOTION_TERMS):
        return "CU 人物脸部与眼神特写，保留微表情"
    if beat_type == "discovery":
        return "MS -> CU 从动作中景收向异常点或眼神落点"
    if index == 1:
        return "MS 建立主体和最近空间关系，不强制拉成远景"
    return "MS/CU 主体表演清楚"


def _framing_reason(visual: str, beat_type: str, character_ids: List[str]) -> str:
    if beat_type == "insert_detail":
        return "本镜功能是证据/道具读取，主体尺度必须让观众看懂物件状态。"
    if beat_type == "action_pressure":
        return "动作镜头优先读清距离、脚步和方向，避免只拍脸或乱晃。"
    if beat_type == "confrontation" or len(character_ids) >= 2:
        return "多角色关系需要固定轴线、互补眼线和可追踪距离。"
    if beat_type == "discovery":
        return "先保留角色动作，再收向异常点，形成叙事发现。"
    return "景别服务本镜故事功能，不做装饰性变化。"


def _camera_motion(index: int, visual: str, beat_type: str) -> str:
    if beat_type == "insert_detail":
        return "locked-off or tiny push-in，稳定拍清道具状态，不做装饰运镜"
    if beat_type == "action_pressure":
        return "controlled tracking or stable action follow，沿运动轴低幅跟随，结果点停住"
    if beat_type == "threshold_transition":
        return "dolly or lateral follow，拍清跨越边界的先后顺序和门内外关系"
    if beat_type == "confrontation":
        return "static or slow push，停在眼神和压力落点0.3-0.5秒"
    if beat_type == "discovery":
        return "slow push or rack attention，从角色动作引到异常点"
    if index == 1:
        return "slow establishing push，先交代主体与空间关系，再靠近叙事重点"
    return "static or slow push，优先保持表演和连续性"


def _camera_reason(visual: str, beat_type: str) -> str:
    if beat_type == "action_pressure":
        return "跟拍只服务动作可读性，不能用抖动掩盖空间关系。"
    if beat_type == "threshold_transition":
        return "边界镜头必须拍清谁先过门、内外侧和威胁停留位置。"
    if beat_type == "discovery":
        return "运镜从日常动作转向异常点，帮助观众理解信息变化。"
    if beat_type == "confrontation":
        return "静态或慢推能保留眼线压力和对峙节奏。"
    return "镜头运动服务情绪和动作结果，不做无因果炫技。"


def _merge_editing_intent(value, beat_type: str, visual: str, timing: Dict) -> Dict:
    fallback = _editing_intent(beat_type, visual, timing)
    if isinstance(value, dict):
        merged = dict(fallback)
        merged.update({k: v for k, v in value.items() if v})
        return merged
    return fallback


def _editing_intent(beat_type: str, visual: str, timing: Dict) -> Dict:
    duration = _positive_float(timing.get("duration_sec"), 0)
    beats = 3 if duration >= 5 else 2
    if beat_type == "action_pressure":
        beats = 4
    if beat_type == "insert_detail":
        beats = 2
    return {
        "cut_reason": _narrative_function(beat_type),
        "minimum_readable_beats": beats,
        "clip_split_hint": "如果本镜无法读清起点、动作和结果，拆分为更短生成单元，不改故事板内容。",
    }


def _risk_flags(visual: str, timing: Dict, character_ids: List[str]) -> List[str]:
    text = str(visual or "")
    risks = []
    if len(character_ids) >= 2:
        risks.append("multi_character_axis_and_eyeline")
    if _has_any(text, THRESHOLD_TERMS):
        risks.append("threshold_boundary_continuity")
    if _has_any(text, ["追", "逃", "奔", "跑"]):
        risks.append("chase_direction_continuity")
    if _has_any(text, ["扔", "抛", "投", "爆裂", "炸"]):
        risks.append("throw_direction_vs_body_direction")
    if _positive_float(timing.get("duration_sec"), 0) >= 12 and _has_any(text, ACTION_TERMS):
        risks.append("long_action_may_need_split_or_reaction_cut")
    return risks


def _quality_flags(visual: str, timing: Dict, beat_type: str) -> List[str]:
    flags = []
    duration = _positive_float(timing.get("duration_sec"), 0)
    if duration >= 12 and beat_type == "action_pressure":
        flags.append("long_action_needs_cutaway_or_reaction")
    if beat_type == "story_progression" and len(str(visual or "").strip()) < 12:
        flags.append("weak_visible_story_action")
    return flags


def _positive_float(value, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed > 0 else default


def _as_list(value) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _has_any(text: str, words: List[str]) -> bool:
    return any(word in str(text or "") for word in words)