"""视频风格预设：加载 + 按剧本内容识别（多选） + 冲突标注。

设计分工（与项目约定一致）：
- 本模块只做确定性的事：把命中的风格预设“找齐、读出、摆出来、标出冲突”。
- 不写死“哪个风格压哪个”的优先级；冲突如何调和交给上层 agent 看情况判断。

调用方式：
    presets = recognize_style_presets(source_text, creative_brief, explicit_ids)
    # presets 是已加载、已合并、并附带 conflicts 提示的结果，可注入 provider prompt。
"""

import json
import os
from typing import Any, Dict, List, Optional

_PRESET_DIRNAME = os.path.join("references", "video_style_presets")

# 风格识别信号表：style_id -> 关键词（中英文）。
# 维度互不互斥：一个剧本可同时命中 genre / technique / director-style 等多个。
# 这里只负责“命中识别”，不决定谁主谁次。
STYLE_SIGNALS = [
    ("ancient_sweet_short_drama", ["古风", "古装", "汉服", "宫", "王爷", "公子", "小姐", "甜宠", "言情", "ancient", "sweet"]),
    ("art_film_mood", ["文艺", "情绪", "氛围", "意境", "留白", "art film", "mood"]),
    ("dimension_breaking_interactive", ["破壁", "次元", "互动", "选择", "分支", "弹幕", "dimension", "interactive"]),
    ("drama_short_sound", ["剧情短片", "音色", "配音", "旁白", "drama short"]),
    ("first_person_pov", ["第一人称", "主视角", "POV", "pov", "fpv", "第一视角"]),
    ("food_documentary", ["美食", "舌尖", "食物", "烹饪", "纪录片", "food", "documentary"]),
    ("immersive_handheld_tracking", ["手持", "跟拍", "沉浸", "纪实", "handheld", "tracking"]),
    ("immersive_interactive_girlfriend", ["互动女友", "陪伴", "对视", "亲密", "girlfriend"]),
    ("industrial_product_commercial", ["工业", "产品", "机械", "宣传片", "industrial", "product"]),
    ("million_dollar_one_take", ["百万运镜", "炫技", "一镜到底", "long take", "one take"]),
    ("miniature_world", ["微缩", "迷你", "缩微", "miniature"]),
    ("miyazaki_animation", ["宫崎骏", "吉卜力", "童话", "miyazaki", "ghibli"]),
    ("new_product_tvc", ["新品", "TVC", "tvc", "广告", "上市", "种草"]),
    ("nolan_director_style", ["诺兰", "悬疑", "烧脑", "非线性", "nolan"]),
    ("one_take_ad", ["一镜到底", "广告", "one take ad"]),
    ("one_take_cinematic", ["一镜到底", "电影级", "长镜头", "one take", "cinematic"]),
    ("shinkai_style", ["新海诚", "唯美", "光影", "青春", "shinkai"]),
    ("story_driven_storyboard", ["故事板", "分镜", "叙事", "storyboard", "story driven"]),
    ("video_analysis_remaking", ["拉片", "复刻", "翻拍", "模仿", "remake", "analysis"]),
    ("wong_kar_wai", ["王家卫", "暧昧", "霓虹", "情绪流", "wong kar"]),
    ("world_cup_traversal", ["世界杯", "足球", "绿茵", "球场", "world cup", "soccer"]),
]


def _presets_dir(skill_root: Optional[str] = None) -> str:
    if skill_root:
        return os.path.join(skill_root, _PRESET_DIRNAME)
    # 默认相对本文件：scripts/ 的上一级是 skill 根
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), _PRESET_DIRNAME)


def load_style_preset(style_id: str, skill_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """读取单个风格预设文件；找不到或损坏返回 None（不抛错、不静默假装成功）。"""
    if not style_id:
        return None
    path = os.path.join(_presets_dir(skill_root), f"{style_id}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        data.setdefault("_meta", {})
        data["_meta"]["style_id"] = style_id
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _match_style_ids(source_text: str, creative_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    """按信号表统计每个风格的命中分；返回有命中的，按分数降序。不强行只选一个。"""
    combined = f"{source_text or ''} {json.dumps(creative_brief or {}, ensure_ascii=False)}"
    combined_lower = combined.lower()
    matched = []
    for style_id, terms in STYLE_SIGNALS:
        score = 0
        for term in terms:
            t = term.lower()
            if t in combined_lower:
                score += 1
        if score:
            matched.append({"style_id": style_id, "score": score})
    matched.sort(key=lambda item: (-item["score"], item["style_id"]))
    return matched


def _detect_conflicts(loaded: List[Dict[str, Any]]) -> List[str]:
    """标出多个预设之间的潜在冲突，交给 agent 看情况调和；本模块不替它拍板。"""
    conflicts = []
    if len(loaded) < 2:
        return conflicts
    # 景别分布冲突：多个预设各自规定了不同的 shot_type_distribution
    distros = []
    for p in loaded:
        dist = (p.get("camera_language") or {}).get("shot_type_distribution")
        if dist:
            distros.append((p["_meta"].get("display_name") or p["_meta"].get("style_id"), dist))
    if len(distros) >= 2:
        names = "、".join(n for n, _ in distros)
        conflicts.append(f"景别分布冲突：{names} 各自规定了不同的景别比例，需由 agent 按本段剧情决定以哪个为主或如何融合。")
    # 配色冲突
    palettes = [(p["_meta"].get("display_name") or p["_meta"].get("style_id"), p.get("primary_palette")) for p in loaded if p.get("primary_palette")]
    if len(palettes) >= 2:
        names = "、".join(n for n, _ in palettes)
        conflicts.append(f"配色冲突：{names} 各有主色调，需 agent 决定主色或如何过渡。")
    # 节奏冲突
    cuts = [(p["_meta"].get("display_name") or p["_meta"].get("style_id"), (p.get("rhythm") or {}).get("cuts_per_15s")) for p in loaded]
    cuts = [(n, c) for n, c in cuts if c]
    if len({c for _, c in cuts}) >= 2:
        detail = "、".join(f"{n}={c}刀/15s" for n, c in cuts)
        conflicts.append(f"节奏冲突：{detail}，需 agent 取舍切镜密度。")
    return conflicts


def recognize_style_presets(
    source_text: str = "",
    creative_brief: Optional[Dict[str, Any]] = None,
    explicit_ids: Optional[List[str]] = None,
    skill_root: Optional[str] = None,
    max_presets: int = 3,
) -> Dict[str, Any]:
    """主入口：识别（或接受显式指定）风格 -> 加载预设 -> 标注冲突。

    - explicit_ids 优先（agent/任务显式指定时）；否则按剧本内容自动识别。
    - 多选：可返回多个命中的预设（默认上限 3，避免噪声）。
    - 返回结构包含 loaded 预设、命中明细、冲突提示；不写死优先级。
    """
    creative_brief = creative_brief or {}
    if explicit_ids:
        chosen = [{"style_id": sid, "score": None, "source": "explicit"} for sid in explicit_ids]
    else:
        chosen = [{**m, "source": "auto"} for m in _match_style_ids(source_text, creative_brief)[:max_presets]]

    loaded = []
    missing = []
    for item in chosen:
        preset = load_style_preset(item["style_id"], skill_root)
        if preset is None:
            missing.append(item["style_id"])
            continue
        preset["_match"] = {"score": item.get("score"), "source": item.get("source")}
        loaded.append(preset)

    return {
        "style_presets_version": "video-style-presets-v1",
        "matched": chosen,
        "loaded": loaded,
        "missing": missing,
        "conflicts": _detect_conflicts(loaded),
        "decision_policy": "代码只负责找齐预设并标出冲突；以哪个风格为主、如何融合，由 agent 按本段剧情判断，不在此写死。",
    }


def style_presets_prompt_text(recognition: Dict[str, Any]) -> str:
    """把识别+加载结果压成一段可注入 provider prompt 的文本（含景别分布、运镜、正负向、节奏、冲突）。"""
    loaded = recognition.get("loaded") or []
    if not loaded:
        return ""
    blocks = []
    for p in loaded:
        meta = p.get("_meta", {})
        name = meta.get("display_name") or meta.get("style_id", "")
        cam = p.get("camera_language") or {}
        dist = cam.get("shot_type_distribution") or {}
        dist_text = "、".join(f"{k}={v}" for k, v in dist.items()) if dist else ""
        pos = "、".join((p.get("positive_prompt_fragments") or [])[:8])
        neg = "、".join((p.get("negative_prompt_fragments") or [])[:6])
        rhythm = p.get("rhythm") or {}
        parts = [f"【{name}】方向：{p.get('style_direction', '')}"]
        if p.get("primary_palette"):
            parts.append(f"配色：{p['primary_palette']}")
        if cam.get("movement_preference"):
            parts.append(f"运镜：{cam['movement_preference']}")
        if dist_text:
            parts.append(f"景别分布：{dist_text}")
        if rhythm.get("cuts_per_15s"):
            parts.append(f"节奏：每15秒约{rhythm['cuts_per_15s']}刀")
        if pos:
            parts.append(f"正向：{pos}")
        if neg:
            parts.append(f"负向：{neg}")
        blocks.append("；".join(parts))
    text = "Style Presets: " + " || ".join(blocks)
    conflicts = recognition.get("conflicts") or []
    if conflicts:
        text += " || 冲突待 agent 裁断：" + "；".join(conflicts)
    return text
