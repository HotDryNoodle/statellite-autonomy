#!/usr/bin/env python3
"""Product traceability and governance compliance helpers."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACE_OUTPUT_DIR = REPO_ROOT / "docs" / "_generated" / "traceability"
DEFAULT_COMPLIANCE_OUTPUT_DIR = REPO_ROOT / "docs" / "_generated" / "compliance"
CLI_PATH = "python3 tools/traceability-cli/traceability_cli.py"
COMPLIANCE_SELF_EXEMPT = {
    "tools/traceability-cli/traceability_cli.py",
}
GOVERNANCE_CLAUSE_PREFIXES = ("HarnessWorkflow_", "HarnessBoundary_", "EvalGovernance_")
LEGACY_FIELD_NAMES = ("affected_contracts", "allowed_contracts", "relevant_contracts")
SPEC_PATH_RE = re.compile(r"(contracts/[A-Za-z0-9_./-]+\.contract\.md|governance/[A-Za-z0-9_./-]+\.policy\.md)")
ANCHOR_RE = re.compile(r'<a id="([A-Za-z0-9_-]+)"></a>')
POLICY_REF_RE = re.compile(r"^governance/[A-Za-z0-9_./-]+\.policy\.md#[A-Za-z0-9_-]+$")


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


def normalize_output_dir(path_text: str, default_dir: Path) -> Path:
    output_dir = Path(path_text) if path_text else default_dir
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    return output_dir


def write_if_changed(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = text.rstrip() + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == rendered:
        return
    path.write_text(rendered, encoding="utf-8")


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


def emit_dry_run(
    command_name: str, commands: list[list[str]], writes: list[str], notes: list[str]
) -> int:
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


def tracked_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git ls-files failed")
    ignored_prefixes = ("docs/_generated/", "builddir/")
    files: list[Path] = []
    for line in completed.stdout.splitlines():
        if not line or line.endswith("/"):
            continue
        if line.startswith(ignored_prefixes):
            continue
        path = REPO_ROOT / line
        if path.exists():
            files.append(path)
    return files


def text_file(path: Path) -> bool:
    return path.suffix in {".md", ".json", ".py", ".txt", ".yaml", ".yml", ".cpp", ".hpp", ".h", ".cc"}


def parse_policy_anchors(path: Path) -> list[str]:
    anchors: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ANCHOR_RE.search(line)
        if match:
            anchors.append(match.group(1))
    return anchors


def build_policy_index() -> dict[str, object]:
    policies: dict[str, dict[str, object]] = {}
    policy_root = REPO_ROOT / "governance" / "policies"
    for path in sorted(policy_root.glob("*.policy.md")):
        rel = str(path.relative_to(REPO_ROOT))
        policies[rel] = {
            "anchors": parse_policy_anchors(path),
            "title": path.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip(),
        }
    return {
        "generated_from": "governance/policies/*.policy.md",
        "policies": policies,
    }


def json_strings(value: object) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, list):
        for item in value:
            strings.extend(json_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(json_strings(item))
    return strings


def run_compliance_checks(trace_output_dir: Path) -> tuple[dict[str, object], dict[str, object]]:
    policy_index = build_policy_index()
    trace = load_trace_or_error(trace_output_dir)
    if trace is None:
        raise RuntimeError("missing trace.json for compliance refresh")

    tracked = tracked_files()
    failures: list[dict[str, object]] = []

    missing_policy_files = [
        path
        for path in (
            "governance/policies/harness_workflow.policy.md",
            "governance/policies/harness_product_boundary.policy.md",
            "governance/policies/eval_governance.policy.md",
        )
        if not (REPO_ROOT / path).exists()
    ]
    if missing_policy_files:
        failures.append(
            {
                "check": "required_policies",
                "details": missing_policy_files,
            }
        )

    legacy_field_hits: list[str] = []
    for path in tracked:
        rel = str(path.relative_to(REPO_ROOT))
        if rel in COMPLIANCE_SELF_EXEMPT:
            continue
        if not text_file(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(name in text for name in LEGACY_FIELD_NAMES):
            legacy_field_hits.append(rel)
    if legacy_field_hits:
        failures.append({"check": "legacy_field_names", "details": legacy_field_hits})

    invalid_spec_hits: list[str] = []
    for path in tracked:
        rel = str(path.relative_to(REPO_ROOT))
        if rel in COMPLIANCE_SELF_EXEMPT:
            continue
        if not text_file(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in SPEC_PATH_RE.findall(text):
            if match.startswith("contracts/") and not (REPO_ROOT / match).exists():
                invalid_spec_hits.append(f"{rel}::{match}")
            if match.startswith("governance/") and not (REPO_ROOT / match).exists():
                invalid_spec_hits.append(f"{rel}::{match}")
    if invalid_spec_hits:
        failures.append({"check": "dangling_spec_paths", "details": invalid_spec_hits})

    governance_clause_hits: list[str] = []
    for domain_path in sorted((REPO_ROOT / "eval" / "domains").rglob("*.json")):
        payload = json.loads(domain_path.read_text(encoding="utf-8"))
        for item in json_strings(payload):
            if any(prefix in item for prefix in GOVERNANCE_CLAUSE_PREFIXES):
                governance_clause_hits.append(str(domain_path.relative_to(REPO_ROOT)))
                break
    if governance_clause_hits:
        failures.append({"check": "eval_metadata_uses_policy_refs", "details": governance_clause_hits})

    invalid_policy_refs: list[str] = []
    for domain_path in sorted((REPO_ROOT / "eval" / "domains").rglob("*.json")):
        payload = json.loads(domain_path.read_text(encoding="utf-8"))
        for item in json_strings(payload):
            if item.startswith("governance/"):
                if not POLICY_REF_RE.match(item):
                    invalid_policy_refs.append(f"{domain_path.relative_to(REPO_ROOT)}::{item}")
                    continue
                policy_path, anchor = item.split("#", 1)
                known_anchors = policy_index["policies"].get(policy_path, {}).get("anchors", [])
                if anchor not in known_anchors:
                    invalid_policy_refs.append(f"{domain_path.relative_to(REPO_ROOT)}::{item}")
    if invalid_policy_refs:
        failures.append({"check": "policy_anchor_refs", "details": invalid_policy_refs})

    governance_modules = sorted(
        module
        for module in trace.get("modules", {}).keys()
        if module in {"harness_workflow", "harness_product_boundary", "eval_governance"}
    )
    if governance_modules:
        failures.append({"check": "traceability_product_only", "details": governance_modules})

    status = {
        "output_dir": str(trace_output_dir),
        "policy_count": len(policy_index["policies"]),
        "trace_contract_count": len(trace.get("contracts", {})),
        "trace_verify_count": len(trace.get("verifies", {})),
        "ok": not failures,
        "failures": failures,
    }
    return policy_index, status


def load_json_or_error(path: Path, command_name: str, refresh_example: str) -> dict[str, object] | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    print_json(
        {
            "error": f"missing generated {command_name} output: {path}",
            "hint": f"Run {command_name} with --refresh first.",
            "examples": [refresh_example],
        }
    )
    return None


def cmd_generate(args: argparse.Namespace) -> int:
    output_dir = normalize_output_dir(args.output_dir, DEFAULT_TRACE_OUTPUT_DIR)
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
    output_dir = normalize_output_dir(args.output_dir, DEFAULT_TRACE_OUTPUT_DIR)
    if args.refresh:
        if args.dry_run:
            return emit_dry_run(
                "query-clause",
                generation_commands(output_dir),
                writes=[str(output_dir)],
                notes=["Dry-run only previews the refresh step before querying the ClauseId."],
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
                "hint": "Use a product ClauseId from the generated trace output or refresh the artifacts first.",
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
    output_dir = normalize_output_dir(args.output_dir, DEFAULT_TRACE_OUTPUT_DIR)
    if args.refresh:
        if args.dry_run:
            return emit_dry_run(
                "status",
                generation_commands(output_dir),
                writes=[str(output_dir)],
                notes=["Dry-run only previews the refresh step before reading product traceability status."],
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


def cmd_compliance(args: argparse.Namespace) -> int:
    trace_output_dir = DEFAULT_TRACE_OUTPUT_DIR
    output_dir = normalize_output_dir(args.output_dir, DEFAULT_COMPLIANCE_OUTPUT_DIR)
    commands = [[sys.executable, str(REPO_ROOT / "tools" / "traceability-cli" / "traceability_cli.py"), "status", "--refresh"]]
    if args.dry_run:
        return emit_dry_run(
            "compliance",
            commands,
            writes=[str(output_dir)],
            notes=["Dry-run only previews the product trace refresh and compliance artifact writes."],
        )
    if args.refresh:
        if ensure_generated(trace_output_dir) != 0:
            return 1
        policy_index, status = run_compliance_checks(trace_output_dir)
        status["output_dir"] = str(output_dir)
        write_if_changed(output_dir / "policy_index.json", json.dumps(policy_index, ensure_ascii=False, indent=2))
        write_if_changed(output_dir / "compliance_status.json", json.dumps(status, ensure_ascii=False, indent=2))
        print_json(status)
        return 0 if status["ok"] else 1

    status = load_json_or_error(
        output_dir / "compliance_status.json",
        "compliance",
        f"{CLI_PATH} compliance --refresh --output-dir {output_dir}",
    )
    if status is None:
        return 1
    print_json(status)
    return 0 if status.get("ok", False) else 1


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Product Clause traceability and governance compliance helpers.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} generate --output-dir docs/_generated/traceability --yes\n"
            f"  {CLI_PATH} status --refresh\n"
            f"  {CLI_PATH} query-clause TimeSys_4_4_4\n"
            f"  {CLI_PATH} compliance --refresh\n"
        ),
        formatter_class=HelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate",
        description="Generate product ClauseId traceability artifacts under docs/_generated/traceability.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} generate --output-dir docs/_generated/traceability --yes\n"
            f"  {CLI_PATH} generate --dry-run"
        ),
        formatter_class=HelpFormatter,
    )
    generate.add_argument("--output-dir", default=str(DEFAULT_TRACE_OUTPUT_DIR))
    generate.add_argument("--dry-run", action="store_true", help="print the generation commands without writing artifacts")
    generate.add_argument("--yes", action="store_true", help="acknowledge overwriting existing generated artifacts")
    generate.set_defaults(handler=cmd_generate)

    query = subparsers.add_parser(
        "query-clause",
        description="Query one product ClauseId from previously generated traceability artifacts.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} query-clause TimeSys_4_4_4\n"
            f"  {CLI_PATH} query-clause LayerBoundary_4_1 --refresh\n"
            f"  {CLI_PATH} query-clause PppFamily_5_5 --output-dir docs/_generated/traceability"
        ),
        formatter_class=HelpFormatter,
    )
    query.add_argument("clause_id")
    query.add_argument("--output-dir", default=str(DEFAULT_TRACE_OUTPUT_DIR))
    query.add_argument("--refresh", action="store_true", help="regenerate artifacts before querying")
    query.add_argument("--dry-run", action="store_true", help="with --refresh, preview the regeneration step without writing artifacts")
    query.set_defaults(handler=cmd_query_clause)

    status = subparsers.add_parser(
        "status",
        description="Summarize the currently generated product traceability artifacts.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} status\n"
            f"  {CLI_PATH} status --refresh\n"
            f"  {CLI_PATH} status --output-dir docs/_generated/traceability"
        ),
        formatter_class=HelpFormatter,
    )
    status.add_argument("--output-dir", default=str(DEFAULT_TRACE_OUTPUT_DIR))
    status.add_argument("--refresh", action="store_true", help="regenerate artifacts before reading status")
    status.add_argument("--dry-run", action="store_true", help="with --refresh, preview the regeneration step without writing artifacts")
    status.set_defaults(handler=cmd_status)

    compliance = subparsers.add_parser(
        "compliance",
        description="Check governance policy compliance without using Clause trace semantics.",
        epilog=(
            "Examples:\n"
            f"  {CLI_PATH} compliance --refresh\n"
            f"  {CLI_PATH} compliance --output-dir docs/_generated/compliance\n"
            f"  {CLI_PATH} compliance --dry-run"
        ),
        formatter_class=HelpFormatter,
    )
    compliance.add_argument("--output-dir", default=str(DEFAULT_COMPLIANCE_OUTPUT_DIR))
    compliance.add_argument("--refresh", action="store_true", help="regenerate compliance artifacts before reading status")
    compliance.add_argument("--dry-run", action="store_true", help="preview the compliance refresh step without writing artifacts")
    compliance.set_defaults(handler=cmd_compliance)

    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
