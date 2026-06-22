import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from music_skill import (  # noqa: E402
    _build_music_input,
    _run_live_music_task,
    build_music_handoff,
    run_task,
)


class FakeClient:
    def __init__(self):
        self.uploads = []
        self.calls = []

    def upload(self, path):
        self.uploads.append(path)
        return f"https://files.example/{os.path.basename(path)}"

    def run_music(self, model, input_obj, out_path=None):
        self.calls.append((model, input_obj, out_path))
        result = {
            "task_id": "task_123",
            "audios": [
                {
                    "audio_id": "audio_123",
                    "audio_url": "https://files.example/generated.mp3",
                    "title": "Generated",
                    "duration": 30,
                }
            ],
            "stems": {},
            "credits_amount": 10,
        }
        if out_path:
            result["local_path"] = out_path
        return result


def _polished_script():
    return {
        "script_id": "script_001",
        "title": "黄泉饭店",
        "tone": "悬疑诡异、地府奇幻",
        "target": "short_drama",
        "source_text": "林缺在雨夜回到黄泉饭店，牛头员工端着托盘出现。",
        "scenes": [
            {
                "scene_no": 1,
                "visual": "饭店大厅突然变暗。",
                "music_cue": "低频鼓点、阴冷弦乐、地府仪式感",
            },
            {
                "scene_no": 2,
                "visual": "牛头员工挡住退路。",
                "music_cue": "紧张脉冲、金属敲击、呼吸停顿",
            },
        ],
    }


def test_build_music_handoff_from_polished_script():
    handoff = build_music_handoff({"polished_script": _polished_script()})
    assert handoff["source_title"] == "黄泉饭店"
    assert handoff["creative_direction"]["tone"] == "悬疑诡异、地府奇幻"
    assert len(handoff["music_tasks"]) == 3
    assert handoff["music_tasks"][0]["role"] == "theme"
    assert handoff["music_tasks"][0]["instrumental"] is False
    assert "黄泉饭店" in handoff["music_tasks"][0]["prompt"]
    assert handoff["music_tasks"][1]["role"] == "scene_bgm"
    assert handoff["music_tasks"][1]["instrumental"] is True
    assert "dark cinematic" in handoff["music_tasks"][1]["style"]


def test_build_music_handoff_from_blueprint_segments():
    blueprint = {
        "blueprint_id": "bp_001",
        "title": "雨夜便利店",
        "global_style": {"tone": "治愈、恋爱、雨夜"},
        "segments": [
            {"index": 1, "music_cue": "雨声、柔和钢琴、城市夜色"},
            {"index": 2, "music_cue": "温暖弦乐、轻微心动感"},
        ],
    }
    handoff = build_music_handoff({"blueprint": blueprint, "theme_instrumental": True})
    assert handoff["source_title"] == "雨夜便利店"
    assert handoff["music_tasks"][0]["instrumental"] is True
    assert len(handoff["music_tasks"]) == 3
    assert handoff["music_tasks"][1]["scene_ref"] == 1
    assert "warm pop" in handoff["music_tasks"][1]["style"]


def test_run_task_writes_music_handoff_json():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "build_music_handoff",
                "polished_script": _polished_script(),
                "output_dir": output_dir,
            }
        )
        assert result["status"] == "success"
        out_path = result["artifacts"][0]["path"]
        assert os.path.exists(out_path)
        with open(out_path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
        assert saved["source_title"] == "黄泉饭店"
        assert len(saved["music_tasks"]) == 3


def test_build_music_input_generate_and_audio_upload_modes():
    client = FakeClient()
    generate = _build_music_input(
        {
            "mode": "generate_music",
            "prompt": "主题歌",
            "style": "cinematic",
            "title": "Theme",
            "instrumental": True,
        },
        "V5",
        client,
    )
    assert generate["custom_mode"] is True
    assert generate["mv"] == "V5"
    assert generate["instrumental"] is True

    cover = _build_music_input(
        {
            "mode": "cover_audio",
            "audio_path": "demo.mp3",
            "prompt": "保持旋律，改成悬疑短剧配乐",
            "style": "dark cinematic",
            "audio_weight": 0.8,
        },
        "V5",
        client,
    )
    assert cover["upload_url"].endswith("/demo.mp3")
    assert cover["audio_weight"] == 0.8

    upload_split = _build_music_input(
        {"mode": "upload_separate_vocals", "audio_path": "external.wav"},
        "V5",
        client,
    )
    assert upload_split == {"upload_url": "https://files.example/external.wav", "mv": "V5"}


def test_build_music_input_generated_track_modes():
    client = FakeClient()
    extend = _build_music_input(
        {
            "mode": "extend_music",
            "audio_id": "audio_1",
            "continue_at": 45,
            "prompt": "加一段副歌",
            "style": "pop",
        },
        "V5",
        client,
    )
    assert extend["audio_id"] == "audio_1"
    assert extend["continue_at"] == 45
    assert extend["default_param_flag"] is True

    replace = _build_music_input(
        {
            "mode": "replace_section",
            "source_task_id": "task_1",
            "audio_id": "audio_1",
            "prompt": "新副歌歌词",
            "tags": "pop, hook",
            "start": 10,
            "end": 20,
        },
        "V5",
        client,
    )
    assert replace["task_id"] == "task_1"
    assert replace["infill_start_s"] == 10
    assert replace["infill_end_s"] == 20

    stems = _build_music_input(
        {"mode": "stem_split", "source_task_id": "task_1", "audio_id": "audio_1"},
        "V5",
        client,
    )
    assert stems == {"task_id": "task_1", "audio_id": "audio_1"}


def test_run_live_music_task_uses_model_map_and_artifact():
    with tempfile.TemporaryDirectory() as output_dir:
        client = FakeClient()
        result = _run_live_music_task(
            {
                "mode": "generate_music",
                "prompt": "主题音乐",
                "output_filename": "theme.mp3",
            },
            output_dir,
            "V5",
            client,
        )
        assert result["status"] == "success"
        assert client.calls[0][0] == "generate-music"
        assert client.calls[0][2].endswith("theme.mp3")
        assert result["artifacts"][0]["type"] == "audio"
        assert result["handoff"]["audios"][0]["audio_id"] == "audio_123"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
