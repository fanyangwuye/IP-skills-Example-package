from typing import Dict, List


ACTION_WORDS = ["跑", "奔", "追", "冲", "逃", "闪避", "格挡", "反击", "打", "扔", "投", "关门", "推门", "进入"]
VAGUE_WORDS = ["连续动作", "推进剧情", "核心场景", "镜头", "画面", "走一下", "看一下"]
SPATIAL_RISK_WORDS = ["门", "窗", "走廊", "入口", "出口", "追", "逃", "扔", "投", "穿过", "进入", "关门"]
NARRATIVE_WORDS = ["发现", "决定", "阻止", "揭示", "反转", "对峙", "对视", "逼近", "停下", "交代", "进入", "出来", "完成", "站", "端着", "检查", "抬眼", "看向"]


def evaluate_storyboard_quality(shots: List[Dict], timing: Dict) -> Dict:
    duration = _positive_float((timing or {}).get("duration_sec"), sum(_shot_duration(shot) for shot in shots))
    shot_count = len(shots)
    shot_durations = [_shot_duration(shot) for shot in shots]
    avg_sec = round(duration / shot_count, 2) if shot_count else 0
    issues = []

    if shot_count == 0:
        issues.append(_issue("empty_storyboard", "error", "clip 没有可执行分镜。", [], "重新生成或补充分镜后再进入视频生成。"))

    if shot_count == 1 and duration >= 12:
        visual = _visual(shots[0]) if shots else ""
        code = "long_unbroken_motion" if _has_any(visual, ACTION_WORDS) else "long_single_shot"
        severity = "error" if code == "long_unbroken_motion" else "warning"
        issues.append(
            _issue(
                code,
                severity,
                "单个分镜承载接近 15 秒，容易变成无叙事长动作。",
                [_shot_id(shots[0])] if shots else [],
                "拆成起势、推进、反应、结果等 2-4 个分镜，或加入反打、特写、空镜/道具桥接。",
            )
        )

    if shot_count >= 6 and duration <= 15:
        severity = "error" if shot_count >= 8 or avg_sec < 1.5 else "warning"
        issues.append(
            _issue(
                "high_shot_density",
                severity,
                f"{duration:g} 秒内包含 {shot_count} 个分镜，平均每镜 {avg_sec:g} 秒，执行压力偏高。",
                [_shot_id(shot) for shot in shots],
                "人工确认是否拆成两个 clip，或把纯反应/插入镜合并为可执行的剪辑节拍。",
            )
        )

    short_ids = [_shot_id(shot) for shot in shots if _shot_duration(shot) < 1.5]
    if short_ids:
        issues.append(
            _issue(
                "too_short_shots",
                "warning",
                "存在低于 1.5 秒的分镜，视频模型可能来不及完成动作相位。",
                short_ids,
                "把极短镜头改成可见起始/动作/落点，或作为剪辑层而不是生成层处理。",
            )
        )

    vague_ids = [_shot_id(shot) for shot in shots if _is_vague_shot(shot)]
    if vague_ids:
        issues.append(
            _issue(
                "vague_storyboard_beats",
                "warning",
                "部分分镜缺少具体可见动作、对象或结果，容易生成空泛画面。",
                vague_ids,
                "补足主体、动作、道具/空间锚点和结束状态；提示词只强化这些已确认内容。",
            )
        )

    weak_ids = [_shot_id(shot) for shot in shots if _weak_narrative_function(shot)]
    if weak_ids:
        issues.append(
            _issue(
                "weak_narrative_function",
                "warning",
                "部分分镜的故事功能不够明确，可能出现为了做视频而做视频的问题。",
                weak_ids,
                "明确每镜承担 hook、交代、压迫、反应、转折、结果或悬念中的一个功能。",
            )
        )

    spatial_ids = [_shot_id(shot) for shot in shots if _needs_spatial_review(shot)]
    if spatial_ids:
        issues.append(
            _issue(
                "spatial_continuity_review",
                "warning",
                "存在门窗/追逃/投掷/进出等高风险空间动作，需要人工确认轴线、方向和边界两侧。",
                spatial_ids,
                "确认安全侧/危险侧、运动方向、角色先后顺序和威胁位置；必要时加入桥接镜头。",
            )
        )

    score = _score(issues)
    status = "fail" if any(item["severity"] == "error" for item in issues) else ("warn" if issues else "pass")
    return {
        "status": status,
        "score": score,
        "metrics": {
            "shot_count": shot_count,
            "duration_sec": duration,
            "avg_sec_per_shot": avg_sec,
            "min_shot_duration_sec": min(shot_durations) if shot_durations else 0,
            "max_shot_duration_sec": max(shot_durations) if shot_durations else 0,
            "action_shot_count": sum(1 for shot in shots if _has_any(_visual(shot), ACTION_WORDS)),
        },
        "issues": issues,
        "review_required": status != "pass",
        "summary": _summary(status, score, issues),
    }


def summarize_storyboard_quality(clips: List[Dict]) -> Dict:
    rows = []
    error_count = 0
    warning_count = 0
    for clip in clips or []:
        quality = clip.get("storyboard_quality") or {}
        issues = quality.get("issues") or []
        error_count += sum(1 for item in issues if item.get("severity") == "error")
        warning_count += sum(1 for item in issues if item.get("severity") == "warning")
        rows.append(
            {
                "clip_id": clip.get("clip_id"),
                "shot_ids": clip.get("shot_ids", []),
                "status": quality.get("status", "unknown"),
                "score": quality.get("score", 0),
                "issue_codes": [item.get("code") for item in issues],
            }
        )
    status = "fail" if error_count else ("warn" if warning_count else "pass")
    return {"status": status, "error_count": error_count, "warning_count": warning_count, "clips": rows}


def _score(issues: List[Dict]) -> int:
    score = 100
    for issue in issues:
        score -= 25 if issue.get("severity") == "error" else 8
    return max(score, 0)


def _summary(status: str, score: int, issues: List[Dict]) -> str:
    if status == "pass":
        return f"故事板生成质量通过，score={score}。"
    codes = "、".join(item.get("code", "") for item in issues)
    return f"故事板需要复核，status={status}，score={score}，issues={codes}。"


def _issue(code: str, severity: str, message: str, shot_ids: List[str], recommendation: str) -> Dict:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "shot_ids": [item for item in shot_ids if item],
        "recommendation": recommendation,
    }


def _is_vague_shot(shot: Dict) -> bool:
    visual = _visual(shot)
    if len(visual.strip()) < 8:
        return True
    return any(word in visual for word in VAGUE_WORDS) and not _has_any(visual, ACTION_WORDS + NARRATIVE_WORDS)


def _weak_narrative_function(shot: Dict) -> bool:
    card = shot.get("storyboard_card") or {}
    story_function = str(card.get("story_function") or "")
    visual = _visual(shot)
    if story_function and story_function != "推进剧情":
        return False
    return not _has_any(visual, NARRATIVE_WORDS + ACTION_WORDS)


def _needs_spatial_review(shot: Dict) -> bool:
    visual = _visual(shot)
    if not _has_any(visual, SPATIAL_RISK_WORDS):
        return False
    card = shot.get("storyboard_card") or {}
    axis = card.get("axis") or shot.get("axis") or {}
    screen = card.get("screen_direction") or shot.get("screen_direction") or {}
    eyeline = card.get("eyeline") or shot.get("eyeline") or {}
    return not axis or not screen or not eyeline


def _shot_duration(shot: Dict) -> float:
    timing = shot.get("timing") or {}
    if timing.get("duration_sec") is not None:
        return _positive_float(timing.get("duration_sec"), 1.0)
    return max(_positive_float(timing.get("end_sec"), 1.0) - _positive_float(timing.get("start_sec"), 0.0), 1.0)


def _positive_float(value, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed > 0 else default


def _visual(shot: Dict) -> str:
    return str(shot.get("visual") or "")


def _shot_id(shot: Dict) -> str:
    return str(shot.get("shot_id") or "")


def _has_any(text: str, words: List[str]) -> bool:
    return any(word in text for word in words)