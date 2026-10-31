"""
Deploy FinSight to a Hugging Face Space (Docker SDK).

    HF_TOKEN=hf_... python demo/hf_space/deploy.py --space <user>/finsight
    python demo/hf_space/deploy.py --space <user>/finsight --dry-run   # stage only

Uploads only what the container needs (Dockerfile, src/, api/, requirements,
licence) plus the Space README with its YAML header. Stale files under src/
and api/ are removed, so the Space runs exactly this repo's code. Secrets (ANTHROPIC_API_KEY) are never uploaded; set them in the
Space settings.
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
APP_FILES = ["Dockerfile", ".dockerignore", "requirements.txt", "LICENSE"]
APP_DIRS = ["src", "api"]
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")

# Space variables (not secrets): a public endpoint gets a per-client ask limit.
SPACE_VARIABLES = {"FINSIGHT_ASK_PER_MIN": "20"}


def stage(dest: Path) -> list[str]:
    for f in APP_FILES:
        shutil.copy(ROOT / f, dest / f)
    for d in APP_DIRS:
        shutil.copytree(ROOT / d, dest / d, ignore=IGNORE)
    shutil.copy(HERE / "README.md", dest / "README.md")
    return sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--space", default=os.environ.get("HF_SPACE"), help="<owner>/<space-name>")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.space:
        ap.error("--space or HF_SPACE is required, e.g. sachinnarayanan/finsight")

    with tempfile.TemporaryDirectory() as tmp:
        files = stage(Path(tmp))
        print(f"staged {len(files)} files for {args.space}")
        if args.dry_run:
            print("\n".join(f"  {f}" for f in files))
            return

        from huggingface_hub import HfApi

        token = os.environ.get("HF_TOKEN")
        if not token:
            raise SystemExit("HF_TOKEN is not set (needs a write token from huggingface.co/settings/tokens)")
        api = HfApi(token=token)
        api.create_repo(args.space, repo_type="space", space_sdk="docker", exist_ok=True)
        for key, value in SPACE_VARIABLES.items():
            api.add_space_variable(args.space, key, value)
        api.upload_folder(
            repo_id=args.space, repo_type="space", folder_path=tmp,
            commit_message="Deploy FinSight from GitHub",
            delete_patterns=["src/**", "api/**"],   # drop stale app files; keep .gitattributes
        )
        print(f"deployed -> https://huggingface.co/spaces/{args.space}")


if __name__ == "__main__":
    main()
