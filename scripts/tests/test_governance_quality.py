from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_quality  # noqa: E402


class GovernanceQualityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.originals = {
            "REPO_ROOT": check_quality.REPO_ROOT,
            "WORKING_PATH": check_quality.WORKING_PATH,
            "TASK_BOARD_PATH": check_quality.TASK_BOARD_PATH,
            "ACTIVE_CONTEXT_PATH": check_quality.ACTIVE_CONTEXT_PATH,
            "TASK_ARCHIVE_PATH": check_quality.TASK_ARCHIVE_PATH,
            "PROJECT_STATUS_PATH": check_quality.PROJECT_STATUS_PATH,
        }

    def tearDown(self) -> None:
        for name, value in self.originals.items():
            setattr(check_quality, name, value)

    def patch_repo(self, repo: Path) -> None:
        check_quality.REPO_ROOT = repo
        check_quality.WORKING_PATH = repo / "docs" / "memory" / "working" / "current_focus.md"
        check_quality.TASK_BOARD_PATH = repo / "docs" / "memory" / "short_term" / "task_board.md"
        check_quality.ACTIVE_CONTEXT_PATH = repo / "docs" / "memory" / "short_term" / "active_context.md"
        check_quality.TASK_ARCHIVE_PATH = repo / "docs" / "traceability" / "task_archive.md"
        check_quality.PROJECT_STATUS_PATH = repo / "docs" / "_generated" / "project_status.json"

    def write_common_files(self, repo: Path) -> None:
        for relative in (
            "docs/memory/working",
            "docs/memory/short_term",
            "docs/traceability",
            "docs/_generated",
            "harness/config",
            "harness/runtime/tasks",
        ):
            (repo / relative).mkdir(parents=True, exist_ok=True)
        (repo / "harness" / "config" / "governance_policy.json").write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "runtime_required_from_task_id": "COLLAB-013",
                    "legacy_task_ids": [],
                    "runtime_retention": {
                        "mode": "tracked_compact_proof",
                        "eligible_phase": "acceptance",
                        "require_archived": True,
                        "tracked_proof_files": ["task_state.json", "events.jsonl", "compact_manifest.json"],
                        "drop_tracked_artifacts": True,
                        "local_spill_dir": "harness/runtime/archive",
                        "local_spill_tracked": False,
                    },
                }
            ),
            encoding="utf-8",
        )
        (repo / "docs" / "memory" / "working" / "current_focus.md").write_text(
            "# Current Focus\n\n"
            "## Current Phase\n- `acceptance`\n\n"
            "## In Progress\n- none\n\n"
            "## Current Blockers\n- none\n\n"
            "## Active Contracts\n- none\n\n"
            "## Next Acceptance Target\n- none\n\n"
            "## Next Agent\n- none\n",
            encoding="utf-8",
        )
        (repo / "docs" / "memory" / "short_term" / "task_board.md").write_text(
            "# Task Board\n\n"
            "| task_id | title | owner_agent | affected_contracts | status | acceptance | blockers |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
        (repo / "docs" / "memory" / "short_term" / "active_context.md").write_text(
            "# Active Context\n\n"
            "## Current Scope\n- none\n\n"
            "## Active Policy Skills\n- none\n\n"
            "## Acceptance Gates\n- none\n\n"
            "## Handoff Expectations\n- none\n",
            encoding="utf-8",
        )
        (repo / "docs" / "traceability" / "task_archive.md").write_text(
            "# Task Archive\n\n"
            "Record tasks after they are marked `done`, logged in `agent_activity_log.md`, and no longer needed in short-term memory.\n\n\n"
            "| task_id | title | owner_agent | affected_contracts | status | acceptance | evidence |\n"
            "| ---------- | ---------- | ---------- | ---------- | ---------- | ---------- | ---------- |\n",
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
            "affected_contracts": ["contracts/harness_workflow.contract.md"],
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
            (repo / "docs" / "memory" / "short_term" / "task_board.md").write_text(
                "# Task Board\n\n"
                "| task_id | title | owner_agent | affected_contracts | status | acceptance | blockers |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| COLLAB-013 | hard cutover | coding_agent | contracts/harness_workflow.contract.md | ready_for_impl | none | none |\n",
                encoding="utf-8",
            )

            result = check_quality.check_runtime_task_board_consistency()
            self.assertFalse(result.ok)
            self.assertIn("COLLAB-013 missing", result.details)

    def test_runtime_current_focus_consistency_detects_phase_and_owner_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_common_files(repo)
            self.patch_repo(repo)
            self.write_runtime_task(repo, "COLLAB-013", phase="implementation", owner="coding_agent")
            (repo / "docs" / "memory" / "working" / "current_focus.md").write_text(
                "# Current Focus\n\n"
                "## Current Phase\n- `verification`\n\n"
                "## In Progress\n- `COLLAB-013`: governance drift\n\n"
                "## Current Blockers\n- none\n\n"
                "## Active Contracts\n- `contracts/harness_workflow.contract.md`\n\n"
                "## Next Acceptance Target\n- `COLLAB-013`: governance drift\n\n"
                "## Next Agent\n- `testing_agent`\n",
                encoding="utf-8",
            )

            result = check_quality.check_runtime_current_focus_consistency()
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
                event_names=["init_task", "close_task"],
            )
            (repo / "docs" / "traceability" / "task_archive.md").write_text(
                "# Task Archive\n\n"
                "Record tasks after they are marked `done`, logged in `agent_activity_log.md`, and no longer needed in short-term memory.\n\n\n"
                "| task_id | title | owner_agent | affected_contracts | status | acceptance | evidence |\n"
                "| ---------- | ---------- | ---------- | ---------- | ---------- | ---------- | ---------- |\n"
                "| COLLAB-013 | hard cutover | project-manager | `contracts/harness_workflow.contract.md` | done | archived | `python3 scripts/check_quality.py --report-json` |\n",
                encoding="utf-8",
            )

            result = check_quality.check_runtime_archive_consistency()
            self.assertFalse(result.ok)
            self.assertIn("missing archive_task event", result.details)

    def test_runtime_archive_consistency_skips_legacy_tasks_before_cutover(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.write_common_files(repo)
            self.patch_repo(repo)
            (repo / "docs" / "traceability" / "task_archive.md").write_text(
                "# Task Archive\n\n"
                "Record tasks after they are marked `done`, logged in `agent_activity_log.md`, and no longer needed in short-term memory.\n\n\n"
                "| task_id | title | owner_agent | affected_contracts | status | acceptance | evidence |\n"
                "| ---------- | ---------- | ---------- | ---------- | ---------- | ---------- | ---------- |\n"
                "| COLLAB-012 | legacy task | project-manager | `contracts/harness_workflow.contract.md` | done | archived | `python3 scripts/check_quality.py --report-json` |\n",
                encoding="utf-8",
            )

            result = check_quality.check_runtime_archive_consistency()
            self.assertTrue(result.ok, result.details)

    def test_runtime_archive_consistency_accepts_compacted_archived_task(self) -> None:
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
                event_names=["init_task", "close_task", "archive_task", "compact_runtime"],
                retention_mode="compacted",
            )
            task_root = repo / "harness" / "runtime" / "tasks" / "COLLAB-013"
            (task_root / "compact_manifest.json").write_text(
                json.dumps({"task_id": "COLLAB-013", "compacted_at": "2026-04-07T00:00:00+00:00"}) + "\n",
                encoding="utf-8",
            )
            (repo / "docs" / "traceability" / "task_archive.md").write_text(
                "# Task Archive\n\n"
                "Record tasks after they are marked `done`, logged in `agent_activity_log.md`, and no longer needed in short-term memory.\n\n\n"
                "| task_id | title | owner_agent | affected_contracts | status | acceptance | evidence |\n"
                "| ---------- | ---------- | ---------- | ---------- | ---------- | ---------- | ---------- |\n"
                "| COLLAB-013 | hard cutover | project-manager | `contracts/harness_workflow.contract.md` | done | compacted | `python3 scripts/check_quality.py --report-json` |\n",
                encoding="utf-8",
            )
            result = check_quality.check_runtime_archive_consistency()
            self.assertTrue(result.ok, result.details)

    def test_runtime_archive_consistency_rejects_missing_compact_manifest(self) -> None:
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
                event_names=["init_task", "close_task", "archive_task", "compact_runtime"],
                retention_mode="compacted",
            )
            (repo / "docs" / "traceability" / "task_archive.md").write_text(
                "# Task Archive\n\n"
                "Record tasks after they are marked `done`, logged in `agent_activity_log.md`, and no longer needed in short-term memory.\n\n\n"
                "| task_id | title | owner_agent | affected_contracts | status | acceptance | evidence |\n"
                "| ---------- | ---------- | ---------- | ---------- | ---------- | ---------- | ---------- |\n"
                "| COLLAB-013 | hard cutover | project-manager | `contracts/harness_workflow.contract.md` | done | compacted | `python3 scripts/check_quality.py --report-json` |\n",
                encoding="utf-8",
            )
            result = check_quality.check_runtime_archive_consistency()
            self.assertFalse(result.ok)
            self.assertIn("compact_manifest.json", result.details)

    def test_runtime_archive_consistency_rejects_tracked_artifacts_after_compaction(self) -> None:
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
                event_names=["init_task", "close_task", "archive_task", "compact_runtime"],
                retention_mode="compacted",
            )
            task_root = repo / "harness" / "runtime" / "tasks" / "COLLAB-013"
            (task_root / "compact_manifest.json").write_text(
                json.dumps({"task_id": "COLLAB-013", "compacted_at": "2026-04-07T00:00:00+00:00"}) + "\n",
                encoding="utf-8",
            )
            (task_root / "artifacts").mkdir()
            (task_root / "artifacts" / "handoff.acceptance.json").write_text("{}", encoding="utf-8")
            (repo / "docs" / "traceability" / "task_archive.md").write_text(
                "# Task Archive\n\n"
                "Record tasks after they are marked `done`, logged in `agent_activity_log.md`, and no longer needed in short-term memory.\n\n\n"
                "| task_id | title | owner_agent | affected_contracts | status | acceptance | evidence |\n"
                "| ---------- | ---------- | ---------- | ---------- | ---------- | ---------- | ---------- |\n"
                "| COLLAB-013 | hard cutover | project-manager | `contracts/harness_workflow.contract.md` | done | compacted | `python3 scripts/check_quality.py --report-json` |\n",
                encoding="utf-8",
            )
            result = check_quality.check_runtime_archive_consistency()
            self.assertFalse(result.ok)
            self.assertIn("still retains tracked raw artifacts", result.details)


if __name__ == "__main__":
    unittest.main()
