"""Expert registry and contract-family authorization checks."""

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

    def validate_contract_access(
        self, agent_name: str, affected_contracts: list[str]
    ) -> None:
        agent = self.require_active(agent_name)
        allowed = set(agent.get("allowed_contracts", []))
        for contract in affected_contracts:
            if contract not in allowed:
                raise ValueError(
                    f"{agent_name} is not allowed to touch contract: {contract}"
                )


def load_expert_registry() -> ExpertRegistry:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return ExpertRegistry(payload)
