import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
import time
from typing import Dict, List, Optional

import requests

try:
    from .config import MusicProviderConfig
except ImportError:
    from config import MusicProviderConfig


class PoYoMusicClient:
    music_detail_path = "/api/generate/detail/music"
    stem_fields = (
        "stem_split",
        "vocal_removal",
        "separate_vocals",
        "upload_separate_vocals",
        "upload_and_separate_vocals",
    )

    def __init__(self, config: MusicProviderConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {config.api_key}"})

    def submit_music(self, model: str, input_obj: Dict, callback_url: Optional[str] = None) -> str:
        payload: Dict[str, object] = {"model": model, "input": input_obj}
        if callback_url:
            payload["callback_url"] = callback_url
        response = self.session.post(
            f"{self.config.api_base}/api/generate/submit",
            json=payload,
            timeout=120,
        )
        self._raise_for_error(response)
        body = response.json()
        task_id = body.get("data", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"Provider did not return task_id: {body}")
        return task_id

    def get_music_detail(self, task_id: str) -> Dict:
        response = self.session.get(
            f"{self.config.api_base}{self.music_detail_path}",
            params={"task_id": task_id},
            timeout=60,
        )
        self._raise_for_error(response)
        return response.json().get("data", {})

    def wait_for_music(self, task_id: str) -> Dict:
        start = time.time()
        interval = max(1, self.config.poll_interval_sec)
        backoff = interval
        while True:
            if time.time() - start > self.config.poll_timeout_sec:
                raise TimeoutError(
                    f"Music task {task_id} did not complete within {self.config.poll_timeout_sec}s"
                )
            try:
                data = self.get_music_detail(task_id)
            except RuntimeError as exc:
                message = str(exc)
                if any(code in message for code in ("429", "500", "502", "503")):
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
                raise
            backoff = interval
            status = data.get("status")
            if status == "finished":
                return data
            if status == "failed":
                raise RuntimeError(data.get("error_message") or f"Music task {task_id} failed")
            time.sleep(interval)

    def run_music(
        self,
        model: str,
        input_obj: Dict,
        out_path: Optional[str] = None,
        callback_url: Optional[str] = None,
        download_all: bool = True,
        download_cover_images: bool = True,
    ) -> Dict:
        task_id = self.submit_music(model, input_obj, callback_url=callback_url)
        data = self.wait_for_music(task_id)
        audios = self.parse_audio_results(data)
        stems = self.parse_stems(data)
        local_path = None
        local_paths = []
        local_cover_paths = []
        if out_path and audios:
            targets = [_variant_path(out_path, index) for index in range(len(audios))] if download_all else [out_path]
            for audio, target in zip(audios, targets):
                local_paths.append(self.download(audio["audio_url"], target))
                if download_cover_images and audio.get("image_url"):
                    local_cover_paths.append(self.download(audio["image_url"], _cover_path(target)))
            local_path = local_paths[0] if local_paths else None
        return {
            "task_id": task_id,
            "audios": audios,
            "stems": stems,
            "credits_amount": data.get("credits_amount"),
            "local_path": local_path,
            "local_paths": local_paths,
            "local_cover_paths": local_cover_paths,
            "raw": data,
        }

    def upload(self, file_path: str, file_name: Optional[str] = None) -> str:
        return self.upload_file(file_path, file_name=file_name)

    def upload_file(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        upload_path: Optional[str] = None,
        proxy_dir: Optional[str] = None,
        keep_proxy: bool = True,
    ) -> str:
        actual_path = file_path
        cleanup_dir = None
        upload_name = file_name or os.path.basename(actual_path)
        mime_type = mimetypes.guess_type(upload_name)[0] or "application/octet-stream"

        if mime_type.startswith("audio/"):
            actual_path, cleanup_dir = self._wrap_audio_as_mp4(
                file_path,
                proxy_dir=proxy_dir if keep_proxy else None,
            )
            upload_name = os.path.basename(actual_path)
            mime_type = "video/mp4"
            upload_path = upload_path or "music-audio-proxy"

        try:
            with open(actual_path, "rb") as fh:
                files = {"file": (upload_name, fh, mime_type)}
                data = {"file_name": upload_name}
                if upload_path:
                    data["upload_path"] = upload_path
                response = self.session.post(
                    f"{self.config.api_base}/api/common/upload/stream",
                    files=files,
                    data=data,
                    timeout=120,
                )
        finally:
            if cleanup_dir:
                shutil.rmtree(cleanup_dir, ignore_errors=True)

        try:
            self._raise_for_error(response)
        except RuntimeError as exc:
            if mime_type.startswith("audio/") and "Unsupported file type" in str(exc):
                raise RuntimeError(
                    "Provider upload endpoint rejected this pure audio file type. "
                    "Pass a public audio_url, or wrap the audio into an MP4 proxy "
                    "and upload the MP4 before running live music remix modes."
                ) from exc
            raise
        body = response.json()
        file_url = body.get("data", {}).get("file_url")
        if not file_url:
            raise RuntimeError(f"Upload did not return file_url: {body}")
        return file_url

    def _wrap_audio_as_mp4(self, file_path: str, proxy_dir: Optional[str] = None):
        ffmpeg = _find_binary("MUSIC_FFMPEG_BIN", "FFMPEG_BIN", "ffmpeg")
        if not ffmpeg:
            raise RuntimeError(
                "ffmpeg is required to upload local audio files. Install ffmpeg, "
                "or set MUSIC_FFMPEG_BIN/FFMPEG_BIN, or pass a public audio_url."
            )

        cleanup_dir = None
        if proxy_dir:
            os.makedirs(proxy_dir, exist_ok=True)
            out_dir = proxy_dir
        else:
            cleanup_dir = tempfile.mkdtemp(prefix="poyo_audio_proxy_")
            out_dir = cleanup_dir

        stem = _safe_ascii_stem(os.path.splitext(os.path.basename(file_path))[0])
        out_path = os.path.join(out_dir, f"{stem}_upload_proxy.mp4")
        duration = _probe_duration(file_path)

        color_input = "color=c=black:s=1280x720:r=1"
        if duration:
            color_input += f":d={duration:.3f}"

        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            color_input,
            "-i",
            file_path,
        ]
        if duration:
            cmd.extend(["-t", f"{duration:.3f}"])
        cmd.extend(
            [
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "veryfast",
                "-tune",
                "stillimage",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                out_path,
            ]
        )
        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(f"ffmpeg failed to create MP4 audio proxy: {completed.stderr}")
        return out_path, cleanup_dir

    def download(self, file_url: str, out_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with self.session.get(file_url, stream=True, timeout=120) as response:
            self._raise_for_error(response)
            with open(out_path, "wb") as fh:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        fh.write(chunk)
        return out_path

    def parse_audio_results(self, data: Dict) -> List[Dict]:
        audios = []
        for file_info in data.get("files", []):
            if file_info.get("audio_url"):
                audios.append(
                    {
                        "audio_id": file_info.get("audio_id"),
                        "audio_url": file_info.get("audio_url"),
                        "title": file_info.get("title"),
                        "duration": file_info.get("duration"),
                        "image_url": file_info.get("image_url"),
                    }
                )
        return audios

    def parse_stems(self, data: Dict) -> Dict:
        for file_info in data.get("files", []):
            for field in self.stem_fields:
                if field in file_info:
                    raw = file_info[field]
                    try:
                        stems = json.loads(raw) if isinstance(raw, str) else raw
                    except Exception:
                        stems = {}
                    return {key: value for key, value in (stems or {}).items() if value}
        return {}

    @staticmethod
    def _raise_for_error(response: requests.Response) -> None:
        if response.ok:
            return
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Provider request failed: {response.status_code} {detail}")


def _find_binary(*env_names_and_default: str) -> Optional[str]:
    default_name = env_names_and_default[-1]
    for name in env_names_and_default[:-1]:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return shutil.which(default_name)


def _probe_duration(file_path: str) -> Optional[float]:
    ffprobe = _find_binary("MUSIC_FFPROBE_BIN", "FFPROBE_BIN", "ffprobe")
    if not ffprobe:
        return None
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    try:
        duration = float(completed.stdout.strip())
    except ValueError:
        return None
    return duration if duration > 0 else None


def _safe_ascii_stem(stem: str) -> str:
    safe = "".join(ch if ch.isascii() and (ch.isalnum() or ch in ("-", "_")) else "_" for ch in stem)
    safe = safe.strip("_")
    return safe or "audio"


def _variant_path(out_path: str, index: int) -> str:
    if index == 0:
        return out_path
    root, ext = os.path.splitext(out_path)
    return f"{root}_variant_{index + 1:02d}{ext or '.mp3'}"


def _cover_path(audio_path: str) -> str:
    root, _ = os.path.splitext(audio_path)
    return f"{root}_cover.jpg"
