import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from continuity import build_continuity_bible  # noqa: E402
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
    for shot in handoff["shots"]:
        assert shot["visual_lock"]
        assert shot["continuity_state"]
        assert shot["reference_binding"]
        assert shot["storyboard_card"]
        assert shot["i2v_prompt"]
        assert shot["negative_prompt"]
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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
