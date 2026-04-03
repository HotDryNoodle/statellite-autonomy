#!/usr/bin/env python3
"""Validate repository commit messages against the strict local spec."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


HEADER_PATTERN = re.compile(
    r"^(feat|fix|refactor|docs|test|build|ci|chore|perf|trace)"
    r"(\([a-z0-9][a-z0-9,-]*\))?: [^\n]{1,72}$"
)
REQUIRED_SECTIONS = (
    "Goal:",
    "Changes:",
    "Contracts:",
    "Traceability:",
    "Validation:",
    "Refs:",
)


def load_message(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_message(message: str) -> tuple[bool, str]:
    if not message.strip():
        return False, "commit message is empty"

    lines = message.splitlines()
    header = lines[0] if lines else ""
    if not HEADER_PATTERN.fullmatch(header):
        return (
            False,
            "first line must match '<type>(<scope>): <summary>' with optional scope "
            "and summary length 1..72",
        )

    section_positions: list[int] = []
    for section in REQUIRED_SECTIONS:
        position = next((index for index, line in enumerate(lines) if line.strip() == section), -1)
        if position < 0:
            return False, f"missing required section: {section}"
        section_positions.append(position)

    if section_positions != sorted(section_positions):
        return False, "required sections must appear in the fixed order"

    for index, section in enumerate(REQUIRED_SECTIONS):
        start = section_positions[index] + 1
        end = section_positions[index + 1] if index + 1 < len(REQUIRED_SECTIONS) else len(lines)
        block = [line.strip() for line in lines[start:end] if line.strip()]
        if not block:
            return False, f"section {section} must contain content or 'None'"
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("message_file", type=Path)
    args = parser.parse_args()

    ok, error = validate_message(load_message(args.message_file))
    if ok:
        return 0

    print("ERROR: commit message format invalid.", file=sys.stderr)
    print(error, file=sys.stderr)
    print(
        "Allowed types: feat|fix|refactor|docs|test|build|ci|chore|perf|trace",
        file=sys.stderr,
    )
    print("Required sections: Goal, Changes, Contracts, Traceability, Validation, Refs", file=sys.stderr)
    print(
        "See skills/commit-message-policy/references/summary-and-examples.md for the local template.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
