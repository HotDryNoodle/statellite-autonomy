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

from dashboard_common import TASK_BOARD_HEADER, parse_task_board


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN = REPO_ROOT / "tools" / "nav-toolchain-mcp" / "toolchain_mcp.py"
TRACEABILITY = REPO_ROOT / "tools" / "traceability-mcp" / "traceability_cli.py"
RENDER_DASHBOARD = REPO_ROOT / "scripts" / "render_project_dashboard.py"
BASELINE_STATUS = {
    "contract_count": 8,
    "verify_count": 8,
    "contracts_with_code": 8,
    "contracts_with_tests": 6,
    "verifies_with_tests": 8,
}
WORKING_PATH = REPO_ROOT / "docs" / "memory" / "working" / "current_focus.md"
TASK_BOARD_PATH = REPO_ROOT / "docs" / "memory" / "short_term" / "task_board.md"
ACTIVE_CONTEXT_PATH = REPO_ROOT / "docs" / "memory" / "short_term" / "active_context.md"
PROJECT_STATUS_PATH = REPO_ROOT / "docs" / "_generated" / "project_status.json"
WORKING_SECTIONS = (
    "Current Phase",
    "In Progress",
    "Current Blockers",
    "Active Contracts",
    "Next Acceptance Target",
    "Next Agent",
)
ACTIVE_CONTEXT_SECTIONS = (
    "Current Scope",
    "Active Policy Skills",
    "Acceptance Gates",
    "Handoff Expectations",
)
@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str


def run_command(args: list[str]) -> tuple[bool, str, str]:
    completed = subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0, completed.stdout.strip(), completed.stderr.strip()


def format_command_output(stdout: str, stderr: str) -> str:
    return "\n".join(part for part in (stdout, stderr) if part).strip()


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
    ok, stdout, stderr = run_command([sys.executable, str(TRACEABILITY), "status"])
    output = format_command_output(stdout, stderr)
    if not ok:
        return CheckResult("traceability_status", False, output or "status command failed")
    try:
        payload = json.loads(stdout)
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


def check_line_limit(path: Path, limit: int) -> CheckResult:
    if not path.exists():
        return CheckResult(path.name, False, f"missing file: {path.relative_to(REPO_ROOT)}")
    line_count = len(path.read_text(encoding="utf-8").splitlines())
    if line_count > limit:
        return CheckResult(path.name, False, f"{path.relative_to(REPO_ROOT)} has {line_count} lines > {limit}")
    return CheckResult(path.name, True, f"{path.relative_to(REPO_ROOT)} has {line_count} lines")


def parse_bullet_sections(path: Path, allowed_sections: tuple[str, ...]) -> tuple[bool, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    sections = {name: [] for name in allowed_sections}
    current: str | None = None
    for line in lines[1:]:
        if line.startswith("## "):
            title = line[3:].strip()
            if title not in sections:
                return False, f"unexpected section {title} in {path.relative_to(REPO_ROOT)}"
            current = title
            continue
        if not line.strip():
            continue
        if current is None:
            return False, f"content outside section in {path.relative_to(REPO_ROOT)}"
        if not line.startswith("- "):
            return False, f"non-bullet content in {path.relative_to(REPO_ROOT)} section {current}"
        sections[current].append(line[2:].strip())
    missing = [title for title, items in sections.items() if not items]
    if missing:
        return False, f"missing content in {path.relative_to(REPO_ROOT)}: {', '.join(missing)}"
    return True, "ok"


def check_working_memory() -> CheckResult:
    if not WORKING_PATH.exists():
        return CheckResult("working_memory_schema", False, f"missing {WORKING_PATH.relative_to(REPO_ROOT)}")
    ok, details = parse_bullet_sections(WORKING_PATH, WORKING_SECTIONS)
    return CheckResult("working_memory_schema", ok, details)


def check_short_term_context() -> CheckResult:
    if not ACTIVE_CONTEXT_PATH.exists():
        return CheckResult("active_context_schema", False, f"missing {ACTIVE_CONTEXT_PATH.relative_to(REPO_ROOT)}")
    ok, details = parse_bullet_sections(ACTIVE_CONTEXT_PATH, ACTIVE_CONTEXT_SECTIONS)
    return CheckResult("active_context_schema", ok, details)


def check_task_board() -> CheckResult:
    if not TASK_BOARD_PATH.exists():
        return CheckResult("task_board_schema", False, f"missing {TASK_BOARD_PATH.relative_to(REPO_ROOT)}")
    try:
        rows = parse_task_board(TASK_BOARD_PATH)
    except ValueError as exc:
        return CheckResult("task_board_schema", False, str(exc))
    return CheckResult("task_board_schema", True, f"validated {len(rows)} task rows against {TASK_BOARD_HEADER}")


def check_dashboard_status_schema() -> CheckResult:
    if not PROJECT_STATUS_PATH.exists():
        return CheckResult("project_status_schema", False, f"missing {PROJECT_STATUS_PATH.relative_to(REPO_ROOT)}")
    try:
        payload = json.loads(PROJECT_STATUS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return CheckResult("project_status_schema", False, f"invalid JSON: {exc}")

    required = {
        "generated_at",
        "current_phase",
        "in_progress",
        "current_blockers",
        "active_contracts",
        "next_acceptance_target",
        "next_agent",
        "active_tasks",
        "blocked_tasks",
        "recent_activity",
        "recent_decisions",
        "accepted_limitations",
        "open_risks",
        "traceability_status",
    }
    missing = sorted(required - payload.keys())
    if missing:
        return CheckResult("project_status_schema", False, f"missing keys: {', '.join(missing)}")
    if not isinstance(payload["current_phase"], str):
        return CheckResult("project_status_schema", False, "current_phase must be a string")
    for field in (
        "in_progress",
        "current_blockers",
        "active_contracts",
        "next_acceptance_target",
        "next_agent",
        "active_tasks",
        "blocked_tasks",
        "recent_activity",
        "recent_decisions",
        "accepted_limitations",
        "open_risks",
    ):
        if not isinstance(payload[field], list):
            return CheckResult("project_status_schema", False, f"{field} must be a list")
    traceability = payload["traceability_status"]
    if not isinstance(traceability, dict):
        return CheckResult("project_status_schema", False, "traceability_status must be an object")
    for field in BASELINE_STATUS:
        if not isinstance(traceability.get(field), int):
            return CheckResult("project_status_schema", False, f"traceability_status.{field} must be an int")
    return CheckResult("project_status_schema", True, "required dashboard status keys present")


def check_generated_files_not_tracked() -> CheckResult:
    ok, stdout, stderr = run_command(["git", "ls-files", "docs/_generated"])
    if not ok:
        return CheckResult(
            "generated_files_untracked",
            False,
            format_command_output(stdout, stderr) or "git ls-files docs/_generated failed",
        )
    tracked = [line for line in stdout.splitlines() if line.strip()]
    if tracked:
        return CheckResult(
            "generated_files_untracked",
            False,
            "tracked generated files found: " + ", ".join(tracked),
        )
    return CheckResult("generated_files_untracked", True, "no tracked files under docs/_generated")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-json", action="store_true")
    parser.add_argument("--skip-build-test", action="store_true")
    parser.add_argument("--skip-project-dashboard", action="store_true")
    args = parser.parse_args()

    checks: list[CheckResult] = []

    commands: list[tuple[str, list[str]]] = []
    if not args.skip_build_test:
        commands.extend(
            (
                ("build", [sys.executable, str(TOOLCHAIN), "build"]),
                ("test", [sys.executable, str(TOOLCHAIN), "test", "--no-rebuild"]),
            )
        )
    commands.append(("traceability_generate", [sys.executable, str(TOOLCHAIN), "traceability"]))
    if not args.skip_project_dashboard:
        commands.append(("project_dashboard", [sys.executable, str(RENDER_DASHBOARD)]))

    for name, command in commands:
        ok, stdout, stderr = run_command(command)
        output = format_command_output(stdout, stderr)
        checks.append(CheckResult(name, ok, output or "(no output)"))
        if not ok:
            payload = {"ok": False, "checks": [check.__dict__ for check in checks]}
            if args.report_json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(f"{name}: failed\n{output}".strip())
            return 1

    checks.append(check_traceability_baseline())
    checks.append(check_line_limit(WORKING_PATH, 50))
    checks.append(check_line_limit(TASK_BOARD_PATH, 120))
    checks.append(check_line_limit(ACTIVE_CONTEXT_PATH, 120))
    checks.append(check_working_memory())
    checks.append(check_task_board())
    checks.append(check_short_term_context())
    if not args.skip_project_dashboard:
        checks.append(check_dashboard_status_schema())
    checks.append(check_generated_files_not_tracked())
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
