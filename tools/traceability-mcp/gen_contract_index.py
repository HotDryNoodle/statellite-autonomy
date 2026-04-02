#!/usr/bin/env python3
"""Build a lightweight contract/verify obligation index for this repository."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_RE = re.compile(r"@contract\{([A-Za-z][A-Za-z0-9_]*)\}")
VERIFY_RE = re.compile(r"@verify\{([A-Za-z][A-Za-z0-9_]*)\}")


def write_if_changed(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = text.rstrip() + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == rendered:
        return
    path.write_text(rendered, encoding="utf-8")


def parse_table_rows(lines: list[str], heading_prefix: str) -> list[list[str]]:
    start = -1
    for index, line in enumerate(lines):
        if line.startswith(heading_prefix):
            start = index + 1
            break
    if start < 0:
        return []

    rows: list[list[str]] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or cells[0].startswith("---") or cells[0] in {"ClauseId", "verify-ID"}:
            continue
        rows.append(cells)
    return rows


def first_match_line(lines: list[str], token: str) -> int:
    for index, line in enumerate(lines, start=1):
        if token in line:
            return index
    return 0


def parse_contract_file(path: Path) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    module = path.name.removesuffix(".contract.md")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    contracts: dict[str, dict[str, object]] = {}
    verifies: dict[str, dict[str, object]] = {}

    for row in parse_table_rows(lines, "## 附录A："):
        clause_match = CONTRACT_RE.search(row[0])
        if not clause_match:
            continue
        clause_id = clause_match.group(1)
        contracts[clause_id] = {
            "module": module,
            "desc": row[1] if len(row) > 1 else "",
            "location": row[2] if len(row) > 2 else "",
            "source_file": str(path.relative_to(REPO_ROOT)),
            "line": first_match_line(lines, clause_id),
        }

    current_verify: str | None = None
    for index, line in enumerate(lines, start=1):
        verify_match = VERIFY_RE.search(line)
        if verify_match:
            current_verify = verify_match.group(1)
            verifies.setdefault(
                current_verify,
                {
                    "module": module,
                    "desc": "",
                    "location": "",
                    "linked_contract_ids": [],
                    "source_file": str(path.relative_to(REPO_ROOT)),
                    "line": index,
                },
            )
            continue

        if current_verify is None:
            continue
        if line.startswith("## "):
            current_verify = None
            continue

        stripped = line.strip()
        if stripped.startswith("- 目的："):
            verifies[current_verify]["desc"] = stripped.removeprefix("- 目的：").strip()
        elif stripped.startswith("- 关联合同："):
            linked = []
            for contract_id in CONTRACT_RE.findall(stripped):
                if contract_id not in linked:
                    linked.append(contract_id)
            verifies[current_verify]["linked_contract_ids"] = linked

    appendix_b_rows = parse_table_rows(lines, "## 附录B：")
    for row in appendix_b_rows:
        verify_match = VERIFY_RE.search(row[0])
        if not verify_match:
            continue
        verify_id = verify_match.group(1)
        verifies.setdefault(
            verify_id,
            {
                "module": module,
                "desc": row[1] if len(row) > 1 else "",
                "location": row[3] if len(row) > 3 else "",
                "linked_contract_ids": [],
                "source_file": str(path.relative_to(REPO_ROOT)),
                "line": first_match_line(lines, verify_id),
            },
        )
        if not verifies[verify_id]["desc"] and len(row) > 1:
            verifies[verify_id]["desc"] = row[1]
        if not verifies[verify_id]["location"] and len(row) > 3:
            verifies[verify_id]["location"] = row[3]
        if len(row) > 2 and not verifies[verify_id]["linked_contract_ids"]:
            verifies[verify_id]["linked_contract_ids"] = CONTRACT_RE.findall(row[2])

    return contracts, verifies


def build_index(repo_root: Path) -> dict[str, object]:
    contracts: dict[str, dict[str, object]] = {}
    verifies: dict[str, dict[str, object]] = {}
    modules: dict[str, dict[str, list[str]]] = {}

    for path in sorted((repo_root / "contracts").glob("*.contract.md")):
        file_contracts, file_verifies = parse_contract_file(path)
        contracts.update(file_contracts)
        verifies.update(file_verifies)
        module = path.name.removesuffix(".contract.md")
        modules[module] = {
            "contracts": sorted(file_contracts.keys()),
            "verifies": sorted(file_verifies.keys()),
        }

    return {
        "generated_from": "contracts/*.contract.md",
        "contracts": contracts,
        "verifies": verifies,
        "modules": modules,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/_generated/traceability/contract_index.json"),
    )
    args = parser.parse_args()

    payload = build_index(REPO_ROOT)
    write_if_changed(args.output, json.dumps(payload, ensure_ascii=False, indent=2))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
