#!/usr/bin/env python3
"""Shared helpers for memory/dashboard validation and rendering."""

from __future__ import annotations

from pathlib import Path


TASK_STATUSES = {
    "active",
    "planned",
    "blocked",
    "ready_for_impl",
    "ready_for_verify",
    "ready_for_acceptance",
}
TASK_BOARD_HEADER = [
    "task_id",
    "title",
    "owner_agent",
    "affected_contracts",
    "status",
    "acceptance",
    "blockers",
]


def parse_markdown_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    table_lines = [line for line in lines if line.strip().startswith("|")]
    if len(table_lines) < 2:
        raise ValueError(f"{path} must contain a markdown table")

    header = [cell.strip() for cell in table_lines[0].strip().strip("|").split("|")]
    separator = [cell.strip() for cell in table_lines[1].strip().strip("|").split("|")]
    if len(separator) != len(header) or any(not cell.startswith("---") for cell in separator):
        raise ValueError(f"{path} has an invalid table separator")

    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(header):
            raise ValueError(f"{path} has a malformed table row: {line}")
        rows.append(dict(zip(header, cells)))

    return header, rows


def parse_task_board(path: Path) -> list[dict[str, str]]:
    header, rows = parse_markdown_table(path)
    if header != TASK_BOARD_HEADER:
        raise ValueError(f"{path} has an unexpected task board header: {header}")
    for row in rows:
        status = row.get("status", "")
        if status not in TASK_STATUSES:
            raise ValueError(f"{path} contains unsupported task status: {status}")
    return rows
