import os
from typing import Dict, List, Optional

try:
    from .config import VideoProviderConfig
    from .poyo_video_client import PoYoVideoClient
    from .storyboard_panel_refs import PANEL_REF_ROLES, build_storyboard_panel_refs
except ImportError:
    from config import VideoProviderConfig
    from poyo_video_client import PoYoVideoClient
    from storyboard_panel_refs import PANEL_REF_ROLES, build_storyboard_panel_refs


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
    _guard_storyboard_execution_map(task, request)
    _guard_live_reference_strength(task, request)
    _guard_characterless_first_frame(task, request)
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


def _guard_storyboard_execution_map(task: Dict, request: Dict) -> None:
    if task.get("allow_missing_storyboard_execution_map"):
        return
    if request.get("provider") != "poyo_video":
        return
    if request.get("unit_kind") != "clip":
        return
    shot_ids = [item for item in request.get("shot_ids") or [] if item]
    execution_map = request.get("storyboard_execution_map") or []
    mapped_ids = [item.get("storyboard_shot_id") for item in execution_map if item.get("storyboard_shot_id")]
    if not execution_map:
        raise RuntimeError(
            "Live clip video generation is blocked because storyboard_execution_map is missing. "
            "Storyboard is the execution blueprint; every paid clip must map video shot order to storyboard shot IDs."
        )
    if shot_ids and mapped_ids != shot_ids:
        raise RuntimeError(
            "Live clip video generation is blocked because storyboard_execution_map does not exactly match shot_ids. "
            "Do not delete, merge away, reorder, or alter storyboard shots without an approved storyboard revision."
        )


def _guard_live_reference_strength(task: Dict, request: Dict) -> None:
    if _uses_all_purpose_reference(task, request):
        if request.get("image_urls"):
            raise RuntimeError(
                "All-purpose reference mode is fixed for this task, but image_urls were present. "
                "Do not replace all-purpose reference with first/last-frame or previous-tail-frame inputs."
            )
        if not request.get("reference_image_urls"):
            raise RuntimeError("All-purpose reference mode requires non-empty reference_image_urls.")
        return
    if task.get("allow_reference_only_live_video"):
        return
    if request.get("provider") != "poyo_video":
        return
    characters = ((request.get("visual_lock") or {}).get("characters") or {})
    if request.get("image_urls"):
        return
    if request.get("reference_image_urls"):
        raise RuntimeError(
            "Live video generation is blocked because this request only has reference_image_urls and no image_urls first-frame input. "
            "For IP continuity, generate or provide a real video first-frame/keyframe image and pass it as image_urls. "
            "Character-bearing clips must not use weak reference-only video generation for identity validation. "
            "Set allow_reference_only_live_video=true only for deliberate non-character cutaways or provider experiments."
        )
    if characters:
        raise RuntimeError(
            "Live character video generation is blocked because the request has locked characters but no image_urls first-frame/keyframe input. "
            "Generate a real character keyframe from the character design sheet plus scene reference, review it, then pass it as image_urls[0]. "
            "Text-to-video or empty-reference live runs cannot prove IP character consistency."
        )


def _guard_characterless_first_frame(task: Dict, request: Dict) -> None:
    if task.get("allow_character_after_cutaway_live_video"):
        return
    if not request.get("image_urls"):
        return
    characters = ((request.get("visual_lock") or {}).get("characters") or {})
    if not characters:
        return
    first_spec = request.get("first_frame_spec") or {}
    composition = str(first_spec.get("composition") or "")
    screen_direction = first_spec.get("screen_direction_lock") or {}
    characterless = "空镜" in composition or "道具插入" in composition or set(screen_direction.keys()) == {"environment"}
    if not characterless:
        return
    raise RuntimeError(
        "Live video generation is blocked because this clip contains locked characters but its first_frame_spec is a characterless cutaway. "
        "Split the cutaway into a separate bridge clip, then start the character clip from a real character keyframe image_urls[0]. "
        "Set allow_character_after_cutaway_live_video=true only for deliberate experiments."
    )


def _base_request(task: Dict, unit: Dict, provider: str, prompt_kind: str, config: VideoProviderConfig) -> Dict:
    unit = _unit_with_storyboard_panel_refs(task, unit)
    all_purpose_reference = _uses_all_purpose_reference(task, unit)
    image_urls = [] if all_purpose_reference else _image_urls(task, unit)
    reference_image_urls = _reference_image_urls(task, unit, image_urls)
    if all_purpose_reference and not reference_image_urls:
        raise ValueError("all_purpose_reference mode requires reference_image_urls")
    if provider == "poyo_video" and image_urls:
        reference_image_urls = []
    mode = task.get("generation_mode") or _infer_generation_mode(task, unit, image_urls, reference_image_urls)
    timing = unit.get("timing") or {}
    unit_id = unit.get("clip_id") or unit.get("shot_id") or "video_unit"
    frame_specs = _unit_frame_specs(unit)
    prompt = _with_reference_image_bindings(
        _with_storyboard_execution_map(_with_frame_specs(_prompt_for_kind(unit, prompt_kind), frame_specs), unit.get("storyboard_execution_map", [])),
        image_urls=image_urls,
        reference_image_urls=reference_image_urls,
        all_purpose_reference=all_purpose_reference,
    )
    return {
        "provider": provider,
        "mode": mode,
        "unit_kind": "clip" if unit.get("clip_id") else "shot",
        "clip_id": unit.get("clip_id", ""),
        "shot_id": unit.get("shot_id", ""),
        "shot_ids": unit.get("shot_ids", []),
        "unit_id": unit_id,
        "model": task.get("model") or config.default_model or _default_model(provider),
        "prompt_kind": prompt_kind,
        "prompt": prompt,
        "negative_prompt": _negative_prompt(unit, image_urls),
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
        "storyboard_panel_refs": unit.get("storyboard_panel_refs", []),
        "storyboard_execution_map": unit.get("storyboard_execution_map", []),
        "previous_clip_end_frame": unit.get("previous_clip_end_frame"),
        "previous_clip_reference_frame": unit.get("previous_clip_reference_frame"),
        "first_frame_spec": frame_specs.get("first_frame_spec", {}),
        "mid_frame_spec": frame_specs.get("mid_frame_spec", {}),
        "last_frame_spec": frame_specs.get("last_frame_spec", {}),
        "reference_binding": unit.get("reference_binding", {}),
        "continuity_state": unit.get("continuity_state", {}),
        "visual_lock": unit.get("visual_lock", {}),
        "axis": unit.get("axis", {}),
        "screen_direction": unit.get("screen_direction", {}),
        "eyeline": unit.get("eyeline", {}),
        "retry_advice": unit.get("retry_advice", []),
        "output_filename": task.get("output_filename") or f"{unit_id}.mp4",
    }


def _with_storyboard_execution_map(prompt: str, storyboard_execution_map: List[Dict]) -> str:
    if not storyboard_execution_map or "故事板执行映射" in prompt:
        return prompt
    rows = []
    for item in storyboard_execution_map:
        rows.append(
            f"视频镜头{item.get('video_shot_order')} = 故事板分镜 {item.get('storyboard_shot_id')}，"
            f"时间 {item.get('start_sec')}-{item.get('end_sec')} 秒，"
            f"景别={item.get('framing')}，运镜={item.get('camera_motion')}，画面={item.get('visual')}"
        )
    text = (
        "故事板执行映射（强制）："
        + "；".join(rows)
        + "。必须按故事板顺序执行每个分镜；不得删除、合并掉、改顺序或改动作。"
        "如果一个 15 秒 clip 无法准确执行全部分镜，必须拆成更短生成单元。"
        "提示词只能强化参考图和故事板已有内容细节，不能新增、修改或减少画面内容。"
    )
    return "\n\n".join([prompt, text])


def _uses_all_purpose_reference(task: Dict, unit_or_request: Optional[Dict] = None) -> bool:
    policy = str(task.get("reference_policy") or task.get("reference_mode") or "").strip()
    if policy == "all_purpose_reference" or task.get("all_purpose_reference") is True:
        return True
    binding = ((unit_or_request or {}).get("reference_binding") or {})
    binding_policy = str(binding.get("reference_mode") or binding.get("reference_policy") or "").strip()
    return binding_policy in {"all_purpose_reference", "all_purpose_reference_only"}


def _with_reference_image_bindings(prompt: str, image_urls: List, reference_image_urls: List, all_purpose_reference: bool = False) -> str:
    refs = image_urls or reference_image_urls
    if not refs:
        return prompt

    lines = ["参考图绑定（必须严格遵守，不要只当风格参考）："]
    if all_purpose_reference:
        lines.extend(
            [
                "全能参考模式已锁定：本次视频只能使用 reference_image_urls 作为全能参考，不得自动替换、降级或改写为 image_urls、首帧、尾帧、上一段尾帧或关键帧 I2V。",
                "所有 @Image 编号按 provider 输入顺序绑定；角色图锁身份，场景图锁空间，故事板图只锁分镜构图、景别、动作相位和剪辑顺序。",
            ]
        )
    else:
        lines.extend(
            [
                "所有 @Image 编号按 provider 输入顺序绑定；image_urls 优先级高于 reference_image_urls，image_urls[0] 是视频首帧/关键帧时必须作为开头画面继承。",
                "角色形象统一高于镜头自由发挥；有人物的付费视频必须先用角色设定图和场景图生成可审核真人物首帧/关键帧，再把该关键帧作为 image_urls[0]。",
            ]
        )
    for index, ref in enumerate(refs, start=1):
        role = _reference_role(ref)
        label = _reference_label(ref)
        marker = f"@Image{index}"
        if role in {"character_design_sheet", "character_reference", "face", "identity", "costume"}:
            lines.append(
                f"{marker} 是角色身份参考图{label}：画面中的对应角色必须使用这张图的同一脸型、眼型、鼻型、唇形、发型系统、年龄感、体型气质和服装轮廓；"
                "只提取角色身份和服饰，不复制设定板排版、文字、道具标签或白底背景。"
            )
        elif role in {"video_scene_reference", "scene", "environment", "space"}:
            lines.append(
                f"{marker} 是场景空间参考图{label}：必须锁定空间布局、可见地标、材质状态、光源方向和整体色调；"
                "不要复制无关文字标识，不要改变场景方向。"
            )
        elif role in {"previous_clip_end_frame", "first_frame", "last_frame"}:
            lines.append(
                f"{marker} 是视频连续性帧{label}：当前视频必须从该画面的角色状态、空间方向、光线、色彩、曝光、白平衡、对比度和动作余势自然延续；"
                "开头至少半秒保持同一色调和照明逻辑，不要突然提亮、变暗、换滤镜、换冷暖或重置调色。"
            )
        elif role == "previous_clip_reference_frame":
            lines.append(
                f"{marker} 是上一镜连续性参考帧{label}：只参考角色状态、服装、场景、光源、色彩、曝光、白平衡、对比度和动作余势；"
                "允许切换到当前镜头设计的机位、景别和构图，可以用近景、特写、全景、远景、背影、反打、空镜、道具插入或手部局部承接；"
                "不要把上一帧当作当前首帧，不要逐像素复制上一帧构图。换景别时仍必须继承同一角色、同一服装、同一场景方向和同一光色。"
            )
        elif role in PANEL_REF_ROLES:
            lines.append(
                f"{marker} 是故事板裁图构图参考{label}：只锁定构图、机位角度、人物站位、主体大小、动作相位、视线和空间锚点；"
                "禁止复制线稿风格、灰度草图质感、表格边框、面板编号、文字标签、箭头、注释或任何分镜板排版。"
            )
        else:
            lines.append(f"{marker} 是生成参考图{label}：必须按其指定角色/场景用途使用，不要忽略。")

    lines.extend(
        [
            "角色一致性优先级高于镜头自由发挥；如果参考图与文字描述冲突，脸、发型、服装和场景布局以参考图为准。",
            "禁止把参考图角色替换成明星脸、网红脸、芭比娃娃脸、AI默认脸或更好看的陌生演员脸。",
            "保留真实皮肤纹理、毛孔、细小瑕疵、自然法令纹、眼下轻微阴影和轻微面部不对称；不要塑料磨皮、玻璃珠眼睛、假睫毛过重、过度锐化、影楼写真感。",
        ]
    )
    return "\n\n".join(part for part in [prompt, "\n".join(lines)] if part)


def _unit_with_storyboard_panel_refs(task: Dict, unit: Dict) -> Dict:
    refs = []
    if task.get("storyboard_panel_refs"):
        refs.extend(_normalize_reference_list(task.get("storyboard_panel_refs") or []))
    if unit.get("storyboard_panel_refs"):
        refs.extend(_normalize_reference_list(unit.get("storyboard_panel_refs") or []))
    if task.get("storyboard_image_path") or task.get("storyboard_panel_source_path") or task.get("storyboard_image_paths"):
        refs.extend(build_storyboard_panel_refs(task, unit))
    if not refs:
        return unit
    updated = dict(unit)
    updated["storyboard_panel_refs"] = refs
    return updated


def _unit_frame_specs(unit: Dict) -> Dict:
    return {
        "first_frame_spec": unit.get("first_frame_spec", {}),
        "mid_frame_spec": unit.get("mid_frame_spec", {}),
        "last_frame_spec": unit.get("last_frame_spec", {}),
    }


def _negative_prompt(unit: Dict, image_urls: List) -> str:
    parts = [unit.get("negative_prompt", "")]
    if image_urls:
        parts.append("不要色彩跳变；不要曝光跳变；不要白平衡漂移；不要对比度突然变化；不要光源冷暖突然切换；不要滤镜感突变")
    return "；".join(part for part in parts if part)


def _with_frame_specs(prompt: str, frame_specs: Dict) -> str:
    first = frame_specs.get("first_frame_spec") or {}
    if not first:
        return prompt
    mid = frame_specs.get("mid_frame_spec") or {}
    last = frame_specs.get("last_frame_spec") or {}
    lines = [
        "视频关键帧构图规格（与故事板共用，必须优先执行）：",
        (
            "首帧 first_frame_spec：必须执行 first frame composition alignment；"
            f"画面={first.get('composition', '')}；"
            f"机位高度={first.get('camera_height_lock', '')}；"
            f"camera angle lock={first.get('camera_angle_lock', '')}；"
            f"subject scale lock={first.get('subject_scale_lock', '')}；"
            f"pose lock={first.get('pose_lock', '')}；"
            f"blocking lock={first.get('blocking_lock', '')}；"
            f"action phase lock={first.get('action_phase_lock', '')}；"
            f"screen direction lock={first.get('screen_direction_lock', '')}；"
            f"scene anchor lock={first.get('scene_anchor_lock', '')}。"
        ),
        (
            "中段 mid_frame_spec：同一空间、同一屏幕方向、同一光源方向；"
            f"画面={mid.get('composition', '')}。"
        ),
        (
            "尾帧 last_frame_spec：作为下一段续接状态，不能换场景方向或重置人物站位；"
            f"画面={last.get('composition', '')}。"
        ),
    ]
    return "\n\n".join([prompt, "\n".join(lines)])


def _reference_role(ref) -> str:
    if isinstance(ref, dict):
        return str(ref.get("role") or ref.get("asset_kind") or "").strip()
    return ""


def _reference_label(ref) -> str:
    if isinstance(ref, dict):
        value = ref.get("path") or ref.get("url") or ref.get("filename") or ref.get("lock") or ""
    else:
        value = str(ref or "")
    name = os.path.basename(str(value)).strip()
    return f"（{name}）" if name else ""


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
    storyboard_refs = []
    for item in unit.get("storyboard_panel_refs") or []:
        ref = _normalize_reference(item)
        if ref.get("url") or ref.get("path"):
            storyboard_refs.append(ref)
    if explicit:
        return _normalize_reference_list(explicit) + _previous_reference_refs(unit) + storyboard_refs
    if image_urls:
        return []
    refs = []
    refs.extend(_previous_reference_refs(unit))
    for item in unit.get("video_reference_images") or []:
        ref = _normalize_reference(item)
        if ref.get("url") or ref.get("path"):
            refs.append(ref)
    refs.extend(storyboard_refs)
    return refs


def _previous_reference_refs(unit: Dict) -> List[Dict]:
    previous = unit.get("previous_clip_reference_frame")
    if not previous:
        return []
    ref = _normalize_reference(previous)
    return [ref] if ref.get("url") or ref.get("path") else []


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
            "first_frame_spec": request.get("first_frame_spec", {}),
            "mid_frame_spec": request.get("mid_frame_spec", {}),
            "last_frame_spec": request.get("last_frame_spec", {}),
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
