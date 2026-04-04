from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLCHAIN = REPO_ROOT / "tools" / "nav-toolchain-cli" / "toolchain_cli.py"
TRACEABILITY = REPO_ROOT / "tools" / "traceability-cli" / "traceability_cli.py"


class CliToolsTest(unittest.TestCase):
    def run_cli(self, cli_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(cli_path), *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    def test_toolchain_help_includes_examples(self) -> None:
        completed = self.run_cli(TOOLCHAIN, "build", "--help")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Examples:", completed.stdout)
        self.assertIn("toolchain_cli.py build --reconfigure", completed.stdout)

    def test_toolchain_build_dry_run_is_machine_readable(self) -> None:
        completed = self.run_cli(TOOLCHAIN, "build", "--dry-run")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["command"], "build")
        self.assertTrue(any("meson compile" in command for command in payload["commands"]))

    def test_traceability_help_includes_examples(self) -> None:
        completed = self.run_cli(TRACEABILITY, "query-clause", "--help")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Examples:", completed.stdout)
        self.assertIn("query-clause TimeSys_4_4_4", completed.stdout)

    def test_traceability_generate_dry_run_is_machine_readable(self) -> None:
        completed = self.run_cli(TRACEABILITY, "generate", "--dry-run")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["command"], "generate")
        self.assertTrue(any("gen_trace.py" in command for command in payload["commands"]))

    def test_query_clause_unknown_id_returns_actionable_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "trace.json").write_text(
                json.dumps(
                    {
                        "contracts": {"Known_1": {"code_refs": [], "test_refs": []}},
                        "verifies": {},
                    }
                ),
                encoding="utf-8",
            )
            completed = self.run_cli(
                TRACEABILITY,
                "query-clause",
                "Missing_Clause",
                "--output-dir",
                str(output_dir),
            )
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertIn("unknown clause id", payload["error"])
        self.assertTrue(payload["examples"])
        self.assertIn("Known_1", payload["known_clause_examples"])


if __name__ == "__main__":
    unittest.main()
