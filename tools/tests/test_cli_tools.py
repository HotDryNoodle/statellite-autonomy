from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLCHAIN = REPO_ROOT / "tools" / "nav-toolchain-cli" / "toolchain_cli.py"
TRACEABILITY = REPO_ROOT / "tools" / "traceability-cli" / "traceability_cli.py"


class CliToolsTest(unittest.TestCase):
    def run_cli(
        self,
        cli_path: Path,
        *args: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command_env = os.environ.copy()
        if env:
            command_env.update(env)
        return subprocess.run(
            ["python3", str(cli_path), *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=command_env,
        )

    def write_executable(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

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

    def test_toolchain_knowledge_help_includes_examples(self) -> None:
        completed = self.run_cli(TOOLCHAIN, "knowledge", "search", "--help")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Examples:", completed.stdout)
        self.assertIn("knowledge search --agent pppar_expert_agent --query ambiguity", completed.stdout)

    def test_toolchain_knowledge_search_filters_allowed_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            obsidian_bin = root / "fake-obsidian"
            self.write_executable(
                obsidian_bin,
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
    echo '["pppar/pride-pppar-filtering.md", "other/out-of-scope.md"]'
    exit 0
    ;;
  read)
    echo "# PPPAR"
    exit 0
    ;;
  *)
    echo "unsupported command: $cmd" >&2
    exit 1
    ;;
esac
""",
            )
            env = {
                "OBSIDIAN_CLI_BIN": str(obsidian_bin),
            }
            completed = self.run_cli(
                TOOLCHAIN,
                "knowledge",
                "search",
                "--agent",
                "pppar_expert_agent",
                "--query",
                "ambiguity",
                env=env,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["matches"], ["pppar/pride-pppar-filtering.md"])
        self.assertEqual(payload["match_count"], 1)

    def test_toolchain_knowledge_search_reports_bridge_hint_when_app_is_unreachable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            obsidian_bin = root / "fake-obsidian"
            self.write_executable(
                obsidian_bin,
                """#!/bin/sh
echo "The CLI is unable to find Obsidian. Please make sure Obsidian is running and try again." >&2
exit 1
""",
            )
            env = {
                "OBSIDIAN_CLI_BIN": str(obsidian_bin),
            }
            completed = self.run_cli(
                TOOLCHAIN,
                "knowledge",
                "search",
                "--agent",
                "pppar_expert_agent",
                "--query",
                "ambiguity",
                env=env,
            )
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertIn("host bridge command", payload["error"])

    def test_toolchain_knowledge_read_rejects_note_outside_allowed_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            obsidian_bin = root / "fake-obsidian"
            self.write_executable(
                obsidian_bin,
                """#!/bin/sh
echo "# PPPAR"
exit 0
""",
            )
            env = {
                "OBSIDIAN_CLI_BIN": str(obsidian_bin),
            }
            completed = self.run_cli(
                TOOLCHAIN,
                "knowledge",
                "read",
                "--agent",
                "pppar_expert_agent",
                "--note",
                "other/out-of-scope.md",
                env=env,
            )
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertIn("outside allowed roots", payload["error"])


if __name__ == "__main__":
    unittest.main()
