#!/usr/bin/env python3
"""Render CI-facing project dashboard artifacts from canonical memory docs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dashboard_common import (
    ACTIVE_CONTEXT_SECTIONS,
    WORKING_SECTIONS,
    parse_bullet_sections,
    parse_task_board,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "_generated"
TRACEABILITY = REPO_ROOT / "tools" / "traceability-cli" / "traceability_cli.py"

WORKING_PATH = REPO_ROOT / "docs" / "memory" / "working" / "current_focus.md"
TASK_BOARD_PATH = REPO_ROOT / "docs" / "memory" / "short_term" / "task_board.md"
ACTIVE_CONTEXT_PATH = REPO_ROOT / "docs" / "memory" / "short_term" / "active_context.md"
KNOWN_LIMITATIONS_PATH = REPO_ROOT / "docs" / "traceability" / "known_limitations.md"
DECISION_LOG_PATH = REPO_ROOT / "docs" / "traceability" / "decision_log.md"
ACTIVITY_LOG_PATH = REPO_ROOT / "docs" / "traceability" / "agent_activity_log.md"

LIMITATION_SECTIONS = ("Accepted Limitations", "Open Risks")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def run_traceability_status() -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(TRACEABILITY), "status"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        details = "\n".join(part for part in (stdout, stderr) if part).strip()
        raise RuntimeError(details or "traceability status failed")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"traceability status returned invalid JSON: {exc}") from exc


def run_compliance_status() -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(TRACEABILITY), "compliance"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        details = "\n".join(part for part in (stdout, stderr) if part).strip()
        raise RuntimeError(details or "compliance status failed")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"compliance status returned invalid JSON: {exc}") from exc


def parse_limitations(path: Path) -> dict[str, list[str]]:
    return parse_bullet_sections(path, LIMITATION_SECTIONS)


def parse_decisions(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    lines = read_lines(path)
    decisions: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in lines:
        if line.startswith("## "):
            if current is not None:
                decisions.append(current)
            current = {"title": line[3:].strip(), "bullets": []}
            continue
        if current is None:
            continue
        if line.startswith("- "):
            current["bullets"].append(line[2:].strip())
    if current is not None:
        decisions.append(current)
    return decisions


def parse_recent_activity(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    lines = [line for line in read_lines(path) if line.strip().startswith("|")]
    if len(lines) < 3:
        return []
    header = [cell.strip() for cell in lines[0].strip().strip("|").split("|")]
    entries: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(header):
            continue
        row = dict(zip(header, cells))
        entries.append(row)
    return entries


def strip_code_ticks(text: str) -> str:
    return text.replace("`", "")


def build_status_payload(
    working: dict[str, list[str]],
    tasks: list[dict[str, str]],
    context: dict[str, list[str]],
    limitations: dict[str, list[str]],
    decisions: list[dict[str, object]],
    activities: list[dict[str, str]],
    traceability_status: dict[str, object],
    compliance_status: dict[str, object],
) -> dict[str, object]:
    active_tasks = [row for row in tasks if row["status"] == "active"]
    blocked_tasks = [row for row in tasks if row["status"] == "blocked"]

    recent_activity = []
    for row in activities[:5]:
        recent_activity.append(
            {
                "timestamp": row.get("timestamp", ""),
                "task_id": row.get("task_id", ""),
                "agent": row.get("agent", ""),
                "result": row.get("result", ""),
            }
        )
    if len(recent_activity) < 5:
        for row in tasks:
            if row["status"] in {"active", "blocked"}:
                recent_activity.append(
                    {
                        "timestamp": "",
                        "task_id": strip_code_ticks(row["task_id"]),
                        "agent": strip_code_ticks(row["owner_agent"]),
                        "result": strip_code_ticks(row["title"]),
                    }
                )
            if len(recent_activity) >= 5:
                break

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_phase": strip_code_ticks(working["Current Phase"][0]),
        "in_progress": [strip_code_ticks(item) for item in working["In Progress"]],
        "current_blockers": [strip_code_ticks(item) for item in working["Current Blockers"]],
        "active_specs": [strip_code_ticks(item) for item in working["Active Specs"]],
        "next_acceptance_target": [strip_code_ticks(item) for item in working["Next Acceptance Target"]],
        "next_agent": [strip_code_ticks(item) for item in working["Next Agent"]],
        "active_tasks": active_tasks,
        "blocked_tasks": blocked_tasks,
        "current_scope": [strip_code_ticks(item) for item in context["Current Scope"]],
        "active_policy_skills": [strip_code_ticks(item) for item in context["Active Policy Skills"]],
        "acceptance_gates": [strip_code_ticks(item) for item in context["Acceptance Gates"]],
        "handoff_expectations": [strip_code_ticks(item) for item in context["Handoff Expectations"]],
        "recent_activity": recent_activity[:5],
        "recent_decisions": decisions[-3:],
        "accepted_limitations": [strip_code_ticks(item) for item in limitations["Accepted Limitations"]],
        "open_risks": [strip_code_ticks(item) for item in limitations["Open Risks"]],
        "traceability_status": traceability_status,
        "compliance_status": compliance_status,
    }


def render_dashboard(status: dict[str, object]) -> str:
    lines = [
        "# Project Dashboard",
        "",
        f"Generated at: `{status['generated_at']}`",
        "",
        "## Current Phase / Focus",
        "",
        f"- Phase: `{status['current_phase']}`",
    ]
    for item in status["in_progress"]:
        lines.append(f"- In progress: {item}")
    for item in status["next_acceptance_target"]:
        lines.append(f"- Next acceptance target: {item}")
    for item in status["next_agent"]:
        lines.append(f"- Next agent: {item}")

    lines += [
        "",
        "## Current Execution Context",
        "",
    ]
    for item in status["current_scope"]:
        lines.append(f"- Current scope: {item}")
    for item in status["active_policy_skills"]:
        lines.append(f"- Active policy skills: {item}")
    for item in status["acceptance_gates"]:
        lines.append(f"- Acceptance gate: {item}")

    lines += [
        "",
        "## Active And Blocked Tasks",
        "",
        "| task_id | owner_agent | status | title | blockers |",
        "| --- | --- | --- | --- | --- |",
    ]
    combined = list(status["active_tasks"]) + list(status["blocked_tasks"])
    if combined:
        for row in combined:
            lines.append(
                "| `{}` | `{}` | `{}` | {} | {} |".format(
                    strip_code_ticks(row["task_id"]),
                    strip_code_ticks(row["owner_agent"]),
                    strip_code_ticks(row["status"]),
                    strip_code_ticks(row["title"]),
                    strip_code_ticks(row["blockers"]),
                )
            )
    else:
        lines += [
            "",
            "No active or blocked tasks.",
        ]

    lines += ["", "## Current Blockers", ""]
    for item in status["current_blockers"]:
        lines.append(f"- {item}")

    lines += ["", "## Recent Project Progress", ""]
    for item in status["recent_activity"]:
        prefix = f"`{item['timestamp']}` " if item["timestamp"] else ""
        lines.append(
            f"- {prefix}`{item['task_id']}` `{item['agent']}`: {item['result']}"
        )

    lines += ["", "## Recent Frozen Decisions", ""]
    if status["recent_decisions"]:
        for item in status["recent_decisions"]:
            lines.append(f"- {item['title']}")
    else:
        lines.append("- none")

    lines += ["", "## Accepted Limitations / Open Risks", ""]
    for item in status["accepted_limitations"]:
        lines.append(f"- Accepted limitation: {item}")
    for item in status["open_risks"]:
        lines.append(f"- Open risk: {item}")

    trace = status["traceability_status"]
    compliance = status["compliance_status"]
    lines += [
        "",
        "## Product Traceability Statistics",
        "",
        f"- contract_count: `{trace['contract_count']}`",
        f"- verify_count: `{trace['verify_count']}`",
        f"- contracts_with_code: `{trace['contracts_with_code']}`",
        f"- contracts_with_tests: `{trace['contracts_with_tests']}`",
        f"- verifies_with_tests: `{trace['verifies_with_tests']}`",
        "",
        "## Governance Compliance",
        "",
        f"- ok: `{compliance['ok']}`",
        f"- policy_count: `{compliance['policy_count']}`",
        f"- failures: `{len(compliance['failures'])}`",
    ]
    return "\n".join(lines) + "\n"


def write_if_changed(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir

    try:
        working = parse_bullet_sections(WORKING_PATH, WORKING_SECTIONS)
        tasks = parse_task_board(TASK_BOARD_PATH)
        context = parse_bullet_sections(ACTIVE_CONTEXT_PATH, ACTIVE_CONTEXT_SECTIONS)
        limitations = parse_limitations(KNOWN_LIMITATIONS_PATH)
        decisions = parse_decisions(DECISION_LOG_PATH)
        activities = parse_recent_activity(ACTIVITY_LOG_PATH)
        traceability_status = run_traceability_status()
        compliance_status = run_compliance_status()
        status = build_status_payload(
            working,
            tasks,
            context,
            limitations,
            decisions,
            activities,
            traceability_status,
            compliance_status,
        )
        dashboard_text = render_dashboard(status)
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    dashboard_path = output_dir / "project_dashboard.md"
    status_path = output_dir / "project_status.json"
    write_if_changed(dashboard_path, dashboard_text)
    write_if_changed(status_path, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "dashboard": str(dashboard_path),
                "status": str(status_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
