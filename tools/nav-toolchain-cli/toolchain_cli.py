#!/usr/bin/env python3
"""Meson toolchain entrypoints for local and cross builds."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from knowledge_ops import KnowledgeError, build_status as build_knowledge_status
from knowledge_ops import read_note as read_knowledge_note
from knowledge_ops import search_notes as search_knowledge_notes

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILD_DIR = REPO_ROOT / "builddir"
TRACE_OUTPUT_DIR = REPO_ROOT / "docs" / "_generated" / "traceability"
EVAL_DOMAINS_DIR = REPO_ROOT / "eval" / "domains"
CLI_PATH = "python3 tools/nav-toolchain-cli/toolchain_cli.py"


class HelpFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    """Formatter that keeps example blocks readable and shows defaults."""


class EvalBlockedError(RuntimeError):
    """Structured blocked verdict with attribution."""

    def __init__(self, message: str, attribution: str) -> None:
        super().__init__(message)
        self.attribution = attribution


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


def first_match(base: Path, pattern: str) -> Path | None:
    matches = sorted(base.glob(pattern))
    return matches[0] if matches else None


def benchmark_binary(build_dir: Path) -> Path:
    return build_dir / "product" / "tests" / "time_benchmark"


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


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


def load_domain_manifest(domain: str, manifest_path: str = "") -> dict[str, Any]:
    path = repo_path(manifest_path) if manifest_path else EVAL_DOMAINS_DIR / domain / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"missing eval domain manifest: {path}")
    manifest = load_json(path)
    if manifest.get("domain") != domain:
        raise ValueError(
            f"eval domain mismatch: expected {domain}, manifest declares {manifest.get('domain', '')}"
        )
    return manifest


def load_eval_scenarios(manifest: dict[str, Any], scenario_paths: list[str]) -> list[dict[str, Any]]:
    declared_paths = scenario_paths or manifest.get("scenario_paths", [])
    loaded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path_text in declared_paths:
        path = repo_path(path_text)
        if not path.exists():
            raise FileNotFoundError(f"missing eval scenario: {path}")
        scenario = load_json(path)
        scenario_id = str(scenario.get("scenario_id") or scenario.get("id") or "")
        if not scenario_id:
            raise ValueError(f"scenario missing scenario_id: {path}")
        if scenario_id in seen_ids:
            raise ValueError(f"duplicate eval scenario_id: {scenario_id}")
        if scenario.get("domain") != manifest["domain"]:
            raise ValueError(
                f"scenario {scenario_id} domain mismatch: {scenario.get('domain', '')} != {manifest['domain']}"
            )
        required = ("scenario_version", "verify_refs", "contract_refs", "truth_source_refs", "runner_adapter")
        missing = [field for field in required if field not in scenario]
        if missing:
            raise ValueError(f"scenario {scenario_id} missing required fields: {', '.join(missing)}")
        seen_ids.add(scenario_id)
        loaded.append(scenario)
    if not loaded:
        raise ValueError(f"domain {manifest['domain']} has no scenarios")
    return loaded


def load_eval_baseline(manifest: dict[str, Any], baseline_path: str = "") -> dict[str, Any]:
    path_text = baseline_path or str(manifest.get("default_baseline", ""))
    if not path_text:
        raise ValueError(f"domain {manifest['domain']} missing default_baseline")
    path = repo_path(path_text)
    if not path.exists():
        raise FileNotFoundError(f"missing eval baseline: {path}")
    baseline = load_json(path)
    required = ("baseline_id", "baseline_version", "recalibration_policy", "approval", "truth_source_refs")
    missing = [field for field in required if field not in baseline]
    if missing:
        raise ValueError(f"baseline {path} missing required fields: {', '.join(missing)}")
    return baseline


def run_time_benchmark_scenario(binary: Path, scenario: dict[str, Any]) -> dict[str, Any]:
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
        raise RuntimeError(output or f"benchmark runner failed for {scenario.get('scenario_id', kind)}")
    payload = json.loads(output)
    payload["driver_elapsed_ms"] = elapsed_ms
    return payload


def compare_time_results(results: list[dict[str, Any]], baseline: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    regressions: list[str] = []
    compared: list[dict[str, Any]] = []
    thresholds = baseline.get("thresholds", {})

    for result in results:
        scenario_id = result["scenario_id"]
        scenario_entry = {
            "scenario_id": scenario_id,
            "metrics": result,
            "checks": [],
            "result_status": "pass",
        }

        scenario_thresholds = thresholds.get(scenario_id, {})

        for metric, expected in scenario_thresholds.get("accuracy", {}).items():
            actual = result.get(metric)
            passed = isinstance(actual, (int, float)) and actual <= expected
            scenario_entry["checks"].append(
                {"metric": metric, "group": "accuracy", "expected": expected, "actual": actual, "ok": passed}
            )
            if not passed:
                regressions.append(f"{scenario_id}:{metric}={actual} > {expected}")

        for metric, expected in scenario_thresholds.get("performance", {}).items():
            actual = result.get(metric)
            passed = isinstance(actual, (int, float)) and actual <= expected
            scenario_entry["checks"].append(
                {"metric": metric, "group": "performance", "expected": expected, "actual": actual, "ok": passed}
            )
            if not passed:
                regressions.append(f"{scenario_id}:{metric}={actual} > {expected}")

        for metric, expected in scenario_thresholds.get("status", {}).items():
            actual = result.get(metric)
            passed = actual == expected
            scenario_entry["checks"].append(
                {"metric": metric, "group": "status", "expected": expected, "actual": actual, "ok": passed}
            )
            if not passed:
                regressions.append(f"{scenario_id}:{metric}={actual} != {expected}")

        if any(not check["ok"] for check in scenario_entry["checks"]):
            scenario_entry["result_status"] = "fail"
        compared.append(scenario_entry)

    return compared, regressions


def normalize_required_patterns(scenario: dict[str, Any]) -> list[str]:
    patterns: list[str] = []
    for entry in scenario.get("required_files", []):
        if isinstance(entry, str):
            patterns.append(entry)
        elif isinstance(entry, dict) and isinstance(entry.get("pattern"), str):
            patterns.append(entry["pattern"])
    return patterns


def validate_required_patterns(base: Path, patterns: list[str]) -> list[str]:
    missing: list[str] = []
    for pattern in patterns:
        if not list(base.glob(pattern)):
            missing.append(pattern)
    return missing


def require_result_metric(result_lookup: dict[str, dict[str, Any]], metric_id: str, key: str) -> float | bool:
    entry = result_lookup.get(metric_id)
    if entry is None:
        raise ValueError(f"missing result metric: {metric_id}")
    if entry.get("status") != "ok":
        raise ValueError(f"metric {metric_id} is not available: {entry.get('status', 'unknown')}")
    values = entry.get("values", {})
    if key not in values:
        raise ValueError(f"metric {metric_id} missing key: {key}")
    return values[key]


def normalize_pppar_metrics(package_root: Path, scenario: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    eval_path = package_root / "eval_results.json"
    payload = load_json(eval_path)
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise ValueError(f"invalid eval_results payload: {eval_path}")
    result_lookup = {
        str(entry.get("id")): entry
        for entry in results
        if isinstance(entry, dict) and entry.get("id")
    }
    profile = str(scenario.get("metric_profile") or "")
    metrics: dict[str, Any] = {
        "orbit_3d_rms_m": float(require_result_metric(result_lookup, "rtn_orbit_error", "d3_rms_m")),
        "carrier_phase_rms_m": float(require_result_metric(result_lookup, "phase_residual_rms", "carrier_phase_rms_m")),
        "pseudorange_rms_m": float(require_result_metric(result_lookup, "phase_residual_rms", "pseudorange_rms_m")),
    }
    if profile == "ppp_ar_leo_core_v1":
        metrics["narrowlane_fix_rate_pct"] = float(
            require_result_metric(result_lookup, "arsig_fixing", "narrowlane_fix_rate_pct")
        )
        metrics["ar_success"] = bool(require_result_metric(result_lookup, "arsig_fixing", "ar_success"))
    return metrics, [str(eval_path)]


def compare_threshold_groups(
    metrics: dict[str, Any],
    scenario_id: str,
    thresholds: dict[str, Any],
    statistics_policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    regressions: list[str] = []
    tolerance = float(statistics_policy.get("degradation_tolerance_ratio", 0.0))

    for metric, expected in thresholds.get("accuracy", {}).items():
        actual = metrics.get(metric)
        limit = expected * (1.0 + tolerance)
        passed = isinstance(actual, (int, float)) and actual <= limit
        checks.append(
            {
                "metric": metric,
                "group": "accuracy",
                "expected": expected,
                "gate_threshold": limit,
                "actual": actual,
                "ok": passed,
            }
        )
        if not passed:
            regressions.append(f"{scenario_id}:{metric}={actual} > {limit}")

    for metric, expected in thresholds.get("reliability", {}).items():
        actual = metrics.get(metric)
        limit = expected * (1.0 - tolerance)
        passed = isinstance(actual, (int, float)) and actual >= limit
        checks.append(
            {
                "metric": metric,
                "group": "reliability",
                "expected": expected,
                "gate_threshold": limit,
                "actual": actual,
                "ok": passed,
            }
        )
        if not passed:
            regressions.append(f"{scenario_id}:{metric}={actual} < {limit}")

    for metric, expected in thresholds.get("performance", {}).items():
        actual = metrics.get(metric)
        limit = expected * (1.0 + tolerance)
        passed = isinstance(actual, (int, float)) and actual <= limit
        checks.append(
            {
                "metric": metric,
                "group": "performance",
                "expected": expected,
                "gate_threshold": limit,
                "actual": actual,
                "ok": passed,
            }
        )
        if not passed:
            regressions.append(f"{scenario_id}:{metric}={actual} > {limit}")

    for metric, expected in thresholds.get("status", {}).items():
        actual = metrics.get(metric)
        passed = actual == expected
        checks.append(
            {
                "metric": metric,
                "group": "status",
                "expected": expected,
                "gate_threshold": expected,
                "actual": actual,
                "ok": passed,
            }
        )
        if not passed:
            regressions.append(f"{scenario_id}:{metric}={actual} != {expected}")

    return checks, regressions


def resolve_pride_runtime_paths(scenario: dict[str, Any]) -> dict[str, Path | str]:
    runtime = scenario.get("pride_runtime", {})
    runtime_root_text = os.environ.get(
        "PRIDE_PPPAR_RUNTIME_ROOT",
        str(runtime.get("runtime_root") or "/home/hotdry/projects/PRIDE-PPPAR"),
    )
    runtime_root = Path(runtime_root_text).expanduser().resolve()
    driver_relpath = str(runtime.get("driver_relpath") or "toolchain/bin/pdp3")
    env_relpath = str(runtime.get("env_relpath") or "toolchain/env.sh")
    scenario_root_text = os.environ.get(
        f"PRIDE_PPPAR_SCENARIO_ROOT_{str(scenario['scenario_id']).upper()}",
        str(runtime.get("runtime_data_package_root") or (runtime_root / "data" / Path(scenario["data_package_root"]).name)),
    )
    scenario_root = Path(scenario_root_text).expanduser().resolve()
    return {
        "runtime_root": runtime_root,
        "driver": runtime_root / driver_relpath,
        "env_file": runtime_root / env_relpath,
        "scenario_root": scenario_root,
        "cli_mode": str(runtime.get("cli_mode") or "L"),
    }


def measure_pppar_runtime_s(scenario: dict[str, Any]) -> tuple[float, list[str]]:
    runtime_paths = resolve_pride_runtime_paths(scenario)
    driver = runtime_paths["driver"]
    env_file = runtime_paths["env_file"]
    scenario_root = runtime_paths["scenario_root"]
    cli_mode = str(runtime_paths["cli_mode"])

    if not driver.exists():
        raise EvalBlockedError(f"missing PRIDE runtime executable: {driver}", "toolchain_failure")
    if not env_file.exists():
        raise EvalBlockedError(f"missing PRIDE runtime env file: {env_file}", "toolchain_failure")
    if not scenario_root.exists():
        raise EvalBlockedError(f"missing PRIDE runtime scenario root: {scenario_root}", "toolchain_failure")

    config_path = scenario_root / "inputs" / "config.cfg"
    obs_path = first_match(scenario_root / "inputs", "*.??o")
    if not config_path.exists():
        raise EvalBlockedError(f"missing PRIDE scenario config: {config_path}", "toolchain_failure")
    if obs_path is None:
        raise EvalBlockedError(
            f"missing PRIDE observation file under: {scenario_root / 'inputs'}",
            "toolchain_failure",
        )

    command = [
        "bash",
        "-lc",
        (
            f"source {shlex.quote(str(env_file))} && "
            f"{shlex.quote(str(driver))} -m {shlex.quote(cli_mode)} "
            f"-cfg {shlex.quote(str(config_path))} {shlex.quote(str(obs_path))}"
        ),
    ]
    with tempfile.TemporaryDirectory(prefix=f"{scenario['scenario_id']}_", dir="/tmp") as tmp:
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        elapsed_s = time.perf_counter() - started
    if completed.returncode != 0:
        output = (completed.stdout.strip() + "\n" + completed.stderr.strip()).strip()
        raise EvalBlockedError(output or f"PRIDE runtime failed for {scenario['scenario_id']}", "toolchain_failure")
    return elapsed_s, []


def run_pppar_eval_scenario(scenario: dict[str, Any], baseline: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    scenario_id = str(scenario["scenario_id"])
    package_root = repo_path(str(scenario.get("data_package_root", "")))
    if not package_root.exists():
        raise EvalBlockedError(f"missing PPPAR data package: {package_root}", "data_issue")

    missing = validate_required_patterns(package_root, normalize_required_patterns(scenario))
    if missing:
        raise EvalBlockedError(
            f"scenario {scenario_id} missing required files: {', '.join(missing)}",
            "data_issue",
        )

    metrics, artifact_paths = normalize_pppar_metrics(package_root, scenario)
    metrics["runtime_s"], runtime_artifacts = measure_pppar_runtime_s(scenario)
    artifact_paths.extend(runtime_artifacts)

    scenario_thresholds = baseline.get("thresholds", {}).get(scenario_id, {})
    checks, regressions = compare_threshold_groups(
        metrics,
        scenario_id,
        scenario_thresholds,
        baseline.get("statistics_policy", {}),
    )
    entry = {
        "scenario_id": scenario_id,
        "scenario_version": scenario["scenario_version"],
        "verify_refs": scenario["verify_refs"],
        "contract_refs": scenario["contract_refs"],
        "truth_source_refs": scenario["truth_source_refs"],
        "checks": checks,
        "metrics": metrics,
        "artifact_paths": sorted(set(artifact_paths)),
        "result_status": "fail" if regressions else "pass",
    }
    return entry, regressions, artifact_paths


def dry_run_eval_command(args: argparse.Namespace, domain: str, command_name: str) -> int:
    manifest = load_domain_manifest(domain, args.manifest)
    report = repo_path(args.report_path)
    execution_mode = manifest.get("execution_mode", "")
    if execution_mode == "time_benchmark":
        build_dir = Path(args.build_dir)
        compile_cmd = ["meson", "compile", "-C", args.build_dir, "time_benchmark"]
        commands = common_command_preview(args, compile_cmd)
        commands.append([str(benchmark_binary(build_dir)), "--kind", "<scenario-kind>", "..."])
        notes = [
            f"Dry-run does not execute the {domain} adapter.",
            "Use --yes to acknowledge overwriting an existing report file.",
        ]
    elif execution_mode == "pppar_eval_results":
        commands = [
            ["python3", "tools/nav-toolchain-cli/toolchain_cli.py", "eval", "--domain", domain, "--report-path", str(report)],
            ["bash", "-lc", "source /home/hotdry/projects/PRIDE-PPPAR/toolchain/env.sh && /home/hotdry/projects/PRIDE-PPPAR/toolchain/bin/pdp3 -m L -cfg <scenario-config> <observation-file>"],
        ]
        notes = [
            f"Dry-run does not execute the {domain} adapter.",
            "PPPAR eval reads saved eval_results.json and measures PRIDE runtime wall-clock seconds via the external runtime.",
            "Use --yes to acknowledge overwriting an existing report file.",
        ]
    else:
        commands = [["python3", "tools/nav-toolchain-cli/toolchain_cli.py", "eval", "--domain", domain, "--report-path", str(report)]]
        notes = [
            f"Domain {domain} is governance-only; runtime execution currently resolves to a blocked verdict.",
            "Use --yes to acknowledge overwriting an existing report file.",
        ]
    return emit_dry_run(command_name, commands, writes=[str(report)], notes=notes)


def build_eval_payload(
    *,
    command_name: str,
    domain: str,
    manifest: dict[str, Any],
    baseline: dict[str, Any],
    report: Path,
    scenario_results: list[dict[str, Any]],
    regressions: list[str],
    blocked_reasons: list[str],
    blocked_attribution: str,
    build_dir: str,
    cross_file: str,
    native_file: str,
    artifact_paths: list[str],
) -> dict[str, Any]:
    if blocked_reasons:
        verdict = "blocked"
        risk_level = "high"
        attribution = blocked_attribution
    elif regressions:
        verdict = "fail"
        risk_level = "high"
        attribution = "algorithm_regression"
    else:
        verdict = "pass"
        risk_level = "low"
        attribution = "none"
    scenario_versions = {
        entry["scenario_id"]: entry.get("scenario_version", "")
        for entry in scenario_results
    }
    verify_refs = sorted({ref for entry in scenario_results for ref in entry.get("verify_refs", [])})
    contract_refs = sorted({ref for entry in scenario_results for ref in entry.get("contract_refs", [])})
    summary = (
        f"{domain} eval {verdict}: {len(scenario_results)} scenario(s), "
        f"{len(regressions)} regression(s), {len(blocked_reasons)} blocked reason(s)."
    )
    return {
        "schema_version": "1.0",
        "command": command_name,
        "domain": domain,
        "domain_version": manifest.get("domain_version", ""),
        "execution_mode": manifest.get("execution_mode", ""),
        "verdict": verdict,
        "risk_level": risk_level,
        "attribution": attribution,
        "summary_for_acceptance": summary,
        "target_build_dir": build_dir,
        "cross_file": cross_file,
        "native_file": native_file,
        "report_path": str(report),
        "baseline": {
            "baseline_id": baseline.get("baseline_id", ""),
            "baseline_version": baseline.get("baseline_version", ""),
            "approval_status": baseline.get("approval", {}).get("status", ""),
        },
        "scenario_count": len(scenario_results),
        "scenario_versions": scenario_versions,
        "verify_refs": verify_refs,
        "contract_refs": contract_refs,
        "artifact_paths": artifact_paths,
        "results": scenario_results,
        "regressions": regressions,
        "blocked_reasons": blocked_reasons,
    }


def cmd_eval(args: argparse.Namespace, *, default_domain: str | None = None, command_name: str = "eval") -> int:
    domain = default_domain or args.domain
    if not domain:
        raise ValueError("eval domain is required")
    manifest = load_domain_manifest(domain, args.manifest)
    scenarios = load_eval_scenarios(manifest, args.scenario)
    baseline = load_eval_baseline(manifest, args.baseline)
    report = repo_path(args.report_path)

    if args.dry_run:
        return dry_run_eval_command(args, domain, command_name)

    maybe_warn_overwrite(report, args.yes)
    report.parent.mkdir(parents=True, exist_ok=True)

    scenario_results: list[dict[str, Any]] = []
    regressions: list[str] = []
    blocked_reasons: list[str] = []
    blocked_attribution = "toolchain_failure"

    execution_mode = manifest.get("execution_mode", "")
    if execution_mode == "time_benchmark":
        if ensure_builddir(args) != 0:
            return 1
        compile_cmd = ["meson", "compile", "-C", args.build_dir, "time_benchmark"]
        if run(compile_cmd) != 0:
            return 1
        binary = benchmark_binary(Path(args.build_dir))
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
        raw_results = [run_time_benchmark_scenario(binary, scenario) for scenario in scenarios]
        compared, regressions = compare_time_results(raw_results, baseline)
        scenario_meta = {scenario["scenario_id"]: scenario for scenario in scenarios}
        for entry in compared:
            meta = scenario_meta[entry["scenario_id"]]
            entry["scenario_version"] = meta["scenario_version"]
            entry["verify_refs"] = meta["verify_refs"]
            entry["contract_refs"] = meta["contract_refs"]
            entry["truth_source_refs"] = meta["truth_source_refs"]
        scenario_results = compared
    elif execution_mode == "governance_only":
        blocked_reasons.append(
            f"domain {domain} has no executable adapter yet; governance assets are tracked but runtime execution is blocked"
        )
        for scenario in scenarios:
            scenario_results.append(
                {
                    "scenario_id": scenario["scenario_id"],
                    "scenario_version": scenario["scenario_version"],
                    "result_status": "blocked",
                    "verify_refs": scenario["verify_refs"],
                    "contract_refs": scenario["contract_refs"],
                    "truth_source_refs": scenario["truth_source_refs"],
                    "checks": [],
                    "metrics": {},
                    "blocked_reason": "missing executable domain adapter",
                }
            )
    elif execution_mode == "pppar_eval_results":
        artifact_paths: set[str] = {str(report)}
        for scenario in scenarios:
            try:
                entry, scenario_regressions, scenario_artifacts = run_pppar_eval_scenario(scenario, baseline)
            except EvalBlockedError as exc:
                blocked_attribution = exc.attribution
                blocked_reasons.append(str(exc))
                scenario_results.append(
                    {
                        "scenario_id": scenario["scenario_id"],
                        "scenario_version": scenario["scenario_version"],
                        "result_status": "blocked",
                        "verify_refs": scenario["verify_refs"],
                        "contract_refs": scenario["contract_refs"],
                        "truth_source_refs": scenario["truth_source_refs"],
                        "checks": [],
                        "metrics": {},
                        "blocked_reason": str(exc),
                    }
                )
                continue
            except ValueError as exc:
                blocked_attribution = "toolchain_failure"
                blocked_reasons.append(str(exc))
                scenario_results.append(
                    {
                        "scenario_id": scenario["scenario_id"],
                        "scenario_version": scenario["scenario_version"],
                        "result_status": "blocked",
                        "verify_refs": scenario["verify_refs"],
                        "contract_refs": scenario["contract_refs"],
                        "truth_source_refs": scenario["truth_source_refs"],
                        "checks": [],
                        "metrics": {},
                        "blocked_reason": str(exc),
                    }
                )
                continue
            scenario_results.append(entry)
            regressions.extend(scenario_regressions)
            artifact_paths.update(scenario_artifacts)
    else:
        raise ValueError(f"unsupported execution_mode for domain {domain}: {execution_mode}")

    payload = build_eval_payload(
        command_name=command_name,
        domain=domain,
        manifest=manifest,
        baseline=baseline,
        report=report,
        scenario_results=scenario_results,
        regressions=regressions,
        blocked_reasons=blocked_reasons,
        blocked_attribution=blocked_attribution,
        build_dir=args.build_dir,
        cross_file=args.cross_file or "",
        native_file=args.native_file or "",
        artifact_paths=sorted(artifact_paths) if execution_mode == "pppar_eval_results" else [str(report)],
    )
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print_json(payload)
    return 0 if payload["verdict"] == "pass" else 1


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
    return cmd_eval(args, default_domain="time", command_name="benchmark")


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


def knowledge_examples() -> list[str]:
    return [
        f"{CLI_PATH} knowledge status --agent pppar_expert_agent",
        f"{CLI_PATH} knowledge search --agent pppar_expert_agent --query ambiguity",
        f"{CLI_PATH} knowledge read --agent pppar_expert_agent --note pppar/pride-pppar-filtering.md",
    ]


def print_knowledge_error(agent: str, error: str) -> int:
    print_json(
        {
            "status": "blocked",
            "agent": agent,
            "error": error,
            "examples": knowledge_examples(),
        }
    )
    return 1


def cmd_knowledge_status(args: argparse.Namespace) -> int:
    try:
        payload = build_knowledge_status(args.agent)
    except KnowledgeError as exc:
        payload = {
            "status": "blocked",
            "agent": args.agent,
            "error": str(exc),
            "examples": knowledge_examples(),
        }
    print_json(payload)
    return 0


def cmd_knowledge_search(args: argparse.Namespace) -> int:
    try:
        _, payload = search_knowledge_notes(args.agent, args.query, args.limit)
    except KnowledgeError as exc:
        return print_knowledge_error(args.agent, str(exc))
    print_json(payload)
    return 0


def cmd_knowledge_read(args: argparse.Namespace) -> int:
    try:
        _, payload = read_knowledge_note(args.agent, args.note)
    except KnowledgeError as exc:
        return print_knowledge_error(args.agent, str(exc))
    print_json(payload)
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CLI-first Meson toolchain entrypoints for build, test, eval, traceability, and expert knowledge tasks.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} build --reconfigure\n"
            f"  {CLI_PATH} test --no-rebuild --test-name time\n"
            f"  {CLI_PATH} eval --domain time --report-path eval/reports/time_benchmark_report.json --yes\n"
            f"  {CLI_PATH} benchmark --report-path eval/reports/time_benchmark_report.json --yes\n"
            f"  {CLI_PATH} benchmark --dry-run\n"
            f"  {CLI_PATH} traceability --output-dir docs/_generated/traceability --yes\n"
            f"  {CLI_PATH} status\n"
            f"  {CLI_PATH} knowledge status --agent pppar_expert_agent"
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

    eval_cmd = subparsers.add_parser(
        "eval",
        description="Execute a governed eval domain and write a standardized verdict report.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} eval --domain time --report-path eval/reports/time_benchmark_report.json --yes\n"
            f"  {CLI_PATH} eval --domain pppar --report-path eval/reports/pppar_eval_report.json --yes\n"
            f"  {CLI_PATH} eval --domain time --dry-run"
        ),
        formatter_class=HelpFormatter,
    )
    add_common(eval_cmd)
    eval_cmd.add_argument("--domain", required=True)
    eval_cmd.add_argument("--manifest", default="")
    eval_cmd.add_argument("--baseline", default="")
    eval_cmd.add_argument("--scenario", action="append", default=[])
    eval_cmd.add_argument("--report-path", default="eval/reports/eval_report.json")
    eval_cmd.add_argument(
        "--yes",
        action="store_true",
        help="acknowledge overwriting an existing eval report",
    )
    eval_cmd.set_defaults(handler=cmd_eval)

    benchmark = subparsers.add_parser(
        "benchmark",
        description="Compatibility alias for time-domain eval using the legacy benchmark entrypoint.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} benchmark --report-path eval/reports/time_benchmark_report.json --yes\n"
            f"  {CLI_PATH} benchmark --build-dir builddir --dry-run"
        ),
        formatter_class=HelpFormatter,
    )
    add_common(benchmark)
    benchmark.add_argument("--manifest", default="")
    benchmark.add_argument("--baseline", default="")
    benchmark.add_argument("--scenario", action="append", default=[])
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

    knowledge = subparsers.add_parser(
        "knowledge",
        description="Access expert-system Obsidian knowledge through CLI-only wrappers.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} knowledge status --agent pppar_expert_agent\n"
            f"  {CLI_PATH} knowledge search --agent pppar_expert_agent --query ambiguity\n"
            f"  {CLI_PATH} knowledge read --agent pppar_expert_agent --note pppar/pride-pppar-filtering.md"
        ),
        formatter_class=HelpFormatter,
    )
    knowledge_subparsers = knowledge.add_subparsers(dest="knowledge_command", required=True)

    knowledge_status = knowledge_subparsers.add_parser(
        "status",
        description="Print machine-readable CLI-only Obsidian access status for an expert agent.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} knowledge status --agent pppar_expert_agent"
        ),
        formatter_class=HelpFormatter,
    )
    knowledge_status.add_argument("--agent", required=True)
    knowledge_status.set_defaults(handler=cmd_knowledge_status)

    knowledge_search = knowledge_subparsers.add_parser(
        "search",
        description="Search expert-system knowledge for an enabled expert agent.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} knowledge search --agent pppar_expert_agent --query ambiguity\n"
            f"  {CLI_PATH} knowledge search --agent pppar_expert_agent --query \"LEO orbit\" --limit 5"
        ),
        formatter_class=HelpFormatter,
    )
    knowledge_search.add_argument("--agent", required=True)
    knowledge_search.add_argument("--query", required=True)
    knowledge_search.add_argument("--limit", type=int, default=10)
    knowledge_search.set_defaults(handler=cmd_knowledge_search)

    knowledge_read = knowledge_subparsers.add_parser(
        "read",
        description="Read a note under an expert agent's allowed Obsidian roots.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} knowledge read --agent pppar_expert_agent --note pppar/pride-pppar-filtering.md"
        ),
        formatter_class=HelpFormatter,
    )
    knowledge_read.add_argument("--agent", required=True)
    knowledge_read.add_argument("--note", required=True)
    knowledge_read.set_defaults(handler=cmd_knowledge_read)

    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
