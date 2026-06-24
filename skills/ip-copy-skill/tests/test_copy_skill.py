import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from blueprint_validate import validate_blueprint  # noqa: E402
from copy_skill import run_task  # noqa: E402
from creative_engine import CreativeEngineRequest, EngineBlockedError, LiveLLMEngine, MockCreativeEngine, OfflineCreativeEngine, build_prompt_pack, build_provider_request  # noqa: E402
from format_adapters import OverseasShortDramaAdapter, VerticalShortDramaAdapter  # noqa: E402
from license_gate import check_license, gate  # noqa: E402
from quality_evaluator import evaluate_scene_cards_quality, evaluate_script_quality  # noqa: E402


LICENSE = {
    "license_id": "L1",
    "ip_id": "demo_ip",
    "source_title": "Demo",
    "rights_holder": "Studio",
    "allowed_targets": ["short_drama_script", "webnovel"],
    "commercial": True,
    "valid_until": "2030-01-01",
}
def test_vertical_short_drama_adapter_spec_locks_structure_and_handoff_rules():
    adapter = VerticalShortDramaAdapter()
    spec = adapter.spec()
    assert spec.format_name == "vertical_short_drama"
    assert spec.structure_levels == ["project", "episode", "scene", "beat", "shot"]
    assert spec.default_aspect_ratio == "9:16"
    assert spec.default_episode_duration_sec == 90
    assert "visual" in spec.required_scene_card_fields
    assert "first_3_seconds_state_conflict_or_reversal" in spec.rhythm_rules
    assert "video_storyboard_ready_action_beats" in spec.quality_checks
    assert "default_aspect_ratio=9:16" in spec.handoff_requirements["image"]


def test_vertical_short_drama_adapter_validates_scene_cards():
    adapter = VerticalShortDramaAdapter()
    good = [
        {
            "visual": "黄泉饭店大厅，林缺翻开菜单账本。",
            "voiceover": "开场三秒，规则已经变了。",
            "duration_sec": 8,
            "asset_goal": {"type": "adapted scene key frame"},
        }
    ]
    assert adapter.validate_scene_cards(good) == []

    bad = [{"visual": "只有画面"}]
    errors = adapter.validate_scene_cards(bad)
    assert any("voiceover" in error for error in errors)
    assert any("duration_sec" in error for error in errors)
    assert any("asset_goal" in error for error in errors)




def test_overseas_short_drama_adapter_spec_locks_localization_rules():
    adapter = OverseasShortDramaAdapter()
    spec = adapter.spec()
    assert spec.format_name == "overseas_short_drama"
    assert spec.structure_levels == ["project", "season", "episode", "scene", "beat"]
    assert spec.default_aspect_ratio == "9:16"
    assert spec.default_episode_duration_sec == 360
    assert "dialogue_translation_ready" in spec.quality_checks
    assert "culture_safe_surface_wording" in spec.handoff_requirements["copy"]
    assert "every_20_to_30_seconds_add_new_emotional_pressure_or_plot_information" in spec.rhythm_rules


def test_overseas_short_drama_prompt_pack_uses_adapter_constraints():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "build_creative_prompt_pack",
                "target_format": "overseas_short_drama",
                "prompt_kind": "script_scenes",
                "title": "黄泉饭店",
                "source_text": "林缺回到黄泉饭店。苏澜发现大厅异常。",
                "creative_brief": {"target": "overseas_short_drama", "tone": "suspense romance"},
                "output_dir": output_dir,
            }
        )
        prompt_pack = result["handoff"]["prompt_pack"]
        assert prompt_pack["format_name"] == "overseas_short_drama"
        assert "dialogue_translation_ready" in prompt_pack["user_prompt"]
        assert "culture_safe_surface_wording" in prompt_pack["user_prompt"]
        assert result["handoff"]["provider_request"]["network_call_allowed"] is False
def test_vertical_short_drama_adapter_builds_creative_engine_payload():
    adapter = VerticalShortDramaAdapter()
    payload = adapter.creative_engine_payload(
        {"title": "黄泉饭店", "characters": [{"name": "林缺"}]},
        {"n_scene_cards": 4},
    )
    assert payload["format_name"] == "vertical_short_drama"
    assert payload["default_aspect_ratio"] == "9:16"
    assert payload["state"]["title"] == "黄泉饭店"
    assert payload["task"]["n_scene_cards"] == 4
    assert "every_10_to_15_seconds_add_new_pressure_or_information" in payload["rhythm_rules"]
def test_quality_evaluator_reports_scaffold_warnings_and_blockers():
    scene_report = evaluate_scene_cards_quality(
        [
            {
                "visual": "核心场景。主要角色围绕该剧情点行动：推进第1个剧情转折。",
                "voiceover": "开场危机。",
                "duration_sec": 8,
                "asset_goal": {"type": "adapted scene key frame"},
                "generation_source": "fallback_scaffold",
            }
        ],
        VerticalShortDramaAdapter().spec(),
    )
    assert scene_report["status"] == "pass"
    assert scene_report["warnings"]

    script_report = evaluate_script_quality({"scenes": []}, VerticalShortDramaAdapter().spec())
    assert script_report["status"] == "fail"
    assert any(item["code"] == "script_scenes_empty" for item in script_report["issues"])



def test_quality_evaluator_reports_creative_quality_warnings():
    adapter_spec = VerticalShortDramaAdapter().spec()
    scene_report = evaluate_scene_cards_quality(
        [
            {
                "visual": "黄泉饭店大厅，林缺突然看见一枚炸弹和陌生怪兽。",
                "voiceover": "异常出现。",
                "duration_sec": 8,
                "asset_goal": {"type": "adapted scene key frame"},
            }
        ],
        adapter_spec,
        context={
            "source_text": "林缺回到黄泉饭店，牛头员工端着托盘出现。",
            "characters": [{"name": "林缺"}, {"name": "牛头"}],
        },
    )
    assert scene_report["quality_report_version"] == "1.1"
    assert "creative_checks" in scene_report
    assert "炸弹" in scene_report["creative_checks"]["unsupported_details"]
    assert any("unsupported" in item or "not found" in item for item in scene_report["warnings"])

    script_report = evaluate_script_quality(
        {
            "source_text": "林缺回到黄泉饭店，牛头员工端着托盘出现。",
            "characters": [{"name": "林缺"}, {"name": "牛头"}],
            "scenes": [
                {
                    "visual": "林缺站在柜台后。",
                    "voiceover": "他回到饭店。",
                    "dialogue": [{"speaker": "陌生人", "line": "这里不对劲。"}],
                    "start_sec": 0,
                    "end_sec": 8,
                }
            ],
            "handoff": {"can_build_blueprint": True},
        },
        adapter_spec,
    )
    checks = script_report["creative_checks"]
    assert checks["dialogue_voice"]["generic_line_count"] == 1
    assert any("speaker not in locked" in item for item in script_report["warnings"])
    assert checks["hook_density"]["total"] == 1
def test_offline_creative_engine_requires_fallback_without_live_call():
    engine = OfflineCreativeEngine()
    result = engine.generate(
        CreativeEngineRequest(
            kind="scene_cards",
            source_text="林缺回到黄泉饭店。",
            schema_name="scene_cards",
        )
    )
    assert result.status == "fallback_required"
    assert result.generation_source == "offline_engine"
    assert result.data == {}
    assert result.warnings


def test_mock_creative_engine_validates_scene_card_schema():
    engine = MockCreativeEngine(
        {
            "scene_cards": [
                {
                    "visual": "黄泉饭店大厅，林缺站在柜台后。",
                    "voiceover": "雨夜，饭店重新开门。",
                    "duration_sec": 8,
                    "asset_goal": {"type": "adapted scene key frame"},
                }
            ]
        }
    )
    result = engine.generate(CreativeEngineRequest(kind="scene_cards", schema_name="scene_cards"))
    assert result.ok
    assert result.data[0]["visual"]

    bad = MockCreativeEngine({"scene_cards": [{"visual": "只有画面"}]})
    bad_result = bad.generate(CreativeEngineRequest(kind="scene_cards", schema_name="scene_cards"))
    assert bad_result.status == "schema_error"
    assert any("voiceover" in error for error in bad_result.errors)


def test_live_llm_engine_blocks_without_explicit_double_approval():
    engine = LiveLLMEngine(provider="test", allow_live=False)
    try:
        engine.generate(CreativeEngineRequest(kind="scene_cards", allow_live=True))
    except EngineBlockedError:
        pass
    else:
        raise AssertionError("live LLM engine must block without engine-level approval")

    approved_engine = LiveLLMEngine(provider="test", allow_live=True)
    result = approved_engine.generate(CreativeEngineRequest(kind="scene_cards", schema_name="scene_cards", allow_live=True))
    assert result.status == "provider_request_ready"
    assert result.raw_response["live_call_made"] is False
    assert result.raw_response["provider_request"]["network_call_allowed"] is False
    assert result.raw_response["provider_request"]["prompt_pack"]["kind"] == "scene_cards"



def test_prompt_pack_builds_adapter_constraints_and_provider_request():
    adapter = VerticalShortDramaAdapter()
    request = CreativeEngineRequest(
        kind="scene_cards",
        source_text="林缺在雨夜回到黄泉饭店，牛头员工端着托盘出现。",
        creative_brief={"target": "short_drama", "tone": "悬疑诡异"},
        format_name=adapter.spec().format_name,
        schema_name="scene_cards",
        payload={"adapter": adapter.creative_engine_payload({"title": "黄泉饭店"}, {"n_scene_cards": 3})},
    )
    prompt_pack = build_prompt_pack(request)
    assert prompt_pack["prompt_pack_version"] == "copy-creative-prompt-pack-v1"
    assert prompt_pack["response_contract"]["json_only"] is True
    assert "visual" in prompt_pack["response_contract"]["item_required"]
    assert "9:16" in prompt_pack["user_prompt"]
    assert "Detected Creative Diagnostics" in prompt_pack["user_prompt"]
    assert "Quality Gate Before Final JSON" in prompt_pack["user_prompt"]
    assert prompt_pack["creative_diagnostics"]["genre_profile"]["primary"] == "underworld_supernatural"
    assert prompt_pack["creative_diagnostics"]["causality_contract"]["source_authority"]
    assert prompt_pack["creative_diagnostics"]["rhythm_contract"]["opening_rule"].startswith("first 3 seconds")
    assert "no_unsupported_plot_drift" in prompt_pack["quality_targets"]
    assert "no_unapproved_new_plot_facts" in prompt_pack["safety_constraints"]

    provider_request = build_provider_request(prompt_pack, provider="openai", model="unit-test-model")
    assert provider_request["network_call_allowed"] is False
    assert provider_request["mode"] == "dry_run_provider_request"
    assert provider_request["messages"][0]["role"] == "system"
    assert provider_request["response_format"]["schema_name"] == "scene_cards"




def test_prompt_pack_builds_character_voice_contract_from_roles():
    adapter = VerticalShortDramaAdapter()
    request = CreativeEngineRequest(
        kind="script_scenes",
        source_text="林缺在黄泉饭店柜台后翻开菜单账本。苏澜用探测器确认大厅异常。",
        creative_brief={"target": "short_drama", "tone": "悬疑诡异"},
        format_name=adapter.spec().format_name,
        schema_name="script_scenes",
        payload={
            "characters": [
                {"name": "林缺", "role": "老板"},
                {"name": "苏澜", "role": "调查者"},
            ],
            "story_beats": ["林缺回到饭店", "苏澜发现异常"],
            "adapter": adapter.creative_engine_payload({"title": "黄泉饭店"}, {}),
        },
    )
    prompt_pack = build_prompt_pack(request)
    voice_contract = prompt_pack["creative_diagnostics"]["character_voice_contract"]
    assert voice_contract[0]["name"] == "林缺"
    assert any("authority" in item for item in voice_contract[0]["voice_rules"])
    assert voice_contract[1]["name"] == "苏澜"
    assert any("evidence" in item for item in voice_contract[1]["voice_rules"])
    assert "do not add unsupported plot facts" in prompt_pack["creative_diagnostics"]["forbidden_drift"]
def test_run_task_build_creative_prompt_pack_writes_dry_run_provider_request():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "build_creative_prompt_pack",
                "prompt_kind": "script_scenes",
                "title": "黄泉饭店",
                "source_text": "林缺回到黄泉饭店。牛头员工端托盘出现。",
                "creative_brief": {"target": "short_drama", "tone": "悬疑诡异"},
                "scene_cards": [
                    {
                        "visual": "黄泉饭店大厅，林缺翻开菜单账本。",
                        "voiceover": "规则变了。",
                        "duration_sec": 8,
                        "asset_goal": {"type": "adapted scene key frame"},
                    }
                ],
                "llm_provider": "openai",
                "llm_model": "unit-test-model",
                "output_dir": output_dir,
            }
        )
        handoff = result["handoff"]
        assert result["status"] == "success"
        assert handoff["live_call_made"] is False
        assert handoff["provider_request"]["network_call_allowed"] is False
        assert handoff["provider_request_summary"]["schema_name"] == "script_scenes"
        assert handoff["prompt_pack"]["kind"] == "script_scenes"
        assert os.path.exists(os.path.join(output_dir, "creative_prompt_pack.json"))
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
        assert cards[0]["generation_source"] == "fallback_scaffold"
        assert result["handoff"]["quality_report"]["target"] == "scene_cards"
        assert result["handoff"]["quality_report"]["warnings"]
        assert os.path.exists(os.path.join(output_dir, "adaptation_scene_cards.json"))

def test_build_adaptation_scene_cards_can_use_mock_creative_engine():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "build_adaptation_scene_cards",
                "title": "黄泉饭店",
                "source_text": "林缺回到黄泉饭店。",
                "creative_engine_mode": "mock",
                "creative_engine_outputs": {
                    "scene_cards": [
                        {
                            "visual": "黄泉饭店大厅，林缺低头翻开菜单账本，红光从纸页里亮起。",
                            "voiceover": "他刚回到饭店，就发现规则已经改写。",
                            "duration_sec": 8,
                            "asset_goal": {"type": "adapted scene key frame", "scene": "黄泉饭店大厅"},
                        }
                    ]
                },
                "output_dir": output_dir,
            }
        )
        cards = result["handoff"]["scene_cards"]
        assert len(cards) == 1
        assert cards[0]["generation_source"] == "mock_engine"
        assert "菜单账本" in cards[0]["visual"]
        assert cards[0]["subtitle"] == cards[0]["voiceover"]


def test_build_adaptation_scene_cards_rejects_bad_explicit_creative_engine_output():
    with tempfile.TemporaryDirectory() as output_dir:
        try:
            run_task(
                {
                    "mode": "build_adaptation_scene_cards",
                    "title": "黄泉饭店",
                    "source_text": "林缺回到黄泉饭店。",
                    "creative_engine_mode": "mock",
                    "creative_engine_outputs": {"scene_cards": [{"visual": "只有画面"}]},
                    "output_dir": output_dir,
                }
            )
        except ValueError as exc:
            assert "CreativeEngine scene card generation failed" in str(exc)
        else:
            raise AssertionError("explicit bad CreativeEngine output must not silently fall back")

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
        assert script["generation_source"] == "fallback_scaffold"
        assert script["scenes"][0]["generation_source"] == "fallback_scaffold"
        assert script["format_adapter"] == "vertical_short_drama"
        assert script["aspect_ratio"] == "9:16"
        assert script["handoff"]["can_build_blueprint"] is True
        assert script["quality_report"]["target"] == "script_draft"
        assert script["quality_report"]["status"] in {"pass", "warn"}
        assert os.path.exists(os.path.join(output_dir, "script_draft.json"))



def test_build_script_draft_can_use_overseas_short_drama_adapter():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "build_script_draft",
                "target_format": "overseas_short_drama",
                "title": "黄泉饭店",
                "scene_cards": [
                    {
                        "visual": "黄泉饭店大厅，林缺翻开菜单账本。",
                        "voiceover": "He returns to the hotel and finds the rules have changed.",
                        "duration_sec": 12,
                        "asset_goal": {"scene": "黄泉饭店大厅", "type": "adapted scene key frame"},
                    }
                ],
                "characters": [{"name": "林缺"}],
                "total_duration_sec": 12,
                "output_dir": output_dir,
            }
        )
        script = result["handoff"]["script_draft"]
        assert script["format_adapter"] == "overseas_short_drama"
        assert script["aspect_ratio"] == "9:16"
        assert "dialogue_translation_ready" in script["quality_checks"]
        assert "culture_safe_surface_wording" in script["handoff"]["copy_requirements"]
def test_build_script_draft_can_use_mock_creative_engine_script_scenes():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "build_script_draft",
                "title": "黄泉饭店",
                "scene_cards": [
                    {
                        "visual": "黄泉饭店大厅，林缺翻开菜单账本。",
                        "voiceover": "规则变了。",
                        "duration_sec": 8,
                        "asset_goal": {"scene": "黄泉饭店大厅", "type": "adapted scene key frame"},
                    }
                ],
                "creative_engine_mode": "mock",
                "creative_engine_outputs": {
                    "script_scenes": [
                        {
                            "visual": "黄泉饭店大厅，林缺低头看见菜单账本自己翻页。",
                            "voiceover": "第一秒，账本先动了。",
                            "dialogue": [{"speaker": "林缺", "line": "谁在点菜？"}],
                            "start_sec": 0,
                            "end_sec": 8,
                        }
                    ]
                },
                "total_duration_sec": 8,
                "output_dir": output_dir,
            }
        )
        script = result["handoff"]["script_draft"]
        assert script["generation_source"] == "mock_engine"
        assert script["scenes"][0]["generation_source"] == "mock_engine"
        assert script["scenes"][0]["dialogue"][0]["line"] == "谁在点菜？"
        assert script["aspect_ratio"] == "9:16"


def test_build_script_draft_rejects_bad_explicit_creative_engine_script_scenes():
    with tempfile.TemporaryDirectory() as output_dir:
        try:
            run_task(
                {
                    "mode": "build_script_draft",
                    "title": "黄泉饭店",
                    "scene_cards": [{"visual": "黄泉饭店大厅", "voiceover": "规则变了", "duration_sec": 8, "asset_goal": {"type": "adapted scene key frame"}}],
                    "creative_engine_mode": "mock",
                    "creative_engine_outputs": {"script_scenes": [{"visual": "只有画面"}]},
                    "output_dir": output_dir,
                }
            )
        except ValueError as exc:
            assert "CreativeEngine script draft generation failed" in str(exc)
        else:
            raise AssertionError("explicit bad script_scenes output must not silently fall back")

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
        assert polished["generation_source"] == "fallback_polish_scaffold"
        assert polished["scenes"][0]["generation_source"] == "fallback_polish_scaffold"
        assert polished["format_adapter"] == "vertical_short_drama"
        assert polished["handoff"]["polished_for_script"] is True
        assert polished["quality_report"]["target"] == "polished_script"
        assert polished["quality_report"]["status"] in {"pass", "warn"}
        assert os.path.exists(os.path.join(output_dir, "polished_script.json"))

def test_polish_script_draft_can_use_mock_creative_engine_polished_scenes():
    with tempfile.TemporaryDirectory() as output_dir:
        script_draft = {
            "title": "黄泉饭店",
            "total_duration_sec": 8,
            "scenes": [
                {
                    "scene_no": 1,
                    "start_sec": 0,
                    "end_sec": 8,
                    "visual": "黄泉饭店大厅，林缺翻开菜单账本。",
                    "voiceover": "规则变了。",
                    "dialogue": [{"speaker": "林缺", "line": "这里不对劲。"}],
                    "asset_goal": {"type": "adapted scene key frame"},
                }
            ],
        }
        result = run_task(
            {
                "mode": "polish_script_draft",
                "script_draft": script_draft,
                "creative_engine_mode": "mock",
                "creative_engine_outputs": {
                    "polished_script_scenes": [
                        {
                            "visual": "黄泉饭店大厅，林缺盯着自动翻页的菜单账本。",
                            "voiceover": "这次不是客人先来，是规则先醒。",
                            "dialogue": [{"speaker": "林缺", "line": "账本自己翻页了。"}],
                            "start_sec": 0,
                            "end_sec": 8,
                        }
                    ]
                },
                "output_dir": output_dir,
            }
        )
        polished = result["handoff"]["polished_script"]
        assert polished["generation_source"] == "mock_engine"
        assert polished["scenes"][0]["generation_source"] == "mock_engine"
        assert polished["scenes"][0]["dialogue"][0]["line"] == "账本自己翻页了。"
        assert polished["format_adapter"] == "vertical_short_drama"


def test_polish_script_draft_rejects_bad_explicit_creative_engine_output():
    with tempfile.TemporaryDirectory() as output_dir:
        try:
            run_task(
                {
                    "mode": "polish_script_draft",
                    "script_draft": {"title": "黄泉饭店", "scenes": [{"visual": "大厅", "voiceover": "规则变了", "dialogue": [], "start_sec": 0, "end_sec": 8}]},
                    "creative_engine_mode": "mock",
                    "creative_engine_outputs": {"polished_script_scenes": [{"visual": "只有画面"}]},
                    "output_dir": output_dir,
                }
            )
        except ValueError as exc:
            assert "CreativeEngine script polish failed" in str(exc)
        else:
            raise AssertionError("explicit bad polished scene output must not silently fall back")

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



def test_build_viral_explainer_script_from_episode_text():
    source_text = """黄泉饭店
第一集
林缺在雨夜回到黄泉饭店，发现大厅里的灯全部变成暗红色。
牛头员工端着托盘从厨房出来，提醒他客人马上就到。
苏澜用探测器发现大厅异常能量暴涨，真正的规则才刚刚出现。
第二集
林缺翻开菜单账本，发现每一道菜都对应一条隐藏规则。
苏澜想离开饭店，却发现大门外的街道已经变成陌生荒原。
牛头低声提醒，今晚的第一位客人不能得罪。
"""
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "build_viral_explainer_script",
                "title": "黄泉饭店",
                "source_text": source_text,
                "max_episodes": 2,
                "viewpoint": "男主视角",
                "output_dir": output_dir,
            }
        )
        assert result["status"] == "success"
        script = result["handoff"]["viral_explainer_script"]
        assert script["mode"] == "viral_explainer_script"
        assert script["viewpoint"] == "男主视角"
        assert len(script["episodes"]) == 2
        assert script["episodes"][0]["opening_hook"]
        assert script["episodes"][0]["narration_lines"]
        assert script["episodes"][0]["cliffhanger"]
        assert "scene_cards" not in script
        assert "林缺" in script["episodes"][0]["source_excerpt"]
        assert os.path.exists(os.path.join(output_dir, "viral_explainer_script.json"))


def test_build_viral_explainer_script_from_script_draft():
    script_draft = {
        "title": "黄泉饭店",
        "scenes": [
            {
                "visual": "林缺站在黄泉饭店服务台后，暗红灯光照亮菜单账本。",
                "voiceover": "林缺刚回到饭店，就发现大厅里的规则已经变了。",
                "dialogue": [{"speaker": "林缺", "line": "今晚不能出错。"}],
            },
            {
                "visual": "苏澜举起探测器，屏幕上的数值突然飙升。",
                "voiceover": "苏澜发现异常能量暴涨，真正的客人正在靠近。",
                "dialogue": [{"speaker": "苏澜", "line": "这里不是普通饭店。"}],
            },
        ],
    }
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "build_viral_explainer_script",
                "script_draft": script_draft,
                "target_platform": "douyin",
                "output_dir": output_dir,
            }
        )
        script = result["handoff"]["viral_explainer_script"]
        episode = script["episodes"][0]
        assert script["target_platform"] == "douyin"
        assert episode["opening_hook"]
        assert len(episode["narration_lines"]) >= 2
        assert episode["platform_notes"]["boundary"] == "不新增角色、不改动原剧情因果、不把解说稿写成分镜场景卡"
        assert any("场景卡" in item for item in script["quality_checks"])

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
