#!/usr/bin/env python3
"""Minimal harness runtime CLI for task lifecycle artifacts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(
    os.environ.get("HARNESS_REPO_ROOT", Path(__file__).resolve().parents[2])
).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.agents_runtime.registry import load_expert_registry
from harness.agents_runtime.runtime_adapter import HarnessRuntimeAdapter
from harness.agents_runtime.sessions import LocalSessionBackend
from harness.agents_runtime.artifacts import validate_artifact_payload
from runtime_model import (
    PHASE_ORDER,
    advance_event,
    allowed_next_states,
    default_task_state,
    init_event,
    validate_transition,
)
RUNTIME_ROOT = REPO_ROOT / "harness" / "runtime" / "tasks"
WORKING_PATH = REPO_ROOT / "docs" / "memory" / "working" / "current_focus.md"
TASK_BOARD_PATH = REPO_ROOT / "docs" / "memory" / "short_term" / "task_board.md"
ACTIVE_CONTEXT_PATH = REPO_ROOT / "docs" / "memory" / "short_term" / "active_context.md"
ACTIVITY_LOG_PATH = REPO_ROOT / "docs" / "traceability" / "agent_activity_log.md"
TASK_ARCHIVE_PATH = REPO_ROOT / "docs" / "traceability" / "task_archive.md"
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


def task_dir(task_id: str) -> Path:
    return RUNTIME_ROOT / task_id


def state_path(task_id: str) -> Path:
    return task_dir(task_id) / "task_state.json"


def events_path(task_id: str) -> Path:
    return task_dir(task_id) / "events.jsonl"


def ensure_task_dir(task_id: str) -> Path:
    path = task_dir(task_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def artifacts_dir(task_id: str) -> Path:
    path = task_dir(task_id) / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def load_state(task_id: str) -> dict[str, Any]:
    return json.loads(state_path(task_id).read_text(encoding="utf-8"))


def load_events(task_id: str) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    event_file = events_path(task_id)
    if not event_file.exists():
        return history
    for line in event_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            history.append(json.loads(line))
    return history


def append_event(task_id: str, payload: dict[str, Any]) -> None:
    event_file = events_path(task_id)
    with event_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def has_event(task_id: str, event_name: str) -> bool:
    return any(event.get("event") == event_name for event in load_events(task_id))


def ensure_section_file(path: Path, title: str, sections: tuple[str, ...]) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for section in sections:
        lines.extend([f"## {section}", "- none", ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_bullet_sections(path: Path, sections: tuple[str, ...]) -> dict[str, list[str]]:
    ensure_section_file(path, path.stem.replace("_", " ").title(), sections)
    payload = {name: [] for name in sections}
    current: str | None = None
    for line in read_lines(path)[1:]:
        if line.startswith("## "):
            title = line[3:].strip()
            current = title if title in payload else None
            continue
        if not line.strip() or current is None:
            continue
        if line.startswith("- "):
            payload[current].append(line[2:].strip())
    return payload


def write_bullet_sections(path: Path, title: str, sections: tuple[str, ...], payload: dict[str, list[str]]) -> None:
    lines = [f"# {title}", ""]
    for section in sections:
        lines.append(f"## {section}")
        items = payload.get(section, []) or ["none"]
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_markdown_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return TASK_BOARD_HEADER, []
    table_lines = [line for line in read_lines(path) if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return TASK_BOARD_HEADER, []
    header = [cell.strip() for cell in table_lines[0].strip().strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == len(header):
            rows.append(dict(zip(header, cells)))
    return header, rows


def write_task_board(rows: list[dict[str, str]]) -> None:
    TASK_BOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Task Board",
        "",
        "| " + " | ".join(TASK_BOARD_HEADER) + " |",
        "| " + " | ".join("---" for _ in TASK_BOARD_HEADER) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row.get(column, "") for column in TASK_BOARD_HEADER) + " |")
    TASK_BOARD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_archive_table(rows: list[dict[str, str]]) -> None:
    TASK_ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Task Archive",
        "",
        "Record tasks after they are marked `done`, logged in `agent_activity_log.md`, and no longer needed in short-term memory.",
        "",
        "",
        "| " + " | ".join(TASK_ARCHIVE_HEADER) + " |",
        "| " + " | ".join("----------" for _ in TASK_ARCHIVE_HEADER) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row.get(column, "") for column in TASK_ARCHIVE_HEADER) + " |")
    TASK_ARCHIVE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def runtime_adapter() -> HarnessRuntimeAdapter:
    return HarnessRuntimeAdapter(load_expert_registry(), LocalSessionBackend.default())


def expert_dispatch_event(
    task_id: str,
    agent_name: str,
    owner: str,
    *,
    affected_contracts: list[str],
    knowledge_query: str = "",
    note_path: str = "",
    handoff_summary: str = "",
    session_ref: str = "",
    artifact_ref: str = "",
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": init_event(task_id, "contract_freeze", owner, handoff_summary or "")["timestamp"],
        "event": "dispatch_expert",
        "task_id": task_id,
        "agent_name": agent_name,
        "owner": owner,
        "affected_contracts": affected_contracts,
        "knowledge_query": knowledge_query,
        "note_path": note_path,
        "handoff_summary": handoff_summary,
        "session_ref": session_ref,
        "artifact_ref": artifact_ref,
        "evidence_refs": evidence_refs or [],
    }


def infer_owner_for_phase(phase: str) -> str:
    if phase == "implementation":
        return "coding_agent"
    if phase == "verification":
        return "testing_agent"
    if phase in {"traceability", "acceptance", "contract_freeze", "intake"}:
        return "project-manager"
    return "project-manager"


def task_board_status_for_phase(phase: str) -> str:
    if phase == "implementation":
        return "ready_for_impl"
    if phase == "verification":
        return "ready_for_verify"
    if phase in {"traceability", "acceptance"}:
        return "ready_for_acceptance"
    if phase in {"intake", "contract_freeze"}:
        return "planned"
    return "active"


def artifact_ref_for_path(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def write_artifact(task_id: str, name: str, payload: dict[str, Any], suffix: str = "") -> str:
    errors = validate_artifact_payload(name, payload)
    if errors:
        raise ValueError("; ".join(errors))
    filename = f"{name}{('.' + suffix) if suffix else ''}.json"
    path = artifacts_dir(task_id) / filename
    write_json(path, payload)
    return artifact_ref_for_path(path)


def build_task_brief_artifact(
    task_state: dict[str, Any],
    *,
    affected_contracts: list[str],
    clause_refs: list[str],
    success_criteria: list[str],
    input_refs: list[str],
    output_expectation: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "artifact_version": "1.0",
        "task_id": task_state["task_id"],
        "goal": task_state["goal"],
        "phase": task_state["phase"],
        "affected_contracts": affected_contracts,
        "clause_refs": clause_refs,
        "success_criteria": success_criteria,
        "input_refs": input_refs,
        "output_expectation": output_expectation,
    }


def build_handoff_artifact(
    task_state: dict[str, Any],
    *,
    from_agent: str,
    to_agent: str,
    summary: str,
    relevant_contracts: list[str],
    evidence_refs: list[str],
    blocking_issues: list[str],
    recommended_actions: list[str],
) -> dict[str, Any]:
    return {
        "task_id": task_state["task_id"],
        "phase": task_state["phase"],
        "from_agent": from_agent,
        "to_agent": to_agent,
        "summary": summary,
        "relevant_contracts": relevant_contracts,
        "evidence_refs": evidence_refs,
        "blocking_issues": blocking_issues,
        "recommended_actions": recommended_actions,
    }


def sync_current_focus(
    task_state: dict[str, Any],
    *,
    affected_contracts: list[str],
    task_brief_ref: str,
    handoff_ref: str,
) -> None:
    payload = parse_bullet_sections(WORKING_PATH, WORKING_SECTIONS)
    payload["Current Phase"] = [f"`{task_state['phase']}`"]
    payload["In Progress"] = [
        f"`{task_state['task_id']}`: {task_state['goal']} (task_brief={task_brief_ref}, handoff={handoff_ref})"
    ]
    payload["Current Blockers"] = task_state.get("blocking_issues", []) or ["none"]
    payload["Active Contracts"] = [f"`{contract}`" for contract in affected_contracts] or ["none"]
    payload["Next Acceptance Target"] = [f"`{task_state['task_id']}`: {task_state['goal']}"]
    payload["Next Agent"] = [f"`{task_state['owner']}`"]
    write_bullet_sections(WORKING_PATH, "Current Focus", WORKING_SECTIONS, payload)


def sync_task_board(
    task_state: dict[str, Any],
    *,
    affected_contracts: list[str],
    handoff_ref: str,
) -> None:
    _header, rows = parse_markdown_table(TASK_BOARD_PATH)
    row = {
        "task_id": task_state["task_id"],
        "title": task_state["goal"],
        "owner_agent": task_state["owner"],
        "affected_contracts": ", ".join(affected_contracts),
        "status": task_board_status_for_phase(task_state["phase"]),
        "acceptance": f"phase={task_state['phase']}; handoff={handoff_ref}",
        "blockers": ", ".join(task_state.get("blocking_issues", [])) or "none",
    }
    updated = False
    for index, current in enumerate(rows):
        if current.get("task_id") == task_state["task_id"]:
            rows[index] = row
            updated = True
            break
    if not updated:
        rows.insert(0, row)
    write_task_board(rows)


def sync_active_context(task_state: dict[str, Any], *, task_brief_ref: str, handoff_ref: str) -> None:
    payload = parse_bullet_sections(ACTIVE_CONTEXT_PATH, ACTIVE_CONTEXT_SECTIONS)
    current_scope = [
        item for item in payload["Current Scope"] if not item.startswith("Current PM workflow task:")
    ]
    current_scope.append(
        f"Current PM workflow task: `{task_state['task_id']}` in phase `{task_state['phase']}` with task_brief={task_brief_ref} and handoff={handoff_ref}."
    )
    payload["Current Scope"] = current_scope
    write_bullet_sections(ACTIVE_CONTEXT_PATH, "Active Context", ACTIVE_CONTEXT_SECTIONS, payload)


def prepend_activity_log_row(row: str) -> None:
    lines = read_lines(ACTIVITY_LOG_PATH)
    if len(lines) < 4:
        ACTIVITY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Agent Activity Log",
            "",
            "Record one entry per task transition. Keep newest entries at the top when adding future rows.",
            "",
            "",
            "| timestamp                 | agent            | task_id    | changed_files | clause_ids | handoff_to | result |",
            "| ------------------------- | ---------------- | ---------- | ------------- | ---------- | ---------- | ------ |",
        ]
    insert_at = 7 if len(lines) >= 7 else len(lines)
    lines.insert(insert_at, row)
    ACTIVITY_LOG_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def sync_governance_memory(
    task_state: dict[str, Any],
    *,
    affected_contracts: list[str],
    task_brief_ref: str,
    handoff_ref: str,
) -> None:
    sync_current_focus(
        task_state,
        affected_contracts=affected_contracts,
        task_brief_ref=task_brief_ref,
        handoff_ref=handoff_ref,
    )
    sync_task_board(
        task_state,
        affected_contracts=affected_contracts,
        handoff_ref=handoff_ref,
    )
    sync_active_context(
        task_state,
        task_brief_ref=task_brief_ref,
        handoff_ref=handoff_ref,
    )
    prepend_activity_log_row(
        "| "
        + " | ".join(
            [
                init_event(task_state["task_id"], task_state["phase"], task_state["owner"], task_state["goal"])["timestamp"],
                "project-manager",
                task_state["task_id"],
                "`docs/memory/working/current_focus.md`, `docs/memory/short_term/task_board.md`, `docs/memory/short_term/active_context.md`, `docs/traceability/agent_activity_log.md`",
                ", ".join(f"`{contract}`" for contract in affected_contracts) or "`none`",
                f"`{task_state['owner']}`",
                f"synchronized PM workflow governance state with task_brief={task_brief_ref} and handoff={handoff_ref}",
            ]
        )
        + " |"
    )


def load_task_context(task_state: dict[str, Any]) -> dict[str, Any]:
    context = {
        "affected_contracts": list(task_state.get("affected_contracts", [])),
        "task_brief_ref": task_state.get("task_brief_ref", ""),
        "handoff_ref": task_state.get("handoff_ref", ""),
        "acceptance_summary": task_state.get("acceptance_summary", ""),
    }
    artifacts_root = artifacts_dir(task_state["task_id"])
    if not context["task_brief_ref"]:
        for path in sorted(artifacts_root.glob("task_brief*.json")):
            context["task_brief_ref"] = artifact_ref_for_path(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not context["affected_contracts"]:
                context["affected_contracts"] = list(payload.get("affected_contracts", []))
    if not context["handoff_ref"]:
        for path in sorted(artifacts_root.glob("handoff*.json")):
            context["handoff_ref"] = artifact_ref_for_path(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not context["affected_contracts"]:
                context["affected_contracts"] = list(payload.get("relevant_contracts", []))
            if not context["acceptance_summary"]:
                context["acceptance_summary"] = payload.get("summary", "")
    return context


def close_task_event(
    task_id: str,
    *,
    owner: str,
    status: str,
    acceptance_summary: str,
    evidence_refs: list[str],
) -> dict[str, Any]:
    return {
        "timestamp": init_event(task_id, "acceptance", owner, acceptance_summary)["timestamp"],
        "event": "close_task",
        "task_id": task_id,
        "owner": owner,
        "status": status,
        "acceptance_summary": acceptance_summary,
        "evidence_refs": evidence_refs,
    }


def archive_task_event(
    task_id: str,
    *,
    owner: str,
    status: str,
    archive_ref: str,
) -> dict[str, Any]:
    return {
        "timestamp": init_event(task_id, "acceptance", owner, status)["timestamp"],
        "event": "archive_task",
        "task_id": task_id,
        "owner": owner,
        "status": status,
        "archive_ref": archive_ref,
    }


def close_task_internal(
    task_id: str,
    *,
    status: str,
    acceptance_summary: str,
    evidence_refs: list[str],
) -> dict[str, Any]:
    state = load_state(task_id)
    if state["phase"] != "acceptance":
        raise ValueError(f"close-task requires acceptance phase; got {state['phase']}")
    context = load_task_context(state)
    combined_evidence = list(dict.fromkeys(list(state.get("evidence_refs", [])) + evidence_refs))
    handoff = build_handoff_artifact(
        state,
        from_agent="project-manager",
        to_agent="none",
        summary=acceptance_summary,
        relevant_contracts=context["affected_contracts"],
        evidence_refs=combined_evidence,
        blocking_issues=list(state.get("blocking_issues", [])),
        recommended_actions=["Archive task when short-term memory can be cleared."],
    )
    handoff_ref = write_artifact(task_id, "handoff", handoff, suffix="acceptance")
    state["owner"] = "project-manager"
    state["current_artifact_ref"] = handoff_ref
    state["affected_contracts"] = context["affected_contracts"]
    state["acceptance_status"] = status
    state["acceptance_summary"] = acceptance_summary
    state["handoff_ref"] = handoff_ref
    state["evidence_refs"] = combined_evidence
    state["updated_at"] = init_event(task_id, state["phase"], state["owner"], state["goal"])["timestamp"]
    write_json(state_path(task_id), state)
    if not has_event(task_id, "close_task"):
        append_event(
            task_id,
            close_task_event(
                task_id,
                owner=state["owner"],
                status=status,
                acceptance_summary=acceptance_summary,
                evidence_refs=combined_evidence,
            ),
        )
        prepend_activity_log_row(
            "| "
            + " | ".join(
                [
                    state["updated_at"],
                    "project-manager",
                    task_id,
                    "`docs/memory/working/current_focus.md`, `docs/memory/short_term/task_board.md`, `docs/traceability/agent_activity_log.md`",
                    ", ".join(f"`{contract}`" for contract in context["affected_contracts"]) or "`none`",
                    "`none`",
                    f"closed task at acceptance with status={status} and handoff={handoff_ref}",
                ]
            )
            + " |"
        )
    return {
        "task_state": state,
        "handoff_ref": handoff_ref,
        "affected_contracts": context["affected_contracts"],
        "evidence_refs": combined_evidence,
    }


def archive_task_internal(
    task_id: str,
    *,
    status: str,
    acceptance_summary: str,
    evidence_refs: list[str],
) -> dict[str, Any]:
    state = load_state(task_id)
    if state["phase"] != "acceptance":
        raise ValueError(f"archive-task requires acceptance phase; got {state['phase']}")
    context = load_task_context(state)
    final_summary = acceptance_summary or context["acceptance_summary"] or state.get("acceptance_summary", "") or state["goal"]
    combined_evidence = list(dict.fromkeys(list(state.get("evidence_refs", [])) + evidence_refs))
    _header, rows = parse_markdown_table(TASK_ARCHIVE_PATH)
    archive_row = {
        "task_id": task_id,
        "title": state["goal"],
        "owner_agent": "project-manager",
        "affected_contracts": ", ".join(f"`{contract}`" for contract in context["affected_contracts"]),
        "status": status,
        "acceptance": final_summary,
        "evidence": "; ".join(f"`{item}`" for item in combined_evidence),
    }
    updated = False
    for index, row in enumerate(rows):
        if row.get("task_id") == task_id:
            rows[index] = archive_row
            updated = True
            break
    if not updated:
        rows.insert(0, archive_row)
    write_archive_table(rows)

    _board_header, board_rows = parse_markdown_table(TASK_BOARD_PATH)
    board_rows = [row for row in board_rows if row.get("task_id") != task_id]
    write_task_board(board_rows)

    working = parse_bullet_sections(WORKING_PATH, WORKING_SECTIONS)
    if any(task_id in item for item in working["In Progress"] + working["Next Acceptance Target"]):
        working["In Progress"] = ["none"]
        working["Current Blockers"] = ["none"]
        working["Active Contracts"] = ["none"]
        working["Next Acceptance Target"] = ["none"]
        working["Next Agent"] = ["none"]
    write_bullet_sections(WORKING_PATH, "Current Focus", WORKING_SECTIONS, working)

    active_context = parse_bullet_sections(ACTIVE_CONTEXT_PATH, ACTIVE_CONTEXT_SECTIONS)
    active_context["Current Scope"] = [
        item for item in active_context["Current Scope"] if task_id not in item
    ] or ["No active PM workflow task."]
    write_bullet_sections(ACTIVE_CONTEXT_PATH, "Active Context", ACTIVE_CONTEXT_SECTIONS, active_context)

    archive_ref = artifact_ref_for_path(TASK_ARCHIVE_PATH)
    state["archived"] = True
    state["archive_ref"] = archive_ref
    state["affected_contracts"] = context["affected_contracts"]
    state["acceptance_status"] = status
    state["acceptance_summary"] = final_summary
    state["evidence_refs"] = combined_evidence
    state["updated_at"] = init_event(task_id, state["phase"], "project-manager", state["goal"])["timestamp"]
    write_json(state_path(task_id), state)
    if not has_event(task_id, "archive_task"):
        append_event(
            task_id,
            archive_task_event(
                task_id,
                owner="project-manager",
                status=status,
                archive_ref=archive_ref,
            ),
        )
        prepend_activity_log_row(
            "| "
            + " | ".join(
                [
                    state["updated_at"],
                    "project-manager",
                    task_id,
                    "`docs/memory/working/current_focus.md`, `docs/memory/short_term/task_board.md`, `docs/memory/short_term/active_context.md`, `docs/traceability/task_archive.md`, `docs/traceability/agent_activity_log.md`",
                    ", ".join(f"`{contract}`" for contract in context["affected_contracts"]) or "`none`",
                    "`none`",
                    f"archived task with status={status} into {archive_ref} and cleared short-term memory",
                ]
            )
            + " |"
        )
    return {
        "task_state": state,
        "archive_ref": archive_ref,
        "archive_row": archive_row,
    }


def sync_governance_for_task(task_id: str) -> dict[str, Any]:
    state = load_state(task_id)
    context = load_task_context(state)
    affected_contracts = context["affected_contracts"] or list(state.get("affected_contracts", []))
    task_brief_ref = context["task_brief_ref"]
    handoff_ref = context["handoff_ref"]

    if state.get("archived", False):
        archive_payload = archive_task_internal(
            task_id,
            status=str(state.get("acceptance_status", "done") or "done"),
            acceptance_summary=str(state.get("acceptance_summary", "") or ""),
            evidence_refs=list(state.get("evidence_refs", [])),
        )
        return {
            "status": "ok",
            "mode": "archived",
            "task_state": archive_payload["task_state"],
            "archive_ref": archive_payload["archive_ref"],
        }

    sync_governance_memory(
        state,
        affected_contracts=affected_contracts,
        task_brief_ref=task_brief_ref,
        handoff_ref=handoff_ref,
    )
    return {
        "status": "ok",
        "mode": "active",
        "task_state": state,
        "task_brief_ref": task_brief_ref,
        "handoff_ref": handoff_ref,
    }


def init_task_state(
    task_id: str,
    goal: str,
    *,
    phase: str,
    owner: str,
    affected_contracts: list[str] | None = None,
    trace_id: str = "",
    run_attempt: int = 1,
    parent_trace_id: str = "",
    session_backend: str = "",
    force: bool = False,
) -> dict[str, Any]:
    ensure_task_dir(task_id)
    if state_path(task_id).exists() and not force:
        raise SystemExit(f"task already exists: {task_id}")
    state = default_task_state(
        task_id,
        goal,
        owner,
        phase,
        trace_id=trace_id,
        run_attempt=run_attempt,
        parent_trace_id=parent_trace_id,
        session_backend=session_backend,
    )
    state["affected_contracts"] = affected_contracts or []
    state["archived"] = False
    write_json(state_path(task_id), state)
    event = init_event(
        task_id,
        phase,
        owner,
        goal,
        trace_id=state["trace_id"],
        run_attempt=state["run_attempt"],
        parent_trace_id=state["parent_trace_id"],
    )
    event["timestamp"] = state["updated_at"]
    append_event(task_id, event)
    return state


def advance_task_state(
    task_id: str,
    *,
    target_phase: str,
    owner: str = "",
    evidence: list[str] | None = None,
    blocker: list[str] | None = None,
    note: str = "",
) -> dict[str, Any]:
    state = load_state(task_id)
    current = state["phase"]
    validate_transition(current, target_phase)
    state["phase"] = target_phase
    state["owner"] = owner or state["owner"]
    state["allowed_next_states"] = allowed_next_states(target_phase)
    state["updated_at"] = init_event(
        task_id,
        target_phase,
        state["owner"],
        state["goal"],
    )["timestamp"]
    if evidence:
        state["evidence_refs"].extend(evidence)
    if blocker:
        state["blocking_issues"] = blocker
    write_json(state_path(task_id), state)
    event = advance_event(
        task_id,
        current,
        target_phase,
        state["owner"],
        evidence_refs=evidence,
        blocking_issues=blocker,
        note=note,
        trace_id=state.get("trace_id", ""),
        run_attempt=state.get("run_attempt", 1),
        parent_trace_id=state.get("parent_trace_id", ""),
    )
    event["timestamp"] = state["updated_at"]
    append_event(task_id, event)
    return state


def dispatch_expert_for_task(
    task_id: str,
    *,
    agent_name: str,
    affected_contracts: list[str],
    knowledge_query: str = "",
    note_path: str = "",
    handoff_summary: str = "",
) -> dict[str, Any]:
    state = load_state(task_id)
    adapter = runtime_adapter()
    result = adapter.dispatch_expert(
        state,
        agent_name,
        affected_contracts,
        knowledge_query=knowledge_query,
        note_path=note_path,
        handoff_summary=handoff_summary,
    )
    updated_state = result["task_state"]
    if not updated_state.get("session_backend"):
        updated_state["session_backend"] = adapter.session_backend.backend_id
    updated_state["affected_contracts"] = affected_contracts
    updated_state["updated_at"] = init_event(
        task_id,
        updated_state["phase"],
        updated_state["owner"],
        updated_state["goal"],
    )["timestamp"]
    write_json(state_path(task_id), updated_state)
    append_event(
        task_id,
        expert_dispatch_event(
            task_id,
            agent_name,
            updated_state["owner"],
            affected_contracts=affected_contracts,
            knowledge_query=knowledge_query,
            note_path=note_path,
            handoff_summary=handoff_summary,
            session_ref=result["session_ref"],
            artifact_ref=(result["knowledge_context"] or {}).get("artifact_ref", ""),
            evidence_refs=(result["knowledge_context"] or {}).get("refs", []),
        ),
    )
    return {
        "task_state": updated_state,
        "session_ref": result["session_ref"],
        "knowledge_context": result["knowledge_context"],
    }


def cmd_init_task(args: argparse.Namespace) -> int:
    state = init_task_state(
        args.task_id,
        args.goal,
        phase=args.phase,
        owner=args.owner,
        affected_contracts=args.contract,
        trace_id=args.trace_id,
        run_attempt=args.run_attempt,
        parent_trace_id=args.parent_trace_id,
        session_backend=args.session_backend,
        force=args.force,
    )
    print(json.dumps(state, indent=2, ensure_ascii=False))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if args.task_id:
        print(json.dumps(load_state(args.task_id), indent=2, ensure_ascii=False))
        return 0
    payload = []
    if RUNTIME_ROOT.exists():
        for path in sorted(RUNTIME_ROOT.glob("*/task_state.json")):
            payload.append(json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    try:
        state = advance_task_state(
            args.task_id,
            target_phase=args.phase,
            owner=args.owner,
            evidence=args.evidence,
            blocker=args.blocker,
            note=args.note or "",
        )
    except ValueError as exc:
        raise SystemExit(f"{exc} for {args.task_id}") from exc
    print(json.dumps(state, indent=2, ensure_ascii=False))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    print(json.dumps(load_events(args.task_id), indent=2, ensure_ascii=False))
    return 0


def cmd_dispatch_expert(args: argparse.Namespace) -> int:
    try:
        result = dispatch_expert_for_task(
            args.task_id,
            agent_name=args.agent,
            affected_contracts=args.contract,
            knowledge_query=args.knowledge_query,
            note_path=args.note,
            handoff_summary=args.summary,
        )
    except ValueError as exc:
        raise SystemExit(f"{exc} for {args.task_id}") from exc
    payload = {
        "status": "ok",
        "task_state": result["task_state"],
        "session_ref": result["session_ref"],
        "knowledge_context": result["knowledge_context"],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_resume_agent(args: argparse.Namespace) -> int:
    state = load_state(args.task_id)
    adapter = runtime_adapter()
    try:
        payload = adapter.resume_agent_session(
            state,
            args.agent,
            adapter.session_backend,
        )
    except ValueError as exc:
        raise SystemExit(f"{exc} for {args.task_id}") from exc
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_close_task(args: argparse.Namespace) -> int:
    try:
        payload = close_task_internal(
            args.task_id,
            status=args.status,
            acceptance_summary=args.acceptance_summary,
            evidence_refs=args.evidence,
        )
        if args.archive:
            archived = archive_task_internal(
                args.task_id,
                status=args.status,
                acceptance_summary=args.acceptance_summary,
                evidence_refs=args.evidence,
            )
            payload["archived"] = True
            payload["archive_ref"] = archived["archive_ref"]
        else:
            payload["archived"] = False
    except ValueError as exc:
        raise SystemExit(f"{exc} for {args.task_id}") from exc
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_archive_task(args: argparse.Namespace) -> int:
    try:
        payload = archive_task_internal(
            args.task_id,
            status=args.status,
            acceptance_summary=args.acceptance_summary,
            evidence_refs=args.evidence,
        )
    except ValueError as exc:
        raise SystemExit(f"{exc} for {args.task_id}") from exc
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_sync_governance(args: argparse.Namespace) -> int:
    try:
        payload = sync_governance_for_task(args.task_id)
    except ValueError as exc:
        raise SystemExit(f"{exc} for {args.task_id}") from exc
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_pm_workflow(args: argparse.Namespace) -> int:
    steps: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {}
    if (args.knowledge_query or args.note) and (args.skip_dispatch or not args.agent):
        raise SystemExit("pm-workflow knowledge query/note requires expert dispatch")
    if state_path(args.task_id).exists():
        state = load_state(args.task_id)
    else:
        state = init_task_state(
            args.task_id,
            args.goal,
            phase="intake",
            owner=args.owner,
            affected_contracts=args.contract,
            trace_id=args.trace_id,
            run_attempt=args.run_attempt,
            parent_trace_id=args.parent_trace_id,
            session_backend=args.session_backend,
        )
        steps.append({"step": "init-task", "phase": state["phase"], "owner": state["owner"]})

    if state["phase"] == "traceability" and args.advance_to == "acceptance":
        state = advance_task_state(
            args.task_id,
            target_phase="acceptance",
            owner="project-manager",
            note=args.advance_note or "pm-workflow promoted task into acceptance",
        )
        steps.append({"step": "advance", "phase": state["phase"], "owner": state["owner"]})

    if state["phase"] == "acceptance" and (args.close_task or args.archive_task):
        close_payload: dict[str, Any] | None = None
        if args.close_task:
            close_payload = close_task_internal(
                args.task_id,
                status=args.close_status,
                acceptance_summary=args.acceptance_summary or args.summary or state["goal"],
                evidence_refs=args.evidence,
            )
            steps.append({"step": "close-task", "handoff_ref": close_payload["handoff_ref"]})
        if args.archive_task:
            archive_payload = archive_task_internal(
                args.task_id,
                status=args.close_status,
                acceptance_summary=args.acceptance_summary or state.get("acceptance_summary", "") or args.summary or state["goal"],
                evidence_refs=args.evidence,
            )
            steps.append({"step": "archive-task", "archive_ref": archive_payload["archive_ref"]})
            state = archive_payload["task_state"]
        elif close_payload is not None:
            state = close_payload["task_state"]
        payload = {
            "status": "ok",
            "task_state": state,
            "steps": steps,
        }
        if close_payload is not None:
            payload["handoff_ref"] = close_payload["handoff_ref"]
        if args.archive_task:
            payload["archive_ref"] = archive_payload["archive_ref"]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if state["phase"] == "intake":
        state = advance_task_state(
            args.task_id,
            target_phase="contract_freeze",
            owner="project-manager",
            note="pm-workflow promoted task to contract_freeze before expert dispatch",
        )
        steps.append({"step": "advance", "phase": state["phase"], "owner": state["owner"]})

    if state["phase"] != "contract_freeze":
        raise SystemExit(
            f"pm-workflow requires task phase intake or contract_freeze before orchestration; got {state['phase']}"
        )

    state["affected_contracts"] = args.contract or list(state.get("affected_contracts", []))
    task_brief = build_task_brief_artifact(
        state,
        affected_contracts=state["affected_contracts"],
        clause_refs=args.clause_ref,
        success_criteria=args.success_criteria,
        input_refs=args.input_ref,
        output_expectation=args.output_expectation,
    )
    task_brief_ref = write_artifact(
        args.task_id,
        "task_brief",
        task_brief,
        suffix=state["phase"],
    )
    state["current_artifact_ref"] = task_brief_ref
    state["task_brief_ref"] = task_brief_ref
    write_json(state_path(args.task_id), state)
    artifacts["task_brief"] = task_brief_ref
    steps.append({"step": "task-brief", "artifact_ref": task_brief_ref})

    dispatch_result: dict[str, Any] | None = None
    if not args.skip_dispatch and args.agent:
        dispatch_result = dispatch_expert_for_task(
            args.task_id,
            agent_name=args.agent,
            affected_contracts=state["affected_contracts"],
            knowledge_query=args.knowledge_query,
            note_path=args.note,
            handoff_summary=args.summary,
        )
        state = dispatch_result["task_state"]
        steps.append(
            {
                "step": "dispatch-expert",
                "phase": state["phase"],
                "owner": state["owner"],
                "session_ref": dispatch_result["session_ref"],
            }
        )

    if args.advance_to:
        next_owner = args.next_owner or infer_owner_for_phase(args.advance_to)
        state = advance_task_state(
            args.task_id,
            target_phase=args.advance_to,
            owner=next_owner,
            note=args.advance_note
            or (
                f"pm-workflow advanced task after {args.agent} expert dispatch"
                if dispatch_result is not None
                else "pm-workflow advanced task without expert dispatch"
            ),
        )
        steps.append({"step": "advance", "phase": state["phase"], "owner": state["owner"]})

    handoff = build_handoff_artifact(
        state,
        from_agent=args.agent if dispatch_result is not None else "project-manager",
        to_agent=state["owner"],
        summary=args.summary
        or (
            f"{args.agent} completed expert dispatch"
            if dispatch_result is not None
            else "project-manager prepared downstream handoff without expert dispatch"
        ),
        relevant_contracts=state["affected_contracts"],
        evidence_refs=list(
            dict.fromkeys(
                (dispatch_result["knowledge_context"] or {}).get("refs", [])
                if dispatch_result is not None
                else list(state.get("evidence_refs", []))
            )
        ),
        blocking_issues=list(state.get("blocking_issues", [])),
        recommended_actions=args.recommended_action
        or (
            [f"Resume {args.agent} session for follow-up evidence if implementation uncovers contract gaps."]
            if dispatch_result is not None
            else ["Proceed with implementation against the frozen contracts and current task brief."]
        ),
    )
    handoff_ref = write_artifact(
        args.task_id,
        "handoff",
        handoff,
        suffix=state["phase"],
    )
    state["current_artifact_ref"] = handoff_ref
    state["handoff_ref"] = handoff_ref
    write_json(state_path(args.task_id), state)
    artifacts["handoff"] = handoff_ref
    steps.append({"step": "handoff", "artifact_ref": handoff_ref})
    sync_governance_memory(
        state,
        affected_contracts=state["affected_contracts"],
        task_brief_ref=task_brief_ref,
        handoff_ref=handoff_ref,
    )
    steps.append({"step": "sync-governance", "current_focus": artifact_ref_for_path(WORKING_PATH)})

    payload = {
        "status": "ok",
        "task_state": state,
        "artifacts": artifacts,
        "steps": steps,
    }
    if dispatch_result is not None:
        payload["knowledge_context"] = dispatch_result["knowledge_context"]
        payload["session_ref"] = dispatch_result["session_ref"]
    if state["phase"] == "acceptance" and args.close_task:
        close_payload = close_task_internal(
            args.task_id,
            status=args.close_status,
            acceptance_summary=args.acceptance_summary or args.summary or state["goal"],
            evidence_refs=args.evidence,
        )
        payload["handoff_ref"] = close_payload["handoff_ref"]
        payload["task_state"] = close_payload["task_state"]
        steps.append({"step": "close-task", "handoff_ref": close_payload["handoff_ref"]})
        if args.archive_task:
            archive_payload = archive_task_internal(
                args.task_id,
                status=args.close_status,
                acceptance_summary=args.acceptance_summary or state.get("acceptance_summary", "") or args.summary or state["goal"],
                evidence_refs=args.evidence,
            )
            payload["archive_ref"] = archive_payload["archive_ref"]
            payload["task_state"] = archive_payload["task_state"]
            steps.append({"step": "archive-task", "archive_ref": archive_payload["archive_ref"]})
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_task = subparsers.add_parser("init-task")
    init_task.add_argument("--task-id", required=True)
    init_task.add_argument("--goal", required=True)
    init_task.add_argument("--phase", choices=PHASE_ORDER, default="intake")
    init_task.add_argument("--owner", default="project-manager")
    init_task.add_argument("--contract", action="append", default=[])
    init_task.add_argument("--trace-id", default="")
    init_task.add_argument("--run-attempt", type=int, default=1)
    init_task.add_argument("--parent-trace-id", default="")
    init_task.add_argument("--session-backend", default="")
    init_task.add_argument("--force", action="store_true")
    init_task.set_defaults(handler=cmd_init_task)

    status = subparsers.add_parser("status")
    status.add_argument("--task-id", default="")
    status.set_defaults(handler=cmd_status)

    advance = subparsers.add_parser("advance")
    advance.add_argument("--task-id", required=True)
    advance.add_argument("--phase", choices=PHASE_ORDER, required=True)
    advance.add_argument("--owner", default="")
    advance.add_argument("--evidence", action="append", default=[])
    advance.add_argument("--blocker", action="append", default=[])
    advance.add_argument("--note", default="")
    advance.set_defaults(handler=cmd_advance)

    replay = subparsers.add_parser("replay")
    replay.add_argument("--task-id", required=True)
    replay.set_defaults(handler=cmd_replay)

    dispatch_expert = subparsers.add_parser("dispatch-expert")
    dispatch_expert.add_argument("--task-id", required=True)
    dispatch_expert.add_argument("--agent", required=True)
    dispatch_expert.add_argument("--contract", action="append", required=True, default=[])
    dispatch_target = dispatch_expert.add_mutually_exclusive_group()
    dispatch_target.add_argument("--knowledge-query", default="")
    dispatch_target.add_argument("--note", default="")
    dispatch_expert.add_argument("--summary", default="")
    dispatch_expert.set_defaults(handler=cmd_dispatch_expert)

    resume_agent = subparsers.add_parser("resume-agent")
    resume_agent.add_argument("--task-id", required=True)
    resume_agent.add_argument("--agent", required=True)
    resume_agent.set_defaults(handler=cmd_resume_agent)

    close_task = subparsers.add_parser("close-task")
    close_task.add_argument("--task-id", required=True)
    close_task.add_argument("--status", choices=("done", "blocked"), default="done")
    close_task.add_argument("--acceptance-summary", required=True)
    close_task.add_argument("--evidence", action="append", default=[])
    close_task.add_argument("--archive", action="store_true")
    close_task.set_defaults(handler=cmd_close_task)

    archive_task = subparsers.add_parser("archive-task")
    archive_task.add_argument("--task-id", required=True)
    archive_task.add_argument("--status", choices=("done", "blocked"), default="done")
    archive_task.add_argument("--acceptance-summary", default="")
    archive_task.add_argument("--evidence", action="append", default=[])
    archive_task.set_defaults(handler=cmd_archive_task)

    sync_governance = subparsers.add_parser("sync-governance")
    sync_governance.add_argument("--task-id", required=True)
    sync_governance.set_defaults(handler=cmd_sync_governance)

    pm_workflow = subparsers.add_parser("pm-workflow")
    pm_workflow.add_argument("--task-id", required=True)
    pm_workflow.add_argument("--goal", required=True)
    pm_workflow.add_argument("--agent", default="")
    pm_workflow.add_argument("--skip-dispatch", action="store_true")
    pm_workflow.add_argument("--contract", action="append", required=True, default=[])
    pm_workflow.add_argument("--clause-ref", action="append", default=[])
    pm_workflow.add_argument(
        "--success-criteria",
        action="append",
        default=["official task lifecycle is recorded through harness control-plane artifacts"],
    )
    pm_workflow.add_argument("--input-ref", action="append", default=[])
    pm_workflow.add_argument(
        "--output-expectation",
        action="append",
        default=["validated handoff artifact for downstream implementation"],
    )
    pm_target = pm_workflow.add_mutually_exclusive_group()
    pm_target.add_argument("--knowledge-query", default="")
    pm_target.add_argument("--note", default="")
    pm_workflow.add_argument("--summary", default="")
    pm_workflow.add_argument("--recommended-action", action="append", default=[])
    pm_workflow.add_argument("--close-task", action="store_true")
    pm_workflow.add_argument("--archive-task", action="store_true")
    pm_workflow.add_argument("--close-status", choices=("done", "blocked"), default="done")
    pm_workflow.add_argument("--acceptance-summary", default="")
    pm_workflow.add_argument("--evidence", action="append", default=[])
    pm_workflow.add_argument("--advance-to", choices=PHASE_ORDER[2:], default="implementation")
    pm_workflow.add_argument("--advance-note", default="")
    pm_workflow.add_argument("--next-owner", default="")
    pm_workflow.add_argument("--owner", default="project-manager")
    pm_workflow.add_argument("--trace-id", default="")
    pm_workflow.add_argument("--run-attempt", type=int, default=1)
    pm_workflow.add_argument("--parent-trace-id", default="")
    pm_workflow.add_argument("--session-backend", default="local-jsonl")
    pm_workflow.set_defaults(handler=cmd_pm_workflow)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
