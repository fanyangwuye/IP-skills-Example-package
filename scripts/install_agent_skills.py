import argparse
import os
import shutil
from pathlib import Path


SKILL_NAMES = [
    "ip-copy-skill",
    "ip-image-skill",
    "ip-music-skill",
    "ip-video-skill",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_codex_skills_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "skills"
    return Path.home() / ".codex" / "skills"


def copy_skill(src: Path, dst: Path, force: bool, dry_run: bool) -> str:
    if not (src / "SKILL.md").exists():
        raise FileNotFoundError(f"Missing SKILL.md: {src}")
    if dst.exists():
        if not force:
            return f"skip existing {dst}"
        if dry_run:
            return f"would replace {dst}"
        shutil.rmtree(dst)
    if dry_run:
        return f"would install {src} -> {dst}"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
    return f"installed {src.name} -> {dst}"


def install(target: Path, force: bool, dry_run: bool) -> list[str]:
    root = repo_root()
    source_root = root / "skills"
    if not source_root.exists():
        raise FileNotFoundError(source_root)
    messages = []
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)
    for name in SKILL_NAMES:
        messages.append(copy_skill(source_root / name, target / name, force=force, dry_run=dry_run))
    return messages


def main() -> None:
    parser = argparse.ArgumentParser(description="Install IP skills into an agent skills directory.")
    parser.add_argument(
        "--target",
        default=str(default_codex_skills_dir()),
        help="Skills directory to install into. Defaults to CODEX_HOME/skills or ~/.codex/skills.",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing installed copies.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be installed without writing files.")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    for message in install(target=target, force=args.force, dry_run=args.dry_run):
        print(message)
    print(f"target={target}")


if __name__ == "__main__":
    main()
