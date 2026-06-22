import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from asset_pack import build_ip_asset_pack_tasks  # noqa: E402
from prompt_builder import build_task_prompt  # noqa: E402


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
    assert len(tasks) == 3
    assert tasks[0]["mode"] == "character_create"
    assert tasks[0]["filename"] == "lin_que_design_sheet.jpg"
    assert "plain neutral background" in tasks[0]["asset_requirements"]
    assert tasks[0]["visual_text_language"] == "zh-CN"
    assert "简体中文" in tasks[0]["visible_text_requirements"][0]
    assert "少量清晰大字标签" in tasks[0]["visible_text_requirements"][1]
    assert tasks[0]["props"][0]["name"] == "menu ledger"
    assert tasks[2]["asset_kind"] == "720_seamless_panorama_scene"
    assert tasks[2]["size"] == "21:9"
    assert tasks[2]["resolution"] == "4K"


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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
