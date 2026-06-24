import json
import os
import sys
import tempfile
import copy

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from continuity import build_continuity_bible, choose_scene_id, find_character_ids_in_text  # noqa: E402
from config import VideoProviderConfig  # noqa: E402
from poyo_video_client import PoYoVideoClient  # noqa: E402
from storyboard_panel_refs import build_storyboard_panel_refs  # noqa: E402
import video_provider  # noqa: E402
from video_provider import prepare_video_generation_request, run_video_generation  # noqa: E402
import video_sequence  # noqa: E402
from video_handoff import build_video_handoff  # noqa: E402
from preflight_video_episode import preflight_video_generation  # noqa: E402
from asset_manifest import build_asset_manifest_review, build_asset_manifest_template, scan_asset_manifest_directory, validate_asset_manifest  # noqa: E402
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


def _martial_task():
    task = copy.deepcopy(_task())
    task["title"] = "青衫剑客"
    task["blueprint"]["segments"] = [
        {
            "index": 1,
            "start_sec": 0,
            "end_sec": 6,
            "visual": "青衫剑客在雨夜石桥上拔剑起势，对手横刀逼近，双方短暂对峙。",
            "voiceover": "雨声压住呼吸，剑光先动。",
        },
        {
            "index": 2,
            "start_sec": 6,
            "end_sec": 12,
            "visual": "青衫剑客侧身闪避后横剑格挡，一次清晰反击逼退对手，收势停在桥边。",
            "voiceover": "一招之后，胜负未分。",
        },
    ]
    task["target_clip_duration_sec"] = 12
    return task


def test_build_continuity_bible_outputs_locks():
    bible = build_continuity_bible(_task())
    assert bible["source_title"] == "黄泉饭店"
    assert "lin_que" in bible["character_locks"]
    assert "niu_tou" in bible["character_locks"]
    assert bible["character_locks"]["lin_que"]["costume_lock"]
    assert bible["character_locks"]["niu_tou"]["prop_locks"][0]["name"] == "菜刀"
    assert "huangquan_hall_720" in bible["scene_locks"]
    assert bible["global_visual_lock"]["style_preset"] == "realistic_short_drama"


def test_continuity_bible_uses_styling_hair_lock():
    task = copy.deepcopy(_task())
    task["ip_asset_pack"]["characters"][0]["character_profile"]["styling"]["hair"] = "黑色古风半束长发，木簪固定，禁止现代短发"
    bible = build_continuity_bible(task)
    assert bible["character_locks"]["lin_que"]["hair_lock"] == "黑色古风半束长发，木簪固定，禁止现代短发"


def test_continuity_bible_infers_xianxia_cloud_atmosphere():
    task = copy.deepcopy(_task())
    task["ip_asset_pack"]["scenes"][0]["description"] = "东方修仙宗门云海石阶，宗门石柱、仙鹤、山风和日外冷白天光"
    bible = build_continuity_bible(task)
    scene = bible["scene_locks"]["huangquan_hall_720"]
    assert scene["weather_atmosphere_lock"] == "云海、山风、轻雾、仙侠日外空气感"
    assert scene["palette_lock"] == "冷白天光、淡金侧逆光、云雾蓝灰、低饱和仙侠写实色调"



def test_video_style_preset_flows_into_continuity_and_prompts():
    task = copy.deepcopy(_task())
    task["style_preset"] = "realistic_xianxia_short_drama"
    bible = build_continuity_bible(task)
    style = bible["global_visual_lock"]
    assert style["style_preset"] == "realistic_xianxia_short_drama"
    assert "realistic xianxia short-drama" in style["style_direction"]
    assert "cool daylight" in style["color_grade"]
    assert "modern short hair" in style["forbidden_drift"]
    handoff = build_video_handoff(task)
    assert "realistic xianxia short-drama" in handoff["shots"][0]["i2v_prompt"]
    assert "grounded xianxia period styling" in handoff["shots"][0]["seedance_prompt"]
def test_build_video_handoff_has_required_shot_fields():
    handoff = build_video_handoff(_task())
    assert len(handoff["shots"]) == 2
    assert len(handoff["clip_plan"]) == 1
    assert len(handoff["storyboard_image_tasks"]) == 1
    assert handoff["clip_prompts"][0]["clip_id"] == "clip_001"
    assert handoff["clip_prompts"][0]["storyboard_execution_map"][0]["storyboard_shot_id"] == "shot_001"
    assert handoff["clip_plan"][0]["video_reference_images"]
    assert handoff["clip_plan"][0]["space_anchor_refs"]
    assert handoff["clip_plan"][0]["first_frame_spec"]["alignment_checks"]
    assert handoff["clip_plan"][0]["first_frame_spec"]["pose_lock"]
    assert handoff["clip_plan"][0]["first_frame_spec"]["blocking_lock"]
    assert handoff["clip_plan"][0]["first_frame_spec"]["action_phase_lock"]
    assert handoff["clip_plan"][0]["mid_frame_spec"]["source_shot_id"]
    assert handoff["clip_plan"][0]["last_frame_spec"]["source_shot_id"]
    assert handoff["clip_plan"][0]["storyboard_mode"] == "production"
    assert handoff["clip_prompts"][0]["storyboard_mode"] == "production"
    assert handoff["clip_plan"][0]["storyboard_execution_map"][0]["storyboard_shot_id"] == "shot_001"
    assert "must_execute_in_order" in handoff["clip_plan"][0]["storyboard_execution_map"][0]["execution_rule"]
    assert "do_not_merge_away" in handoff["clip_plan"][0]["storyboard_execution_map"][0]["execution_rule"]
    assert handoff["clip_plan"][0]["storyboard_revision_suggestions"] == []
    assert handoff["clip_plan"][0]["storyboard_quality"]["status"] == "pass"
    assert handoff["clip_prompts"][0]["storyboard_quality"]["status"] == "pass"
    assert handoff["quality_checks"]["storyboard_quality_summary"]["status"] == "pass"
    assert "故事板执行映射" in handoff["clip_plan"][0]["clip_prompt"]
    assert "Prompt Packet V1" in handoff["clip_plan"][0]["clip_prompt"]
    assert "Global Context" in handoff["clip_plan"][0]["clip_prompt"]
    assert "Internal Story Facts" in handoff["clip_plan"][0]["clip_prompt"]
    assert "Reference Bindings" in handoff["clip_plan"][0]["clip_prompt"]
    assert "Spatial Blocking" in handoff["clip_plan"][0]["clip_prompt"]
    assert "15s Timeline" in handoff["clip_plan"][0]["clip_prompt"]
    assert "Continuation Contract" in handoff["clip_plan"][0]["clip_prompt"]
    assert "Platform-Safe Surface Wording" in handoff["clip_plan"][0]["clip_prompt"]
    assert "Execution Constraints" in handoff["clip_plan"][0]["clip_prompt"]
    assert any("Prompt Packet V1" in item for item in handoff["clip_plan"][0]["quality_checks"])
    assert "first_frame_spec" in handoff["clip_prompts"][0]
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



def test_clip_provider_prompts_are_model_specific_and_compact():
    handoff = build_video_handoff(_task())
    clip = handoff["clip_plan"][0]
    required_sections = [
        "Prompt Packet V1",
        "Global Context",
        "Internal Story Facts",
        "Reference Bindings",
        "Spatial Blocking",
        "15s Timeline",
        "Continuation Contract",
        "Platform-Safe Surface Wording",
        "Execution Constraints",
    ]
    provider_prompts = [clip["i2v_prompt"], clip["seedance_prompt"], clip["t2v_prompt"]]
    assert clip["i2v_prompt"] != clip["seedance_prompt"]
    assert clip["seedance_prompt"] != clip["t2v_prompt"]
    assert clip["i2v_prompt"] != clip["t2v_prompt"]
    assert "prompt_kind=i2v" in clip["i2v_prompt"]
    assert "prompt_kind=seedance" in clip["seedance_prompt"]
    assert "prompt_kind=t2v" in clip["t2v_prompt"]
    budgets = clip["prompt_strategy"]["provider_prompt_budgets"]
    for kind, prompt in [("i2v", clip["i2v_prompt"]), ("seedance", clip["seedance_prompt"]), ("t2v", clip["t2v_prompt"])]:
        for section in required_sections:
            assert section in prompt
        assert len(prompt) < len(clip["clip_prompt"])
        assert len(prompt) <= budgets[kind]
    assert clip["prompt_strategy"]["architecture"] == "Prompt Packet V1"
    assert "compact surface packets" in clip["prompt_strategy"]["provider_prompts"]


def test_storyboard_draft_mode_marks_review_only_without_changing_map():
    task = copy.deepcopy(_task())
    task["storyboard_mode"] = "draft"
    handoff = build_video_handoff(task)
    clip = handoff["clip_plan"][0]
    execution_map = clip["storyboard_execution_map"]
    required_sections = [
        "Prompt Packet V1",
        "Global Context",
        "Internal Story Facts",
        "Reference Bindings",
        "Spatial Blocking",
        "15s Timeline",
        "Continuation Contract",
        "Platform-Safe Surface Wording",
        "Execution Constraints",
    ]

    assert clip["storyboard_mode"] == "draft"
    assert handoff["clip_prompts"][0]["storyboard_mode"] == "draft"
    assert [item["storyboard_shot_id"] for item in execution_map] == clip["shot_ids"]
    assert all(item["storyboard_mode"] == "draft" for item in execution_map)
    assert "draft_review_allowed" in execution_map[0]["execution_rule"]
    assert "do_not_apply_without_user_approval" in execution_map[0]["execution_rule"]
    assert "must_execute_in_order" not in execution_map[0]["execution_rule"]
    assert clip["storyboard_revision_suggestions"]
    assert "不得自动" in clip["storyboard_revision_suggestions"][0]
    assert "故事板执行映射（草稿审查）" in clip["clip_prompt"]
    assert "Storyboard execution map draft review" in clip["i2v_prompt"]
    for prompt in [clip["i2v_prompt"], clip["seedance_prompt"], clip["t2v_prompt"]]:
        for section in required_sections:
            assert section in prompt


def test_clip_provider_prompt_budget_preserves_required_sections_for_long_clip():
    task = copy.deepcopy(_task())
    long_visual = "林缺站在黄泉饭店大厅中央，" + "柜台、厨房门、雨夜玻璃窗、红色招牌反光、湿冷地面、菜单账本、托盘、菜刀、门口阴影、墙面旧钟反复进入画面，" * 12
    task["blueprint"]["segments"] = [
        {
            "index": 1,
            "start_sec": 0,
            "end_sec": 5,
            "visual": long_visual + "林缺抬眼看向门口。",
            "voiceover": "雨夜，饭店重新开门。",
        },
        {
            "index": 2,
            "start_sec": 5,
            "end_sec": 11,
            "visual": long_visual + "牛头端着托盘从厨房出来，和林缺隔着柜台对视。",
            "voiceover": "员工回来了。",
        },
    ]
    handoff = build_video_handoff(task)
    clip = handoff["clip_plan"][0]
    required_sections = [
        "Prompt Packet V1",
        "Global Context",
        "Internal Story Facts",
        "Reference Bindings",
        "Spatial Blocking",
        "15s Timeline",
        "Continuation Contract",
        "Platform-Safe Surface Wording",
        "Execution Constraints",
    ]
    for kind in ("i2v", "seedance", "t2v"):
        prompt = clip[f"{kind}_prompt"]
        assert len(prompt) <= clip["prompt_strategy"]["provider_prompt_budgets"][kind]
        for section in required_sections:
            assert section in prompt
def test_character_matching_uses_role_alias_and_props_before_fallback():
    bible = build_continuity_bible(_task())
    locks = bible["character_locks"]
    assert find_character_ids_in_text("老板翻开菜单账本，抬眼看向门口。", locks) == ["lin_que"]
    assert find_character_ids_in_text("托盘从厨房门后出现，员工压低菜刀。", locks) == ["niu_tou"]


def test_scene_matching_uses_weighted_specific_tokens_not_generic_time_tokens():
    scene_locks = {
        "office_alley": {
            "name": "场1-1 夜/内 巡捕房值班房、窄巷子",
            "layout_lock": "夜内巡捕房值班房，旁边有窄巷子",
            "landmark_lock": ["巡捕房", "窄巷子"],
        },
        "sect_hall": {
            "name": "场1-2 夜/内 宗门大殿",
            "layout_lock": "夜内宗门大殿，石阶、云雾、祖师像",
            "landmark_lock": ["宗门大殿", "石阶", "祖师像"],
        },
    }
    assert choose_scene_id("夜色里，宗门大殿的石阶被云雾压住。", scene_locks) == "sect_hall"


def test_action_opening_uses_content_driven_framing_camera_and_end_state():
    handoff = build_video_handoff(_martial_task())
    shot = handoff["shots"][0]
    card = shot["storyboard_card"]
    assert "FS/MS 动作中景" in card["framing"]
    assert "stable action follow" in card["camera_motion"]
    assert "武器或关键道具已进入" in shot["continuity_state"]["current_end_state"]
    assert "高度警觉" in shot["prompt_profile"]["performance_control"]

def test_negative_prompt_profile_prioritizes_provider_prompt_and_retry_advice_is_shot_specific():
    task = copy.deepcopy(_martial_task())
    task["style_preset"] = "realistic_xianxia_short_drama"
    handoff = build_video_handoff(task)
    shot = handoff["shots"][0]
    profile = shot["negative_prompt_profile"]
    assert profile["critical_identity_negatives"]
    assert profile["spatial_negatives"]
    assert profile["model_artifact_negatives"]
    assert profile["action_safety_negatives"]
    assert profile["style_negatives"]
    assert len(profile["provider_negative_prompt"]) < len(profile["audit_negative_prompt"])
    assert "不要换脸" in shot["negative_prompt"]
    assert "不要越轴" in shot["negative_prompt"]
    assert "不要招式文字" in shot["negative_prompt"]
    assert "不要塑料皮肤" in shot["negative_prompt"]
    assert any("shot_001" in item and "动作糊成一团" in item for item in shot["retry_advice"])
    assert any("shot_001" in item and "运镜太晃" in item for item in shot["retry_advice"])
def test_storyboard_image_task_for_clip_design_sheet():
    handoff = build_video_handoff(_task())
    task = handoff["storyboard_image_tasks"][0]
    assert task["mode"] == "text_to_image"
    assert task["asset_kind"] == "clip_storyboard_board"
    assert task["filename"] == "clip_001_clip_storyboard_board.jpg"
    assert task["visual_text_language"] == "zh-CN"
    assert "storyboard_profile" in task
    assert task["storyboard_profile"]["clip_id"] == "clip_001"
    assert task["storyboard_profile"]["storyboard_type"] == "clip_storyboard_board"
    assert task["storyboard_profile"]["panel_count"] == 5
    assert task["storyboard_profile"]["first_frame_spec"]["kind"] == "first_frame"
    assert "first frame composition alignment" in task["storyboard_profile"]["first_frame_spec"]["alignment_checks"]
    assert "start_state" in task["storyboard_profile"]
    assert "main_action" in task["storyboard_profile"]
    assert "end_state" in task["storyboard_profile"]
    assert task["video_reference_images"]
    assert task["space_anchor_refs"]
    assert any("no dialogue subtitles" in item for item in task["asset_requirements"])
    assert any("first frame composition alignment" in item for item in task["asset_requirements"])
    assert any("camera angle lock" in item for item in task["asset_requirements"])
    assert any("subject scale lock" in item for item in task["asset_requirements"])
    assert any("pose lock" in item for item in task["asset_requirements"])
    assert any("blocking lock" in item for item in task["asset_requirements"])
    assert any("screen direction lock" in item for item in task["asset_requirements"])
    assert "5-panel short-drama storyboard board" in task["composition"]
    assert "panel 1 must match the intended video first frame composition" in task["composition"]
    assert "pose lock=" in task["composition"]
    assert "action phase lock=" in task["composition"]


def test_shot_table_storyboard_type_has_table_columns():
    task_data = _task()
    task_data["storyboard_type"] = "shot_table_storyboard"
    handoff = build_video_handoff(task_data)
    task = handoff["storyboard_image_tasks"][0]
    assert task["asset_kind"] == "shot_table_storyboard"
    assert task["storyboard_profile"]["storyboard_type"] == "shot_table_storyboard"
    assert "镜头号 / 画面与构图 / 摄影机运动 / 动作表演 / 台词声音 / 时长或时间点" in task["composition"]
    assert any("shot_table_storyboard" in item for item in task["asset_requirements"])


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


def test_cutaway_visual_without_character_name_keeps_empty_character_list():
    task = copy.deepcopy(_task())
    task["blueprint"]["segments"] = [
        {
            "index": 1,
            "start_sec": 0,
            "end_sec": 5,
            "visual": "空镜/道具插入，云雾掠过石阶，残旗在宗门石柱旁晃动。",
            "voiceover": "系统即将出现。",
        }
    ]
    handoff = build_video_handoff(task)
    shot = handoff["shots"][0]
    assert shot["characters"] == []
    assert shot["screen_direction"] == {"environment": "空镜保持空间方向清楚"}
    assert shot["visual_lock"]["characters"] == {}


def test_prompts_include_quality_layers_and_retry_advice():
    handoff = build_video_handoff(_task())
    shot = handoff["shots"][1]
    assert "动作流程" in shot["i2v_prompt"]
    assert "真实感锚点" in shot["i2v_prompt"]
    assert "不要完美模板脸" in shot["i2v_prompt"]
    assert "不要塑料皮肤" in shot["negative_prompt"]
    assert "不要AI模板脸" in shot["negative_prompt"]
    assert "不要玻璃珠眼睛" in shot["negative_prompt"]
    assert any("脸漂移" in item for item in shot["retry_advice"])
    assert handoff["seedance_prompts"][1]["prompt"] == shot["seedance_prompt"]


def test_martial_arts_layer_enhances_shot_clip_and_storyboard():
    handoff = build_video_handoff(_martial_task())
    shot = handoff["shots"][0]
    clip = handoff["clip_plan"][0]
    storyboard_task = handoff["storyboard_image_tasks"][0]
    assert shot["storyboard_card"]["action_scene_type"] == "martial_arts"
    assert shot["prompt_profile"]["martial_arts_layer"]["scene_type"] == "martial_arts"
    assert "武戏调度" in shot["i2v_prompt"]
    assert "起势亮明距离" in shot["i2v_prompt"]
    assert "不要招式文字" in shot["negative_prompt"]
    assert clip["martial_arts_layer"]["scene_type"] == "martial_arts"
    assert "武戏调度" in clip["clip_prompt"]
    assert storyboard_task["storyboard_profile"]["martial_arts_layer"]["scene_type"] == "martial_arts"
    assert storyboard_task["asset_kind"] == "martial_action_storyboard"
    assert storyboard_task["storyboard_profile"]["panel_count"] == 12
    assert any("starting stance" in item for item in storyboard_task["asset_requirements"])
    assert any("red arrows" in item for item in storyboard_task["asset_requirements"])


def test_plain_slap_does_not_trigger_martial_arts_layer():
    task = copy.deepcopy(_task())
    task["blueprint"]["global_style"]["tone"] = "东方仙侠古风短剧"
    task["blueprint"]["segments"] = [
        {
            "index": 1,
            "start_sec": 0,
            "end_sec": 5,
            "visual": "陈凡站在云端石阶上，摸脸后给自己一巴掌，确认不是做梦。",
        }
    ]
    handoff = build_video_handoff(task)
    shot = handoff["shots"][0]
    clip = handoff["clip_plan"][0]
    assert shot["prompt_profile"]["martial_arts_layer"] == {}
    assert "武戏调度" not in shot["i2v_prompt"]
    assert clip["martial_arts_layer"] == {}
    assert "武戏调度" not in clip["clip_prompt"]


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
    assert "first frame composition alignment" in clip["clip_prompt"]
    assert "动作相位" in clip["clip_prompt"]
    assert "跨 clip 衔接不等于每段都复制上一段构图" in clip["clip_prompt"]
    assert "近景、特写、全景、远景、背影、反打、空镜、道具插入或手部局部" in clip["clip_prompt"]


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
            "clip_index": 1,
            "prompt_kind": "seedance",
        },
        config,
    )
    assert request["provider"] == "offline"
    assert request["clip_id"] == "clip_001"
    assert request["unit_kind"] == "clip"
    assert request["mode"] == "image_to_video"
    assert "first frame composition alignment" in request["prompt"]
    assert "pose lock=" in request["prompt"]
    assert "action phase lock=" in request["prompt"]
    assert request["transport"]["type"] == "dry_run"
    assert request["reference_binding"]["scene_lock"]
    assert request["first_frame_spec"]["alignment_checks"]
    assert request["storyboard_mode"] == "production"
    assert request["storyboard_execution_map"][0]["storyboard_shot_id"] == "shot_001"
    assert "故事板执行映射" in request["prompt"]


def test_storyboard_panel_refs_crop_and_bind_to_provider_request():
    handoff = build_video_handoff(_task())
    with tempfile.TemporaryDirectory() as output_dir:
        storyboard_path = os.path.join(output_dir, "clip_001_clip_storyboard_board.jpg")
        Image.new("RGB", (1200, 600), "white").save(storyboard_path)
        refs = build_storyboard_panel_refs(
            {
                "storyboard_image_path": storyboard_path,
                "output_dir": output_dir,
                "storyboard_panel_count": 3,
                "storyboard_panel_top_ratio": 0.1,
                "storyboard_panel_bottom_ratio": 0.5,
                "storyboard_panel_left_ratio": 0.08,
                "storyboard_panel_right_ratio": 0.98,
            },
            handoff["clip_plan"][0],
        )
        assert [ref["role"] for ref in refs] == ["first_frame_layout_ref", "mid_frame_layout_ref", "last_frame_layout_ref"]
        assert all(os.path.exists(ref["path"]) for ref in refs)

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
                "clip_index": 1,
                "storyboard_image_path": storyboard_path,
                "output_dir": output_dir,
                "storyboard_panel_count": 3,
                "storyboard_panel_top_ratio": 0.1,
                "storyboard_panel_bottom_ratio": 0.5,
                "storyboard_panel_left_ratio": 0.08,
                "storyboard_panel_right_ratio": 0.98,
            },
            config,
        )
        roles = [ref["role"] for ref in request["reference_image_urls"]]
        assert "first_frame_layout_ref" in roles
        assert "mid_frame_layout_ref" in roles
        assert "last_frame_layout_ref" in roles
        assert "故事板裁图构图参考" in request["prompt"]
        assert "禁止复制线稿风格" in request["prompt"]


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


def test_poyo_defaults_to_seedance2_not_fast():
    handoff = build_video_handoff(_task())
    config = VideoProviderConfig(
        provider="poyo_video",
        api_key="test",
        api_base="https://api.example",
        output_root="",
        default_model="",
        default_aspect_ratio="9:16",
        default_resolution="480p",
        poll_interval_sec=1,
        poll_timeout_sec=5,
    )
    request = prepare_video_generation_request(
        {
            "video_handoff": handoff,
            "provider": "poyo_video",
            "image_urls": ["https://files.example/first.png"],
            "duration_sec": 5,
        },
        config,
    )
    assert request["model"] == "seedance-2"
    assert request["transport"]["json"]["model"] == "seedance-2"


def test_poyo_blocks_fast_model_unless_explicitly_allowed():
    handoff = build_video_handoff(_task())
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    try:
        prepare_video_generation_request(
            {
                "video_handoff": handoff,
                "provider": "poyo_video",
                "model": "seedance-2-fast",
                "image_urls": ["https://files.example/first.png"],
                "duration_sec": 5,
            },
            config,
        )
    except RuntimeError as exc:
        assert "seedance-2-fast is not allowed by default" in str(exc)
    else:
        raise AssertionError("fast model should require explicit user opt-in")

    request = prepare_video_generation_request(
        {
            "video_handoff": handoff,
            "provider": "poyo_video",
            "model": "seedance-2-fast",
            "allow_fast_model": True,
            "image_urls": ["https://files.example/first.png"],
            "duration_sec": 5,
        },
        config,
    )
    assert request["transport"]["json"]["model"] == "seedance-2-fast"


def test_poyo_reference_images_are_bound_with_image_markers():
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
            "generation_mode": "multimodal_to_video",
            "reference_image_urls": [
                {"url": "https://files.example/lin_que_design_sheet.jpg", "role": "character_design_sheet"},
                {"url": "https://files.example/hall_video_scene_reference.jpg", "role": "video_scene_reference"},
            ],
            "duration_sec": 5,
        },
        config,
    )
    prompt = request["transport"]["json"]["input"]["prompt"]
    assert "@Image1 是角色身份参考图" in prompt
    assert "@Image2 是场景空间参考图" in prompt
    assert "可见地标、材质状态、光源方向和整体色调" in prompt
    assert "雨夜湿地反光" not in prompt
    assert "禁止把参考图角色替换成明星脸" in prompt
    assert "同一脸型、眼型、鼻型、唇形、发型系统" in prompt
    assert request["transport"]["json"]["input"]["reference_image_urls"] == [
        "https://files.example/lin_que_design_sheet.jpg",
        "https://files.example/hall_video_scene_reference.jpg",
    ]



def test_all_purpose_reference_policy_does_not_fall_back_to_first_or_tail_frame():
    handoff = build_video_handoff(_task())
    handoff["clip_plan"][0]["previous_clip_end_frame"] = {"url": "https://files.example/previous_tail.png", "role": "previous_clip_end_frame"}
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
            "reference_policy": "all_purpose_reference",
            "reference_image_urls": [
                {"url": "https://files.example/zhouhao.jpg", "role": "character_reference"},
                {"url": "https://files.example/storyboard.jpg", "role": "storyboard_layout_reference"},
            ],
            "duration_sec": 15,
        },
        config,
    )
    assert request["mode"] == "multimodal_to_video"
    assert request["image_urls"] == []
    assert [item["url"] for item in request["reference_image_urls"]] == [
        "https://files.example/zhouhao.jpg",
        "https://files.example/storyboard.jpg",
    ]
    input_obj = request["transport"]["json"]["input"]
    assert "image_urls" not in input_obj
    assert input_obj["reference_image_urls"] == [
        "https://files.example/zhouhao.jpg",
        "https://files.example/storyboard.jpg",
    ]
    assert "全能参考模式已锁定" in request["prompt"]
    assert "不得自动替换、降级或改写为 image_urls" in request["prompt"]
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


def test_storyboard_quality_blocks_long_unbroken_running_shot():
    task = copy.deepcopy(_task())
    task["blueprint"]["segments"] = [
        {
            "index": 1,
            "start_sec": 0,
            "end_sec": 15,
            "visual": "林缺在黄泉饭店走廊里持续奔跑，沿同一方向躲避追击，整段没有反应镜头和结果落点。",
        }
    ]
    handoff = build_video_handoff(task)
    clip = handoff["clip_plan"][0]
    quality = clip["storyboard_quality"]

    assert quality["status"] == "fail"
    assert any(issue["code"] == "long_unbroken_motion" for issue in quality["issues"])
    assert clip["storyboard_execution_map"][0]["storyboard_shot_id"] == "shot_001"
    assert handoff["quality_checks"]["storyboard_quality_summary"]["status"] == "fail"

    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    report = preflight_video_generation(
        {
            "mode": "preflight_video_generation",
            "provider": "poyo_video",
            "video_handoff": handoff,
            "clip_index": 1,
            "image_urls": [{"url": "https://files.example/first.png", "role": "first_frame"}],
        },
        config,
    )
    assert report["status"] == "fail"
    assert any("storyboard_quality failed" in error and "long_unbroken_motion" in error for error in report["errors"])


def test_storyboard_quality_warns_dense_clip_without_reordering_map():
    task = copy.deepcopy(_task())
    task["target_clip_duration_sec"] = 15
    task["blueprint"]["segments"] = [
        {"index": idx + 1, "start_sec": idx * 2, "end_sec": (idx + 1) * 2, "visual": f"林缺发现柜台异常后完成第{idx + 1}个清楚动作落点。"}
        for idx in range(6)
    ]
    handoff = build_video_handoff(task)
    clip = handoff["clip_plan"][0]
    quality = clip["storyboard_quality"]

    assert quality["status"] == "warn"
    assert any(issue["code"] == "high_shot_density" for issue in quality["issues"])
    assert [item["storyboard_shot_id"] for item in clip["storyboard_execution_map"]] == clip["shot_ids"]

    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    report = preflight_video_generation(
        {
            "mode": "preflight_video_generation",
            "provider": "poyo_video",
            "video_handoff": handoff,
            "clip_index": 1,
            "image_urls": [{"url": "https://files.example/first.png", "role": "first_frame"}],
        },
        config,
    )
    assert report["status"] == "pass"
    assert any("storyboard_quality warning" in warning and "high_shot_density" in warning for warning in report["warnings"])


def test_bridge_clip_policy_adds_cutaway_between_clips():
    task = copy.deepcopy(_task())
    task["target_clip_duration_sec"] = 5
    task["bridge_clip_policy"] = "always"
    task["bridge_clip_duration_sec"] = 2
    task["blueprint"]["segments"] = [
        {"index": idx + 1, "start_sec": idx * 5, "end_sec": (idx + 1) * 5, "visual": f"陈渊在值班房连续动作 {idx + 1}"}
        for idx in range(2)
    ]
    handoff = build_video_handoff(task)
    assert len(handoff["clip_plan"]) == 2
    assert len(handoff["bridge_clips"]) == 1
    bridge = handoff["bridge_clips"][0]
    assert bridge["bridge_clip"] is True
    assert bridge["after_clip_id"] == "clip_001"
    assert bridge["before_clip_id"] == "clip_002"
    assert bridge["timing"]["duration_sec"] == 2
    assert "不要背景音乐" in bridge["negative_prompt"]
    assert "环境、道具、背影、手部或局部动作" in bridge["clip_prompt"]
    assert "近景、特写、远景、全景、反打或侧背角度" in bridge["clip_prompt"]
    assert "减少人脸漂移和AI模板脸风险" in bridge["clip_prompt"]
    assert handoff["edit_decision_list"]["bridge_timeline"][0]["clip_id"] == bridge["clip_id"]


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
    assert request["first_frame_spec"]["kind"] == "first_frame"
    assert "色彩、曝光、白平衡、对比度" in request["prompt"]
    assert "不要色彩跳变" in request["negative_prompt"]
    input_obj = request["transport"]["json"]["input"]
    assert input_obj["image_urls"] == ["https://files.example/clip001_last.png"]
    assert "reference_image_urls" not in input_obj


def test_poyo_previous_frame_drops_explicit_reference_images_for_transport():
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
            "reference_image_urls": [{"url": "https://files.example/character.jpg", "role": "character_design_sheet"}],
        },
        config,
    )
    assert request["image_urls"][0]["url"] == "https://files.example/clip001_last.png"
    assert request["reference_image_urls"] == []
    assert "不要曝光跳变" in request["negative_prompt"]
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


def test_run_video_sequence_carries_previous_clip_end_frame_between_clips():
    task = copy.deepcopy(_task())
    task["target_clip_duration_sec"] = 5
    task["blueprint"]["segments"] = [
        {"index": idx + 1, "start_sec": idx * 5, "end_sec": (idx + 1) * 5, "visual": f"陈渊在值班房连续动作 {idx + 1}"}
        for idx in range(2)
    ]
    handoff = build_video_handoff(task)

    calls = []
    original_run = video_sequence.run_video_generation
    original_extract = video_sequence._extract_frame

    with tempfile.TemporaryDirectory() as output_dir:
        def fake_run_video_generation(clip_task, config):
            calls.append(clip_task)
            clip_id = clip_task["clip"]["clip_id"]
            video_path = os.path.join(output_dir, f"{clip_id}.mp4")
            with open(video_path, "wb") as fh:
                fh.write(b"fake mp4")
            return {
                "status": "success",
                "dry_run": False,
                "request": {"clip_id": clip_id, "previous_clip_end_frame": clip_task["clip"].get("previous_clip_end_frame")},
                "result": {"task_id": f"task_{clip_id}", "credits_amount": 1, "local_paths": [video_path]},
                "artifacts": [{"type": "video", "path": video_path}],
            }

        def fake_extract_frame(video_path, out_dir, clip_id, label, seek):
            path = os.path.join(out_dir, f"{clip_id}_{label}_frame.jpg")
            with open(path, "wb") as fh:
                fh.write(b"frame")
            return path

        video_sequence.run_video_generation = fake_run_video_generation
        video_sequence._extract_frame = fake_extract_frame
        try:
            config = VideoProviderConfig(
                provider="offline",
                api_key="",
                api_base="",
                output_root=output_dir,
                default_model="offline-preview",
                default_aspect_ratio="9:16",
                default_resolution="480p",
                poll_interval_sec=1,
                poll_timeout_sec=5,
            )
            result = video_sequence.run_video_sequence(
                {
                    "mode": "run_video_sequence",
                    "video_handoff": handoff,
                    "max_clips": 2,
                    "continuation_mode": "hard_first_frame",
                    "dry_run": False,
                    "output_dir": output_dir,
                },
                config,
            )
        finally:
            video_sequence.run_video_generation = original_run
            video_sequence._extract_frame = original_extract

    assert len(result["clip_results"]) == 2
    assert calls[0]["generate_audio"] is True
    assert calls[1]["generate_audio"] is True
    assert calls[0]["clip"].get("previous_clip_end_frame") is None
    prev = calls[1]["clip"].get("previous_clip_end_frame")
    assert prev["role"] == "previous_clip_end_frame"
    assert prev["source_clip_id"] == "clip_001"
    assert prev["path"].endswith("clip_001_last_frame.jpg")


def test_run_video_sequence_can_use_provided_clip_video_for_continuation_dry_run():
    task = copy.deepcopy(_task())
    task["target_clip_duration_sec"] = 5
    task["blueprint"]["segments"] = [
        {"index": idx + 1, "start_sec": idx * 5, "end_sec": (idx + 1) * 5, "visual": f"陈渊在值班房连续动作 {idx + 1}"}
        for idx in range(2)
    ]
    handoff = build_video_handoff(task)
    calls = []
    original_run = video_sequence.run_video_generation
    original_extract = video_sequence._extract_frame

    with tempfile.TemporaryDirectory() as output_dir:
        provided_video = os.path.join(output_dir, "provided_clip_001.mp4")
        with open(provided_video, "wb") as fh:
            fh.write(b"fake mp4")

        def fake_run_video_generation(clip_task, config):
            calls.append(clip_task)
            return {
                "status": "success",
                "dry_run": True,
                "request": {"clip_id": clip_task["clip"]["clip_id"], "image_urls": []},
                "artifacts": [],
                "result": {},
            }

        def fake_extract_frame(video_path, out_dir, clip_id, label, seek):
            path = os.path.join(out_dir, f"{clip_id}_{label}_frame.jpg")
            with open(path, "wb") as fh:
                fh.write(b"frame")
            return path

        video_sequence.run_video_generation = fake_run_video_generation
        video_sequence._extract_frame = fake_extract_frame
        try:
            config = VideoProviderConfig("offline", "", "", output_dir, "offline-preview", "9:16", "480p", 1, 5)
            result = video_sequence.run_video_sequence(
                {
                    "video_handoff": handoff,
                    "max_clips": 2,
                    "continuation_mode": "hard_first_frame",
                    "provided_clip_video_paths": {"1": provided_video},
                    "output_dir": output_dir,
                },
                config,
            )
        finally:
            video_sequence.run_video_generation = original_run
            video_sequence._extract_frame = original_extract

    assert result["clip_results"][0]["last_frame"].endswith("clip_001_last_frame.jpg")
    assert calls[1]["clip"]["previous_clip_end_frame"]["path"].endswith("clip_001_last_frame.jpg")


def test_run_video_sequence_interleaves_bridge_clips():
    task = copy.deepcopy(_task())
    task["target_clip_duration_sec"] = 5
    task["bridge_clip_policy"] = "always"
    task["blueprint"]["segments"] = [
        {"index": idx + 1, "start_sec": idx * 5, "end_sec": (idx + 1) * 5, "visual": f"陈渊在值班房连续动作 {idx + 1}"}
        for idx in range(2)
    ]
    handoff = build_video_handoff(task)
    calls = []
    original_run = video_sequence.run_video_generation
    original_extract = video_sequence._extract_frame

    with tempfile.TemporaryDirectory() as output_dir:
        def fake_run_video_generation(clip_task, config):
            calls.append(clip_task)
            video_path = os.path.join(output_dir, f"{clip_task['clip']['clip_id']}.mp4")
            with open(video_path, "wb") as fh:
                fh.write(b"fake mp4")
            return {"status": "success", "dry_run": True, "request": {}, "artifacts": [{"type": "video", "path": video_path}], "result": {}}

        def fake_extract_frame(video_path, out_dir, clip_id, label, seek):
            path = os.path.join(out_dir, f"{clip_id}_{label}_frame.jpg")
            with open(path, "wb") as fh:
                fh.write(b"frame")
            return path

        video_sequence.run_video_generation = fake_run_video_generation
        video_sequence._extract_frame = fake_extract_frame
        try:
            config = VideoProviderConfig("offline", "", "", output_dir, "offline-preview", "9:16", "480p", 1, 5)
            result = video_sequence.run_video_sequence(
                {"video_handoff": handoff, "include_bridge_clips": True, "max_clips": 3, "output_dir": output_dir},
                config,
            )
        finally:
            video_sequence.run_video_generation = original_run
            video_sequence._extract_frame = original_extract

    assert [call["clip"]["clip_id"] for call in calls] == ["clip_001", "bridge_001_002", "clip_002"]
    assert calls[1]["clip"]["bridge_clip"] is True
    assert calls[1]["duration_sec"] == 2.0
    assert result["clip_results"][1]["bridge_clip"] is True


def test_bridge_clip_visual_uses_transition_states_not_generic_cutaway():
    task = copy.deepcopy(_task())
    task["target_clip_duration_sec"] = 5
    task["bridge_clip_policy"] = "always"
    task["blueprint"]["global_style"]["tone"] = "东方仙侠古风短剧"
    task["blueprint"]["segments"] = [
        {"index": 1, "start_sec": 0, "end_sec": 5, "visual": "陈凡站在云海石阶上抬手，袖口被山风带起。"},
        {"index": 2, "start_sec": 5, "end_sec": 10, "visual": "陈凡看向石柱旁亮起的淡蓝系统光幕。"},
    ]
    handoff = build_video_handoff(task)
    bridge = handoff["bridge_clips"][0]
    assert "上一镜尾态" in bridge["visual"]
    assert "下一镜开始" in bridge["visual"]
    assert "桥接画面必须由上一镜尾态和下一镜信息目标推导" in bridge["clip_prompt"]
    assert "不能只拍无关云雾" in bridge["clip_prompt"]
    assert "云雾、山门、石阶、窗边光、门外冷光、雨水或地面反光" not in bridge["visual"]


def test_run_video_sequence_reference_reframe_uses_previous_frame_as_reference_not_first_frame():
    task = copy.deepcopy(_task())
    task["target_clip_duration_sec"] = 5
    task["blueprint"]["segments"] = [
        {"index": idx + 1, "start_sec": idx * 5, "end_sec": (idx + 1) * 5, "visual": f"陈渊在值班房连续动作 {idx + 1}"}
        for idx in range(2)
    ]
    handoff = build_video_handoff(task)
    calls = []
    original_run = video_sequence.run_video_generation
    original_extract = video_sequence._extract_frame

    with tempfile.TemporaryDirectory() as output_dir:
        def fake_run_video_generation(clip_task, config):
            calls.append(clip_task)
            video_path = os.path.join(output_dir, f"{clip_task['clip']['clip_id']}.mp4")
            with open(video_path, "wb") as fh:
                fh.write(b"fake mp4")
            return {
                "status": "success",
                "dry_run": True,
                "request": {},
                "artifacts": [{"type": "video", "path": video_path}],
                "result": {},
            }

        def fake_extract_frame(video_path, out_dir, clip_id, label, seek):
            path = os.path.join(out_dir, f"{clip_id}_{label}_frame.jpg")
            with open(path, "wb") as fh:
                fh.write(b"frame")
            return path

        video_sequence.run_video_generation = fake_run_video_generation
        video_sequence._extract_frame = fake_extract_frame
        try:
            config = VideoProviderConfig("offline", "", "", output_dir, "offline-preview", "9:16", "480p", 1, 5)
            video_sequence.run_video_sequence({"video_handoff": handoff, "max_clips": 2, "output_dir": output_dir}, config)
        finally:
            video_sequence.run_video_generation = original_run
            video_sequence._extract_frame = original_extract

    assert calls[1]["clip"].get("previous_clip_end_frame") is None
    prev_ref = calls[1]["clip"].get("previous_clip_reference_frame")
    assert prev_ref["role"] == "previous_clip_reference_frame"
    assert "do not copy" in prev_ref["use"]


def test_prepare_reference_reframe_request_uses_previous_frame_as_reference_image():
    handoff = build_video_handoff(_task())
    clip = dict(handoff["clip_plan"][0])
    clip["previous_clip_reference_frame"] = {
        "url": "https://files.example/clip001_last.png",
        "role": "previous_clip_reference_frame",
    }
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    request = prepare_video_generation_request(
        {
            "provider": "poyo_video",
            "clip": clip,
            "reference_image_urls": [{"url": "https://files.example/character.jpg", "role": "character_design_sheet"}],
        },
        config,
    )
    assert request["image_urls"] == []
    assert [ref["role"] for ref in request["reference_image_urls"]] == [
        "character_design_sheet",
        "previous_clip_reference_frame",
    ]
    assert "上一镜连续性参考帧" in request["prompt"]
    assert "不要把上一帧当作当前首帧" in request["prompt"]
    assert "近景、特写、全景、远景、背影、反打、空镜、道具插入或手部局部" in request["prompt"]
    assert "换景别时仍必须继承同一角色" in request["prompt"]


def test_live_video_blocks_missing_storyboard_execution_map():
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    try:
        run_video_generation(
            {
                "mode": "run_video_generation",
                "provider": "poyo_video",
                "clip": {
                    "clip_id": "clip_999",
                    "shot_ids": ["shot_001"],
                    "timing": {"duration_sec": 5},
                    "clip_prompt": "测试片段",
                    "visual_lock": {},
                },
                "dry_run": False,
                "image_urls": [{"url": "https://files.example/first.png", "role": "first_frame"}],
            },
            config,
        )
    except RuntimeError as exc:
        assert "storyboard_execution_map is missing" in str(exc)
    else:
        raise AssertionError("live clip video should require storyboard_execution_map")

def test_live_video_blocks_draft_storyboard_mode():
    task = copy.deepcopy(_task())
    task["storyboard_mode"] = "draft"
    handoff = build_video_handoff(task)
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    try:
        run_video_generation(
            {
                "mode": "run_video_generation",
                "provider": "poyo_video",
                "video_handoff": handoff,
                "clip_index": 1,
                "dry_run": False,
                "image_urls": [{"url": "https://files.example/first.png", "role": "first_frame"}],
            },
            config,
        )
    except RuntimeError as exc:
        assert "storyboard_mode=draft" in str(exc)
    else:
        raise AssertionError("draft storyboard mode should be blocked before live generation")


def test_preflight_blocks_draft_storyboard_mode():
    task = copy.deepcopy(_task())
    task["storyboard_mode"] = "draft"
    handoff = build_video_handoff(task)
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    report = preflight_video_generation(
        {
            "mode": "preflight_video_generation",
            "provider": "poyo_video",
            "video_handoff": handoff,
            "clip_index": 1,
            "image_urls": [{"url": "https://files.example/first.png", "role": "first_frame"}],
        },
        config,
    )
    assert report["status"] == "fail"
    assert any("storyboard_mode=draft" in error for error in report["errors"])

def test_live_video_blocks_reference_only_generation_by_default():
    handoff = build_video_handoff(_task())
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    try:
        run_video_generation(
            {
                "mode": "run_video_generation",
                "provider": "poyo_video",
                "video_handoff": handoff,
                "clip_index": 1,
                "dry_run": False,
                "reference_image_urls": [
                    {"url": "https://files.example/linque.jpg", "role": "character_design_sheet", "character_id": "lin_que"},
                    {"url": "https://files.example/niutou.jpg", "role": "character_design_sheet", "character_id": "niu_tou"},
                    {"url": "https://files.example/scene.jpg", "role": "video_scene_reference"},
                ],
            },
            config,
        )
    except RuntimeError as exc:
        assert "only has reference_image_urls and no image_urls first-frame input" in str(exc)
    else:
        raise AssertionError("reference-only live video should be blocked")


def test_live_video_blocks_character_text_to_video_by_default():
    handoff = build_video_handoff(_task())
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    try:
        run_video_generation(
            {
                "mode": "run_video_generation",
                "provider": "poyo_video",
                "video_handoff": handoff,
                "clip_index": 1,
                "dry_run": False,
            },
            config,
        )
    except RuntimeError as exc:
        assert "locked characters but no image_urls first-frame/keyframe input" in str(exc)
    else:
        raise AssertionError("character live text-to-video should be blocked")


def test_live_video_blocks_character_clip_with_cutaway_first_frame():
    task = copy.deepcopy(_task())
    task["blueprint"]["segments"] = [
        {
            "index": 1,
            "start_sec": 0,
            "end_sec": 5,
            "visual": "空镜/道具插入，云雾掠过石阶，残旗在宗门石柱旁晃动。",
        },
        {
            "index": 2,
            "start_sec": 5,
            "end_sec": 10,
            "visual": "林缺站在石阶边看向淡蓝光幕。",
        },
    ]
    task["target_clip_duration_sec"] = 10
    handoff = build_video_handoff(task)
    clip = handoff["clip_plan"][0]
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    try:
        run_video_generation(
            {
                "mode": "run_video_generation",
                "provider": "poyo_video",
                "clip": clip,
                "dry_run": False,
                "image_urls": [{"url": "https://files.example/cutaway_first_frame.jpg", "role": "first_frame"}],
            },
            config,
        )
    except RuntimeError as exc:
        assert "first_frame_spec is a characterless cutaway" in str(exc)
    else:
        raise AssertionError("character clip with cutaway first frame should be blocked")



def test_clip_prompt_adds_high_risk_spatial_templates():
    task = copy.deepcopy(_task())
    task["blueprint"]["segments"] = [
        {
            "index": 1,
            "start_sec": 0,
            "end_sec": 5,
            "visual": "林缺从门外向饭店入口奔跑，黑雾在身后追击。",
        },
        {
            "index": 2,
            "start_sec": 5,
            "end_sec": 10,
            "visual": "林缺冲过门槛进入大厅，牛头在门内接应，门在身后关闭。",
        },
    ]
    handoff = build_video_handoff(task)
    prompt = handoff["clip_plan"][0]["clip_prompt"]
    assert "高风险空间模板" in prompt
    assert "追逐空间模板" in prompt
    assert "门槛/入口边界模板" in prompt
    assert "先显示角色完整越过边界" in prompt


def test_live_video_blocks_missing_prompt_packet_sections():
    handoff = build_video_handoff(_task())
    clip = copy.deepcopy(handoff["clip_plan"][0])
    clip["clip_prompt"] = "旧格式提示词，只有普通描述，没有固定架构。"
    clip["i2v_prompt"] = clip["clip_prompt"]
    clip["seedance_prompt"] = clip["clip_prompt"]
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    try:
        run_video_generation(
            {
                "mode": "run_video_generation",
                "provider": "poyo_video",
                "clip": clip,
                "dry_run": False,
                "image_urls": [{"url": "https://files.example/first.png", "role": "first_frame"}],
            },
            config,
        )
    except RuntimeError as exc:
        assert "Prompt Packet V1 is incomplete" in str(exc)
        assert "Global Context" in str(exc)
    else:
        raise AssertionError("live clip video should require Prompt Packet V1 sections")






def test_build_asset_manifest_template_includes_required_reference_ids():
    handoff = build_video_handoff(_task())
    manifest = build_asset_manifest_template(_task(), video_handoff=handoff)

    assert manifest["asset_manifest_version"] == "1.1"
    assert manifest["reference_policy"] == "all_purpose_reference"
    assert [ref["character_id"] for ref in manifest["character_references"]] == ["lin_que", "niu_tou"]
    assert manifest["scene_references"][0]["scene_id"] == "huangquan_hall_720"
    assert manifest["space_anchor_refs"][0]["scene_id"] == "huangquan_hall_720"
    assert manifest["storyboard_references"][0]["clip_id"] == "clip_001"
    assert manifest["storyboard_references"][0]["shot_ids"] == ["shot_001", "shot_002"]
    assert "character identity comes from character references" in manifest["notes"][2]



def test_scan_asset_manifest_directory_matches_locked_ids():
    with tempfile.TemporaryDirectory() as asset_dir:
        for filename in [
            "lin_que_character_reference.png",
            "niu_tou_identity_ref.jpg",
            "huangquan_hall_720_video_scene_reference.png",
            "huangquan_hall_720_panorama_space_anchor.png",
            "clip_001_storyboard_board.png",
            "random_unused.png",
        ]:
            with open(os.path.join(asset_dir, filename), "wb") as fh:
                fh.write(b"fake")

        handoff = build_video_handoff(_task())
        manifest = scan_asset_manifest_directory({**_task(), "asset_dir": asset_dir}, video_handoff=handoff)

    assert [ref["scan_status"] for ref in manifest["character_references"]] == ["matched", "matched"]
    assert manifest["scene_references"][0]["scan_status"] == "matched"
    assert manifest["space_anchor_refs"][0]["scan_status"] == "matched"
    assert manifest["storyboard_references"][0]["scan_status"] == "matched"
    assert manifest["character_references"][0]["character_id"] == "lin_que"
    assert manifest["scene_references"][0]["scene_id"] == "huangquan_hall_720"
    assert manifest["storyboard_references"][0]["clip_id"] == "clip_001"
    assert manifest["scan_report"]["matched_count"] == 5
    assert manifest["scan_report"]["missing_count"] == 0
    assert any(item["filename"] == "random_unused.png" for item in manifest["scan_report"]["unassigned_assets"])
    errors, warnings = validate_asset_manifest({"asset_manifest": manifest})
    assert errors == []
    assert any("fragile local user/download path" in warning for warning in warnings)


def test_scan_asset_manifest_directory_reports_missing_assets():
    with tempfile.TemporaryDirectory() as asset_dir:
        with open(os.path.join(asset_dir, "lin_que_character_reference.png"), "wb") as fh:
            fh.write(b"fake")
        manifest = scan_asset_manifest_directory({**_task(), "asset_dir": asset_dir}, video_handoff=build_video_handoff(_task()))

    assert manifest["scan_report"]["matched_count"] == 1
    assert manifest["scan_report"]["missing_count"] == 4
    assert any(item["character_id"] == "niu_tou" for item in manifest["scan_report"]["missing_references"])
    errors, _warnings = validate_asset_manifest({"asset_manifest": manifest})
    assert any("missing path/url" in error for error in errors)


def test_validate_asset_manifest_blocks_template_placeholders():
    manifest = build_asset_manifest_template(_task(), video_handoff=build_video_handoff(_task()))
    errors, _warnings = validate_asset_manifest({"asset_manifest": manifest})
    assert any("still has placeholder path/url" in error for error in errors)


def test_run_task_writes_asset_manifest_scan():
    with tempfile.TemporaryDirectory() as asset_dir, tempfile.TemporaryDirectory() as output_dir:
        for filename in [
            "lin_que_character_reference.png",
            "niu_tou_character_reference.png",
            "huangquan_hall_720_video_scene_reference.png",
            "huangquan_hall_720_panorama_space_anchor.png",
            "clip_001_storyboard_board.png",
        ]:
            with open(os.path.join(asset_dir, filename), "wb") as fh:
                fh.write(b"fake")
        result = run_task({**_task(), "mode": "scan_asset_manifest_directory", "asset_dir": asset_dir, "output_dir": output_dir})
        path = result["artifacts"][0]["path"]
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)

    assert result["handoff"]["asset_manifest"]["scan_report"]["missing_count"] == 0
    assert saved["character_references"][0]["scan_status"] == "matched"


def test_build_asset_manifest_review_groups_missing_and_unassigned_assets():
    with tempfile.TemporaryDirectory() as asset_dir:
        for filename in ["lin_que_character_reference.png", "random_unused.png"]:
            with open(os.path.join(asset_dir, filename), "wb") as fh:
                fh.write(b"fake")
        manifest = scan_asset_manifest_directory({**_task(), "asset_dir": asset_dir}, video_handoff=build_video_handoff(_task()))
        review = build_asset_manifest_review({"asset_manifest": manifest})

    assert review["status"] == "needs_assets"
    assert review["summary"]["matched_count"] == 1
    assert review["summary"]["missing_count"] == 4
    assert review["summary"]["unassigned_asset_count"] == 1
    assert any(item["action"] == "add_or_bind_asset_path" and item["identifier"] == "niu_tou" for item in review["action_items"])
    assert any(item["action"] == "review_unassigned_assets" for item in review["action_items"])
    assert review["groups"]["character_references"][0]["status"] == "matched"
    assert review["groups"]["character_references"][1]["status"] == "missing_path"


def test_build_asset_manifest_review_flags_placeholders():
    manifest = build_asset_manifest_template(_task(), video_handoff=build_video_handoff(_task()))
    review = build_asset_manifest_review({"asset_manifest": manifest})

    assert review["status"] == "needs_assets"
    assert review["summary"]["placeholder_count"] == 5
    assert any(item["action"] == "replace_placeholder_path" for item in review["action_items"])
    assert any("still has placeholder path/url" in error for error in review["errors"])


def test_run_task_writes_asset_manifest_review():
    with tempfile.TemporaryDirectory() as asset_dir, tempfile.TemporaryDirectory() as output_dir:
        with open(os.path.join(asset_dir, "lin_que_character_reference.png"), "wb") as fh:
            fh.write(b"fake")
        result = run_task({**_task(), "mode": "review_asset_manifest", "asset_dir": asset_dir, "output_dir": output_dir})
        path = result["artifacts"][0]["path"]
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)

    assert result["handoff"]["asset_manifest_review"]["status"] == "needs_assets"
    assert saved["summary"]["missing_count"] == 4

def test_validate_asset_manifest_requires_role_specific_ids():
    errors, warnings = validate_asset_manifest(
        {
            "asset_manifest": {
                "character_references": [{"url": "https://files.example/linque.png", "role": "character_reference"}],
                "scene_references": [{"url": "https://files.example/hall.png", "role": "video_scene_reference"}],
                "storyboard_references": [{"url": "https://files.example/board.png", "role": "storyboard_layout_reference"}],
                "space_anchor_refs": [{"url": "https://files.example/pano.png", "role": "space_anchor"}],
            }
        }
    )

    assert warnings == []
    assert any("character_reference missing character_id" in error for error in errors)
    assert any("video_scene_reference missing scene_id" in error for error in errors)
    assert any("storyboard_layout_reference missing clip_id" in error for error in errors)
    assert any("space_anchor missing scene_id" in error for error in errors)


def test_run_task_writes_asset_manifest_template():
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task({**_task(), "mode": "build_asset_manifest_template", "output_dir": output_dir})
        path = result["artifacts"][0]["path"]
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)

    assert result["handoff"]["asset_manifest_template"]["character_references"][0]["character_id"] == "lin_que"
    assert saved["storyboard_references"][0]["clip_id"] == "clip_001"

def test_prepare_video_generation_uses_asset_manifest_reference_order():
    handoff = build_video_handoff(_task())
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    request = prepare_video_generation_request(
        {
            "provider": "poyo_video",
            "video_handoff": handoff,
            "reference_policy": "all_purpose_reference",
            "asset_manifest": {
                "character_references": [
                    {"url": "https://files.example/linque.png", "role": "character_reference", "character_id": "lin_que"}
                ],
                "scene_references": [
                    {"url": "https://files.example/hall.png", "role": "video_scene_reference", "scene_id": "hall"}
                ],
                "storyboard_references": [
                    {"url": "https://files.example/board.png", "role": "storyboard_layout_reference", "clip_id": "clip_001"}
                ],
                "space_anchor_refs": [
                    {"url": "https://files.example/panorama.png", "role": "space_anchor", "scene_id": "hall"}
                ],
            },
            "clip_index": 1,
        },
        config,
    )
    assert request["image_urls"] == []
    assert [ref["role"] for ref in request["reference_image_urls"]] == [
        "character_reference",
        "video_scene_reference",
        "storyboard_layout_reference",
    ]
    assert [ref["role"] for ref in request["space_anchor_refs"]][-1] == "space_anchor"
    input_obj = request["transport"]["json"]["input"]
    assert "image_urls" not in input_obj
    assert input_obj["reference_image_urls"] == [
        "https://files.example/linque.png",
        "https://files.example/hall.png",
        "https://files.example/board.png",
    ]


def test_preflight_asset_manifest_warns_fragile_local_paths():
    handoff = build_video_handoff(_task())
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    report = preflight_video_generation(
        {
            "provider": "poyo_video",
            "video_handoff": handoff,
            "reference_policy": "all_purpose_reference",
            "asset_manifest": {
                "character_references": [
                    {"path": "C:\\Users\\qjw\\Downloads\\linque.png", "role": "character_reference", "character_id": "lin_que"},
                    {"url": "https://files.example/niutou.png", "role": "character_reference", "character_id": "niu_tou"},
                ],
                "scene_references": [{"url": "https://files.example/hall.png", "role": "video_scene_reference", "scene_id": "huangquan_hall_720"}],
                "storyboard_references": [{"url": "https://files.example/board.png", "role": "storyboard_layout_reference", "clip_id": "clip_001"}],
            },
            "clip_index": 1,
        },
        config,
    )
    assert report["status"] == "pass"
    assert any("fragile local user/download path" in warning for warning in report["warnings"])

def test_preflight_blocks_ambiguous_multi_character_reference_binding():
    handoff = build_video_handoff(_task())
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    report = preflight_video_generation(
        {
            "mode": "preflight_video_generation",
            "provider": "poyo_video",
            "video_handoff": handoff,
            "reference_policy": "all_purpose_reference",
            "reference_image_urls": [
                {"url": "https://files.example/one-character.jpg", "role": "character_reference"},
                {"url": "https://files.example/hall.jpg", "role": "video_scene_reference"},
                {"url": "https://files.example/storyboard.jpg", "role": "storyboard_layout_reference"},
            ],
            "max_clips": 1,
        },
        config,
    )
    assert report["status"] == "fail"
    assert any("character reference binding incomplete" in error for error in report["errors"])
    check = next(item for item in report["checks"] if item["name"] == "character_reference_bindings")
    assert check["status"] == "fail"
    assert check["detail"]["required_character_ids"] == ["lin_que", "niu_tou"]
    assert check["detail"]["ambiguous_character_reference_count"] == 1

def test_preflight_video_generation_passes_all_purpose_clip():
    handoff = build_video_handoff(_task())
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    report = preflight_video_generation(
        {
            "mode": "preflight_video_generation",
            "provider": "poyo_video",
            "video_handoff": handoff,
            "reference_policy": "all_purpose_reference",
            "reference_image_urls": [
                {"url": "https://files.example/linque.jpg", "role": "character_reference", "character_id": "lin_que"},
                {"url": "https://files.example/niutou.jpg", "role": "character_reference", "character_id": "niu_tou"},
                {"url": "https://files.example/hall.jpg", "role": "video_scene_reference"},
                {"url": "https://files.example/storyboard.jpg", "role": "storyboard_layout_reference"},
            ],
            "max_clips": 1,
        },
        config,
    )
    assert report["status"] == "pass"
    assert report["checked_count"] == 1
    assert not report["errors"]
    assert any(item["name"] == "all_purpose_reference_urls" and item["status"] == "pass" for item in report["checks"])
    assert any(item["name"] == "prompt_packet_v1" and item["status"] == "pass" for item in report["checks"])




def test_preflight_video_generation_respects_clip_index():
    task = copy.deepcopy(_task())
    task["target_clip_duration_sec"] = 5
    task["blueprint"]["segments"] = [
        {"index": 1, "start_sec": 0, "end_sec": 5, "visual": "林缺在柜台前检查菜单账本。"},
        {"index": 2, "start_sec": 5, "end_sec": 10, "visual": "牛头从厨房门后端着托盘走出。"},
    ]
    handoff = build_video_handoff(task)
    assert len(handoff["clip_plan"]) == 2
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    report = preflight_video_generation(
        {
            "mode": "preflight_video_generation",
            "provider": "poyo_video",
            "video_handoff": handoff,
            "clip_index": 2,
            "reference_policy": "all_purpose_reference",
            "reference_image_urls": [{"url": "https://files.example/linque.jpg", "role": "character_reference"}],
        },
        config,
    )
    assert report["checked_count"] == 1
    assert all(item["unit"] == "clip_002" for item in report["checks"])

def test_preflight_video_generation_blocks_old_prompt_packet():
    handoff = build_video_handoff(_task())
    clip = copy.deepcopy(handoff["clip_plan"][0])
    clip["clip_prompt"] = "旧格式提示词，只有普通描述，没有固定架构。"
    clip["i2v_prompt"] = clip["clip_prompt"]
    clip["seedance_prompt"] = clip["clip_prompt"]
    config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
    report = preflight_video_generation(
        {
            "mode": "preflight_video_generation",
            "provider": "poyo_video",
            "clip": clip,
            "image_urls": [{"url": "https://files.example/first.png", "role": "first_frame"}],
        },
        config,
    )
    assert report["status"] == "fail"
    assert any("Prompt Packet V1 missing sections" in error for error in report["errors"])


def test_run_task_writes_preflight_report():
    handoff = build_video_handoff(_task())
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_task(
            {
                "mode": "preflight_video_generation",
                "provider": "poyo_video",
                "video_handoff": handoff,
                "reference_policy": "all_purpose_reference",
                "reference_image_urls": [{"url": "https://files.example/linque.jpg", "role": "character_reference"}],
                "max_clips": 1,
                "output_dir": output_dir,
            }
        )
        path = result["artifacts"][0]["path"]
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
    assert saved["mode"] == "preflight_video_generation"
    assert saved["checked_count"] == 1


def test_live_video_all_purpose_reference_passes_with_fake_client():
    handoff = build_video_handoff(_task())
    captured = {}

    class FakePoYoVideoClient:
        def __init__(self, config):
            self.config = config

        def run_seedance2(self, request, output_dir="", callback_url=None, download=True):
            captured["request"] = request
            captured["output_dir"] = output_dir
            captured["callback_url"] = callback_url
            captured["download"] = download
            return {"task_id": "fake_task", "credits_amount": 0, "local_paths": []}

    original_client = video_provider.PoYoVideoClient
    video_provider.PoYoVideoClient = FakePoYoVideoClient
    try:
        config = VideoProviderConfig("poyo_video", "test", "https://api.example", "", "seedance-2", "9:16", "480p", 1, 5)
        result = run_video_generation(
            {
                "mode": "run_video_generation",
                "provider": "poyo_video",
                "video_handoff": handoff,
                "reference_policy": "all_purpose_reference",
                "reference_image_urls": [
                    {"url": "https://files.example/linque.jpg", "role": "character_reference", "character_id": "lin_que"},
                    {"url": "https://files.example/niutou.jpg", "role": "character_reference", "character_id": "niu_tou"},
                    {"url": "https://files.example/hall.jpg", "role": "video_scene_reference"},
                    {"url": "https://files.example/storyboard.jpg", "role": "storyboard_layout_reference"},
                ],
                "clip_index": 1,
                "dry_run": False,
                "download": False,
            },
            config,
        )
    finally:
        video_provider.PoYoVideoClient = original_client

    assert result["status"] == "success"
    assert result["dry_run"] is False
    request = captured["request"]
    assert request["image_urls"] == []
    assert [ref["role"] for ref in request["reference_image_urls"]] == [
        "character_reference",
        "character_reference",
        "video_scene_reference",
        "storyboard_layout_reference",
    ]
    assert "全能参考模式已锁定" in request["prompt"]
    assert request["transport"]["json"]["model"] == "seedance-2"
if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
