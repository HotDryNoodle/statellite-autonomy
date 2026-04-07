"""Local session backend metadata for the harness adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SESSION_ROOT = REPO_ROOT / "harness" / "runtime" / "sessions"
EXPERT_AGENTS = {
    "architecture_expert_agent",
    "pppar_expert_agent",
    "rdpod_analyst_agent",
}


@dataclass(frozen=True)
class LocalSessionBackend:
    backend_id: str
    root: Path

    @classmethod
    def default(cls) -> "LocalSessionBackend":
        return cls("local-jsonl", SESSION_ROOT)

    def session_path(self, session_ref: str) -> Path:
        safe_ref = session_ref.replace("/", "__")
        return self.root / f"{safe_ref}.jsonl"

    def append_message(self, session_ref: str, role: str, content: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.session_path(session_ref).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"role": role, "content": content}, ensure_ascii=False) + "\n")

    def read_messages(self, session_ref: str) -> list[dict[str, Any]]:
        path = self.session_path(session_ref)
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]


def session_ref_for_agent(task_id: str, agent_name: str) -> str:
    if agent_name == "project_manager_agent":
        return f"pm/{task_id}"
    if agent_name in EXPERT_AGENTS:
        return f"expert/{task_id}/{agent_name}"
    if agent_name == "coding_agent":
        return f"coding/{task_id}"
    if agent_name == "testing_agent":
        return f"testing/{task_id}"
    if agent_name == "eval_agent":
        return f"eval/{task_id}"
    raise ValueError(f"unknown agent session policy: {agent_name}")


def validate_agent_session(task_state: dict, agent_name: str) -> str:
    session_ref = task_state.get("session_refs", {}).get(agent_name, "")
    if not session_ref:
        raise ValueError(f"missing session ref for {agent_name}")
    expected = session_ref_for_agent(task_state["task_id"], agent_name)
    if session_ref != expected:
        raise ValueError(
            f"session isolation violation: expected {expected}, got {session_ref}"
        )
    return session_ref


def validate_resume_backend(task_state: dict, backend: LocalSessionBackend) -> None:
    expected = task_state.get("session_backend", "")
    if expected and expected != backend.backend_id:
        raise ValueError(
            f"session backend mismatch: expected {expected}, got {backend.backend_id}"
        )
