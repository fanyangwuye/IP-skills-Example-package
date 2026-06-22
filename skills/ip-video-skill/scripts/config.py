import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VideoProviderConfig:
    provider: str
    api_key: str
    api_base: str
    output_root: str
    default_model: str
    default_aspect_ratio: str
    default_resolution: str
    poll_interval_sec: int
    poll_timeout_sec: int


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def scripts_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def skill_root() -> str:
    return os.path.dirname(scripts_root())


def project_root() -> str:
    return os.path.dirname(os.path.dirname(skill_root()))


def default_output_root() -> str:
    return os.path.join(project_root(), "outputs")


def load_video_provider_config() -> VideoProviderConfig:
    provider = _env("VIDEO_PROVIDER", "offline") or "offline"
    return VideoProviderConfig(
        provider=provider,
        api_key=_env("VIDEO_API_KEY") or _env("JIMENG_API_KEY") or _env("POYO_API_KEY"),
        api_base=(_env("VIDEO_API_BASE") or _env("JIMENG_API_BASE") or _env("POYO_BASE_URL")).rstrip("/"),
        output_root=_env("VIDEO_OUTPUT_ROOT", default_output_root()),
        default_model=_env("VIDEO_DEFAULT_MODEL", ""),
        default_aspect_ratio=_env("VIDEO_DEFAULT_ASPECT_RATIO", "9:16") or "9:16",
        default_resolution=_env("VIDEO_DEFAULT_RESOLUTION", "480p") or "480p",
        poll_interval_sec=int(_env("VIDEO_POLL_INTERVAL_SEC", "4") or "4"),
        poll_timeout_sec=int(_env("VIDEO_POLL_TIMEOUT_SEC", "600") or "600"),
    )
