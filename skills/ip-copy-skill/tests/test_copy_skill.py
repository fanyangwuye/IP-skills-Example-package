import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from blueprint_validate import validate_blueprint  # noqa: E402
from copy_skill import run_task  # noqa: E402
from license_gate import check_license, gate  # noqa: E402


LICENSE = {
    "license_id": "L1",
    "ip_id": "demo_ip",
    "source_title": "Demo",
    "rights_holder": "Studio",
    "allowed_targets": ["short_drama_script", "webnovel"],
    "commercial": True,
    "valid_until": "2030-01-01",
}


def test_license_pass():
    ok, reasons = check_license(LICENSE, "short_drama", commercial_use=True, today=date(2026, 1, 1))
    assert ok and reasons == [], reasons


def test_license_no_record():
    ok, reasons = check_license(None, "short_drama", False)
    assert not ok and reasons


def test_license_target_out_of_scope():
    ok, reasons = check_license(LICENSE, "real_actor", False, today=date(2026, 1, 1))
    assert not ok and reasons


def test_license_commercial_denied():
    blocked = dict(LICENSE, commercial=False)
    ok, reasons = check_license(blocked, "short_drama", commercial_use=True, today=date(2026, 1, 1))
    assert not ok and reasons


def test_license_expired():
    ok, reasons = check_license(LICENSE, "short_drama", False, today=date(2031, 1, 1))
    assert not ok and reasons


def test_gate_raises():
    try:
        gate(None, "short_drama", False)
    except PermissionError:
        pass
    else:
        raise AssertionError("gate 未放行时应抛 PermissionError")


def _good_blueprint():
    return {
        "blueprint_id": "B1",
        "ip_id": "demo_ip",
        "target": "short_drama",
        "total_duration_sec": 30,
        "segments": [
            {"index": 1, "start_sec": 0, "end_sec": 10, "visual": "v1", "voiceover": "o1"},
            {"index": 2, "start_sec": 10, "end_sec": 20, "visual": "v2", "voiceover": "o2"},
            {"index": 3, "start_sec": 20, "end_sec": 30, "visual": "v3", "voiceover": "o3"},
        ],
    }


def test_bp_good():
    ok, errors = validate_blueprint(_good_blueprint())
    assert ok, errors


def test_bp_gap():
    blueprint = _good_blueprint()
    blueprint["segments"][1]["start_sec"] = 12
    ok, errors = validate_blueprint(blueprint)
    assert not ok and errors


def test_bp_total_mismatch():
    blueprint = _good_blueprint()
    blueprint["total_duration_sec"] = 45
    ok, errors = validate_blueprint(blueprint)
    assert not ok and errors


def test_bp_missing_visual():
    blueprint = _good_blueprint()
    blueprint["segments"][0].pop("visual")
    ok, errors = validate_blueprint(blueprint)
    assert not ok and errors


def test_bp_bad_index():
    blueprint = _good_blueprint()
    blueprint["segments"][2]["index"] = 5
    ok, errors = validate_blueprint(blueprint)
    assert not ok and errors


def test_build_blueprint_handoff(tmp_path=None):
    with tempfile.TemporaryDirectory() as output_dir:
        task = {
            "mode": "build_blueprint",
            "ip_id": "demo_ip",
            "target": "short_drama",
            "commercial_use": True,
            "title": "Rainy Convenience Store",
            "total_duration_sec": 30,
            "scene_cards": [
                {
                    "visual": "Rainy street outside a convenience store, heroine seen from behind under neon.",
                    "voiceover": "That night, the rain felt like it could hide the whole city.",
                    "asset_goal": {"type": "hero portrait", "purpose": "opening key frame"},
                },
                {
                    "visual": "Inside the store, cold and warm light split two figures across the shelf.",
                    "voiceover": "I did not expect to meet him there.",
                    "asset_goal": {"type": "two-character scene", "purpose": "tension beat"},
                },
                {
                    "visual": "They walk out together as the rain thins and the sky starts to lift.",
                    "voiceover": "Some meetings are already an answer by themselves.",
                    "asset_goal": {"type": "ending scene", "purpose": "release beat"},
                },
            ],
            "character_sheet": {
                "character_profile": {
                    "identity": {"name": "Lin Yue"},
                },
                "identity_anchors": ["same face"],
                "continuity_rules": ["keep identity stable"],
                "interaction_state": {"locked_traits": ["face"]},
            },
            "license_path": os.path.join(os.path.dirname(__file__), "..", "references", "licenses", "demo_ip.json"),
            "output_dir": output_dir,
        }
        result = run_task(task)
        assert result["status"] == "success"
        blueprint = result["handoff"]["blueprint"]
        ok, errors = validate_blueprint(blueprint)
        assert ok, errors
        assert len(result["handoff"]["image_handoff"]["image_tasks"]) == 3


def test_build_ip_asset_pack_from_source_text():
    with tempfile.TemporaryDirectory() as output_dir:
        task = {
            "mode": "build_ip_asset_pack",
            "ip_id": "huangquan_demo",
            "title": "黄泉饭店",
            "source_text": (
                "林缺在雨夜回到黄泉饭店，老板的菜单账本放在柜台上。"
                "牛头员工端着托盘从厨房出来，手里还拿着菜刀。"
                "苏澜背着生存背包来到酒店门口，用探测器确认大厅里的异常能量。"
            ),
            "output_dir": output_dir,
        }
        result = run_task(task)
        assert result["status"] == "success"
        pack = result["handoff"]["ip_asset_pack"]
        assert pack["mode"] == "ip_asset_pack"
        assert pack["visual_text_language"] == "zh-CN"
        names = [item["character_profile"]["identity"]["name"] for item in pack["characters"]]
        assert len(names) >= 3
        assert "林缺" in names
        assert "牛头" in names
        assert "苏澜" in names
        assert len(pack["scenes"]) >= 2
        assert any(scene["size"] == "21:9" and scene["resolution"] == "4K" for scene in pack["scenes"])
        assert os.path.exists(os.path.join(output_dir, "ip_asset_pack.json"))


def test_build_ip_asset_pack_from_screenplay_format():
    source_text = """第一集
场1-1 夜/内 巡捕房值班房、窄巷子
出场人物：陈渊、赵德柱
△夜雨淅沥，巡捕房值班房内，两人身影摇曳。
陈渊（内心OS）：
我这是穿越了？
赵德柱VO：醒了？
△陈渊迅速捂住脑袋，指尖用力按着太阳穴。
场1-2 夜/外 乌水镇南市窄巷
出场人物：陈渊、赵德柱、虎妖、系统
△巷弄幽深，血腥味刺鼻。
虎妖（狞笑）：这肉，挺嫩啊！
"""
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "build_ip_asset_pack",
                "ip_id": "screenplay_demo",
                "title": "剧本格式测试",
                "source_text": source_text,
                "output_dir": output_dir,
            }
        )
        pack = result["handoff"]["ip_asset_pack"]
        names = [item["character_profile"]["identity"]["name"] for item in pack["characters"]]
        assert names[:4] == ["陈渊", "赵德柱", "虎妖", "系统"]
        assert "出场人物" not in names
        assert "指尖" not in names
        scene_names = [scene["name"] for scene in pack["scenes"]]
        assert len(scene_names) == 2
        assert "场1-1 夜/内 巡捕房值班房、窄巷子" in scene_names
        assert "场1-2 夜/外 乌水镇南市窄巷" in scene_names


def test_build_ip_asset_pack_keeps_explicit_multi_characters():
    with tempfile.TemporaryDirectory() as output_dir:
        task = {
            "mode": "build_ip_asset_pack",
            "ip_id": "ensemble_demo",
            "title": "群像测试",
            "source_text": "三人小队进入废墟基地。",
            "characters": [
                {"name": "队长", "role": "小队负责人", "props": [{"name": "地图", "use": "行动规划"}]},
                {"name": "工程师", "role": "设备维护者", "props": [{"name": "工具箱", "use": "维修设备"}]},
                {"name": "向导", "role": "路线引导者"},
            ],
            "scenes": [
                {"name": "废墟基地入口", "description": "三人小队进入废墟基地入口"}
            ],
            "output_dir": output_dir,
        }
        result = run_task(task)
        pack = result["handoff"]["ip_asset_pack"]
        names = [item["character_profile"]["identity"]["name"] for item in pack["characters"]]
        assert names == ["队长", "工程师", "向导"]
        assert pack["characters"][0]["props"][0]["name"] == "地图"
        assert pack["scenes"][0]["name"] == "废墟基地入口"


def test_update_adaptation_state_from_conversation():
    with tempfile.TemporaryDirectory() as output_dir:
        task = {
            "mode": "update_adaptation_state",
            "title": "黄泉饭店",
            "source_text": "林缺在雨夜回到黄泉饭店，牛头员工端着托盘出现，苏澜用探测器发现大厅异常。",
            "conversation_turns": [
                {
                    "role": "user",
                    "content": "改成竖屏短剧，开头要强钩子，风格悬疑诡异，不要太血腥，中文对白。",
                }
            ],
            "output_dir": output_dir,
        }
        result = run_task(task)
        assert result["status"] == "success"
        state = result["handoff"]["adaptation_state"]
        assert state["creative_direction"]["target"] == "short_drama"
        assert "悬疑诡异" in state["creative_direction"]["tone"]
        assert any("避免血腥" in item for item in state["constraints"])
        names = [item["name"] for item in state["characters"]]
        assert "林缺" in names
        assert "苏澜" in names
        roles = {item["name"]: item["role"] for item in state["characters"]}
        assert roles["苏澜"] == "调查者 / 异常能量探测者"
        assert roles["林缺"] != "服务人员 / 员工"
        assert state["story_beats"]
        assert os.path.exists(os.path.join(output_dir, "adaptation_state.json"))


def test_build_adaptation_scene_cards_from_state():
    with tempfile.TemporaryDirectory() as output_dir:
        state = {
            "title": "黄泉饭店",
            "source_text": "林缺回到黄泉饭店。牛头出现。苏澜发现异常。",
            "creative_direction": {
                "target": "short_drama",
                "tone": "悬疑诡异、强钩子",
                "viewpoint": "男主视角",
            },
            "characters": [
                {"name": "林缺", "role": "老板"},
                {"name": "牛头", "role": "员工"},
                {"name": "苏澜", "role": "调查者"},
            ],
            "scenes": [
                {"name": "黄泉饭店大厅", "description": "黑暗饭店大厅，红色幽光和服务台"},
            ],
            "story_beats": [
                "开场前三秒，饭店大厅突然变成阎王殿",
                "牛头端着托盘挡住去路",
                "苏澜的探测器显示能量暴涨",
                "林缺发现菜单账本能改变规则",
            ],
        }
        task = {
            "mode": "build_adaptation_scene_cards",
            "adaptation_state": state,
            "n_scene_cards": 4,
            "total_duration_sec": 40,
            "output_dir": output_dir,
        }
        result = run_task(task)
        assert result["status"] == "success"
        cards = result["handoff"]["scene_cards"]
        assert len(cards) == 4
        assert cards[0]["duration_sec"] == 10
        assert "林缺" in cards[0]["visual"]
        assert cards[0]["voiceover"]
        assert cards[0]["asset_goal"]["type"] == "adapted scene key frame"
        assert os.path.exists(os.path.join(output_dir, "adaptation_scene_cards.json"))


def test_build_script_draft_from_scene_cards():
    with tempfile.TemporaryDirectory() as output_dir:
        scene_cards = [
            {
                "visual": "黄泉饭店大厅突然变成阎王殿，林缺站在服务台后。",
                "voiceover": "开场前三秒，饭店大厅突然变成阎王殿",
                "subtitle": "饭店大厅突然变成阎王殿",
                "music_cue": "低频悬念起势",
                "duration_sec": 8,
                "asset_goal": {"scene": "黄泉饭店大厅", "type": "adapted scene key frame"},
            },
            {
                "visual": "牛头端着托盘挡住苏澜的退路。",
                "voiceover": "牛头端着托盘挡住苏澜的退路",
                "duration_sec": 8,
                "asset_goal": {"scene": "黄泉饭店大厅", "type": "adapted scene key frame"},
            },
        ]
        task = {
            "mode": "build_script_draft",
            "title": "黄泉饭店",
            "scene_cards": scene_cards,
            "characters": [{"name": "林缺"}, {"name": "牛头"}, {"name": "苏澜"}],
            "total_duration_sec": 16,
            "output_dir": output_dir,
        }
        result = run_task(task)
        script = result["handoff"]["script_draft"]
        assert script["title"] == "黄泉饭店"
        assert len(script["scenes"]) == 2
        assert script["scenes"][0]["dialogue"]
        assert script["scenes"][0]["start_sec"] == 0
        assert script["scenes"][-1]["end_sec"] == 16
        assert script["handoff"]["can_build_blueprint"] is True
        assert os.path.exists(os.path.join(output_dir, "script_draft.json"))


def test_build_script_draft_from_adaptation_state():
    with tempfile.TemporaryDirectory() as output_dir:
        task = {
            "mode": "build_script_draft",
            "title": "黄泉饭店",
            "source_text": "林缺回到黄泉饭店。牛头出现。苏澜发现异常。",
            "conversation_turns": [
                {"role": "user", "content": "做成竖屏短剧，悬疑诡异，中文对白。"}
            ],
            "n_scene_cards": 3,
            "total_duration_sec": 30,
            "output_dir": output_dir,
        }
        result = run_task(task)
        script = result["handoff"]["script_draft"]
        assert len(script["scenes"]) == 3
        assert script["target"] == "short_drama"
        assert script["scenes"][0]["voiceover"]
        assert script["handoff"]["scene_cards"]


def test_build_script_draft_from_screenplay_uses_scene_cast_only():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "build_script_draft",
                "title": "剧本场次测试",
                "source_text": (
                    "第一集\n"
                    "场1-1 夜/内 巡捕房值班房、窄巷子\n"
                    "出场人物：陈渊、赵德柱\n"
                    "△陈渊在简陋木床上猛然睁眼。\n"
                    "赵德柱VO：醒了？\n"
                    "场1-2 夜/外 乌水镇南市窄巷\n"
                    "出场人物：陈渊、赵德柱、虎妖、系统\n"
                    "△阴影中，一头九尺高的灰毛虎妖凌空扑下！\n"
                ),
                "total_duration_sec": 12,
                "output_dir": output_dir,
            }
        )
        cards = result["handoff"]["script_draft"]["handoff"]["scene_cards"]
        assert len(cards) == 2
        assert "陈渊、赵德柱围绕该剧情点行动" in cards[0]["visual"]
        assert "虎妖围绕该剧情点行动" not in cards[0]["visual"]
        assert "陈渊、赵德柱、虎妖、系统围绕该剧情点行动" in cards[1]["visual"]


def test_polish_script_draft_preserves_structure_and_strengthens_dialogue():
    with tempfile.TemporaryDirectory() as output_dir:
        script_draft = {
            "title": "黄泉饭店",
            "tone": "悬疑诡异、强钩子",
            "total_duration_sec": 16,
            "constraints": ["输出中文对白"],
            "characters": [{"name": "林缺"}, {"name": "牛头"}],
            "scenes": [
                {
                    "scene_no": 1,
                    "start_sec": 0,
                    "end_sec": 8,
                    "visual": "黄泉饭店大厅突然变暗。",
                    "voiceover": "饭店大厅突然变暗",
                    "dialogue": [{"speaker": "林缺", "line": "这里不对劲。"}],
                    "asset_goal": {"type": "adapted scene key frame"},
                },
                {
                    "scene_no": 2,
                    "start_sec": 8,
                    "end_sec": 16,
                    "visual": "红色幽光照亮服务台。",
                    "voiceover": "红色幽光里，真正的客人还没有现身",
                    "dialogue": [{"speaker": "林缺", "line": "可真正的答案还没有出现，红色幽光里，真正的客人还没有现身"}],
                    "asset_goal": {"type": "adapted scene key frame"},
                },
            ],
        }
        result = run_task(
            {
                "mode": "polish_script_draft",
                "script_draft": script_draft,
                "polish_intensity": "medium",
                "output_dir": output_dir,
            }
        )
        polished = result["handoff"]["polished_script"]
        assert len(polished["scenes"]) == 2
        assert polished["scenes"][0]["original_dialogue"][0]["line"] == "这里不对劲。"
        assert polished["scenes"][0]["dialogue"][0]["line"] != "这里不对劲。"
        assert "conflict_notes" in polished["scenes"][0]
        assert polished["scenes"][-1]["beat_function"] == "cliffhanger"
        assert polished["handoff"]["polished_for_script"] is True
        assert os.path.exists(os.path.join(output_dir, "polished_script.json"))


def test_polish_script_draft_can_build_from_state():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "polish_script_draft",
                "title": "黄泉饭店",
                "source_text": "林缺回到黄泉饭店。牛头出现。苏澜发现异常。",
                "conversation_turns": [{"role": "user", "content": "竖屏短剧，悬疑诡异，中文对白。"}],
                "n_scene_cards": 3,
                "total_duration_sec": 30,
                "output_dir": output_dir,
            }
        )
        polished = result["handoff"]["polished_script"]
        assert len(polished["scenes"]) == 3
        assert polished["polish"]["rules"]
        assert polished["scenes"][0]["dialogue"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
