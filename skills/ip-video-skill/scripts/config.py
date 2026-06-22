import os
from dataclasses import dataclass


@dataclass
class VideoProviderConfig:
    provider: str = "offline"
    api_key: str = ""
    api_base: str = ""
    output_root: str = ""
    default_model: str = ""


def load_video_provider_config() -> VideoProviderConfig:
    return VideoProviderConfig(
        provider=os.getenv("VIDEO_PROVIDER", "offline"),
        api_key=os.getenv("VIDEO_API_KEY", ""),
        api_base=os.getenv("VIDEO_API_BASE", ""),
        output_root=os.getenv("VIDEO_OUTPUT_ROOT", os.getcwd()),
        default_model=os.getenv("VIDEO_DEFAULT_MODEL", ""),
    )
