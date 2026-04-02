#!/usr/bin/env python3
"""Repository-local quality gate for build, test, traceability, and evidence tags."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN = REPO_ROOT / "tools" / "nav-toolchain-mcp" / "toolchain_mcp.py"
TRACEABILITY = REPO_ROOT / "tools" / "traceability-mcp" / "traceability_cli.py"
BASELINE_STATUS = {
    "contract_count": 8,
    "verify_count": 8,
    "contracts_with_code": 8,
    "contracts_with_tests": 6,
    "verifies_with_tests": 8,
}


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str


def run_command(args: list[str]) -> tuple[bool, str]:
    completed = subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()
    if completed.stderr.strip():
        output = (output + "\n" + completed.stderr.strip()).strip()
    return completed.returncode == 0, output


def contract_evidence_sources() -> Iterable[Path]:
    yield from sorted(REPO_ROOT.glob("src/**/*.h"))


def test_sources() -> Iterable[Path]:
    yield from sorted(REPO_ROOT.glob("tests/**/*.cpp"))


def extract_contract_ids(text: str) -> list[str]:
    return re.findall(r"@contract\{([^}]+)\}", text)


def extract_tagged_tests(text: str) -> list[tuple[str, bool, bool]]:
    pattern = re.compile(
        r"(?P<comment>(?:\s*/\*\*.*?\*/\s*)?)TEST(?:_F|_P)?\s*\(\s*([^,]+)\s*,\s*([^)]+)\)",
        re.DOTALL,
    )
    tagged: list[tuple[str, bool, bool]] = []
    for match in pattern.finditer(text):
        comment = match.group("comment") or ""
        test_name = f"{match.group(2).strip()}.{match.group(3).strip()}"
        tagged.append(
            (
                test_name,
                "@verify{" in comment,
                "@covers{" in comment,
            )
        )
    return tagged


def check_contract_tags() -> CheckResult:
    missing_files: list[str] = []
    total_tags = 0
    for path in contract_evidence_sources():
        text = path.read_text(encoding="utf-8")
        tags = extract_contract_ids(text)
        total_tags += len(tags)
        if not tags:
            missing_files.append(str(path.relative_to(REPO_ROOT)))
    if missing_files:
        return CheckResult(
            "contract_tags",
            False,
            "missing @contract tags in: " + ", ".join(missing_files),
        )
    return CheckResult("contract_tags", True, f"found {total_tags} @contract tags")


def check_test_tags() -> CheckResult:
    failures: list[str] = []
    test_count = 0
    for path in test_sources():
        text = path.read_text(encoding="utf-8")
        for test_name, has_verify, has_covers in extract_tagged_tests(text):
            test_count += 1
            if not has_verify or not has_covers:
                failures.append(
                    f"{path.relative_to(REPO_ROOT)}::{test_name} "
                    f"(verify={has_verify}, covers={has_covers})"
                )
    if failures:
        return CheckResult(
            "test_tags",
            False,
            "missing @verify/@covers on: " + ", ".join(failures),
        )
    return CheckResult("test_tags", True, f"validated {test_count} tagged tests")


def check_traceability_baseline() -> CheckResult:
    ok, output = run_command([sys.executable, str(TRACEABILITY), "status"])
    if not ok:
        return CheckResult("traceability_status", False, output or "status command failed")
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        return CheckResult("traceability_status", False, f"invalid JSON: {exc}")

    regressions: list[str] = []
    for key, expected in BASELINE_STATUS.items():
        actual = payload.get(key)
        if not isinstance(actual, int):
            regressions.append(f"{key}=missing")
        elif actual < expected:
            regressions.append(f"{key}={actual} < {expected}")
    if regressions:
        return CheckResult(
            "traceability_status",
            False,
            "baseline regression: " + ", ".join(regressions),
        )
    return CheckResult("traceability_status", True, json.dumps(payload, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-json", action="store_true")
    args = parser.parse_args()

    checks: list[CheckResult] = []

    for name, command in (
        ("build", [sys.executable, str(TOOLCHAIN), "build"]),
        ("test", [sys.executable, str(TOOLCHAIN), "test", "--no-rebuild"]),
        ("traceability_generate", [sys.executable, str(TOOLCHAIN), "traceability"]),
    ):
        ok, output = run_command(command)
        checks.append(CheckResult(name, ok, output or "(no output)"))
        if not ok:
            payload = {"ok": False, "checks": [check.__dict__ for check in checks]}
            if args.report_json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(f"{name}: failed\n{output}".strip())
            return 1

    checks.append(check_traceability_baseline())
    checks.append(check_contract_tags())
    checks.append(check_test_tags())

    ok = all(check.ok for check in checks)
    payload = {"ok": ok, "checks": [check.__dict__ for check in checks]}
    if args.report_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for check in checks:
            state = "PASS" if check.ok else "FAIL"
            print(f"[{state}] {check.name}: {check.details}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
