"""Agents SDK-oriented harness adapter scaffold with local fallbacks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.agents_runtime.allowlist import execute_tool
from harness.agents_runtime.artifacts import validate_artifact_payload
from harness.agents_runtime.registry import ExpertRegistry, load_expert_registry
from harness.agents_runtime.sessions import LocalSessionBackend, validate_resume_backend
from harness.agents_runtime.tracing import redact_text
from harness.orchestrator.runtime_model import allowed_next_states, validate_transition

try:  # pragma: no cover - optional runtime import
    from agents import Agent  # type: ignore
except ImportError:  # pragma: no cover - local test environments may not have it
    Agent = None


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class HarnessRuntimeAdapter:
    registry: ExpertRegistry
    session_backend: LocalSessionBackend

    def create_agent_graph(
        self, task_id: str, active_contracts: list[str], workflow_config: dict[str, Any]
    ) -> dict[str, Any]:
        graph = {
            "task_id": task_id,
            "sdk_available": Agent is not None,
            "session_backend": self.session_backend.backend_id,
            "active_contracts": active_contracts,
            "agents": {
                "project_manager_agent": {"role": "orchestrator"},
                "architecture_expert_agent": {
                    "role": "architecture",
                    "trigger_contracts": ["contracts/layer_boundary.contract.md"],
                },
                "pppar_expert_agent": {"role": "expert"},
                "rdpod_analyst_agent": {"role": "expert"},
                "coding_agent": {"role": "implementation"},
                "testing_agent": {"role": "verification"},
                "eval_agent": {"role": "tool_router"},
            },
            "workflow_config": workflow_config,
        }
        return graph

    def validate_handoff(self, payload: dict[str, Any], current_task_state: dict[str, Any]) -> None:
        errors = validate_artifact_payload("handoff", payload)
        if errors:
            raise ValueError("; ".join(errors))
        validate_transition(current_task_state["phase"], payload["phase"])

    def run_phase(
        self, task_state: dict[str, Any], phase: str, input_artifact: dict[str, Any]
    ) -> dict[str, Any]:
        validate_transition(task_state["phase"], phase)
        artifact_name = input_artifact.get("kind", "")
        if artifact_name:
            errors = validate_artifact_payload(artifact_name, input_artifact)
            if errors:
                raise ValueError("; ".join(errors))
        return {
            "phase": phase,
            "allowed_next_states": allowed_next_states(phase),
            "current_artifact_ref": input_artifact.get("artifact_ref", ""),
            "trace_excerpt": redact_text(str(input_artifact)) if input_artifact else "",
        }

    def resume_phase(
        self, task_state: dict[str, Any], session_backend_ref: LocalSessionBackend
    ) -> dict[str, Any]:
        validate_resume_backend(task_state, session_backend_ref)
        return {
            "task_id": task_state["task_id"],
            "phase": task_state["phase"],
            "session_refs": task_state.get("session_refs", {}),
            "pending_approvals": task_state.get("pending_approvals", []),
        }

    def validate_expert_contracts(
        self, agent_name: str, affected_contracts: list[str]
    ) -> None:
        self.registry.validate_contract_access(agent_name, affected_contracts)

    def execute_allowed_tool(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        result = execute_tool(tool_name, params)
        return {
            "tool_name": result.tool_name,
            "command": result.command,
            "return_code": result.return_code,
            "stdout_excerpt": redact_text(result.stdout_excerpt),
            "stderr_excerpt": redact_text(result.stderr_excerpt),
            "artifact_paths": result.artifact_paths,
        }


def create_agent_graph(
    task_id: str, active_contracts: list[str], workflow_config: dict[str, Any]
) -> dict[str, Any]:
    adapter = HarnessRuntimeAdapter(load_expert_registry(), LocalSessionBackend.default())
    return adapter.create_agent_graph(task_id, active_contracts, workflow_config)
