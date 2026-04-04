#!/usr/bin/env python3
"""Traceability generation and query helpers."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "_generated" / "traceability"
CLI_PATH = "python3 tools/traceability-cli/traceability_cli.py"


class HelpFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    """Formatter that keeps example blocks readable and shows defaults."""


def print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def shell_join(cmd: list[str]) -> str:
    return shlex.join(cmd)


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


def normalize_output_dir(path_text: str) -> Path:
    output_dir = Path(path_text)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    return output_dir


def generation_commands(output_dir: Path) -> list[list[str]]:
    return [
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "traceability-cli" / "gen_contract_index.py"),
            "--output",
            str(output_dir / "contract_index.json"),
        ],
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "traceability-cli" / "gen_trace.py"),
            "--output-dir",
            str(output_dir),
        ],
    ]


def emit_dry_run(command_name: str,
                 commands: list[list[str]],
                 writes: list[str],
                 notes: list[str]) -> int:
    print_json(
        {
            "command": command_name,
            "dry_run": True,
            "commands": [shell_join(cmd) for cmd in commands],
            "writes": writes,
            "notes": notes,
        }
    )
    return 0


def maybe_warn_overwrite(path: Path, yes: bool) -> None:
    if path.exists() and not yes:
        print(
            (
                f"warning: overwriting existing file: {path}\n"
                f"hint: rerun with --yes to acknowledge the overwrite explicitly."
            ),
            file=sys.stderr,
        )


def ensure_generated(output_dir: Path) -> int:
    commands = generation_commands(output_dir)
    if run(commands[0]) != 0:
        return 1
    return run(commands[1])


def load_trace(output_dir: Path) -> dict[str, object]:
    return json.loads((output_dir / "trace.json").read_text(encoding="utf-8"))


def load_trace_or_error(output_dir: Path) -> dict[str, object] | None:
    trace_path = output_dir / "trace.json"
    if trace_path.exists():
        return load_trace(output_dir)
    print_json(
        {
            "error": f"missing generated trace output: {trace_path}",
            "hint": "Run generate first or rerun this command with --refresh.",
            "examples": [
                f"{CLI_PATH} generate --output-dir {output_dir}",
                f"{CLI_PATH} status --output-dir {output_dir} --refresh",
            ],
        }
    )
    return None


def cmd_generate(args: argparse.Namespace) -> int:
    output_dir = normalize_output_dir(args.output_dir)
    commands = generation_commands(output_dir)
    if args.dry_run:
        return emit_dry_run(
            "generate",
            commands,
            writes=[str(output_dir)],
            notes=[
                "Dry-run does not regenerate any traceability artifacts.",
                "Use --yes to acknowledge overwriting existing generated artifacts.",
            ],
        )
    maybe_warn_overwrite(output_dir / "trace.json", args.yes)
    if ensure_generated(output_dir) != 0:
        return 1
    payload = {
        "output_dir": str(output_dir),
        "files": sorted(str(path) for path in output_dir.glob("*")),
    }
    print_json(payload)
    return 0


def cmd_query_clause(args: argparse.Namespace) -> int:
    output_dir = normalize_output_dir(args.output_dir)
    if args.refresh:
        if args.dry_run:
            return emit_dry_run(
                "query-clause",
                generation_commands(output_dir),
                writes=[str(output_dir)],
                notes=["Dry-run only previews the refresh step before querying the clause."],
            )
        if ensure_generated(output_dir) != 0:
            return 1
    trace = load_trace_or_error(output_dir)
    if trace is None:
        return 1
    clause_id = args.clause_id
    if clause_id in trace["contracts"]:
        payload = {"kind": "contract", "clause_id": clause_id, **trace["contracts"][clause_id]}
    elif clause_id in trace["verifies"]:
        payload = {"kind": "verify", "clause_id": clause_id, **trace["verifies"][clause_id]}
    else:
        known_ids = sorted(list(trace["contracts"].keys()) + list(trace["verifies"].keys()))
        print_json(
            {
                "error": f"unknown clause id: {clause_id}",
                "hint": "Use a known ClauseId from the generated trace output or refresh the artifacts first.",
                "examples": [
                    f"{CLI_PATH} query-clause TimeSys_4_4_4",
                    f"{CLI_PATH} query-clause LayerBoundary_4_1",
                    f"{CLI_PATH} query-clause {clause_id} --refresh",
                ],
                "known_clause_examples": known_ids[:5],
            }
        )
        return 1
    print_json(payload)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    output_dir = normalize_output_dir(args.output_dir)
    if args.refresh:
        if args.dry_run:
            return emit_dry_run(
                "status",
                generation_commands(output_dir),
                writes=[str(output_dir)],
                notes=["Dry-run only previews the refresh step before reading status."],
            )
        if ensure_generated(output_dir) != 0:
            return 1
    trace = load_trace_or_error(output_dir)
    if trace is None:
        return 1
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
    print_json(payload)
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CLI-first traceability generation and query helpers.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} generate --output-dir docs/_generated/traceability --yes\n"
            f"  {CLI_PATH} generate --dry-run\n"
            f"  {CLI_PATH} status --output-dir docs/_generated/traceability\n"
            f"  {CLI_PATH} status --refresh\n"
            f"  {CLI_PATH} query-clause TimeSys_4_4_4\n"
            f"  {CLI_PATH} query-clause LayerBoundary_4_1 --refresh"
        ),
        formatter_class=HelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate",
        description="Generate ClauseId traceability artifacts under docs/_generated/traceability.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} generate --output-dir docs/_generated/traceability --yes\n"
            f"  {CLI_PATH} generate --dry-run"
        ),
        formatter_class=HelpFormatter,
    )
    generate.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    generate.add_argument(
        "--dry-run",
        action="store_true",
        help="print the generation commands without writing artifacts",
    )
    generate.add_argument(
        "--yes",
        action="store_true",
        help="acknowledge overwriting existing generated artifacts",
    )
    generate.set_defaults(handler=cmd_generate)

    query = subparsers.add_parser(
        "query-clause",
        description="Query one ClauseId from previously generated traceability artifacts.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} query-clause TimeSys_4_4_4\n"
            f"  {CLI_PATH} query-clause LayerBoundary_4_1 --refresh\n"
            f"  {CLI_PATH} query-clause HarnessBoundary_2_3 --output-dir docs/_generated/traceability"
        ),
        formatter_class=HelpFormatter,
    )
    query.add_argument("clause_id")
    query.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    query.add_argument(
        "--refresh",
        action="store_true",
        help="regenerate artifacts before querying",
    )
    query.add_argument(
        "--dry-run",
        action="store_true",
        help="with --refresh, preview the regeneration step without writing artifacts",
    )
    query.set_defaults(handler=cmd_query_clause)

    status = subparsers.add_parser(
        "status",
        description="Summarize the currently generated traceability artifacts.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} status\n"
            f"  {CLI_PATH} status --refresh\n"
            f"  {CLI_PATH} status --output-dir docs/_generated/traceability"
        ),
        formatter_class=HelpFormatter,
    )
    status.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    status.add_argument(
        "--refresh",
        action="store_true",
        help="regenerate artifacts before reading status",
    )
    status.add_argument(
        "--dry-run",
        action="store_true",
        help="with --refresh, preview the regeneration step without writing artifacts",
    )
    status.set_defaults(handler=cmd_status)

    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
