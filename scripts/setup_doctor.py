import argparse
import json
import os
import shutil
import sys
from typing import Callable, Dict, List, Optional


CheckResult = Dict[str, object]


def run_checks(env: Optional[Dict[str, str]] = None, which: Optional[Callable[[str], Optional[str]]] = None) -> Dict:
    env = dict(os.environ if env is None else env)
    which = which or shutil.which
    checks: List[CheckResult] = []

    checks.append(_python_check())
    checks.extend(_poyo_checks(env))
    checks.extend(_ffmpeg_checks(env, which))
    checks.extend(_dreamina_checks(env, which))
    checks.extend(_output_checks(env))

    summary = _summary(checks)
    return {
        "status": summary["status"],
        "summary": summary,
        "checks": checks,
        "next_steps": _next_steps(checks),
    }


def _python_check() -> CheckResult:
    version = ".".join(str(part) for part in sys.version_info[:3])
    ok = sys.version_info >= (3, 8)
    return _check(
        "python.version",
        "pass" if ok else "fail",
        f"Python {version}",
        "Use Python 3.8+." if not ok else "",
    )


def _poyo_checks(env: Dict[str, str]) -> List[CheckResult]:
    poyo_key = _env(env, "POYO_API_KEY")
    video_provider = _env(env, "VIDEO_PROVIDER", "offline") or "offline"
    image_key = _env(env, "IMAGE_API_KEY") or poyo_key
    music_key = _env(env, "MUSIC_API_KEY") or poyo_key
    video_key = _env(env, "VIDEO_API_KEY") or poyo_key
    video_status = "pass" if video_key else ("warn" if video_provider == "poyo_video" else "info")

    return [
        _check(
            "poyo.image_key",
            "pass" if image_key else "warn",
            "PoYo image key is configured." if image_key else "PoYo image key is missing.",
            "Set IMAGE_API_KEY or POYO_API_KEY for live image generation." if not image_key else "",
        ),
        _check(
            "poyo.music_key",
            "pass" if music_key else "warn",
            "PoYo music key is configured." if music_key else "PoYo music key is missing.",
            "Set MUSIC_API_KEY or POYO_API_KEY for live music generation." if not music_key else "",
        ),
        _check(
            "poyo.video_key",
            video_status,
            "PoYo video key is configured." if video_key else "PoYo video key is not configured.",
            "Set VIDEO_API_KEY or POYO_API_KEY for live poyo_video generation." if not video_key and video_provider == "poyo_video" else "",
        ),
        _check(
            "poyo.base_url",
            "pass",
            f"PoYo base URL: {_env(env, 'IMAGE_API_BASE') or _env(env, 'MUSIC_API_BASE') or _env(env, 'POYO_BASE_URL') or 'https://api.poyo.ai'}",
            "",
        ),
    ]


def _ffmpeg_checks(env: Dict[str, str], which: Callable[[str], Optional[str]]) -> List[CheckResult]:
    ffmpeg = _env(env, "MUSIC_FFMPEG_BIN") or _env(env, "FFMPEG_BIN") or which("ffmpeg")
    ffprobe = _env(env, "MUSIC_FFPROBE_BIN") or _env(env, "FFPROBE_BIN") or which("ffprobe")
    return [
        _check(
            "ffmpeg.binary",
            "pass" if ffmpeg else "warn",
            f"ffmpeg found: {ffmpeg}" if ffmpeg else "ffmpeg not found.",
            "Install ffmpeg or set MUSIC_FFMPEG_BIN if you need local WAV/MP3 upload proxy wrapping." if not ffmpeg else "",
        ),
        _check(
            "ffmpeg.ffprobe",
            "pass" if ffprobe else "info",
            f"ffprobe found: {ffprobe}" if ffprobe else "ffprobe not found.",
            "Set MUSIC_FFPROBE_BIN if duration probing is needed for future audio/video checks." if not ffprobe else "",
        ),
    ]


def _dreamina_checks(env: Dict[str, str], which: Callable[[str], Optional[str]]) -> List[CheckResult]:
    provider = _env(env, "VIDEO_PROVIDER", "offline") or "offline"
    dreamina = _env(env, "DREAMINA_CLI_PATH") or _env(env, "JIMENG_CLI_PATH") or which("dreamina")
    status = "pass" if provider not in {"dreamina_cli", "jimeng_cli"} or dreamina else "warn"
    message = f"VIDEO_PROVIDER={provider}."
    if dreamina:
        message += f" dreamina found: {dreamina}"
    elif provider in {"dreamina_cli", "jimeng_cli"}:
        message += " dreamina CLI not found."
    else:
        message += " Dreamina CLI is optional until VIDEO_PROVIDER=dreamina_cli."
    return [
        _check(
            "dreamina.provider",
            status,
            message,
            "Install Dreamina CLI yourself, then run dreamina login and dreamina -h." if status == "warn" else "",
        )
    ]


def _output_checks(env: Dict[str, str]) -> List[CheckResult]:
    output_roots = [
        ("image.output_root", _env(env, "IMAGE_OUTPUT_ROOT")),
        ("music.output_root", _env(env, "MUSIC_OUTPUT_ROOT")),
        ("video.output_root", _env(env, "VIDEO_OUTPUT_ROOT")),
    ]
    checks = []
    for name, path in output_roots:
        if not path:
            checks.append(_check(name, "info", f"{name} is not set.", "Default project outputs/ will be used where supported."))
            continue
        parent = path if os.path.isdir(path) else os.path.dirname(path) or path
        exists_or_parent_exists = os.path.isdir(path) or os.path.isdir(parent)
        checks.append(
            _check(
                name,
                "pass" if exists_or_parent_exists else "warn",
                f"{name}: {path}",
                "Create this output directory before live generation." if not exists_or_parent_exists else "",
            )
        )
    return checks


def _summary(checks: List[CheckResult]) -> Dict[str, int]:
    counts = {"pass": 0, "warn": 0, "fail": 0, "info": 0}
    for check in checks:
        counts[str(check["status"])] += 1
    status = "fail" if counts["fail"] else ("warn" if counts["warn"] else "pass")
    return {"status": status, **counts}


def _next_steps(checks: List[CheckResult]) -> List[str]:
    steps = []
    for check in checks:
        if check["status"] in {"warn", "fail"} and check.get("fix"):
            steps.append(str(check["fix"]))
    return _dedupe(steps)


def _check(name: str, status: str, message: str, fix: str = "") -> CheckResult:
    return {"name": name, "status": status, "message": message, "fix": fix}


def _env(env: Dict[str, str], name: str, default: str = "") -> str:
    return str(env.get(name, default) or "").strip()


def _dedupe(items: List[str]) -> List[str]:
    result = []
    seen = set()
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _format_text(report: Dict) -> str:
    lines = [f"setup_doctor status: {report['status']}"]
    for check in report["checks"]:
        lines.append(f"[{check['status']}] {check['name']}: {check['message']}")
        if check.get("fix"):
            lines.append(f"  fix: {check['fix']}")
    if report["next_steps"]:
        lines.append("next steps:")
        lines.extend(f"- {step}" for step in report["next_steps"])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    parser.add_argument("--output", help="Optional path to write the JSON report")
    args = parser.parse_args()

    report = run_checks()
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_format_text(report))


if __name__ == "__main__":
    main()
