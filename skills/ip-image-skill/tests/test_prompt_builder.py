import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from prompt_builder import build_image_prompt, build_task_prompt, load_style_card  # noqa: E402


def test_build_prompt_without_style_card():
    prompt = build_image_prompt("simple portrait")
    assert prompt == "simple portrait"


def test_build_prompt_with_style_card():
    card = {
        "style_direction": "cinematic",
        "primary_palette": "blue gold",
        "character_anchors": ["heroine", "long dark hair"],
        "positive_prompt_fragments": ["consistent face"],
        "forbidden_elements": ["duplicate face"],
        "negative_prompt_fragments": ["blurry eyes"],
    }
    prompt = build_image_prompt("rain portrait", card)
    assert "Style direction: cinematic" in prompt
    assert "Primary palette: blue gold" in prompt
    assert "rain portrait" in prompt
    assert "Avoid: duplicate face" in prompt


def test_load_style_card_from_path():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "card.json")
        payload = {"style_direction": "test"}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        loaded = load_style_card(style_card_path=path)
        assert loaded["style_direction"] == "test"


def test_load_style_card_from_builtin_preset():
    loaded = load_style_card(style_preset="realistic_short_drama")
    assert "short-drama" in loaded["style_direction"]
    assert "AI-looking face" in loaded["negative_prompt_fragments"]


def test_style_preset_merges_with_project_card():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "card.json")
        payload = {
            "style_direction": "project style",
            "positive_prompt_fragments": ["project-specific wardrobe"],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        loaded = load_style_card(style_card_path=path, style_preset="realistic_short_drama")
        assert loaded["style_direction"] == "project style"
        assert "realistic actor portrait" in loaded["positive_prompt_fragments"]
        assert "project-specific wardrobe" in loaded["positive_prompt_fragments"]


def test_style_preset_does_not_auto_merge_ip_card():
    loaded = load_style_card(ip_id="demo_ip", style_preset="realistic_short_drama")
    assert "short-drama" in loaded["style_direction"]
    assert "young East Asian heroine" not in loaded.get("character_anchors", [])


def test_build_task_prompt_for_novel_character_creation():
    task = {
        "asset_kind": "character_portrait",
        "creative_goal": "Create the lead heroine from the novel excerpt",
        "character_name": "Lin Yue",
        "source_text": "Lin Yue stepped out of the rainy station in a dark coat, calm but alert.",
        "appearance_traits": ["East Asian", "calm eyes", "dark long hair"],
        "scene": "rainy station exit at night",
        "emotion": "calm vigilance",
        "prompt": "premium cinematic portrait"
    }
    prompt = build_task_prompt(task)
    assert "Character name: Lin Yue" in prompt
    assert "Source text for extraction and visual adaptation:" in prompt
    assert "Asset kind: character_portrait" in prompt


def test_build_task_prompt_for_interactive_single_image():
    task = {
        "asset_kind": "single_character_image",
        "prompt": "Create the character image",
        "interaction_notes": ["keep the face softer", "change outfit to deep blue"],
        "conversation_turns": [
            {"role": "user", "content": "make her feel more mysterious"},
            {"role": "user", "content": "keep the same identity and face"}
        ]
    }
    prompt = build_task_prompt(task)
    assert "Interaction refinements:" in prompt
    assert "Conversation cues:" in prompt
    assert "make her feel more mysterious" in prompt


def test_build_task_prompt_for_character_sheet_structure():
    task = {
        "mode": "character_create",
        "creation_stage": "character_creation",
        "current_focus": "lock face and costume direction",
        "character_profile": {
            "identity": {"name": "Lin Yue", "role": "lead heroine"},
            "appearance": {"ethnicity": "East Asian", "hair": "long dark hair"},
            "personality": {"aura": "calm vigilance"}
        },
        "identity_anchors": ["same face", "same hairline", "same eye shape"],
        "continuity_rules": ["do not drift from the established identity"],
        "asset_target": {
            "type": "hero portrait",
            "framing": "waist-up",
            "purpose": "key visual"
        },
        "interaction_state": {
            "locked_traits": ["face", "hair"],
            "latest_user_direction": "make the wardrobe more premium"
        }
    }
    prompt = build_task_prompt(task)
    assert "Character profile:" in prompt
    assert "Identity anchors:" in prompt
    assert "Asset target:" in prompt
    assert "Interaction state:" in prompt


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
