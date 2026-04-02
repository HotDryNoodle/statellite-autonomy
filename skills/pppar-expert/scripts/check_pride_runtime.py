from __future__ import annotations

import argparse
import os
from pathlib import Path


def find_repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError("unable to locate repository root from script path")


REPO_ROOT = find_repo_root()
DEFAULT_PREFIX = REPO_ROOT / "tools" / "PRIDE"
MANUAL_ZH = REPO_ROOT / "tools" / "PRIDE" / "src" / "doc" / "PRIDE PPP-AR v3.2 manual-ch.pdf"
MANUAL_EN = REPO_ROOT / "tools" / "PRIDE" / "src" / "doc" / "PRIDE PPP-AR v3.2 manual-en.pdf"



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check the standalone PRIDE-PPPAR runtime")
    parser.add_argument("--prefix", default=str(DEFAULT_PREFIX), help="installation prefix")
    return parser



def main() -> None:
    args = build_parser().parse_args()
    prefix = Path(args.prefix).expanduser().resolve()
    src_dir = prefix / "src"
    runtime_dir = prefix / "runtime"
    env_file = prefix / "env.sh"

    checks = [
        ("prefix", prefix.exists(), prefix),
        ("source tree", src_dir.exists(), src_dir),
        ("runtime dir", runtime_dir.exists(), runtime_dir),
        ("runtime executable", (runtime_dir / "pdp3").exists(), runtime_dir / "pdp3"),
        ("runtime config", (runtime_dir / "config_template").exists(), runtime_dir / "config_template"),
        ("bin dir", (src_dir / "bin").exists(), src_dir / "bin"),
        ("scripts dir", (src_dir / "scripts").exists(), src_dir / "scripts"),
        ("table dir", (src_dir / "table").exists(), src_dir / "table"),
        ("env file", env_file.exists(), env_file),
        ("manual zh", MANUAL_ZH.exists(), MANUAL_ZH),
        ("manual en", MANUAL_EN.exists(), MANUAL_EN),
    ]

    failed = False
    for label, ok, path in checks:
        status = "OK" if ok else "MISSING"
        print(f"[{status}] {label}: {path}")
        failed = failed or not ok

    print("")
    print("Environment overrides:")
    for key in (
        "PPP_FLOAT_PRIDE_EXECUTABLE",
        "PPP_FLOAT_PRIDE_TABLE_DIR",
        "PPP_FLOAT_PRIDE_BIN_DIR",
        "PPP_FLOAT_PRIDE_SCRIPT_DIR",
    ):
        print(f"- {key}={os.environ.get(key, '')}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
