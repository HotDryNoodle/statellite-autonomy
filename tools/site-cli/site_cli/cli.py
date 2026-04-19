"""Console entrypoint for site build orchestration."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import signal
import socketserver
import subprocess
import sys
import textwrap
import time
import webbrowser
from pathlib import Path

from . import build_site


class _DefaultsWithRawEpilogFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    """Show per-argument defaults; keep description/epilog as authored (multiline Examples)."""


class _ReuseAddrTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


PREVIEW_RUNTIME_DIR = build_site.SITE_DIR / "_runtime"
PREVIEW_STATE_PATH = PREVIEW_RUNTIME_DIR / "preview_server.json"
_PREVIEW_STATE_REL = PREVIEW_STATE_PATH.relative_to(build_site.REPO_ROOT)

_ROOT_DESCRIPTION = (
    "Stage documentation into site/_staging, optionally render PlantUML to SVG, "
    "and run MkDocs (build or serve). Preview commands serve site/_generated over HTTP."
)

_ROOT_EPILOG = textwrap.dedent(
    f"""\
    Environment:
      PLANTUML_SERVER_URL   Passed through to staging when PlantUML rendering runs.

    Preview state (after `site-cli start`):
      {_PREVIEW_STATE_REL}

    Examples:
      site-cli build
      site-cli build --skip-puml
      site-cli serve
      PLANTUML_SERVER_URL=http://127.0.0.1:8080 site-cli build
      site-cli start --port 8765 --no-browser
      site-cli stop
    """
)

_BUILD_EPILOG = textwrap.dedent(
    """\
    Runs staging, optional PlantUML render, then `mkdocs build --strict` into site/_generated.

    Examples:
      site-cli build
      site-cli build --skip-puml
      PLANTUML_SERVER_URL=http://127.0.0.1:8080 site-cli build
    """
)

_SERVE_EPILOG = textwrap.dedent(
    """\
    Runs staging, optional PlantUML render, then `mkdocs serve` (long-running; Ctrl+C to stop).

    Examples:
      site-cli serve
      site-cli serve --skip-puml
    """
)

_OPEN_EPILOG = textwrap.dedent(
    f"""\
    Foreground HTTP server for site/_generated; blocks until Ctrl+C. Opens a browser unless
    --no-browser is set. For automation, prefer `site-cli start` (background) and read
    {_PREVIEW_STATE_REL} or use `site-cli start --json`.

    Examples:
      site-cli open
      site-cli open --port 9000 --no-browser
    """
)

_START_EPILOG = textwrap.dedent(
    f"""\
    Background `http.server` for site/_generated. Writes state to {_PREVIEW_STATE_REL}.

    Examples:
      site-cli start --port 8765 --no-browser
      site-cli start --json --no-browser
    """
)


def _formatter() -> type[argparse.HelpFormatter]:
    return _DefaultsWithRawEpilogFormatter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=_ROOT_DESCRIPTION,
        epilog=_ROOT_EPILOG,
        formatter_class=_formatter(),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser(
        "build",
        description="Stage docs and run `mkdocs build --strict`.",
        epilog=_BUILD_EPILOG,
        formatter_class=_formatter(),
    )
    build.add_argument(
        "--server-url",
        default=None,
        metavar="URL",
        help="Reuse an existing PlantUML server instead of container discovery/temporary startup.",
    )
    build.add_argument(
        "--skip-puml",
        action="store_true",
        help="Skip PlantUML rendering (blueprint pages will link to raw .puml only).",
    )

    serve = subparsers.add_parser(
        "serve",
        description="Stage docs and run `mkdocs serve` for live preview.",
        epilog=_SERVE_EPILOG,
        formatter_class=_formatter(),
    )
    serve.add_argument(
        "--server-url",
        default=None,
        metavar="URL",
        help="Reuse an existing PlantUML server instead of container discovery/temporary startup.",
    )
    serve.add_argument(
        "--skip-puml",
        action="store_true",
        help="Skip PlantUML rendering (blueprint pages will link to raw .puml only).",
    )

    open_p = subparsers.add_parser(
        "open",
        help="Serve the latest built static site (site/_generated) and open it in a browser.",
        description="Foreground HTTP server for the last `site-cli build` output.",
        epilog=_OPEN_EPILOG,
        formatter_class=_formatter(),
    )
    open_p.add_argument("--port", type=int, default=8765)
    open_p.add_argument("--no-browser", action="store_true")

    start = subparsers.add_parser(
        "start",
        help="Start a background HTTP preview server for site/_generated.",
        description="Background preview of site/_generated.",
        epilog=_START_EPILOG,
        formatter_class=_formatter(),
    )
    start.add_argument("--port", type=int, default=8765)
    start.add_argument("--no-browser", action="store_true")
    start.add_argument(
        "--json",
        action="store_true",
        help="Print one JSON object on stdout (pid, port, url, root, state_path); for automation.",
    )

    subparsers.add_parser(
        "stop",
        help="Stop the background HTTP preview server started by `site-cli start`.",
    )
    return parser


def _generated_root() -> Path:
    root = build_site.GENERATED_SITE_DIR.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError(f"no built site at {index}. Run `site-cli build` first.")
    return root


def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _load_preview_state() -> dict[str, object] | None:
    if not PREVIEW_STATE_PATH.exists():
        return None
    try:
        return json.loads(PREVIEW_STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _clear_preview_state() -> None:
    if PREVIEW_STATE_PATH.exists():
        PREVIEW_STATE_PATH.unlink()


def _open_generated_site(port: int, open_browser: bool) -> int:
    root = _generated_root()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    try:
        httpd = _ReuseAddrTCPServer(("127.0.0.1", port), handler)
    except OSError as exc:
        print(f"error: could not bind 127.0.0.1:{port}: {exc}", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{port}/"
    print(f"Serving {root} at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    finally:
        httpd.server_close()


def _start_preview_server(port: int, open_browser: bool, json_output: bool) -> int:
    root = _generated_root()
    state = _load_preview_state()
    if state and isinstance(state.get("pid"), int) and _is_process_alive(int(state["pid"])):
        msg = f"error: preview server already running at {state.get('url', 'unknown url')}"
        if json_output:
            print(json.dumps({"error": "already_running", "url": state.get("url")}), file=sys.stdout)
        else:
            print(msg, file=sys.stderr)
        return 1
    if state:
        _clear_preview_state()

    PREVIEW_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "http.server",
        str(port),
        "--bind",
        "127.0.0.1",
        "--directory",
        str(root),
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=build_site.REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    url = f"http://127.0.0.1:{port}/"
    started_at = int(time.time())
    state_path_str = str(PREVIEW_STATE_PATH.resolve())
    payload = {
        "pid": proc.pid,
        "port": port,
        "url": url,
        "root": str(root),
        "started_at": started_at,
        "state_path": state_path_str,
    }
    PREVIEW_STATE_PATH.write_text(
        json.dumps(
            {
                "pid": proc.pid,
                "port": port,
                "url": url,
                "root": str(root),
                "started_at": started_at,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if open_browser:
        webbrowser.open(url)
    if json_output:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"Started preview server at {url}")
    return 0


def _stop_preview_server() -> int:
    state = _load_preview_state()
    if not state or not isinstance(state.get("pid"), int):
        _clear_preview_state()
        print("Preview server already stopped.")
        return 0

    pid = int(state["pid"])
    if not _is_process_alive(pid):
        _clear_preview_state()
        print("Preview server already stopped.")
        return 0

    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if not _is_process_alive(pid):
            _clear_preview_state()
            print("Stopped preview server.")
            return 0
        time.sleep(0.1)
    os.kill(pid, signal.SIGKILL)
    _clear_preview_state()
    print("Stopped preview server.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "open":
        return _open_generated_site(args.port, open_browser=not args.no_browser)
    if args.command == "start":
        return _start_preview_server(
            args.port,
            open_browser=not args.no_browser,
            json_output=args.json,
        )
    if args.command == "stop":
        return _stop_preview_server()

    forwarded: list[str] = []
    if args.server_url:
        forwarded.extend(["--server-url", args.server_url])
    if args.skip_puml:
        forwarded.append("--skip-puml")
    if args.command == "build":
        forwarded.append("--build")
    elif args.command == "serve":
        forwarded.append("--serve")
    return build_site.main(forwarded)


__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
