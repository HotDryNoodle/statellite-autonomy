#!/usr/bin/env python3
"""Generate contract <-> code <-> tests traceability artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_RE = re.compile(r"@contract\{([A-Za-z][A-Za-z0-9_]*)\}")
VERIFY_RE = re.compile(r"@verify\{([A-Za-z][A-Za-z0-9_]*)\}")
COVERS_RE = re.compile(r"@covers\{([^}]+)\}")
GTEST_RE = re.compile(
    r"^\s*TEST(?:_F|_P)?\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"
)


def write_if_changed(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = text.rstrip() + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == rendered:
        return
    path.write_text(rendered, encoding="utf-8")


def read_contract_index(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def snippet(lines: list[str], line_no: int, radius: int = 4) -> str:
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)
    return "\n".join(lines[start - 1 : end])


def symbol_near(lines: list[str], line_no: int) -> str:
    for line in lines[line_no - 1 : min(len(lines), line_no + 8)]:
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("//"):
            continue
        return stripped
    return lines[line_no - 1].strip()


def scan_code(repo_root: Path) -> dict[str, list[dict[str, object]]]:
    evidence: dict[str, list[dict[str, object]]] = {}
    for path in sorted((repo_root / "product" / "src").rglob("*")):
        if path.suffix not in {".h", ".hpp", ".hh", ".cpp", ".cc", ".cxx"}:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        rel = str(path.relative_to(repo_root))
        for index, line in enumerate(lines, start=1):
            for clause_id in CONTRACT_RE.findall(line):
                evidence.setdefault(clause_id, []).append(
                    {
                        "path": rel,
                        "line": index,
                        "symbol": symbol_near(lines, index),
                        "snippet": snippet(lines, index),
                    }
                )
    return evidence


def scan_tests(repo_root: Path) -> tuple[dict[str, list[dict[str, object]]], dict[str, list[dict[str, object]]]]:
    verifies: dict[str, list[dict[str, object]]] = {}
    covers: dict[str, list[dict[str, object]]] = {}

    for path in sorted((repo_root / "product" / "tests").rglob("*.cpp")):
        lines = path.read_text(encoding="utf-8").splitlines()
        rel = str(path.relative_to(repo_root))
        comment_buffer: list[str] = []

        for index, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("/**") or stripped.startswith("*") or stripped.startswith("*/"):
                comment_buffer.append(line)
                continue
            if stripped.startswith("//"):
                comment_buffer.append(line)
                continue

            test_match = GTEST_RE.match(line)
            if test_match:
                suite, case = test_match.groups()
                joined = "\n".join(comment_buffer)
                verify_ids = VERIFY_RE.findall(joined)
                covered_symbols = COVERS_RE.findall(joined)
                test_entry = {
                    "path": rel,
                    "line": index,
                    "suite": suite,
                    "case": case,
                    "snippet": snippet(lines, index, radius=12),
                    "covers": covered_symbols,
                }
                for verify_id in verify_ids:
                    verifies.setdefault(verify_id, []).append(test_entry)
                for symbol in covered_symbols:
                    covers.setdefault(symbol, []).append(test_entry)
                comment_buffer = []
                continue

            if stripped:
                comment_buffer = []

    return verifies, covers


def percent(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{(100.0 * numerator / denominator):.1f}%"


def generate(repo_root: Path, output_dir: Path) -> dict[str, Path]:
    contract_index_path = output_dir / "contract_index.json"
    contract_index = read_contract_index(contract_index_path)
    contracts = contract_index["contracts"]
    verifies = contract_index["verifies"]

    code_evidence = scan_code(repo_root)
    test_evidence, covered_api = scan_tests(repo_root)

    trace_contracts: dict[str, object] = {}
    trace_verifies: dict[str, object] = {}

    contract_lines = [
        "# Clause Trace Matrix",
        "",
        "| ClauseId | Code | Verify | Tests | Status |",
        "| --- | --- | --- | --- | --- |",
    ]

    for clause_id, clause in sorted(contracts.items()):
        linked_verify_ids = sorted(
            verify_id
            for verify_id, verify in verifies.items()
            if clause_id in verify.get("linked_contract_ids", [])
        )
        tests = []
        for verify_id in linked_verify_ids:
            tests.extend(test_evidence.get(verify_id, []))
        trace_contracts[clause_id] = {
            "module": clause["module"],
            "desc": clause.get("desc", ""),
            "code_refs": code_evidence.get(clause_id, []),
            "verify_refs": linked_verify_ids,
            "test_refs": tests,
        }
        status = "covered" if code_evidence.get(clause_id) and tests else "partial" if code_evidence.get(clause_id) or tests else "missing"
        contract_lines.append(
            "| `{}` | {} | {} | {} | {} |".format(
                clause_id,
                len(code_evidence.get(clause_id, [])),
                len(linked_verify_ids),
                len(tests),
                status,
            )
        )

    for verify_id, verify in sorted(verifies.items()):
        trace_verifies[verify_id] = {
            "module": verify["module"],
            "desc": verify.get("desc", ""),
            "linked_contract_ids": verify.get("linked_contract_ids", []),
            "test_refs": test_evidence.get(verify_id, []),
        }

    trace_payload = {
        "contracts": trace_contracts,
        "verifies": trace_verifies,
        "covered_apis": covered_api,
    }

    contract_total = len(contracts)
    contract_with_code = sum(1 for clause_id in contracts if code_evidence.get(clause_id))
    contract_with_tests = sum(
        1
        for clause_id in contracts
        if any(
            clause_id in verify.get("linked_contract_ids", []) and test_evidence.get(verify_id)
            for verify_id, verify in verifies.items()
        )
    )
    verify_total = len(verifies)
    verify_with_tests = sum(1 for verify_id in verifies if test_evidence.get(verify_id))

    requirements_lines = [
        "# Contract Coverage Summary",
        "",
        "| Metric | Covered | Total | Coverage |",
        "| --- | --- | --- | --- |",
        f"| Contracts with code evidence | {contract_with_code} | {contract_total} | {percent(contract_with_code, contract_total)} |",
        f"| Contracts with test evidence | {contract_with_tests} | {contract_total} | {percent(contract_with_tests, contract_total)} |",
    ]

    test_lines = [
        "# Verify Coverage Summary",
        "",
        "| Metric | Covered | Total | Coverage |",
        "| --- | --- | --- | --- |",
        f"| Verify obligations with tests | {verify_with_tests} | {verify_total} | {percent(verify_with_tests, verify_total)} |",
    ]

    trace_json = output_dir / "trace.json"
    write_if_changed(trace_json, json.dumps(trace_payload, ensure_ascii=False, indent=2))
    contract_md = output_dir / "clause_trace_matrix.md"
    write_if_changed(contract_md, "\n".join(contract_lines))
    requirements_md = output_dir / "contract_coverage_summary.md"
    write_if_changed(requirements_md, "\n".join(requirements_lines))
    test_md = output_dir / "verify_coverage_summary.md"
    write_if_changed(test_md, "\n".join(test_lines))

    return {
        "trace_json": trace_json,
        "clause_trace_matrix": contract_md,
        "contract_coverage_summary": requirements_md,
        "verify_coverage_summary": test_md,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/_generated/traceability"),
    )
    args = parser.parse_args()

    outputs = generate(REPO_ROOT, args.output_dir)
    print(json.dumps({key: str(path) for key, path in outputs.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
