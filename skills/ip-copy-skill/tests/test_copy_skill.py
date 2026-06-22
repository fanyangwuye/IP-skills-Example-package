import os
import sys
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
    output_dir = os.path.join(os.getcwd(), "tmp_copy_skill_test")
    os.makedirs(output_dir, exist_ok=True)
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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")

