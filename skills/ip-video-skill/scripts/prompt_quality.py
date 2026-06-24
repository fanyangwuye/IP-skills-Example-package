from typing import Dict, List

try:
    from .martial_arts import build_martial_arts_layer, is_martial_arts_scene, martial_arts_text
    from .shot_director import director_plan_text
except ImportError:
    from martial_arts import build_martial_arts_layer, is_martial_arts_scene, martial_arts_text
    from shot_director import director_plan_text


def build_prompt_profile(index: int, visual: str, storyboard_card: Dict, continuity_state: Dict, visual_lock: Dict) -> Dict:
    duration = _duration_text(storyboard_card)
    director_plan = storyboard_card.get("director_plan") or {}
    emotional_turn = director_plan.get("emotional_turn") or {}
    emotion = "、".join(item for item in [emotional_turn.get("start"), emotional_turn.get("turn"), emotional_turn.get("end")] if item) or _emotion_from_visual(visual)
    scene = visual_lock.get("scene") or {}
    style = visual_lock.get("style") or {}
    characters = visual_lock.get("characters") or {}
    martial_arts_layer = (
        build_martial_arts_layer(visual, storyboard_card, continuity_state)
        if is_martial_arts_scene(visual, storyboard_card.get("action_scene_type", ""))
        else {}
    )
    return {
        "shot_id": storyboard_card.get("shot_id", ""),
        "duration": duration,
        "narrative_intent": storyboard_card.get("story_function", "推进剧情"),
        "director_plan": director_plan,
        "director_intent": director_plan_text(director_plan),
        "action_flow": _action_flow(visual, continuity_state, director_plan),
        "martial_arts_layer": martial_arts_layer,
        "performance_control": _performance_control(emotion, characters, director_plan),
        "camera_control": _camera_control(storyboard_card, emotion, director_plan),
        "spatial_continuity": _spatial_continuity(storyboard_card, continuity_state),
        "lighting_texture": _lighting_texture(scene, style),
        "sound_design": _sound_design(storyboard_card),
        "realism_anchors": _realism_anchors(characters, scene),
        "execution_constraints": _execution_constraints(storyboard_card),
        "retry_advice": _retry_advice(storyboard_card),
    }

def compose_i2v_prompt(visual: str, profile: Dict, reference_binding: Dict) -> str:
    return "\n".join(
        [
            f"[镜头 | {profile['duration']}]",
            "图生视频。严格使用参考图锁定角色脸、发型、服饰、道具、场景布局、光源方向和整体色调；参考图只贡献其指定属性，不互相污染。",
            f"叙事目标：{profile['narrative_intent']}。",
            _optional_line("导演设计", profile.get("director_intent", "")),
            f"画面内容：{visual}",
            f"动作流程：{profile['action_flow']}",
            _optional_line("武戏调度", martial_arts_text(profile.get("martial_arts_layer") or {})),
            f"表演控制：{profile['performance_control']}",
            f"镜头控制：{profile['camera_control']}",
            f"空间连续性：{profile['spatial_continuity']}",
            f"光线与质感：{profile['lighting_texture']}",
            f"声音：{profile['sound_design']}",
            f"真实感锚点：{profile['realism_anchors']}",
            f"执行边界：{profile['execution_constraints']}",
            f"参考绑定：{_binding_text(reference_binding)}",
        ]
    )


def compose_t2v_prompt(visual: str, profile: Dict, visual_lock: Dict) -> str:
    return "\n".join(
        [
            f"[镜头 | {profile['duration']}]",
            "文生视频仅用于快速构图和动作预览；如果需要角色脸、服装和质感稳定，必须改用角色参考图和正常场景参考图做图生视频。",
            "按连续性圣经生成同一角色和同一场景，不能把新镜头当作独立重启。",
            f"叙事目标：{profile['narrative_intent']}。",
            _optional_line("导演设计", profile.get("director_intent", "")),
            f"画面内容：{visual}",
            f"动作流程：{profile['action_flow']}",
            _optional_line("武戏调度", martial_arts_text(profile.get("martial_arts_layer") or {})),
            f"角色锁定：{_character_lock_text(visual_lock.get('characters') or {})}",
            f"场景锁定：{_scene_lock_text(visual_lock.get('scene') or {})}",
            f"表演控制：{profile['performance_control']}",
            f"镜头控制：{profile['camera_control']}",
            f"空间连续性：{profile['spatial_continuity']}",
            f"光线与质感：{profile['lighting_texture']}",
            f"声音：{profile['sound_design']}",
            f"真实感锚点：{profile['realism_anchors']}",
            f"执行边界：{profile['execution_constraints']}",
        ]
    )


def compose_seedance_prompt(visual: str, profile: Dict, reference_binding: Dict) -> str:
    return "\n".join(
        [
            f"[镜头 | {profile['duration']}]",
            _optional_line("导演设计", profile.get("director_intent", "")),
            f"画面内容：{visual}",
            _optional_line("武戏调度", martial_arts_text(profile.get("martial_arts_layer") or {})),
            f"表演控制：{profile['performance_control']}",
            f"镜头控制：{profile['camera_control']}",
            f"空间连续性：{profile['spatial_continuity']}",
            f"光线与质感：{profile['lighting_texture']}",
            f"声音：{profile['sound_design']}",
            f"执行边界：{profile['execution_constraints']}",
            f"参考图绑定：{_binding_text(reference_binding)}",
        ]
    )


def build_negative_prompt(multichar: bool, action_scene: bool = False, style: Dict = None) -> str:
    profile = build_negative_prompt_profile(multichar, action_scene, style or {})
    return "；".join(profile["provider_negative_prompt"])


def build_negative_prompt_profile(multichar: bool, action_scene: bool = False, style: Dict = None) -> Dict:
    style = style or {}
    critical_identity = [
        "不要换脸",
        "不要改变发型",
        "不要改变服装颜色和材质",
        "不要新增无关人物",
        "不要道具凭空出现或消失",
    ]
    spatial = ["不要重置场景布局", "不要改变光源方向"]
    model_artifacts = [
        "不要塑料皮肤",
        "不要AI模板脸",
        "不要玻璃珠眼睛",
        "不要完美对称五官",
        "不要字幕乱码或伪文字",
        "不要画面字幕",
        "不要片头片尾文字",
        "不要背景音乐",
        "不要歌曲",
        "不要音乐铺底",
    ]
    if multichar:
        spatial.extend(["不要越轴", "不要屏幕方向翻转", "不要视线同向错位", "不要人物距离瞬移"])
    action_safety = []
    if action_scene:
        action_safety.extend(["无血腥", "无伤口特写", "无暴力血浆", "不要招式文字", "不要动作轨迹线", "不要肢体断裂"])
    style_negatives = _style_negative_items(style)
    provider_negative = _dedupe(critical_identity + spatial + model_artifacts[:8] + action_safety[:5] + style_negatives[:8])
    audit_negative = _dedupe(critical_identity + spatial + model_artifacts + action_safety + style_negatives)
    return {
        "critical_identity_negatives": critical_identity,
        "spatial_negatives": spatial,
        "model_artifact_negatives": model_artifacts,
        "action_safety_negatives": action_safety,
        "style_negatives": style_negatives,
        "provider_negative_prompt": provider_negative,
        "audit_negative_prompt": audit_negative,
        "length_policy": "provider_negative_prompt keeps identity, spatial, artifact, action, and style negatives in priority order",
    }


def build_retry_advice(profile: Dict, multichar: bool) -> List[str]:
    advice = list(profile.get("retry_advice") or [])
    shot_id = profile.get("shot_id") or "this shot"
    camera = str(profile.get("camera_control") or "")
    spatial = str(profile.get("spatial_continuity") or "")
    action_flow = str(profile.get("action_flow") or "")
    advice.extend(
        [
            f"{shot_id}: 如果脸漂移，缩短本镜动作幅度，优先使用锁脸参考，并把脸部保持在同一光源方向。",
            f"{shot_id}: 如果服装变色，降低场景色光污染，重申服饰款式、材质、颜色和状态不变。",
            f"{shot_id}: 如果场景重置，使用同一正常场景参考图，重申门、柜台、窗、道路、石阶等可见地标位置。",
        ]
    )
    if multichar:
        advice.extend(
            [
                f"{shot_id}: 如果越轴，按本镜空间连续性重申屏幕左右关系，机位固定在轴线同一侧。",
                f"{shot_id}: 如果视线错位，重申双方视线互补且高度匹配，不要让两人看向同一侧。",
            ]
        )
    if any(word in camera for word in ["handheld", "tracking", "action follow", "跟随"]):
        advice.append(f"{shot_id}: 如果运镜太晃，改成低幅稳定跟拍，只在命中点或情绪点短暂停留。")
    if profile.get("martial_arts_layer"):
        advice.append(f"{shot_id}: 如果动作糊成一团，拆成起势、一次攻防、反应停顿、收势四拍，用中景拍清距离和脚步。")
    if any(word in action_flow for word in ["门", "窗", "入口", "出口", "穿过", "关门"]):
        advice.append(f"{shot_id}: 如果门窗/出入口空间错乱，明确内外侧、谁先过门、威胁停在哪一侧，再重抽。")
    if "scene anchor" in spatial or "场景" in spatial:
        advice.append(f"{shot_id}: 如果空间地标跳位，降低镜头运动复杂度，保留一个前景/后景地标作为连续锚点。")
    return _dedupe(advice)


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result
def _style_negative_items(style: Dict) -> List[str]:
    items = []
    for key in ("forbidden_drift", "style_realism_constraints"):
        for value in style.get(key) or []:
            text = str(value or "").strip()
            if not text:
                continue
            if text.startswith("avoid "):
                text = "不要" + text[len("avoid "):]
            elif text.startswith("no "):
                text = "不要" + text[len("no "):]
            elif text.startswith("keep "):
                continue
            items.append(text)
    return _dedupe(items)
def _duration_text(storyboard_card: Dict) -> str:
    timing = storyboard_card.get("timing") or {}
    duration = timing.get("duration_sec")
    if duration:
        return f"{duration:g}秒"
    return "按上游 timing 时长执行"


def _action_flow(visual: str, continuity_state: Dict, director_plan: Dict = None) -> str:
    action_chain = ((director_plan or {}).get("action_chain") or {})
    if action_chain.get("summary"):
        return action_chain["summary"]
    return (
        f"从「{continuity_state['current_start_state']}」开始；"
        f"中段只执行一个主动作「{continuity_state['main_action_transition'] or visual}」；"
        f"结束在「{continuity_state['current_end_state']}」。动作不要瞬间到位，保留半拍迟疑、呼吸和结果落点。"
    )


def _performance_control(emotion: str, characters: Dict, director_plan: Dict = None) -> str:
    names = "、".join(lock.get("name", char_id) for char_id, lock in characters.items()) or "镜头主体"
    emotional_turn = ((director_plan or {}).get("emotional_turn") or {})
    performance_note = emotional_turn.get("performance_note") or "只安排1-2个微动作，例如视线短暂停住、眼睑收紧、手指微收、下颌轻压、呼吸变浅。"
    beat_type = (director_plan or {}).get("beat_type", "")
    return (
        f"{names}保持克制真实表演，当前情绪为{emotion}，镜头节拍={beat_type}。"
        f"{performance_note}"
        "情绪主要放在眼神、嘴角、呼吸和停顿里，不做夸张舞台化表情。"
        "动作不要瞬间到位，先有迟疑、判断或呼吸，再执行。"
    )

def _camera_control(storyboard_card: Dict, emotion: str, director_plan: Dict = None) -> str:
    framing = storyboard_card.get("framing", "MS 主体清楚")
    motion = storyboard_card.get("camera_motion", "stable observation")
    framing_reason = (((director_plan or {}).get("framing") or {}).get("reason") or "景别服务本镜故事功能")
    camera_reason = (((director_plan or {}).get("camera_motion") or {}).get("reason") or "镜头运动服务情绪和动作结果")
    return (
        f"{framing}；{motion}。镜头运动服务于{emotion}，不要装饰性乱动。"
        f"景别理由：{framing_reason}；运镜理由：{camera_reason}。"
        "先让观众看清主体和空间关系，再在情绪落点短暂停留0.3-0.5秒。"
    )

def _spatial_continuity(storyboard_card: Dict, continuity_state: Dict) -> str:
    return (
        f"起始态必须继承上一镜：{continuity_state['current_start_state']}。"
        f"轴线：{storyboard_card['axis']['line']}；屏幕方向：{storyboard_card['screen_direction']}；"
        f"视线：{storyboard_card['eyeline']}。人物距离、前后景、高低关系和道具所在手必须可追踪。"
    )


def _lighting_texture(scene: Dict, style: Dict) -> str:
    lighting = scene.get("lighting_lock") or style.get("lighting_policy") or "电影化自然光，保持光源方向连续"
    palette = scene.get("palette_lock") or style.get("color_grade") or "低漂移电影色调"
    atmosphere = scene.get("weather_atmosphere_lock") or "环境氛围与上一镜一致"
    style_direction = style.get("style_direction", "")
    positive = "，".join((style.get("style_positive_fragments") or [])[:5])
    realism = "，".join((style.get("style_realism_constraints") or [])[:5])
    style_note = ""
    if style_direction or positive or realism:
        style_note = f"风格卡约束：{style_direction}；正向质感={positive}；真实感约束={realism}。"
    return (
        f"主光逻辑：{lighting}；色调：{palette}；环境：{atmosphere}。"
        f"{style_note}"
        "保留自然明暗层次，不要全脸打平。皮肤有毛孔、轻微眼周纹理和自然肤色变化；"
        "眼睛不要玻璃珠高光，五官不要完美对称，脸部保留一侧眼睑略沉、嘴角轻微不对称、下颌与法令区自然层次；"
        "头发有碎发边缘，布料有压痕和褶皱，场景表面有灰尘、水痕、划痕或不规则反光。"
    )


def _sound_design(storyboard_card: Dict) -> str:
    sound = storyboard_card.get("sound_subtitle") or {}
    parts = []
    if sound.get("voiceover"):
        parts.append(f"旁白内容仅作为剪辑参考，不要求视频模型生成可听人声：{sound['voiceover']}")
    if sound.get("dialogue"):
        parts.append(f"对白内容仅作为表演节奏参考，不要求视频模型生成清晰台词：{sound['dialogue']}")
    if sound.get("subtitle"):
        parts.append(f"字幕内容只进入后期剪辑 metadata，禁止生成画面字幕：{sound['subtitle']}")
    parts.append("只保留现场环境声和拟音：空间底噪、风声、雨声、脚步、衣料摩擦、呼吸、门响或道具轻响。")
    parts.append("禁止背景音乐、歌曲、音乐铺底、片头片尾声效和抢戏音效。")
    return "；".join(parts)


def _realism_anchors(characters: Dict, scene: Dict) -> str:
    char_text = _character_lock_text(characters)
    scene_text = _scene_lock_text(scene)
    return (
        f"{char_text}。{scene_text}。人物不要完美模板脸、网红脸、塑料皮肤或蜡像感；"
        "保留毛孔、眼下轻微阴影、鼻翼和面颊自然肤色变化、嘴唇干湿不均、碎发和衣料压痕。"
        "动作有轻微反应延迟，环境不要像干净棚拍。"
    )


def _execution_constraints(storyboard_card: Dict) -> str:
    multichar = len(storyboard_card.get("characters_present") or []) >= 2
    director_plan = storyboard_card.get("director_plan") or {}
    constraints = [
        "每镜只保留一个主动作和一个情绪落点",
        "必须执行 director_plan 中的节拍、动作链、景别理由、运镜理由和剪辑意图",
        "不要把世界观解释写成画面文字",
        "禁止画面字幕、伪文字、水印、片头片尾和标题卡",
        "禁止背景音乐和歌曲；视频模型只处理现场环境声与拟音",
        "不要新增不在连续性圣经里的角色、服装、道具和地标",
        "如果没有角色参考图，本镜只作为构图预览，不作为角色效果验收",
    ]
    if multichar:
        constraints.append("双人关系优先清楚，不用复杂运镜破坏轴线")
    for flag in director_plan.get("quality_flags") or []:
        constraints.append(f"director_plan quality flag: {flag}")
    return "；".join(constraints)

def _retry_advice(storyboard_card: Dict) -> List[str]:
    director_plan = storyboard_card.get("director_plan") or {}
    advice = [
        "如果动作太乱，缩短为一个主动作并改用稳定中景。",
        "如果表情过度，强调克制微表情和呼吸变化。",
        "如果画面太像棚拍，增加真实材质、污渍、反光不规则和环境底噪。",
    ]
    if "handheld" in storyboard_card.get("camera_motion", ""):
        advice.append("如果手持太晃，改成可控低幅跟拍，命中点或情绪点短暂停留。")
    if storyboard_card.get("action_scene_type") == "martial_arts":
        advice.append("如果武戏动作糊成一团，改成起势、一次攻防、收势三拍，并用中景稳定拍清距离。")
    for risk in director_plan.get("continuity_risks") or []:
        advice.append(f"如果出现 {risk}，按 director_plan 的景别、运镜理由和动作链重写本镜，不要临时添加新动作。")
    return advice

def _emotion_from_visual(visual: str) -> str:
    text = str(visual or "")
    if any(word in text for word in ["渡劫", "天雷", "雷劫", "飞升", "顿悟", "心魔", "剑意", "灵力暴涨"]):
        return "震撼、压抑、临界突破"
    if any(word in text for word in ["拔剑", "格挡", "反击", "压制", "逼退", "横刀", "出手", "攻防"]):
        return "高度警觉、克制杀意、动作专注"
    if any(word in text for word in ["追", "冲", "逃", "奔", "撞", "扑来"]):
        return "急迫、恐惧压迫、求生本能"
    if any(word in text for word in ["对视", "逼", "质问", "审视", "沉默", "低声", "抬眼"]):
        return "压迫、试探、克制对峙"
    if any(word in text for word in ["规则", "账本", "系统", "探测器", "异常", "发现", "原来"]):
        return "疑惑、判断、信息反转"
    if any(word in text for word in ["雨", "夜", "门", "暗", "黑", "雾", "黄泉", "地府", "诡异"]):
        return "悬疑、迟疑、克制不安"
    if any(word in text for word in ["笑", "缓", "放下", "走出", "松开", "重逢", "拥抱"]):
        return "释放、余震、轻微缓和"
    if any(word in text for word in ["落泪", "哽咽", "诀别", "牺牲", "回忆"]):
        return "隐忍、悲伤、情绪压低"
    return "专注、判断、情绪推进"


def _binding_text(reference_binding: Dict) -> str:
    return (
        f"锁脸={reference_binding.get('face_locks', {})}；"
        f"锁衣={reference_binding.get('costume_locks', {})}；"
        f"锁道具={reference_binding.get('prop_locks', {})}；"
        f"锁景={reference_binding.get('scene_lock', '')}；"
        f"锁风格={reference_binding.get('style_lock', '')}。"
    )


def _optional_line(label: str, value: str) -> str:
    return f"{label}：{value}" if value else ""


def _character_lock_text(characters: Dict) -> str:
    if not characters:
        return "保持同一主体身份、发型、服饰和体型气质"
    parts = []
    for char_id, lock in characters.items():
        parts.append(
            f"{lock.get('name', char_id)}：脸={lock.get('face_lock', '同一脸')}，"
            f"发型={lock.get('hair_lock', '同一发型')}，"
            f"服饰={lock.get('costume_lock', '同一服饰')}，"
            f"气质={lock.get('body_temperament_lock', '同一体型气质')}"
        )
    return "；".join(parts)


def _scene_lock_text(scene: Dict) -> str:
    if not scene:
        return "场景布局、光源方向和主要地标保持连续"
    return (
        f"场景={scene.get('name', '')}，布局={scene.get('layout_lock', '')}，"
        f"地标={scene.get('landmark_lock', [])}，光线={scene.get('lighting_lock', '')}"
    )
