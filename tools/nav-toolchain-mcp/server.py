#!/usr/bin/env python3
"""stdio MCP server for the local Meson toolchain."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "tools" / "nav-toolchain-mcp" / "toolchain_mcp.py"

PROTOCOL_VERSION = "2024-11-05"


TOOLS = [
    {
        "name": "nav_toolchain_status",
        "description": "Return repository, build, and traceability status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "buildDir": {"type": "string"},
                "crossFile": {"type": "string"},
                "nativeFile": {"type": "string"}
            },
            "additionalProperties": False
        },
    },
    {
        "name": "nav_toolchain_build",
        "description": "Run Meson setup/compile for native or cross builds.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "buildDir": {"type": "string"},
                "crossFile": {"type": "string"},
                "nativeFile": {"type": "string"},
                "reconfigure": {"type": "boolean"},
                "mesonOptions": {"type": "array", "items": {"type": "string"}},
                "compileArgs": {"type": "array", "items": {"type": "string"}}
            },
            "additionalProperties": False
        },
    },
    {
        "name": "nav_toolchain_test",
        "description": "Run Meson tests for a native or cross-configured build directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "buildDir": {"type": "string"},
                "testName": {"type": "string"},
                "noRebuild": {"type": "boolean"},
                "crossFile": {"type": "string"},
                "nativeFile": {"type": "string"},
                "reconfigure": {"type": "boolean"},
                "mesonOptions": {"type": "array", "items": {"type": "string"}}
            },
            "additionalProperties": False
        },
    },
    {
        "name": "nav_toolchain_traceability",
        "description": "Generate traceability artifacts from contracts, code, and tests.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outputDir": {"type": "string"}
            },
            "additionalProperties": False
        },
    },
    {
        "name": "nav_toolchain_benchmark",
        "description": "Generate the current benchmark report placeholder for a target build configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "buildDir": {"type": "string"},
                "crossFile": {"type": "string"},
                "nativeFile": {"type": "string"},
                "reportPath": {"type": "string"}
            },
            "additionalProperties": False
        },
    },
]


def read_message() -> dict | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        name, value = line.decode("utf-8").split(":", 1)
        headers[name.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    payload = sys.stdin.buffer.read(length)
    return json.loads(payload.decode("utf-8"))


def write_message(message: dict) -> None:
    payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8"))
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def make_response(request_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def make_error(request_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def run_cli(subcommand: str, extra_args: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        [sys.executable, str(CLI), subcommand] + extra_args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()
    if completed.stderr.strip():
        output = (output + "\n" + completed.stderr.strip()).strip()
    return completed.returncode, output


def tool_result(text: str, is_error: bool = False) -> dict:
    return {
        "content": [{"type": "text", "text": text or "(no output)"}],
        "isError": is_error,
    }


def handle_request(message: dict) -> dict | None:
    method = message.get("method")
    request_id = message.get("id")

    if method == "initialize":
        return make_response(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "nav-toolchain", "version": "0.1.0"},
            },
        )

    if method == "notifications/initialized":
        return None

    if method == "ping":
        return make_response(request_id, {})

    if method == "tools/list":
        return make_response(request_id, {"tools": TOOLS})

    if method == "tools/call":
        params = message.get("params", {})
        name = params.get("name")
        mapping = {
            "nav_toolchain_status": "status",
            "nav_toolchain_build": "build",
            "nav_toolchain_test": "test",
            "nav_toolchain_traceability": "traceability",
            "nav_toolchain_benchmark": "benchmark",
        }
        if name not in mapping:
            return make_error(request_id, -32602, f"Unknown tool: {name}")
        extra_args: list[str] = []
        if "buildDir" in params:
            extra_args += ["--build-dir", params["buildDir"]]
        if params.get("crossFile"):
            extra_args += ["--cross-file", params["crossFile"]]
        if params.get("nativeFile"):
            extra_args += ["--native-file", params["nativeFile"]]
        if params.get("reconfigure"):
            extra_args.append("--reconfigure")
        for item in params.get("mesonOptions", []):
            extra_args += ["--meson-option", item]
        for item in params.get("compileArgs", []):
            extra_args += ["--compile-arg", item]
        if params.get("testName"):
            extra_args += ["--test-name", params["testName"]]
        if params.get("noRebuild"):
            extra_args.append("--no-rebuild")
        if params.get("outputDir"):
            extra_args += ["--output-dir", params["outputDir"]]
        if params.get("reportPath"):
            extra_args += ["--report-path", params["reportPath"]]
        return_code, output = run_cli(mapping[name], extra_args)
        return make_response(request_id, tool_result(output, is_error=return_code != 0))

    return make_error(request_id, -32601, f"Method not found: {method}")


def main() -> int:
    while True:
        message = read_message()
        if message is None:
            return 0
        response = handle_request(message)
        if response is not None:
            write_message(response)


if __name__ == "__main__":
    sys.exit(main())
