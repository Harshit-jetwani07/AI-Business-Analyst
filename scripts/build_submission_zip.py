from __future__ import annotations

import fnmatch
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "submission_assets"
ZIP_PATH = OUTPUT_DIR / "AI_Business_Analyst_safe_submission.zip"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
}

EXCLUDE_PATTERNS = [
    ".env",
    "*.pyc",
    "*.pyo",
    "data/*.db",
    "uploads/*",
    "reports/*",
    "exports/*",
    "submission_assets/*.zip",
]

KEEP_FILES = {
    "uploads/.gitkeep",
    "reports/.gitkeep",
    "exports/.gitkeep",
}


def should_exclude(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if any(part in EXCLUDE_DIRS for part in path.relative_to(ROOT).parts):
        return True
    if rel in KEEP_FILES:
        return False
    return any(fnmatch.fnmatch(rel, pattern) for pattern in EXCLUDE_PATTERNS)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_dir() or should_exclude(path):
                continue
            zf.write(path, path.relative_to(ROOT).as_posix())

    print(f"Created {ZIP_PATH}")


if __name__ == "__main__":
    main()
