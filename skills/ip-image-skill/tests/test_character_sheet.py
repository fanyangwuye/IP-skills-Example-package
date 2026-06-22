import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from character_sheet import apply_character_turn, build_task_from_character_sheet, empty_character_sheet, merge_character_sheet, suggest_next_questions, summarize_character_sheet  # noqa: E402


def test_empty_character_sheet():
    sheet = empty_character_sheet("Lin Yue")
    assert sheet["character_profile"]["identity"]["name"] == "Lin Yue"
    assert sheet["interaction_state"]["decision_log"] == []


def test_merge_character_sheet():
    base = empty_character_sheet("Lin Yue")
    update = {
        "character_profile": {
            "appearance": {"hair": "long dark hair"},
        },
        "identity_anchors": ["same face"],
        "interaction_state": {
            "locked_traits": ["face"],
        },
    }
    merged = merge_character_sheet(base, update)
    assert merged["character_profile"]["appearance"]["hair"] == "long dark hair"
    assert "same face" in merged["identity_anchors"]
    assert "face" in merged["interaction_state"]["locked_traits"]


def test_build_task_from_character_sheet():
    sheet = empty_character_sheet("Lin Yue")
    sheet["asset_target"] = {"type": "hero portrait"}
    task = build_task_from_character_sheet(
        sheet,
        output_dir="out",
        extra_task_fields={"ip_id": "demo_ip", "quality": "high"},
    )
    assert task["mode"] == "character_create"
    assert task["character_profile"]["identity"]["name"] == "Lin Yue"
    assert task["asset_target"]["type"] == "hero portrait"
    assert task["ip_id"] == "demo_ip"


def test_apply_character_turn():
    sheet = empty_character_sheet("Lin Yue")
    update = {
        "character_profile": {
            "appearance": {"hair": "long dark hair"},
            "personality": {"aura": "calm vigilance"},
        },
        "identity_anchors": ["same face"],
        "locked_traits": ["face"],
        "latest_user_direction": "keep her restrained",
        "decision_log": ["locked the face"],
        "pending_questions": ["这一轮你想先生成什么资产？例如头像、半身、全身、服装图。"],
    }
    updated = apply_character_turn(sheet, update)
    assert updated["character_profile"]["appearance"]["hair"] == "long dark hair"
    assert "same face" in updated["identity_anchors"]
    assert "face" in updated["interaction_state"]["locked_traits"]
    assert updated["interaction_state"]["latest_user_direction"] == "keep her restrained"


def test_suggest_next_questions():
    sheet = empty_character_sheet("Lin Yue")
    questions = suggest_next_questions(sheet, max_questions=2)
    assert len(questions) == 2
    assert all(isinstance(item, str) and item for item in questions)


def test_summarize_character_sheet():
    sheet = empty_character_sheet("Lin Yue")
    sheet["character_profile"]["appearance"]["hair"] = "long dark hair"
    summary = summarize_character_sheet(sheet)
    assert summary["identity"]["name"] == "Lin Yue"
    assert "missing_fields" in summary
    assert "next_questions" in summary


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
