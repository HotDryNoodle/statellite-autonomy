#!/usr/bin/env python3
"""Meson toolchain entrypoints for local and cross builds."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILD_DIR = REPO_ROOT / "builddir"
TRACE_OUTPUT_DIR = REPO_ROOT / "docs" / "_generated" / "traceability"
SCENARIO_DIR = REPO_ROOT / "eval" / "scenarios"
BASELINE_DIR = REPO_ROOT / "eval" / "baselines"


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


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def benchmark_binary(build_dir: Path) -> Path:
    return build_dir / "tests" / "time_benchmark"


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


def ensure_builddir(args: argparse.Namespace) -> int:
    build_dir = Path(args.build_dir)
    if build_dir.exists() and not args.reconfigure and not args.cross_file and not args.native_file and not args.meson_option:
        return 0
    return run(setup_command(args))


def cmd_build(args: argparse.Namespace) -> int:
    if ensure_builddir(args) != 0:
        return 1
    cmd = ["meson", "compile", "-C", args.build_dir]
    for item in args.compile_arg:
        cmd.append(item)
    return run(cmd)


def cmd_test(args: argparse.Namespace) -> int:
    if ensure_builddir(args) != 0:
        return 1
    cmd = ["meson", "test", "-C", args.build_dir, "--print-errorlogs"]
    if args.no_rebuild:
        cmd.append("--no-rebuild")
    if args.test_name:
        cmd.append(args.test_name)
    return run(cmd)


def cmd_benchmark(args: argparse.Namespace) -> int:
    if ensure_builddir(args) != 0:
        return 1
    if run(["meson", "compile", "-C", args.build_dir, "time_benchmark"]) != 0:
        return 1

    build_dir = Path(args.build_dir)
    binary = benchmark_binary(build_dir)
    if not binary.exists():
        print(f"Benchmark runner not found: {binary}", file=sys.stderr)
        return 1

    scenario_paths = sorted(SCENARIO_DIR.glob("*.json"))
    accuracy = load_json(BASELINE_DIR / "time_accuracy_baseline.json")
    performance = load_json(BASELINE_DIR / "time_performance_baseline.json")
    status = load_json(BASELINE_DIR / "time_status_baseline.json")

    results = [run_benchmark_scenario(binary, load_json(path)) for path in scenario_paths]
    compared, regressions = compare_benchmarks(results, accuracy, performance, status)

    report = Path(args.report_path)
    if not report.is_absolute():
        report = REPO_ROOT / report
    report.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "pass" if not regressions else "fail",
        "target_build_dir": args.build_dir,
        "cross_file": args.cross_file or "",
        "native_file": args.native_file or "",
        "scenario_count": len(results),
        "results": compared,
        "regressions": regressions,
    }
    report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(report)
    return 0 if not regressions else 1


def cmd_traceability(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    index_cmd = [
        sys.executable,
        str(REPO_ROOT / "tools" / "traceability-mcp" / "gen_contract_index.py"),
        "--output",
        str(output_dir / "contract_index.json"),
    ]
    if run_quiet(index_cmd) != 0:
        return 1
    trace_cmd = [
        sys.executable,
        str(REPO_ROOT / "tools" / "traceability-mcp" / "gen_trace.py"),
        "--output-dir",
        str(output_dir),
    ]
    return run_quiet(trace_cmd)


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
    print(json.dumps(payload, indent=2))
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--build-dir", default=str(DEFAULT_BUILD_DIR))
        subparser.add_argument("--cross-file", default="")
        subparser.add_argument("--native-file", default="")
        subparser.add_argument("--reconfigure", action="store_true")
        subparser.add_argument("--meson-option", action="append", default=[])

    build = subparsers.add_parser("build")
    add_common(build)
    build.add_argument("--compile-arg", action="append", default=[])
    build.set_defaults(handler=cmd_build)

    test = subparsers.add_parser("test")
    add_common(test)
    test.add_argument("--test-name", default="")
    test.add_argument("--no-rebuild", action="store_true")
    test.set_defaults(handler=cmd_test)

    benchmark = subparsers.add_parser("benchmark")
    add_common(benchmark)
    benchmark.add_argument(
        "--report-path",
        default="eval/reports/benchmark-placeholder.json",
    )
    benchmark.set_defaults(handler=cmd_benchmark)

    traceability = subparsers.add_parser("traceability")
    traceability.add_argument("--output-dir", default=str(TRACE_OUTPUT_DIR))
    traceability.set_defaults(handler=cmd_traceability)

    status = subparsers.add_parser("status")
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
