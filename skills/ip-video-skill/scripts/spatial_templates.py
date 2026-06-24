from typing import Dict, List


CHASE_TERMS = ["追", "逃", "奔跑", "狂奔", "跑向", "追击", "追逐", "身后", "黑雾", "pursu", "chase", "run"]
THROW_BACK_TERMS = ["反手", "后抛", "抛", "扔", "爆裂", "炸", "射击", "回击", "throw", "mine", "backward", "firing"]
THRESHOLD_TERMS = ["门", "门槛", "入口", "进门", "冲门", "大厅", "door", "entrance", "threshold", "hall"]
WINDOW_TERMS = ["窗", "玻璃", "窗外", "窗内", "window", "glass"]


def high_risk_spatial_template_text(shots: List[Dict]) -> str:
    visual = " ".join(str(shot.get("visual", "")) for shot in shots)
    if not visual:
        return ""
    templates = []
    if _has_any(visual, CHASE_TERMS):
        templates.append(
            "追逐空间模板：先声明移动轴线和逃生目标，逃生目标始终在角色前方，追逐压力始终在角色身后；"
            "角色身体运动方向必须持续远离追逐方，不得主动冲向追逐方；"
            "如需回头、回击或看向身后，身体重心和脚步仍保持朝逃生目标移动。"
        )
    if _has_any(visual, THROW_BACK_TERMS):
        templates.append(
            "反手处理道具模板：身体前进方向和道具处理方向必须分开写清；"
            "人物继续朝逃生方向移动，手臂只向身后或侧后方短促处理道具；"
            "镜头优先侧面或侧后方，让人向前逃、道具向后飞同时可读，禁止写成主动迎战。"
        )
    if _has_any(visual, THRESHOLD_TERMS):
        templates.append(
            "门槛/入口边界模板：门框、入口或门槛是硬空间边界；"
            "必须标明外侧、内侧、角色跨越方向、边界关闭时机和追逐方停留位置；"
            "先显示角色完整越过边界，再显示关门或阻断；追逐方不得无解释跳到边界另一侧。"
        )
    if _has_any(visual, WINDOW_TERMS):
        templates.append(
            "窗框/玻璃边界模板：窗内和窗外是两层空间，窗框或玻璃必须保持同一边界方向；"
            "窗内角色、窗外压力、反光和视线方向不能互换；切反打前必须保留窗框或反光作为空间锚点。"
        )
    if not templates:
        return ""
    return " 高风险空间模板：" + " ".join(templates)


def _has_any(text: str, terms: List[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)
