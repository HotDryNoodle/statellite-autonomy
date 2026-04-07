#!/usr/bin/env python3
"""Shared helpers for governance docs, runtime policy, and dashboard parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path


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
TASK_STATUSES = {
    "active",
    "planned",
    "blocked",
    "ready_for_impl",
    "ready_for_verify",
    "ready_for_acceptance",
}
TASK_BOARD_HEADER = [
    "task_id",
    "title",
    "owner_agent",
    "affected_contracts",
    "status",
    "acceptance",
    "blockers",
]
TASK_ARCHIVE_HEADER = [
    "task_id",
    "title",
    "owner_agent",
    "affected_contracts",
    "status",
    "acceptance",
    "evidence",
]
TASK_ID_PATTERN = re.compile(r"^(?P<prefix>[A-Za-z_]+)-(?P<number>\d+)(?:[-_].*)?$")


def parse_bullet_sections(path: Path, allowed_sections: tuple[str, ...]) -> dict[str, list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    sections = {name: [] for name in allowed_sections}
    current: str | None = None

    for line in lines[1:]:
        if line.startswith("## "):
            title = line[3:].strip()
            if title not in sections:
                raise ValueError(f"{path} contains unexpected section: {title}")
            current = title
            continue
        if not line.strip():
            continue
        if current is None:
            raise ValueError(f"{path} contains content outside a section")
        if not line.startswith("- "):
            raise ValueError(f"{path} contains non-bullet content in section {current}")
        sections[current].append(line[2:].strip())

    for title in allowed_sections:
        if not sections[title]:
            raise ValueError(f"{path} missing content for section: {title}")
    return sections


def parse_markdown_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    table_lines = [line for line in lines if line.strip().startswith("|")]
    if len(table_lines) < 2:
        raise ValueError(f"{path} must contain a markdown table")

    header = [cell.strip() for cell in table_lines[0].strip().strip("|").split("|")]
    separator = [cell.strip() for cell in table_lines[1].strip().strip("|").split("|")]
    if len(separator) != len(header) or any(not cell.startswith("---") for cell in separator):
        raise ValueError(f"{path} has an invalid table separator")

    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(header):
            raise ValueError(f"{path} has a malformed table row: {line}")
        rows.append(dict(zip(header, cells)))

    return header, rows


def parse_task_board(path: Path) -> list[dict[str, str]]:
    header, rows = parse_markdown_table(path)
    if header != TASK_BOARD_HEADER:
        raise ValueError(f"{path} has an unexpected task board header: {header}")
    for row in rows:
        status = row.get("status", "")
        if status not in TASK_STATUSES:
            raise ValueError(f"{path} contains unsupported task status: {status}")
    return rows


def parse_task_archive(path: Path) -> list[dict[str, str]]:
    header, rows = parse_markdown_table(path)
    if header != TASK_ARCHIVE_HEADER:
        raise ValueError(f"{path} has an unexpected task archive header: {header}")
    return rows


def task_status_for_phase(phase: str) -> str:
    if phase == "implementation":
        return "ready_for_impl"
    if phase == "verification":
        return "ready_for_verify"
    if phase in {"traceability", "acceptance"}:
        return "ready_for_acceptance"
    if phase in {"intake", "contract_freeze"}:
        return "planned"
    return "active"


def load_governance_policy(repo_root: Path) -> dict[str, object]:
    path = repo_root / "harness" / "config" / "governance_policy.json"
    default_policy: dict[str, object] = {
        "version": "1.0",
        "runtime_required_from_task_id": "COLLAB-013",
        "legacy_task_ids": [],
        "runtime_retention": {
            "mode": "tracked_compact_proof",
            "eligible_phase": "acceptance",
            "require_archived": True,
            "tracked_proof_files": ["task_state.json", "events.jsonl", "compact_manifest.json"],
            "drop_tracked_artifacts": True,
            "local_spill_dir": "harness/runtime/archive",
            "local_spill_tracked": False,
        },
    }
    if not path.exists():
        return default_policy
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("legacy_task_ids", []), list):
        raise ValueError(f"{path} legacy_task_ids must be a list")
    if not isinstance(payload.get("runtime_retention", {}), dict):
        raise ValueError(f"{path} runtime_retention must be an object")
    default_policy.update(payload)
    retention = dict(default_policy["runtime_retention"])
    retention.update(payload.get("runtime_retention", {}))
    default_policy["runtime_retention"] = retention
    return default_policy


def _task_cutover_key(task_id: str) -> tuple[str, int] | None:
    match = TASK_ID_PATTERN.match(task_id)
    if match is None:
        return None
    return match.group("prefix"), int(match.group("number"))


def requires_runtime_record(task_id: str, policy: dict[str, object]) -> bool:
    legacy_task_ids = {str(item) for item in policy.get("legacy_task_ids", [])}
    if task_id in legacy_task_ids:
        return False
    cutoff = str(policy.get("runtime_required_from_task_id", "")).strip()
    if not cutoff:
        return True
    if task_id == cutoff:
        return True
    task_key = _task_cutover_key(task_id)
    cutoff_key = _task_cutover_key(cutoff)
    if task_key is not None and cutoff_key is not None and task_key[0] == cutoff_key[0]:
        return task_key[1] >= cutoff_key[1]
    return True


def task_state_path(repo_root: Path, task_id: str) -> Path:
    return repo_root / "harness" / "runtime" / "tasks" / task_id / "task_state.json"


def task_events_path(repo_root: Path, task_id: str) -> Path:
    return repo_root / "harness" / "runtime" / "tasks" / task_id / "events.jsonl"


def task_compact_manifest_path(repo_root: Path, task_id: str) -> Path:
    return repo_root / "harness" / "runtime" / "tasks" / task_id / "compact_manifest.json"


def task_artifacts_dir(repo_root: Path, task_id: str) -> Path:
    return repo_root / "harness" / "runtime" / "tasks" / task_id / "artifacts"


def load_task_state(repo_root: Path, task_id: str) -> dict[str, object] | None:
    path = task_state_path(repo_root, task_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_task_events(repo_root: Path, task_id: str) -> list[dict[str, object]]:
    path = task_events_path(repo_root, task_id)
    if not path.exists():
        return []
    events: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def load_task_compact_manifest(repo_root: Path, task_id: str) -> dict[str, object] | None:
    path = task_compact_manifest_path(repo_root, task_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
