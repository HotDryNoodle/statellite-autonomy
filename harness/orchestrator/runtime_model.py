"""Shared harness runtime rules and task-state helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


PHASE_ORDER = (
    "intake",
    "contract_freeze",
    "implementation",
    "verification",
    "traceability",
    "acceptance",
)

ALLOWED_NEXT = {
    "intake": ["contract_freeze"],
    "contract_freeze": ["implementation"],
    "implementation": ["verification", "contract_freeze"],
    "verification": ["traceability", "implementation"],
    "traceability": ["acceptance", "implementation", "verification"],
    "acceptance": [],
}

TASK_STATE_SCHEMA_VERSION = "1.1"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def allowed_next_states(phase: str) -> list[str]:
    if phase not in ALLOWED_NEXT:
        raise ValueError(f"unknown phase: {phase}")
    return list(ALLOWED_NEXT[phase])


def ensure_valid_phase(phase: str) -> None:
    if phase not in PHASE_ORDER:
        raise ValueError(f"unknown phase: {phase}")


def validate_transition(current: str, target: str) -> None:
    ensure_valid_phase(current)
    ensure_valid_phase(target)
    allowed = ALLOWED_NEXT[current]
    if target not in allowed:
        raise ValueError(
            f"illegal phase transition: {current} -> {target}; allowed={allowed}"
        )


def default_task_state(
    task_id: str,
    goal: str,
    owner: str,
    phase: str = "intake",
    *,
    trace_id: str = "",
    run_attempt: int = 1,
    parent_trace_id: str = "",
    session_backend: str = "",
    session_refs: dict[str, str] | None = None,
    current_artifact_ref: str = "",
    pending_approvals: list[str] | None = None,
) -> dict[str, Any]:
    ensure_valid_phase(phase)
    return {
        "schema_version": TASK_STATE_SCHEMA_VERSION,
        "task_id": task_id,
        "goal": goal,
        "phase": phase,
        "owner": owner,
        "allowed_next_states": allowed_next_states(phase),
        "evidence_refs": [],
        "blocking_issues": [],
        "trace_id": trace_id,
        "run_attempt": run_attempt,
        "parent_trace_id": parent_trace_id,
        "session_backend": session_backend,
        "session_refs": session_refs or {},
        "current_artifact_ref": current_artifact_ref,
        "pending_approvals": pending_approvals or [],
        "affected_specs": [],
        "archived": False,
        "updated_at": now_iso(),
    }


def init_event(
    task_id: str,
    phase: str,
    owner: str,
    goal: str,
    *,
    trace_id: str = "",
    run_attempt: int = 1,
    parent_trace_id: str = "",
) -> dict[str, Any]:
    return {
        "timestamp": now_iso(),
        "event": "init_task",
        "task_id": task_id,
        "phase": phase,
        "owner": owner,
        "goal": goal,
        "trace_id": trace_id,
        "run_attempt": run_attempt,
        "parent_trace_id": parent_trace_id,
    }


def advance_event(
    task_id: str,
    current_phase: str,
    target_phase: str,
    owner: str,
    *,
    evidence_refs: list[str] | None = None,
    blocking_issues: list[str] | None = None,
    note: str = "",
    trace_id: str = "",
    run_attempt: int = 1,
    parent_trace_id: str = "",
) -> dict[str, Any]:
    return {
        "timestamp": now_iso(),
        "event": "advance",
        "task_id": task_id,
        "from_phase": current_phase,
        "to_phase": target_phase,
        "owner": owner,
        "evidence_refs": evidence_refs or [],
        "blocking_issues": blocking_issues or [],
        "note": note,
        "trace_id": trace_id,
        "run_attempt": run_attempt,
        "parent_trace_id": parent_trace_id,
    }
