import mimetypes
import os
import time
from typing import Dict, List, Optional

import requests

try:
    from .config import VideoProviderConfig
except ImportError:
    from config import VideoProviderConfig


class PoYoVideoClient:
    def __init__(self, config: VideoProviderConfig):
        if not config.api_key:
            raise RuntimeError("Missing VIDEO_API_KEY or POYO_API_KEY for poyo_video")
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {config.api_key}"})

    def run_seedance2(
        self,
        request: Dict,
        output_dir: str,
        callback_url: Optional[str] = None,
        download: bool = True,
    ) -> Dict:
        payload = self.build_submit_payload(request, callback_url=callback_url)
        task_id = self.submit(payload)
        data = self.wait_for_task(task_id)
        local_paths = self.download_files(data.get("files") or [], output_dir, request) if download else []
        return {
            "task_id": task_id,
            "status": data.get("status"),
            "credits_amount": data.get("credits_amount"),
            "files": data.get("files", []),
            "local_paths": local_paths,
            "raw": data,
            "payload": payload,
        }

    def build_submit_payload(self, request: Dict, callback_url: Optional[str] = None) -> Dict:
        model = request.get("model") or "seedance-2"
        input_obj = {
            "prompt": request["prompt"],
            "resolution": _valid_resolution(model, request.get("resolution")),
            "duration": _valid_duration(request.get("duration_sec")),
        }
        if request.get("aspect_ratio"):
            input_obj["aspect_ratio"] = request["aspect_ratio"]
        if request.get("generate_audio") is not None:
            input_obj["generate_audio"] = bool(request.get("generate_audio"))
        if request.get("seed") is not None:
            input_obj["seed"] = int(request["seed"])

        references = self._resolve_reference_inputs(request)
        input_obj.update(references)

        payload: Dict[str, object] = {"model": model, "input": input_obj}
        if callback_url:
            payload["callback_url"] = callback_url
        return payload

    def submit(self, payload: Dict) -> str:
        response = self.session.post(
            f"{self.config.api_base or 'https://api.poyo.ai'}/api/generate/submit",
            json=payload,
            timeout=120,
        )
        self._raise_for_error(response)
        body = response.json()
        task_id = body.get("data", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"PoYo video submit did not return task_id: {body}")
        return task_id

    def get_task_status(self, task_id: str) -> Dict:
        response = self.session.get(
            f"{self.config.api_base or 'https://api.poyo.ai'}/api/generate/status/{task_id}",
            timeout=60,
        )
        self._raise_for_error(response)
        return response.json().get("data", {})

    def wait_for_task(self, task_id: str) -> Dict:
        start = time.time()
        interval = max(2, int(self.config.poll_interval_sec or 4))
        backoff = interval
        while True:
            if time.time() - start > self.config.poll_timeout_sec:
                raise TimeoutError(f"PoYo video task {task_id} did not complete within {self.config.poll_timeout_sec}s")
            try:
                data = self.get_task_status(task_id)
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
                raise RuntimeError(data.get("error_message") or f"PoYo video task {task_id} failed")
            time.sleep(interval)

    def upload_file(self, file_path: str, upload_path: Optional[str] = None) -> str:
        upload_name = os.path.basename(file_path)
        mime_type = mimetypes.guess_type(upload_name)[0] or "application/octet-stream"
        with open(file_path, "rb") as fh:
            files = {"file": (upload_name, fh, mime_type)}
            data = {"file_name": upload_name}
            if upload_path:
                data["upload_path"] = upload_path
            response = self.session.post(
                f"{self.config.api_base or 'https://api.poyo.ai'}/api/common/upload/stream",
                files=files,
                data=data,
                timeout=120,
            )
        self._raise_for_error(response)
        body = response.json()
        file_url = body.get("data", {}).get("file_url")
        if not file_url:
            raise RuntimeError(f"PoYo upload did not return file_url: {body}")
        return file_url

    def download_files(self, files: List[Dict], output_dir: str, request: Dict) -> List[str]:
        os.makedirs(output_dir, exist_ok=True)
        local_paths = []
        for index, file_info in enumerate(files, start=1):
            file_url = file_info.get("file_url")
            if not file_url:
                continue
            suffix = _suffix_for_file(file_info)
            base = os.path.splitext(
                request.get("output_filename") or request.get("clip_id") or request.get("shot_id") or request.get("unit_id") or "video"
            )[0]
            out_path = os.path.join(output_dir, f"{base}_{index:02d}{suffix}")
            local_paths.append(self.download(file_url, out_path))
        return local_paths

    def download(self, file_url: str, out_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with self.session.get(file_url, stream=True, timeout=180) as response:
            self._raise_for_error(response)
            with open(out_path, "wb") as fh:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        fh.write(chunk)
        return out_path

    def _resolve_reference_inputs(self, request: Dict) -> Dict:
        image_urls = [_resolve_url(self, item) for item in request.get("image_urls") or []]
        reference_image_urls = [_resolve_url(self, item) for item in request.get("reference_image_urls") or []]
        reference_video_urls = [_resolve_url(self, item) for item in request.get("reference_video_urls") or []]
        reference_audio_urls = [_resolve_url(self, item) for item in request.get("reference_audio_urls") or []]

        if image_urls and (reference_image_urls or reference_video_urls or reference_audio_urls):
            raise ValueError("PoYo Seedance 2 does not allow image_urls together with reference_*_urls")

        result = {}
        if image_urls:
            result["image_urls"] = image_urls[:2]
        if reference_image_urls:
            result["reference_image_urls"] = reference_image_urls[:9]
        if reference_video_urls:
            result["reference_video_urls"] = reference_video_urls[:3]
        if reference_audio_urls:
            result["reference_audio_urls"] = reference_audio_urls[:3]
        if reference_audio_urls and not (reference_image_urls or reference_video_urls):
            raise ValueError("reference_audio_urls requires at least one reference image or reference video")
        if len(reference_image_urls) + len(reference_video_urls) + len(reference_audio_urls) > 12:
            raise ValueError("PoYo Seedance 2 supports at most 12 reference files total")
        return result

    @staticmethod
    def _raise_for_error(response: requests.Response) -> None:
        if response.ok:
            return
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Provider request failed: {response.status_code} {detail}")


def _resolve_url(client: PoYoVideoClient, item) -> str:
    if isinstance(item, str):
        if item.startswith(("http://", "https://")):
            return item
        return client.upload_file(item, upload_path="video-reference")
    if item.get("url"):
        return item["url"]
    if item.get("path"):
        return client.upload_file(item["path"], upload_path=item.get("upload_path") or "video-reference")
    raise ValueError(f"Reference item must contain url or path: {item}")


def _valid_duration(value) -> int:
    duration = int(round(float(value or 5)))
    return max(4, min(duration, 15))


def _valid_resolution(model: str, resolution: Optional[str]) -> str:
    requested = resolution or "480p"
    if model == "seedance-2-fast" and requested == "1080p":
        return "720p"
    if requested not in {"480p", "720p", "1080p"}:
        return "720p"
    return requested


def _suffix_for_file(file_info: Dict) -> str:
    if file_info.get("format"):
        return f".{str(file_info['format']).lstrip('.')}"
    content_type = file_info.get("content_type") or ""
    if "video" in content_type:
        return ".mp4"
    if "image" in content_type:
        return ".png"
    if "audio" in content_type:
        return ".mp3"
    return {"video": ".mp4", "image": ".png", "audio": ".mp3", "3d": ".glb"}.get(file_info.get("file_type"), ".bin")
