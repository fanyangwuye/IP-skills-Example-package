import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from setup_doctor import run_checks  # noqa: E402


def _which_none(_name):
    return None


def _which_some(name):
    return f"/usr/bin/{name}"


def _by_name(report, name):
    for check in report["checks"]:
        if check["name"] == name:
            return check
    raise AssertionError(name)


def test_setup_doctor_warns_without_keys_or_ffmpeg():
    report = run_checks(env={"VIDEO_PROVIDER": "dreamina_cli"}, which=_which_none)
    assert report["status"] == "warn"
    assert _by_name(report, "poyo.image_key")["status"] == "warn"
    assert _by_name(report, "poyo.music_key")["status"] == "warn"
    assert _by_name(report, "ffmpeg.binary")["status"] == "warn"
    assert _by_name(report, "dreamina.provider")["status"] == "warn"
    assert any("Dreamina CLI" in step for step in report["next_steps"])


def test_setup_doctor_accepts_shared_poyo_key_and_tools():
    report = run_checks(
        env={
            "POYO_API_KEY": "test",
            "VIDEO_PROVIDER": "dreamina_cli",
            "IMAGE_OUTPUT_ROOT": os.getcwd(),
            "MUSIC_OUTPUT_ROOT": os.getcwd(),
            "VIDEO_OUTPUT_ROOT": os.getcwd(),
        },
        which=_which_some,
    )
    assert report["status"] == "pass"
    assert _by_name(report, "poyo.image_key")["status"] == "pass"
    assert _by_name(report, "poyo.music_key")["status"] == "pass"
    assert _by_name(report, "dreamina.provider")["status"] == "pass"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all passed")
