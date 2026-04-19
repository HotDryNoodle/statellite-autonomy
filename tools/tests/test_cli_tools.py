from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLCHAIN = REPO_ROOT / "tools" / "meson-cli" / "meson_cli.py"
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

    def write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def stage_fake_pride_runtime(self, root: Path, *, failing: bool = False) -> None:
        env_file = root / "toolchain" / "env.sh"
        driver = root / "toolchain" / "bin" / "pdp3"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        driver.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text(
            "\n".join(
                [
                    f'export PPP_FLOAT_PRIDE_EXECUTABLE="{driver}"',
                    f'export PPP_FLOAT_PRIDE_BIN_DIR="{driver.parent}"',
                    'export PATH="$PPP_FLOAT_PRIDE_BIN_DIR:$PATH"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        if failing:
            content = "#!/bin/sh\necho 'runtime failed' >&2\nexit 1\n"
        else:
            content = "#!/bin/sh\nsleep 0.01\nexit 0\n"
        self.write_executable(driver, content)
        for scenario_name, obs_name in (
            ("scenario_leo_gracefo_ppp_ar_grac", "grac0010.25o"),
            ("scenario_leo_gracefo_ppp_float_grad", "grad0010.25o"),
        ):
            scenario_root = root / "data" / scenario_name / "inputs"
            scenario_root.mkdir(parents=True, exist_ok=True)
            (scenario_root / "config.cfg").write_text("# fake config\n", encoding="utf-8")
            (scenario_root / obs_name).write_text("fake obs\n", encoding="utf-8")

    def stage_pppar_manifest_and_baseline(
        self,
        root: Path,
        *,
        runtime_s_max: float,
        orbit_scale: float = 1.0,
        tolerance_ratio: float | None = None,
    ) -> tuple[Path, Path]:
        manifest = json.loads((REPO_ROOT / "eval" / "domains" / "pppar" / "manifest.json").read_text(encoding="utf-8"))
        baseline = json.loads(
            (REPO_ROOT / "eval" / "domains" / "pppar" / "baselines" / "pppfamily_pride_baseline.json").read_text(
                encoding="utf-8"
            )
        )
        manifest_path = root / "pppar_manifest.json"
        baseline_path = root / "pppar_baseline.json"
        manifest["default_baseline"] = str(baseline_path)
        if tolerance_ratio is not None:
            baseline["statistics_policy"]["degradation_tolerance_ratio"] = tolerance_ratio
        baseline["thresholds"]["leo_gracefo_ppp_ar_grac"]["performance"]["runtime_s"] = runtime_s_max
        baseline["thresholds"]["leo_gracefo_ppp_float_grad"]["performance"]["runtime_s"] = runtime_s_max
        if orbit_scale != 1.0:
            baseline["thresholds"]["leo_gracefo_ppp_ar_grac"]["accuracy"]["orbit_3d_rms_m"] *= orbit_scale
        self.write_json(manifest_path, manifest)
        self.write_json(baseline_path, baseline)
        return manifest_path, baseline_path

    def test_toolchain_help_includes_examples(self) -> None:
        completed = self.run_cli(TOOLCHAIN, "build", "--help")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Examples:", completed.stdout)
        self.assertIn("meson_cli.py build --reconfigure", completed.stdout)

    def test_toolchain_build_dry_run_is_machine_readable(self) -> None:
        completed = self.run_cli(TOOLCHAIN, "build", "--dry-run")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["command"], "build")
        self.assertTrue(any("meson compile" in command for command in payload["commands"]))

    def test_toolchain_eval_help_includes_examples(self) -> None:
        completed = self.run_cli(TOOLCHAIN, "eval", "--help")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Examples:", completed.stdout)
        self.assertIn("eval --domain time", completed.stdout)

    def test_toolchain_eval_dry_run_is_machine_readable(self) -> None:
        completed = self.run_cli(TOOLCHAIN, "eval", "--domain", "time", "--dry-run")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["command"], "eval")
        self.assertTrue(any("time_benchmark" in command for command in payload["commands"]))

    def test_toolchain_eval_pppar_dry_run_mentions_external_runtime(self) -> None:
        completed = self.run_cli(TOOLCHAIN, "eval", "--domain", "pppar", "--dry-run")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["command"], "eval")
        self.assertTrue(any("toolchain/bin/pdp3" in command for command in payload["commands"]))
        self.assertTrue(any("eval_results.json" in note for note in payload["notes"]))

    def test_toolchain_eval_pppar_passes_with_fake_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.stage_fake_pride_runtime(root)
            manifest_path, _ = self.stage_pppar_manifest_and_baseline(root, runtime_s_max=5.0)
            report_path = root / "pppar_eval_report.json"
            completed = self.run_cli(
                TOOLCHAIN,
                "eval",
                "--domain",
                "pppar",
                "--manifest",
                str(manifest_path),
                "--report-path",
                str(report_path),
                "--yes",
                env={"PRIDE_PPPAR_RUNTIME_ROOT": str(root)},
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["verdict"], "pass")
        self.assertEqual(payload["domain"], "pppar")
        self.assertEqual(payload["execution_mode"], "pppar_eval_results")
        self.assertEqual(payload["scenario_count"], 2)
        self.assertTrue(all(result["result_status"] == "pass" for result in payload["results"]))

    def test_toolchain_eval_pppar_fails_on_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.stage_fake_pride_runtime(root)
            manifest_path, _ = self.stage_pppar_manifest_and_baseline(root, runtime_s_max=5.0, orbit_scale=0.5)
            report_path = root / "pppar_eval_report.json"
            completed = self.run_cli(
                TOOLCHAIN,
                "eval",
                "--domain",
                "pppar",
                "--manifest",
                str(manifest_path),
                "--report-path",
                str(report_path),
                "--yes",
                env={"PRIDE_PPPAR_RUNTIME_ROOT": str(root)},
            )
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["verdict"], "fail")
        self.assertEqual(payload["attribution"], "algorithm_regression")
        self.assertTrue(payload["regressions"])

    def test_toolchain_eval_pppar_allows_regression_within_tolerance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.stage_fake_pride_runtime(root)
            manifest_path, _ = self.stage_pppar_manifest_and_baseline(
                root,
                runtime_s_max=5.0,
                orbit_scale=0.9,
                tolerance_ratio=0.2,
            )
            report_path = root / "pppar_eval_report.json"
            completed = self.run_cli(
                TOOLCHAIN,
                "eval",
                "--domain",
                "pppar",
                "--manifest",
                str(manifest_path),
                "--report-path",
                str(report_path),
                "--yes",
                env={"PRIDE_PPPAR_RUNTIME_ROOT": str(root)},
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["verdict"], "pass")
        first_check = payload["results"][0]["checks"][0]
        self.assertGreater(first_check["actual"], first_check["expected"])
        self.assertTrue(first_check["ok"])

    def test_toolchain_eval_pppar_returns_blocked_when_runtime_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path, _ = self.stage_pppar_manifest_and_baseline(root, runtime_s_max=5.0)
            report_path = root / "pppar_eval_report.json"
            completed = self.run_cli(
                TOOLCHAIN,
                "eval",
                "--domain",
                "pppar",
                "--manifest",
                str(manifest_path),
                "--report-path",
                str(report_path),
                "--yes",
                env={"PRIDE_PPPAR_RUNTIME_ROOT": str(root / "missing-runtime")},
            )
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["verdict"], "blocked")
        self.assertEqual(payload["attribution"], "toolchain_failure")
        self.assertTrue(payload["blocked_reasons"])

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
