from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.agents_runtime.allowlist import build_tool_command, sanitize_tool_params
from harness.agents_runtime.artifacts import validate_artifact_payload
from harness.agents_runtime.curator import build_knowledge_patch_proposal
from harness.agents_runtime.knowledge import build_knowledge_context
from harness.agents_runtime.registry import load_expert_registry
from harness.agents_runtime.runtime_adapter import HarnessRuntimeAdapter, create_agent_graph
from harness.agents_runtime.sessions import (
    LocalSessionBackend,
    session_ref_for_agent,
    validate_resume_backend,
)
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

    def test_tool_allowlist_builds_eval_command(self) -> None:
        command, artifacts = build_tool_command(
            "eval",
            {
                "domain": "pppar",
                "report_path": "eval/reports/pppar_eval_report.json",
                "yes": True,
            },
        )
        self.assertIn("eval", command)
        self.assertIn("--domain", command)
        self.assertIn("pppar", command)
        self.assertEqual(artifacts, ["eval/reports/pppar_eval_report.json"])

    def test_tool_allowlist_builds_knowledge_search_command(self) -> None:
        command, artifacts = build_tool_command(
            "knowledge_search",
            {
                "agent": "pppar_expert_agent",
                "query": "ambiguity",
                "limit": 5,
            },
        )
        self.assertIn("knowledge", command)
        self.assertIn("search", command)
        self.assertIn("--agent", command)
        self.assertEqual(artifacts, [])

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
            ["/home/hotdry/Documents/expert-system/wiki/pppar/README.md"],
            ["PppFamily_5_1"],
            "capture a corrected expert rule",
        )
        self.assertEqual(proposal["approval_mode"], "human_in_the_loop")

    def test_knowledge_context_schema_is_valid(self) -> None:
        errors = validate_artifact_payload(
            "knowledge_context",
            build_knowledge_context(
                "COLLAB-012",
                "pppar_expert_agent",
                "obsidian_cli",
                "ambiguity",
                ["pppar/pride-pppar-ambiguity-chain.md"],
                "knowledge_context:COLLAB-012:pppar_expert_agent:search",
                ["match_count=1"],
            ),
        )
        self.assertEqual(errors, [])

    def test_dispatch_expert_assigns_isolated_session_and_knowledge_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            backend = LocalSessionBackend("local-jsonl", Path(tmp))
            adapter = HarnessRuntimeAdapter(load_expert_registry(), backend)
            task_state = default_task_state(
                "COLLAB-012",
                "exercise PPP expert dispatch",
                "project-manager",
                phase="contract_freeze",
                session_backend="local-jsonl",
                session_refs={"coding_agent": "coding/COLLAB-012"},
            )
            with patch.object(
                adapter,
                "execute_allowed_tool",
                return_value={
                    "tool_name": "knowledge_search",
                    "command": ["python3"],
                    "return_code": 0,
                    "stdout_excerpt": json.dumps(
                        {
                            "source_mode": "obsidian_cli",
                            "matches": ["pppar/pride-pppar-filtering.md"],
                            "match_count": 1,
                        }
                    ),
                    "stderr_excerpt": "",
                    "artifact_paths": [],
                },
            ):
                result = adapter.dispatch_expert(
                    task_state,
                    "pppar_expert_agent",
                    ["contracts/ppp_family.contract.md"],
                    knowledge_query="ambiguity",
                    handoff_summary="collect PPP family evidence",
                )
        self.assertEqual(
            result["session_ref"],
            session_ref_for_agent("COLLAB-012", "pppar_expert_agent"),
        )
        self.assertEqual(
            result["task_state"]["session_refs"]["coding_agent"],
            "coding/COLLAB-012",
        )
        self.assertEqual(
            result["task_state"]["session_refs"]["pppar_expert_agent"],
            "expert/COLLAB-012/pppar_expert_agent",
        )
        self.assertEqual(
            result["knowledge_context"]["refs"],
            ["pppar/pride-pppar-filtering.md"],
        )

    def test_resume_agent_session_rejects_cross_role_session_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            backend = LocalSessionBackend("local-jsonl", Path(tmp))
            adapter = HarnessRuntimeAdapter(load_expert_registry(), backend)
            task_state = default_task_state(
                "COLLAB-012",
                "exercise resume",
                "project-manager",
                session_backend="local-jsonl",
                session_refs={"pppar_expert_agent": "coding/COLLAB-012"},
            )
            with self.assertRaisesRegex(ValueError, "session isolation violation"):
                adapter.resume_agent_session(task_state, "pppar_expert_agent", backend)

    def test_dispatch_expert_rejects_failed_knowledge_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            backend = LocalSessionBackend("local-jsonl", Path(tmp))
            adapter = HarnessRuntimeAdapter(load_expert_registry(), backend)
            task_state = default_task_state(
                "COLLAB-012",
                "exercise PPP expert dispatch",
                "project-manager",
                phase="contract_freeze",
            )
            with patch.object(
                adapter,
                "execute_allowed_tool",
                return_value={
                    "tool_name": "knowledge_search",
                    "command": ["python3"],
                    "return_code": 1,
                    "stdout_excerpt": "",
                    "stderr_excerpt": "obsidian help failed: The CLI is unable to find Obsidian. If this command is running inside a sandbox, configure OBSIDIAN_CLI_PREFIX to a host bridge command or point OBSIDIAN_CLI_BIN at a host-visible wrapper.",
                    "artifact_paths": [],
                },
            ):
                with self.assertRaisesRegex(ValueError, "host bridge command"):
                    adapter.dispatch_expert(
                        task_state,
                        "pppar_expert_agent",
                        ["contracts/ppp_family.contract.md"],
                        knowledge_query="ambiguity",
                    )


if __name__ == "__main__":
    unittest.main()
