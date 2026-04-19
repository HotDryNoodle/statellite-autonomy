#!/usr/bin/env python3
"""PlantUML rendering via HTTP server, with optional managed local containers."""

from __future__ import annotations

import argparse
import http.client
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
import uuid
import zlib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_IMAGE = "docker.io/plantuml/plantuml-server:jetty"
DEFAULT_TIMEOUT_S = 30.0
PLANTUML_B64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
_READINESS_SOURCE = "@startuml\nAlice -> Bob\n@enduml\n"


class _DefaultsWithRawEpilogFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    """Show per-argument defaults; keep description/epilog as authored (multiline Examples)."""


_ROOT_DESCRIPTION = (
    "Render or lint PlantUML via a PlantUML server over HTTP. "
    "If --server-url is omitted, tries a running plantuml-server container, "
    "then starts a temporary podman/docker container."
)

_ROOT_EPILOG = textwrap.dedent(
    """\
    Environment:
      PLANTUML_SERVER_URL   Default base URL when --server-url is omitted.

    Examples:
      plantuml-cli render --input diagram.puml --output diagram.svg --server-url http://127.0.0.1:8080
      PLANTUML_SERVER_URL=http://127.0.0.1:8080 plantuml-cli lint --input diagram.puml
      plantuml-cli render --input diagram.puml --output diagram.svg
    """
)

_RENDER_EPILOG = textwrap.dedent(
    """\
    Examples:
      plantuml-cli render --input arch/system/foo.puml --output arch/system/foo.svg --server-url http://127.0.0.1:8080
      plantuml-cli render --input diagram.puml --output out.svg --timeout 60
    """
)

_LINT_EPILOG = textwrap.dedent(
    """\
    Examples:
      plantuml-cli lint --input diagram.puml --server-url http://127.0.0.1:8080
      PLANTUML_SERVER_URL=http://127.0.0.1:8080 plantuml-cli lint --input diagram.puml
    """
)


def _encode_six_bit(b: int) -> str:
    return PLANTUML_B64[b & 0x3F]


def _encode_three_bytes(b1: int, b2: int, b3: int) -> str:
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F
    return _encode_six_bit(c1) + _encode_six_bit(c2) + _encode_six_bit(c3) + _encode_six_bit(c4)


def encode_plantuml(text: str) -> str:
    raw = text.encode("utf-8")
    deflated = zlib.compress(raw, 9)[2:-4]
    buf = []
    i = 0
    while i < len(deflated):
        b1 = deflated[i]
        b2 = deflated[i + 1] if i + 1 < len(deflated) else 0
        b3 = deflated[i + 2] if i + 2 < len(deflated) else 0
        buf.append(_encode_three_bytes(b1, b2, b3))
        i += 3
    return "".join(buf)


def _probe_svg(server_url: str, source: str) -> bytes:
    encoded = encode_plantuml(source)
    url = server_url.rstrip("/") + "/svg/" + encoded
    with urllib.request.urlopen(url, timeout=20) as resp:
        return resp.read()


_RETRIABLE_SERVER_ERRORS = (
    urllib.error.URLError,
    TimeoutError,
    ConnectionResetError,
    http.client.RemoteDisconnected,
    OSError,
)


def _render_via_server(src: Path, dst: Path, server_url: str) -> None:
    payload = _probe_svg(server_url, src.read_text(encoding="utf-8"))
    if not payload.lstrip().startswith(b"<"):
        raise RuntimeError(
            f"PlantUML server returned non-SVG payload for {src} (first bytes: {payload[:40]!r})"
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(payload)


def render_plantuml(src: Path, dst: Path, server_url: str) -> None:
    try:
        _render_via_server(src, dst, server_url)
    except _RETRIABLE_SERVER_ERRORS as exc:
        raise RuntimeError(f"PlantUML server request failed for {src}: {exc}") from exc


def lint_plantuml(src: Path, server_url: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / f"{src.stem}.svg"
        render_plantuml(src, dst, server_url)


def _container_engine_missing_message() -> str:
    return textwrap.dedent(
        """\
        No container engine found (expected `podman` or `docker` on PATH).
        Without a server URL, this tool can start a temporary PlantUML server via a container.

        Fix one of:
          - Install podman or docker, then retry; or
          - Point at an existing PlantUML server (no container needed), e.g.
              PLANTUML_SERVER_URL=http://127.0.0.1:8080 plantuml-cli render --input diagram.puml --output out.svg
              plantuml-cli lint --input diagram.puml --server-url http://127.0.0.1:8080
        """
    ).strip()


def _choose_container_engine() -> str:
    for engine in ("podman", "docker"):
        if shutil.which(engine):
            return engine
    raise RuntimeError(_container_engine_missing_message())


def _available_container_engines() -> list[str]:
    return [engine for engine in ("podman", "docker") if shutil.which(engine)]


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((DEFAULT_SERVER_HOST, 0))
        return int(sock.getsockname()[1])


def _wait_for_server(server_url: str, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    last_error = "server did not become ready"
    while time.monotonic() < deadline:
        try:
            payload = _probe_svg(server_url, _READINESS_SOURCE)
            if payload.lstrip().startswith(b"<"):
                return
            last_error = f"unexpected readiness payload: {payload[:40]!r}"
        except _RETRIABLE_SERVER_ERRORS as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for PlantUML server at {server_url}: {last_error}")


def _parse_published_port(ports_field: str) -> str | None:
    for part in ports_field.split(","):
        token = part.strip()
        if "->8080/tcp" not in token:
            continue
        host_side = token.split("->", 1)[0]
        if ":" not in host_side:
            continue
        port = host_side.rsplit(":", 1)[-1]
        if port.isdigit():
            return f"http://{DEFAULT_SERVER_HOST}:{port}"
    return None


def _discover_server_url() -> str | None:
    for engine in _available_container_engines():
        completed = subprocess.run(
            [engine, "ps", "--format", "{{.Image}}|{{.Ports}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            continue
        for line in completed.stdout.splitlines():
            if "|" not in line:
                continue
            image, ports = line.split("|", 1)
            if "plantuml-server" not in image:
                continue
            server_url = _parse_published_port(ports)
            if server_url:
                return server_url
    return None


@contextmanager
def managed_server(
    server_url: str | None = None,
    *,
    image: str = DEFAULT_IMAGE,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> Iterator[str]:
    if server_url:
        yield server_url
        return

    discovered = _discover_server_url()
    if discovered:
        yield discovered
        return

    engine = _choose_container_engine()
    port = _pick_free_port()
    url = f"http://{DEFAULT_SERVER_HOST}:{port}"
    container_name = f"plantuml-cli-{uuid.uuid4().hex[:8]}"
    run_cmd = [
        engine,
        "run",
        "-d",
        "--rm",
        "--name",
        container_name,
        "-p",
        f"{DEFAULT_SERVER_HOST}:{port}:8080",
        image,
    ]
    completed = subprocess.run(
        run_cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise RuntimeError(f"Failed to start PlantUML server via {engine}: {details}")

    cleanup_warning: str | None = None
    try:
        _wait_for_server(url, timeout_s)
        yield url
    finally:
        stop = subprocess.run(
            [engine, "rm", "-f", container_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if stop.returncode != 0:
            cleanup_warning = stop.stderr.strip() or stop.stdout.strip() or "unknown error"
        if cleanup_warning:
            print(
                f"warning: failed to cleanup PlantUML server container {container_name}: {cleanup_warning}",
                file=sys.stderr,
            )


def _formatter() -> type[argparse.HelpFormatter]:
    return _DefaultsWithRawEpilogFormatter


def _shared_server_parent() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False, formatter_class=_formatter())
    parent.add_argument(
        "--server-url",
        metavar="URL",
        default=os.environ.get("PLANTUML_SERVER_URL"),
        help="PlantUML server base URL. If unset, discover a running container or start a temporary one.",
    )
    parent.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        metavar="SEC",
        help="Seconds to wait for a temporary PlantUML server to become ready.",
    )
    parent.add_argument(
        "--image",
        default=DEFAULT_IMAGE,
        metavar="REF",
        help="Image for temporary PlantUML server (podman/docker run).",
    )
    return parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=_ROOT_DESCRIPTION,
        epilog=_ROOT_EPILOG,
        formatter_class=_formatter(),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    shared = _shared_server_parent()

    render = subparsers.add_parser(
        "render",
        parents=[shared],
        description="Render a .puml file to SVG using the PlantUML server.",
        epilog=_RENDER_EPILOG,
        formatter_class=_formatter(),
    )
    render.add_argument("--input", required=True, type=Path, help="Input .puml file.")
    render.add_argument("--output", required=True, type=Path, help="Output .svg path.")

    lint = subparsers.add_parser(
        "lint",
        parents=[shared],
        description="Validate a .puml file by rendering to a temporary SVG (discards output).",
        epilog=_LINT_EPILOG,
        formatter_class=_formatter(),
    )
    lint.add_argument("--input", required=True, type=Path, help="Input .puml file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with managed_server(
            args.server_url,
            image=args.image,
            timeout_s=args.timeout,
        ) as server_url:
            if args.command == "render":
                render_plantuml(args.input, args.output, server_url)
                print(f"rendered {args.input} -> {args.output} via {server_url}")
                return 0
            if args.command == "lint":
                lint_plantuml(args.input, server_url)
                print(f"lint ok: {args.input} via {server_url}")
                return 0
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"error: unknown command {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
