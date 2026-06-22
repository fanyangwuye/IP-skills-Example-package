import json
import mimetypes
import os
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
    ) -> Dict:
        task_id = self.submit_music(model, input_obj, callback_url=callback_url)
        data = self.wait_for_music(task_id)
        audios = self.parse_audio_results(data)
        stems = self.parse_stems(data)
        local_path = None
        if out_path and audios:
            local_path = self.download(audios[0]["audio_url"], out_path)
        return {
            "task_id": task_id,
            "audios": audios,
            "stems": stems,
            "credits_amount": data.get("credits_amount"),
            "local_path": local_path,
            "raw": data,
        }

    def upload(self, file_path: str, file_name: Optional[str] = None) -> str:
        upload_name = file_name or os.path.basename(file_path)
        mime_type = mimetypes.guess_type(upload_name)[0] or "application/octet-stream"
        with open(file_path, "rb") as fh:
            files = {"file": (upload_name, fh, mime_type)}
            data = {"file_name": upload_name}
            response = self.session.post(
                f"{self.config.api_base}/api/common/upload/stream",
                files=files,
                data=data,
                timeout=120,
            )
        try:
            self._raise_for_error(response)
        except RuntimeError as exc:
            if mime_type.startswith("audio/") and "Unsupported file type" in str(exc):
                raise RuntimeError(
                    "Provider upload endpoint rejected this audio file type. "
                    "Pass a public audio_url for live music remix modes, or update "
                    "the client when the provider's audio upload endpoint is known."
                ) from exc
            raise
        body = response.json()
        file_url = body.get("data", {}).get("file_url")
        if not file_url:
            raise RuntimeError(f"Upload did not return file_url: {body}")
        return file_url

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
