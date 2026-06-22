import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageProviderConfig:
    provider: str
    api_key: str
    api_base: str
    gen_model: str
    edit_model: str
    output_root: str
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


def load_image_provider_config() -> ImageProviderConfig:
    provider = _env("IMAGE_PROVIDER", "poyo") or "poyo"
    api_key = _env("IMAGE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing IMAGE_API_KEY environment variable")

    api_base = _env("IMAGE_API_BASE", "https://api.poyo.ai") or "https://api.poyo.ai"
    gen_model = _env("IMAGE_GEN_MODEL", "gpt-image-2") or "gpt-image-2"
    edit_model = _env("IMAGE_EDIT_MODEL", "gpt-image-2-edit") or "gpt-image-2-edit"
    output_root = _env("IMAGE_OUTPUT_ROOT", default_output_root())

    poll_interval_sec = int(_env("IMAGE_POLL_INTERVAL_SEC", "3") or "3")
    poll_timeout_sec = int(_env("IMAGE_POLL_TIMEOUT_SEC", "600") or "600")

    return ImageProviderConfig(
        provider=provider,
        api_key=api_key,
        api_base=api_base.rstrip("/"),
        gen_model=gen_model,
        edit_model=edit_model,
        output_root=output_root,
        poll_interval_sec=poll_interval_sec,
        poll_timeout_sec=poll_timeout_sec,
    )
