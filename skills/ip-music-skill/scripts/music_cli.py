import argparse
import json
import os

try:
    from .music_skill import run_task
except ImportError:
    from music_skill import run_task


def _parse_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out-dir", default="", help="Output directory")
    parser.add_argument("--mv", default="", help="Suno model version, for example V5")


def _parse_generated_audio_ids(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task-id", required=True, help="Upstream provider task_id")
    parser.add_argument("--audio-id", required=True, help="Upstream provider audio_id")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IP music skill CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    generate = sub.add_parser("generate", help="Generate music from prompt")
    generate.add_argument("--prompt", required=True)
    generate.add_argument("--style", default="")
    generate.add_argument("--title", default="")
    generate.add_argument("--instrumental", action="store_true")
    generate.add_argument("--out", default="generated_music.mp3")
    _parse_common(generate)

    handoff = sub.add_parser("handoff", help="Build music handoff from JSON task")
    handoff.add_argument("--task", required=True)

    stems = sub.add_parser("stems", help="Split a generated music track into stems")
    _parse_generated_audio_ids(stems)
    _parse_common(stems)

    separate = sub.add_parser("separate", help="Separate vocals from a generated music track")
    _parse_generated_audio_ids(separate)
    _parse_common(separate)

    upload_separate = sub.add_parser("upload-separate", help="Separate vocals/stems from an uploaded audio file")
    upload_separate.add_argument("--audio", required=True, help="Local audio path")
    _parse_common(upload_separate)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd == "handoff":
        with open(args.task, "r", encoding="utf-8") as fh:
            task = json.load(fh)
    elif args.cmd == "generate":
        task = {
            "mode": "generate_music",
            "prompt": args.prompt,
            "style": args.style,
            "title": args.title,
            "instrumental": args.instrumental,
            "filename": args.out,
        }
        if args.out_dir:
            task["output_dir"] = args.out_dir
        if args.mv:
            task["mv"] = args.mv
    elif args.cmd in {"stems", "separate"}:
        task = {
            "mode": "stem_split" if args.cmd == "stems" else "separate_vocals",
            "source_task_id": args.task_id,
            "audio_id": args.audio_id,
        }
        if args.out_dir:
            task["output_dir"] = args.out_dir
        if args.mv:
            task["mv"] = args.mv
    elif args.cmd == "upload-separate":
        task = {
            "mode": "upload_separate_vocals",
            "audio_path": args.audio,
        }
        if args.out_dir:
            task["output_dir"] = args.out_dir
        if args.mv:
            task["mv"] = args.mv
    else:
        raise ValueError(args.cmd)

    result = run_task(task)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
