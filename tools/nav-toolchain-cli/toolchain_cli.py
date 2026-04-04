#!/usr/bin/env python3
"""Meson toolchain entrypoints for local and cross builds."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILD_DIR = REPO_ROOT / "builddir"
TRACE_OUTPUT_DIR = REPO_ROOT / "docs" / "_generated" / "traceability"
SCENARIO_DIR = REPO_ROOT / "eval" / "scenarios"
BASELINE_DIR = REPO_ROOT / "eval" / "baselines"
CLI_PATH = "python3 tools/nav-toolchain-cli/toolchain_cli.py"


class HelpFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    """Formatter that keeps example blocks readable and shows defaults."""


def print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def shell_join(cmd: list[str]) -> str:
    return shlex.join(cmd)


def run(cmd: list[str]) -> int:
    completed = subprocess.run(cmd, cwd=REPO_ROOT)
    return completed.returncode


def run_capture(cmd: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()
    if completed.stderr.strip():
        output = (output + "\n" + completed.stderr.strip()).strip()
    return completed.returncode, output


def run_quiet(cmd: list[str]) -> int:
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        if completed.stdout.strip():
            print(completed.stdout.strip())
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
    return completed.returncode


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def benchmark_binary(build_dir: Path) -> Path:
    return build_dir / "product" / "tests" / "time_benchmark"


def benchmark_report_path(args: argparse.Namespace) -> Path:
    report = Path(args.report_path)
    if not report.is_absolute():
        report = REPO_ROOT / report
    return report


def maybe_warn_overwrite(path: Path, yes: bool) -> None:
    if path.exists() and not yes:
        print(
            (
                f"warning: overwriting existing file: {path}\n"
                f"hint: rerun with --yes to acknowledge the overwrite explicitly."
            ),
            file=sys.stderr,
        )


def emit_dry_run(command_name: str,
                 commands: list[list[str]],
                 writes: list[str] | None = None,
                 notes: list[str] | None = None) -> int:
    payload = {
        "command": command_name,
        "dry_run": True,
        "commands": [shell_join(cmd) for cmd in commands],
        "writes": writes or [],
        "notes": notes or [],
    }
    print_json(payload)
    return 0


def setup_command(args: argparse.Namespace) -> list[str]:
    build_dir = Path(args.build_dir)
    cmd = ["meson", "setup", str(build_dir)]
    if build_dir.exists():
        cmd.append("--reconfigure")
    if args.reconfigure and "--reconfigure" not in cmd:
        cmd.append("--reconfigure")
    if args.cross_file:
        cmd += ["--cross-file", args.cross_file]
    if args.native_file:
        cmd += ["--native-file", args.native_file]
    for item in args.meson_option:
        cmd.append(f"-D{item}")
    return cmd


def setup_required(args: argparse.Namespace) -> bool:
    build_dir = Path(args.build_dir)
    return not (
        build_dir.exists()
        and not args.reconfigure
        and not args.cross_file
        and not args.native_file
        and not args.meson_option
    )


def ensure_builddir(args: argparse.Namespace) -> int:
    if not setup_required(args):
        return 0
    return run(setup_command(args))


def common_command_preview(args: argparse.Namespace, final_cmd: list[str]) -> list[list[str]]:
    commands: list[list[str]] = []
    if setup_required(args):
        commands.append(setup_command(args))
    commands.append(final_cmd)
    return commands


def traceability_commands(output_dir: Path) -> list[list[str]]:
    return [
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "traceability-cli" / "gen_contract_index.py"),
            "--output",
            str(output_dir / "contract_index.json"),
        ],
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "traceability-cli" / "gen_trace.py"),
            "--output-dir",
            str(output_dir),
        ],
    ]


def run_benchmark_scenario(binary: Path, scenario: dict) -> dict:
    kind = scenario["kind"]
    command = [str(binary), "--kind", kind]

    if kind == "roundtrip":
        civil = scenario["civil_time"]
        command += [
            "--year", str(civil["year"]),
            "--month", str(civil["month"]),
            "--day", str(civil["day"]),
            "--hour", str(civil["hour"]),
            "--minute", str(civil["min"]),
            "--second", str(civil["sec"]),
            "--iterations", str(scenario["iterations"]),
            "--leap-file", str(REPO_ROOT / scenario["leap_seconds"]),
        ]
    elif kind == "leap_second_boundary":
        command += [
            "--iterations", str(scenario["iterations"]),
            "--leap-file", str(REPO_ROOT / scenario["leap_seconds"]),
        ]
    elif kind == "ut1_dependency":
        civil = scenario["civil_time"]
        command += [
            "--year", str(civil["year"]),
            "--month", str(civil["month"]),
            "--day", str(civil["day"]),
            "--hour", str(civil["hour"]),
            "--minute", str(civil["min"]),
            "--second", str(civil["sec"]),
            "--iterations", str(scenario["iterations"]),
            "--ut1-minus-utc", str(scenario["ut1_minus_utc_seconds"]),
            "--leap-file", str(REPO_ROOT / scenario["leap_seconds"]),
        ]
    elif kind == "invalid_inputs":
        command += ["--iterations", str(scenario["iterations"])]
    else:
        raise ValueError(f"Unsupported benchmark scenario kind: {kind}")

    started = time.perf_counter()
    return_code, output = run_capture(command)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if return_code != 0:
        raise RuntimeError(output or f"benchmark runner failed for {scenario['id']}")
    payload = json.loads(output)
    payload["driver_elapsed_ms"] = elapsed_ms
    return payload


def compare_benchmarks(results: list[dict],
                       accuracy: dict,
                       performance: dict,
                       status: dict) -> tuple[list[dict], list[str]]:
    regressions: list[str] = []
    compared: list[dict] = []

    for result in results:
        scenario_id = result["scenario_id"]
        scenario_entry = {
            "scenario_id": scenario_id,
            "metrics": result,
            "checks": [],
        }

        for metric, expected in accuracy.get(scenario_id, {}).items():
            actual = result.get(metric)
            passed = isinstance(actual, (int, float)) and actual <= expected
            scenario_entry["checks"].append(
                {"metric": metric, "expected": expected, "actual": actual, "ok": passed}
            )
            if not passed:
                regressions.append(f"{scenario_id}:{metric}={actual} > {expected}")

        for metric, expected in performance.get(scenario_id, {}).items():
            actual = result.get(metric)
            passed = isinstance(actual, (int, float)) and actual <= expected
            scenario_entry["checks"].append(
                {"metric": metric, "expected": expected, "actual": actual, "ok": passed}
            )
            if not passed:
                regressions.append(f"{scenario_id}:{metric}={actual} > {expected}")

        for metric, expected in status.get(scenario_id, {}).items():
            actual = result.get(metric)
            passed = actual == expected
            scenario_entry["checks"].append(
                {"metric": metric, "expected": expected, "actual": actual, "ok": passed}
            )
            if not passed:
                regressions.append(f"{scenario_id}:{metric}={actual} != {expected}")

        compared.append(scenario_entry)

    return compared, regressions


def cmd_build(args: argparse.Namespace) -> int:
    compile_cmd = ["meson", "compile", "-C", args.build_dir]
    for item in args.compile_arg:
        compile_cmd.append(item)
    if args.dry_run:
        return emit_dry_run(
            "build",
            common_command_preview(args, compile_cmd),
            writes=[args.build_dir],
            notes=["Build preview only; no files were modified."],
        )
    if ensure_builddir(args) != 0:
        return 1
    return run(compile_cmd)


def cmd_test(args: argparse.Namespace) -> int:
    test_cmd = ["meson", "test", "-C", args.build_dir, "--print-errorlogs"]
    if args.no_rebuild:
        test_cmd.append("--no-rebuild")
    if args.test_name:
        test_cmd.append(args.test_name)
    if args.dry_run:
        return emit_dry_run(
            "test",
            common_command_preview(args, test_cmd),
            writes=[args.build_dir],
            notes=["Test preview only; no build or test command was executed."],
        )
    if ensure_builddir(args) != 0:
        return 1
    return run(test_cmd)


def cmd_benchmark(args: argparse.Namespace) -> int:
    build_dir = Path(args.build_dir)
    report = benchmark_report_path(args)
    compile_cmd = ["meson", "compile", "-C", args.build_dir, "time_benchmark"]
    if args.dry_run:
        commands = common_command_preview(args, compile_cmd)
        commands.append([str(benchmark_binary(build_dir)), "--kind", "<scenario-kind>", "..."])
        return emit_dry_run(
            "benchmark",
            commands,
            writes=[str(report)],
            notes=[
                "Dry-run does not build the benchmark runner or execute scenarios.",
                "Use --yes to acknowledge overwriting an existing report file.",
            ],
        )
    if ensure_builddir(args) != 0:
        return 1
    if run(compile_cmd) != 0:
        return 1

    binary = benchmark_binary(build_dir)
    if not binary.exists():
        print(
            (
                f"error: benchmark runner not found: {binary}\n"
                f"example: {CLI_PATH} benchmark --report-path eval/reports/time_benchmark_report.json\n"
                f"hint: make sure the build completed successfully and the `time_benchmark` target exists."
            ),
            file=sys.stderr,
        )
        return 1

    scenario_paths = sorted(SCENARIO_DIR.glob("*.json"))
    accuracy = load_json(BASELINE_DIR / "time_accuracy_baseline.json")
    performance = load_json(BASELINE_DIR / "time_performance_baseline.json")
    status = load_json(BASELINE_DIR / "time_status_baseline.json")

    results = [run_benchmark_scenario(binary, load_json(path)) for path in scenario_paths]
    compared, regressions = compare_benchmarks(results, accuracy, performance, status)

    maybe_warn_overwrite(report, args.yes)
    report.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "pass" if not regressions else "fail",
        "target_build_dir": args.build_dir,
        "cross_file": args.cross_file or "",
        "native_file": args.native_file or "",
        "scenario_count": len(results),
        "report_path": str(report),
        "results": compared,
        "regressions": regressions,
    }
    report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print_json(payload)
    return 0 if not regressions else 1


def cmd_traceability(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    commands = traceability_commands(output_dir)
    if args.dry_run:
        return emit_dry_run(
            "traceability",
            commands,
            writes=[str(output_dir)],
            notes=[
                "Dry-run does not regenerate traceability artifacts.",
                "Use --yes to acknowledge overwriting existing generated artifacts.",
            ],
        )
    maybe_warn_overwrite(output_dir / "trace.json", args.yes)
    if run_quiet(commands[0]) != 0:
        return 1
    if run_quiet(commands[1]) != 0:
        return 1
    print_json(
        {
            "output_dir": str(output_dir),
            "files": sorted(str(path) for path in output_dir.glob("*")),
        }
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    build_dir = Path(args.build_dir)
    payload = {
        "skills": sorted(
            str(path.relative_to(REPO_ROOT))
            for path in (REPO_ROOT / "skills").glob("*")
        ),
        "contracts": sorted(
            str(path.relative_to(REPO_ROOT))
            for path in (REPO_ROOT / "contracts").glob("*.md")
        ),
        "build_dir": str(build_dir),
        "builddir_exists": build_dir.exists(),
        "cross_file": args.cross_file or "",
        "native_file": args.native_file or "",
        "traceability_generated": TRACE_OUTPUT_DIR.exists(),
    }
    if build_dir.exists():
        rc, info = run_capture(["meson", "introspect", str(build_dir), "--buildoptions"])
        payload["buildoptions_available"] = rc == 0
        if rc == 0:
            payload["buildoptions_excerpt"] = info.splitlines()[:5]
    print_json(payload)
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CLI-first Meson toolchain entrypoints for build, test, benchmark, and traceability tasks.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} build --reconfigure\n"
            f"  {CLI_PATH} test --no-rebuild --test-name time\n"
            f"  {CLI_PATH} benchmark --report-path eval/reports/time_benchmark_report.json --yes\n"
            f"  {CLI_PATH} benchmark --dry-run\n"
            f"  {CLI_PATH} traceability --output-dir docs/_generated/traceability --yes\n"
            f"  {CLI_PATH} status"
        ),
        formatter_class=HelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--build-dir", default=str(DEFAULT_BUILD_DIR))
        subparser.add_argument("--cross-file", default="")
        subparser.add_argument("--native-file", default="")
        subparser.add_argument("--reconfigure", action="store_true")
        subparser.add_argument("--meson-option", action="append", default=[])
        subparser.add_argument(
            "--dry-run",
            action="store_true",
            help="print the commands and write targets without executing them",
        )

    build = subparsers.add_parser(
        "build",
        description="Configure the Meson build directory when needed, then compile targets.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} build --reconfigure\n"
            f"  {CLI_PATH} build --cross-file tools/nav-toolchain-cli/config/linux.ini --native-file tools/nav-toolchain-cli/config/linux.ini\n"
            f"  {CLI_PATH} build --dry-run"
        ),
        formatter_class=HelpFormatter,
    )
    add_common(build)
    build.add_argument("--compile-arg", action="append", default=[])
    build.set_defaults(handler=cmd_build)

    test = subparsers.add_parser(
        "test",
        description="Run Meson tests after configuring the build directory when needed.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} test --no-rebuild\n"
            f"  {CLI_PATH} test --test-name time\n"
            f"  {CLI_PATH} test --dry-run"
        ),
        formatter_class=HelpFormatter,
    )
    add_common(test)
    test.add_argument("--test-name", default="")
    test.add_argument("--no-rebuild", action="store_true")
    test.set_defaults(handler=cmd_test)

    benchmark = subparsers.add_parser(
        "benchmark",
        description="Build the benchmark runner, execute scenarios, and write a JSON report.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} benchmark --report-path eval/reports/time_benchmark_report.json --yes\n"
            f"  {CLI_PATH} benchmark --build-dir builddir --dry-run"
        ),
        formatter_class=HelpFormatter,
    )
    add_common(benchmark)
    benchmark.add_argument(
        "--report-path",
        default="eval/reports/time_benchmark_report.json",
    )
    benchmark.add_argument(
        "--yes",
        action="store_true",
        help="acknowledge overwriting an existing benchmark report",
    )
    benchmark.set_defaults(handler=cmd_benchmark)

    traceability = subparsers.add_parser(
        "traceability",
        description="Regenerate traceability artifacts under docs/_generated/traceability.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} traceability --output-dir docs/_generated/traceability --yes\n"
            f"  {CLI_PATH} traceability --dry-run"
        ),
        formatter_class=HelpFormatter,
    )
    traceability.add_argument("--output-dir", default=str(TRACE_OUTPUT_DIR))
    traceability.add_argument(
        "--dry-run",
        action="store_true",
        help="print the regeneration plan without writing any artifacts",
    )
    traceability.add_argument(
        "--yes",
        action="store_true",
        help="acknowledge overwriting existing generated artifacts",
    )
    traceability.set_defaults(handler=cmd_traceability)

    status = subparsers.add_parser(
        "status",
        description="Print machine-readable repository and build-directory status.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} status\n"
            f"  {CLI_PATH} status --build-dir builddir"
        ),
        formatter_class=HelpFormatter,
    )
    status.add_argument("--build-dir", default=str(DEFAULT_BUILD_DIR))
    status.add_argument("--cross-file", default="")
    status.add_argument("--native-file", default="")
    status.set_defaults(handler=cmd_status)

    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
