#!/usr/bin/env python3
"""PlantUML renderer with CLI and HTTP-server fallback.

Modes (controlled by env var PLANTUML_MODE, defaults to "auto"):

- cli: use local ``plantuml`` binary or ``java -jar $PLANTUML_JAR``.
- server: POST to a running PlantUML server
  (PLANTUML_SERVER_URL, default ``http://localhost:8080``).
- auto: prefer cli if available, otherwise fall back to server,
  otherwise raise with a helpful message.

Used by site/scripts/build_site.py. Can also be invoked directly:

    python3 site/scripts/render_plantuml.py \
        --input architecture/blueprints/system/harness-product-boundary.puml \
        --output /tmp/out.svg
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zlib
from pathlib import Path
from typing import Optional

DEFAULT_SERVER_URL = "http://localhost:8080"
PLANTUML_B64 = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
)


def _encode_six_bit(b: int) -> str:
    return PLANTUML_B64[b & 0x3F]


def _encode_three_bytes(b1: int, b2: int, b3: int) -> str:
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F
    return (
        _encode_six_bit(c1)
        + _encode_six_bit(c2)
        + _encode_six_bit(c3)
        + _encode_six_bit(c4)
    )


def encode_plantuml(text: str) -> str:
    """Encode PlantUML source to the URL-safe form used by plantuml-server."""

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


def _resolve_cli() -> Optional[list[str]]:
    plantuml_bin = shutil.which("plantuml")
    if plantuml_bin:
        return [plantuml_bin]
    jar = os.environ.get("PLANTUML_JAR")
    if jar and Path(jar).exists():
        java = shutil.which("java")
        if java:
            return [java, "-jar", jar]
    return None


def _render_via_cli(src: Path, dst: Path) -> None:
    cmd = _resolve_cli()
    if cmd is None:
        raise RuntimeError(
            "PlantUML CLI not found. Install `plantuml` package or set PLANTUML_JAR to a jar path."
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    out_dir = dst.parent
    proc = subprocess.run(
        [*cmd, "-tsvg", "-o", str(out_dir.resolve()), str(src)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"PlantUML CLI failed for {src}: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    produced = out_dir / (src.stem + ".svg")
    if produced != dst:
        if produced.exists():
            produced.replace(dst)
        else:
            raise RuntimeError(f"PlantUML CLI did not produce {produced}")


def _render_via_server(src: Path, dst: Path, server_url: str) -> None:
    text = src.read_text(encoding="utf-8")
    encoded = encode_plantuml(text)
    url = server_url.rstrip("/") + "/svg/" + encoded
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            payload = resp.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"PlantUML server request failed for {src}: {exc}"
        ) from exc
    if not payload.lstrip().startswith(b"<"):
        raise RuntimeError(
            f"PlantUML server returned non-SVG payload for {src} (first bytes: {payload[:40]!r})"
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(payload)


def render_plantuml(src: Path, dst: Path, mode: str = "auto") -> str:
    """Render a single .puml to .svg. Returns the mode actually used."""

    mode = mode.lower()
    server_url = os.environ.get("PLANTUML_SERVER_URL", DEFAULT_SERVER_URL)

    if mode == "cli":
        _render_via_cli(src, dst)
        return "cli"
    if mode == "server":
        _render_via_server(src, dst, server_url)
        return "server"
    if mode == "auto":
        if _resolve_cli() is not None:
            _render_via_cli(src, dst)
            return "cli"
        _render_via_server(src, dst, server_url)
        return "server"
    raise ValueError(f"unknown PLANTUML_MODE: {mode}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--mode",
        default=os.environ.get("PLANTUML_MODE", "auto"),
        choices=["auto", "cli", "server"],
    )
    args = parser.parse_args()

    try:
        used = render_plantuml(args.input, args.output, args.mode)
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"rendered {args.input} -> {args.output} via {used}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
