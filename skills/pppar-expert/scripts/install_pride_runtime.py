from __future__ import annotations

import argparse
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


def find_repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError("unable to locate repository root from script path")


REPO_ROOT = find_repo_root()
DEFAULT_PREFIX = REPO_ROOT / "tools" / "PRIDE"
DEFAULT_TARBALL = REPO_ROOT / "vendor" / "PRIDE-PPPAR-master.tar.gz"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install the standalone PRIDE-PPPAR runtime")
    parser.add_argument("--prefix", default=str(DEFAULT_PREFIX), help="installation prefix")
    parser.add_argument("--tarball", default=str(DEFAULT_TARBALL), help="local PRIDE-PPPAR source tarball")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    prefix = Path(args.prefix).expanduser().resolve()
    tarball = Path(args.tarball).expanduser().resolve()

    if not tarball.exists():
        raise RuntimeError(f"tarball not found: {tarball}")

    ensure_build_tools()

    src_dir = prefix / "src"
    runtime_dir = prefix / "runtime"
    env_file = prefix / "env.sh"
    build_root = prefix / "build"

    prefix.mkdir(parents=True, exist_ok=True)
    build_root.mkdir(parents=True, exist_ok=True)

    extract_tarball(tarball, src_dir, build_root)
    make_executables(src_dir / "src")
    chmod_helpers(src_dir / "scripts")
    ensure_latest_igs20_atx(src_dir / "table")
    prepare_runtime(src_dir, runtime_dir)
    write_env_file(env_file, runtime_dir, src_dir)

    print(f"installed PRIDE-PPPAR under {prefix}")
    print(f"source:   {src_dir}")
    print(f"runtime:  {runtime_dir}")
    print(f"env file: {env_file}")
    print("")
    print(f"source {env_file}")
    print("./.venv/bin/python .codex/skills/pride-pppar-expert/scripts/check_pride_runtime.py")



def ensure_build_tools() -> None:
    for tool in ("gfortran", "gcc", "make"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"required build tool not found: {tool}")



def extract_tarball(tarball_path: Path, src_dir: Path, build_root: Path) -> None:
    if src_dir.exists():
        shutil.rmtree(src_dir)
    with tempfile.TemporaryDirectory(dir=build_root) as temp_dir:
        temp_path = Path(temp_dir)
        with tarfile.open(tarball_path, "r:gz") as archive:
            archive.extractall(temp_path)
        extracted = temp_path / "PRIDE-PPPAR-master"
        if not extracted.exists():
            raise RuntimeError(f"expected extracted directory not found: {extracted}")
        shutil.move(str(extracted), str(src_dir))



def make_executables(src_subdir: Path) -> None:
    run_command(["make", "clean"], cwd=src_subdir)
    run_command(["make"], cwd=src_subdir)
    run_command(["make", "install"], cwd=src_subdir)



def chmod_helpers(scripts_dir: Path) -> None:
    for pattern in ("*.py", "*.sh"):
        for helper in scripts_dir.glob(pattern):
            helper.chmod(0o755)



def ensure_latest_igs20_atx(table_dir: Path) -> None:
    igs20_files = sorted(table_dir.glob("igs20_*.atx"))
    if not igs20_files:
        raise RuntimeError(f"no igs20 ANTEX files found in {table_dir}")
    expected = table_dir / "igs20_2388.atx"
    if not expected.exists():
        shutil.copy2(igs20_files[-1], expected)



def prepare_runtime(src_dir: Path, runtime_dir: Path) -> None:
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_dir / "scripts" / "pdp3.sh", runtime_dir / "pdp3")
    shutil.copy2(src_dir / "table" / "config_template", runtime_dir / "config_template")
    (runtime_dir / "pdp3").chmod(0o755)



def write_env_file(path: Path, runtime_dir: Path, src_dir: Path) -> None:
    executable = runtime_dir / "pdp3"
    table_dir = src_dir / "table"
    bin_dir = src_dir / "bin"
    scripts_dir = src_dir / "scripts"
    path.write_text(
        "\n".join(
            [
                f'export PPP_FLOAT_PRIDE_EXECUTABLE="{executable}"',
                f'export PPP_FLOAT_PRIDE_TABLE_DIR="{table_dir}"',
                f'export PPP_FLOAT_PRIDE_BIN_DIR="{bin_dir}"',
                f'export PPP_FLOAT_PRIDE_SCRIPT_DIR="{scripts_dir}"',
                'export PATH="$(dirname "$PPP_FLOAT_PRIDE_EXECUTABLE"):$PPP_FLOAT_PRIDE_BIN_DIR:$PPP_FLOAT_PRIDE_SCRIPT_DIR:$PATH"',
                "",
            ]
        ),
        encoding="utf-8",
    )



def run_command(argv: list[str], cwd: Path) -> None:
    completed = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(argv)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


if __name__ == "__main__":
    main()
