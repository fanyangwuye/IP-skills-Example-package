import os
from typing import Dict, List, Optional

try:
    from .config import VideoProviderConfig
except ImportError:
    from config import VideoProviderConfig


SUPPORTED_PROVIDERS = {"offline", "dry_run", "jimeng_cli", "poyo_video"}


def prepare_video_generation_request(task: Dict, config: VideoProviderConfig) -> Dict:
    provider = task.get("provider") or config.provider
    if provider not in SUPPORTED_PROVIDERS:
        raise RuntimeError(f"Unsupported VIDEO_PROVIDER: {provider}")

    handoff = task.get("video_handoff") or task.get("handoff") or {}
    shot = task.get("shot") or _select_shot(handoff, task)
    if not shot:
        raise ValueError("prepare_video_generation requires shot or video_handoff.shots")

    prompt_kind = task.get("prompt_kind", _default_prompt_kind(provider))
    request = _base_request(task, shot, provider, prompt_kind, config)
    if provider == "jimeng_cli":
        request["transport"] = _jimeng_cli_transport(task, request)
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
    raise RuntimeError(
        f"Live video generation for provider '{provider}' is not implemented yet. "
        "Use dry_run=true to inspect the provider request."
    )


def _base_request(task: Dict, shot: Dict, provider: str, prompt_kind: str, config: VideoProviderConfig) -> Dict:
    mode = task.get("generation_mode") or _infer_generation_mode(task, shot)
    timing = shot.get("timing") or {}
    return {
        "provider": provider,
        "mode": mode,
        "shot_id": shot.get("shot_id", ""),
        "model": task.get("model") or config.default_model or _default_model(provider),
        "prompt_kind": prompt_kind,
        "prompt": _prompt_for_kind(shot, prompt_kind),
        "negative_prompt": shot.get("negative_prompt", ""),
        "duration_sec": task.get("duration_sec") or timing.get("duration_sec"),
        "aspect_ratio": task.get("aspect_ratio") or config.default_aspect_ratio,
        "resolution": task.get("resolution") or config.default_resolution,
        "reference_images": _reference_images(task, shot),
        "reference_binding": shot.get("reference_binding", {}),
        "continuity_state": shot.get("continuity_state", {}),
        "visual_lock": shot.get("visual_lock", {}),
        "axis": shot.get("axis", {}),
        "screen_direction": shot.get("screen_direction", {}),
        "eyeline": shot.get("eyeline", {}),
        "retry_advice": shot.get("retry_advice", []),
        "output_filename": task.get("output_filename") or f"{shot.get('shot_id', 'shot')}.mp4",
    }


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
    if provider == "jimeng_cli":
        return "seedance"
    if provider == "poyo_video":
        return "i2v"
    return "seedance"


def _default_model(provider: str) -> str:
    return {
        "jimeng_cli": "jimeng-video-default",
        "poyo_video": "video-default",
        "offline": "offline-preview",
        "dry_run": "offline-preview",
    }.get(provider, "video-default")


def _infer_generation_mode(task: Dict, shot: Dict) -> str:
    refs = _reference_images(task, shot)
    return "image_to_video" if refs else "text_to_video"


def _prompt_for_kind(shot: Dict, prompt_kind: str) -> str:
    if prompt_kind == "i2v":
        return shot.get("i2v_prompt") or shot.get("seedance_prompt") or shot.get("t2v_prompt", "")
    if prompt_kind == "t2v":
        return shot.get("t2v_prompt") or shot.get("seedance_prompt") or shot.get("i2v_prompt", "")
    if prompt_kind == "seedance":
        return shot.get("seedance_prompt") or shot.get("i2v_prompt") or shot.get("t2v_prompt", "")
    raise ValueError("prompt_kind must be one of: seedance, i2v, t2v")


def _reference_images(task: Dict, shot: Dict) -> List[Dict]:
    explicit = task.get("reference_images") or []
    if explicit:
        return [_normalize_reference(item) for item in explicit]

    refs = []
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


def _jimeng_cli_transport(task: Dict, request: Dict) -> Dict:
    executable = task.get("jimeng_cli_path") or task.get("cli_path") or "jimeng"
    args = [
        "generate",
        "--mode",
        request["mode"],
        "--model",
        request["model"],
        "--aspect-ratio",
        request["aspect_ratio"],
        "--duration",
        str(request.get("duration_sec") or ""),
        "--output",
        request["output_filename"],
    ]
    return {
        "type": "cli",
        "executable": executable,
        "args": args,
        "stdin_json": request,
        "note": "CLI schema is a stable placeholder until the official Jimeng CLI command contract is confirmed.",
    }


def _poyo_video_transport(task: Dict, request: Dict, config: VideoProviderConfig) -> Dict:
    return {
        "type": "http",
        "method": "POST",
        "url": (task.get("api_base") or config.api_base or "https://api.poyo.ai") + "/api/generate/submit",
        "headers": {"Authorization": "Bearer ${VIDEO_API_KEY}"},
        "json": {
            "model": task.get("provider_model_name", "video-generation"),
            "input": request,
        },
        "note": "PoYo video endpoint schema is a placeholder until official video docs are confirmed.",
    }
