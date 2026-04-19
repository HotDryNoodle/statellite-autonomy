from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_CLI_PKG = REPO_ROOT / "tools" / "site-cli"
PLANTUML_PKG = REPO_ROOT / "tools" / "plantuml-cli"
for path in (str(SITE_CLI_PKG), str(PLANTUML_PKG)):
    if path not in sys.path:
        sys.path.insert(0, path)
PYTHONPATH = f"{SITE_CLI_PKG}{os.pathsep}{PLANTUML_PKG}"
SITE_RUNTIME = REPO_ROOT / "site" / "_runtime" / "preview_server.json"


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = PYTHONPATH
    if extra:
        env.update(extra)
    return env


class SiteToolingTest(unittest.TestCase):
    def tearDown(self) -> None:
        if SITE_RUNTIME.exists():
            subprocess.run(
                [sys.executable, "-m", "site_cli.cli", "stop"],
                cwd=REPO_ROOT,
                env=_env(),
                capture_output=True,
                text=True,
                check=False,
            )

    def test_site_cli_start_and_stop(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "site_cli.cli", "start", "--port", "8876", "--no-browser"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=_env(),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(SITE_RUNTIME.exists())
        state = json.loads(SITE_RUNTIME.read_text(encoding="utf-8"))
        self.assertEqual(state["port"], 8876)

        stop = subprocess.run(
            [sys.executable, "-m", "site_cli.cli", "stop"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=_env(),
        )
        self.assertEqual(stop.returncode, 0, stop.stderr)
        self.assertFalse(SITE_RUNTIME.exists())

    def test_site_cli_open_help(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "site_cli.cli", "open", "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=_env(),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--port", completed.stdout)
        self.assertIn("--no-browser", completed.stdout)

    def test_plantuml_cli_uses_explicit_server_url_without_container(self) -> None:
        import plantuml_cli.cli as plantuml_cli

        src = REPO_ROOT / "architecture" / "blueprints" / "system" / "harness-product-boundary.puml"
        dst = Path(tempfile.gettempdir()) / "plantuml-explicit.svg"
        if dst.exists():
            dst.unlink()
        with mock.patch.object(plantuml_cli, "_discover_server_url", return_value=None), \
             mock.patch.object(plantuml_cli, "_choose_container_engine", side_effect=AssertionError("should not start container")), \
             mock.patch.object(plantuml_cli, "_probe_svg", return_value=b"<svg></svg>"):
            with plantuml_cli.managed_server("http://127.0.0.1:18080") as server_url:
                plantuml_cli.render_plantuml(src, dst, server_url)
        self.assertTrue(dst.exists())
        dst.unlink()

    def test_plantuml_discovery_prefers_running_container(self) -> None:
        import plantuml_cli.cli as plantuml_cli

        with mock.patch("shutil.which", side_effect=lambda name: f"/usr/bin/{name}"), \
             mock.patch("subprocess.run") as run_mock:
            run_mock.return_value = mock.Mock(returncode=0, stdout="docker.io/plantuml/plantuml-server:jetty|127.0.0.1:19090->8080/tcp\n", stderr="")
            discovered = plantuml_cli._discover_server_url()
        self.assertEqual(discovered, "http://127.0.0.1:19090")

    def test_plantuml_managed_server_starts_temporary_container_when_needed(self) -> None:
        import plantuml_cli.cli as plantuml_cli

        calls: list[list[str]] = []

        def fake_run(cmd: list[str], **_: object) -> mock.Mock:
            calls.append(cmd)
            if cmd[1] == "run":
                return mock.Mock(returncode=0, stdout="container-id\n", stderr="")
            if cmd[1] == "rm":
                return mock.Mock(returncode=0, stdout="", stderr="")
            raise AssertionError(cmd)

        with mock.patch.object(plantuml_cli, "_discover_server_url", return_value=None), \
             mock.patch.object(plantuml_cli, "_choose_container_engine", return_value="podman"), \
             mock.patch.object(plantuml_cli, "_pick_free_port", return_value=19191), \
             mock.patch.object(plantuml_cli, "_wait_for_server", return_value=None), \
             mock.patch("subprocess.run", side_effect=fake_run):
            with plantuml_cli.managed_server(None) as url:
                self.assertEqual(url, "http://127.0.0.1:19191")

        self.assertEqual(calls[0][:2], ["podman", "run"])
        self.assertEqual(calls[-1][:3], ["podman", "rm", "-f"])


if __name__ == "__main__":
    unittest.main()
