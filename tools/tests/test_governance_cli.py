from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_PKG = REPO_ROOT / "tools" / "governance-cli"
if str(GOVERNANCE_PKG) not in sys.path:
    sys.path.insert(0, str(GOVERNANCE_PKG))

import governance_cli  # noqa: E402
import governance_dashboard  # noqa: E402


class GovernanceCliHelpTest(unittest.TestCase):
    def test_governance_cli_help_lists_subcommands(self) -> None:
        completed = subprocess.run(
            ["python3", str(GOVERNANCE_PKG / "governance_cli.py"), "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("quality", completed.stdout)
        self.assertIn("dashboard", completed.stdout)


class GovernanceQualityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.originals = {
            "REPO_ROOT": governance_cli.REPO_ROOT,
            "WORKING_PATH": governance_cli.WORKING_PATH,
            "TASK_BOARD_PATH": governance_cli.TASK_BOARD_PATH,
            "ACTIVE_CONTEXT_PATH": governance_cli.ACTIVE_CONTEXT_PATH,
            "TASK_ARCHIVE_PATH": governance_cli.TASK_ARCHIVE_PATH,
            "PROJECT_STATUS_PATH": governance_cli.PROJECT_STATUS_PATH,
            "BLUEPRINT_ROOT": governance_cli.BLUEPRINT_ROOT,
            "SYSTEM_BLUEPRINT_DIR": governance_cli.SYSTEM_BLUEPRINT_DIR,
            "DECISION_BLUEPRINT_DIR": governance_cli.DECISION_BLUEPRINT_DIR,
        }

    def tearDown(self) -> None:
        for name, value in self.originals.items():
            setattr(governance_cli, name, value)

    def patch_repo(self, repo: Path) -> None:
        governance_cli.REPO_ROOT = repo
        governance_cli.WORKING_PATH = repo / "governance" / "records" / "working" / "current_focus.md"
        governance_cli.TASK_BOARD_PATH = repo / "governance" / "records" / "short_term" / "task_board.md"
        governance_cli.ACTIVE_CONTEXT_PATH = repo / "governance" / "records" / "short_term" / "active_context.md"
        governance_cli.TASK_ARCHIVE_PATH = repo / "governance" / "records" / "task_archive.md"
        governance_cli.PROJECT_STATUS_PATH = repo / "docs" / "_generated" / "project_status.json"
        governance_cli.BLUEPRINT_ROOT = repo / "architecture" / "blueprints"
        governance_cli.SYSTEM_BLUEPRINT_DIR = governance_cli.BLUEPRINT_ROOT / "system"
        governance_cli.DECISION_BLUEPRINT_DIR = governance_cli.BLUEPRINT_ROOT / "decisions"

    def write_common_files(self, repo: Path) -> None:
        for relative in (
            "governance/records/working",
            "governance/records/short_term",
            "governance/records",
            "docs/_generated",
            "architecture/blueprints/system",
            "architecture/blueprints/decisions",
            "harness/eval/agent_workflow/architecture_expert",
            "harness/config",
            "harness/runtime/tasks",
        ):
            (repo / relative).mkdir(parents=True, exist_ok=True)
        (repo / "harness" / "eval" / "agent_workflow" / "architecture_expert" / "README.md").write_text(
            "# architecture eval\n",
            encoding="utf-8",
        )
        (repo / "harness" / "config" / "agent_registry.json").write_text(
            '{\n'
            '  "version": "1.0",\n'
            '  "agents": {\n'
            '    "architecture_expert_agent": {\n'
            '      "status": "active",\n'
            '      "kind": "architecture",\n'
            '      "allowed_specs": ["contracts/layer_boundary.contract.md"],\n'
            '      "eval_dataset": "harness/eval/agent_workflow/architecture_expert"\n'
            "    }\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        (repo / "harness" / "config" / "governance_policy.json").write_text(
            '{\n'
            '  "version": "1.0",\n'
            '  "runtime_required_from_task_id": "COLLAB-013",\n'
            '  "legacy_task_ids": [],\n'
            '  "runtime_retention": {\n'
            '    "mode": "tracked_compact_proof",\n'
            '    "eligible_phase": "acceptance",\n'
            '    "require_archived": true,\n'
            '    "tracked_proof_files": ["task_state.json", "events.jsonl", "compact_manifest.json"],\n'
            '    "drop_tracked_artifacts": true,\n'
            '    "local_spill_dir": "harness/runtime/archive",\n'
            '    "local_spill_tracked": false\n'
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        (repo / "governance" / "records" / "working" / "current_focus.md").write_text(
            "# Current Focus\n\n"
            "## Current Phase\n- `acceptance`\n\n"
            "## In Progress\n- none\n\n"
            "## Current Blockers\n- none\n\n"
            "## Active Specs\n- none\n\n"
            "## Next Acceptance Target\n- none\n\n"
            "## Next Agent\n- none\n",
            encoding="utf-8",
        )
        (repo / "governance" / "records" / "short_term" / "task_board.md").write_text(
            "# Task Board\n\n"
            "| task_id | title | owner_agent | affected_specs | status | acceptance | blockers |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
        (repo / "governance" / "records" / "short_term" / "active_context.md").write_text(
            "# Active Context\n\n"
            "## Current Scope\n- none\n\n"
            "## Active Policy Skills\n- none\n\n"
            "## Acceptance Gates\n- none\n\n"
            "## Handoff Expectations\n- none\n",
            encoding="utf-8",
        )
        (repo / "governance" / "records" / "task_archive.md").write_text(
            "# Task Archive\n\n"
            "Record tasks after they are marked `done`, logged in `agent_activity_log.md`, and no longer needed in short-term memory.\n\n\n"
            "| task_id | title | owner_agent | affected_specs | status | acceptance | evidence |\n"
            "| ---------- | ---------- | ---------- | ---------- | ---------- | ---------- | ---------- |\n",
            encoding="utf-8",
        )
        (repo / "architecture" / "blueprints" / "system" / "harness-product-boundary.puml").write_text(
            "@startuml\n@enduml\n",
            encoding="utf-8",
        )
        (repo / "architecture" / "blueprints" / "system" / "harness-product-boundary.md").write_text(
            "---\nblueprint_type: system\nstatus: active\neffective_specs:\n  - contracts/layer_boundary.contract.md\nreplaced_by: \"\"\n---\n",
            encoding="utf-8",
        )
        (repo / "architecture" / "blueprints" / "decisions" / "freeze-runtime-boundary.puml").write_text(
            "@startuml\n@enduml\n",
            encoding="utf-8",
        )
        (repo / "architecture" / "blueprints" / "decisions" / "freeze-runtime-boundary.md").write_text(
            "---\nblueprint_type: decision\nstatus: active\ncreated_from_task: COLLAB-023\neffective_specs:\n  - governance/policies/harness_workflow.policy.md\nvalid_for_task: COLLAB-023\nreplaced_by: \"\"\nsuperseded_reason: \"\"\n---\n",
            encoding="utf-8",
        )

    def write_runtime_task(
        self,
        repo: Path,
        task_id: str,
        *,
        phase: str,
        owner: str,
        archived: bool = False,
        acceptance_status: str = "",
        event_names: list[str] | None = None,
        retention_mode: str = "",
    ) -> None:
        task_root = repo / "harness" / "runtime" / "tasks" / task_id
        task_root.mkdir(parents=True, exist_ok=True)
        state = {
            "schema_version": "1.1",
            "task_id": task_id,
            "goal": "governance test",
            "phase": phase,
            "owner": owner,
            "allowed_next_states": [],
            "evidence_refs": [],
            "blocking_issues": [],
            "affected_specs": ["governance/policies/harness_workflow.policy.md"],
            "archived": archived,
            "acceptance_status": acceptance_status,
            "updated_at": "2026-04-07T00:00:00+00:00",
        }
        if retention_mode:
            state["retention_mode"] = retention_mode
        (task_root / "task_state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        events = []
        for event_name in event_names or []:
            events.append({"event": event_name, "task_id": task_id})
        (task_root / "events.jsonl").write_text(
            "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + ("\n" if events else ""),
            encoding="utf-8",
        )

    def test_runtime_task_board_consistency_fails_without_runtime_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_common_files(repo)
            self.patch_repo(repo)
            (repo / "governance" / "records" / "short_term" / "task_board.md").write_text(
                "# Task Board\n\n"
                "| task_id | title | owner_agent | affected_specs | status | acceptance | blockers |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| COLLAB-013 | hard cutover | coding_agent | governance/policies/harness_workflow.policy.md | ready_for_impl | none | none |\n",
                encoding="utf-8",
            )

            result = governance_cli.check_runtime_task_board_consistency()
            self.assertFalse(result.ok)
            self.assertIn("COLLAB-013 missing", result.details)

    def test_agent_eval_datasets_fails_when_registry_path_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_common_files(repo)
            self.patch_repo(repo)
            (repo / "harness" / "config" / "agent_registry.json").write_text(
                '{\n'
                '  "version": "1.0",\n'
                '  "agents": {\n'
                '    "architecture_expert_agent": {\n'
                '      "status": "active",\n'
                '      "kind": "architecture",\n'
                '      "allowed_specs": ["contracts/layer_boundary.contract.md"],\n'
                '      "eval_dataset": "harness/eval/agent_workflow/missing_architecture_eval"\n'
                "    }\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            result = governance_cli.check_agent_eval_datasets()
            self.assertFalse(result.ok)
            self.assertIn("missing_architecture_eval", result.details)

    def test_runtime_current_focus_consistency_detects_phase_and_owner_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_common_files(repo)
            self.patch_repo(repo)
            self.write_runtime_task(repo, "COLLAB-013", phase="implementation", owner="coding_agent")
            (repo / "governance" / "records" / "working" / "current_focus.md").write_text(
                "# Current Focus\n\n"
                "## Current Phase\n- `verification`\n\n"
                "## In Progress\n- `COLLAB-013`: governance drift\n\n"
                "## Current Blockers\n- none\n\n"
                "## Active Specs\n- `governance/policies/harness_workflow.policy.md`\n\n"
                "## Next Acceptance Target\n- `COLLAB-013`: governance drift\n\n"
                "## Next Agent\n- `testing_agent`\n",
                encoding="utf-8",
            )

            result = governance_cli.check_runtime_current_focus_consistency()
            self.assertFalse(result.ok)
            self.assertIn("current_focus phase=verification", result.details)
            self.assertIn("next_agent=testing_agent", result.details)

    def test_runtime_archive_consistency_requires_close_and_archive_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_common_files(repo)
            self.patch_repo(repo)
            self.write_runtime_task(
                repo,
                "COLLAB-013",
                phase="acceptance",
                owner="project-manager",
                archived=True,
                acceptance_status="done",
                event_names=["advance"],
            )
            (repo / "governance" / "records" / "task_archive.md").write_text(
                "# Task Archive\n\n"
                "| task_id | title | owner_agent | affected_specs | status | acceptance | evidence |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| COLLAB-013 | hard cutover | project-manager | `governance/policies/harness_workflow.policy.md` | done | archived | `python3 tools/governance-cli/governance_cli.py quality --report-json` |\n",
                encoding="utf-8",
            )

            result = governance_cli.check_runtime_archive_consistency()
            self.assertFalse(result.ok)
            self.assertIn("missing close_task event", result.details)
            self.assertIn("missing archive_task event", result.details)

    def test_runtime_archive_consistency_skips_legacy_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_common_files(repo)
            self.patch_repo(repo)
            (repo / "governance" / "records" / "task_archive.md").write_text(
                "# Task Archive\n\n"
                "| task_id | title | owner_agent | affected_specs | status | acceptance | evidence |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| COLLAB-012 | legacy task | project-manager | `governance/policies/harness_workflow.policy.md` | done | archived | `python3 tools/governance-cli/governance_cli.py quality --report-json` |\n",
                encoding="utf-8",
            )

            result = governance_cli.check_runtime_archive_consistency()
            self.assertTrue(result.ok, result.details)

    def test_runtime_archive_consistency_accepts_compacted_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_common_files(repo)
            self.patch_repo(repo)
            self.write_runtime_task(
                repo,
                "COLLAB-013",
                phase="acceptance",
                owner="project-manager",
                archived=True,
                acceptance_status="compacted",
                event_names=["close_task", "archive_task", "compact_runtime"],
                retention_mode="compacted",
            )
            (repo / "harness" / "runtime" / "tasks" / "COLLAB-013" / "compact_manifest.json").write_text(
                "{\n  \"retained\": []\n}\n",
                encoding="utf-8",
            )
            (repo / "governance" / "records" / "task_archive.md").write_text(
                "# Task Archive\n\n"
                "| task_id | title | owner_agent | affected_specs | status | acceptance | evidence |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| COLLAB-013 | hard cutover | project-manager | `governance/policies/harness_workflow.policy.md` | compacted | archived | `python3 tools/governance-cli/governance_cli.py quality --report-json` |\n",
                encoding="utf-8",
            )

            result = governance_cli.check_runtime_archive_consistency()
            self.assertTrue(result.ok, result.details)

    def test_architecture_blueprints_require_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_common_files(repo)
            self.patch_repo(repo)
            (repo / "architecture" / "blueprints" / "system" / "broken.md").write_text(
                "---\nblueprint_type: system\nstatus: unknown\n---\n",
                encoding="utf-8",
            )
            (repo / "architecture" / "blueprints" / "system" / "broken.puml").write_text(
                "@startuml\n@enduml\n",
                encoding="utf-8",
            )

            result = governance_cli.check_architecture_blueprints()
            self.assertFalse(result.ok)
            self.assertIn("broken.md", result.details)

    def test_architecture_freeze_artifacts_require_existing_blueprints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_common_files(repo)
            self.patch_repo(repo)
            artifacts = repo / "harness" / "runtime" / "tasks" / "COLLAB-023" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "architecture_freeze.acceptance.json").write_text(
                '{\n  "blueprint_refs": ["architecture/blueprints/decisions/missing.puml"]\n}\n',
                encoding="utf-8",
            )

            result = governance_cli.check_architecture_freeze_artifacts()
            self.assertFalse(result.ok)
            self.assertIn("missing blueprint", result.details)


class PromptDocsTest(unittest.TestCase):
    def test_main_path_prompt_docs_stay_within_limit(self) -> None:
        result = governance_cli.check_prompt_doc_limits()
        self.assertTrue(result.ok, result.details)

    def test_project_manager_references_exist_and_are_linked(self) -> None:
        result = governance_cli.check_project_manager_references()
        self.assertTrue(result.ok, result.details)

    def test_prompt_doc_routing_prefers_progressive_disclosure(self) -> None:
        result = governance_cli.check_prompt_doc_routing()
        self.assertTrue(result.ok, result.details)

    def test_prompt_doc_limit_check_catches_oversized_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            oversized = repo / "AGENTS.md"
            oversized.write_text("\n".join("x" for _ in range(101)) + "\n", encoding="utf-8")
            original_limits = governance_cli.PROMPT_DOC_LIMITS
            try:
                governance_cli.PROMPT_DOC_LIMITS = {oversized: 100}
                result = governance_cli.check_prompt_doc_limits()
            finally:
                governance_cli.PROMPT_DOC_LIMITS = original_limits
            self.assertFalse(result.ok)
            self.assertIn("101 lines > 100", result.details)


class GovernanceDashboardDisplayTest(unittest.TestCase):
    def test_dashboard_normalizes_legacy_acceptance_gate_display(self) -> None:
        payload = governance_dashboard.build_status_payload(
            working={
                "Current Phase": ["implementation"],
                "In Progress": ["none"],
                "Current Blockers": ["none"],
                "Active Specs": ["none"],
                "Next Acceptance Target": ["none"],
                "Next Agent": ["none"],
            },
            tasks=[],
            context={
                "Current Scope": ["none"],
                "Active Policy Skills": ["none"],
                "Acceptance Gates": ["python3 scripts/check_quality.py --report-json"],
                "Handoff Expectations": ["none"],
            },
            limitations={"Accepted Limitations": ["none"], "Open Risks": ["none"]},
            decisions=[],
            activities=[],
            traceability_status={
                "contract_count": 15,
                "verify_count": 12,
                "contracts_with_code": 8,
                "contracts_with_tests": 6,
                "verifies_with_tests": 8,
            },
            compliance_status={"ok": True, "policy_count": 3, "failures": []},
        )
        self.assertEqual(
            payload["acceptance_gates"],
            ["python3 tools/governance-cli/governance_cli.py quality --report-json"],
        )


if __name__ == "__main__":
    unittest.main()
