from typing import Dict, List, Tuple

TOLERANCE_SEC = 0.5


def validate_blueprint(blueprint: Dict) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    for field in ("blueprint_id", "ip_id", "target", "total_duration_sec", "segments"):
        if field not in blueprint:
            errors.append(f"缺少顶层字段: {field}")
    if errors:
        return False, errors

    segments = blueprint["segments"]
    if not segments:
        return False, ["segments 为空"]

    ordered = sorted(segments, key=lambda item: item.get("index", 0))
    for index, segment in enumerate(ordered, start=1):
        if segment.get("index") != index:
            errors.append(f"第 {index} 段 index 应为 {index}，实际 {segment.get('index')}")
        if not segment.get("visual"):
            errors.append(f"第 {index} 段缺 visual（图片/视频 Skill 需要）")
        if not segment.get("voiceover"):
            errors.append(f"第 {index} 段缺 voiceover（配音需要）")
        start = segment.get("start_sec")
        end = segment.get("end_sec")
        if start is None or end is None:
            errors.append(f"第 {index} 段缺 start_sec/end_sec")
            continue
        if start >= end:
            errors.append(f"第 {index} 段 start_sec({start}) 应 < end_sec({end})")

    if all(seg.get("start_sec") is not None and seg.get("end_sec") is not None for seg in ordered):
        if abs(ordered[0]["start_sec"] - 0) > TOLERANCE_SEC:
            errors.append(f"首段应从 0 开始，实际 {ordered[0]['start_sec']}")
        for left, right in zip(ordered, ordered[1:]):
            if abs(left["end_sec"] - right["start_sec"]) > TOLERANCE_SEC:
                errors.append(
                    f"第 {left['index']} 段尾({left['end_sec']}) 与第 {right['index']} 段头({right['start_sec']}) 不相接"
                )
        last_end = ordered[-1]["end_sec"]
        if abs(last_end - blueprint["total_duration_sec"]) > TOLERANCE_SEC:
            errors.append(f"末段结束({last_end}) 与总时长({blueprint['total_duration_sec']}) 不符")

    return len(errors) == 0, errors

