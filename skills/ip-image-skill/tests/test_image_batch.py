import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from image_skill import _run_image_batch  # noqa: E402


class FakeClient:
    def __init__(self):
        self.submitted = []
        self.waited = []

    def submit_text_to_image(self, prompt, quality="high", size="1:1", resolution="2K", image_urls=None):
        task_id = f"task_{len(self.submitted) + 1:02d}"
        self.submitted.append(
            {
                "task_id": task_id,
                "prompt": prompt,
                "quality": quality,
                "size": size,
                "resolution": resolution,
                "image_urls": image_urls or [],
            }
        )
        return task_id

    def wait_for_task(self, task_id):
        self.waited.append(task_id)
        return {"files": [{"file_url": f"https://example.test/{task_id}.jpg"}]}

    def download_file(self, file_url, out_path):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as fh:
            fh.write(file_url.encode("utf-8"))
        return out_path


def test_image_batch_submits_all_before_waiting():
    with tempfile.TemporaryDirectory() as output_dir:
        client = FakeClient()
        result = _run_image_batch(
            {
                "mode": "image_batch",
                "tasks": [
                    {"mode": "text_to_image", "prompt": "scene", "filename": "scene.jpg"},
                    {"mode": "character_create", "prompt": "character", "filename": "character.jpg"},
                ],
            },
            output_dir,
            client,
        )
        assert result["status"] == "success"
        assert [item["task_id"] for item in client.submitted] == ["task_01", "task_02"]
        assert client.waited == ["task_01", "task_02"]
        assert len(result["artifacts"]) == 2
        assert os.path.exists(os.path.join(output_dir, "scene.jpg"))
        assert os.path.exists(os.path.join(output_dir, "character.jpg"))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
