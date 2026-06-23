from typing import Dict, List


BRIDGE_TYPES = ["environment_cutaway", "prop_insert", "reaction_cutaway", "motion_bridge"]


def build_bridge_clips(task: Dict, clips: List[Dict]) -> List[Dict]:
    policy = task.get("bridge_clip_policy", "none")
    if policy not in {"none", "auto", "always"}:
        policy = "none"
    if policy == "none" or len(clips) < 2:
        return []

    bridges = []
    for index in range(len(clips) - 1):
        prev_clip = clips[index]
        next_clip = clips[index + 1]
        risk = _continuity_risk(prev_clip, next_clip)
        if policy == "always" or risk["level"] in {"medium", "high"}:
            bridges.append(_bridge_clip(index + 1, prev_clip, next_clip, risk, task))
    return bridges


def interleave_clips_with_bridges(clips: List[Dict], bridges: List[Dict]) -> List[Dict]:
    by_after = {bridge.get("after_clip_id"): bridge for bridge in bridges}
    result = []
    for clip in clips:
        result.append(clip)
        bridge = by_after.get(clip.get("clip_id"))
        if bridge:
            result.append(bridge)
    return result


def _continuity_risk(prev_clip: Dict, next_clip: Dict) -> Dict:
    reasons = []
    prev_scenes = set(prev_clip.get("scene_ids") or [])
    next_scenes = set(next_clip.get("scene_ids") or [])
    prev_chars = set(prev_clip.get("characters") or [])
    next_chars = set(next_clip.get("characters") or [])
    if prev_scenes != next_scenes:
        reasons.append("scene_change")
    if prev_chars != next_chars:
        reasons.append("character_set_change")
    if next_clip.get("previous_clip_end_frame") is None:
        reasons.append("no_hard_first_frame")
    if len(prev_chars | next_chars) >= 2:
        reasons.append("multi_character_axis_risk")
    level = "high" if "scene_change" in reasons else ("medium" if reasons else "low")
    return {"level": level, "reasons": reasons}


def _bridge_clip(index: int, prev_clip: Dict, next_clip: Dict, risk: Dict, task: Dict) -> Dict:
    bridge_id = f"bridge_{index:03d}_{index + 1:03d}"
    duration = float(task.get("bridge_clip_duration_sec") or 2.0)
    bridge_type = _bridge_type(task, prev_clip, next_clip, risk)
    scene_ids = next_clip.get("scene_ids") or prev_clip.get("scene_ids") or []
    timing = {
        "duration_sec": duration,
        "start_sec": (prev_clip.get("timing") or {}).get("end_sec"),
        "end_sec": ((prev_clip.get("timing") or {}).get("end_sec") or 0) + duration,
    }
    visual = _bridge_visual(bridge_type, prev_clip, next_clip)
    prompt = _bridge_prompt(bridge_id, bridge_type, visual, prev_clip, next_clip, risk)
    return {
        "clip_id": bridge_id,
        "bridge_clip": True,
        "bridge_type": bridge_type,
        "after_clip_id": prev_clip.get("clip_id", ""),
        "before_clip_id": next_clip.get("clip_id", ""),
        "timing": timing,
        "visual": visual,
        "characters": [],
        "scene_ids": scene_ids,
        "visual_lock": next_clip.get("visual_lock") or prev_clip.get("visual_lock", {}),
        "reference_binding": next_clip.get("reference_binding") or prev_clip.get("reference_binding", {}),
        "video_reference_images": next_clip.get("video_reference_images") or prev_clip.get("video_reference_images", []),
        "space_anchor_refs": next_clip.get("space_anchor_refs") or prev_clip.get("space_anchor_refs", []),
        "continuity_state": {
            "previous_end_state": (prev_clip.get("continuity_state") or {}).get("current_end_state", ""),
            "current_start_state": "桥接空镜承接上一镜情绪和环境声",
            "main_action_transition": visual,
            "current_end_state": "桥接空镜完成，准备切入下一人物镜头",
            "next_handoff": (next_clip.get("continuity_state") or {}).get("current_start_state", ""),
        },
        "clip_prompt": prompt,
        "i2v_prompt": prompt,
        "seedance_prompt": prompt,
        "t2v_prompt": prompt,
        "negative_prompt": (
            "不要新增主要人物正脸；不要背景音乐；不要歌曲；不要字幕；不要标题卡；不要伪文字；"
            "不要色彩跳变；不要曝光跳变；不要白平衡漂移；不要场景重置"
        ),
        "retry_advice": ["如果人物漂移，用纯环境空镜或道具特写重抽。", "如果色彩跳变，强调继承上一镜光源和白平衡。"],
        "quality_checks": [
            "桥接镜头是否避免主要人物正脸",
            "是否继承上一镜环境声、色彩、曝光和光源方向",
            "是否为下一镜换机位/换景别提供自然缓冲",
        ],
        "continuity_risk": risk,
    }


def _bridge_type(task: Dict, prev_clip: Dict, next_clip: Dict, risk: Dict) -> str:
    preferred = task.get("bridge_clip_type")
    if preferred in BRIDGE_TYPES:
        return preferred
    if risk.get("level") == "high":
        return "environment_cutaway"
    if prev_clip.get("characters") and next_clip.get("characters"):
        return "prop_insert"
    return "environment_cutaway"


def _bridge_visual(bridge_type: str, prev_clip: Dict, next_clip: Dict) -> str:
    scene_text = "、".join(next_clip.get("scene_ids") or prev_clip.get("scene_ids") or ["当前场景"])
    prev_end = _state_text(prev_clip, "current_end_state") or _clip_visual_tail(prev_clip)
    next_start = _state_text(next_clip, "current_start_state") or _clip_visual_tail(next_clip)
    if bridge_type == "prop_insert":
        return (
            f"{scene_text} 道具或局部承接特写：从上一镜尾态“{prev_end}”里的衣袖、手指、剑柄、脚步或道具余势切入，"
            f"落到与下一镜开始“{next_start}”直接相关的石阶纹理、门缝光线、桌面反光、系统光边缘或关键道具；"
            "同一光源、同一白平衡、同一空间方向，不出现主要人物完整正脸。"
        )
    if bridge_type == "reaction_cutaway":
        return (
            f"{scene_text} 局部反应镜头：承接上一镜尾态“{prev_end}”的呼吸、衣角、手指、肩背或侧脸边缘停顿，"
            f"把视线和身体方向引向下一镜开始“{next_start}”；避免主要人物完整正脸，避免换脸风险。"
        )
    if bridge_type == "motion_bridge":
        return (
            f"{scene_text} 运动桥接：把上一镜尾态“{prev_end}”的动作余势转移到同一阵风、同一道光、同一片尘雾、门扇轻动或衣摆余动上，"
            f"最后把运动方向导向下一镜开始“{next_start}”；运动是剪辑承接，不是随机空镜。"
        )
    return (
        f"{scene_text} 叙事空镜：承接上一镜尾态“{prev_end}”的环境声、光色和动作余势，"
        f"选择能引出下一镜开始“{next_start}”的具体空间锚点，例如同一方向的石阶边缘、残旗受风、石柱光边、门缝光或地面反光；"
        "空镜必须服务剪辑衔接和视线引导，不能只拍无关云雾或随机景物。"
    )


def _bridge_prompt(bridge_id: str, bridge_type: str, visual: str, prev_clip: Dict, next_clip: Dict, risk: Dict) -> str:
    return (
        f"{bridge_id} 桥接镜头，类型 {bridge_type}，时长约 1-3 秒。"
        f"画面：{visual}"
        "用途：遮挡上下镜头人物姿态、轴线、色彩或机位不连续的问题，让剪辑更自然。"
        "桥接画面必须由上一镜尾态和下一镜信息目标推导，不能只拍无关云雾、石阶或泛用环境素材。"
        "继承上一镜的环境声、天气/云雾/尘埃/室内空气状态、光源方向、色彩、曝光、白平衡和对比度；"
        "允许为下一镜换机位和换景别做缓冲，下一镜可以切到近景、特写、远景、全景、反打或侧背角度。"
        "优先拍环境、道具、背影、手部或局部动作，避免主要人物完整正脸，减少人脸漂移和AI模板脸风险。"
        "声音只保留现场环境声和拟音，例如雨声、灯火细响、门响、脚步远声、衣料轻响；禁止背景音乐、歌曲、音乐铺底和自动台词。"
        f"连续性风险：{risk.get('level')}，原因：{', '.join(risk.get('reasons') or [])}。"
        f"上一镜结束：{(prev_clip.get('continuity_state') or {}).get('current_end_state', '')}"
        f"下一镜开始：{(next_clip.get('continuity_state') or {}).get('current_start_state', '')}"
    )


def _state_text(clip: Dict, key: str) -> str:
    return str((clip.get("continuity_state") or {}).get(key) or "").strip()


def _clip_visual_tail(clip: Dict) -> str:
    visual = str(clip.get("visual") or "").strip()
    if not visual:
        return ""
    parts = [part.strip() for part in visual.replace("；", "。").split("。") if part.strip()]
    return parts[-1] if parts else visual
