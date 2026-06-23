import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from asset_pack import build_ip_asset_pack_tasks  # noqa: E402
from prompt_builder import build_task_prompt  # noqa: E402
from image_skill import _run_ip_asset_pack  # noqa: E402


class _RecordingClient:
    """Records the interleaving of submit vs wait calls."""

    def __init__(self):
        self.events = []
        self._submitted = 0

    def submit_text_to_image(self, prompt, quality="high", size="1:1", resolution="2K", image_urls=None):
        self._submitted += 1
        task_id = f"task_{self._submitted:02d}"
        self.events.append(("submit", task_id))
        return task_id

    def wait_for_task(self, task_id):
        self.events.append(("wait", task_id))
        return {"files": [{"file_url": f"https://example.test/{task_id}.jpg"}]}

    def download_file(self, file_url, out_path):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as fh:
            fh.write(file_url.encode("utf-8"))
        return out_path


def test_build_ip_asset_pack_tasks():
    pack = {
        "style_preset": "realistic_short_drama",
        "characters": [
            {
                "character_id": "lin_que",
                "character_profile": {
                    "identity": {"name": "Lin Que"},
                },
                "props": [{"name": "menu ledger"}],
            },
            {
                "character_id": "su_lan",
                "character_profile": {
                    "identity": {"name": "Su Lan"},
                },
            },
        ],
        "scenes": [
            {
                "scene_id": "hotel_exterior",
                "description": "neon hotel in wasteland",
            }
        ],
    }
    tasks = build_ip_asset_pack_tasks(pack, output_dir="out")
    assert len(tasks) == 4
    assert tasks[0]["mode"] == "character_create"
    assert tasks[0]["filename"] == "lin_que_design_sheet.jpg"
    assert "plain neutral background" in tasks[0]["asset_requirements"]
    assert any("not a celebrity face" in item for item in tasks[0]["asset_requirements"])
    assert any("visible pores" in item for item in tasks[0]["asset_requirements"])
    assert tasks[0]["visual_text_language"] == "zh-CN"
    assert "简体中文" in tasks[0]["visible_text_requirements"][0]
    assert "少量清晰大字标签" in tasks[0]["visible_text_requirements"][1]
    assert tasks[0]["props"][0]["name"] == "menu ledger"
    assert tasks[2]["asset_kind"] == "720_seamless_panorama_scene"
    assert tasks[2]["size"] == "21:9"
    assert tasks[2]["resolution"] == "4K"
    assert tasks[3]["asset_kind"] == "video_scene_reference"
    assert tasks[3]["size"] == "16:9"
    assert any("normal perspective environment reference" in item for item in tasks[3]["asset_requirements"])


def test_asset_pack_prompt_contains_specs():
    pack = {
        "characters": [
            {
                "character_id": "lin_que",
                "character_profile": {"identity": {"name": "Lin Que"}},
                "props": [{"name": "red wine glass"}],
            }
        ],
        "scenes": [
            {
                "scene_id": "hotel_exterior",
                "description": "neon hotel in wasteland",
            }
        ],
    }
    tasks = build_ip_asset_pack_tasks(pack, output_dir="out")
    character_prompt = build_task_prompt(tasks[0])
    scene_prompt = build_task_prompt(tasks[1])
    assert "Character props and callouts:" in character_prompt
    assert "no environment scene" in character_prompt
    assert "Visible text language: zh-CN" in character_prompt
    assert "图片内所有可见文字默认使用简体中文" in character_prompt
    assert "不要生成密集小段落" in character_prompt
    assert "720-degree equirectangular panorama" in scene_prompt
    assert "left and right edges must connect seamlessly" in scene_prompt
    assert "GPT Image 2 output spec:" in scene_prompt


def test_asset_pack_can_override_visible_text_language():
    pack = {
        "visual_text_language": "en-US",
        "visible_text_requirements": ["all visible text must be English"],
        "characters": [
            {
                "character_id": "lin_que",
                "character_profile": {"identity": {"name": "Lin Que"}},
            }
        ],
    }
    tasks = build_ip_asset_pack_tasks(pack, output_dir="out")
    prompt = build_task_prompt(tasks[0])
    assert tasks[0]["visual_text_language"] == "en-US"
    assert "Visible text language: en-US" in prompt
    assert "all visible text must be English" in prompt


def test_asset_pack_submits_chunk_before_waiting():
    pack = {
        "characters": [
            {"character_id": "a", "character_profile": {"identity": {"name": "A"}}},
            {"character_id": "b", "character_profile": {"identity": {"name": "B"}}},
            {"character_id": "c", "character_profile": {"identity": {"name": "C"}}},
        ]
    }
    with tempfile.TemporaryDirectory() as output_dir:
        client = _RecordingClient()
        result = _run_ip_asset_pack(pack, output_dir, client)

    assert result["status"] == "success"
    assert len(result["artifacts"]) == 3
    kinds = [kind for kind, _ in client.events]
    # Within the single chunk, every submit must happen before any wait.
    assert kinds == ["submit", "submit", "submit", "wait", "wait", "wait"]


def test_asset_pack_chunks_respect_max_batch():
    pack = {
        "max_batch": 2,
        "characters": [
            {"character_id": "a", "character_profile": {"identity": {"name": "A"}}},
            {"character_id": "b", "character_profile": {"identity": {"name": "B"}}},
            {"character_id": "c", "character_profile": {"identity": {"name": "C"}}},
        ],
    }
    with tempfile.TemporaryDirectory() as output_dir:
        client = _RecordingClient()
        _run_ip_asset_pack(pack, output_dir, client)

    kinds = [kind for kind, _ in client.events]
    # Two chunks of size 2 and 1: submits and waits stay grouped per chunk.
    assert kinds == ["submit", "submit", "wait", "wait", "submit", "wait"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
