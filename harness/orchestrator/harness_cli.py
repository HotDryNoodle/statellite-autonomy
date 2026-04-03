#!/usr/bin/env python3
"""Minimal harness runtime CLI for task lifecycle artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = REPO_ROOT / "harness" / "runtime" / "tasks"
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    state = {
        "task_id": args.task_id,
        "goal": args.goal,
        "phase": args.phase,
        "owner": args.owner,
        "allowed_next_states": ALLOWED_NEXT[args.phase],
        "evidence_refs": [],
        "blocking_issues": [],
        "updated_at": now_iso(),
    }
    write_json(state_path(args.task_id), state)
    append_event(
        args.task_id,
        {
            "timestamp": state["updated_at"],
            "event": "init_task",
            "phase": args.phase,
            "owner": args.owner,
            "goal": args.goal,
        },
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
    state = load_state(args.task_id)
    current = state["phase"]
    allowed = ALLOWED_NEXT[current]
    if args.phase not in allowed:
        raise SystemExit(
            f"illegal phase transition for {args.task_id}: {current} -> {args.phase}; allowed={allowed}"
        )
    state["phase"] = args.phase
    state["owner"] = args.owner or state["owner"]
    state["allowed_next_states"] = ALLOWED_NEXT[args.phase]
    state["updated_at"] = now_iso()
    if args.evidence:
        state["evidence_refs"].extend(args.evidence)
    if args.blocker:
        state["blocking_issues"] = args.blocker
    write_json(state_path(args.task_id), state)
    append_event(
        args.task_id,
        {
            "timestamp": state["updated_at"],
            "event": "advance",
            "from_phase": current,
            "to_phase": args.phase,
            "owner": state["owner"],
            "evidence_refs": args.evidence or [],
            "blocking_issues": args.blocker or [],
            "note": args.note or "",
        },
    )
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
