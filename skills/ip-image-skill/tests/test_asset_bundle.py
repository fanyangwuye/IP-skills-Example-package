import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from character_sheet import build_asset_bundle_tasks  # noqa: E402


def test_build_asset_bundle_tasks():
    sheet = {
        "character_profile": {
            "identity": {"name": "Lin Yue"},
        },
        "identity_anchors": ["same face"],
        "continuity_rules": ["keep identity stable"],
        "interaction_state": {"locked_traits": ["face"]},
        "asset_target": {},
    }
    bundle = [
        {
            "label": "hero_portrait",
            "filename": "hero_portrait.jpg",
            "asset_target": {"type": "hero portrait", "framing": "waist-up"},
            "camera": "waist-up portrait",
        },
        {
            "label": "full_body_turnaround",
            "asset_target": {"type": "full body", "purpose": "costume direction"},
            "camera": "full body front view",
        },
    ]
    tasks = build_asset_bundle_tasks(
        sheet,
        output_dir="out",
        asset_bundle=bundle,
        common_fields={"ip_id": "demo_ip", "quality": "high"},
    )
    assert len(tasks) == 2
    assert tasks[0]["bundle_item_label"] == "hero_portrait"
    assert tasks[0]["asset_target"]["type"] == "hero portrait"
    assert tasks[0]["ip_id"] == "demo_ip"
    assert tasks[1]["bundle_item_label"] == "full_body_turnaround"
    assert tasks[1]["filename"] == "full_body_turnaround.jpg"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
