from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "harness" / "orchestrator" / "harness_cli.py"
RUNTIME_MODEL = REPO_ROOT / "harness" / "orchestrator" / "runtime_model.py"


class HarnessCliTest(unittest.TestCase):
    def stage_runtime_repo(self, repo: Path) -> Path:
        for relative in (
            "harness/orchestrator",
            "harness/agents_runtime",
            "harness/config",
            "harness/schemas",
            "tools/nav-toolchain-cli",
            "docs/memory/working",
            "docs/memory/short_term",
            "docs/traceability",
        ):
            (repo / relative).mkdir(parents=True, exist_ok=True)
        for relative in (
            "harness/orchestrator/harness_cli.py",
            "harness/orchestrator/runtime_model.py",
            "harness/agents_runtime/__init__.py",
            "harness/agents_runtime/allowlist.py",
            "harness/agents_runtime/artifacts.py",
            "harness/agents_runtime/curator.py",
            "harness/agents_runtime/knowledge.py",
            "harness/agents_runtime/registry.py",
            "harness/agents_runtime/runtime_adapter.py",
            "harness/agents_runtime/sessions.py",
            "harness/agents_runtime/tracing.py",
            "harness/config/agent_registry.json",
            "harness/config/governance_policy.json",
            "harness/config/knowledge_registry.json",
            "harness/config/tool_allowlist.json",
            "harness/schemas/architecture_freeze.schema.json",
            "harness/schemas/handoff.schema.json",
            "harness/schemas/knowledge_context.schema.json",
            "harness/schemas/task_brief.schema.json",
            "tools/nav-toolchain-cli/toolchain_cli.py",
            "tools/nav-toolchain-cli/knowledge_ops.py",
            "docs/memory/working/current_focus.md",
            "docs/memory/short_term/task_board.md",
            "docs/memory/short_term/active_context.md",
            "docs/traceability/agent_activity_log.md",
            "docs/traceability/task_archive.md",
        ):
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, target)
        return repo / "harness" / "orchestrator" / "harness_cli.py"

    def run_cli(self, cli_path: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HARNESS_REPO_ROOT"] = str(cwd)
        return subprocess.run(
            ["python3", str(cli_path), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
        )

    def prepare_acceptance_task(self, repo: Path, runtime_cli: Path) -> None:
        obsidian_bin = repo / "fake-obsidian"
        obsidian_bin.write_text(
            """#!/bin/sh
if [ "${1#vault=}" != "$1" ]; then
  shift 1
fi
cmd="$1"
case "$cmd" in
  help)
    echo "Obsidian help"
    exit 0
    ;;
  search)
    echo '["pppar/pride-pppar-ambiguity-chain.md"]'
    exit 0
    ;;
  *)
    echo "unsupported command: $cmd" >&2
    exit 1
    ;;
esac
""",
            encoding="utf-8",
        )
        obsidian_bin.chmod(0o755)
        env = os.environ.copy()
        env["HARNESS_REPO_ROOT"] = str(repo)
        env["OBSIDIAN_CLI_BIN"] = str(obsidian_bin)
        workflow = subprocess.run(
            [
                "python3",
                str(runtime_cli),
                "pm-workflow",
                "--task-id",
                "COLLAB-TEST",
                "--goal",
                "run PM workflow",
                "--agent",
                "pppar_expert_agent",
                "--contract",
                "contracts/ppp_family.contract.md",
                "--knowledge-query",
                "ambiguity",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(workflow.returncode, 0, workflow.stderr)
        for phase in ("verification", "traceability", "acceptance"):
            advanced = self.run_cli(
                runtime_cli,
                "advance",
                "--task-id",
                "COLLAB-TEST",
                "--phase",
                phase,
                "--owner",
                "project-manager" if phase == "acceptance" else ("testing_agent" if phase == "verification" else "project-manager"),
                cwd=repo,
            )
            self.assertEqual(advanced.returncode, 0, advanced.stderr)

    def test_init_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)

            init = self.run_cli(
                runtime_cli,
                "init-task",
                "--task-id", "COLLAB-TEST",
                "--goal", "exercise harness runtime",
                cwd=repo,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            state = json.loads(init.stdout)
            self.assertEqual(state["phase"], "intake")

            advance = self.run_cli(
                runtime_cli,
                "advance",
                "--task-id", "COLLAB-TEST",
                "--phase", "contract_freeze",
                "--note", "moved to contract freeze",
                cwd=repo,
            )
            self.assertEqual(advance.returncode, 0, advance.stderr)
            advanced_state = json.loads(advance.stdout)
            self.assertEqual(advanced_state["phase"], "contract_freeze")

            replay = self.run_cli(runtime_cli, "replay", "--task-id", "COLLAB-TEST", cwd=repo)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            history = json.loads(replay.stdout)
            self.assertEqual(len(history), 2)
            self.assertEqual(history[1]["to_phase"], "contract_freeze")

    def test_illegal_transition_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)

            init = self.run_cli(
                runtime_cli,
                "init-task",
                "--task-id", "COLLAB-TEST",
                "--goal", "exercise harness runtime",
                cwd=repo,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            invalid = self.run_cli(
                runtime_cli,
                "advance",
                "--task-id", "COLLAB-TEST",
                "--phase", "verification",
                cwd=repo,
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("illegal phase transition", invalid.stderr + invalid.stdout)

    def test_dispatch_expert_persists_session_and_knowledge_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)

            init = self.run_cli(
                runtime_cli,
                "init-task",
                "--task-id", "COLLAB-TEST",
                "--goal", "exercise expert dispatch",
                "--phase", "contract_freeze",
                "--session-backend", "local-jsonl",
                cwd=repo,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            obsidian_bin = repo / "fake-obsidian"
            obsidian_bin.write_text(
                """#!/bin/sh
if [ "${1#vault=}" != "$1" ]; then
  shift 1
fi
cmd="$1"
case "$cmd" in
  help)
    echo "Obsidian help"
    exit 0
    ;;
  search)
    echo '["pppar/pride-pppar-filtering.md"]'
    exit 0
    ;;
  *)
    echo "unsupported command: $cmd" >&2
    exit 1
    ;;
esac
""",
                encoding="utf-8",
            )
            obsidian_bin.chmod(0o755)

            env = os.environ.copy()
            env["HARNESS_REPO_ROOT"] = str(repo)
            env["OBSIDIAN_CLI_BIN"] = str(obsidian_bin)
            dispatch = subprocess.run(
                [
                    "python3",
                    str(runtime_cli),
                    "dispatch-expert",
                    "--task-id",
                    "COLLAB-TEST",
                    "--agent",
                    "pppar_expert_agent",
                    "--contract",
                    "contracts/ppp_family.contract.md",
                    "--knowledge-query",
                    "ambiguity",
                    "--summary",
                    "collect PPP evidence",
                ],
                cwd=repo,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(dispatch.returncode, 0, dispatch.stderr)
            payload = json.loads(dispatch.stdout)
            self.assertEqual(
                payload["session_ref"],
                "expert/COLLAB-TEST/pppar_expert_agent",
            )
            self.assertEqual(
                payload["knowledge_context"]["refs"],
                ["pppar/pride-pppar-filtering.md"],
            )

            state = json.loads(
                (repo / "harness" / "runtime" / "tasks" / "COLLAB-TEST" / "task_state.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(state["owner"], "pppar_expert_agent")
            self.assertEqual(
                state["session_refs"]["pppar_expert_agent"],
                "expert/COLLAB-TEST/pppar_expert_agent",
            )
            self.assertIn(
                "pppar/pride-pppar-filtering.md",
                state["evidence_refs"],
            )

            history = json.loads(
                self.run_cli(runtime_cli, "replay", "--task-id", "COLLAB-TEST", cwd=repo).stdout
            )
            self.assertEqual(history[-1]["event"], "dispatch_expert")
            self.assertEqual(history[-1]["agent_name"], "pppar_expert_agent")

    def test_pm_workflow_runs_init_dispatch_and_advance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)
            obsidian_bin = repo / "fake-obsidian"
            obsidian_bin.write_text(
                """#!/bin/sh
if [ "${1#vault=}" != "$1" ]; then
  shift 1
fi
cmd="$1"
case "$cmd" in
  help)
    echo "Obsidian help"
    exit 0
    ;;
  search)
    echo '["pppar/pride-pppar-ambiguity-chain.md"]'
    exit 0
    ;;
  *)
    echo "unsupported command: $cmd" >&2
    exit 1
    ;;
esac
""",
                encoding="utf-8",
            )
            obsidian_bin.chmod(0o755)

            env = os.environ.copy()
            env["HARNESS_REPO_ROOT"] = str(repo)
            env["OBSIDIAN_CLI_BIN"] = str(obsidian_bin)
            workflow = subprocess.run(
                [
                    "python3",
                    str(runtime_cli),
                    "pm-workflow",
                    "--task-id",
                    "COLLAB-TEST",
                    "--goal",
                    "run PM workflow",
                    "--agent",
                    "pppar_expert_agent",
                    "--contract",
                    "contracts/ppp_family.contract.md",
                    "--knowledge-query",
                    "ambiguity",
                ],
                cwd=repo,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(workflow.returncode, 0, workflow.stderr)
            payload = json.loads(workflow.stdout)
            self.assertEqual(payload["task_state"]["phase"], "implementation")
            self.assertEqual(payload["task_state"]["owner"], "coding_agent")
            self.assertEqual(len(payload["steps"]), 7)
            self.assertEqual(payload["steps"][0]["step"], "init-task")
            self.assertEqual(payload["steps"][1]["phase"], "contract_freeze")
            self.assertEqual(payload["steps"][2]["step"], "task-brief")
            self.assertEqual(payload["steps"][3]["step"], "dispatch-expert")
            self.assertEqual(payload["steps"][4]["phase"], "implementation")
            self.assertEqual(payload["steps"][5]["step"], "handoff")
            self.assertEqual(payload["steps"][6]["step"], "sync-governance")
            self.assertEqual(
                payload["knowledge_context"]["refs"],
                ["pppar/pride-pppar-ambiguity-chain.md"],
            )
            self.assertIn("task_brief", payload["artifacts"])
            self.assertIn("handoff", payload["artifacts"])

            task_brief = json.loads((repo / payload["artifacts"]["task_brief"]).read_text(encoding="utf-8"))
            self.assertEqual(task_brief["task_id"], "COLLAB-TEST")
            self.assertEqual(task_brief["phase"], "contract_freeze")

            handoff = json.loads((repo / payload["artifacts"]["handoff"]).read_text(encoding="utf-8"))
            self.assertEqual(handoff["from_agent"], "pppar_expert_agent")
            self.assertEqual(handoff["to_agent"], "coding_agent")
            self.assertEqual(handoff["phase"], "implementation")

            current_focus = (repo / "docs/memory/working/current_focus.md").read_text(encoding="utf-8")
            self.assertIn("`implementation`", current_focus)
            self.assertIn("COLLAB-TEST", current_focus)
            self.assertIn(payload["artifacts"]["task_brief"], current_focus)
            self.assertIn(payload["artifacts"]["handoff"], current_focus)

            task_board = (repo / "docs/memory/short_term/task_board.md").read_text(encoding="utf-8")
            self.assertIn("| COLLAB-TEST |", task_board)
            self.assertIn("ready_for_impl", task_board)
            self.assertIn(payload["artifacts"]["handoff"], task_board)

            active_context = (repo / "docs/memory/short_term/active_context.md").read_text(encoding="utf-8")
            self.assertIn("Current PM workflow task:", active_context)
            self.assertIn(payload["artifacts"]["task_brief"], active_context)

            activity_log = (repo / "docs/traceability/agent_activity_log.md").read_text(encoding="utf-8")
            self.assertIn("synchronized PM workflow governance state", activity_log)
            self.assertIn("COLLAB-TEST", activity_log)

            history = json.loads(
                self.run_cli(runtime_cli, "replay", "--task-id", "COLLAB-TEST", cwd=repo).stdout
            )
            self.assertEqual(
                [event["event"] for event in history],
                ["init_task", "advance", "dispatch_expert", "advance"],
            )

            resumed = self.run_cli(
                runtime_cli,
                "resume-agent",
                "--task-id",
                "COLLAB-TEST",
                "--agent",
                "pppar_expert_agent",
                cwd=repo,
            )
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            resumed_payload = json.loads(resumed.stdout)
            self.assertEqual(
                resumed_payload["session_ref"],
                "expert/COLLAB-TEST/pppar_expert_agent",
            )
            self.assertEqual(len(resumed_payload["messages"]), 2)

    def test_pm_workflow_supports_general_tasks_without_expert_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)

            workflow = self.run_cli(
                runtime_cli,
                "pm-workflow",
                "--task-id",
                "COLLAB-TEST",
                "--goal",
                "run PM workflow without expert",
                "--contract",
                "governance/harness_workflow.policy.md",
                "--skip-dispatch",
                cwd=repo,
            )
            self.assertEqual(workflow.returncode, 0, workflow.stderr)
            payload = json.loads(workflow.stdout)
            self.assertEqual(payload["task_state"]["phase"], "implementation")
            self.assertEqual(payload["task_state"]["owner"], "coding_agent")
            self.assertEqual([step["step"] for step in payload["steps"]], [
                "init-task",
                "advance",
                "task-brief",
                "advance",
                "handoff",
                "sync-governance",
            ])

            handoff = json.loads((repo / payload["artifacts"]["handoff"]).read_text(encoding="utf-8"))
            self.assertEqual(handoff["from_agent"], "project-manager")
            self.assertEqual(handoff["to_agent"], "coding_agent")
            self.assertEqual(handoff["architecture_freeze_ref"], "")

    def test_freeze_architecture_persists_artifact_and_links_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)
            blueprint_root = repo / "docs" / "architecture" / "blueprints" / "decisions"
            blueprint_root.mkdir(parents=True, exist_ok=True)
            (blueprint_root / "harness-product-boundary.puml").write_text("@startuml\n@enduml\n", encoding="utf-8")
            (blueprint_root / "harness-product-boundary.md").write_text(
                "---\nblueprint_type: decision\nstatus: active\ncreated_from_task: COLLAB-TEST\n"
                "effective_specs:\n  - contracts/layer_boundary.contract.md\nvalid_for_task: COLLAB-TEST\n"
                "replaced_by: ''\nsuperseded_reason: ''\n---\n",
                encoding="utf-8",
            )

            workflow = self.run_cli(
                runtime_cli,
                "pm-workflow",
                "--task-id",
                "COLLAB-TEST",
                "--goal",
                "freeze architecture boundary",
                "--contract",
                "contracts/layer_boundary.contract.md",
                "--skip-dispatch",
                "--problem-statement",
                "freeze harness/product separation",
                "--boundary-decision",
                "harness owns orchestration only",
                "--dependency-direction",
                "product depends on contracts, not on harness runtime",
                "--interface-freeze-point",
                "runtime artifacts are orchestration-only",
                "--ownership-lifecycle-constraint",
                "project-manager owns phase transitions",
                "--nfr-constraint",
                "blueprints must remain repo-local and versioned",
                "--blueprint-ref",
                "docs/architecture/blueprints/decisions/harness-product-boundary.puml",
                "--blueprint-ref",
                "docs/architecture/blueprints/decisions/harness-product-boundary.md",
                cwd=repo,
            )
            self.assertEqual(workflow.returncode, 0, workflow.stderr)
            payload = json.loads(workflow.stdout)
            self.assertIn("architecture_freeze", payload["artifacts"])

            freeze = json.loads((repo / payload["artifacts"]["architecture_freeze"]).read_text(encoding="utf-8"))
            self.assertEqual(freeze["problem_statement"], "freeze harness/product separation")
            self.assertIn(
                "docs/architecture/blueprints/decisions/harness-product-boundary.puml",
                freeze["blueprint_refs"],
            )

            handoff = json.loads((repo / payload["artifacts"]["handoff"]).read_text(encoding="utf-8"))
            self.assertEqual(handoff["architecture_freeze_ref"], payload["artifacts"]["architecture_freeze"])

            state = json.loads(
                (repo / "harness" / "runtime" / "tasks" / "COLLAB-TEST" / "task_state.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(state["architecture_freeze_ref"], payload["artifacts"]["architecture_freeze"])

    def test_freeze_architecture_requires_blueprint_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)

            init = self.run_cli(
                runtime_cli,
                "init-task",
                "--task-id",
                "COLLAB-TEST",
                "--goal",
                "freeze architecture",
                "--phase",
                "contract_freeze",
                cwd=repo,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            freeze = self.run_cli(
                runtime_cli,
                "freeze-architecture",
                "--task-id",
                "COLLAB-TEST",
                "--contract",
                "contracts/layer_boundary.contract.md",
                "--problem-statement",
                "missing blueprint",
                "--boundary-decision",
                "freeze boundary",
                "--dependency-direction",
                "one-way dependencies",
                "--interface-freeze-point",
                "runtime API is orchestration-only",
                "--ownership-lifecycle-constraint",
                "pm owns lifecycle",
                "--nfr-constraint",
                "versioned artifacts only",
                cwd=repo,
            )
            self.assertNotEqual(freeze.returncode, 0)
            self.assertIn("required", freeze.stderr + freeze.stdout)

    def test_sync_governance_repairs_active_docs_from_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)

            workflow = self.run_cli(
                runtime_cli,
                "pm-workflow",
                "--task-id",
                "COLLAB-TEST",
                "--goal",
                "repair governance docs",
                "--contract",
                "governance/harness_workflow.policy.md",
                "--skip-dispatch",
                cwd=repo,
            )
            self.assertEqual(workflow.returncode, 0, workflow.stderr)

            (repo / "docs/memory/working/current_focus.md").write_text(
                "# Current Focus\n\n## Current Phase\n- `verification`\n\n## In Progress\n- `COLLAB-TEST`: drift\n\n## Current Blockers\n- none\n\n## Active Specs\n- none\n\n## Next Acceptance Target\n- none\n\n## Next Agent\n- `testing_agent`\n",
                encoding="utf-8",
            )
            (repo / "docs/memory/short_term/task_board.md").write_text(
                "# Task Board\n\n| task_id | title | owner_agent | affected_specs | status | acceptance | blockers |\n| --- | --- | --- | --- | --- | --- | --- |\n| COLLAB-TEST | drift | testing_agent | none | ready_for_verify | none | none |\n",
                encoding="utf-8",
            )

            repaired = self.run_cli(
                runtime_cli,
                "sync-governance",
                "--task-id",
                "COLLAB-TEST",
                cwd=repo,
            )
            self.assertEqual(repaired.returncode, 0, repaired.stderr)
            payload = json.loads(repaired.stdout)
            self.assertEqual(payload["mode"], "active")

            current_focus = (repo / "docs/memory/working/current_focus.md").read_text(encoding="utf-8")
            self.assertIn("`implementation`", current_focus)
            self.assertIn("COLLAB-TEST", current_focus)

            task_board = (repo / "docs/memory/short_term/task_board.md").read_text(encoding="utf-8")
            self.assertIn("| COLLAB-TEST |", task_board)
            self.assertIn("ready_for_impl", task_board)

    def test_close_task_with_archive_clears_short_term_and_updates_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)
            self.prepare_acceptance_task(repo, runtime_cli)

            closed = self.run_cli(
                runtime_cli,
                "close-task",
                "--task-id",
                "COLLAB-TEST",
                "--acceptance-summary",
                "accepted and archived",
                "--evidence",
                "python3 scripts/check_quality.py --report-json",
                "--archive",
                cwd=repo,
            )
            self.assertEqual(closed.returncode, 0, closed.stderr)
            payload = json.loads(closed.stdout)
            self.assertTrue(payload["archived"])
            self.assertIn("archive_ref", payload)

            archive = (repo / "docs/traceability/task_archive.md").read_text(encoding="utf-8")
            self.assertIn("| COLLAB-TEST |", archive)
            self.assertIn("accepted and archived", archive)

            task_board = (repo / "docs/memory/short_term/task_board.md").read_text(encoding="utf-8")
            self.assertNotIn("| COLLAB-TEST |", task_board)

            current_focus = (repo / "docs/memory/working/current_focus.md").read_text(encoding="utf-8")
            self.assertIn("- none", current_focus)
            self.assertNotIn("COLLAB-TEST", current_focus)

            active_context = (repo / "docs/memory/short_term/active_context.md").read_text(encoding="utf-8")
            self.assertNotIn("COLLAB-TEST", active_context)

            history = json.loads(
                self.run_cli(runtime_cli, "replay", "--task-id", "COLLAB-TEST", cwd=repo).stdout
            )
            self.assertEqual(history[-2]["event"], "close_task")
            self.assertEqual(history[-1]["event"], "archive_task")

            repeated = self.run_cli(
                runtime_cli,
                "close-task",
                "--task-id",
                "COLLAB-TEST",
                "--acceptance-summary",
                "accepted and archived",
                "--evidence",
                "python3 scripts/check_quality.py --report-json",
                "--archive",
                cwd=repo,
            )
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            replay = json.loads(
                self.run_cli(runtime_cli, "replay", "--task-id", "COLLAB-TEST", cwd=repo).stdout
            )
            self.assertEqual(len([event for event in replay if event["event"] == "close_task"]), 1)
            self.assertEqual(len([event for event in replay if event["event"] == "archive_task"]), 1)

    def test_pm_workflow_can_close_and_archive_existing_acceptance_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)
            self.prepare_acceptance_task(repo, runtime_cli)

            workflow = self.run_cli(
                runtime_cli,
                "pm-workflow",
                "--task-id",
                "COLLAB-TEST",
                "--goal",
                "run PM workflow",
                "--agent",
                "pppar_expert_agent",
                "--contract",
                "contracts/ppp_family.contract.md",
                "--close-task",
                "--archive-task",
                "--acceptance-summary",
                "pm workflow archived accepted task",
                "--evidence",
                "python3 scripts/check_quality.py --report-json",
                cwd=repo,
            )
            self.assertEqual(workflow.returncode, 0, workflow.stderr)
            payload = json.loads(workflow.stdout)
            self.assertEqual(payload["steps"][0]["step"], "close-task")
            self.assertEqual(payload["steps"][1]["step"], "archive-task")
            self.assertIn("archive_ref", payload)

            archive = (repo / "docs/traceability/task_archive.md").read_text(encoding="utf-8")
            self.assertIn("pm workflow archived accepted task", archive)

    def test_compact_runtime_moves_artifacts_to_local_spill_and_keeps_tracked_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)
            self.prepare_acceptance_task(repo, runtime_cli)
            closed = self.run_cli(
                runtime_cli,
                "close-task",
                "--task-id",
                "COLLAB-TEST",
                "--acceptance-summary",
                "accepted and archived",
                "--archive",
                cwd=repo,
            )
            self.assertEqual(closed.returncode, 0, closed.stderr)

            compacted = self.run_cli(runtime_cli, "compact-runtime", "--task-id", "COLLAB-TEST", cwd=repo)
            self.assertEqual(compacted.returncode, 0, compacted.stderr)
            payload = json.loads(compacted.stdout)
            self.assertFalse(payload["already_compacted"])
            self.assertTrue((repo / "harness/runtime/tasks/COLLAB-TEST/compact_manifest.json").exists())
            self.assertFalse((repo / "harness/runtime/tasks/COLLAB-TEST/artifacts").exists())
            spill = repo / "harness/runtime/archive/COLLAB-TEST/artifacts"
            self.assertTrue((spill / "task_brief.contract_freeze.json").exists())
            self.assertTrue((spill / "handoff.acceptance.json").exists())
            state = json.loads((repo / "harness/runtime/tasks/COLLAB-TEST/task_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["retention_mode"], "compacted")
            replay = self.run_cli(runtime_cli, "replay", "--task-id", "COLLAB-TEST", cwd=repo)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            history = json.loads(replay.stdout)
            self.assertEqual(history[-1]["event"], "compact_runtime")

            again = self.run_cli(runtime_cli, "compact-runtime", "--task-id", "COLLAB-TEST", cwd=repo)
            self.assertEqual(again.returncode, 0, again.stderr)
            second = json.loads(again.stdout)
            self.assertTrue(second["already_compacted"])

    def test_compact_runtime_rejects_non_archived_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = self.stage_runtime_repo(repo)
            workflow = self.run_cli(
                runtime_cli,
                "pm-workflow",
                "--task-id",
                "COLLAB-TEST",
                "--goal",
                "run PM workflow",
                "--contract",
                "governance/harness_workflow.policy.md",
                "--skip-dispatch",
                cwd=repo,
            )
            self.assertEqual(workflow.returncode, 0, workflow.stderr)
            for phase in ("verification", "traceability", "acceptance"):
                advanced = self.run_cli(
                    runtime_cli,
                    "advance",
                    "--task-id",
                    "COLLAB-TEST",
                    "--phase",
                    phase,
                    "--owner",
                    "project-manager" if phase in {"traceability", "acceptance"} else "testing_agent",
                    cwd=repo,
                )
                self.assertEqual(advanced.returncode, 0, advanced.stderr)
            compacted = self.run_cli(runtime_cli, "compact-runtime", "--task-id", "COLLAB-TEST", cwd=repo)
            self.assertNotEqual(compacted.returncode, 0)
            self.assertIn("requires archived=true state", compacted.stderr + compacted.stdout)


if __name__ == "__main__":
    unittest.main()
