import mimetypes
import os
import time
from typing import Dict, List, Optional

import requests

try:
    from .config import ImageProviderConfig
except ImportError:
    from config import ImageProviderConfig


class PoYoClient:
    def __init__(self, config: ImageProviderConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.api_key}",
            }
        )

    def submit_text_to_image(
        self,
        prompt: str,
        quality: str = "high",
        size: str = "1:1",
        resolution: str = "2K",
        image_urls: Optional[List[str]] = None,
        callback_url: Optional[str] = None,
    ) -> str:
        payload: Dict[str, object] = {
            "model": self.config.gen_model,
            "input": {
                "prompt": prompt,
                "quality": quality,
                "size": size,
                "resolution": resolution,
            },
        }
        if image_urls:
            payload["input"]["image_urls"] = image_urls
        if callback_url:
            payload["callback_url"] = callback_url
        return self._submit_task(payload)

    def submit_image_edit(
        self,
        prompt: str,
        image_urls: List[str],
        quality: str = "high",
        size: str = "1:1",
        resolution: Optional[str] = None,
        callback_url: Optional[str] = None,
    ) -> str:
        payload: Dict[str, object] = {
            "model": self.config.edit_model,
            "input": {
                "prompt": prompt,
                "image_urls": image_urls,
                "quality": quality,
                "size": size,
            },
        }
        if resolution:
            payload["input"]["resolution"] = resolution
        if callback_url:
            payload["callback_url"] = callback_url
        return self._submit_task(payload)

    def upload_file_stream(
        self,
        file_path: str,
        upload_path: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> Dict:
        upload_name = file_name or os.path.basename(file_path)
        mime_type = mimetypes.guess_type(upload_name)[0] or "application/octet-stream"
        with open(file_path, "rb") as fh:
            files = {"file": (upload_name, fh, mime_type)}
            data = {}
            if upload_path:
                data["upload_path"] = upload_path
            if file_name:
                data["file_name"] = file_name
            response = self.session.post(
                f"{self.config.api_base}/api/common/upload/stream",
                files=files,
                data=data,
                timeout=120,
            )
        self._raise_for_error(response)
        payload = response.json()
        return payload["data"]

    def get_task_status(self, task_id: str) -> Dict:
        response = self.session.get(
            f"{self.config.api_base}/api/generate/status/{task_id}",
            timeout=60,
        )
        self._raise_for_error(response)
        payload = response.json()
        return payload["data"]

    def wait_for_task(self, task_id: str) -> Dict:
        start = time.time()
        interval = max(1, self.config.poll_interval_sec)

        while True:
            if time.time() - start > self.config.poll_timeout_sec:
                raise TimeoutError(
                    f"Task {task_id} did not complete within {self.config.poll_timeout_sec}s"
                )

            data = self.get_task_status(task_id)
            status = data["status"]
            if status == "finished":
                return data
            if status == "failed":
                raise RuntimeError(data.get("error_message") or f"Task {task_id} failed")

            time.sleep(interval)

    def download_file(self, file_url: str, out_path: str) -> str:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with self.session.get(file_url, stream=True, timeout=120) as response:
            self._raise_for_error(response)
            with open(out_path, "wb") as fh:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        fh.write(chunk)
        return out_path

    def _submit_task(self, payload: Dict[str, object]) -> str:
        response = self.session.post(
            f"{self.config.api_base}/api/generate/submit",
            json=payload,
            timeout=120,
        )
        self._raise_for_error(response)
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else None
        task_id = data.get("task_id") if isinstance(data, dict) else None
        if not task_id:
            raise RuntimeError(f"Provider submit did not return task_id: {body}")
        return task_id

    @staticmethod
    def _raise_for_error(response: requests.Response) -> None:
        if response.ok:
            return
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Provider request failed: {response.status_code} {detail}")
