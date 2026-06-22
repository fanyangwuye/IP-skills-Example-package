import os
from dataclasses import dataclass


@dataclass(frozen=True)
class MusicProviderConfig:
    provider: str
    api_key: str
    api_base: str
    output_root: str
    default_model_version: str
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


def load_music_provider_config() -> MusicProviderConfig:
    provider = _env("MUSIC_PROVIDER", "poyo") or "poyo"
    api_key = _env("MUSIC_API_KEY") or _env("POYO_API_KEY")
    if not api_key:
        raise RuntimeError("Missing MUSIC_API_KEY or POYO_API_KEY environment variable")

    api_base = _env("MUSIC_API_BASE") or _env("POYO_BASE_URL", "https://api.poyo.ai")
    output_root = _env("MUSIC_OUTPUT_ROOT", default_output_root())
    default_model_version = _env("MUSIC_DEFAULT_MODEL_VERSION", "V5") or "V5"
    poll_interval_sec = int(_env("MUSIC_POLL_INTERVAL_SEC", "4") or "4")
    poll_timeout_sec = int(_env("MUSIC_POLL_TIMEOUT_SEC", "600") or "600")

    return MusicProviderConfig(
        provider=provider,
        api_key=api_key,
        api_base=api_base.rstrip("/"),
        output_root=output_root,
        default_model_version=default_model_version,
        poll_interval_sec=poll_interval_sec,
        poll_timeout_sec=poll_timeout_sec,
    )
