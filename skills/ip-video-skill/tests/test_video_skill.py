import json
import os
import sys
import tempfile
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from continuity import build_continuity_bible  # noqa: E402
from config import VideoProviderConfig  # noqa: E402
from poyo_video_client import PoYoVideoClient  # noqa: E402
from video_provider import prepare_video_generation_request  # noqa: E402
from video_handoff import build_video_handoff  # noqa: E402
from video_skill import run_task  # noqa: E402


def _task():
    return {
        "mode": "build_video_handoff",
        "title": "黄泉饭店",
        "blueprint": {
            "title": "黄泉饭店",
            "global_style": {"tone": "暗黑经营、真实短剧、诡异复苏"},
            "segments": [
                {
                    "index": 1,
                    "start_sec": 0,
                    "end_sec": 5,
                    "visual": "林缺站在黄泉饭店柜台后，菜单账本摊开。",
                    "voiceover": "雨夜，黄泉饭店重新开门。",
                    "music_cue": "低频悬疑",
                },
                {
                    "index": 2,
                    "start_sec": 5,
                    "end_sec": 11,
                    "visual": "牛头端着托盘从厨房出来，手里菜刀压低，和林缺隔着柜台对视。",
                    "voiceover": "员工回来了，可客人不是活人。",
                    "music_cue": "紧张脉冲",
                },
            ],
        },
        "ip_asset_pack": {
            "title": "黄泉饭店",
            "style_preset": "realistic_short_drama",
            "characters": [
                {
                    "character_id": "lin_que",
                    "character_profile": {
                        "identity": {"name": "林缺", "role": "黄泉饭店老板", "age_range": "二十多岁"},
                        "appearance": {
                            "face_shape": "清瘦利落",
                            "eyes": "冷静黑眼睛",
                            "hair": "黑色短发",
                            "body_type": "高瘦",
                        },
                        "styling": {
                            "wardrobe": "深色西装，旧金细节",
                            "palette": "黑、深蓝、暗红、旧金",
                            "materials": "哑光羊毛、深色皮革",
                        },
                    },
                    "props": [{"name": "菜单账本", "use": "经营身份道具"}],
                },
                {
                    "character_id": "niu_tou",
                    "character_profile": {
                        "identity": {"name": "牛头", "role": "黄泉饭店员工"},
                        "appearance": {"face_shape": "牛头犄角", "body_type": "高大强壮"},
                        "styling": {"wardrobe": "深色服务员制服和皮革围裙", "materials": "旧皮革、黑布"},
                    },
                    "props": [{"name": "菜刀", "use": "厨房威慑道具"}, {"name": "托盘", "use": "服务身份道具"}],
                },
            ],
            "scenes": [
                {
                    "scene_id": "huangquan_hall_720",
                    "name": "黄泉饭店大厅",
                    "description": "雨夜饭店大厅，柜台、厨房门、红色招牌反光、湿冷地面",
                    "lighting": "夜晚红色招牌弱光",
                }
            ],
        },
        "music_handoff": {"music_tasks": [{"role": "theme", "task_id": "theme_1"}]},
    }


def test_build_continuity_bible_outputs_locks():
    bible = build_continuity_bible(_task())
    assert bible["source_title"] == "黄泉饭店"
    assert "lin_que" in bible["character_locks"]
    assert "niu_tou" in bible["character_locks"]
    assert bible["character_locks"]["lin_que"]["costume_lock"]
    assert bible["character_locks"]["niu_tou"]["prop_locks"][0]["name"] == "菜刀"
    assert "huangquan_hall_720" in bible["scene_locks"]
    assert bible["global_visual_lock"]["style_preset"] == "realistic_short_drama"


def test_build_video_handoff_has_required_shot_fields():
    handoff = build_video_handoff(_task())
    assert len(handoff["shots"]) == 2
    assert len(handoff["clip_plan"]) == 1
    assert handoff["clip_prompts"][0]["clip_id"] == "clip_001"
    assert handoff["clip_plan"][0]["video_reference_images"]
    assert handoff["clip_plan"][0]["space_anchor_refs"]
    for shot in handoff["shots"]:
        assert shot["visual_lock"]
        assert shot["continuity_state"]
        assert shot["reference_binding"]
        assert shot["storyboard_card"]
        assert shot["prompt_profile"]
        assert shot["i2v_prompt"]
        assert shot["t2v_prompt"]
        assert shot["seedance_prompt"]
        assert shot["negative_prompt"]
        assert shot["retry_advice"]
        assert shot["quality_checks"]


def test_multi_character_shot_has_axis_screen_direction_and_eyeline():
    handoff = build_video_handoff(_task())
    shot = handoff["shots"][1]
    assert set(shot["characters"]) == {"lin_que", "niu_tou"}
    assert shot["axis"]["type"] == "character_axis"
    assert "lin_que" in shot["screen_direction"]
    assert "niu_tou" in shot["screen_direction"]
    assert "lin_que" in shot["eyeline"]
    assert "不要越轴" in shot["negative_prompt"]
    assert "空间连续性" in shot["seedance_prompt"]
    assert "表演控制" in shot["seedance_prompt"]
    assert "光线与质感" in shot["seedance_prompt"]


def test_prompts_include_quality_layers_and_retry_advice():
    handoff = build_video_handoff(_task())
    shot = handoff["shots"][1]
    assert "动作流程" in shot["i2v_prompt"]
    assert "真实感锚点" in shot["i2v_prompt"]
    assert "不要塑料皮肤" in shot["negative_prompt"]
    assert any("脸漂移" in item for item in shot["retry_advice"])
    assert handoff["seedance_prompts"][1]["prompt"] == shot["seedance_prompt"]


def test_video_prompts_preserve_ambient_sound_and_forbid_bgm_subtitles():
    handoff = build_video_handoff(_task())
    shot = handoff["shots"][0]
    clip = handoff["clip_plan"][0]
    assert "只保留现场环境声和拟音" in shot["i2v_prompt"]
    assert "禁止背景音乐" in shot["i2v_prompt"]
    assert "禁止生成画面字幕" in shot["i2v_prompt"]
    assert "BGM：" not in shot["i2v_prompt"]
    assert "不要画面字幕" in shot["negative_prompt"]
    assert "不要背景音乐" in shot["negative_prompt"]
    assert "声音只保留现场环境声与拟音" in clip["clip_prompt"]
    assert "画面禁止字幕" in clip["clip_prompt"]


def test_run_task_writes_video_handoff_json():
    with tempfile.TemporaryDirectory() as output_dir:
        task = _task()
        task["output_dir"] = output_dir
        result = run_task(task)
        assert result["status"] == "success"
        out_path = result["artifacts"][0]["path"]
        assert os.path.exists(out_path)
        with open(out_path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
        assert saved["source_title"] == "黄泉饭店"
        assert len(saved["edit_decision_list"]["timeline"]) == 2
        assert len(saved["edit_decision_list"]["clip_timeline"]) == 1


def test_prepare_video_generation_request_offline():
    handoff = build_video_handoff(_task())
    config = VideoProviderConfig(
        provider="offline",
        api_key="",
        api_base="",
        output_root="",
        default_model="offline-preview",
        default_aspect_ratio="9:16",
        default_resolution="480p",
        poll_interval_sec=1,
        poll_timeout_sec=5,
    )
    request = prepare_video_generation_request(
        {
            "mode": "prepare_video_generation",
            "video_handoff": handoff,
            "shot_index": 2,
            "prompt_kind": "seedance",
        },
        config,
    )
    assert request["provider"] == "offline"
    assert request["shot_id"] == "shot_002"
    assert request["mode"] == "image_to_video"
    assert "空间连续性" in request["prompt"]
    assert request["transport"]["type"] == "dry_run"
    assert request["reference_binding"]["scene_lock"]


def test_prepare_video_generation_request_dreamina_cli_shape():
    handoff = build_video_handoff(_task())
    config = VideoProviderConfig(
        provider="dreamina_cli",
        api_key="",
        api_base="",
        output_root="",
        default_model="dreamina-test",
        default_aspect_ratio="9:16",
        default_resolution="480p",
        poll_interval_sec=1,
        poll_timeout_sec=5,
    )
    request = prepare_video_generation_request(
        {
            "video_handoff": handoff,
            "shot_id": "shot_001",
            "reference_images": [{"path": "lin_que.png", "role": "face"}],
            "duration_sec": 5,
            "output_filename": "shot_001.mp4",
        },
        config,
    )
    assert request["provider"] == "dreamina_cli"
    assert request["mode"] == "image_to_video"
    assert request["transport"]["type"] == "cli"
    assert request["transport"]["executable"] == "dreamina"
    assert request["transport"]["subcommand"] == "image2video"
    assert request["transport"]["help_command"] == ["dreamina", "image2video", "-h"]
    assert request["transport"]["intended_parameters"]["duration_sec"] == 5


def test_prepare_video_generation_request_poyo_seedance2_shape():
    handoff = build_video_handoff(_task())
    config = VideoProviderConfig(
        provider="poyo_video",
        api_key="test",
        api_base="https://api.example",
        output_root="",
        default_model="seedance-2",
        default_aspect_ratio="9:16",
        default_resolution="480p",
        poll_interval_sec=1,
        poll_timeout_sec=5,
    )
    request = prepare_video_generation_request(
        {
            "video_handoff": handoff,
            "provider": "poyo_video",
            "model": "seedance-2",
            "image_urls": ["https://files.example/first.png"],
            "duration_sec": 5,
            "generate_audio": False,
            "seed": 42,
        },
        config,
    )
    assert request["transport"]["type"] == "http"
    assert request["transport"]["json"]["model"] == "seedance-2"
    input_obj = request["transport"]["json"]["input"]
    assert input_obj["prompt"]
    assert input_obj["image_urls"] == ["https://files.example/first.png"]
    assert input_obj["resolution"] == "480p"
    assert input_obj["duration"] == 5
    assert input_obj["generate_audio"] is False
    assert input_obj["seed"] == 42
    assert request["transport"]["status_url"].endswith("/api/generate/status/{task_id}")


def test_clip_plan_groups_30_seconds_into_two_clips():
    task = copy.deepcopy(_task())
    task["target_clip_duration_sec"] = 15
    task["blueprint"]["segments"] = [
        {"index": idx + 1, "start_sec": idx * 5, "end_sec": (idx + 1) * 5, "visual": f"林缺在黄泉饭店大厅推进连续动作 {idx + 1}"}
        for idx in range(6)
    ]
    handoff = build_video_handoff(task)
    clips = handoff["clip_plan"]
    assert len(clips) == 2
    assert all(clip["timing"]["duration_sec"] <= 15 for clip in clips)
    assert clips[0]["shot_ids"] == ["shot_001", "shot_002", "shot_003"]
    assert clips[1]["continuity_state"]["current_start_state"] == handoff["shots"][3]["continuity_state"]["current_start_state"]
    assert clips[0]["space_anchor_refs"]
    assert clips[0]["video_reference_images"]


def test_prepare_clip_generation_uses_previous_clip_end_frame_and_keeps_panorama_as_anchor():
    task = copy.deepcopy(_task())
    task["target_clip_duration_sec"] = 5
    task["previous_clip_end_frames"] = {
        "clip_001": {"url": "https://files.example/clip001_last.png", "role": "previous_clip_end_frame"}
    }
    handoff = build_video_handoff(task)
    config = VideoProviderConfig(
        provider="poyo_video",
        api_key="test",
        api_base="https://api.example",
        output_root="",
        default_model="seedance-2",
        default_aspect_ratio="9:16",
        default_resolution="480p",
        poll_interval_sec=1,
        poll_timeout_sec=5,
    )
    request = prepare_video_generation_request(
        {
            "video_handoff": handoff,
            "provider": "poyo_video",
            "clip_index": 2,
            "duration_sec": 5,
        },
        config,
    )
    assert request["unit_kind"] == "clip"
    assert request["clip_id"] == "clip_002"
    assert request["image_urls"][0]["url"] == "https://files.example/clip001_last.png"
    assert request["reference_image_urls"] == []
    assert request["space_anchor_refs"]
    assert request["video_reference_images"]
    input_obj = request["transport"]["json"]["input"]
    assert input_obj["image_urls"] == ["https://files.example/clip001_last.png"]
    assert "reference_image_urls" not in input_obj


class FakeResponse:
    ok = True

    def __init__(self, payload=None, chunks=None):
        self.payload = payload or {}
        self.chunks = chunks or []

    def json(self):
        return self.payload

    def iter_content(self, chunk_size=65536):
        yield from self.chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeVideoSession:
    def __init__(self):
        self.headers = {}
        self.posts = []
        self.gets = []

    def post(self, url, json=None, files=None, data=None, timeout=None):
        self.posts.append({"url": url, "json": json, "files": files, "data": data, "timeout": timeout})
        return FakeResponse({"code": 200, "data": {"task_id": "task_video_123", "status": "not_started"}})

    def get(self, url, stream=False, timeout=None):
        self.gets.append({"url": url, "stream": stream, "timeout": timeout})
        if "status" in url:
            return FakeResponse(
                {
                    "code": 200,
                    "data": {
                        "task_id": "task_video_123",
                        "status": "finished",
                        "credits_amount": 20,
                        "files": [
                            {
                                "file_url": "https://storage.example/video.mp4",
                                "file_type": "video",
                                "format": "mp4",
                            }
                        ],
                        "created_time": "2026-04-04T10:30:00",
                        "progress": 100,
                        "error_message": None,
                    },
                }
            )
        return FakeResponse(chunks=[b"mp4data"])


def test_poyo_video_client_submit_poll_download():
    with tempfile.TemporaryDirectory() as output_dir:
        config = VideoProviderConfig(
            provider="poyo_video",
            api_key="test",
            api_base="https://api.example",
            output_root=output_dir,
            default_model="seedance-2",
            default_aspect_ratio="9:16",
            default_resolution="1080p",
            poll_interval_sec=1,
            poll_timeout_sec=5,
        )
        client = PoYoVideoClient(config)
        client.session = FakeVideoSession()
        result = client.run_seedance2(
            {
                "model": "seedance-2",
                "prompt": "测试视频提示词",
                "resolution": "1080p",
                "duration_sec": 5,
                "aspect_ratio": "9:16",
                "image_urls": [{"url": "https://files.example/first.png"}],
                "output_filename": "shot_001.mp4",
            },
            output_dir=output_dir,
        )
        assert result["task_id"] == "task_video_123"
        assert result["credits_amount"] == 20
        assert result["local_paths"][0].endswith("shot_001_01.mp4")
        assert os.path.exists(result["local_paths"][0])
        submit = client.session.posts[0]["json"]
        assert submit["model"] == "seedance-2"
        assert submit["input"]["image_urls"] == ["https://files.example/first.png"]


def test_run_task_prepare_video_generation_writes_json():
    with tempfile.TemporaryDirectory() as output_dir:
        handoff = build_video_handoff(_task())
        result = run_task(
            {
                "mode": "prepare_video_generation",
                "video_handoff": handoff,
                "shot_index": 1,
                "output_dir": output_dir,
            }
        )
        assert result["status"] == "success"
        out_path = result["artifacts"][0]["path"]
        assert os.path.exists(out_path)
        with open(out_path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
        assert saved["provider"] == "offline"
        assert saved["shot_id"] == "shot_001"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
