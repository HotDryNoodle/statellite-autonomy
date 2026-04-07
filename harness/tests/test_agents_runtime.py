from __future__ import annotations

import json
import unittest

from harness.agents_runtime.allowlist import build_tool_command, sanitize_tool_params
from harness.agents_runtime.artifacts import validate_artifact_payload
from harness.agents_runtime.curator import build_knowledge_patch_proposal
from harness.agents_runtime.registry import load_expert_registry
from harness.agents_runtime.runtime_adapter import HarnessRuntimeAdapter, create_agent_graph
from harness.agents_runtime.sessions import LocalSessionBackend, validate_resume_backend
from harness.agents_runtime.tracing import redact_text
from harness.orchestrator.runtime_model import default_task_state, validate_transition


class AgentsRuntimeTest(unittest.TestCase):
    def test_task_brief_schema_requires_contract_fields(self) -> None:
        errors = validate_artifact_payload(
            "task_brief",
            {
                "schema_version": "1.0",
                "artifact_version": "1.0",
                "task_id": "COLLAB-011",
                "goal": "wire PM task brief",
                "phase": "intake",
                "affected_contracts": ["contracts/harness_workflow.contract.md"],
                "clause_refs": ["HarnessWorkflow_2_2"],
            },
        )
        self.assertEqual(errors, [])

    def test_tool_allowlist_rejects_unknown_param(self) -> None:
        with self.assertRaisesRegex(ValueError, "disallowed param"):
            sanitize_tool_params("build", {"unexpected": True})

    def test_tool_allowlist_builds_expected_command(self) -> None:
        command, artifacts = build_tool_command(
            "benchmark",
            {
                "report_path": "eval/reports/time_benchmark_report.json",
                "yes": True,
            },
        )
        self.assertIn("benchmark", command)
        self.assertIn("--report-path", command)
        self.assertEqual(artifacts, ["eval/reports/time_benchmark_report.json"])

    def test_registry_enforces_contract_access(self) -> None:
        registry = load_expert_registry()
        registry.validate_contract_access(
            "pppar_expert_agent",
            ["contracts/ppp_family.contract.md"],
        )
        with self.assertRaisesRegex(ValueError, "not allowed"):
            registry.validate_contract_access(
                "pppar_expert_agent",
                ["contracts/rdpod_family.contract.md"],
            )

    def test_resume_requires_same_backend(self) -> None:
        task_state = default_task_state(
            "COLLAB-011",
            "exercise resume",
            "project-manager",
            session_backend="local-jsonl",
        )
        validate_resume_backend(task_state, LocalSessionBackend.default())
        with self.assertRaisesRegex(ValueError, "session backend mismatch"):
            validate_resume_backend(
                task_state,
                LocalSessionBackend("other-backend", LocalSessionBackend.default().root),
            )

    def test_runtime_adapter_uses_shared_transition_rules(self) -> None:
        adapter = HarnessRuntimeAdapter(load_expert_registry(), LocalSessionBackend.default())
        task_state = default_task_state("COLLAB-011", "phase check", "project-manager")
        with self.assertRaisesRegex(ValueError, "illegal phase transition"):
            validate_transition("intake", "verification")
        with self.assertRaisesRegex(ValueError, "illegal phase transition"):
            adapter.run_phase(task_state, "verification", {})

    def test_tracing_redaction_masks_repo_root_and_tokens(self) -> None:
        redacted = redact_text(
            "token=secret-value path=/home/hotdry/projects/statellite-autonomy-plugin/file"
        )
        self.assertIn("[REDACTED]", redacted)
        self.assertIn("<repo>", redacted)

    def test_create_agent_graph_includes_architecture_agent(self) -> None:
        graph = create_agent_graph(
            "COLLAB-011",
            ["contracts/harness_workflow.contract.md"],
            {"mode": "sync"},
        )
        self.assertIn("architecture_expert_agent", graph["agents"])

    def test_curator_proposal_is_human_in_loop(self) -> None:
        proposal = build_knowledge_patch_proposal(
            "COLLAB-011",
            ["trace:1"],
            ["skills/pppar-expert/references/CHANGELOG.md"],
            ["PppFamily_4_1"],
            "capture a corrected expert rule",
        )
        self.assertEqual(proposal["approval_mode"], "human_in_the_loop")


if __name__ == "__main__":
    unittest.main()
