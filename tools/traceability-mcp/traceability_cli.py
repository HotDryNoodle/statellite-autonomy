#!/usr/bin/env python3
"""Traceability generation and query helpers."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "_generated" / "traceability"


def run(cmd: list[str]) -> int:
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        if completed.stdout.strip():
            print(completed.stdout.strip())
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
    return completed.returncode


def ensure_generated(output_dir: Path) -> int:
    index_cmd = [
        sys.executable,
        str(REPO_ROOT / "tools" / "traceability-mcp" / "gen_contract_index.py"),
        "--output",
        str(output_dir / "contract_index.json"),
    ]
    if run(index_cmd) != 0:
        return 1
    trace_cmd = [
        sys.executable,
        str(REPO_ROOT / "tools" / "traceability-mcp" / "gen_trace.py"),
        "--output-dir",
        str(output_dir),
    ]
    return run(trace_cmd)


def load_trace(output_dir: Path) -> dict[str, object]:
    return json.loads((output_dir / "trace.json").read_text(encoding="utf-8"))


def cmd_generate(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    if ensure_generated(output_dir) != 0:
        return 1
    payload = {
        "output_dir": str(output_dir),
        "files": sorted(str(path) for path in output_dir.glob("*")),
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_query_clause(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    if ensure_generated(output_dir) != 0:
        return 1
    trace = load_trace(output_dir)
    clause_id = args.clause_id
    if clause_id in trace["contracts"]:
        payload = {"kind": "contract", "clause_id": clause_id, **trace["contracts"][clause_id]}
    elif clause_id in trace["verifies"]:
        payload = {"kind": "verify", "clause_id": clause_id, **trace["verifies"][clause_id]}
    else:
        print(json.dumps({"error": f"unknown clause id: {clause_id}"}, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    if ensure_generated(output_dir) != 0:
        return 1
    trace = load_trace(output_dir)
    contracts = trace["contracts"]
    verifies = trace["verifies"]
    payload = {
        "output_dir": str(output_dir),
        "contract_count": len(contracts),
        "verify_count": len(verifies),
        "contracts_with_code": sum(1 for item in contracts.values() if item["code_refs"]),
        "contracts_with_tests": sum(1 for item in contracts.values() if item["test_refs"]),
        "verifies_with_tests": sum(1 for item in verifies.values() if item["test_refs"]),
    }
    print(json.dumps(payload, indent=2))
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    generate.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    generate.set_defaults(handler=cmd_generate)

    query = subparsers.add_parser("query-clause")
    query.add_argument("clause_id")
    query.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    query.set_defaults(handler=cmd_query_clause)

    status = subparsers.add_parser("status")
    status.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    status.set_defaults(handler=cmd_status)

    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
