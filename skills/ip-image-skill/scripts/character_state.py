import argparse
import json
import os

try:
    from .character_sheet import apply_character_turn, summarize_character_sheet
except ImportError:
    from character_sheet import apply_character_turn, summarize_character_sheet


def run_character_state(sheet: dict, turn_update: dict) -> dict:
    updated_sheet = apply_character_turn(sheet, turn_update)
    return {
        "updated_sheet": updated_sheet,
        "summary": summarize_character_sheet(updated_sheet),
    }


def _cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet", required=True, help="Path to the current character sheet JSON")
    parser.add_argument("--update", required=True, help="Path to the current turn update JSON")
    parser.add_argument("--out", help="Optional output path for the updated character sheet JSON")
    args = parser.parse_args()

    with open(args.sheet, "r", encoding="utf-8") as fh:
        sheet = json.load(fh)
    with open(args.update, "r", encoding="utf-8") as fh:
        turn_update = json.load(fh)

    result = run_character_state(sheet, turn_update)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result["updated_sheet"], fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    _cli()
