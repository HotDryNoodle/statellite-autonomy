#!/usr/bin/env python3
"""Manual stdio wrapper for traceability CLI generation and clause lookup."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "tools" / "traceability-mcp" / "traceability_cli.py"
PROTOCOL_VERSION = "2024-11-05"


TOOLS = [
    {
        "name": "traceability_generate",
        "description": "Generate contract, code, and test traceability markdown and JSON artifacts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outputDir": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "traceability_query_clause",
        "description": "Return traceability evidence for one contract or verify clause id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "clauseId": {"type": "string"},
                "outputDir": {"type": "string"},
            },
            "required": ["clauseId"],
            "additionalProperties": False,
        },
    },
    {
        "name": "traceability_status",
        "description": "Return traceability coverage counts after regenerating artifacts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outputDir": {"type": "string"},
            },
            "additionalProperties": False,
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
        decoded = line.decode("utf-8")
        if ":" not in decoded:
            raise ValueError(f"Invalid header line: {decoded.strip()}")
        name, value = decoded.split(":", 1)
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
                "serverInfo": {"name": "traceability-cli", "version": "0.2.0"},
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
            "traceability_generate": "generate",
            "traceability_query_clause": "query-clause",
            "traceability_status": "status",
        }
        if name not in mapping:
            return make_error(request_id, -32602, f"Unknown tool: {name}")
        extra_args: list[str] = []
        if params.get("outputDir"):
            extra_args += ["--output-dir", params["outputDir"]]
        if params.get("clauseId"):
            extra_args.append(params["clauseId"])
        return_code, output = run_cli(mapping[name], extra_args)
        return make_response(request_id, tool_result(output, is_error=return_code != 0))
    return make_error(request_id, -32601, f"Method not found: {method}")


def main() -> int:
    while True:
        try:
            message = read_message()
        except Exception as exc:
            write_message(
                make_error(None, -32700, f"Failed to parse incoming message: {exc}")
            )
            return 1
        if message is None:
            return 0
        try:
            response = handle_request(message)
        except Exception as exc:
            response = make_error(message.get("id"), -32603, f"Internal error: {exc}")
        if response is not None:
            write_message(response)


if __name__ == "__main__":
    raise SystemExit(main())
