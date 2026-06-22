import json
import os

try:
    from .config import default_output_root, load_image_provider_config, project_root, skill_root
except ImportError:
    from config import default_output_root, load_image_provider_config, project_root, skill_root


def run_doctor() -> dict:
    config = load_image_provider_config()
    os.makedirs(config.output_root, exist_ok=True)

    result = {
        "status": "ok",
        "project_root": project_root(),
        "skill_root": skill_root(),
        "provider": config.provider,
        "api_base": config.api_base,
        "gen_model": config.gen_model,
        "edit_model": config.edit_model,
        "output_root": config.output_root,
        "using_default_output_root": os.path.normcase(config.output_root) == os.path.normcase(default_output_root()),
        "checks": {
            "api_key_present": bool(config.api_key),
            "output_root_exists": os.path.isdir(config.output_root),
        },
    }
    return result


if __name__ == "__main__":
    print(json.dumps(run_doctor(), ensure_ascii=False, indent=2))

