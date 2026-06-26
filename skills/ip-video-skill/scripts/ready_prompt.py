"""成品提示词：剧本主导 → 风格库辅助补缺 → beat_type 工业级词兜底，无损翻译成可直接用的中文。

优先级（工业级设计）：
1. 剧本明确写的（基调/特效/运镜/光影/动作）→ 第一优先，原样用
2. 剧本没写的 → 风格库辅助补充
3. 都没有 → 按 beat_type 注入工业级通用词兜底
全程：服装一致性强约束 + 时间码分段 + 对白卡位 + 全中文过审。
"""

from typing import Any, Dict, List

_CHARS_PER_15S = 55

# beat_type → 工业级专业运镜/节奏词（剧本没写运镜时兜底）
_BEAT_PRO_CAMERA = {
    "establishing_hook": "电影级建立镜头，构图考究，缓入交代空间与氛围",
    "discovery": "专业级运镜，跟随视线推进，景深层次分明",
    "confrontation": "双人对峙机位，正反打清晰，轴线稳定",
    "action_pressure": "超高速战斗节奏，凌厉电影级动作运镜，快慢交替",
    "reversal": "希区柯克变焦（背景拉伸）制造眩晕，缓推定格揭示，强反差光影",
    "threshold_transition": "主观俯冲/过曝转场，画面拉伸，沉浸式越界感",
    "spectacle_threshold": "高端奇观运镜，摇臂俯冲或环绕，院线级视觉冲击",
    "insert_detail": "特写插入，浅景深突出关键道具，质感细腻",
}
# 通用工业级质感词（所有镜头叠加）
_PRO_TEXTURE = "电影质感，专业级分镜，院线级画面，光影叙事，高级感构图。"


def _shot_dialogue(shot: Dict) -> List[Dict]:
    sound = (shot.get("storyboard_card") or {}).get("sound_subtitle") or {}
    d = sound.get("dialogue") or shot.get("dialogue") or []
    if isinstance(d, str):
        d = [d]
    return d


def _shot_onscreen(shot: Dict) -> List[str]:
    sound = (shot.get("storyboard_card") or {}).get("sound_subtitle") or {}
    items = sound.get("screen_text") or shot.get("screen_text") or []
    if isinstance(items, str):
        items = [items]
    out = []
    for it in items:
        if isinstance(it, dict):
            content = str(it.get("content") or it.get("text") or "").strip()
            where = str(it.get("position") or it.get("位置") or "").strip()
            if content:
                out.append(f"「{content}」" + (f"（{where}）" if where else ""))
        elif str(it).strip():
            out.append(f"「{str(it).strip()}」")
    return out


def _pro(shot: Dict) -> Dict:
    return (shot.get("storyboard_card") or {}).get("pro_design") or {}


def _style_setting_line(clip: Dict, shots: List[Dict]) -> str:
    """整体设定：剧本基调优先，风格库辅助补缺。"""
    # 1. 剧本基调优先
    tone = ""
    for s in shots:
        t = _pro(s).get("style_tone")
        if t:
            tone = t
            break
    bits = []
    sp = clip.get("style_presets") or {}
    loaded = sp.get("loaded") or []
    conflicts = sp.get("conflicts") or []
    p = loaded[0] if loaded else {}
    zh = {"close_up": "特写", "medium": "中景", "wide": "全景", "extreme_close_up": "大特写"}
    # 多个命中的风格都列出来作辅助参考（多选叠加），主风格取第一个
    style_names = [x.get("display_name") for x in loaded if x.get("display_name")]
    if tone:
        bits.append(f"基调：{tone}")
        if len(style_names) >= 1:
            bits.append("风格库辅助参考：" + "、".join(style_names))
        cam = p.get("camera_language") or {}
        dist = cam.get("shot_type_distribution") or {}
        if dist:
            order = sorted(dist.items(), key=lambda kv: -kv[1])
            bits.append("景别参考：" + "、".join(f"{zh.get(k, k)}为主" if i == 0 else zh.get(k, k) for i, (k, _) in enumerate(order)))
    else:
        # 剧本没写基调 → 风格库辅助（多选）
        if p.get("primary_palette"):
            bits.append(f"配色（风格库辅助）：{p['primary_palette']}")
        if len(style_names) >= 2:
            bits.append("叠加风格参考：" + "、".join(style_names[1:]))
        cam = p.get("camera_language") or {}
        dist = cam.get("shot_type_distribution") or {}
        if dist:
            order = sorted(dist.items(), key=lambda kv: -kv[1])
            bits.append("景别：" + "、".join(f"{zh.get(k, k)}为主" if i == 0 else zh.get(k, k) for i, (k, _) in enumerate(order)))
    # 多风格冲突 → 交给 agent 判断，不写死
    if conflicts:
        bits.append("（多风格冲突，由agent按本段剧情取舍：" + "；".join(conflicts) + "）")
    return _PRO_TEXTURE + ("，".join(bits) + "。" if bits else "")


def _camera_line(shot: Dict) -> str:
    """运镜：剧本写的优先 → beat_type 工业词兜底。"""
    pro_cam = _pro(shot).get("camera")
    if pro_cam:
        return pro_cam  # 剧本明确写了运镜/分镜，原样用
    # 兜底：按 beat_type 注入工业级专业运镜
    bt = (shot.get("director_plan") or {}).get("beat_type", "")
    return _BEAT_PRO_CAMERA.get(bt, "电影级运镜，专业构图")


def _performance_hint(shot: Dict) -> str:
    """表演：剧本动作设计优先 → director_plan 兜底。"""
    pro_action = _pro(shot).get("action_design")
    dp = shot.get("director_plan") or {}
    et = dp.get("emotional_turn") or {}
    note = et.get("performance_note") or ""
    if pro_action:
        return pro_action + ("；" + note if note else "")
    framing = (dp.get("framing") or {}).get("value") or ""
    framing_zh = framing
    for en, zh in [("ECU", "大特写"), ("WS/中景", "全景到中景"), ("FS/MS", "全景到中景"),
                   ("WS", "全景"), ("FS", "全景"), ("MS", "中景"), ("MCU", "中近景"), ("CU", "特写")]:
        framing_zh = framing_zh.replace(en, zh)
    parts = [x for x in [framing_zh, note] if x]
    return "；".join(parts)


def build_ready_prompt(clip: Dict, shots: List[Dict]) -> Dict[str, Any]:
    timing = clip.get("timing") or {}
    dur = float(timing.get("duration_sec") or 15)
    lines = []
    warnings = []

    # 1) 整体设定（剧本基调主导 + 风格库辅助 + 工业质感）
    base_visual = "；".join(s.get("visual", "") for s in shots if s.get("visual"))
    lines.append(f"整体设定：{base_visual}。{_style_setting_line(clip, shots)}")

    # 服装一致性强约束（工业级要求）
    lines.append("一致性锁定：角色面容、发型、服装、配饰严格按参考图，跨镜头不漂移、不换装、不变形。")

    # 2) 时间码分段：画面 + 运镜(剧本/工业) + 特效(剧本) + 光影(剧本) + 表演 + 对白
    n = max(1, len(shots))
    seg = dur / n
    t = 0.0
    total_chars = 0
    for shot in shots:
        start, end = int(round(t)), int(round(min(dur, t + seg)))
        t += seg
        pro = _pro(shot)
        seg_text = f"[00:{start:02d}-00:{end:02d}] {shot.get('visual', '')}"
        cam = _camera_line(shot)
        if cam:
            seg_text += f"。运镜：{cam}"
        perf = _performance_hint(shot)
        if perf:
            seg_text += f"。表演：{perf}"
        if pro.get("vfx"):
            seg_text += f"。特效：{pro['vfx']}"
        if pro.get("lighting"):
            seg_text += f"。光影：{pro['lighting']}"
        if pro.get("sound_design"):
            seg_text += f"。音效：{pro['sound_design']}"
        lines.append(seg_text)
        for d in _shot_dialogue(shot):
            if isinstance(d, dict):
                spk = str(d.get("speaker") or "角色").strip()
                line = str(d.get("line") or d.get("text") or "").strip()
            else:
                spk, line = "角色", str(d or "").strip()
            if line:
                lines.append(f"　{spk}：「{line}」")
                total_chars += len(line)

    if total_chars > _CHARS_PER_15S * (dur / 15):
        warnings.append(f"本段对白约{total_chars}字，可能超出{int(dur)}秒语速容量（建议每15秒≤{_CHARS_PER_15S}字），考虑拆段。")

    # 3) 画面文字
    texts = []
    for shot in shots:
        texts.extend(_shot_onscreen(shot))
    if texts:
        lines.append("画面文字（精准渲染、常见字）：" + "；".join(texts) + "。")

    # 4) 打斗层
    mal = clip.get("martial_arts_layer") or {}
    if mal:
        combat_bits = []
        bs = mal.get("beat_structure")
        if bs:
            combat_bits.append("动作节拍：" + (bs if isinstance(bs, str) else "、".join(str(x) for x in bs)))
        for key, label in [("distance_rule", "距离"), ("movement_rule", "动作"), ("weapon_rule", "兵器"), ("impact_rule", "打击反馈"), ("camera_rule", "运镜")]:
            v = mal.get(key)
            if v:
                combat_bits.append(f"{label}：{v}")
        if combat_bits:
            lines.append("武打设计（超高速战斗、凌厉电影级动作）：" + "；".join(combat_bits) + "。风格化武侠不血腥；不要招式编号、箭头、速度线、字幕。")

    # 5) 爆点/钩子（剧本写的）
    hooks = [_pro(s).get("hook") for s in shots if _pro(s).get("hook")]
    if hooks:
        lines.append("情绪爆点：" + "；".join(hooks) + "。")

    # 6) 音频 + 禁止
    lines.append("音频：保留台词对白与环境/互动音效，台词与口型同步。不要画面字幕、片头片尾、水印、背景音乐。")

    # 7) 参考
    lines.append("参考（全能参考图，非首尾帧）：第一张锁角色身份与服装，第二张锁场景布局与光线，第三张锁构图与走位。")

    return {"prompt": "\n".join(lines), "warnings": warnings}
