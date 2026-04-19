"""Expert registry and spec-family authorization checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "harness" / "config" / "agent_registry.json"


@dataclass
class ExpertRegistry:
    payload: dict[str, Any]

    def agent_names(self) -> list[str]:
        return sorted(self.payload["agents"].keys())

    def require_active(self, agent_name: str) -> dict[str, Any]:
        agent = self.payload["agents"].get(agent_name)
        if agent is None:
            raise ValueError(f"unknown agent: {agent_name}")
        if agent["status"] != "active":
            raise ValueError(f"agent is not active: {agent_name}")
        return agent

    def validate_spec_access(
        self, agent_name: str, affected_specs: list[str]
    ) -> None:
        agent = self.require_active(agent_name)
        allowed = set(agent.get("allowed_specs", []))
        for spec in affected_specs:
            if spec not in allowed:
                raise ValueError(
                    f"{agent_name} is not allowed to touch spec: {spec}"
                )

    def missing_eval_datasets(self, *, repo_root: Path | None = None) -> list[str]:
        base_root = (repo_root or REPO_ROOT).resolve()
        missing: list[str] = []
        for agent_name in self.agent_names():
            agent = self.require_active(agent_name)
            dataset = str(agent.get("eval_dataset", "") or "").strip()
            if dataset and not (base_root / dataset).exists():
                missing.append(f"{agent_name}:{dataset}")
        return missing


def load_expert_registry(*, repo_root: Path | None = None) -> ExpertRegistry:
    base_root = (repo_root or REPO_ROOT).resolve()
    payload = json.loads((base_root / "harness" / "config" / "agent_registry.json").read_text(encoding="utf-8"))
    return ExpertRegistry(payload)
