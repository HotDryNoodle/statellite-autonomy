from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "harness" / "orchestrator" / "harness_cli.py"


class HarnessCliTest(unittest.TestCase):
    def run_cli(self, cli_path: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(cli_path), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
        )

    def test_init_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "harness" / "orchestrator").mkdir(parents=True)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = repo / "harness" / "orchestrator" / "harness_cli.py"
            runtime_cli.write_text(CLI.read_text(encoding="utf-8"), encoding="utf-8")

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
            (repo / "harness" / "orchestrator").mkdir(parents=True)
            (repo / "harness" / "runtime").mkdir(parents=True)
            runtime_cli = repo / "harness" / "orchestrator" / "harness_cli.py"
            runtime_cli.write_text(CLI.read_text(encoding="utf-8"), encoding="utf-8")

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


if __name__ == "__main__":
    unittest.main()
