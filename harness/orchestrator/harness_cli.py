#!/usr/bin/env python3
"""Minimal harness runtime CLI for task lifecycle artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from runtime_model import (
    PHASE_ORDER,
    advance_event,
    allowed_next_states,
    default_task_state,
    init_event,
    validate_transition,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = REPO_ROOT / "harness" / "runtime" / "tasks"


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_state(task_id: str) -> dict[str, Any]:
    return json.loads(state_path(task_id).read_text(encoding="utf-8"))


def append_event(task_id: str, payload: dict[str, Any]) -> None:
    event_file = events_path(task_id)
    with event_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def cmd_init_task(args: argparse.Namespace) -> int:
    ensure_task_dir(args.task_id)
    if state_path(args.task_id).exists() and not args.force:
        raise SystemExit(f"task already exists: {args.task_id}")
    state = default_task_state(
        args.task_id,
        args.goal,
        args.owner,
        args.phase,
        trace_id=args.trace_id,
        run_attempt=args.run_attempt,
        parent_trace_id=args.parent_trace_id,
        session_backend=args.session_backend,
    )
    write_json(state_path(args.task_id), state)
    event = init_event(
        args.task_id,
        args.phase,
        args.owner,
        args.goal,
        trace_id=state["trace_id"],
        run_attempt=state["run_attempt"],
        parent_trace_id=state["parent_trace_id"],
    )
    event["timestamp"] = state["updated_at"]
    append_event(args.task_id, event)
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
    state = load_state(args.task_id)
    current = state["phase"]
    try:
        validate_transition(current, args.phase)
    except ValueError as exc:
        raise SystemExit(f"{exc} for {args.task_id}") from exc
    state["phase"] = args.phase
    state["owner"] = args.owner or state["owner"]
    state["allowed_next_states"] = allowed_next_states(args.phase)
    state["updated_at"] = init_event(
        args.task_id,
        args.phase,
        state["owner"],
        state["goal"],
    )["timestamp"]
    if args.evidence:
        state["evidence_refs"].extend(args.evidence)
    if args.blocker:
        state["blocking_issues"] = args.blocker
    write_json(state_path(args.task_id), state)
    event = advance_event(
        args.task_id,
        current,
        args.phase,
        state["owner"],
        evidence_refs=args.evidence,
        blocking_issues=args.blocker,
        note=args.note or "",
        trace_id=state.get("trace_id", ""),
        run_attempt=state.get("run_attempt", 1),
        parent_trace_id=state.get("parent_trace_id", ""),
    )
    event["timestamp"] = state["updated_at"]
    append_event(args.task_id, event)
    print(json.dumps(state, indent=2, ensure_ascii=False))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    history: list[dict[str, Any]] = []
    event_file = events_path(args.task_id)
    if event_file.exists():
        for line in event_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                history.append(json.loads(line))
    print(json.dumps(history, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_task = subparsers.add_parser("init-task")
    init_task.add_argument("--task-id", required=True)
    init_task.add_argument("--goal", required=True)
    init_task.add_argument("--phase", choices=PHASE_ORDER, default="intake")
    init_task.add_argument("--owner", default="project-manager")
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

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
