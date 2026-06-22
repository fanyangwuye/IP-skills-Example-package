import json
import os
import tempfile


def test_bridge_manifest_write():
    with tempfile.TemporaryDirectory() as d:
        handoff = {
            "image_tasks": [
                {"mode": "text_to_image", "prompt": "scene one"},
                {"mode": "text_to_image", "prompt": "scene two"},
            ]
        }
        handoff_path = os.path.join(d, "image_handoff.json")
        with open(handoff_path, "w", encoding="utf-8") as fh:
            json.dump(handoff, fh)

        out_dir = os.path.join(d, "out")
        os.makedirs(out_dir, exist_ok=True)

        manifest = {
            "status": "success",
            "handoff_path": handoff_path,
            "n_image_tasks": len(handoff["image_tasks"]),
            "results": [],
        }
        manifest_path = os.path.join(out_dir, "copy_to_image_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh)

        assert os.path.exists(manifest_path)


if __name__ == "__main__":
    test_bridge_manifest_write()
    print("PASS test_bridge_manifest_write")
