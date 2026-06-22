from typing import Dict, List


def build_prompt_profile(index: int, visual: str, storyboard_card: Dict, continuity_state: Dict, visual_lock: Dict) -> Dict:
    duration = _duration_text(storyboard_card)
    emotion = _emotion_from_visual(visual)
    scene = visual_lock.get("scene") or {}
    style = visual_lock.get("style") or {}
    characters = visual_lock.get("characters") or {}
    return {
        "duration": duration,
        "narrative_intent": storyboard_card.get("story_function", "推进剧情"),
        "action_flow": _action_flow(visual, continuity_state),
        "performance_control": _performance_control(emotion, characters),
        "camera_control": _camera_control(storyboard_card, emotion),
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
            f"画面内容：{visual}",
            f"动作流程：{profile['action_flow']}",
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
            "文生视频。按连续性圣经生成同一角色和同一场景，不能把新镜头当作独立重启。",
            f"叙事目标：{profile['narrative_intent']}。",
            f"画面内容：{visual}",
            f"动作流程：{profile['action_flow']}",
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
            f"画面内容：{visual}",
            f"表演控制：{profile['performance_control']}",
            f"镜头控制：{profile['camera_control']}",
            f"空间连续性：{profile['spatial_continuity']}",
            f"光线与质感：{profile['lighting_texture']}",
            f"声音：{profile['sound_design']}",
            f"执行边界：{profile['execution_constraints']}",
            f"参考图绑定：{_binding_text(reference_binding)}",
        ]
    )


def build_negative_prompt(multichar: bool, action_scene: bool = False) -> str:
    items = [
        "不要换脸",
        "不要改变发型",
        "不要改变服装颜色和材质",
        "不要新增无关人物",
        "不要复制参考图中的无关背景或路人",
        "不要重置场景布局",
        "不要改变光源方向",
        "不要道具凭空出现或消失",
        "不要塑料皮肤",
        "不要过度磨皮",
        "不要夸张表情",
        "不要无意义镜头乱晃",
        "不要字幕乱码或伪文字",
        "不要画面字幕",
        "不要片头片尾文字",
        "不要背景音乐",
        "不要歌曲",
        "不要音乐铺底",
    ]
    if multichar:
        items.extend(["不要越轴", "不要屏幕方向翻转", "不要视线同向错位", "不要人物距离瞬移"])
    if action_scene:
        items.extend(["无血腥", "无伤口特写", "无暴力血浆", "动作风格化且非写实伤害展示"])
    return "；".join(items)


def build_retry_advice(profile: Dict, multichar: bool) -> List[str]:
    advice = list(profile.get("retry_advice") or [])
    advice.extend(
        [
            "如果脸漂移，缩短动作幅度并把角色参考设为锁脸优先。",
            "如果服装变色，降低场景色光污染，重申服饰款式、材质、颜色不变。",
            "如果场景重置，改用同一场景参考图并强调门、柜台、窗、道路等地标位置。",
        ]
    )
    if multichar:
        advice.extend(
            [
                "如果越轴，重申A屏幕左朝右、B屏幕右朝左，机位固定在轴线同一侧。",
                "如果视线错位，重申双方视线互补且高度匹配。",
            ]
        )
    return advice


def _duration_text(storyboard_card: Dict) -> str:
    timing = storyboard_card.get("timing") or {}
    duration = timing.get("duration_sec")
    if duration:
        return f"{duration:g}秒"
    return "按上游 timing 时长执行"


def _action_flow(visual: str, continuity_state: Dict) -> str:
    return (
        f"从「{continuity_state['current_start_state']}」开始；"
        f"中段只执行一个主动作「{continuity_state['main_action_transition'] or visual}」；"
        f"结束在「{continuity_state['current_end_state']}」。动作不要瞬间到位，保留半拍迟疑、呼吸和结果落点。"
    )


def _performance_control(emotion: str, characters: Dict) -> str:
    names = "、".join(lock.get("name", char_id) for char_id, lock in characters.items()) or "镜头主体"
    return (
        f"{names}保持克制真实表演，当前情绪为{emotion}。"
        "只安排1-2个微动作，例如视线短暂停住、眼睑收紧、手指微收、下颌轻压、呼吸变浅。"
        "情绪主要放在眼神、嘴角、呼吸和停顿里，不做夸张舞台化表情。"
    )


def _camera_control(storyboard_card: Dict, emotion: str) -> str:
    framing = storyboard_card.get("framing", "MS 主体清楚")
    motion = storyboard_card.get("camera_motion", "stable observation")
    return (
        f"{framing}；{motion}。镜头运动服务于{emotion}，不要装饰性乱动。"
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
    return (
        f"主光逻辑：{lighting}；色调：{palette}；环境：{atmosphere}。"
        "保留自然明暗层次，不要全脸打平。皮肤有毛孔、轻微眼周纹理和自然肤色变化；"
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
    return f"{char_text}。{scene_text}。人物不要完美模板脸，动作有轻微反应延迟，环境不要像干净棚拍。"


def _execution_constraints(storyboard_card: Dict) -> str:
    multichar = len(storyboard_card.get("characters_present") or []) >= 2
    constraints = [
        "每镜只保留一个主动作和一个情绪落点",
        "不要把世界观解释写成画面文字",
        "禁止画面字幕、伪文字、水印、片头片尾和标题卡",
        "禁止背景音乐和歌曲；视频模型只处理现场环境声与拟音",
        "不要新增不在连续性圣经里的角色、服装、道具和地标",
    ]
    if multichar:
        constraints.append("双人关系优先清楚，不用复杂运镜破坏轴线")
    return "；".join(constraints)


def _retry_advice(storyboard_card: Dict) -> List[str]:
    advice = [
        "如果动作太乱，缩短为一个主动作并改用稳定中景。",
        "如果表情过度，强调克制微表情和呼吸变化。",
        "如果画面太像棚拍，增加真实材质、污渍、反光不规则和环境底噪。",
    ]
    if "handheld" in storyboard_card.get("camera_motion", ""):
        advice.append("如果手持太晃，改成可控低幅跟拍，命中点或情绪点短暂停留。")
    return advice


def _emotion_from_visual(visual: str) -> str:
    if any(word in visual for word in ["对视", "挡", "逼", "刀", "追", "冲", "打"]):
        return "紧张、警觉、压迫"
    if any(word in visual for word in ["雨", "夜", "门", "暗", "黑"]):
        return "悬疑、迟疑、克制不安"
    if any(word in visual for word in ["笑", "缓", "放下", "走出"]):
        return "释放、余震、轻微缓和"
    return "专注、判断、情绪推进"


def _binding_text(reference_binding: Dict) -> str:
    return (
        f"锁脸={reference_binding.get('face_locks', {})}；"
        f"锁衣={reference_binding.get('costume_locks', {})}；"
        f"锁道具={reference_binding.get('prop_locks', {})}；"
        f"锁景={reference_binding.get('scene_lock', '')}；"
        f"锁风格={reference_binding.get('style_lock', '')}。"
    )


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
