import os
from typing import Dict, List, Optional

try:
    from .config import VideoProviderConfig
    from .poyo_video_client import PoYoVideoClient
except ImportError:
    from config import VideoProviderConfig
    from poyo_video_client import PoYoVideoClient


SUPPORTED_PROVIDERS = {"offline", "dry_run", "dreamina_cli", "jimeng_cli", "poyo_video"}


def prepare_video_generation_request(task: Dict, config: VideoProviderConfig) -> Dict:
    provider = task.get("provider") or config.provider
    if provider not in SUPPORTED_PROVIDERS:
        raise RuntimeError(f"Unsupported VIDEO_PROVIDER: {provider}")

    handoff = task.get("video_handoff") or task.get("handoff") or {}
    unit = task.get("clip") or task.get("shot") or _select_generation_unit(handoff, task)
    if not unit:
        raise ValueError("prepare_video_generation requires clip, shot, video_handoff.clip_plan, or video_handoff.shots")

    prompt_kind = task.get("prompt_kind", _default_prompt_kind(provider))
    request = _base_request(task, unit, provider, prompt_kind, config)
    if provider in {"dreamina_cli", "jimeng_cli"}:
        request["transport"] = _dreamina_cli_transport(task, request)
    elif provider == "poyo_video":
        request["transport"] = _poyo_video_transport(task, request, config)
    else:
        request["transport"] = {"type": "dry_run", "note": "No external API call will be made."}
    return request


def run_video_generation(task: Dict, config: VideoProviderConfig) -> Dict:
    request = prepare_video_generation_request(task, config)
    provider = request["provider"]
    if provider in {"offline", "dry_run"} or task.get("dry_run", True):
        return {
            "status": "success",
            "provider": provider,
            "mode": "run_video_generation",
            "dry_run": True,
            "request": request,
            "logs": ["prepared video provider request; no external API call executed"],
        }
    if provider == "poyo_video":
        client = PoYoVideoClient(config)
        output_dir = task.get("output_dir") or config.output_root
        result = client.run_seedance2(
            request,
            output_dir=output_dir,
            callback_url=task.get("callback_url"),
            download=bool(task.get("download", True)),
        )
        return {
            "status": "success",
            "provider": provider,
            "mode": "run_video_generation",
            "dry_run": False,
            "request": request,
            "result": result,
            "artifacts": [
                {"type": "video", "path": path, "meta": {"provider": "poyo_video", "task_id": result.get("task_id")}}
                for path in result.get("local_paths", [])
            ],
            "logs": [f"completed PoYo video task {result.get('task_id')}", f"downloaded {len(result.get('local_paths', []))} file(s)"],
        }
    raise RuntimeError(
        f"Live video generation for provider '{provider}' is not implemented yet. "
        "Use dry_run=true to inspect the provider request."
    )


def _base_request(task: Dict, unit: Dict, provider: str, prompt_kind: str, config: VideoProviderConfig) -> Dict:
    image_urls = _image_urls(task, unit)
    reference_image_urls = _reference_image_urls(task, unit, image_urls)
    mode = task.get("generation_mode") or _infer_generation_mode(task, unit, image_urls, reference_image_urls)
    timing = unit.get("timing") or {}
    unit_id = unit.get("clip_id") or unit.get("shot_id") or "video_unit"
    return {
        "provider": provider,
        "mode": mode,
        "unit_kind": "clip" if unit.get("clip_id") else "shot",
        "clip_id": unit.get("clip_id", ""),
        "shot_id": unit.get("shot_id", ""),
        "unit_id": unit_id,
        "model": task.get("model") or config.default_model or _default_model(provider),
        "prompt_kind": prompt_kind,
        "prompt": _prompt_for_kind(unit, prompt_kind),
        "negative_prompt": unit.get("negative_prompt", ""),
        "duration_sec": task.get("duration_sec") or timing.get("duration_sec"),
        "aspect_ratio": task.get("aspect_ratio") or config.default_aspect_ratio,
        "resolution": task.get("resolution") or config.default_resolution,
        "generate_audio": task.get("generate_audio"),
        "seed": task.get("seed"),
        "image_urls": image_urls,
        "reference_image_urls": reference_image_urls,
        "reference_video_urls": _normalize_reference_list(task.get("reference_video_urls") or []),
        "reference_audio_urls": _normalize_reference_list(task.get("reference_audio_urls") or []),
        "reference_images": _reference_images(task, unit),
        "video_reference_images": unit.get("video_reference_images", []),
        "space_anchor_refs": unit.get("space_anchor_refs", []),
        "previous_clip_end_frame": unit.get("previous_clip_end_frame"),
        "reference_binding": unit.get("reference_binding", {}),
        "continuity_state": unit.get("continuity_state", {}),
        "visual_lock": unit.get("visual_lock", {}),
        "axis": unit.get("axis", {}),
        "screen_direction": unit.get("screen_direction", {}),
        "eyeline": unit.get("eyeline", {}),
        "retry_advice": unit.get("retry_advice", []),
        "output_filename": task.get("output_filename") or f"{unit_id}.mp4",
    }


def _select_generation_unit(handoff: Dict, task: Dict) -> Optional[Dict]:
    wants_clip = bool(task.get("clip_id") or task.get("clip_index") or task.get("generation_unit") == "clip")
    wants_shot = bool(task.get("shot_id") or task.get("shot_index") or task.get("generation_unit") == "shot")
    if (wants_clip or not wants_shot) and handoff.get("clip_plan"):
        return _select_clip(handoff, task)
    return _select_shot(handoff, task)


def _select_clip(handoff: Dict, task: Dict) -> Optional[Dict]:
    clips = handoff.get("clip_plan") or handoff.get("clips") or []
    if not clips:
        return None
    clip_id = task.get("clip_id")
    if clip_id:
        for clip in clips:
            if clip.get("clip_id") == clip_id:
                return clip
        raise ValueError(f"clip_id not found in video_handoff: {clip_id}")
    index = int(task.get("clip_index", 1) or 1)
    if index < 1 or index > len(clips):
        raise ValueError(f"clip_index out of range: {index}")
    return clips[index - 1]


def _select_shot(handoff: Dict, task: Dict) -> Optional[Dict]:
    shots = handoff.get("shots") or []
    if not shots:
        return None
    shot_id = task.get("shot_id")
    if shot_id:
        for shot in shots:
            if shot.get("shot_id") == shot_id:
                return shot
        raise ValueError(f"shot_id not found in video_handoff: {shot_id}")
    index = int(task.get("shot_index", 1) or 1)
    if index < 1 or index > len(shots):
        raise ValueError(f"shot_index out of range: {index}")
    return shots[index - 1]


def _default_prompt_kind(provider: str) -> str:
    if provider in {"dreamina_cli", "jimeng_cli"}:
        return "seedance"
    if provider == "poyo_video":
        return "i2v"
    return "seedance"


def _default_model(provider: str) -> str:
    return {
        "jimeng_cli": "jimeng-video-default",
        "dreamina_cli": "dreamina-video-default",
        "poyo_video": "video-default",
        "offline": "offline-preview",
        "dry_run": "offline-preview",
    }.get(provider, "video-default")


def _infer_generation_mode(task: Dict, unit: Dict, image_urls: List, reference_image_urls: List) -> str:
    if image_urls:
        return "frames_to_video" if unit.get("clip_id") else "image_to_video"
    if reference_image_urls:
        return "multimodal_to_video"
    refs = _reference_images(task, unit)
    return "image_to_video" if refs else "text_to_video"


def _prompt_for_kind(shot: Dict, prompt_kind: str) -> str:
    if prompt_kind == "i2v":
        return shot.get("i2v_prompt") or shot.get("clip_prompt") or shot.get("seedance_prompt") or shot.get("t2v_prompt", "")
    if prompt_kind == "t2v":
        return shot.get("t2v_prompt") or shot.get("clip_prompt") or shot.get("seedance_prompt") or shot.get("i2v_prompt", "")
    if prompt_kind == "seedance":
        return shot.get("seedance_prompt") or shot.get("clip_prompt") or shot.get("i2v_prompt") or shot.get("t2v_prompt", "")
    raise ValueError("prompt_kind must be one of: seedance, i2v, t2v")


def _image_urls(task: Dict, unit: Dict) -> List:
    explicit = task.get("image_urls") or []
    if explicit:
        return _normalize_reference_list(explicit)
    previous = unit.get("previous_clip_end_frame")
    if previous:
        return [_normalize_reference(previous)]
    return []


def _reference_image_urls(task: Dict, unit: Dict, image_urls: List) -> List:
    explicit = task.get("reference_image_urls") or []
    if explicit:
        return _normalize_reference_list(explicit)
    if image_urls:
        return []
    refs = []
    for item in unit.get("video_reference_images") or []:
        ref = _normalize_reference(item)
        if ref.get("url") or ref.get("path"):
            refs.append(ref)
    return refs


def _reference_images(task: Dict, shot: Dict) -> List[Dict]:
    explicit = task.get("reference_images") or []
    if explicit:
        return [_normalize_reference(item) for item in explicit]

    refs = []
    for item in shot.get("video_reference_images") or []:
        refs.append(_normalize_reference(item))
    binding = shot.get("reference_binding") or {}
    for role, values in (binding.get("face_locks") or {}).items():
        refs.append({"role": "face", "lock": values, "character": role})
    for role, values in (binding.get("costume_locks") or {}).items():
        refs.append({"role": "costume", "lock": values, "character": role})
    if binding.get("scene_lock"):
        refs.append({"role": "scene", "lock": binding["scene_lock"]})
    return refs


def _normalize_reference(item) -> Dict:
    if isinstance(item, str):
        kind = "path" if os.path.exists(item) else "url"
        return {kind: item, "role": "general"}
    return dict(item)


def _normalize_reference_list(items: List) -> List:
    return [_normalize_reference(item) for item in items]


def _dreamina_cli_transport(task: Dict, request: Dict) -> Dict:
    executable = task.get("dreamina_cli_path") or task.get("jimeng_cli_path") or task.get("cli_path") or "dreamina"
    subcommand = task.get("dreamina_subcommand") or _dreamina_subcommand(request)
    return {
        "type": "cli",
        "executable": executable,
        "subcommand": subcommand,
        "help_command": [executable, subcommand, "-h"],
        "intended_parameters": {
            "prompt": request["prompt"],
            "negative_prompt": request["negative_prompt"],
            "duration_sec": request.get("duration_sec"),
            "aspect_ratio": request["aspect_ratio"],
            "resolution": request["resolution"],
            "model": request["model"],
            "reference_images": request["reference_images"],
            "output_filename": request["output_filename"],
        },
        "stdin_json": request,
        "note": (
            "Official entrypoint is dreamina. Run help_command first and map intended_parameters "
            "to the exact flags reported by `dreamina <subcommand> -h` before any paid generation."
        ),
    }


def _dreamina_subcommand(request: Dict) -> str:
    mode = request.get("mode")
    refs = request.get("reference_images") or []
    if mode == "text_to_video":
        return "text2video"
    if mode == "frames_to_video":
        return "frames2video"
    if mode == "multimodal_to_video":
        return "multimodal2video"
    if len(refs) > 1:
        return "multiframe2video"
    return "image2video"


def _poyo_video_transport(task: Dict, request: Dict, config: VideoProviderConfig) -> Dict:
    model = task.get("provider_model_name") or request.get("model") or "seedance-2"
    input_obj = {
        "prompt": request["prompt"],
        "resolution": request["resolution"],
        "duration": int(round(float(request.get("duration_sec") or 5))),
    }
    if request.get("aspect_ratio"):
        input_obj["aspect_ratio"] = request["aspect_ratio"]
    if request.get("generate_audio") is not None:
        input_obj["generate_audio"] = bool(request["generate_audio"])
    if request.get("seed") is not None:
        input_obj["seed"] = int(request["seed"])
    for key in ("image_urls", "reference_image_urls", "reference_video_urls", "reference_audio_urls"):
        if request.get(key):
            input_obj[key] = [item.get("url", item) if isinstance(item, dict) else item for item in request[key]]
    return {
        "type": "http",
        "method": "POST",
        "url": (task.get("api_base") or config.api_base or "https://api.poyo.ai") + "/api/generate/submit",
        "headers": {"Authorization": "Bearer ${VIDEO_API_KEY}"},
        "json": {"model": model, "input": input_obj},
        "status_url": (task.get("api_base") or config.api_base or "https://api.poyo.ai") + "/api/generate/status/{task_id}",
        "note": "PoYo Seedance 2 request. Live execution requires dry_run=false and VIDEO_API_KEY or POYO_API_KEY.",
    }
