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
from config import MusicProviderConfig  # noqa: E402
from poyo_music_client import PoYoMusicClient  # noqa: E402


class FakeClient:
    def __init__(self):
        self.uploads = []
        self.calls = []

    def upload_file(self, path, **kwargs):
        self.uploads.append((path, kwargs))
        return f"https://files.example/{os.path.basename(path)}"

    def upload(self, path):
        return self.upload_file(path)

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
    assert client.uploads[-1][1] == {"proxy_dir": None, "keep_proxy": True}


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

    upload_extend = _build_music_input(
        {
            "mode": "upload_extend_audio",
            "audio_url": "https://files.example/input.mp4",
            "continue_at": 30,
            "instrumental": True,
            "style": "cinematic",
            "title": "Extended",
            "audio_weight": 0.7,
        },
        "V5",
        client,
    )
    assert upload_extend["upload_url"].endswith("/input.mp4")
    assert upload_extend["default_param_flag"] is True
    assert upload_extend["continue_at"] == 30
    assert upload_extend["audio_weight"] == 0.7


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


class FakeUploadResponse:
    ok = True

    def json(self):
        return {"data": {"file_url": "https://storage.example/proxy.mp4"}}


class FakeUploadSession:
    def __init__(self):
        self.headers = {}
        self.posts = []

    def post(self, url, files=None, data=None, timeout=None):
        file_name, fh, mime_type = files["file"]
        self.posts.append(
            {
                "url": url,
                "file_name": file_name,
                "mime_type": mime_type,
                "data": dict(data),
                "bytes": fh.read(4),
                "timeout": timeout,
            }
        )
        return FakeUploadResponse()


def test_audio_path_upload_wraps_to_mp4_proxy():
    with tempfile.TemporaryDirectory() as tmp:
        audio_path = os.path.join(tmp, "demo.wav")
        proxy_path = os.path.join(tmp, "demo_upload_proxy.mp4")
        with open(audio_path, "wb") as fh:
            fh.write(b"RIFF")

        config = MusicProviderConfig(
            provider="poyo",
            api_key="test",
            api_base="https://api.example",
            output_root=tmp,
            default_model_version="V5",
            poll_interval_sec=1,
            poll_timeout_sec=1,
        )
        client = PoYoMusicClient(config)
        client.session = FakeUploadSession()

        def fake_wrap(path, proxy_dir=None):
            assert path == audio_path
            assert proxy_dir == tmp
            with open(proxy_path, "wb") as fh:
                fh.write(b"mp4!")
            return proxy_path, None

        client._wrap_audio_as_mp4 = fake_wrap
        url = client.upload_file(audio_path, proxy_dir=tmp)
        assert url == "https://storage.example/proxy.mp4"
        post = client.session.posts[0]
        assert post["file_name"] == "demo_upload_proxy.mp4"
        assert post["mime_type"] == "video/mp4"
        assert post["data"]["upload_path"] == "music-audio-proxy"
        assert post["bytes"] == b"mp4!"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
