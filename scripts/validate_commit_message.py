#!/usr/bin/env python3
"""Validate repository commit messages against the relaxed local spec."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


HEADER_PATTERN = re.compile(
    r"^(feat|fix|refactor|docs|test|build|ci|chore|perf|trace)"
    r"(\([a-z0-9][a-z0-9,-]*\))?: [^\n]{1,72}$"
)


def load_message(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_message(message: str) -> tuple[bool, str]:
    if not message.strip():
        return False, "commit message is empty"

    header = message.splitlines()[0] if message.splitlines() else ""
    if not HEADER_PATTERN.fullmatch(header):
        return (
            False,
            "first line must match '<type>(<scope>): <summary>' with optional scope "
            "and summary length 1..72",
        )
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
    print("See commit-message-relaxed-spec.md for the local template.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
