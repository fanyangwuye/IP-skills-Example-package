import os
import shutil
import subprocess
from typing import Dict, List

try:
    from .bridge_clips import interleave_clips_with_bridges
    from .config import VideoProviderConfig
    from .video_provider import run_video_generation
except ImportError:
    from bridge_clips import interleave_clips_with_bridges
    from config import VideoProviderConfig
    from video_provider import run_video_generation


def run_video_sequence(task: Dict, config: VideoProviderConfig) -> Dict:
    handoff = task.get("video_handoff") or task.get("handoff") or {}
    clips = _sequence_units(handoff, task)
    if not clips:
        raise ValueError("run_video_sequence requires video_handoff.clip_plan")

    output_dir = task.get("output_dir") or config.output_root or os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    max_clips = int(task.get("max_clips") or len(clips))
    start_index = int(task.get("start_clip_index") or 1)
    clip_indexes = list(range(start_index, min(len(clips), start_index + max_clips - 1) + 1))
    previous_end_frame = task.get("initial_previous_clip_end_frame")
    provided_video_paths = _provided_video_paths(task)

    clip_results = []
    generated_paths = []
    for clip_index in clip_indexes:
        clip = dict(clips[clip_index - 1])
        if previous_end_frame and not clip.get("bridge_clip"):
            if _continuation_mode(task, clip) == "hard_first_frame":
                clip["previous_clip_end_frame"] = previous_end_frame
            else:
                clip["previous_clip_reference_frame"] = {
                    **previous_end_frame,
                    "role": "previous_clip_reference_frame",
                    "use": (
                        "continuity reference for character state, costume, scene, lighting, exposure, white balance, color grade, "
                        "and action momentum; do not copy this frame as the next clip first-frame composition"
                    ),
                }

        clip_task = _clip_task(task, handoff, clip, clip_index, output_dir)
        result = run_video_generation(clip_task, config)
        local_paths = _local_video_paths(result)
        if clip_index in provided_video_paths:
            local_paths = [provided_video_paths[clip_index]]
        generated_paths.extend(local_paths)

        first_frame = _extract_frame(local_paths[0], output_dir, clip.get("clip_id", f"clip_{clip_index:03d}"), "first", "0") if local_paths else None
        last_frame = _extract_frame(local_paths[0], output_dir, clip.get("clip_id", f"clip_{clip_index:03d}"), "last", task.get("last_frame_seek", "-0.08")) if local_paths else None
        if last_frame and not clip.get("bridge_clip"):
            previous_end_frame = {"path": last_frame, "role": "previous_clip_end_frame", "source_clip_id": clip.get("clip_id", "")}

        clip_results.append(
            {
                "clip_index": clip_index,
                "clip_id": clip.get("clip_id", ""),
                "bridge_clip": bool(clip.get("bridge_clip")),
                "bridge_type": clip.get("bridge_type", ""),
                "status": result.get("status"),
                "dry_run": result.get("dry_run"),
                "task_id": (result.get("result") or {}).get("task_id"),
                "credits_amount": (result.get("result") or {}).get("credits_amount"),
                "local_paths": local_paths,
                "first_frame": first_frame,
                "last_frame": last_frame,
                "next_previous_clip_end_frame": previous_end_frame,
                "request": result.get("request", {}),
            }
        )

    return {
        "status": "success",
        "provider": config.provider,
        "mode": "run_video_sequence",
        "clip_results": clip_results,
        "generated_paths": generated_paths,
        "final_previous_clip_end_frame": previous_end_frame,
        "quality_checks": _sequence_quality_checks(),
    }


def _clip_task(task: Dict, handoff: Dict, clip: Dict, clip_index: int, output_dir: str) -> Dict:
    output_stem = task.get("output_stem") or "sequence"
    clip_id = clip.get("clip_id", f"clip_{clip_index:03d}")
    inherited = {
        key: task[key]
        for key in (
            "provider",
            "dry_run",
            "download",
            "prompt_kind",
            "generation_mode",
            "model",
            "provider_model_name",
            "duration_sec",
            "aspect_ratio",
            "resolution",
            "generate_audio",
            "seed",
            "reference_image_urls",
            "reference_video_urls",
            "reference_audio_urls",
            "continuation_mode",
            "include_bridge_clips",
            "storyboard_panel_refs",
            "storyboard_image_path",
            "storyboard_image_paths",
            "storyboard_panel_count",
            "storyboard_panel_top_ratio",
            "storyboard_panel_bottom_ratio",
            "storyboard_panel_left_ratio",
            "storyboard_panel_right_ratio",
            "storyboard_panel_boxes",
            "callback_url",
        )
        if key in task
    }
    inherited.update(
        {
            "mode": "run_video_generation",
            "video_handoff": handoff,
            "clip": clip,
            "generation_unit": "clip",
            "clip_index": clip_index,
            "output_dir": output_dir,
            "output_filename": task.get("output_filename_template", f"{clip_id}_{output_stem}.mp4").format(
                clip_id=clip_id,
                clip_index=clip_index,
                output_stem=output_stem,
            ),
        }
    )
    if clip.get("bridge_clip"):
        inherited["duration_sec"] = (clip.get("timing") or {}).get("duration_sec") or task.get("bridge_clip_duration_sec") or 2
        inherited["generation_mode"] = task.get("bridge_generation_mode") or "multimodal_to_video"
    if "dry_run" not in inherited:
        inherited["dry_run"] = True
    if "download" not in inherited:
        inherited["download"] = True
    if "generate_audio" not in inherited:
        inherited["generate_audio"] = True
    return inherited


def _sequence_units(handoff: Dict, task: Dict) -> List[Dict]:
    clips = list(handoff.get("clip_plan") or [])
    bridges = list(handoff.get("bridge_clips") or [])
    include = bool(task.get("include_bridge_clips")) or task.get("bridge_clip_policy") in {"auto", "always"}
    if include and bridges:
        return interleave_clips_with_bridges(clips, bridges)
    return clips


def _local_video_paths(result: Dict) -> List[str]:
    paths = []
    for artifact in result.get("artifacts") or []:
        if artifact.get("type") == "video" and artifact.get("path"):
            paths.append(artifact["path"])
    if not paths:
        paths.extend((result.get("result") or {}).get("local_paths") or [])
    return paths


def _provided_video_paths(task: Dict) -> Dict[int, str]:
    values = task.get("provided_clip_video_paths") or {}
    if isinstance(values, list):
        return {index + 1: path for index, path in enumerate(values) if path}
    if isinstance(values, dict):
        result = {}
        for key, path in values.items():
            try:
                index = int(str(key).replace("clip_", ""))
            except ValueError:
                continue
            if path:
                result[index] = path
        return result
    return {}


def _continuation_mode(task: Dict, clip: Dict) -> str:
    mode = task.get("continuation_mode") or clip.get("continuation_mode") or "reference_reframe"
    if mode not in {"reference_reframe", "hard_first_frame"}:
        return "reference_reframe"
    return mode


def _extract_frame(video_path: str, output_dir: str, clip_id: str, label: str, seek: str) -> str:
    if not video_path or not os.path.exists(video_path):
        return ""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return ""
    out_path = os.path.join(output_dir, f"{clip_id}_{label}_frame.jpg")
    seek_values = [str(seek)]
    if str(seek).startswith("-"):
        seek_values.extend(["-0.35", "-0.75"])
    for seek_value in seek_values:
        command = [ffmpeg, "-y"]
        if seek_value.startswith("-"):
            command.extend(["-sseof", seek_value])
        else:
            command.extend(["-ss", seek_value])
        command.extend(["-i", video_path, "-frames:v", "1", out_path])
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
    return ""


def _sequence_quality_checks() -> List[str]:
    return [
        "每段生成后是否成功抽取 first_frame 和 last_frame",
        "clip N 的 last_frame 是否按 continuation_mode 作为 clip N+1 的首帧或连续性参考帧",
        "如果 provider 不允许 previous frame 与 reference images 混传，是否优先使用 previous frame 保障续接",
        "reference_reframe 模式下是否允许新机位/新景别，同时继承上一段角色状态、光影和色彩",
        "下一段首帧是否继承上一段尾帧的人物姿态、屏幕方向、光源和空间锚点",
        "下一段首帧是否继承上一段尾帧的色彩、曝光、白平衡、对比度和雨夜冷暖关系",
        "生成视频是否保留环境声和拟音，且没有背景音乐、歌曲或自动台词",
        "角色脸、服饰、道具和场景布局是否跨 clip 一致",
    ]
