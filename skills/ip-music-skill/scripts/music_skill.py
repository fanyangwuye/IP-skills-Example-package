import argparse
import json
import os
from typing import Dict, List, Optional

try:
    from .config import load_music_provider_config
    from .poyo_music_client import PoYoMusicClient
except ImportError:
    from config import load_music_provider_config
    from poyo_music_client import PoYoMusicClient


MODEL_BY_MODE = {
    "generate_music": "generate-music",
    "add_instrumental": "add-instrumental",
    "add_vocals": "add-vocals",
    "cover_audio": "upload-and-cover-audio",
    "extend_music": "extend-music",
    "upload_extend_audio": "upload-and-extend-audio",
    "replace_section": "replace-section",
    "stem_split": "stem-split",
    "separate_vocals": "separate-vocals",
    "upload_separate_vocals": "upload-and-separate-vocals",
}


def run_task(task: Dict) -> Dict:
    mode = task.get("mode", "build_music_handoff")
    if mode == "build_music_handoff":
        return _run_build_music_handoff(task)
    if mode not in MODEL_BY_MODE:
        raise ValueError(
            "mode must be one of: build_music_handoff, "
            + ", ".join(sorted(MODEL_BY_MODE))
        )

    config = load_music_provider_config()
    if config.provider != "poyo":
        raise RuntimeError(f"Unsupported MUSIC_PROVIDER: {config.provider}")
    client = PoYoMusicClient(config)
    output_dir = task.get("output_dir") or config.output_root
    os.makedirs(output_dir, exist_ok=True)
    return _run_live_music_task(task, output_dir, config.default_model_version, client)


def _run_build_music_handoff(task: Dict) -> Dict:
    handoff = build_music_handoff(task)
    output_dir = task.get("output_dir") or os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, task.get("handoff_filename", "music_handoff.json"))
    _write_json(out_path, handoff)
    return {
        "status": "success",
        "skill": "ip-music-skill",
        "mode": "build_music_handoff",
        "task_id": task.get("task_id", "build_music_handoff"),
        "artifacts": [{"type": "json", "path": out_path, "meta": {"kind": "music_handoff"}}],
        "handoff": handoff,
        "logs": [f"built music handoff with {len(handoff['music_tasks'])} music tasks"],
    }


def build_music_handoff(task: Dict) -> Dict:
    script = task.get("polished_script") or task.get("script_draft") or {}
    blueprint = task.get("blueprint") or {}
    scene_cards = task.get("scene_cards") or script.get("handoff", {}).get("scene_cards") or []
    source_title = task.get("title") or script.get("title") or blueprint.get("title", "")
    creative_direction = task.get("creative_direction") or {
        "tone": script.get("tone") or blueprint.get("global_style", {}).get("tone", ""),
        "target": script.get("target") or blueprint.get("target", ""),
        "audience": script.get("audience", ""),
    }
    music_tasks = []

    theme_prompt = _theme_prompt(source_title, creative_direction, script, blueprint)
    music_tasks.append(
        {
            "mode": "generate_music",
            "role": "theme",
            "prompt": theme_prompt,
            "style": _style_from_direction(creative_direction, default="cinematic, theme song, memorable hook"),
            "title": f"{source_title or 'IP'} Theme",
            "instrumental": bool(task.get("theme_instrumental", False)),
            "mv": task.get("mv", "V5"),
            "output_filename": "theme_song.mp3",
        }
    )

    cues = _collect_music_cues(script, blueprint, scene_cards)
    for index, cue in enumerate(cues, start=1):
        music_tasks.append(
            {
                "mode": "generate_music",
                "role": "scene_bgm",
                "prompt": cue.get("prompt", cue.get("music_cue", "")),
                "style": cue.get("style") or _style_from_direction(creative_direction, default="cinematic underscore, short drama bgm"),
                "title": f"{source_title or 'Scene'} BGM {index:02d}",
                "instrumental": True,
                "mv": task.get("mv", "V5"),
                "output_filename": f"scene_bgm_{index:02d}.mp3",
                "scene_ref": cue.get("scene_ref", index),
            }
        )

    return {
        "source_title": source_title,
        "creative_direction": creative_direction,
        "music_tasks": music_tasks,
        "source_summary": {
            "script_id": script.get("script_id", ""),
            "blueprint_id": blueprint.get("blueprint_id", ""),
            "n_scene_cards": len(scene_cards),
        },
    }


def _run_live_music_task(
    task: Dict,
    output_dir: str,
    default_model_version: str,
    client: PoYoMusicClient,
) -> Dict:
    mode = task["mode"]
    input_obj = _build_music_input(task, default_model_version, client)
    model = MODEL_BY_MODE[mode]
    filename = task.get("filename") or task.get("output_filename") or _default_filename(mode)
    out_path = os.path.join(output_dir, filename) if _downloads_audio(mode) else None
    result = client.run_music(
        model,
        input_obj,
        out_path=out_path,
        download_all=bool(task.get("download_all", True)),
    )

    artifacts = []
    local_paths = result.get("local_paths") or ([result["local_path"]] if result.get("local_path") else [])
    for index, local_path in enumerate(local_paths):
        artifacts.append(
            {
                "type": "audio",
                "path": local_path,
                "meta": {
                    "provider": "poyo",
                    "model": model,
                    "task_id": result.get("task_id"),
                    "audio": (result.get("audios") or [{}])[index] if index < len(result.get("audios", [])) else {},
                    "variant_index": index + 1,
                },
            }
        )
    if result.get("stems"):
        artifacts.append(
            {
                "type": "stems",
                "path": output_dir,
                "meta": {
                    "provider": "poyo",
                    "model": model,
                    "task_id": result.get("task_id"),
                    "stems": result.get("stems", {}),
                },
            }
        )

    return {
        "status": "success",
        "skill": "ip-music-skill",
        "mode": mode,
        "task_id": result.get("task_id"),
        "artifacts": artifacts,
        "handoff": {
            "audios": result.get("audios", []),
            "local_paths": local_paths,
            "stems": result.get("stems", {}),
            "credits_amount": result.get("credits_amount"),
        },
        "logs": [f"completed {mode} with model {model}", f"downloaded {len(local_paths)} audio file(s)"],
    }


def _build_music_input(task: Dict, default_model_version: str, client: PoYoMusicClient) -> Dict:
    mode = task["mode"]
    mv = task.get("mv", default_model_version)
    if mode == "generate_music":
        input_obj = {
            "prompt": task["prompt"],
            "custom_mode": bool(task.get("style") or task.get("title") or task.get("instrumental")),
            "instrumental": bool(task.get("instrumental", False)),
            "mv": mv,
        }
        _copy_optional(
            task,
            input_obj,
            ("style", "title", "negative_tags", "vocal_gender", "style_weight", "weirdness_constraint", "persona_id"),
        )
        return input_obj

    if mode in {"add_instrumental", "add_vocals", "cover_audio"}:
        input_obj = {
            "upload_url": _resolve_audio_url(task, client),
            "mv": mv,
        }
        if mode == "add_instrumental":
            input_obj["title"] = task.get("title", "Instrumental")
            input_obj["tags"] = task["tags"]
            _copy_optional(
                task,
                input_obj,
                ("negative_tags", "vocal_gender", "style_weight", "weirdness_constraint", "persona_id"),
            )
        elif mode == "add_vocals":
            input_obj["prompt"] = task["prompt"]
            input_obj["title"] = task.get("title", "With Vocals")
            input_obj["style"] = task["style"]
            _copy_optional(
                task,
                input_obj,
                ("negative_tags", "vocal_gender", "style_weight", "weirdness_constraint", "persona_id"),
            )
        else:
            input_obj["prompt"] = task["prompt"]
            input_obj["custom_mode"] = bool(task.get("style") or task.get("title"))
            input_obj["instrumental"] = bool(task.get("instrumental", False))
            _copy_optional(
                task,
                input_obj,
                (
                    "style",
                    "title",
                    "negative_tags",
                    "vocal_gender",
                    "style_weight",
                    "weirdness_constraint",
                    "audio_weight",
                    "persona_id",
                ),
            )
        return input_obj

    if mode == "upload_extend_audio":
        input_obj = {
            "upload_url": _resolve_audio_url(task, client),
            "default_param_flag": bool(
                task.get(
                    "default_param_flag",
                    bool(task.get("prompt") or task.get("style") or task.get("title")),
                )
            ),
            "instrumental": bool(task.get("instrumental", True)),
            "continue_at": task.get("continue_at", task.get("at", 0)),
            "mv": mv,
        }
        _copy_optional(
            task,
            input_obj,
            (
                "prompt",
                "style",
                "title",
                "negative_tags",
                "vocal_gender",
                "style_weight",
                "weirdness_constraint",
                "audio_weight",
                "persona_id",
            ),
        )
        return input_obj

    if mode == "extend_music":
        input_obj = {
            "default_param_flag": bool(task.get("prompt") or task.get("style") or task.get("continue_at") is not None),
            "audio_id": task["audio_id"],
            "mv": mv,
        }
        if input_obj["default_param_flag"]:
            input_obj["prompt"] = task.get("prompt", "")
            input_obj["style"] = task.get("style", "")
            input_obj["title"] = task.get("title", "Extended")
            input_obj["continue_at"] = task.get("continue_at", task.get("at", 0))
        _copy_optional(task, input_obj, ("negative_tags", "style_weight", "weirdness_constraint", "audio_weight", "persona_id"))
        return input_obj

    if mode == "replace_section":
        input_obj = {
            "task_id": task["source_task_id"],
            "audio_id": task["audio_id"],
            "prompt": task["prompt"],
            "tags": task["tags"],
            "title": task.get("title", "Replaced Section"),
            "infill_start_s": task["start"],
            "infill_end_s": task["end"],
            "full_lyrics": task.get("full_lyrics", ""),
        }
        _copy_optional(task, input_obj, ("negative_tags",))
        return input_obj

    if mode in {"stem_split", "separate_vocals"}:
        return {"task_id": task["source_task_id"], "audio_id": task["audio_id"]}

    if mode == "upload_separate_vocals":
        return {"upload_url": _resolve_audio_url(task, client), "mv": mv}

    raise ValueError(f"Unsupported music mode: {mode}")


def _resolve_audio_url(task: Dict, client: PoYoMusicClient) -> str:
    if task.get("audio_url"):
        return task["audio_url"]
    if task.get("audio_path"):
        return client.upload_file(
            task["audio_path"],
            proxy_dir=task.get("upload_proxy_dir") or task.get("output_dir"),
            keep_proxy=bool(task.get("keep_upload_proxy", True)),
        )
    raise ValueError("audio_url or audio_path is required")


def _copy_optional(source: Dict, target: Dict, keys) -> None:
    for key in keys:
        if source.get(key) not in (None, ""):
            target[key] = source[key]


def _collect_music_cues(script: Dict, blueprint: Dict, scene_cards: List[Dict]) -> List[Dict]:
    cues = []
    if script.get("scenes"):
        for scene in script["scenes"]:
            if scene.get("music_cue"):
                cues.append(
                    {
                        "music_cue": scene["music_cue"],
                        "prompt": scene["music_cue"],
                        "scene_ref": scene.get("scene_no"),
                    }
                )
    elif blueprint.get("segments"):
        for segment in blueprint["segments"]:
            if segment.get("music_cue"):
                cues.append(
                    {
                        "music_cue": segment["music_cue"],
                        "prompt": segment["music_cue"],
                        "scene_ref": segment.get("index"),
                    }
                )
    else:
        for index, card in enumerate(scene_cards, start=1):
            if card.get("music_cue"):
                cues.append(
                    {
                        "music_cue": card["music_cue"],
                        "prompt": card["music_cue"],
                        "scene_ref": index,
                    }
                )
    return cues[: int(script.get("max_bgm_tasks", 4) or 4)] if script else cues[:4]


def _theme_prompt(source_title: str, direction: Dict, script: Dict, blueprint: Dict) -> str:
    parts = [
        f"为《{source_title or '本IP'}》创作一首主题音乐",
        direction.get("tone", ""),
        direction.get("target", ""),
        script.get("source_text", "")[:160] if script else blueprint.get("source_text", "")[:160],
    ]
    return "，".join(part for part in parts if part)


def _style_from_direction(direction: Dict, default: str) -> str:
    tone = str(direction.get("tone", ""))
    if any(word in tone for word in ("悬疑", "诡异", "暗黑", "地府")):
        return "dark cinematic, suspense, low strings, ritual percussion, short drama soundtrack"
    if any(word in tone for word in ("甜", "治愈", "恋爱")):
        return "warm pop, emotional piano, soft strings, romantic short drama"
    return default


def _default_filename(mode: str) -> str:
    return {
        "generate_music": "generated_music.mp3",
        "add_instrumental": "with_instrumental.mp3",
        "add_vocals": "with_vocals.mp3",
        "cover_audio": "cover_audio.mp3",
        "extend_music": "extended_music.mp3",
        "upload_extend_audio": "upload_extended_audio.mp3",
        "replace_section": "replaced_section.mp3",
    }.get(mode, f"{mode}.mp3")


def _downloads_audio(mode: str) -> bool:
    return mode not in {"stem_split", "separate_vocals", "upload_separate_vocals"}


def _write_json(path: str, payload: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="Path to a task JSON file")
    args = parser.parse_args()
    with open(args.task, "r", encoding="utf-8") as fh:
        task = json.load(fh)
    result = run_task(task)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
