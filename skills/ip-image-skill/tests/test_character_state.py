import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from character_sheet import empty_character_sheet  # noqa: E402
from character_state import run_character_state  # noqa: E402


def test_run_character_state():
    sheet = empty_character_sheet("Lin Yue")
    update = {
        "character_profile": {
            "appearance": {"hair": "long dark hair"},
        },
        "identity_anchors": ["same face"],
        "locked_traits": ["face"],
    }
    result = run_character_state(sheet, update)
    assert result["updated_sheet"]["character_profile"]["appearance"]["hair"] == "long dark hair"
    assert "same face" in result["updated_sheet"]["identity_anchors"]
    assert "summary" in result


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
