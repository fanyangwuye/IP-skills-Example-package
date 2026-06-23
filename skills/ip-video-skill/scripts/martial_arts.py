from typing import Dict


MARTIAL_ARTS_KEYWORDS = [
    "刀光",
    "刀法",
    "拔刀",
    "横刀",
    "拔剑",
    "横剑",
    "剑光",
    "剑气",
    "剑芒",
    "剑诀",
    "飞剑",
    "枪法",
    "长枪",
    "棍法",
    "拳法",
    "掌法",
    "腿法",
    "飞踢",
    "劈砍",
    "突刺",
    "格挡",
    "闪避",
    "反击",
    "招式",
    "轻功",
    "对峙",
    "交手",
    "缠斗",
    "追击",
    "攻防",
    "收势",
    "起势",
]


def is_martial_arts_scene(text: str, explicit_type: str = "") -> bool:
    if explicit_type == "martial_arts":
        return True
    haystack = str(text or "")
    return any(keyword in haystack for keyword in MARTIAL_ARTS_KEYWORDS)


def build_martial_arts_layer(visual: str, storyboard_card: Dict, continuity_state: Dict) -> Dict:
    multichar = len(storyboard_card.get("characters_present") or []) >= 2
    return {
        "scene_type": "martial_arts",
        "beat_structure": "起势亮明距离 -> 一次清晰攻防 -> 反应停顿 -> 收势落点",
        "distance_rule": _distance_rule(multichar),
        "movement_rule": _movement_rule(visual),
        "weapon_rule": _weapon_rule(visual),
        "camera_rule": "先用中景或全景交代双方距离和动线，再用低幅跟拍贴近动作；命中点停留0.3秒，不用快速乱切掩盖动作。",
        "impact_rule": "打击反馈用衣摆、脚步、水花、尘土、兵器轻响、呼吸停顿和身体重心变化表现，不用血腥和伤口特写。",
        "continuity_rule": (
            f"武戏必须从「{continuity_state.get('current_start_state', '')}」开始，"
            f"结束在「{continuity_state.get('current_end_state', '')}」，中间动作不能瞬移或跳过重心转移。"
        ),
        "safety_rule": "风格化武侠动作，无血腥、无伤口特写、无肢体断裂、无写实伤害展示。",
        "ui_rule": "不要编号、箭头、动作轨迹线、招式文字、漫画速度线、UI标注、字幕、水印或标题卡进入视频画面。",
        "storyboard_rule": "故事板图按起势、交锋、收势三面板设计；每格只画一个动作关键点，动作方向和角色站位连续。",
    }


def martial_arts_text(layer: Dict) -> str:
    if not layer:
        return ""
    return (
        f"武戏调度：{layer.get('beat_structure')}。"
        f"距离与站位：{layer.get('distance_rule')}。"
        f"身法动线：{layer.get('movement_rule')}。"
        f"兵器/肢体路径：{layer.get('weapon_rule')}。"
        f"镜头：{layer.get('camera_rule')}。"
        f"打击反馈：{layer.get('impact_rule')}。"
        f"连续性：{layer.get('continuity_rule')}。"
        f"安全边界：{layer.get('safety_rule')}。"
        f"画面排除：{layer.get('ui_rule')}"
    )


def _distance_rule(multichar: bool) -> str:
    if multichar:
        return "双方距离、轴线、屏幕方向和眼线必须先交代清楚；攻防距离变化要在画面内完成。"
    return "主体与目标、门槛、桌椅、台阶等空间锚点的距离必须可追踪。"


def _movement_rule(visual: str) -> str:
    if any(word in visual for word in ["轻功", "飞身", "跃", "跳"]):
        return "轻功只表现一次明确起跳、空中方向和落点，衣摆与发丝跟随运动，不漂浮失重。"
    if any(word in visual for word in ["追", "冲", "跑"]):
        return "追击先有蓄力脚步，再沿同一动线加速，镜头跟随但主体保持清楚。"
    return "动作从脚步和重心启动，经腰胯带动上身，再到手部或兵器完成，不要只有手臂乱挥。"


def _weapon_rule(visual: str) -> str:
    if "剑" in visual:
        return "剑路保持细长清晰，一次主刺或横挡即可，剑尖方向、手腕角度和收剑落点要连续。"
    if "刀" in visual:
        return "刀路偏重劈、压、横挡，一次主动作即可，刀背和刀刃方向不能跳变。"
    if any(word in visual for word in ["拳", "掌", "腿", "踢"]):
        return "拳掌腿法要看清起手、发力、落点和收势，避免肢体模糊变形。"
    return "道具或肢体路径必须清楚，不要一段里塞入多个不可读招式。"
