"""Local session backend metadata for the harness adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SESSION_ROOT = REPO_ROOT / "harness" / "runtime" / "sessions"


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


def validate_resume_backend(task_state: dict, backend: LocalSessionBackend) -> None:
    expected = task_state.get("session_backend", "")
    if expected and expected != backend.backend_id:
        raise ValueError(
            f"session backend mismatch: expected {expected}, got {backend.backend_id}"
        )
